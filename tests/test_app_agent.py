"""Tests de la app Streamlit del agente (sin API)."""
import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RUTA_APP = RAIZ / "app_agent.py"
RUTA_UI = RAIZ / "src" / "ui_agente.py"

FUNCIONES_AGENTE = {"procesar_turno", "aprobar_plan"}
MODULOS_PROHIBIDOS = {"src.graph", "src.tools", "src.state"}


def _arbol(ruta: Path) -> ast.Module:
    return ast.parse(ruta.read_text(encoding="utf-8"))


def _importados(arbol: ast.Module) -> set[str]:
    """Nombres completos importados: módulos y 'modulo.nombre'."""
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            nombres.add(modulo)
            nombres.update(f"{modulo}.{alias.name}" for alias in nodo.names)
    return nombres


def _es_prohibido(nombre: str) -> bool:
    raiz = nombre.split(".")[0]
    return (
        raiz in {"langgraph", "google"}
        or raiz.startswith("langchain")
        or any(nombre == m or nombre.startswith(m + ".") for m in MODULOS_PROHIBIDOS)
    )


def test_capas_sin_logica_de_grafo():
    for ruta in (RUTA_APP, RUTA_UI):
        importados = _importados(_arbol(ruta))
        assert not [n for n in importados if _es_prohibido(n)], ruta.name

    # La lógica pura no conoce al agente: lo recibe inyectado.
    assert not [n for n in _importados(_arbol(RUTA_UI)) if n.startswith("src.agent")]

    # La app solo usa las dos funciones públicas, por atributo.
    arbol_app = _arbol(RUTA_APP)
    importados_app = _importados(arbol_app)
    assert "src.agent" in importados_app
    assert not [n for n in importados_app
                if n.startswith("src.agent.") and n.split(".")[-1] not in FUNCIONES_AGENTE]
    usos = {
        nodo.attr for nodo in ast.walk(arbol_app)
        if isinstance(nodo, ast.Attribute)
        and isinstance(nodo.value, ast.Name) and nodo.value.id == "agent"
    }
    assert usos == FUNCIONES_AGENTE

    # La app no lee variables de entorno ni .env.
    assert not [n for n in importados_app if n.split(".")[0] in {"os", "dotenv"}]
    nombres_app = {
        nodo.attr if isinstance(nodo, ast.Attribute) else nodo.id
        for nodo in ast.walk(arbol_app)
        if isinstance(nodo, (ast.Attribute, ast.Name))
    }
    assert not nombres_app & {"environ", "getenv", "load_dotenv"}
