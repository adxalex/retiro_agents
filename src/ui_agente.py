"""Lógica de la interfaz Streamlit del agente, sin Streamlit ni grafo."""
import os
import re
import uuid
from typing import Callable

import config

ROL_USUARIO = "usuario"
ROL_AGENTE = "agente"
ROL_AVISO = "aviso"
ROL_SISTEMA = "sistema"

AVISO_ERROR_AGENTE = (
    "El agente no ha podido procesar la petición. Inténtalo de nuevo."
)
AVISO_PLAN_NO_COMPLETADO = "El plan no se ha completado."
AVISO_PLAN_PENDIENTE = "Hay un plan pendiente: apruébalo o recházalo para continuar"
MENSAJE_PLAN_APROBADO = "Plan aprobado"
MENSAJE_PLAN_RECHAZADO = "Plan rechazado, puedes hacer otra petición"

AVISO_IMAGEN_FORMATO = (
    "Formato de imagen no admitido: solo PNG o JPG. El mensaje no se ha enviado."
)
AVISO_IMAGEN_TAMANO = (
    f"La imagen supera {config.IMAGEN_MAX_BYTES // (1024 * 1024)} MB. "
    "El mensaje no se ha enviado."
)

CAMPOS_TRAZA = ("ts", "origen", "nombre", "status", "preview")

# Secretos que nunca deben llegar a la pantalla.
MASCARA = "***"
VARIABLES_SECRETAS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "AEMET_API_KEY")
PATRON_CLAVE_GOOGLE = re.compile(r"AIza[0-9A-Za-z_-]{35}")

# Primeros bytes que identifican cada formato admitido.
FIRMAS_IMAGEN = {
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
}


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


def _resultado_vacio(
    error: str | None = None, pendiente_aprobacion: bool = False
) -> dict:
    """Resultado con las claves del contrato y valores neutros."""
    return {
        "thread_id": "",
        "respuesta": "",
        "plan": [],
        "pendiente_aprobacion": pendiente_aprobacion,
        "done": False,
        "traza": [],
        "error": error,
    }


def llamar_seguro(
    funcion: Callable[..., dict], *args, pendiente_previo: bool = False
) -> dict:
    """Llama al agente y convierte cualquier fallo en un resultado con error.

    Si el agente no devuelve un dict, se conserva el último estado de
    aprobación conocido en lugar de suponer uno nuevo.
    """
    try:
        resultado = funcion(*args)
    except Exception:
        return _resultado_vacio(AVISO_ERROR_AGENTE, pendiente_previo)
    if not isinstance(resultado, dict):
        return _resultado_vacio(AVISO_ERROR_AGENTE, pendiente_previo)
    completo = _resultado_vacio()
    completo.update(resultado)
    return completo


def ocultar_secretos(texto):
    """Enmascara claves de API conocidas; lo que no es texto se devuelve igual."""
    if not isinstance(texto, str):
        return texto
    for variable in VARIABLES_SECRETAS:
        valor = os.environ.get(variable)
        if valor:
            texto = texto.replace(valor, MASCARA)
    return PATRON_CLAVE_GOOGLE.sub(MASCARA, texto)


def _evento_sin_secretos(evento: dict) -> dict:
    """Copia del evento con preview y comentario enmascarados."""
    limpio = dict(evento)
    if "preview" in evento:
        limpio["preview"] = ocultar_secretos(evento["preview"])
    args = evento.get("args")
    if isinstance(args, dict) and "comentario" in args:
        limpio["args"] = {**args, "comentario": ocultar_secretos(args["comentario"])}
    return limpio


def registrar(sesion: dict, resultado: dict) -> dict:
    """Guarda el último resultado del agente, sin secretos y sustituyendo al anterior."""
    limpio = dict(resultado)
    limpio["respuesta"] = ocultar_secretos(resultado["respuesta"])
    limpio["error"] = ocultar_secretos(resultado["error"])
    limpio["plan"] = [ocultar_secretos(paso) for paso in resultado["plan"] or []]
    limpio["traza"] = [
        _evento_sin_secretos(e) if isinstance(e, dict) else e
        for e in resultado["traza"] or []
    ]
    sesion["ultimo"] = limpio
    return limpio


def pendiente(sesion: dict) -> bool:
    """Indica si el agente tiene un plan pendiente de decisión."""
    ultimo = sesion.get("ultimo")
    return bool(ultimo and ultimo.get("pendiente_aprobacion"))


def validar_imagen(
    mime: str | None, datos: bytes | None
) -> tuple[dict | None, str | None]:
    """Comprueba formato y tamaño de la imagen adjunta.

    Devuelve (imagen, aviso): la imagen en el formato del contrato si es
    válida, o None y el aviso que se muestra si no lo es.
    """
    if datos is None:
        return None, None
    firma = FIRMAS_IMAGEN.get(mime) if mime in config.IMAGEN_MIME_PERMITIDOS else None
    if firma is None or not datos.startswith(firma):
        return None, AVISO_IMAGEN_FORMATO
    if len(datos) > config.IMAGEN_MAX_BYTES:
        return None, AVISO_IMAGEN_TAMANO
    return {"bytes": datos, "mime": mime}, None


def filas_traza(traza: list) -> list[dict]:
    """Reduce cada evento de traza a los campos que muestra el panel."""
    return [
        {campo: evento.get(campo) or "" for campo in CAMPOS_TRAZA}
        for evento in traza or []
    ]


def comentario_hitl(traza: list) -> str | None:
    """Comentario del último evento HITL de la traza, si no está vacío."""
    eventos_hitl = [e for e in traza or [] if e.get("origen") == "hitl"]
    if not eventos_hitl:
        return None
    args = eventos_hitl[-1].get("args")
    if not isinstance(args, dict):
        return None
    comentario = (args.get("comentario") or "").strip()
    return comentario or None


def estado_depuracion(sesion: dict) -> dict:
    """Datos del panel de depuración a partir del último resultado."""
    ultimo = sesion.get("ultimo") or {}
    traza = ultimo.get("traza") or []
    return {
        "thread_id": sesion["thread_id"],
        "pendiente_aprobacion": bool(ultimo.get("pendiente_aprobacion")),
        "done": bool(ultimo.get("done")),
        "filas": filas_traza(traza),
        "comentario": comentario_hitl(traza),
    }


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

    imagen, aviso = validar_imagen(mime, datos)
    if aviso:
        _anadir(sesion, ROL_AVISO, aviso)
        return

    _anadir(sesion, ROL_USUARIO, texto)
    resultado = llamar_seguro(
        procesar, texto, sesion["thread_id"], imagen,
        pendiente_previo=pendiente(sesion))
    resultado = registrar(sesion, resultado)
    if imagen:
        # Una clave nueva vacía el selector: la imagen no se reenvía.
        sesion["uploader_key"] += 1

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
        aprobar, sesion["thread_id"], aprobado, (comentario or "").strip(),
        pendiente_previo=pendiente(sesion))
    resultado = registrar(sesion, resultado)

    if resultado["error"]:
        _anadir(sesion, ROL_AVISO, resultado["error"])
    elif aprobado and resultado["done"]:
        _anadir(sesion, ROL_SISTEMA, MENSAJE_PLAN_APROBADO)
    elif aprobado:
        _anadir(sesion, ROL_AVISO, AVISO_PLAN_NO_COMPLETADO)
    else:
        _anadir(sesion, ROL_SISTEMA, MENSAJE_PLAN_RECHAZADO)
