
"""Grafo de ejecución del agente del Parque del Retiro."""

from datetime import datetime
from typing import Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

import config
from src.state import EstadoGrafo


RUTAS_VALIDAS = {"normas", "entorno", "sintetizar"}
ESPECIALISTAS = {"normas", "entorno"}


def _ahora_iso() -> str:
    """Devuelve la fecha y hora con zona horaria."""
    return datetime.now().astimezone().isoformat()


def _evento(
    origen: str,
    nombre: str,
    args: dict,
    status: str,
    preview: str,
) -> dict:
    """Construye un evento de trazabilidad."""
    return {
        "ts": _ahora_iso(),
        "origen": origen,
        "nombre": nombre,
        "args": args,
        "status": status,
        "preview": str(preview)[:200],
    }


def _ejecutar_tool(nombre: str, args: dict) -> dict:
    """Ejecuta una herramienta sin propagar excepciones."""
    try:
        from src.tools import ejecutar_tool

        resultado = ejecutar_tool(nombre, args)

        if not isinstance(resultado, dict):
            raise TypeError(
                "La herramienta debe devolver un diccionario."
            )

        return resultado

    except Exception as exc:
        return {
            "tool": nombre,
            "status": "error",
            "data": {},
            "error": str(exc),
            "traza": _evento(
                "tool",
                nombre,
                args,
                "error",
                str(exc),
            ),
        }


def _limite_alcanzado(estado: EstadoGrafo) -> bool:
    """Comprueba el límite global de iteraciones."""
    return estado.get("pasos", 0) >= config.MAX_ITER


def _especialista_disponible(
    estado: EstadoGrafo,
    especialista: str,
) -> bool:
    """Comprueba el límite de ejecuciones de un especialista."""
    contadores = estado.get("pasos_especialista", {})
    return (
        contadores.get(especialista, 0)
        < config.MAX_STEPS_ESPECIALISTA
    )


def _actualizar_contador(
    estado: EstadoGrafo,
    especialista: str,
) -> dict[str, int]:
    """Incrementa el contador de ejecuciones de un especialista."""
    contadores = dict(estado.get("pasos_especialista", {}))
    contadores[especialista] = contadores.get(especialista, 0) + 1
    return contadores


def _ruta_fallback(estado: EstadoGrafo) -> str:
    """Selecciona una ruta determinista si falla el supervisor LLM."""
    pedido = estado.get("pedido", "").lower()
    notas = estado.get("notas", {})

    if _limite_alcanzado(estado):
        return "sintetizar"

    palabras_planificacion = (
        "plan", "ruta", "visita", "horario", "hora", "tiempo",
        "meteorología", "clima", "hoy", "mañana", "organizar",
        "itinerario", "cuánto tiempo", "abierto", "abren", "cierran",
        "lluvia", "temperatura", "previsión",
    )

    palabras_conocimiento = (
        "dónde", "donde", "historia", "norma", "regla", "servicio",
        "instalación", "instalaciones", "estanque", "palacio",
        "jardín", "jardines", "monumento", "fuente", "retiro",
        "se puede", "qué hay", "que hay", "acceso", "entrada",
    )

    necesita_planificacion = any(
        palabra in pedido for palabra in palabras_planificacion
    )
    necesita_conocimiento = any(
        palabra in pedido for palabra in palabras_conocimiento
    )

    # Si la petición necesita ambos especialistas, priorizamos
    # el que todavía no se haya consultado.
    if (
        necesita_planificacion
        and "entorno" not in notas
        and _especialista_disponible(estado, "entorno")
    ):
        return "entorno"

    if (
        necesita_conocimiento
        and "normas" not in notas
        and _especialista_disponible(estado, "normas")
    ):
        return "normas"

    # Si la petición no encaja en palabras conocidas, empezamos
    # por el conocimiento documentado.
    if not notas:
        if _especialista_disponible(estado, "normas"):
            return "normas"
        if _especialista_disponible(estado, "entorno"):
            return "entorno"

    # Si ya hay información, intentamos consultar el especialista
    # que falte, respetando siempre sus límites.
    if (
        "normas" not in notas
        and _especialista_disponible(estado, "normas")
    ):
        return "normas"

    if (
        "entorno" not in notas
        and _especialista_disponible(estado, "entorno")
    ):
        return "entorno"

    return "sintetizar"


