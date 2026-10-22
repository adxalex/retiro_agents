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


class AprobadorFalso:
    """Doble de aprobar_plan que registra llamadas y devuelve datos fijos."""

    def __init__(self):
        self.llamadas = []
        self.respuesta = {}

    def __call__(self, thread_id, aprobado, comentario=""):
        self.llamadas.append(
            {"thread_id": thread_id, "aprobado": aprobado, "comentario": comentario})
        return resultado(thread_id=thread_id, **self.respuesta)


@pytest.fixture
def procesar_falso():
    return AgenteFalso()


@pytest.fixture
def aprobar_falso():
    return AprobadorFalso()


@pytest.fixture
def sesion_con_plan(sesion, procesar_falso):
    """Sesión cuyo último turno ha dejado un plan pendiente."""
    procesar_falso.respuestas = [
        {"respuesta": "Propuesta", "plan": ["Paso 1"], "pendiente_aprobacion": True}]
    ui_agente.enviar_turno(sesion, "Plan de visita", None, None, procesar_falso)
    return sesion


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


def test_error_se_muestra_como_aviso(sesion, procesar_falso):
    procesar_falso.respuestas = [{"error": "Fallo de la tool."}]

    ui_agente.enviar_turno(sesion, "Hola", None, None, procesar_falso)

    assert [(m["rol"], m["texto"]) for m in sesion["mensajes"]] == [
        (ui_agente.ROL_USUARIO, "Hola"),
        (ui_agente.ROL_AVISO, "Fallo de la tool."),
    ]
    assert sesion["ultimo"]["error"] == "Fallo de la tool."


def test_excepcion_del_agente_se_convierte_en_aviso(sesion):
    def procesar_que_falla(texto, thread_id, imagen=None):
        raise RuntimeError("caída inesperada")

    ui_agente.enviar_turno(sesion, "Hola", None, None, procesar_que_falla)

    assert [(m["rol"], m["texto"]) for m in sesion["mensajes"]] == [
        (ui_agente.ROL_USUARIO, "Hola"),
        (ui_agente.ROL_AVISO, ui_agente.AVISO_ERROR_AGENTE),
    ]
    assert sesion["ultimo"]["error"] == ui_agente.AVISO_ERROR_AGENTE
    assert sesion["ultimo"]["pendiente_aprobacion"] is False
    assert sesion["ultimo"]["done"] is False


def test_error_plan_pendiente_como_aviso(sesion, procesar_falso):
    error = "Hay un plan pendiente de aprobación."
    procesar_falso.respuestas = [
        {"respuesta": "Propuesta", "plan": ["Paso"], "pendiente_aprobacion": True,
         "error": error},
    ]

    ui_agente.enviar_turno(sesion, "Otra cosa", None, None, procesar_falso)

    assert sesion["mensajes"][-1] == {
        "rol": ui_agente.ROL_AVISO, "texto": error, "plan": []}
    assert ui_agente.pendiente(sesion) is True


def test_error_plan_pendiente_no_duplica_respuesta(sesion, procesar_falso):
    error = "Hay un plan pendiente de aprobación."
    procesar_falso.respuestas = [
        {"respuesta": "Propuesta", "plan": ["Paso"], "pendiente_aprobacion": True,
         "error": error},
    ]

    ui_agente.enviar_turno(sesion, "Otra cosa", None, None, procesar_falso)

    assert [(m["rol"], m["texto"]) for m in sesion["mensajes"]] == [
        (ui_agente.ROL_USUARIO, "Otra cosa"),
        (ui_agente.ROL_AVISO, error),
    ]


def test_traza_se_reemplaza(sesion, procesar_falso):
    evento_1 = {"origen": "supervisor", "nombre": "normas"}
    evento_2 = {"origen": "supervisor", "nombre": "entorno"}
    procesar_falso.respuestas = [{"traza": [evento_1]}, {"traza": [evento_2]}]

    ui_agente.enviar_turno(sesion, "P1", None, None, procesar_falso)
    ui_agente.enviar_turno(sesion, "P2", None, None, procesar_falso)

    assert sesion["ultimo"]["traza"] == [evento_2]


def test_chat_bloqueado_con_plan_pendiente(sesion, procesar_falso):
    assert ui_agente.pendiente(sesion) is False

    procesar_falso.respuestas = [
        {"respuesta": "Propuesta", "plan": ["Paso"], "pendiente_aprobacion": True}]
    ui_agente.enviar_turno(sesion, "Plan", None, None, procesar_falso)

    assert ui_agente.pendiente(sesion) is True


def test_estado_solo_desde_banderas(sesion, procesar_falso):
    procesar_falso.respuestas = [
        {"respuesta": "Plan pendiente de aprobación. Plan aprobado.",
         "pendiente_aprobacion": False},
        {"respuesta": "", "plan": ["Paso"], "pendiente_aprobacion": True},
    ]

    ui_agente.enviar_turno(sesion, "P1", None, None, procesar_falso)
    assert ui_agente.pendiente(sesion) is False

    ui_agente.enviar_turno(sesion, "P2", None, None, procesar_falso)
    assert ui_agente.pendiente(sesion) is True


