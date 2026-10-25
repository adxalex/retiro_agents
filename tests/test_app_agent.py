"""Tests de la app Streamlit del agente (sin API)."""
import ast
import uuid
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import src.agent
from src import ui_agente

RAIZ = Path(__file__).resolve().parents[1]
RUTA_APP = RAIZ / "app_agent.py"
RUTA_UI = RAIZ / "src" / "ui_agente.py"

FUNCIONES_AGENTE = {"procesar_turno", "aprobar_plan"}
MODULOS_PROHIBIDOS = {"src.graph", "src.tools", "src.state"}


def _arbol(ruta: Path) -> ast.Module:
    return ast.parse(ruta.read_text(encoding="utf-8"))


def _importados(arbol: ast.Module) -> set[str]:
    """Nombres completos importados: módulos y 'modulo.nombre'."""
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            nombres.add(modulo)
            nombres.update(f"{modulo}.{alias.name}" for alias in nodo.names)
    return nombres


def _es_prohibido(nombre: str) -> bool:
    raiz = nombre.split(".")[0]
    return (
        raiz in {"langgraph", "google"}
        or raiz.startswith("langchain")
        or any(nombre == m or nombre.startswith(m + ".") for m in MODULOS_PROHIBIDOS)
    )


def test_capas_sin_logica_de_grafo():
    for ruta in (RUTA_APP, RUTA_UI):
        importados = _importados(_arbol(ruta))
        assert not [n for n in importados if _es_prohibido(n)], ruta.name

    # La lógica pura no conoce al agente: lo recibe inyectado.
    assert not [n for n in _importados(_arbol(RUTA_UI)) if n.startswith("src.agent")]

    # La app solo usa las dos funciones públicas, por atributo.
    arbol_app = _arbol(RUTA_APP)
    importados_app = _importados(arbol_app)
    assert "src.agent" in importados_app
    assert not [n for n in importados_app
                if n.startswith("src.agent.") and n.split(".")[-1] not in FUNCIONES_AGENTE]
    usos = {
        nodo.attr for nodo in ast.walk(arbol_app)
        if isinstance(nodo, ast.Attribute)
        and isinstance(nodo.value, ast.Name) and nodo.value.id == "agent"
    }
    assert usos == FUNCIONES_AGENTE

    # La app no lee variables de entorno ni .env.
    assert not [n for n in importados_app if n.split(".")[0] in {"os", "dotenv"}]
    nombres_app = {
        nodo.attr if isinstance(nodo, ast.Attribute) else nodo.id
        for nodo in ast.walk(arbol_app)
        if isinstance(nodo, (ast.Attribute, ast.Name))
    }
    assert not nombres_app & {"environ", "getenv", "load_dotenv"}


# --- App completa con AppTest y el agente sustituido por dobles ---

PLAN = ["Entrar por la Puerta de Alcalá", "Ver el Palacio de Cristal"]


def resultado(**campos) -> dict:
    """Resultado con las claves del contrato público del agente."""
    base = {"thread_id": "", "respuesta": "", "plan": [],
            "pendiente_aprobacion": False, "done": False, "traza": [],
            "error": None}
    base.update(campos)
    return base


class AgenteDoble:
    """Sustituye a las dos funciones públicas del agente y cuenta llamadas."""

    def __init__(self):
        self.turnos = []
        self.aprobaciones = []
        self.respuestas_turno = []
        self.respuesta_aprobar = {}

    def procesar_turno(self, texto, thread_id, imagen=None):
        self.turnos.append((texto, thread_id, imagen))
        datos = self.respuestas_turno.pop(0) if self.respuestas_turno else {}
        return resultado(thread_id=thread_id, **datos)

    def aprobar_plan(self, thread_id, aprobado, comentario=""):
        self.aprobaciones.append((thread_id, aprobado, comentario))
        return resultado(thread_id=thread_id, **self.respuesta_aprobar)


