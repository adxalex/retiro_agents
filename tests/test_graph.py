
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
