"""
Hook para el MCP Server de CloudFormation (awslabs.cfn-mcp-server).

Herramientas disponibles:
  - create_resource          → crea un recurso via Cloud Control API
  - get_resource             → describe un recurso existente
  - update_resource          → actualiza un recurso con patch
  - delete_resource          → elimina un recurso
  - list_resources           → lista recursos de un TypeName
  - get_resource_schema_information → devuelve el schema CloudFormation del TypeName
  - get_request_status       → estado de una operación asíncrona
  - create_template          → genera template CFN de recursos listados/creados
"""

import json
import logging
from typing import Any, Dict, Tuple

CFN_TOOLS = {
    "create_resource",
    "get_resource",
    "update_resource",
    "delete_resource",
    "list_resources",
    "get_resource_schema_information",
    "get_request_status",
    "create_template",
}


def is_cfn_tool(tool_name: str) -> bool:
    return tool_name in CFN_TOOLS


def preprocess_cfn_tool(envelope: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Extrae nombre y argumentos del envelope del LLM.
    Aplica coerciones necesarias:
      - DesiredState dict → JSON string (como espera Cloud Control API)
      - PatchDocument dict → JSON string
    """
    tool_name = envelope.get("tool", "")
    args = dict(envelope.get("arguments", {}) or {})

    # Cloud Control API espera DesiredState como string JSON
    if tool_name in {"create_resource", "update_resource"}:
        if "DesiredState" in args and isinstance(args["DesiredState"], dict):
            args["DesiredState"] = json.dumps(args["DesiredState"])

    # PatchDocument también debe ser string JSON (lista de operaciones RFC 6902)
    if tool_name == "update_resource":
        if "PatchDocument" in args and isinstance(args["PatchDocument"], (dict, list)):
            args["PatchDocument"] = json.dumps(args["PatchDocument"])

    return tool_name, args


def postprocess_cfn_result(
    result: Any, tool_name: str
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Procesa el resultado de una herramienta CFN y devuelve
    (éxito: bool, mensaje_markdown: str, datos_raw: dict).
    """
    from utilities.postprocess import extract_text_blob

    raw = extract_text_blob(result) or str(result)
    data: Dict[str, Any] = {}

    if isinstance(raw, str):
        raw = raw.strip()
        try:
            data = json.loads(raw)
        except Exception:
            data = {"raw": raw}

    # ─── Formateo por tipo de operación ───────────────────────────────────────

    if tool_name == "create_resource":
        pe = data.get("ProgressEvent") or {}
        if pe:
            msg = (
                f"**Creación iniciada** ✅\n"
                f"- Tipo: `{pe.get('TypeName', 'N/A')}`\n"
                f"- Identificador: `{pe.get('Identifier', 'pendiente')}`\n"
                f"- Estado: `{pe.get('OperationStatus', 'N/A')}`\n"
                f"- Mensaje: {pe.get('StatusMessage', '') or 'OK'}"
            )
        else:
            msg = (
                f"**Recurso creado.**\n"
                f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)[:500]}\n```"
            )

    elif tool_name == "list_resources":
        items = data.get("ResourceDescriptions") or []
        count = len(items)
        if count == 0:
            msg = "No se encontraron recursos de ese tipo en la región."
        else:
            lines = [f"- `{r.get('Identifier', '?')}`" for r in items[:20]]
            msg = f"**{count} recurso(s) encontrado(s):**\n" + "\n".join(lines)
            if count > 20:
                msg += f"\n… y {count - 20} más."

    elif tool_name == "get_resource":
        rd = data.get("ResourceDescription") or data
        props_str = json.dumps(rd, indent=2, ensure_ascii=False)
        msg = f"**Detalles del recurso:**\n```json\n{props_str[:2000]}\n```"
        if len(props_str) > 2000:
            msg += "\n*(truncado)*"

    elif tool_name in {"update_resource", "delete_resource"}:
        pe = data.get("ProgressEvent") or {}
        op_label = "Actualización" if tool_name == "update_resource" else "Eliminación"
        msg = (
            f"**{op_label} iniciada** ✅\n"
            f"- Tipo: `{pe.get('TypeName', 'N/A')}`\n"
            f"- Identificador: `{pe.get('Identifier', 'N/A')}`\n"
            f"- Estado: `{pe.get('OperationStatus', 'N/A')}`"
        )

    elif tool_name == "get_request_status":
        pe = data.get("ProgressEvent") or {}
        status_emoji = {"SUCCESS": "✅", "FAILED": "❌", "IN_PROGRESS": "⏳"}.get(
            pe.get("OperationStatus", ""), "🔄"
        )
        msg = (
            f"**Estado de la operación:** {status_emoji}\n"
            f"- Operación: `{pe.get('Operation', 'N/A')}`\n"
            f"- Estado: `{pe.get('OperationStatus', 'N/A')}`\n"
            f"- Tipo: `{pe.get('TypeName', 'N/A')}`\n"
            f"- Identificador: `{pe.get('Identifier', 'N/A')}`\n"
            f"- Mensaje: {pe.get('StatusMessage', '') or 'Sin mensaje adicional'}"
        )

    elif tool_name == "create_template":
        tmpl = (
            data.get("TemplateBody")
            or data.get("template")
            or json.dumps(data, indent=2)
        )
        preview = str(tmpl)[:3000]
        msg = f"**Template CloudFormation generado:** 📄\n```yaml\n{preview}\n```"
        if len(str(tmpl)) > 3000:
            msg += "\n*(template truncado para visualización)*"

    elif tool_name == "get_resource_schema_information":
        schema = data.get("Schema") or data
        schema_str = json.dumps(schema, indent=2, ensure_ascii=False)
        msg = f"**Schema del recurso:**\n```json\n{schema_str[:2500]}\n```"
        if len(schema_str) > 2500:
            msg += "\n*(schema truncado)*"

    else:
        # Fallback genérico
        msg = (
            f"**`{tool_name}` ejecutado.**\n"
            f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)[:800]}\n```"
        )

    return True, msg, data
