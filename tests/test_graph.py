
from src.graph import build_graph, _ruta_fallback
import config


def test_build_graph_devuelve_un_grafo_compilado():
    grafo = build_graph()

    assert grafo is not None
    assert callable(grafo.invoke)


def test_grafo_contiene_los_nodos_principales():
    grafo = build_graph()
    nodos = grafo.get_graph().nodes

    esperados = {
        "supervisor",
        "normas",
        "entorno",
        "sintetizar",
        "aplicar",
    }

    assert esperados.issubset(nodos.keys())


def test_max_iter_es_seis():
    assert config.MAX_ITER == 6


def test_max_steps_especialista_es_tres():
    assert config.MAX_STEPS_ESPECIALISTA == 3


def test_fallback_sintetiza_al_alcanzar_max_iter():
    estado = {
        "pedido": "Quiero organizar una visita",
        "notas": {},
        "pasos": config.MAX_ITER,
        "pasos_especialista": {},
    }

    assert _ruta_fallback(estado) == "sintetizar"


def test_estado_inicializa_contador_por_especialista():
    from src.state import EstadoGrafo
    from typing import get_type_hints

    campos = get_type_hints(EstadoGrafo, include_extras=True)

    assert "pasos_especialista" in campos

def test_aplicar_marca_done_true_con_plan_aprobado():
    from src.state import EstadoGrafo

    grafo = build_graph()

    estado = {
        "pedido": "Quiero visitar el Retiro",
        "plan": ["Visitar el Palacio de Cristal"],
        "aprobado": True,
        "comentario_aprobacion": "",
        "traza": [],
        "done": False,
    }

    resultado = grafo.nodes["aplicar"].invoke(estado)

    assert resultado["done"] is True


def test_aplicar_no_completa_un_plan_rechazado():
    grafo = build_graph()

    estado = {
        "pedido": "Quiero visitar el Retiro",
        "plan": ["Visitar el Palacio de Cristal"],
        "aprobado": False,
        "comentario_aprobacion": "Prefiero otra ruta",
        "traza": [],
        "done": False,
    }

    resultado = grafo.nodes["aplicar"].invoke(estado)

    assert resultado["done"] is False
    assert resultado["plan"] == []
    assert resultado["pedido"] == ""
    assert resultado["aprobado"] is None


def test_aplicar_no_completa_sin_aprobacion_explicita():
    grafo = build_graph()

    estado = {
        "pedido": "Quiero visitar el Retiro",
        "plan": ["Visitar el Palacio de Cristal"],
        "aprobado": None,
        "comentario_aprobacion": "",
        "traza": [],
        "done": False,
    }

    resultado = grafo.nodes["aplicar"].invoke(estado)

    assert resultado["done"] is False
    assert resultado["traza"][-1]["status"] == "blocked"


def test_sintesis_sin_plan_no_pasa_a_aplicar():
    from src.graph import _ruta_tras_sintesis
    from langgraph.graph import END

    estado = {"plan": [], "respuesta": "Respuesta informativa"}

    assert _ruta_tras_sintesis(estado) == END


def test_sintesis_con_plan_pasa_a_aplicar():
    from src.graph import _ruta_tras_sintesis

    estado = {"plan": ["Revisar la información disponible"]}

    assert _ruta_tras_sintesis(estado) == "aplicar"


def test_supervisor_reserva_la_ultima_pasada_para_sintesis(monkeypatch):
    from src.graph import _ruta_supervisor_limitada

    def selector_que_no_debe_llamarse(estado):
        raise AssertionError(
            "No debe consultarse al selector en la última pasada"
        )

    monkeypatch.setattr(
        "src.graph._seleccionar_ruta",
        selector_que_no_debe_llamarse,
    )

    estado = {
        "pedido": "Organizar una visita",
        "notas": {},
        "pasos": config.MAX_ITER - 1,
        "pasos_especialista": {},
    }

    assert _ruta_supervisor_limitada(estado) == "sintetizar"
