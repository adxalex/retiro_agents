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


PROMPT_NORMAS = """
Eres el especialista de conocimiento del Parque del Retiro de Madrid.

Tu responsabilidad es responder preguntas sobre historia, lugares,
jardines, instalaciones, servicios y normas usando exclusivamente
la información proporcionada por la herramienta RAG.

Instrucciones:
- No inventes hechos que no aparezcan en el resultado del RAG.
- Respeta las abstenciones y limitaciones del RAG.
- Conserva las fuentes y citas que proporcione la herramienta.
- Si la evidencia es insuficiente, indícalo claramente.
- Responde en español, de forma clara y concisa.
"""

PROMPT_ENTORNO = """
Eres el especialista de planificación de visitas al Parque del Retiro.

Tu responsabilidad es interpretar la petición del usuario y los datos
proporcionados por las herramientas de hora, contexto externo e imagen.

Instrucciones:
- No inventes horarios, meteorología, cierres ni resultados de herramientas.
- Distingue los datos comprobados de la información no disponible.
- Si la petición requiere organizar una visita, propone pasos concretos
  solo cuando estén respaldados por la información disponible.
- Presenta los pasos de un plan como viñetas que comiencen por "- ".
- Si no hay información suficiente para proponer un plan fiable,
  indícalo en lugar de inventar un itinerario.
- Responde en español.
"""


def _generar_nota_especialista(
    prompt: str,
    contexto: str,
    llm_runner: Callable | None = None,
) -> str | None:
    """Genera la nota de un especialista, sin propagar errores del LLM."""
    try:
        if llm_runner is not None:
            resultado = llm_runner(prompt, contexto)
        else:
            from langchain_google_genai import ChatGoogleGenerativeAI

            modelo = getattr(
                config,
                "LLM_MODEL",
                "gemini-2.5-flash",
            )
            llm = ChatGoogleGenerativeAI(model=modelo)
            resultado = llm.invoke([
                ("system", prompt),
                ("human", contexto),
            ])

        contenido = getattr(resultado, "content", resultado)

        if isinstance(contenido, str) and contenido.strip():
            return contenido.strip()

    except Exception:
        # El especialista conserva el resultado original de las tools
        # si el LLM falla o no está disponible.
        return None

    return None



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

def _ruta_supervisor_limitada(estado: EstadoGrafo) -> str:
    """Selecciona una ruta respetando el límite de iteraciones."""
    # Reservamos la última ejecución del supervisor para sintetizar.
    if estado.get("pasos", 0) >= config.MAX_ITER - 1:
        return "sintetizar"

    ruta = _seleccionar_ruta(estado)

    if ruta not in RUTAS_VALIDAS:
        ruta = _ruta_fallback(estado)

    if (
        ruta in ESPECIALISTAS
        and not _especialista_disponible(estado, ruta)
    ):
        ruta = _ruta_fallback(estado)

    if (
        ruta in ESPECIALISTAS
        and not _especialista_disponible(estado, ruta)
    ):
        return "sintetizar"

    return ruta if ruta in RUTAS_VALIDAS else "sintetizar"



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


def _ruta_tras_sintesis(estado: EstadoGrafo) -> str:
    """Solo solicita aprobación si existe un plan no vacío."""
    plan = estado.get("plan") or []

    if any(
        isinstance(paso, str) and paso.strip()
        for paso in plan
    ):
        return "aplicar"

    return END



