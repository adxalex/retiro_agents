
from datetime import datetime
from typing import Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.state import EstadoGrafo


def _ahora_iso() -> str:
    """Devuelve la fecha y hora actual en formato ISO 8601."""
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
        "preview": preview[:200],
    }


def _ejecutar_tool(nombre: str, args: dict) -> dict:
    """Ejecuta una herramienta sin propagar errores al grafo."""
    try:
        from src.tools import ejecutar_tool

        resultado = ejecutar_tool(nombre, args)

        if not isinstance(resultado, dict):
            raise TypeError("La herramienta debe devolver un diccionario.")

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


def _ruta_fallback(estado: EstadoGrafo) -> str:
    """Selecciona un especialista mediante reglas Python si falla el supervisor LLM."""
    pedido = estado.get("pedido", "").lower()
    notas = estado.get("notas", {})
    pasos = estado.get("pasos", 0)

    # Evitamos superar el límite de iteraciones.
    if pasos >= 6:
        return "sintetizar"

    palabras_planificacion = (
        "plan", "ruta", "visita", "horario", "hora", "tiempo",
        "meteorología", "clima", "hoy", "mañana", "organizar",
        "itinerario", "cuánto tiempo", "abierto", "abren", "cierran",
    )
    palabras_conocimiento = (
        "dónde", "donde", "historia", "norma", "regla", "servicio",
        "instalación", "instalaciones", "estanque", "palacio",
        "jardín", "jardines", "monumento", "fuente", "retiro",
        "se puede", "qué hay", "que hay",
    )

    necesita_planificacion = any(
        palabra in pedido for palabra in palabras_planificacion
    )
    necesita_conocimiento = any(
        palabra in pedido for palabra in palabras_conocimiento
    )

    # Si el usuario necesita ambas especialidades, se consultan las dos.
    if necesita_planificacion and "entorno" not in notas:
        return "entorno"

    if necesita_conocimiento and "normas" not in notas:
        return "normas"

    # Para consultas generales, empezamos por el conocimiento del parque.
    if not notas:
        return "normas"

    return "sintetizar"


