"""Streamlit: chat, contexto recuperado y tabla de metricas."""
import time

import streamlit as st

from config import LLM_MODEL, TOP_K, COLLECTION_NAME
from src.generate import responder

st.set_page_config(page_title="Retiro RAG", page_icon="🌳")


def _inicializar_estado() -> None:
    """Crea las estructuras de sesion la primera vez que carga la pagina."""
    if "historial" not in st.session_state:
        st.session_state.historial = []  # lista de {"pregunta": ..., "respuesta": dict}
    if "metricas" not in st.session_state:
        st.session_state.metricas = []  # lista de filas para la tabla


def _renderizar_banner_clima() -> None:
    """Banner opcional con el clima en vivo del Retiro (AEMET).

    No forma parte del RAG: no entra al contexto del LLM ni a las citas.
    Si el modulo de David todavia no esta integrado, no se muestra nada.
    """
    try:
        from src.contexto_visita import saludo_contextual
    except ImportError:
        return

    contexto = saludo_contextual()
    with st.container(border=True):
        st.markdown(f"**{contexto['saludo']}**")
        observacion = contexto.get("observacion")
        if observacion and observacion.get("temperatura_c") is not None:
            columnas = st.columns(3)
            columnas[0].metric("Temperatura", f"{observacion['temperatura_c']} °C")
            if observacion.get("viento_kmh") is not None:
                columnas[1].metric("Viento", f"{observacion['viento_kmh']:.0f} km/h")
            if observacion.get("racha_kmh") is not None:
                columnas[2].metric("Racha máx.", f"{observacion['racha_kmh']:.0f} km/h")
        for peculiaridad in contexto.get("peculiaridades", []):
            st.caption(peculiaridad)
        if contexto.get("fuente"):
            st.caption(f"Tiempo actual, medido por {contexto['fuente']}.")


def _renderizar_historial() -> None:
    """Vuelve a pintar todos los turnos de chat ya realizados."""
    for turno in st.session_state.historial:
        with st.chat_message("user"):
            st.write(turno["pregunta"])
        with st.chat_message("assistant"):
            _renderizar_respuesta(turno["respuesta"])


def _renderizar_respuesta(respuesta: dict) -> None:
    """Muestra respuesta, fuentes y chunks de un resultado de responder()."""
    if respuesta.get("abstuvo"):
        st.warning(respuesta["respuesta"])
    else:
        st.write(respuesta["respuesta"])

    citas = respuesta.get("citas") or []
    for cita in citas:
        marca = "" if cita["oficial"] else "⚠ "
        st.caption(f"[{cita['n']}] {marca}{cita['texto']}")

    chunks = respuesta.get("chunks") or []
    if chunks:
        with st.expander(f"Ver {len(chunks)} chunk(s) recuperado(s)"):
            for chunk in chunks:
                procedencia = chunk.get("source", "desconocido")
                if chunk.get("page"):
                    procedencia += f" · página {chunk['page']}"
                st.markdown(
                    f"**{procedencia}** · score {chunk.get('score', 0):.3f}"
                )
                st.text(chunk.get("text", ""))


def _clasificar_error(error: Exception) -> str:
    """Traduce una excepcion real del pipeline a un mensaje entendible.

    Sigue la misma convencion que main.py: busca pistas en el mensaje para
    distinguir indice no construido, configuracion incompleta u otro fallo.
    """
    mensaje = str(error)
    if "does not exist" in mensaje or COLLECTION_NAME in mensaje:
        return (
            f"El índice de Chroma ('{COLLECTION_NAME}') todavía no existe. "
            "Constrúyelo primero con `python main.py --index` antes de preguntar."
        )
    if "API key" in mensaje or "GEMINI_API_KEY" in mensaje:
        return (
            "Configuración incompleta: falta `GEMINI_API_KEY` (o `GOOGLE_API_KEY`) "
            "en tu archivo .env."
        )
    if isinstance(error, ValueError):
        return f"No se pudo procesar la pregunta: {mensaje}"
    return f"Fallo al generar la respuesta (Gemini o Chroma): {mensaje}"


def _procesar_pregunta(pregunta: str) -> None:
    """Llama a responder(), mide tiempo y actualiza historial y metricas."""
    inicio = time.perf_counter()
    error_mostrado = None
    try:
        with st.spinner("Buscando en el corpus del Retiro..."):
            respuesta = responder(pregunta)
    except Exception as error:  # noqa: BLE001 - se traduce para la interfaz
        error_mostrado = _clasificar_error(error)
        respuesta = {
            "respuesta": error_mostrado,
            "fuentes": [],
            "chunks": [],
            "abstuvo": True,
        }
    tiempo = time.perf_counter() - inicio

    st.session_state.historial.append(
        {"pregunta": pregunta, "respuesta": respuesta})
    st.session_state.metricas.append({
        "pregunta": pregunta,
        "k": TOP_K,
        "n_chunks": len(respuesta.get("chunks") or []),
        "tiempo_s": round(tiempo, 2),
        "modelo": LLM_MODEL,
        "abstuvo": respuesta.get("abstuvo", False),
        "error": error_mostrado,
    })


def main() -> None:
    """Punto de entrada de la app de Streamlit."""
    st.title("Retiro RAG — Asistente del Parque de El Retiro")
    _renderizar_banner_clima()
    _inicializar_estado()
    _renderizar_historial()

    pregunta = st.chat_input("Pregunta algo sobre el Parque de El Retiro...")
    if pregunta:
        with st.chat_message("user"):
            st.write(pregunta)
        with st.chat_message("assistant"):
            _procesar_pregunta(pregunta)
            _renderizar_respuesta(st.session_state.historial[-1]["respuesta"])

    if st.session_state.historial and st.button("🗑️ Limpiar historial"):
        st.session_state.historial = []
        st.session_state.metricas = []
        st.rerun()

    if st.session_state.metricas:
        st.subheader("Métricas de las consultas")
        st.dataframe(st.session_state.metricas, use_container_width=True)


if __name__ == "__main__":
    main()