@pytest.fixture
def agente(monkeypatch):
    doble = AgenteDoble()
    monkeypatch.setattr(src.agent, "procesar_turno", doble.procesar_turno)
    monkeypatch.setattr(src.agent, "aprobar_plan", doble.aprobar_plan)
    return doble


@pytest.fixture
def app(agente):
    return AppTest.from_file(str(RUTA_APP), default_timeout=30).run()


def _thread_id(at: AppTest) -> str:
    return at.session_state["agente"]["thread_id"]


def _enviar(at: AppTest, texto: str) -> AppTest:
    return at.chat_input(key="chat").set_value(texto).run()


def _con_plan(at: AppTest, agente: AgenteDoble) -> AppTest:
    """Deja la app con un plan pendiente de aprobación."""
    agente.respuestas_turno.append({
        "respuesta": "Propuesta de visita", "plan": PLAN,
        "pendiente_aprobacion": True,
        "traza": [{"ts": "t", "origen": "hitl", "nombre": "pausa", "args": {},
                   "status": "pending", "preview": "Plan pendiente"}],
    })
    return _enviar(at, "Quiero un plan")


def _textos_depuracion(at: AppTest) -> str:
    return " ".join(m.value for m in at.expander[0].markdown)


def test_app_arranca_con_thread_id(app):
    assert not app.exception
    thread_id = _thread_id(app)
    assert uuid.UUID(thread_id).version == 4
    assert thread_id in _textos_depuracion(app)


def test_app_chat_y_respuesta(app, agente):
    agente.respuestas_turno = [{"respuesta": "R1"}, {"respuesta": "R2"}]

    _enviar(app, "Hola")
    _enviar(app, "Otra pregunta")

    assert not app.exception
    thread_id = _thread_id(app)
    assert agente.turnos == [("Hola", thread_id, None),
                             ("Otra pregunta", thread_id, None)]
    assert [m.markdown[0].value for m in app.chat_message] == [
        "Hola", "R1", "Otra pregunta", "R2"]


def test_app_plan_pendiente_bloquea_chat_y_avisa(app, agente):
    assert app.chat_input(key="chat").disabled is False

    _con_plan(app, agente)

    assert app.chat_input(key="chat").disabled is True
    assert ui_agente.AVISO_PLAN_PENDIENTE in [w.value for w in app.warning]


def test_app_botones_habilitados_solo_con_plan(app, agente):
    assert app.button(key="aprobar").disabled is True
    assert app.button(key="rechazar").disabled is True

    _con_plan(app, agente)

    assert app.button(key="aprobar").disabled is False
    assert app.button(key="rechazar").disabled is False
    assert app.text_area(key="comentario_0").disabled is False


def test_app_sin_aprobacion_automatica(app, agente):
    _con_plan(app, agente)
    app.run()
    app.run()

    assert agente.aprobaciones == []
    assert app.chat_input(key="chat").disabled is True


def _comprobar_decision(app, agente, boton, aprobado, mensaje, respuesta):
    _con_plan(app, agente)
    agente.respuesta_aprobar = respuesta

    app.text_area(key="comentario_0").input("Prefiero el estanque")
    app.button(key=boton).click().run()

    assert not app.exception
    assert agente.aprobaciones == [(_thread_id(app), aprobado, "Prefiero el estanque")]
    assert mensaje in [i.value for i in app.info]
    assert app.chat_input(key="chat").disabled is False
    assert app.button(key="aprobar").disabled is True
    # El campo de comentario vuelve vacío.
    assert app.text_area(key="comentario_1").value == ""


def test_app_aprobar_desde_sidebar(app, agente):
    _comprobar_decision(app, agente, "aprobar", True, ui_agente.MENSAJE_PLAN_APROBADO,
                        {"done": True, "pendiente_aprobacion": False})


def test_app_rechazar_desde_sidebar(app, agente):
    _comprobar_decision(app, agente, "rechazar", False, ui_agente.MENSAJE_PLAN_RECHAZADO,
                        {"done": False, "pendiente_aprobacion": False})


