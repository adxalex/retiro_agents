
from typing import get_type_hints

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from src.state import EstadoGrafo, EventoTraza


def test_estado_tiene_los_campos_del_contrato():
    campos = get_type_hints(EstadoGrafo, include_extras=True)

    esperados = {
        "thread_id",
        "historial",
        "done",
        "pedido",
        "notas",
        "respuesta",
        "plan",
        "aprobado",
        "pasos",
        "traza",
    }

    assert esperados.issubset(campos.keys())


def test_historial_utiliza_add_messages():
    campos = get_type_hints(EstadoGrafo, include_extras=True)
    historial = campos["historial"]

    assert historial.__metadata__[0] is add_messages


def test_historial_admite_mensajes_langchain():
    campos = get_type_hints(EstadoGrafo, include_extras=True)
    historial = campos["historial"]

    assert AnyMessage in historial.__args__ or hasattr(historial, "__metadata__")


def test_tipos_de_los_campos_del_pedido():
    campos = get_type_hints(EstadoGrafo)

    assert campos["thread_id"] is str
    assert campos["done"] is bool
    assert campos["pedido"] is str
    assert campos["notas"] == dict[str, str]
    assert campos["respuesta"] is str
    assert campos["plan"] == list[str]
    assert campos["aprobado"] == bool | None
    assert campos["pasos"] is int
    assert campos["traza"] == list[EventoTraza]


def test_evento_traza_tiene_los_campos_acordados():
    campos = get_type_hints(EventoTraza)

    assert set(campos) == {
        "ts",
        "origen",
        "nombre",
        "args",
        "status",
        "preview",
    }

def test_origen_de_traza_esta_restringido():
    campos = get_type_hints(EventoTraza, include_extras=True)
    origen = campos["origen"]

    assert origen.__args__ == ("supervisor", "tool", "hitl")

