"""Tests de logging_utils.py: registro en JSONL, cronometro y resumen."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import logging_utils  # noqa: E402
from src.logging_utils import Cronometro, log_query, resumen_de_consultas  # noqa: E402


@pytest.fixture
def log_temporal(tmp_path, monkeypatch):
    """Redirige el fichero de registro a una carpeta temporal."""
    ruta = tmp_path / "output" / "consultas.jsonl"
    monkeypatch.setattr(logging_utils, "RUTA_LOG", ruta)
    return ruta


def leer(ruta: Path) -> list[dict]:
    return [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]


def test_escribe_una_linea_por_consulta(log_temporal):
    log_query("¿A que hora cierra?", k=3, n_chunks=3, tiempo=1.2, modelo="gemini")
    log_query("¿Y en verano?", k=5, n_chunks=5, tiempo=0.8, modelo="gemini")
    assert len(leer(log_temporal)) == 2


def test_el_registro_tiene_los_campos_esperados(log_temporal):
    log_query("pregunta", k=3, n_chunks=2, tiempo=1.234, modelo="gemini-2.5-flash")
    registro = leer(log_temporal)[0]
    assert {
        "timestamp",
        "pregunta",
        "top_k",
        "n_chunks",
        "tiempo_s",
        "modelo",
        "abstuvo",
    } <= set(registro)
    assert registro["top_k"] == 3
    assert registro["tiempo_s"] == 1.234
    assert registro["abstuvo"] is False


def test_guarda_los_campos_extra(log_temporal):
    log_query(
        "x", k=3, n_chunks=1, tiempo=0.5, modelo="m",
        abstuvo=True, motivo_abstencion="score_bajo", score_top1=0.11,
    )
    registro = leer(log_temporal)[0]
    assert registro["abstuvo"] is True
    assert registro["motivo_abstencion"] == "score_bajo"
    assert registro["score_top1"] == 0.11


def test_crea_la_carpeta_si_no_existe(log_temporal):
    assert not log_temporal.parent.exists()
    log_query("x", k=3, n_chunks=1, tiempo=0.1, modelo="m")
    assert log_temporal.exists()


def test_conserva_los_acentos(log_temporal):
    log_query("¿Dónde está el Palacio de Cristal?", k=3, n_chunks=1,
              tiempo=0.1, modelo="m")
    assert "¿Dónde está" in log_temporal.read_text(encoding="utf-8")


def test_un_fallo_de_escritura_no_rompe_la_consulta(tmp_path, monkeypatch):
    """Si el fichero no se puede escribir, log_query avisa pero no lanza."""
    ruta_imposible = tmp_path / "fichero.txt" / "consultas.jsonl"
    ruta_imposible.parent.write_text("soy un fichero, no una carpeta")
    monkeypatch.setattr(logging_utils, "RUTA_LOG", ruta_imposible)
    registro = log_query("x", k=3, n_chunks=1, tiempo=0.1, modelo="m")
    assert registro["pregunta"] == "x"


def test_cronometro_mide_el_tiempo():
    with Cronometro() as crono:
        time.sleep(0.05)
    assert crono.segundos >= 0.05


def test_resumen_de_un_fichero_inexistente(tmp_path):
    resumen = resumen_de_consultas(tmp_path / "no_existe.jsonl")
    assert resumen == {
        "total": 0,
        "abstenciones": 0,
        "tasa_abstencion": 0.0,
        "tiempo_medio_s": 0.0,
    }


def test_resumen_cuenta_abstenciones_y_tiempo_medio(log_temporal):
    log_query("a", k=3, n_chunks=3, tiempo=1.0, modelo="m")
    log_query("b", k=3, n_chunks=3, tiempo=2.0, modelo="m", abstuvo=True)
    log_query("c", k=3, n_chunks=3, tiempo=3.0, modelo="m", abstuvo=True)
    resumen = resumen_de_consultas(log_temporal)
    assert resumen["total"] == 3
    assert resumen["abstenciones"] == 2
    assert resumen["tasa_abstencion"] == pytest.approx(0.667, abs=0.001)
    assert resumen["tiempo_medio_s"] == pytest.approx(2.0)


def test_el_resumen_ignora_lineas_corruptas(log_temporal):
    log_query("a", k=3, n_chunks=1, tiempo=1.0, modelo="m")
    with log_temporal.open("a", encoding="utf-8") as fichero:
        fichero.write("esto no es json\n\n")
    assert resumen_de_consultas(log_temporal)["total"] == 1
