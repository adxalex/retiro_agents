"""Pruebas unitarias de hora_actual.py."""
from datetime import datetime
import importlib

modulo = importlib.import_module("src.tools.hora_actual")


def test_hora_actual_returns_iso_timestamp(monkeypatch):
    class FixedDateTime:
        @classmethod
        def now(cls):
            return datetime(2025, 3, 4, 5, 6, 7)

    monkeypatch.setattr(modulo, "datetime", FixedDateTime)

    assert modulo.hora_actual() == {
        "data": "2025-03-04T05:06:07",
        "error": None,
    }


def test_hora_actual_returns_error_when_clock_fails(monkeypatch):
    class BrokenDateTime:
        @classmethod
        def now(cls):
            raise RuntimeError("clock unavailable")

    monkeypatch.setattr(modulo, "datetime", BrokenDateTime)

    assert modulo.hora_actual() == {
        "data": None,
        "error": "clock unavailable",
    }
