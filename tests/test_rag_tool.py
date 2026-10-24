"""Pruebas unitarias de rag_tool.py."""
from src.tools import rag_tool as modulo


def test_rag_ask_returns_responder_result(monkeypatch):
    expected = "El Retiro se inauguró en el siglo XVII."
    received = {}

    def fake_responder(pregunta):
        received["pregunta"] = pregunta
        return expected

    monkeypatch.setattr(modulo, "responder", fake_responder)

    result = modulo.rag_ask({"pregunta": "¿Cuál es la historia del Retiro?"})

    assert received["pregunta"] == "¿Cuál es la historia del Retiro?"
    assert result == {"data": expected, "error": None}


def test_rag_ask_returns_error_when_responder_fails(monkeypatch):
    def fake_responder(pregunta):
        raise RuntimeError("fallo del generador")

    monkeypatch.setattr(modulo, "responder", fake_responder)

    assert modulo.rag_ask({"pregunta": "Pregunta de prueba"}) == {
        "data": None,
        "error": "fallo del generador",
    }


def test_rag_ask_passes_none_when_question_is_missing(monkeypatch):
    received = {}

    def fake_responder(pregunta):
        received["pregunta"] = pregunta
        return "respuesta"

    monkeypatch.setattr(modulo, "responder", fake_responder)

    result = modulo.rag_ask({})

    assert received["pregunta"] is None
    assert result == {"data": "respuesta", "error": None}
