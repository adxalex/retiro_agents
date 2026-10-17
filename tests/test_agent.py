
from uuid import uuid4

import pytest

import src.agent as agent
import src.graph as graph_module


def generador_simulado(prompt, contexto):
    """Simula el resultado del LLM sin llamadas externas."""
    return contexto


@pytest.fixture
def agente_pruebas(monkeypatch):
    """Crea un agente aislado sin llamadas a servicios externos."""

    def supervisor_determinista(estado):
        return graph_module._ruta_fallback(estado)

    def herramienta_simulada(nombre, args):
        if nombre == "rag_ask":
            data = {
                "respuesta": "Respuesta documental simulada.",
                "fuentes": ["documento_demo.pdf"],
                "citas": [],
                "abstuvo": False,
                "motivo_abstencion": None,
            }
        elif nombre == "hora_actual":
            data = {
                "hora_madrid": "12:00",
                "estado_parque": "dato simulado",
            }
        else:
            data = {"resultado": "simulado"}

        return {
            "tool": nombre,
            "status": "ok",
            "data": data,
            "error": None,
            "traza": {
                "ts": "2026-01-01T12:00:00+01:00",
                "origen": "tool",
                "nombre": nombre,
                "args": args,
                "status": "ok",
                "preview": "Resultado simulado",
            },
        }

    monkeypatch.setattr(
        graph_module,
        "_seleccionar_ruta",
        supervisor_determinista,
    )

    grafo = graph_module.build_graph(
        tool_runner=herramienta_simulada,
        llm_runner=generador_simulado,
    )

    monkeypatch.setattr(agent, "_grafo", grafo)

    return agent


def test_procesar_turno_devuelve_contrato_publico(agente_pruebas):
    thread_id = str(uuid4())

    resultado = agente_pruebas.procesar_turno(
        "¿Qué lugares interesantes hay en el Retiro?",
        thread_id,
    )

    assert set(resultado) == {
        "thread_id",
        "respuesta",
        "plan",
        "pendiente_aprobacion",
        "done",
        "traza",
        "error",
    }
    assert resultado["thread_id"] == thread_id
    assert resultado["error"] is None
    assert isinstance(resultado["respuesta"], str)
    assert isinstance(resultado["plan"], list)
    assert isinstance(resultado["traza"], list)


def test_el_grafo_se_pausa_antes_de_aplicar(agente_pruebas):
    thread_id = str(uuid4())

    resultado = agente_pruebas.procesar_turno(
        "¿Qué lugares interesantes hay en el Retiro?",
        thread_id,
    )

    assert resultado["pendiente_aprobacion"] is True
    assert resultado["done"] is False

    snapshot = agente_pruebas._grafo.get_state(
        {"configurable": {"thread_id": thread_id}}
    )

    assert "aplicar" in snapshot.next


def test_aprobar_plan_marca_done_como_true(agente_pruebas):
    thread_id = str(uuid4())

    agente_pruebas.procesar_turno(
        "¿Qué lugares interesantes hay en el Retiro?",
        thread_id,
    )

    resultado = agente_pruebas.aprobar_plan(thread_id, True)

    assert resultado["error"] is None
    assert resultado["pendiente_aprobacion"] is False
    assert resultado["done"] is True


def test_rechazar_plan_limpia_el_pedido(agente_pruebas):
    thread_id = str(uuid4())

    agente_pruebas.procesar_turno(
        "¿Qué lugares interesantes hay en el Retiro?",
        thread_id,
    )

    resultado = agente_pruebas.aprobar_plan(
        thread_id,
        False,
        "Quiero otra propuesta",
    )

    assert resultado["error"] is None
    assert resultado["done"] is False
    assert resultado["pendiente_aprobacion"] is False
    assert resultado["respuesta"] == ""
    assert resultado["plan"] == []

    estado = agente_pruebas._estado_actual(
        {"configurable": {"thread_id": thread_id}}
    )

    assert estado["pedido"] == ""
    assert estado["notas"] == {}
    assert estado["aprobado"] is None


def test_se_puede_iniciar_otro_pedido_tras_rechazar(agente_pruebas):
    thread_id = str(uuid4())

    agente_pruebas.procesar_turno(
        "¿Qué lugares interesantes hay en el Retiro?",
        thread_id,
    )

    agente_pruebas.aprobar_plan(thread_id, False)

    resultado = agente_pruebas.procesar_turno(
        "Cuéntame la historia del parque",
        thread_id,
    )

    assert resultado["error"] is None
    assert resultado["pendiente_aprobacion"] is True
    assert resultado["done"] is False


def test_las_conversaciones_no_comparten_estado(agente_pruebas):
    thread_a = str(uuid4())
    thread_b = str(uuid4())

    agente_pruebas.procesar_turno(
        "¿Qué lugares interesantes hay en el Retiro?",
        thread_a,
    )

    agente_pruebas.procesar_turno(
        "¿Qué lugares interesantes hay en el Retiro?",
        thread_b,
    )

    agente_pruebas.aprobar_plan(thread_a, True)

    estado_a = agente_pruebas._estado_actual(
        {"configurable": {"thread_id": thread_a}}
    )

    estado_b = agente_pruebas._estado_actual(
        {"configurable": {"thread_id": thread_b}}
    )

    assert estado_a["done"] is True
    assert estado_b["done"] is False

    assert agente_pruebas._hay_plan_pendiente(
        {"configurable": {"thread_id": thread_b}}
    )


def test_la_traza_registra_supervisor_y_herramientas(agente_pruebas):
    resultado = agente_pruebas.procesar_turno(
        "¿Qué lugares interesantes hay en el Retiro?",
        str(uuid4()),
    )

    origenes = {
        evento["origen"]
        for evento in resultado["traza"]
    }

    assert "supervisor" in origenes
    assert "tool" in origenes

    for evento in resultado["traza"]:
        assert {
            "ts",
            "origen",
            "nombre",
            "args",
            "status",
            "preview",
        }.issubset(evento)


def test_no_se_puede_aprobar_si_no_hay_plan(agente_pruebas):
    resultado = agente_pruebas.aprobar_plan(
        str(uuid4()),
        True,
    )

    assert resultado["error"] is not None
    assert resultado["done"] is False


def test_procesar_turno_rechaza_consultas_vacias(agente_pruebas):
    resultado = agente_pruebas.procesar_turno(
        "   ",
        str(uuid4()),
    )

    assert resultado["error"] is not None
    assert resultado["pendiente_aprobacion"] is False


def test_supervisor_respeta_limite_de_iteraciones():
    from src.graph import _ruta_fallback

    estado = {
        "pedido": "Quiero organizar una visita",
        "notas": {},
        "pasos": 6,
    }

    assert _ruta_fallback(estado) == "sintetizar"


def test_historial_se_conserva_en_la_misma_conversacion(agente_pruebas):
    thread_id = str(uuid4())

    agente_pruebas.procesar_turno(
        "¿Qué lugares interesantes hay en el Retiro?",
        thread_id,
    )

    agente_pruebas.aprobar_plan(thread_id, False)

    agente_pruebas.procesar_turno(
        "Cuéntame la historia del parque",
        thread_id,
    )

    estado = agente_pruebas._estado_actual(
        {"configurable": {"thread_id": thread_id}}
    )

    mensajes = estado["historial"]
    contenidos = [mensaje.content for mensaje in mensajes]

    assert any(
        "lugares interesantes" in contenido.lower()
        for contenido in contenidos
    )

    assert any(
        "historia del parque" in contenido.lower()
        for contenido in contenidos
    )
