"""Lógica de la interfaz Streamlit del agente, sin Streamlit ni grafo."""
import uuid
from typing import Callable

ROL_USUARIO = "usuario"
ROL_AGENTE = "agente"


def nueva_sesion() -> dict:
    """Crea el estado de una conversación nueva."""
    return {
        "thread_id": str(uuid.uuid4()),
        "mensajes": [],
        "ultimo": None,
        "uploader_key": 0,
    }


def _anadir(sesion: dict, rol: str, texto: str, plan: list | None = None) -> None:
    """Añade un mensaje al chat de la sesión."""
    sesion["mensajes"].append({"rol": rol, "texto": texto, "plan": list(plan or [])})


def enviar_turno(
    sesion: dict,
    texto: str,
    mime: str | None,
    datos: bytes | None,
    procesar: Callable[..., dict],
) -> None:
    """Envía un mensaje al agente y añade al chat lo que devuelve."""
    texto = (texto or "").strip()
    if not texto:
        return

    _anadir(sesion, ROL_USUARIO, texto)
    resultado = procesar(texto, sesion["thread_id"], None)

    respuesta = resultado.get("respuesta") or ""
    plan = resultado.get("plan") or []
    if respuesta or plan:
        _anadir(sesion, ROL_AGENTE, respuesta, plan)
