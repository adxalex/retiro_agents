"""Interfaz de terminal para construir el índice del corpus."""

from __future__ import annotations

import argparse
import json
from typing import Any

from config import DATA_DIR
from src.pipeline import build_index


def parse_args() -> argparse.Namespace:
    """Define los argumentos del comando."""
    parser = argparse.ArgumentParser(
        description="Construye el índice Chroma del corpus completo.",
    )
    parser.add_argument(
        "--data-dir",
        default=DATA_DIR,
        help="Directorio raíz del corpus.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida load y chunk sin llamar a Gemini ni Chroma.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Conserva la colección y realiza upsert sin reconstruirla.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Muestra el resumen en formato JSON.",
    )
    return parser.parse_args()


def print_report(report: dict[str, Any], as_json: bool = False) -> None:
    """Presenta el resultado sin añadir lógica al pipeline."""
    if as_json:
        print(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print(f"Documentos cargados: {report['documents']}")
    print(f"Fuentes diferentes: {report['sources']}")
    print(f"Chunks generados: {report['chunks']}")

    print("\nChunks por corpus_group:")
    for group, count in report["chunks_by_group"].items():
        print(f"  {group}: {count}")

    if report["indexed"]:
        print(
            "\nIndexación completada. "
            f"Registros en Chroma: {report['collection_count']}"
        )
    else:
        print("\nDry run completado: Gemini y Chroma no fueron utilizados.")


def main() -> None:
    """Ejecuta el comando solicitado."""
    arguments = parse_args()

    report = build_index(
        data_dir=arguments.data_dir,
        recreate=not arguments.keep_existing,
        dry_run=arguments.dry_run,
    )

    print_report(report, as_json=arguments.json)


if __name__ == "__main__":
    main()