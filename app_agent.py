"""Streamlit del agente: chat, aprobación del plan y panel de depuración."""
import streamlit as st

from src import agent
from src import ui_agente

st.set_page_config(page_title="Agente del Retiro", page_icon="🌳")

# Avatar y elemento de Streamlit con que se pinta cada rol del chat.
AVATARES = {
    ui_agente.ROL_USUARIO: "user",
    ui_agente.ROL_AGENTE: "assistant",
    ui_agente.ROL_SISTEMA: "ℹ️",
    ui_agente.ROL_AVISO: "⚠️",
}


def _sesion() -> dict:
    """Devuelve la sesión del agente, creándola en la primera carga."""
    if "agente" not in st.session_state:
        st.session_state["agente"] = ui_agente.nueva_sesion()
    if "comentario_n" not in st.session_state:
        st.session_state["comentario_n"] = 0
    return st.session_state["agente"]


def _pintar_mensaje(mensaje: dict) -> None:
    """Pinta un mensaje del chat según su rol."""
    rol = mensaje["rol"]
    with st.chat_message(rol if rol == ui_agente.ROL_USUARIO else "assistant",
                         avatar=AVATARES.get(rol)):
        if rol == ui_agente.ROL_AVISO:
            st.warning(mensaje["texto"])
        elif rol == ui_agente.ROL_SISTEMA:
            st.info(mensaje["texto"])
        elif mensaje["texto"]:
            st.markdown(mensaje["texto"])
        if mensaje["plan"]:
            st.markdown("\n".join(
                f"{i}. {paso}" for i, paso in enumerate(mensaje["plan"], start=1)))


def _sidebar(sesion: dict) -> None:
    """Comentario y botones de decisión sobre el plan pendiente."""
    hay_plan = ui_agente.pendiente(sesion)
    with st.sidebar:
        st.header("Plan propuesto")
        comentario = st.text_area(
            "Comentario (opcional)",
            key=f"comentario_{st.session_state['comentario_n']}",
            disabled=not hay_plan,
        )
        columna_aprobar, columna_rechazar = st.columns(2)
        aprobar = columna_aprobar.button(
            "Aprobar", key="aprobar", disabled=not hay_plan, type="primary")
        rechazar = columna_rechazar.button(
            "Rechazar", key="rechazar", disabled=not hay_plan)

    if aprobar or rechazar:
        with st.spinner("Enviando la decisión al agente..."):
            ui_agente.decidir(sesion, aprobar, comentario, agent.aprobar_plan)
        # Una clave nueva deja vacío el campo de comentario.
        st.session_state["comentario_n"] += 1
        st.rerun()


def _depuracion(sesion: dict) -> None:
    """Panel plegable con el estado y la traza de la última llamada."""
    datos = ui_agente.estado_depuracion(sesion)
    with st.expander("Depuración", expanded=False):
        st.markdown(f"**thread_id:** `{datos['thread_id']}`")
        st.markdown(
            f"**pendiente_aprobacion:** `{datos['pendiente_aprobacion']}` · "
            f"**done:** `{datos['done']}`")
        if datos["filas"]:
            st.dataframe(datos["filas"], hide_index=True)
        else:
            st.caption("Sin eventos de traza.")
        if datos["comentario"]:
            st.markdown(f"**Comentario de la decisión:** {datos['comentario']}")


def main() -> None:
    """Punto de entrada de la app de Streamlit."""
    st.title("Agente del Parque de El Retiro")
    sesion = _sesion()
    _sidebar(sesion)

    for mensaje in sesion["mensajes"]:
        _pintar_mensaje(mensaje)

    bloqueado = ui_agente.pendiente(sesion)
    if bloqueado:
        st.warning(ui_agente.AVISO_PLAN_PENDIENTE)

    _depuracion(sesion)

    texto = st.chat_input(
        "Pregunta o pide un plan de visita...", key="chat", disabled=bloqueado)
    if texto:
        with st.spinner("El agente está trabajando..."):
            ui_agente.enviar_turno(sesion, texto, None, None, agent.procesar_turno)
        st.rerun()


if __name__ == "__main__":
    main()
