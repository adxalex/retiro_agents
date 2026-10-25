"""Pruebas unitarias de aemet_api.py."""
import pytest
from src.tools import aemet_api as api


class FakeResponse:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def test_configure_api_returns_key(monkeypatch):
    monkeypatch.setattr(api, "load_dotenv", lambda: None)
    monkeypatch.setenv("AEMET_API_KEY", "test-key")
    assert api._configure_api() == "test-key"


def test_configure_api_without_key_raises(monkeypatch):
    monkeypatch.setattr(api, "load_dotenv", lambda: None)
    monkeypatch.delenv("AEMET_API_KEY", raising=False)
    with pytest.raises(ValueError, match="AEMET_API_KEY"):
        api._configure_api()


def test_search_endpoint_requests_url_and_temporary_data(monkeypatch):
    monkeypatch.setattr(api, "_configure_api", lambda: "test-key")
    responses = [
        FakeResponse({"datos": "https://example.test/data"}),
        FakeResponse([{"temperatura": 20}]),
    ]
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(api.requests, "get", fake_get)
    result = api._search_endpoint("/observaciones/")

    assert result == [{"temperatura": 20}]
    assert calls[0][0] == f"{api.BASE_URL_AEMET}observaciones/"
    assert calls[0][1]["params"] == {"api_key": "test-key"}
    assert calls[0][1]["timeout"] == api.TIEMPO_MAXIMO
    assert calls[1][0] == "https://example.test/data"
    assert calls[1][1]["timeout"] == api.TIEMPO_MAXIMO


def test_search_endpoint_rejects_invalid_metadata_json(monkeypatch):
    monkeypatch.setattr(api, "_configure_api", lambda: "key")
    monkeypatch.setattr(api.requests, "get", lambda *a, **k: FakeResponse(ValueError("bad json")))
    with pytest.raises(ValueError, match="JSON invalida"):
        api._search_endpoint("endpoint")


def test_search_endpoint_rejects_missing_temporary_url(monkeypatch):
    monkeypatch.setattr(api, "_configure_api", lambda: "key")
    monkeypatch.setattr(api.requests, "get", lambda *a, **k: FakeResponse({}))
    with pytest.raises(ValueError, match="AEMET"):
        api._search_endpoint("endpoint")


def test_search_endpoint_rejects_non_list_data(monkeypatch):
    monkeypatch.setattr(api, "_configure_api", lambda: "key")
    responses = [FakeResponse({"datos": "https://example.test/data"}), FakeResponse({"value": 1})]
    monkeypatch.setattr(api.requests, "get", lambda *a, **k: responses.pop(0))
    with pytest.raises(ValueError, match="Formato de datos inesperado"):
        api._search_endpoint("endpoint")


@pytest.mark.parametrize(
    ("function_name", "endpoint_name", "empty_message", "format_message"),
    [
        ("_get_observaciones", "EP_OBSERVACIONES", "No se han devuelto observaciones", "observaciones no es válido"),
        ("_get_previsiones", "EP_PREVISIONES", "No se han devuelto previsiones", "previsiones no es válido"),
        ("_get_avisos", "EP_AVISOS", "No se han devuelto avisos", "avisos no es válido"),
    ],
)
def test_data_getters_validate_results(monkeypatch, function_name, endpoint_name, empty_message, format_message):
    monkeypatch.setattr(api, "_search_endpoint", lambda endpoint: [])
    with pytest.raises(ValueError, match=empty_message):
        getattr(api, function_name)()

    monkeypatch.setattr(api, "_search_endpoint", lambda endpoint: ["invalid"])
    with pytest.raises(ValueError, match=format_message):
        getattr(api, function_name)()

    expected = {"value": 1}
    monkeypatch.setattr(api, "_search_endpoint", lambda endpoint: [expected])
    assert getattr(api, function_name)() == expected


def test_fallback_requires_dictionary(monkeypatch, tmp_path):
    fallback = tmp_path / "fallback.json"
    fallback.write_text('{"temperatura": 18}', encoding="utf-8")
    monkeypatch.setattr(api, "FALLBACK_JSON", str(fallback))
    assert api._get_observaciones_fallback() == {"temperatura": 18}

    fallback.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match="debe contener un diccionario"):
        api._get_observaciones_fallback()


def test_api_dominio_returns_aemet_data(monkeypatch):
    observations = {"temperatura": 20}
    forecast = {"cielo": "despejado"}
    alerts = {"avisos": []}
    monkeypatch.setattr(api, "_get_observaciones", lambda: observations)
    monkeypatch.setattr(api, "_get_previsiones", lambda: forecast)
    monkeypatch.setattr(api, "_get_avisos", lambda: alerts)

    result = api.api_dominio()

    assert result == {
        "data": {
            "observaciones": observations,
            "previsiones": forecast,
            "avisos": alerts,
            "origen": "aemet",
        },
        "error": None,
    }


def test_api_dominio_uses_fallback_when_observations_fail(monkeypatch):
    fallback = {"temperatura": 17}
    monkeypatch.setattr(api, "_get_observaciones", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    monkeypatch.setattr(api, "_get_observaciones_fallback", lambda: fallback)

    result = api.api_dominio()

    assert result["data"]["observaciones"] == fallback
    assert result["data"]["origen"] == "respaldo"
    assert result["data"]["previsiones"] is None
    assert result["data"]["avisos"] is None
    assert result["error"] is None


def test_api_dominio_keeps_observations_if_forecast_or_alerts_fail(monkeypatch):
    monkeypatch.setattr(api, "_get_observaciones", lambda: {"temperatura": 20})
    monkeypatch.setattr(api, "_get_previsiones", lambda: (_ for _ in ()).throw(RuntimeError("forecast error")))
    monkeypatch.setattr(api, "_get_avisos", lambda: {"avisos": []})

    result = api.api_dominio()

    assert result["data"]["observaciones"] == {"temperatura": 20}
    assert result["data"]["previsiones"] is None
    assert result["data"]["avisos"] == {"avisos": []}
    assert result["error"] is None


def test_api_dominio_reports_fallback_failure(monkeypatch):
    monkeypatch.setattr(api, "_get_observaciones", lambda: (_ for _ in ()).throw(RuntimeError("API down")))
    monkeypatch.setattr(api, "_get_observaciones_fallback", lambda: (_ for _ in ()).throw(OSError("file missing")))

    result = api.api_dominio()

    assert result["data"]["observaciones"] is None
    assert result["data"]["origen"] is None
    assert "Error en el fallback" in result["error"]
    assert "file missing" in result["error"]
