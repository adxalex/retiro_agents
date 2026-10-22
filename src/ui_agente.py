"""Lógica de la interfaz Streamlit del agente, sin Streamlit ni grafo."""
import uuid
from typing import Callable

ROL_USUARIO = "usuario"
ROL_AGENTE = "agente"
ROL_AVISO = "aviso"
ROL_SISTEMA = "sistema"

AVISO_ERROR_AGENTE = (
    "El agente no ha podido procesar la petición. Inténtalo de nuevo."
)
AVISO_PLAN_NO_COMPLETADO = "El plan no se ha completado."
MENSAJE_PLAN_APROBADO = "Plan aprobado"
MENSAJE_PLAN_RECHAZADO = "Plan rechazado, puedes hacer otra petición"


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


def _resultado_vacio(error: str | None = None) -> dict:
    """Resultado con las claves del contrato y valores neutros."""
    return {
        "thread_id": "",
        "respuesta": "",
        "plan": [],
        "pendiente_aprobacion": False,
        "done": False,
        "traza": [],
        "error": error,
    }


def llamar_seguro(funcion: Callable[..., dict], *args) -> dict:
    """Llama al agente y convierte cualquier fallo en un resultado con error."""
    try:
        resultado = funcion(*args)
    except Exception:
        return _resultado_vacio(AVISO_ERROR_AGENTE)
    if not isinstance(resultado, dict):
        return _resultado_vacio(AVISO_ERROR_AGENTE)
    completo = _resultado_vacio()
    completo.update(resultado)
    return completo


def registrar(sesion: dict, resultado: dict) -> None:
    """Guarda el último resultado del agente, sustituyendo al anterior."""
    sesion["ultimo"] = resultado


def pendiente(sesion: dict) -> bool:
    """Indica si el agente tiene un plan pendiente de decisión."""
    ultimo = sesion.get("ultimo")
    return bool(ultimo and ultimo.get("pendiente_aprobacion"))


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
    resultado = llamar_seguro(procesar, texto, sesion["thread_id"], None)
    registrar(sesion, resultado)

    respuesta = resultado["respuesta"] or ""
    plan = resultado["plan"] or []
    # Con plan pendiente, el núcleo devuelve el pedido anterior: no se repite.
    repetido = bool(resultado["error"] and resultado["pendiente_aprobacion"])
    if (respuesta or plan) and not repetido:
        _anadir(sesion, ROL_AGENTE, respuesta, plan)
    if resultado["error"]:
        _anadir(sesion, ROL_AVISO, resultado["error"])


def decidir(
    sesion: dict,
    aprobado: bool,
    comentario: str,
    aprobar: Callable[..., dict],
) -> None:
    """Envía la decisión humana sobre el plan pendiente y la refleja en el chat."""
    if not pendiente(sesion):
        return

    resultado = llamar_seguro(
        aprobar, sesion["thread_id"], aprobado, (comentario or "").strip())
    registrar(sesion, resultado)

    if resultado["error"]:
        _anadir(sesion, ROL_AVISO, resultado["error"])
    elif aprobado and resultado["done"]:
        _anadir(sesion, ROL_SISTEMA, MENSAJE_PLAN_APROBADO)
    elif aprobado:
        _anadir(sesion, ROL_AVISO, AVISO_PLAN_NO_COMPLETADO)
    else:
        _anadir(sesion, ROL_SISTEMA, MENSAJE_PLAN_RECHAZADO)