def build_graph(
    tool_runner: Callable | None = None,
    llm_runner: Callable | None = None,
):
    """Construye y devuelve el grafo compilado del agente."""
    ejecutar = tool_runner or _ejecutar_tool

    
    def supervisor(estado: EstadoGrafo) -> Command:
        """Selecciona una ruta sin superar MAX_ITER pasadas."""
        pasos_actuales = estado.get("pasos", 0)

        # La última pasada disponible se reserva para sintetizar.
        # Así nunca se envía un especialista al supervisor por séptima vez.
        if pasos_actuales >= config.MAX_ITER - 1:
            ruta = "sintetizar"
        else:
            ruta = _ruta_supervisor_limitada(estado)

        if ruta not in RUTAS_VALIDAS:
            ruta = _ruta_fallback(estado)

        if (
            ruta in ESPECIALISTAS
            and not _especialista_disponible(estado, ruta)
        ):
            ruta = _ruta_fallback(estado)

        if ruta not in RUTAS_VALIDAS:
            ruta = "sintetizar"

        # Un especialista agotado no puede volver a seleccionarse.
        if (
            ruta in ESPECIALISTAS
            and not _especialista_disponible(estado, ruta)
        ):
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
                "pasos": pasos_actuales + 1,
                "traza": estado.get("traza", []) + [evento],
            },
            goto=ruta,
        )

    def conocimiento_retiro(estado: EstadoGrafo) -> dict:
        """Consulta el conocimiento documentado mediante RAG."""
        nombre_tool = "rag_ask"
        argumentos = {"pregunta": estado.get("pedido", "")}

        resultado = ejecutar(nombre_tool, argumentos)
        data = resultado.get("data") or {}

        nota_original = _formatear_resultado_rag(data)

        if resultado.get("status") != "ok":
            nota = (
                "No se pudo consultar el conocimiento documentado "
                "del parque. No se ha confirmado información del RAG. "
                f"Error: {resultado.get('error') or 'desconocido'}"
            )
        else:
            contexto = (
                f"Petición del usuario:\n"
                f"{estado.get('pedido', '')}\n\n"
                f"Resultado de rag_ask:\n{nota_original}"
            )

            nota = (
                _generar_nota_especialista(
                    PROMPT_NORMAS,
                    contexto,
                    llm_runner,
                )
                or nota_original
            )

        notas = dict(estado.get("notas", {}))
        notas["normas"] = nota

        # Registrar también la ejecución de la herramienta en la traza.
        evento_tool = resultado.get("traza") or _evento(
            "tool",
            nombre_tool,
            argumentos,
            resultado.get("status", "error"),
            nota_original or resultado.get("error", ""),
        )

        return {
            "notas": notas,
            "pasos_especialista": _actualizar_contador(
                estado, "normas"
            ),
            "traza": estado.get("traza", []) + [evento_tool],
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

        
        contexto_original = "\n".join(resultados)

        contexto = (
            f"Petición del usuario:\n"
            f"{estado.get('pedido', '')}\n\n"
            f"Datos obtenidos de las herramientas:\n"
            f"{contexto_original}"
        )

        nota_generada = _generar_nota_especialista(
            PROMPT_ENTORNO,
            contexto,
            llm_runner,
        )

        # Si falla el LLM, conservamos los datos originales.
        nota = nota_generada or contexto_original

        notas = dict(estado.get("notas", {}))
        notas["entorno"] = nota

        return {
            "notas": notas,
            "pasos_especialista": _actualizar_contador(
                estado, "entorno"
            ),
            "traza": estado.get("traza", []) + eventos,
        }

    
    
    
    def sintetizar(estado: EstadoGrafo) -> dict:
        """Integra los resultados y prepara una propuesta para HITL."""
        notas = estado.get("notas", {})
        normas = (notas.get("normas") or "").strip()
        entorno = (notas.get("entorno") or "").strip()

        secciones = []
        limitaciones = []
        plan = []

        # Información documental.
        normas_lower = normas.lower()
        normas_utiles = bool(normas) and not any(
            texto in normas_lower
            for texto in (
                "no se pudo consultar",
                "no se ha confirmado información del rag",
                "no ha podido confirmar la respuesta",
            )
        )

        if normas:
            secciones.append(
                "**Información sobre el Parque del Retiro**\n" + normas
            )

        if normas and not normas_utiles:
            limitaciones.append(
                "La información documental no se ha podido verificar."
            )

        # Contexto temporal, información externa e imagen.
        entorno_lower = entorno.lower()
        entorno_util = bool(entorno) and not all(
            frase in entorno_lower
            for frase in (
                "no se pudo obtener la hora",
                "no se pudo obtener información externa",
                "no se pudo describir la imagen",
            )
        )

        if entorno:
            secciones.append(
                "**Contexto de la visita**\n" + entorno
            )

        if any(
            frase in entorno_lower
            for frase in (
                "no se pudo obtener",
                "no se pudo describir",
                "error:",
            )
        ):
            limitaciones.append(
                "Una o varias herramientas no han devuelto información fiable."
            )

        # Si ya existen pasos estructurados, los conservamos.
        # No extraemos como acciones las líneas descriptivas de las tools.
        for linea in entorno.splitlines():
            texto = linea.strip()
            paso = ""

            if texto.startswith(("- ", "• ", "* ")):
                paso = texto[2:].strip()
            elif (
                len(texto) >= 3
                and texto[0].isdigit()
                and texto[1:3] in (". ", ") ")
            ):
                paso = texto[3:].strip()

            if paso and paso not in plan:
                plan.append(paso)

        # Si los especialistas han aportado información utilizable, pero
        # todavía no han construido un itinerario, proponemos acciones
        # de revisión basadas en las fuentes disponibles. No inventamos
        # nombres de lugares, horarios ni condiciones del parque.
        if not plan and (normas_utiles or entorno_util):
            if normas_utiles:
                plan.append(
                    "Revisar los lugares de interés identificados "
                    "en la información documental disponible."
                )

            if entorno_util:
                plan.append(
                    "Revisar el contexto temporal y la información externa "
                    "disponible antes de organizar la visita."
                )

        if secciones:
            respuesta = "\n\n".join(secciones)
        else:
            respuesta = (
                "No he podido obtener información suficiente para responder "
                "con garantías. No voy a inventar datos sobre el parque."
            )
            limitaciones.append(
                "Ninguno de los especialistas ha aportado información utilizable."
            )

        if limitaciones:
            respuesta += (
                "\n\n**Limitaciones**\n"
                + "\n".join(
                    f"- {texto}"
                    for texto in dict.fromkeys(limitaciones)
                )
            )

        if plan:
            respuesta += (
                "\n\n**Propuesta pendiente de aprobación**\n"
                + "\n".join(f"- {paso}" for paso in plan)
                + "\n\nNo se aplicará hasta que la apruebes."
            )
        else:
            respuesta += (
                "\n\nNo se ha generado una propuesta aprobable porque "
                "no hay información suficiente."
            )

        return {
            "respuesta": respuesta,
            "plan": plan,
            "aprobado": None,
            "comentario_aprobacion": "",
            "done": False,
        }




    def aplicar(estado: EstadoGrafo) -> dict:
        """Finaliza el plan únicamente tras validarlo y recibir aprobación."""
        aprobado = estado.get("aprobado")
        comentario = (
            estado.get("comentario_aprobacion") or ""
        ).strip()
        plan = estado.get("plan") or []

        if aprobado is True:
            # No se puede completar un plan vacío.
            if not plan:
                evento = _evento(
                    "hitl",
                    "aplicar",
                    {"comentario": comentario},
                    "error",
                    "No se puede completar un plan vacío.",
                )
                return {
                    "done": False,
                    "traza": estado.get("traza", []) + [evento],
                }

            # El plan aprobado se conserva como resultado final.
            # En este proyecto, aplicar significa confirmar la
            # propuesta de visita; no modifica sistemas externos.
            evento = _evento(
                "hitl",
                "aplicar",
                {
                    "comentario": comentario,
                    "numero_pasos": len(plan),
                },
                "ok",
                "El plan de visita ha sido aprobado y confirmado.",
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

        # Sin aprobación explícita, nunca se completa el plan.
        evento = _evento(
            "hitl",
            "aplicar",
            {},
            "blocked",
            "No existe aprobación humana explícita.",
        )
        return {
            "done": False,
            "traza": estado.get("traza", []) + [evento],
        }


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

    # Solo se solicita aprobación si sintetizar ha generado un plan.
    builder.add_conditional_edges(
        "sintetizar",
        _ruta_tras_sintesis,
    )

    builder.add_edge("aplicar", END)


    # IMPORTANTE: devolver el grafo compilado.
    return builder.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["aplicar"],
    )