def _seleccionar_ruta(estado: EstadoGrafo) -> str:
    """Intenta usar un supervisor LLM y recurre a Python si falla."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from src import config

        modelo = getattr(
            config,
            "LLM_MODEL",
            getattr(config, "MODELO_PRINCIPAL", "gemini-2.5-flash"),
        )

        llm = ChatGoogleGenerativeAI(model=modelo)

        mensaje = (
            "Eres el supervisor de un agente sobre el Parque del Retiro de Madrid. "
            "Selecciona el siguiente nodo y responde SOLO con uno de estos nombres: "
            "'normas', 'entorno' o 'sintetizar'.\n"
            "'normas' consulta el conocimiento documentado del parque mediante RAG.\n"
            "'entorno' consulta contexto de visita, como hora, meteorología o imagen.\n"
            "'sintetizar' termina la consulta a especialistas y prepara la respuesta.\n"
            f"Consulta del usuario: {estado.get('pedido', '')}\n"
            f"Notas obtenidas: {list(estado.get('notas', {}).keys())}\n"
            f"Iteración actual: {estado.get('pasos', 0)}"
        )

        resultado = llm.invoke(mensaje)
        ruta = resultado.content.strip().lower().strip("'\"")

        if ruta in {"normas", "entorno", "sintetizar"}:
            if estado.get("pasos", 0) >= 6:
                return "sintetizar"
            return ruta

    except Exception:
        # Si el modelo no está disponible, usamos la selección determinista.
        pass

    return _ruta_fallback(estado)


def build_graph(
    tool_runner: Callable | None = None,
):
    """Construye y compila el grafo del agente con pausa antes de aplicar el plan."""
    ejecutar = tool_runner or _ejecutar_tool

    def supervisor(estado: EstadoGrafo) -> dict:
        ruta = _seleccionar_ruta(estado)
        evento = _evento(
            "supervisor",
            ruta,
            {},
            "ok",
            f"Siguiente nodo seleccionado: {ruta}",
        )

        return {
            "pasos": estado.get("pasos", 0) + 1,
            "traza": estado.get("traza", []) + [evento],
        }

    def conocimiento_retiro(estado: EstadoGrafo) -> dict:
        nombre_tool = "rag_ask"
        argumentos = {"pregunta": estado.get("pedido", "")}
        resultado = ejecutar(nombre_tool, argumentos)

        data = resultado.get("data") or {}
        if isinstance(data, dict):
            nota = str(data.get("respuesta", data))
        else:
            nota = str(data)

        if resultado.get("status") != "ok":
            nota = (
                f"No se pudo consultar el conocimiento documentado del parque: "
                f"{resultado.get('error') or 'error desconocido'}"
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
            "traza": estado.get("traza", []) + [evento],
        }

    def planificacion_visita(estado: EstadoGrafo) -> dict:
        # En esta primera versión se consulta la hora. Más adelante
        # ampliaremos el especialista con meteorología e imágenes.
        nombre_tool = "hora_actual"
        argumentos = {}
        resultado = ejecutar(nombre_tool, argumentos)

        data = resultado.get("data") or {}
        if isinstance(data, dict):
            nota = str(data)
        else:
            nota = str(data)

        if resultado.get("status") != "ok":
            nota = (
                "No se pudo obtener el contexto temporal de la visita: "
                f"{resultado.get('error') or 'error desconocido'}"
            )

        evento = resultado.get("traza") or _evento(
            "tool",
            nombre_tool,
            argumentos,
            resultado.get("status", "error"),
            nota,
        )

        notas = dict(estado.get("notas", {}))
        notas["entorno"] = nota

        return {
            "notas": notas,
            "traza": estado.get("traza", []) + [evento],
        }

    def sintetizar(estado: EstadoGrafo) -> dict:
        notas = estado.get("notas", {})
        partes = []

        if notas.get("normas"):
            partes.append(
                "Conocimiento del Retiro:\n" + notas["normas"]
            )

        if notas.get("entorno"):
            partes.append(
                "Planificación y contexto de visita:\n" + notas["entorno"]
            )

        respuesta = "\n\n".join(partes)
        if not respuesta:
            respuesta = (
                "No he podido obtener información suficiente para responder "
                "con garantías."
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
        }

    def aplicar(estado: EstadoGrafo) -> dict:
        aprobado = estado.get("aprobado")

        if aprobado is True:
            evento = _evento(
                "hitl",
                "aprobar",
                {},
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
                {},
                "ok",
                "El usuario ha rechazado el plan.",
            )
            return {
                "pedido": "",
                "notas": {},
                "respuesta": "",
                "plan": [],
                "aprobado": None,
                "pasos": 0,
                "done": False,
                "traza": estado.get("traza", []) + [evento],
            }

        # La aplicación nunca debe marcarse como terminada sin aprobación.
        return {"done": False}

    grafo = StateGraph(EstadoGrafo)

    grafo.add_node("supervisor", supervisor)
    grafo.add_node("normas", conocimiento_retiro)
    grafo.add_node("entorno", planificacion_visita)
    grafo.add_node("sintetizar", sintetizar)
    grafo.add_node("aplicar", aplicar)

    grafo.add_edge(START, "supervisor")

    grafo.add_conditional_edges(
        "supervisor",
        _seleccionar_ruta,
        {
            "normas": "normas",
            "entorno": "entorno",
            "sintetizar": "sintetizar",
        },
    )

    grafo.add_edge("normas", "supervisor")
    grafo.add_edge("entorno", "supervisor")
    grafo.add_edge("sintetizar", "aplicar")
    grafo.add_edge("aplicar", END)

    return grafo.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["aplicar"],
    )