def test_app_nueva_conversacion_siempre_visible(app, agente):
    assert app.button(key="nueva_conversacion").disabled is False
    primero = _thread_id(app)

    _con_plan(app, agente)
    assert app.button(key="nueva_conversacion").disabled is False

    app.button(key="nueva_conversacion").click().run()

    assert not app.exception
    assert _thread_id(app) != primero
    assert len(app.chat_message) == 0
    assert app.chat_input(key="chat").disabled is False
    assert agente.aprobaciones == []


def test_app_selector_un_solo_archivo_png_jpg(app):
    selector = app.get("file_uploader")[0]

    assert selector.proto.multiple_files is False
    assert list(selector.proto.type) == [".png", ".jpg", ".jpeg"]


def test_app_plan_se_pinta_como_lista(app, agente):
    _con_plan(app, agente)

    textos = [m.value for m in app.chat_message[1].markdown]
    assert textos == ["Propuesta de visita",
                      "1. Entrar por la Puerta de Alcalá\n2. Ver el Palacio de Cristal"]


def test_app_traza_en_panel(app, agente):
    agente.respuestas_turno.append({"respuesta": "R", "traza": [
        {"ts": "t1", "origen": "supervisor", "nombre": "entorno", "args": {"x": 1},
         "status": "ok", "preview": "ruta"},
        {"ts": "t2", "origen": "tool", "nombre": "hora_actual", "args": {},
         "status": "ok", "preview": "10:00"},
    ]})

    _enviar(app, "¿Qué hora es?")

    tabla = app.expander[0].dataframe[0].value
    assert list(tabla.columns) == ["ts", "origen", "nombre", "status", "preview"]
    assert list(tabla["nombre"]) == ["entorno", "hora_actual"]


@pytest.mark.parametrize("comentario, esperado", [
    ("Prefiero el estanque", ["**Comentario de la decisión:** Prefiero el estanque"]),
    ("", []),
], ids=["con_comentario", "sin_comentario"])
def test_app_comentario_en_panel(app, agente, comentario, esperado):
    _con_plan(app, agente)
    agente.respuesta_aprobar = {"traza": [
        {"ts": "t3", "origen": "hitl", "nombre": "rechazar",
         "args": {"comentario": comentario}, "status": "ok", "preview": "rechazado"}]}

    app.text_area(key="comentario_0").input(comentario)
    app.button(key="rechazar").click().run()

    lineas = [m.value for m in app.expander[0].markdown if "Comentario" in m.value]
    assert lineas == esperado


def test_app_nueva_conversacion_vacia_comentario(app, agente):
    _con_plan(app, agente)
    app.text_area(key="comentario_0").input("borrador").run()

    app.button(key="nueva_conversacion").click().run()

    n = app.session_state["comentario_n"]
    assert app.text_area(key=f"comentario_{n}").value == ""


def test_app_peticion_tras_rechazo_mismo_hilo(app, agente):
    _con_plan(app, agente)
    hilo = _thread_id(app)
    app.button(key="rechazar").click().run()

    agente.respuestas_turno.append({"respuesta": "Respuesta tras rechazo"})
    _enviar(app, "Otra cosa")

    assert agente.turnos[-1] == ("Otra cosa", hilo, None)
    assert app.chat_message[-1].markdown[0].value == "Respuesta tras rechazo"


def test_app_expander_depuracion(app, agente):
    assert [e.label for e in app.expander] == ["Depuración"]
    assert "**pendiente_aprobacion:** `False`" in _textos_depuracion(app)

    _con_plan(app, agente)
    assert "**pendiente_aprobacion:** `True`" in _textos_depuracion(app)
    assert "**done:** `False`" in _textos_depuracion(app)

    agente.respuesta_aprobar = {"done": True, "pendiente_aprobacion": False}
    app.button(key="aprobar").click().run()
    assert "**pendiente_aprobacion:** `False`" in _textos_depuracion(app)
    assert "**done:** `True`" in _textos_depuracion(app)