def _seleccionar_ruta(estado: EstadoGrafo) -> str:
    """Selecciona el siguiente nodo mediante el supervisor LLM."""
    if _limite_alcanzado(estado):
        return "sintetizar"

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        modelo = getattr(
            config,
            "LLM_MODEL",
            getattr(
                config,
                "MODELO_PRINCIPAL",
                "gemini-2.5-flash",
            ),
        )

        llm = ChatGoogleGenerativeAI(model=modelo)

        mensaje = (
            "Eres el supervisor de un agente del Parque del Retiro "
            "de Madrid. Responde SOLO con uno de estos nombres: "
            "normas, entorno o sintetizar.\n"
            "normas: consulta el conocimiento documentado del parque.\n"
            "entorno: consulta el contexto temporal y externo de la visita.\n"
            "sintetizar: termina las consultas y prepara la respuesta.\n"
            f"Consulta: {estado.get('pedido', '')}\n"
            f"Especialistas consultados: "
            f"{list(estado.get('notas', {}).keys())}\n"
            f"Iteración: {estado.get('pasos', 0)}"
        )

        resultado = llm.invoke(mensaje)
        ruta = resultado.content.strip().lower().strip("'\"")

        if ruta in RUTAS_VALIDAS:
            return ruta

    except Exception:
        # Si el modelo no está disponible, usamos el fallback.
        pass

    return _ruta_fallback(estado)


def _formatear_resultado_rag(data: dict) -> str:
    """Conserva respuesta, fuentes y citas disponibles del RAG."""
    if not isinstance(data, dict):
        return str(data)

    partes = []

    respuesta = data.get("respuesta")
    if respuesta:
        partes.append(str(respuesta))

    fuentes = data.get("fuentes")
    if fuentes:
        partes.append(f"Fuentes: {fuentes}")

    citas = data.get("citas")
    if citas:
        partes.append(f"Citas: {citas}")

    if data.get("abstuvo"):
        motivo = data.get("motivo_abstencion")
        partes.append(
            "El sistema RAG no ha podido confirmar la respuesta."
            + (f" Motivo: {motivo}" if motivo else "")
        )

    return "\n".join(partes) if partes else str(data)