def test_aprobar_llama_con_true_y_comentario(sesion_con_plan, aprobar_falso):
    ui_agente.decidir(sesion_con_plan, True, "  Empezar por el estanque ", aprobar_falso)

    assert aprobar_falso.llamadas == [{
        "thread_id": sesion_con_plan["thread_id"],
        "aprobado": True,
        "comentario": "Empezar por el estanque",
    }]


def test_rechazar_llama_con_false_y_comentario(sesion_con_plan, aprobar_falso):
    ui_agente.decidir(sesion_con_plan, False, "", aprobar_falso)

    assert aprobar_falso.llamadas == [{
        "thread_id": sesion_con_plan["thread_id"],
        "aprobado": False,
        "comentario": "",
    }]


def test_aprobacion_con_done_muestra_plan_aprobado(sesion_con_plan, aprobar_falso):
    aprobar_falso.respuesta = {"done": True}

    ui_agente.decidir(sesion_con_plan, True, "", aprobar_falso)

    assert sesion_con_plan["mensajes"][-1] == {
        "rol": ui_agente.ROL_SISTEMA,
        "texto": ui_agente.MENSAJE_PLAN_APROBADO,
        "plan": [],
    }


def test_rechazo_muestra_mensaje(sesion_con_plan, aprobar_falso):
    ui_agente.decidir(sesion_con_plan, False, "", aprobar_falso)

    assert sesion_con_plan["mensajes"][-1] == {
        "rol": ui_agente.ROL_SISTEMA,
        "texto": ui_agente.MENSAJE_PLAN_RECHAZADO,
        "plan": [],
    }


def test_decision_conserva_mensajes(sesion_con_plan, aprobar_falso):
    previos = [dict(m) for m in sesion_con_plan["mensajes"]]
    aprobar_falso.respuesta = {"done": True}

    ui_agente.decidir(sesion_con_plan, True, "", aprobar_falso)

    assert sesion_con_plan["mensajes"][:len(previos)] == previos
    assert len(sesion_con_plan["mensajes"]) == len(previos) + 1


@pytest.mark.parametrize("aprobado", [True, False])
def test_decision_desbloquea_chat(sesion_con_plan, aprobar_falso, aprobado):
    aprobar_falso.respuesta = {"done": aprobado, "pendiente_aprobacion": False}

    ui_agente.decidir(sesion_con_plan, aprobado, "", aprobar_falso)

    assert ui_agente.pendiente(sesion_con_plan) is False


def test_aprobacion_con_error_no_muestra_aprobado(sesion_con_plan, aprobar_falso):
    aprobar_falso.respuesta = {"done": True, "error": "Fallo al aplicar."}

    ui_agente.decidir(sesion_con_plan, True, "", aprobar_falso)

    textos = [m["texto"] for m in sesion_con_plan["mensajes"]]
    assert ui_agente.MENSAJE_PLAN_APROBADO not in textos
    assert sesion_con_plan["mensajes"][-1]["rol"] == ui_agente.ROL_AVISO
    assert sesion_con_plan["mensajes"][-1]["texto"] == "Fallo al aplicar."


def test_aprobacion_sin_done_no_muestra_aprobado(sesion_con_plan, aprobar_falso):
    aprobar_falso.respuesta = {"done": False}

    ui_agente.decidir(sesion_con_plan, True, "", aprobar_falso)

    textos = [m["texto"] for m in sesion_con_plan["mensajes"]]
    assert ui_agente.MENSAJE_PLAN_APROBADO not in textos
    assert sesion_con_plan["mensajes"][-1] == {
        "rol": ui_agente.ROL_AVISO,
        "texto": ui_agente.AVISO_PLAN_NO_COMPLETADO,
        "plan": [],
    }


def test_turno_pendiente_no_llama_a_aprobar(
        sesion, procesar_falso, aprobar_falso):
    # Un turno que deja el plan pendiente no decide por su cuenta.
    procesar_falso.respuestas = [
        {"respuesta": "Propuesta", "plan": ["Paso"], "pendiente_aprobacion": True}]
    ui_agente.enviar_turno(sesion, "Plan", None, None, procesar_falso)
    assert aprobar_falso.llamadas == []

    # Sin plan pendiente, decidir no llama al agente ni cambia el chat.
    otra = ui_agente.nueva_sesion()
    ui_agente.decidir(otra, True, "", aprobar_falso)
    assert aprobar_falso.llamadas == []
    assert otra["mensajes"] == []
    assert otra["ultimo"] is None


def test_mensajes_de_decision_textos_exactos():
    assert ui_agente.MENSAJE_PLAN_APROBADO == "Plan aprobado"
    assert ui_agente.MENSAJE_PLAN_RECHAZADO == (
        "Plan rechazado, puedes hacer otra petición")


def test_decision_usa_mismo_thread_id(sesion_con_plan, procesar_falso, aprobar_falso):
    ui_agente.decidir(sesion_con_plan, False, "", aprobar_falso)

    assert procesar_falso.llamadas[0]["thread_id"] == sesion_con_plan["thread_id"]
    assert aprobar_falso.llamadas[0]["thread_id"] == sesion_con_plan["thread_id"]
