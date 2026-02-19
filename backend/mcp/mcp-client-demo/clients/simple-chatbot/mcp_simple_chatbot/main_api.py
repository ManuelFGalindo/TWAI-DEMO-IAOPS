#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main_api.py — FastAPI HTTP server que expone el MCP Chat Session al frontend de IAOPS.

Corre en puerto 8001 (o configurable via MCP_API_PORT env).

Endpoints:
  GET  /api/ai/aws/status          — health check + servidores activos
  POST /api/ai/aws/chat            — procesa un mensaje, devuelve respuesta
  POST /api/ai/aws/reset           — limpia el historial de conversación
  GET  /api/ai/aws/history         — devuelve el historial de una sesión

Gestión de sesiones: cada session_id tiene su propio historial. Las sesiones
son compartidas; los servidores MCP se inicializan una sola vez (singleton).
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── Añadir el paquete al path ───────────────────────────────────────────────
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from config import Configuration
from llm.client import LLMClient
from orchestration.session import ChatSession
from servers.base import Server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Modelos HTTP ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    # Pista de modo que el frontend puede enviar para condicionar el LLM
    # "auto" | "diagram" | "infrastructure" | "both"
    mode: Optional[str] = "auto"


class ChatResponse(BaseModel):
    mode: str           # "answer" | "tool" | "raw"
    text: str
    diagram_path: Optional[str] = None
    cfn_data: Optional[Dict[str, Any]] = None
    session_id: str


class ResetResponse(BaseModel):
    status: str
    session_id: str


# ─── Estado global (singleton de servidores MCP) ─────────────────────────────

_global_lock = asyncio.Lock()
_global_session: Optional[ChatSession] = None      # servidores MCP compartidos
_histories: Dict[str, List[Dict[str, str]]] = {}   # historial por session_id


async def _get_or_init_mcp_session() -> ChatSession:
    """Inicializa los servidores MCP una sola vez. Thread-safe."""
    global _global_session
    async with _global_lock:
        # Re-inicializar si ningún servidor sigue vivo
        needs_init = (
            _global_session is None
            or not any(s.session for s in _global_session.servers)
        )
        if not needs_init:
            return _global_session

        logger.info("Inicializando servidores MCP...")
        _ = Configuration()

        cfg_path = _HERE / "servers_config.json"
        with open(cfg_path) as f:
            cfg = json.load(f)

        servers = [
            Server(name, conf)
            for name, conf in cfg.get("mcpServers", {}).items()
            if not conf.get("disabled", False)
        ]

        llm_client = LLMClient()
        cs = ChatSession(servers, llm_client)

        alive, errors = [], []
        for s in servers:
            try:
                await s.initialize()
                if s.session:
                    alive.append(s)
                    logger.info(f"  ✅ Servidor '{s.name}' iniciado")
            except Exception as e:
                errors.append((s.name, str(e)))
                logger.warning(f"  ❌ Servidor '{s.name}' falló: {e}")

        if not alive:
            raise RuntimeError(
                "No hay servidores MCP disponibles. "
                + "; ".join(f"{n}: {e}" for n, e in errors)
            )

        cs.servers = alive
        await cs._prewarm_servers()
        _global_session = cs
        logger.info(f"MCP Session lista con {len(alive)} servidor(es).")
        return _global_session


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicio: pre-inicializar para reducir latencia en primer request
    try:
        await _get_or_init_mcp_session()
    except Exception as e:
        logger.warning(f"Pre-init MCP falló (se reintentará en primer request): {e}")
    yield
    # Apagado: limpiar conexiones MCP
    if _global_session:
        await _global_session.cleanup_servers()
        logger.info("MCP Session cerrada.")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="IAOPS MCP API",
    description="Puente HTTP entre el frontend IAOPS y los servidores MCP de AWS",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

MODE_HINTS = {
    "diagram":        "[MODO: Solo genera el diagrama visual, NO crear recursos reales]",
    "infrastructure": "[MODO: Crear/gestionar recursos reales en AWS via CloudFormation API]",
    "both":           "[MODO: Genera DIAGRAMA y también CREA los recursos reales en AWS]",
}


def _get_history(session_id: str) -> List[Dict[str, str]]:
    if session_id not in _histories:
        _histories[session_id] = []
    return _histories[session_id]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/ai/aws/status")
async def status():
    """Health check: devuelve estado de los servidores MCP."""
    if _global_session is None:
        return {"status": "not_initialized", "servers": []}
    servers_info = [
        {
            "name": s.name,
            "alive": s.session is not None,
        }
        for s in _global_session.servers
    ]
    return {
        "status": "ok",
        "servers": servers_info,
        "active_sessions": len(_histories),
    }


@app.post("/api/ai/aws/reset", response_model=ResetResponse)
async def reset_session(session_id: str = "default"):
    """Limpia el historial de conversación de una sesión."""
    _histories[session_id] = []
    return ResetResponse(status="reset", session_id=session_id)


@app.get("/api/ai/aws/history")
async def get_history(session_id: str = "default"):
    """Devuelve el historial de mensajes de una sesión."""
    return {
        "session_id": session_id,
        "messages": _get_history(session_id),
    }


@app.post("/api/ai/aws/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Procesa un mensaje de usuario a través del LLM + MCP servers.
    Devuelve la respuesta del asistente.
    """
    session_id = req.session_id or "default"
    history = _get_history(session_id)

    # Intentar obtener/inicializar los servidores MCP
    try:
        mcp_session = await _get_or_init_mcp_session()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Servidores MCP no disponibles: {e}")

    # Inyectar hint de modo si el frontend lo especificó
    user_content = req.message
    if req.mode and req.mode in MODE_HINTS:
        user_content = f"{MODE_HINTS[req.mode]}\n{req.message}"

    history.append({"role": "user", "content": user_content})

    try:
        llm_response = await mcp_session.llm_client.get_response(history)
        out = await mcp_session.process_llm_response(llm_response, history)
    except Exception as e:
        logger.exception("Error procesando mensaje")
        # No agregar al historial si falló
        history.pop()
        raise HTTPException(status_code=500, detail=str(e))

    response_text = out.get("text", "")
    history.append({"role": "assistant", "content": response_text})

    return ChatResponse(
        mode=out.get("mode", "answer"),
        text=response_text,
        diagram_path=out.get("diagram_path"),
        cfn_data=out.get("cfn_data"),
        session_id=session_id,
    )


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("MCP_API_PORT", "8001"))
    uvicorn.run(
        "main_api:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False,
    )
