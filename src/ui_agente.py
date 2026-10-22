"""Lógica de la interfaz Streamlit del agente, sin Streamlit ni grafo."""
import uuid


def nueva_sesion() -> dict:
    """Crea el estado de una conversación nueva."""
    return {
        "thread_id": str(uuid.uuid4()),
        "mensajes": [],
        "ultimo": None,
        "uploader_key": 0,
    }
