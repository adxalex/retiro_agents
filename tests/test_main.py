"""Tests de la CLI: --query, --ask, argumentos y codigos de salida.

No llaman a Gemini ni a ChromaDB: se sustituyen retrieve y responder.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main as cli  # noqa: E402


def chunk(score=0.82, source="guia.pdf", texto="El parque abre de 6:00 a 22:00."):
    return {
        "chunk_id": "guia__0000",
        "document_id": "guia",
        "text": texto,
        "source": source,
        "chunk_index": 0,
        "category": "informacion_practica",
        "corpus_group": "itinerarios_informacion_practica_seguridad",
        "page": 1,
        "score": score,
    }


def salida_respondida(chunks=None):
    chunks = chunks or [chunk()]
    return {
        "respuesta": "El parque abre de 6:00 a 22:00 [1].",
        "fuentes": ["guia.pdf"],
        "chunks": chunks,
        "abstuvo": False,
        "motivo_abstencion": None,
    }


def salida_abstenida():
    return {
        "respuesta": "No he encontrado esa informacion.",
        "fuentes": [],
        "chunks": [chunk(0.05)],
        "abstuvo": True,
        "motivo_abstencion": "score_bajo (0.050 < 0.300)",
    }


@pytest.fixture
def retrieve_falso(monkeypatch):
    """Sustituye src.retrieve.retrieve y guarda los argumentos recibidos."""
    llamadas = {}

    def _falso(query, top_k=3, collection=None, client=None, where=None):
        llamadas.update(query=query, top_k=top_k, where=where)
        return llamadas.get("devolver", [chunk()])

    import src.retrieve
    monkeypatch.setattr(src.retrieve, "retrieve", _falso)
    return llamadas


@pytest.fixture
def responder_falso(monkeypatch):
    """Sustituye src.generate.responder y guarda los argumentos recibidos."""
    llamadas = {"devolver": salida_respondida()}

    def _falso(pregunta, top_k=3, score_minimo=None, collection=None,
               client=None, where=None):
        llamadas.update(pregunta=pregunta, top_k=top_k,
                        score_minimo=score_minimo, where=where)
        return llamadas["devolver"]

    import src.generate
    monkeypatch.setattr(src.generate, "responder", _falso)
    return llamadas


# --- --query ---------------------------------------------------------------


def test_query_muestra_los_fragmentos(retrieve_falso, capsys):
    assert cli.cmd_query("¿A que hora cierra?") == 0
    salida = capsys.readouterr().out
    assert "El parque abre de 6:00 a 22:00." in salida
    assert "score 0.820" in salida
    assert "guia.pdf" in salida


def test_query_sin_resultados_avisa_y_devuelve_error(retrieve_falso, capsys):
    retrieve_falso["devolver"] = []
    assert cli.cmd_query("x") == 1
    assert "indice" in capsys.readouterr().out.lower()


def test_query_pasa_top_k_y_categoria(retrieve_falso):
    cli.cmd_query("x", top_k=5, category="seguridad")
    assert retrieve_falso["top_k"] == 5
    assert retrieve_falso["where"] == {"category": "seguridad"}


def test_query_sin_categoria_no_manda_filtro(retrieve_falso):
    cli.cmd_query("x")
    assert retrieve_falso["where"] is None


def test_query_en_json_es_json_valido(retrieve_falso, capsys):
    cli.cmd_query("x", como_json=True)
    datos = json.loads(capsys.readouterr().out)
    assert datos[0]["chunk_id"] == "guia__0000"


# --- --ask -----------------------------------------------------------------


def test_ask_muestra_respuesta_y_fuentes(responder_falso, capsys):
    assert cli.cmd_ask("¿A que hora cierra?") == 0
    salida = capsys.readouterr().out
    assert "El parque abre de 6:00 a 22:00 [1]." in salida
    assert "Fuentes:" in salida
    assert "guia.pdf" in salida


def test_ask_con_abstencion_muestra_el_motivo(responder_falso, capsys):
    responder_falso["devolver"] = salida_abstenida()
    assert cli.cmd_ask("x") == 0
    salida = capsys.readouterr().out
    assert "abstencion" in salida
    assert "score_bajo" in salida
    assert "Fuentes:" not in salida


def test_ask_pasa_todos_los_argumentos(responder_falso):
    cli.cmd_ask("x", top_k=5, category="historia", score_minimo=0.4)
    assert responder_falso["top_k"] == 5
    assert responder_falso["where"] == {"category": "historia"}
    assert responder_falso["score_minimo"] == 0.4


def test_ask_con_contexto_muestra_los_fragmentos(responder_falso, capsys):
    cli.cmd_ask("x", mostrar_contexto=True)
    assert "Contexto recuperado" in capsys.readouterr().out


def test_ask_sin_contexto_no_los_muestra(responder_falso, capsys):
    cli.cmd_ask("x")
    assert "Contexto recuperado" not in capsys.readouterr().out


def test_ask_en_json_incluye_la_abstencion(responder_falso, capsys):
    responder_falso["devolver"] = salida_abstenida()
    cli.cmd_ask("x", como_json=True)
    datos = json.loads(capsys.readouterr().out)
    assert datos["abstuvo"] is True


# --- argumentos ------------------------------------------------------------


def test_sin_argumentos_muestra_la_ayuda(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py"])
    assert cli.main() == 0
    assert "usage" in capsys.readouterr().out


def test_top_k_invalido_es_error(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--ask", "x", "--top-k", "0"])
    with pytest.raises(SystemExit) as salida:
        cli.main()
    assert salida.value.code == 2


def test_main_enruta_a_ask(monkeypatch, responder_falso, capsys):
    monkeypatch.setattr(
        sys, "argv", ["main.py", "--ask", "¿A que hora cierra?"])
    assert cli.main() == 0
    assert "Pregunta:" in capsys.readouterr().out


def test_main_enruta_a_query(monkeypatch, retrieve_falso, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "--query", "x"])
    assert cli.main() == 0
    assert "Fragmentos recuperados" in capsys.readouterr().out


def test_un_error_no_muestra_traza(monkeypatch, capsys):
    import src.generate

    def _explota(*_args, **_kwargs):
        raise RuntimeError("No se ha definido GEMINI_API_KEY.")

    monkeypatch.setattr(src.generate, "responder", _explota)
    monkeypatch.setattr(sys, "argv", ["main.py", "--ask", "x"])
    assert cli.main() == 1
    error = capsys.readouterr().err
    assert "GEMINI_API_KEY" in error
    assert "Traceback" not in error


def test_index_conecta_con_pipeline(monkeypatch, capsys):
    """Comprueba que --index utiliza el pipeline sin servicios externos."""
    import src.pipeline

    received = {}

    def fake_build_index(*, recreate, dry_run=False):
        received["recreate"] = recreate
        received["dry_run"] = dry_run
        return {
            "documents": 255,
            "sources": 17,
            "chunks": 1177,
            "chunks_by_group": {},
            "indexed": True,
            "collection_count": 1177,
        }

    monkeypatch.setattr(src.pipeline, "build_index", fake_build_index)

    assert cli.cmd_index(recreate=True) == 0
    assert received["recreate"] is True

    output = capsys.readouterr().out
    assert "Indexacion completada" in output
    assert "1177" in output


def test_index_no_recrea_la_coleccion_por_defecto(monkeypatch, capsys):
    """Sin flags, --index hace upsert: NUNCA borra la coleccion.

    Reconstruir el indice consume cuota de la API y descarta horas de trabajo,
    asi que debe pedirse a proposito con --recreate-index.
    """
    import src.pipeline

    recibidos = {}

    def _falso(data_dir=None, recreate=False, dry_run=False):
        recibidos.update(recreate=recreate, dry_run=dry_run)
        return {
            "documents": 255,
            "sources": 17,
            "chunks": 1177,
            "chunks_by_group": {"historia_monumentos_jardines": 34},
            "indexed": True,
            "collection_count": 1177,
        }

    monkeypatch.setattr(src.pipeline, "build_index", _falso)
    monkeypatch.setattr(sys, "argv", ["main.py", "--index"])
    assert cli.main() == 0
    assert recibidos["recreate"] is False, "El default debe ser seguro."
    assert recibidos["dry_run"] is False
    assert "Upsert" in capsys.readouterr().out


def test_recreate_index_solo_cuando_se_pide(monkeypatch, capsys):
    import src.pipeline

    recibidos = {}

    def _falso(data_dir=None, recreate=False, dry_run=False):
        recibidos.update(recreate=recreate)
        return {"documents": 255, "sources": 17, "chunks": 1177,
                "chunks_by_group": {}, "indexed": True, "collection_count": 1177}

    monkeypatch.setattr(src.pipeline, "build_index", _falso)
    monkeypatch.setattr(sys, "argv", ["main.py", "--index", "--recreate-index"])
    assert cli.main() == 0
    assert recibidos["recreate"] is True
    assert "recreada" in capsys.readouterr().out


def test_index_con_dry_run_no_indexa(monkeypatch, capsys):
    import src.pipeline

    monkeypatch.setattr(src.pipeline, "build_index", lambda **kwargs: {
        "documents": 255, "sources": 17, "chunks": 1177,
        "chunks_by_group": {}, "indexed": False, "collection_count": 0,
    })
    monkeypatch.setattr(sys, "argv", ["main.py", "--index", "--dry-run"])
    assert cli.main() == 0
    assert "No se ha llamado a Gemini" in capsys.readouterr().out


def test_coleccion_inexistente_explica_como_indexar(monkeypatch, capsys):
    """Si el indice no existe, la CLI dice como construirlo."""
    import src.retrieve

    def _explota(*_args, **_kwargs):
        raise ValueError("Collection [retiro_madrid] does not exist")

    monkeypatch.setattr(src.retrieve, "retrieve", _explota)
    monkeypatch.setattr(sys, "argv", ["main.py", "--query", "x"])
    assert cli.main() == 1
    error = capsys.readouterr().err
    assert "--index" in error
    assert "Traceback" not in error
