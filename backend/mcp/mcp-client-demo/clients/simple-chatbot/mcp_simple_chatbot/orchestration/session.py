import os, json, logging, asyncio
from typing import List, Dict, Any
from servers.base import Server
from llm.client import LLMClient
from servers.hooks import aws_diagram
from servers.hooks import cfn as cfn_hook

class ChatSession:
    def __init__(self, servers: List[Server], llm_client: LLMClient) -> None:
        self.servers = servers
        self.llm_client = llm_client

    async def _prewarm_servers(self):
        for s in self.servers:
            if s.name.endswith("aws-diagram-mcp-server"):
                await aws_diagram.prewarm(s)

    async def cleanup_servers(self) -> None:
        for server in reversed(self.servers):
            try:
                await server.cleanup()
            except Exception as e:
                logging.warning(f"Warning during final cleanup: {e}")

    async def process_llm_response(self, llm_response: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        def _clean_json_string(js: str) -> str:
            import re
            return re.sub(r"^```(?:\s*json)?\s*(.*?)\s*```$", r"\1", js, flags=re.S|re.I).strip()

        try:
            envelope = json.loads(_clean_json_string(llm_response))
            decision = envelope.get("decision")

            if decision == "answer":
                return {"mode": "answer", "text": envelope.get("answer") or "Entendido."}

            if decision == "tool":
                tool_name = envelope.get("tool")
                if not tool_name:
                    return {"mode": "answer", "text": "No tool specified."}

                # ---- Tool pipelines por nombre (extensible)
                pipelines = {
                    "generate_diagram": self._run_generate_diagram_pipeline,
                    **{t: self._run_cfn_tool_pipeline for t in cfn_hook.CFN_TOOLS},
                }
                if tool_name not in pipelines:
                    return {"mode": "answer", "text": f"No hay pipeline para la tool '{tool_name}'."}
                return await pipelines[tool_name](envelope)

            return {"mode": "raw", "text": llm_response}
        except json.JSONDecodeError:
            return {"mode": "raw", "text": llm_response}

    async def _run_generate_diagram_pipeline(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        # localizar server compatible
        for server in self.servers:
            tools = await server.list_tools()
            if any(t.name == "generate_diagram" for t in tools):
                try:
                    source_dir = os.path.dirname(os.path.abspath(__file__))
                except NameError:
                    source_dir = os.getcwd()
                source_dir = os.path.abspath(os.path.join(source_dir, ".."))  # raiz del proyecto

                # pre
                expected_png, tool_args, explanation = aws_diagram.preprocess_generate_diagram(envelope, source_dir)

                # exec
                result = await server.execute_tool("generate_diagram", tool_args)

                # post
                ok, msg = aws_diagram.postprocess_generate_diagram(
                    result, expected_png, tool_args["filename"], source_dir
                )
                if ok:
                    if explanation:
                        msg = (explanation.strip() or "") + ("\n" if explanation else "") + msg
                    return {"mode": "tool", "text": msg}
                return {"mode": "answer", "text": msg}

        return {"mode": "answer", "text": "No se encontró un servidor con 'generate_diagram'."}

    async def _run_cfn_tool_pipeline(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta cualquier herramienta del CloudFormation MCP Server."""
        tool_name, tool_args = cfn_hook.preprocess_cfn_tool(envelope)
        explanation = envelope.get("explanation") or ""

        # Buscar servidor que tenga la tool
        for server in self.servers:
            tools = await server.list_tools()
            if any(t.name == tool_name for t in tools):
                try:
                    logging.info(f"CFN: ejecutando '{tool_name}' en servidor '{server.name}'")
                    result = await server.execute_tool(tool_name, tool_args)
                    ok, msg, data = cfn_hook.postprocess_cfn_result(result, tool_name)
                    if explanation:
                        msg = f"{explanation.strip()}\n\n{msg}"
                    return {"mode": "tool", "text": msg, "cfn_data": data}
                except Exception as exc:
                    logging.exception(f"Error ejecutando CFN tool {tool_name}")
                    return {"mode": "answer", "text": f"Error al ejecutar `{tool_name}`: {exc}"}

        return {"mode": "answer", "text": f"No se encontró un servidor con la herramienta '{tool_name}'. Asegúrate de que el cfn-mcp-server esté configurado."}

    async def start(self) -> None:
        try:
            # init servers
            alive, errors = [], []
            for s in self.servers:
                try:
                    await s.initialize()
                    if s.session: alive.append(s)
                except Exception as e:
                    errors.append((s.name, str(e)))
            if not alive:
                for nm, err in errors:
                    logging.error("Server '%s' error: %s", nm, err)
                logging.error("No MCP servers available.")
                return
            self.servers = alive

            await self._prewarm_servers()

            messages: List[Dict[str, str]] = []
            while True:
                try:
                    user_input = input("You: ").strip()
                    # comandos de salida
                    if user_input.lower() in {"exit", "quit", "salir", "q", "x"}:
                        logging.info("Exiting...")
                        break
                    # ignorar entradas vacías
                    if not user_input:
                        continue

                    # agrega el turno del usuario
                    messages.append({"role": "user", "content": user_input})

                    # --- llamada al LLM (async) con manejo de errores ---
                    try:
                        llm_response = await self.llm_client.get_response(messages)  # ahora es async
                    except Exception as e:
                        # Manejo suave de throttling u otros errores del modelo
                        msg = str(e)
                        if "Throttling" in msg or "Too many requests" in msg:
                            friendly = ("Estoy recibiendo muchas solicitudes al modelo ahora mismo. "
                                        "Intentemos de nuevo en unos segundos.")
                            print("Assistant (answer): ", friendly)
                            # No agregamos turno de asistente al historial para no contaminar contexto
                            await asyncio.sleep(1.5)
                            continue
                        else:
                            friendly = f"Ocurrió un error al invocar el modelo: {e}"
                            print("Assistant (answer): ", friendly)
                            # Tampoco añadimos al historial; seguimos el loop
                            continue

                    # --- postproceso normal ---
                    out = await self.process_llm_response(llm_response, messages)

                    if out["mode"] == "answer":
                        print("Assistant (answer): ", out["text"])
                    elif out["mode"] == "tool":
                        print("\nAssistant (tool): ", out["text"])
                    else:
                        print("Assistant (raw): ", out["text"])

                    # agrega la respuesta del asistente al historial
                    messages.append({"role": "assistant", "content": out["text"]})

                except (KeyboardInterrupt, EOFError):
                    logging.info("\nExiting...")
                    break
        finally:
            await self.cleanup_servers()
