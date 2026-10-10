from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.download_index import (  # noqa: E402
    _extraer_seguro,
    calcular_sha256,
)


def test_calcular_sha256(tmp_path):
    archivo = tmp_path / "datos.bin"
    archivo.write_bytes(b"retiro")

    esperado = hashlib.sha256(b"retiro").hexdigest()

    assert calcular_sha256(archivo) == esperado


def test_extraer_zip_valido(tmp_path):
    zip_path = tmp_path / "indice.zip"
    destino = tmp_path / "chroma"

    with zipfile.ZipFile(zip_path, "w") as archivo:
        archivo.writestr("chroma.sqlite3", b"db")
        archivo.writestr("segmento/data.bin", b"vector")

    destino.mkdir()
    _extraer_seguro(zip_path, destino)

    assert (destino / "chroma.sqlite3").exists()
    assert (destino / "segmento" / "data.bin").exists()


def test_rechaza_path_traversal(tmp_path):
    zip_path = tmp_path / "indice.zip"
    destino = tmp_path / "chroma"

    with zipfile.ZipFile(zip_path, "w") as archivo:
        archivo.writestr("../fuera.txt", b"no")

    destino.mkdir()

    with pytest.raises(ValueError, match="Ruta no segura"):
        _extraer_seguro(zip_path, destino)