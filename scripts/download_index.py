"""Descarga e instala el índice Chroma preconstruido del MVP."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from config import CHROMA_DIR

INDEX_URL = os.getenv(
    "RETIRO_INDEX_URL",
    "https://github.com/adxalex/retiro_rag/releases/download/"
    "index-v1/chroma_retiro_madrid.zip"
)

# Sustituir por el SHA-256 real de chroma_retiro_madrid.zip.
INDEX_SHA256 = "176c11459f4d681da77b92b5b62daabefb85c628d612d19da099755f2143a882"


def calcular_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)

    return digest.hexdigest()


def _extraer_seguro(zip_path: Path, destino: Path) -> None:
    """Extrae el ZIP rechazando rutas que escapen del directorio destino."""
    destino_resuelto = destino.resolve()

    with zipfile.ZipFile(zip_path) as archivo:
        for miembro in archivo.infolist():
            ruta = (destino / miembro.filename).resolve()

            if destino_resuelto not in ruta.parents and ruta != destino_resuelto:
                raise ValueError(
                    f"Ruta no segura dentro del ZIP: {miembro.filename}"
                )

        archivo.extractall(destino)


def instalar_indice(
    *,
    url: str = INDEX_URL,
    destino: Path | None = None,
    sha256_esperado: str = INDEX_SHA256,
    force: bool = False,
) -> Path:
    destino = destino or Path(CHROMA_DIR)

    if destino.exists():
        if not force:
            raise FileExistsError(
                f"El índice ya existe en '{destino}'. "
                "No se sobrescribe automáticamente."
            )

        shutil.rmtree(destino)

    with tempfile.TemporaryDirectory() as temporal:
        zip_path = Path(temporal) / "chroma_retiro_madrid.zip"

        print("Descargando índice Chroma preconstruido...")
        urllib.request.urlretrieve(url, zip_path)

        sha256_real = calcular_sha256(zip_path)

        if sha256_real.lower() != sha256_esperado.lower():
            raise ValueError(
                "El SHA-256 del índice descargado no coincide.\n"
                f"Esperado: {sha256_esperado}\n"
                f"Recibido: {sha256_real}"
            )

        destino.mkdir(parents=True, exist_ok=False)
        _extraer_seguro(zip_path, destino)

    print(f"Índice instalado correctamente en: {destino}")
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Descarga el índice Chroma preconstruido del Retiro RAG."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sustituye un directorio de índice existente.",
    )

    args = parser.parse_args()

    try:
        instalar_indice(force=args.force)
    except Exception as error:  # noqa: BLE001
        print(f"Error: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