def build_graph(tool_runner: Callable | None = None):
    """Construye y devuelve el grafo compilado del agente."""
    ejecutar = tool_runner or _ejecutar_tool

    def supervisor(estado: EstadoGrafo) -> Command:
        """Selecciona una ruta y aplica los límites de ejecución."""
        ruta = _seleccionar_ruta(estado)

        # Solo se permiten las rutas definidas en el contrato.
        if ruta not in RUTAS_VALIDAS:
            ruta = _ruta_fallback(estado)

        # No permitimos ejecutar especialistas que hayan agotado
        # su número máximo de ejecuciones.
        if (
            ruta in ESPECIALISTAS
            and not _especialista_disponible(estado, ruta)
        ):
            ruta = _ruta_fallback(estado)

        # Última barrera de seguridad.
        if ruta not in RUTAS_VALIDAS:
            ruta = "sintetizar"

        evento = _evento(
            "supervisor",
            ruta,
            {},
            "ok",
            f"Siguiente nodo seleccionado: {ruta}",
        )

        return Command(
            update={
                "pasos": estado.get("pasos", 0) + 1,
                "traza": estado.get("traza", []) + [evento],
            },
            goto=ruta,
        )

    def conocimiento_retiro(estado: EstadoGrafo) -> dict:
        """Consulta el conocimiento documentado mediante RAG."""
        nombre_tool = "rag_ask"
        argumentos = {"consulta": estado.get("pedido", "")}
        resultado = ejecutar(nombre_tool, argumentos)

        data = resultado.get("data") or {}
        nota = _formatear_resultado_rag(data)

        if resultado.get("status") != "ok":
            nota = (
                "No se pudo consultar el conocimiento documentado "
                "del parque. No se ha confirmado información del RAG. "
                f"Error: {resultado.get('error') or 'desconocido'}"
            )

        evento = resultado.get("traza") or _evento(
            "tool",
            nombre_tool,
            argumentos,
            resultado.get("status", "error"),
            nota,
        )

        notas = dict(estado.get("notas", {}))
        notas["normas"] = nota

        return {
            "notas": notas,
            "pasos_especialista": _actualizar_contador(
                estado, "normas"
            ),
            "traza": estado.get("traza", []) + [evento],
        }

    def planificacion_visita(estado: EstadoGrafo) -> dict:
        """Consulta hora, información externa e imagen opcional."""
        resultados = []
        eventos = []

        # Hora y contexto temporal.
        nombre_tool = "hora_actual"
        resultado = ejecutar(nombre_tool, {})
        data = resultado.get("data") or {}

        if resultado.get("status") == "ok":
            resultados.append(f"Hora y contexto: {data}")
        else:
            resultados.append(
                "No se pudo obtener la hora o el contexto temporal. "
                f"Error: {resultado.get('error') or 'desconocido'}"
            )

        eventos.append(
            resultado.get("traza") or _evento(
                "tool",
                nombre_tool,
                {},
                resultado.get("status", "error"),
                str(data),
            )
        )

        # Contexto externo, por ejemplo meteorología.
        nombre_tool = "api_dominio"
        resultado = ejecutar(nombre_tool, {})
        data = resultado.get("data") or {}

        if resultado.get("status") == "ok":
            resultados.append(f"Información externa: {data}")
        else:
            resultados.append(
                "No se pudo obtener información externa. "
                f"Error: {resultado.get('error') or 'desconocido'}"
            )

        eventos.append(
            resultado.get("traza") or _evento(
                "tool",
                nombre_tool,
                {},
                resultado.get("status", "error"),
                str(data),
            )
        )

        # La imagen es opcional.
        imagen = estado.get("imagen")
        if imagen:
            nombre_tool = "describir_imagen"
            argumentos = {"imagen": imagen}
            resultado = ejecutar(nombre_tool, argumentos)
            data = resultado.get("data") or {}

            if resultado.get("status") == "ok":
                resultados.append(f"Descripción de imagen: {data}")
            else:
                resultados.append(
                    "No se pudo describir la imagen. "
                    f"Error: {resultado.get('error') or 'desconocido'}"
                )

            eventos.append(
                resultado.get("traza") or _evento(
                    "tool",
                    nombre_tool,
                    argumentos,
                    resultado.get("status", "error"),
                    str(data),
                )
            )

        notas = dict(estado.get("notas", {}))
        notas["entorno"] = "\n".join(resultados)

        return {
            "notas": notas,
            "pasos_especialista": _actualizar_contador(
                estado, "entorno"
            ),
            "traza": estado.get("traza", []) + eventos,
        }

    def sintetizar(estado: EstadoGrafo) -> dict:
        """Combina las notas y prepara la respuesta y el plan."""
        notas = estado.get("notas", {})
        partes = []

        if notas.get("normas"):
            partes.append(
                "Conocimiento del Retiro:\n" + notas["normas"]
            )

        if notas.get("entorno"):
            partes.append(
                "Planificación y contexto de visita:\n"
                + notas["entorno"]
            )

        respuesta = "\n\n".join(partes)

        if not respuesta:
            respuesta = (
                "No he podido obtener información suficiente "
                "para responder con garantías."
            )

        plan = [
            linea.strip()
            for linea in respuesta.splitlines()
            if linea.strip()
        ]

        return {
            "respuesta": respuesta,
            "plan": plan,
            "aprobado": None,
            "comentario_aprobacion": "",
            "done": False,
        }

    def aplicar(estado: EstadoGrafo) -> dict:
        """Procesa la decisión humana después de la pausa."""
        aprobado = estado.get("aprobado")
        comentario = (
            estado.get("comentario_aprobacion") or ""
        ).strip()

        if aprobado is True:
            evento = _evento(
                "hitl",
                "aprobar",
                {"comentario": comentario},
                "ok",
                "El usuario ha aprobado el plan.",
            )

            return {
                "done": True,
                "traza": estado.get("traza", []) + [evento],
            }

        if aprobado is False:
            evento = _evento(
                "hitl",
                "rechazar",
                {"comentario": comentario},
                "ok",
                "El usuario ha rechazado el plan.",
            )

            return {
                "pedido": "",
                "notas": {},
                "respuesta": "",
                "plan": [],
                "aprobado": None,
                "comentario_aprobacion": "",
                "pasos": 0,
                "pasos_especialista": {},
                "done": False,
                "traza": estado.get("traza", []) + [evento],
            }

        # Nunca completar un plan sin aprobación explícita.
        return {"done": False}

    # Construcción del grafo.
    builder = StateGraph(EstadoGrafo)

    builder.add_node("supervisor", supervisor)
    builder.add_node("normas", conocimiento_retiro)
    builder.add_node("entorno", planificacion_visita)
    builder.add_node("sintetizar", sintetizar)
    builder.add_node("aplicar", aplicar)

    # Conexiones.
    builder.add_edge(START, "supervisor")
    builder.add_edge("normas", "supervisor")
    builder.add_edge("entorno", "supervisor")
    builder.add_edge("sintetizar", "aplicar")
    builder.add_edge("aplicar", END)

    # IMPORTANTE: devolver el grafo compilado.
    return builder.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["aplicar"],
    )
