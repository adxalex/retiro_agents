"""Pruebas unitarias de hora_actual.py."""

from datetime import datetime
import importlib

modulo = importlib.import_module("src.tools.hora_actual")


def test_hora_actual_parque_abierto_invierno(monkeypatch):
    class FixedDateTime:
        @classmethod
        def now(cls):
            return datetime(2025, 3, 4, 14, 30)

    monkeypatch.setattr(modulo, "datetime", FixedDateTime)

    assert modulo.hora_actual() == {
        "data": {
            "hora_madrid": "14:30",
            "estado_parque": "Abierto",
        },
        "error": None,
    }


def test_hora_actual_parque_cerrado_antes_apertura(monkeypatch):
    class FixedDateTime:
        @classmethod
        def now(cls):
            return datetime(2025, 3, 4, 5, 6)

    monkeypatch.setattr(modulo, "datetime", FixedDateTime)

    assert modulo.hora_actual() == {
        "data": {
            "hora_madrid": "05:06",
            "estado_parque": "Cerrado",
        },
        "error": None,
    }


def test_hora_actual_parque_cerrado_hora_cierre_invierno(monkeypatch):
    class FixedDateTime:
        @classmethod
        def now(cls):
            return datetime(2025, 3, 4, 22, 0)

    monkeypatch.setattr(modulo, "datetime", FixedDateTime)

    assert modulo.hora_actual() == {
        "data": {
            "hora_madrid": "22:00",
            "estado_parque": "Cerrado",
        },
        "error": None,
    }


def test_hora_actual_parque_abierto_verano(monkeypatch):
    class FixedDateTime:
        @classmethod
        def now(cls):
            return datetime(2025, 7, 15, 23, 30)

    monkeypatch.setattr(modulo, "datetime", FixedDateTime)

    assert modulo.hora_actual() == {
        "data": {
            "hora_madrid": "23:30",
            "estado_parque": "Abierto",
        },
        "error": None,
    }


def test_hora_actual_parque_cerrado_verano(monkeypatch):
    class FixedDateTime:
        @classmethod
        def now(cls):
            return datetime(2025, 7, 15, 0, 30)

    monkeypatch.setattr(modulo, "datetime", FixedDateTime)

    assert modulo.hora_actual() == {
        "data": {
            "hora_madrid": "00:30",
            "estado_parque": "Cerrado",
        },
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