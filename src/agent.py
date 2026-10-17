
"""Interfaz pública del agente del Parque del Retiro."""

from typing import Any

from langchain_core.messages import HumanMessage

from src.graph import build_graph


# Una única instancia para conservar el checkpointer entre llamadas.
_grafo = build_graph()


def _config(thread_id: str) -> dict:
    """Configuración de persistencia de una conversación."""
    return {"configurable": {"thread_id": thread_id}}


def _respuesta_publica(
    thread_id: str,
    estado: dict,
    pendiente_aprobacion: bool = False,
    error: str | None = None,
) -> dict:
    """Convierte el estado interno al contrato público del agente."""
    return {
        "thread_id": thread_id,
        "respuesta": estado.get("respuesta", "") or "",
        "plan": estado.get("plan", []) or [],
        "pendiente_aprobacion": pendiente_aprobacion,
        "done": bool(estado.get("done", False)),
        "traza": estado.get("traza", []) or [],
        "error": error,
    }


def _estado_actual(config: dict) -> dict:
    """Obtiene el estado guardado para una conversación."""
    snapshot = _grafo.get_state(config)
    return dict(snapshot.values or {})


def _hay_plan_pendiente(config: dict) -> bool:
    """Comprueba si el grafo está pausado antes de aplicar el plan."""
    snapshot = _grafo.get_state(config)
    return "aplicar" in (snapshot.next or ())


def procesar_turno(
    texto: str,
    thread_id: str,
    imagen: dict | None = None,
) -> dict:
    """Procesa una consulta y devuelve la respuesta según el contrato público."""

    try:
        if not isinstance(texto, str) or not texto.strip():
            return _respuesta_publica(
                thread_id,
                {},
                error="La consulta no puede estar vacía.",
            )
        
        config = _config(thread_id)

        if not isinstance(thread_id, str) or not thread_id.strip():
            return _respuesta_publica(
                thread_id,
                {},
                error="El thread_id debe ser una cadena no vacía.",
            )

        if _hay_plan_pendiente(config):
            return _respuesta_publica(
                thread_id,
                _estado_actual(config),
                pendiente_aprobacion=True,
                error="Hay un plan pendiente de aprobación. "
                      "Apruébalo o recházalo antes de enviar otra consulta.",
            )

        estado_inicial = {
            "thread_id": thread_id,
            "historial": [HumanMessage(content=texto.strip())],
            "done": False,
            "pedido": texto.strip(),
            "notas": {},
            "respuesta": "",
            "plan": [],
            "aprobado": None,
            "pasos": 0,
            "pasos_especialista": {},
            "traza": [],
            "imagen": imagen,
        }

        # La imagen se acepta en la interfaz pública. Su integración
        # con el especialista visual se completará en el grafo.
        if imagen is not None:
            if not isinstance(imagen, dict):
                return _respuesta_publica(
                    thread_id,
                    {},
                    error="La imagen debe ser un diccionario con bytes y mime.",
                )

            if "bytes" not in imagen or "mime" not in imagen:
                return _respuesta_publica(
                    thread_id,
                    {},
                    error="La imagen debe incluir las claves 'bytes' y 'mime'.",
                )

        resultado = _grafo.invoke(estado_inicial, config=config)
        estado = dict(resultado or _estado_actual(config))
        pendiente = _hay_plan_pendiente(config)

        return _respuesta_publica(
            thread_id,
            estado,
            pendiente_aprobacion=pendiente,
        )

    except Exception as exc:
        try:
            estado = _estado_actual(config)
            pendiente = _hay_plan_pendiente(config)
        except Exception:
            estado = {}
            pendiente = False

        return _respuesta_publica(
            thread_id,
            estado,
            pendiente_aprobacion=pendiente,
            error=f"Error al procesar la consulta: {exc}",
        )


def aprobar_plan(
    thread_id: str,
    aprobado: bool,
    comentario: str = "",
) -> dict:
    """Aprueba o rechaza el plan que está pendiente en una conversación."""
    

    try:
        if not isinstance(thread_id, str) or not thread_id.strip():
            return _respuesta_publica(
                thread_id,
                {},
                error="El thread_id debe ser una cadena no vacía.",
            )

        config = _config(thread_id)

        if not isinstance(aprobado, bool):
            return _respuesta_publica(
                thread_id,
                _estado_actual(config),
                error="El parámetro aprobado debe ser True o False.",
            )

        if not _hay_plan_pendiente(config):
            return _respuesta_publica(
                thread_id,
                _estado_actual(config),
                error="No hay ningún plan pendiente de aprobación.",
            )

        estado = _estado_actual(config)

        if not estado.get("plan"):
            return _respuesta_publica(
                thread_id,
                estado,
                error="No existe un plan que pueda aprobarse o rechazarse.",
            )

        # Guardamos la decisión y reanudamos el grafo desde el nodo
        # donde se encontraba pausado: 'aplicar'.
        _grafo.update_state(
            config,
            {
                "aprobado": aprobado,
                "comentario_aprobacion": comentario,
            },
        )

        resultado = _grafo.invoke(None, config=config)
        estado_final = dict(resultado or _estado_actual(config))

        return _respuesta_publica(
            thread_id,
            estado_final,
            pendiente_aprobacion=_hay_plan_pendiente(config),
        )

    except Exception as exc:
        try:
            estado = _estado_actual(config)
            pendiente = _hay_plan_pendiente(config)
        except Exception:
            estado = {}
            pendiente = False

        return _respuesta_publica(
            thread_id,
            estado,
            pendiente_aprobacion=pendiente,
            error=f"Error al gestionar la aprobación: {exc}",
        )
