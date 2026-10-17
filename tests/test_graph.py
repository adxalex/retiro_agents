
from src.graph import build_graph


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
