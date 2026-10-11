"""Configuracion comun de las pruebas.

Los tests llaman a responder(), que registra cada consulta en
output/consultas.jsonl. Sin esta proteccion, una ejecucion de la suite deja
cientos de entradas falsas en el registro real y las metricas del informe
quedan inservibles: se midio un tiempo medio de 0,465 s cuando una consulta
real tarda entre 6 y 15 s.

Esta fixture redirige el registro a un fichero temporal en todas las pruebas.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def log_aislado(tmp_path, monkeypatch):
    """Ninguna prueba debe escribir en el registro real de consultas."""
    from src import logging_utils

    monkeypatch.setattr(
        logging_utils, "RUTA_LOG", tmp_path / "consultas_de_prueba.jsonl"
    )
