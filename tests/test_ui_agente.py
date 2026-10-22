"""Tests de la lógica de la interfaz Streamlit del agente (sin API)."""
import ast
import uuid
from pathlib import Path

import config
from src import ui_agente

RUTA_UI_AGENTE = Path(__file__).resolve().parents[1] / "src" / "ui_agente.py"


def test_config_limites_imagen():
    assert config.IMAGEN_MAX_BYTES == 5 * 1024 * 1024
    assert config.IMAGEN_MIME_PERMITIDOS == ("image/png", "image/jpeg")


def test_nueva_sesion_genera_thread_id_uuid4():
    sesion = ui_agente.nueva_sesion()

    assert uuid.UUID(sesion["thread_id"]).version == 4
    assert sesion["mensajes"] == []
    assert sesion["ultimo"] is None
    assert sesion["uploader_key"] == 0


def test_ui_agente_no_importa_streamlit_ni_nucleo():
    arbol = ast.parse(RUTA_UI_AGENTE.read_text(encoding="utf-8"))
    modulos = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            modulos.add(nodo.module or "")
            modulos.update(f"{nodo.module}.{alias.name}" for alias in nodo.names)

    prohibidos = ("streamlit", "src.agent", "src.graph", "langgraph")
    assert not any(m.startswith(prohibidos) for m in modulos)
