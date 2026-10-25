"""Pruebas unitarias de image_decrip.py."""
import pytest
from src.tools import image_decrip as modulo


def test_configure_api_returns_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert modulo.configure_api() == "test-key"


def test_configure_api_without_key_raises(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        modulo.configure_api()


def test_describir_imagen_reports_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = modulo.describir_imagen({"imagen": {"bytes": b"image", "mime": "image/png"}})

    assert result == {"data": None, "error": "Error: falta GEMINI_API_KEY"}


def test_describir_imagen_returns_model_description(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeModels:
        def generate_content(self, **kwargs):
            return type("Output", (), {"text": "  Un cartel del parque.  "})()

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-key"
            self.models = FakeModels()

    monkeypatch.setattr(modulo.genai, "Client", FakeClient)
    result = modulo.describir_imagen({"imagen": {"bytes": b"fake-image", "mime": "image/png"}})

    assert result == {"data": "Un cartel del parque.", "error": None}


def test_describir_imagen_handles_empty_model_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeModels:
        def generate_content(self, **kwargs):
            return type("Output", (), {"text": "  "})()

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr(modulo.genai, "Client", FakeClient)
    result = modulo.describir_imagen({"imagen": {"bytes": b"fake-image", "mime": "image/png"}})

    assert result == {"data": None, "error": "Error: respuesta vacía del modelo."}


def test_describir_imagen_handles_model_exception(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("service unavailable")

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr(modulo.genai, "Client", FakeClient)
    result = modulo.describir_imagen({"imagen": {"bytes": b"fake-image", "mime": "image/png"}})

    assert result["data"] is None
    assert "Error al leer la imagen: service unavailable" == result["error"]


def test_describir_imagen_handles_missing_image_argument(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    result = modulo.describir_imagen({})

    assert result["data"] is None
    assert result["error"] is not None
    assert "Error al leer la imagen" in result["error"]
