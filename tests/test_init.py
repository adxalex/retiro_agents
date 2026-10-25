"""Pruebas unitarias de las herramientas registradas en src.tools."""

from pathlib import Path

import pytest
import src.tools as modulo


def test_args_validation_without_args_uses_empty_dict():
    assert modulo.args_validation("api_dominio") == {}
    assert modulo.args_validation("hora_actual") == {}


def test_args_validation_rejects_non_dict_args():
    with pytest.raises(TypeError, match="args debe ser un diccionario"):
        modulo.args_validation("hora_actual", "no es un diccionario")


def test_args_validation_api_dominio_ignores_args():
    assert modulo.args_validation("api_dominio", {"extra": "valor"}) == {}


def test_args_validation_rag_ask_strips_question():
    assert modulo.args_validation("rag_ask", {"pregunta": "  ¿Dónde está el parque?  "}) == {
        "pregunta": "¿Dónde está el parque?"
    }


def test_args_validation_rag_ask_handles_missing_or_empty_question():
    assert modulo.args_validation("rag_ask", {}) == {"pregunta": ""}
    assert modulo.args_validation("rag_ask", {"pregunta": None}) == {"pregunta": ""}


def test_args_validation_rag_ask_converts_question_to_string():
    assert modulo.args_validation("rag_ask", {"pregunta": 123}) == {"pregunta": "123"}


def test_args_validation_unknown_tool_raises_value_error():
    with pytest.raises(ValueError, match="No hay validación definida"):
        modulo.args_validation("herramienta_desconocida", {})


def test_args_validation_image_uses_default_file_when_image_is_missing(monkeypatch, tmp_path):
    image_path = tmp_path / "imagen.png"
    image_path.write_bytes(b"imagen-de-prueba")
    monkeypatch.setattr(modulo, "IMAGE_DEFAULT_PATH", image_path)

    assert modulo.args_validation("describir_imagen", {}) == {
        "imagen": {"bytes": b"imagen-de-prueba", "mime": "image/png"}
    }


@pytest.mark.parametrize(
    ("filename", "expected_mime"),
    [("imagen.png", "image/png"), ("imagen.jpg", "image/jpeg")],
)
def test_args_validation_image_selects_mime_from_default_extension(
    monkeypatch, tmp_path, filename, expected_mime
):
    image_path = tmp_path / filename
    image_path.write_bytes(b"imagen")
    monkeypatch.setattr(modulo, "IMAGE_DEFAULT_PATH", image_path)

    result = modulo.args_validation("describir_imagen", {"imagen": "ruta no válida"})

    assert result == {"imagen": {"bytes": b"imagen", "mime": expected_mime}}


def test_args_validation_image_keeps_valid_image(monkeypatch, tmp_path):
    image_path = tmp_path / "predeterminada.png"
    image_path.write_bytes(b"imagen-predeterminada")
    monkeypatch.setattr(modulo, "IMAGE_DEFAULT_PATH", image_path)

    result = modulo.args_validation(
        "describir_imagen",
        {"imagen": {"bytes": b"imagen-proporcionada", "mime": "image/jpeg"}},
    )

    assert result == {
        "imagen": {"bytes": b"imagen-proporcionada", "mime": "image/jpeg"}
    }


@pytest.mark.parametrize(
    "imagen",
    [
        {"bytes": b"", "mime": "image/png"},
        {"bytes": "no son bytes", "mime": "image/png"},
        {"bytes": b"imagen", "mime": "image/gif"},
        {"mime": "image/png"},
    ],
)
def test_args_validation_image_falls_back_when_image_is_invalid(
    monkeypatch, tmp_path, imagen
):
    image_path = tmp_path / "predeterminada.jpg"
    image_path.write_bytes(b"imagen-fallback")
    monkeypatch.setattr(modulo, "IMAGE_DEFAULT_PATH", image_path)

    result = modulo.args_validation("describir_imagen", {"imagen": imagen})

    assert result == {
        "imagen": {"bytes": b"imagen-fallback", "mime": "image/jpeg"}
    }


def test_ejecutar_tool_blocks_unknown_tool():
    result = modulo.ejecutar_tool("no_existe", {})

    assert result["tool"] == "no_existe"
    assert result["status"] == "blocked"
    assert result["data"] is None
    assert result["traza"]["status"] == "blocked"
    assert result["traza"]["nombre"] == "no_existe"


def test_ejecutar_tool_returns_success_and_trace(monkeypatch):
    monkeypatch.setitem(
        modulo.TOOL_REGISTRY,
        "hora_actual",
        lambda args: {"data": {"hora_madrid": "12:30"}, "error": None},
    )

    result = modulo.ejecutar_tool("hora_actual", {"ignorado": True})

    assert result["tool"] == "hora_actual"
    assert result["status"] == "ok"
    assert result["data"] == {"hora_madrid": "12:30"}
    assert result["error"] is None
    assert result["traza"]["status"] == "ok"
    assert result["traza"]["args"] == {}
    assert result["traza"]["preview"] == "{'hora_madrid': '12:30'}"
    assert result["traza"]["origen"] == "tool"


def test_ejecutar_tool_returns_error_when_tool_reports_error(monkeypatch):
    monkeypatch.setitem(
        modulo.TOOL_REGISTRY,
        "hora_actual",
        lambda args: {"data": None, "error": "fallo de prueba"},
    )

    result = modulo.ejecutar_tool("hora_actual", {})

    assert result["status"] == "error"
    assert result["data"] is None
    assert result["error"] == "fallo de prueba"
    assert result["traza"]["status"] == "error"
    assert result["traza"]["preview"] == "fallo de prueba"


def test_ejecutar_tool_rejects_non_dict_response(monkeypatch):
    monkeypatch.setitem(modulo.TOOL_REGISTRY, "hora_actual", lambda args: "respuesta inválida")

    result = modulo.ejecutar_tool("hora_actual", {})

    assert result["status"] == "error"
    assert result["error"] == (
        "Error al ejecutar la tool: La herramienta debe devolver un diccionario"
    )
    assert result["traza"]["status"] == "error"


@pytest.mark.parametrize(
    "response",
    [
        {"data": "sin campo error"},
        {"error": None},
    ],
)
def test_ejecutar_tool_rejects_response_missing_required_fields(monkeypatch, response):
    monkeypatch.setitem(modulo.TOOL_REGISTRY, "hora_actual", lambda args: response)

    result = modulo.ejecutar_tool("hora_actual", {})

    assert result["status"] == "error"
    assert result["error"] == (
        "Error al ejecutar la tool: La respuesta debe contener 'error' y 'data'"
    )
    assert result["traza"]["status"] == "error"


def test_ejecutar_tool_catches_exception_from_validation_or_tool(monkeypatch):
    def raise_error(args):
        raise RuntimeError("error inesperado")

    monkeypatch.setitem(modulo.TOOL_REGISTRY, "hora_actual", raise_error)

    result = modulo.ejecutar_tool("hora_actual", {})

    assert result["status"] == "error"
    assert result["error"] == "Error al ejecutar la tool: error inesperado"
    assert result["traza"]["status"] == "error"
    assert result["traza"]["preview"] == result["error"]


def test_ejecutar_tool_limits_trace_preview_to_200_characters(monkeypatch):
    long_text = "x" * 250
    monkeypatch.setitem(
        modulo.TOOL_REGISTRY,
        "hora_actual",
        lambda args: {"data": long_text, "error": None},
    )

    result = modulo.ejecutar_tool("hora_actual", {})

    assert result["status"] == "ok"
    assert result["traza"]["preview"] == long_text[:200]
    assert len(result["traza"]["preview"]) == 200
