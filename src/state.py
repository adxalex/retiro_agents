
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class EventoTraza(TypedDict):
    """Evento de trazabilidad del agente."""

    ts: str
    origen: Literal["supervisor", "tool", "hitl"]
    nombre: str
    args: dict
    status: str
    preview: str


class EstadoGrafo(TypedDict):
    """Estado compartido del agente del Parque del Retiro."""

    # Datos persistentes de la conversación
    thread_id: str
    historial: Annotated[list[AnyMessage], add_messages]
    done: bool

    # Datos del pedido actual
    pedido: str
    notas: dict[str, str]
    respuesta: str
    plan: list[str]
    aprobado: bool | None
    pasos: int
    traza: list[EventoTraza]
