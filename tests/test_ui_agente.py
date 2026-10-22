"""Tests de la lógica de la interfaz Streamlit del agente (sin API)."""
import ast
import uuid
from pathlib import Path

import pytest

import config
from src import ui_agente

RUTA_UI_AGENTE = Path(__file__).resolve().parents[1] / "src" / "ui_agente.py"


def resultado(**campos) -> dict:
    """Resultado con las claves del contrato público del agente."""
    base = {
        "thread_id": "",
        "respuesta": "",
        "plan": [],
        "pendiente_aprobacion": False,
        "done": False,
        "traza": [],
        "error": None,
    }
    base.update(campos)
    return base


class AgenteFalso:
    """Doble de procesar_turno que registra llamadas y devuelve datos fijos."""

    def __init__(self):
        self.llamadas = []
        self.respuestas = []

    def __call__(self, texto, thread_id, imagen=None):
        self.llamadas.append(
            {"texto": texto, "thread_id": thread_id, "imagen": imagen})
        datos = self.respuestas.pop(0) if self.respuestas else {}
        return resultado(thread_id=thread_id, **datos)


@pytest.fixture
def procesar_falso():
    return AgenteFalso()


@pytest.fixture
def sesion():
    return ui_agente.nueva_sesion()


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


def test_mensajes_en_orden_cronologico(sesion, procesar_falso):
    procesar_falso.respuestas = [{"respuesta": "R1"}, {"respuesta": "R2"}]

    ui_agente.enviar_turno(sesion, "P1", None, None, procesar_falso)
    ui_agente.enviar_turno(sesion, "P2", None, None, procesar_falso)

    assert [(m["rol"], m["texto"]) for m in sesion["mensajes"]] == [
        (ui_agente.ROL_USUARIO, "P1"),
        (ui_agente.ROL_AGENTE, "R1"),
        (ui_agente.ROL_USUARIO, "P2"),
        (ui_agente.ROL_AGENTE, "R2"),
    ]


def test_enviar_turno_llama_con_thread_id_activo(sesion, procesar_falso):
    ui_agente.enviar_turno(sesion, "Hola", None, None, procesar_falso)
    ui_agente.enviar_turno(sesion, "Otra", None, None, procesar_falso)

    assert [ll["thread_id"] for ll in procesar_falso.llamadas] == [
        sesion["thread_id"], sesion["thread_id"]]
    assert procesar_falso.llamadas[0]["texto"] == "Hola"
    assert procesar_falso.llamadas[0]["imagen"] is None


@pytest.mark.parametrize("texto", ["", "   ", "\n\t"])
def test_texto_vacio_no_llama_al_agente(sesion, procesar_falso, texto):
    ui_agente.enviar_turno(sesion, texto, None, None, procesar_falso)

    assert procesar_falso.llamadas == []
    assert sesion["mensajes"] == []


def test_respuesta_no_vacia_se_anade(sesion, procesar_falso):
    procesar_falso.respuestas = [{"respuesta": "El parque abre a las 6:00."}]

    ui_agente.enviar_turno(sesion, "¿Horario?", None, None, procesar_falso)

    ultimo = sesion["mensajes"][-1]
    assert ultimo["rol"] == ui_agente.ROL_AGENTE
    assert ultimo["texto"] == "El parque abre a las 6:00."


def test_respuesta_y_plan_vacios_no_anaden_mensaje(sesion, procesar_falso):
    ui_agente.enviar_turno(sesion, "Hola", None, None, procesar_falso)

    assert [m["rol"] for m in sesion["mensajes"]] == [ui_agente.ROL_USUARIO]


def test_plan_se_guarda_como_lista(sesion, procesar_falso):
    plan = ["Entrar por la Puerta de Alcalá", "Ver el Palacio de Cristal"]
    procesar_falso.respuestas = [{"respuesta": "Propuesta:", "plan": plan}]

    ui_agente.enviar_turno(sesion, "Plan de visita", None, None, procesar_falso)

    ultimo = sesion["mensajes"][-1]
    assert ultimo["rol"] == ui_agente.ROL_AGENTE
    assert ultimo["plan"] == plan
