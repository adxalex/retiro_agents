"""Compara configuraciones de chunking sobre el mismo conjunto documental."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from src.chunk import chunk_documents


def parse_configuration(value: str) -> tuple[int, int]:
    """Convierte una configuración SIZE:OVERLAP en dos enteros."""
    try:
        chunk_size_text, overlap_text = value.split(":", maxsplit=1)
        chunk_size = int(chunk_size_text)
        chunk_overlap = int(overlap_text)
    except (ValueError, AttributeError) as exc:
        raise argparse.ArgumentTypeError(
            "La configuración debe tener el formato SIZE:OVERLAP, por ejemplo 500:50."
        ) from exc

    if chunk_size <= 0:
        raise argparse.ArgumentTypeError("SIZE debe ser mayor que cero.")

    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise argparse.ArgumentTypeError(
            "OVERLAP debe ser mayor o igual que cero y menor que SIZE."
        )

    return chunk_size, chunk_overlap


def load_documents(input_path: Path) -> list[dict[str, Any]]:
    """Carga y valida superficialmente el JSON de documentos."""
    if not input_path.is_file():
        raise FileNotFoundError(
            f"No existe el archivo de entrada: {input_path}")

    with input_path.open("r", encoding="utf-8-sig") as file:
        payload = json.load(file)

    if isinstance(payload, list):
        documents = payload
    elif isinstance(payload, dict) and isinstance(payload.get("documents"), list):
        documents = payload["documents"]
    else:
        raise ValueError(
            "El JSON debe ser una lista o un objeto con la clave 'documents'."
        )

    if not documents:
        raise ValueError("El archivo de entrada no contiene documentos.")

    if not all(isinstance(document, dict) for document in documents):
        raise TypeError("Todos los documentos deben ser objetos JSON.")

    return documents


def percentile_95(lengths: list[int]) -> float:
    """Calcula un percentil 95 sencillo mediante rango más cercano."""
    if not lengths:
        return 0.0

    ordered = sorted(lengths)
    index = max(0, round(0.95 * len(ordered) + 0.5) - 1)
    return float(ordered[min(index, len(ordered) - 1)])


def summarize_chunks(
    chunks: list[dict[str, Any]],
    chunk_size: int,
    chunk_overlap: int,
) -> dict[str, Any]:
    """Genera métricas estructurales de una ejecución de chunking."""
    lengths = [len(chunk["text"]) for chunk in chunks]
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    texts = [chunk["text"] for chunk in chunks]

    chunks_by_document = Counter(
        str(chunk["document_id"]) for chunk in chunks
    )
    chunks_by_category = Counter(
        str(chunk["category"]) for chunk in chunks
    )

    duplicate_ids = sum(
        count - 1 for count in Counter(chunk_ids).values() if count > 1
    )
    repeated_texts = sum(
        count - 1 for count in Counter(texts).values() if count > 1
    )

    return {
        "configuration": {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        },
        "total_chunks": len(chunks),
        "unique_chunk_ids": len(set(chunk_ids)),
        "duplicate_chunk_ids": duplicate_ids,
        "exact_repeated_texts": repeated_texts,
        "length_characters": {
            "minimum": min(lengths) if lengths else 0,
            "mean": round(statistics.fmean(lengths), 2) if lengths else 0.0,
            "median": round(statistics.median(lengths), 2) if lengths else 0.0,
            "p95": percentile_95(lengths),
            "maximum": max(lengths) if lengths else 0,
        },
        "chunks_by_document": dict(sorted(chunks_by_document.items())),
        "chunks_by_category": dict(sorted(chunks_by_category.items())),
    }


def compare_configurations(
    documents: list[dict[str, Any]],
    configurations: list[tuple[int, int]],
) -> dict[str, Any]:
    """Ejecuta todas las configuraciones sobre los mismos documentos."""
    results = []

    for chunk_size, chunk_overlap in configurations:
        chunks = chunk_documents(
            documents,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        results.append(
            summarize_chunks(
                chunks,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )

    return {
        "experiment": "chunking_configuration_comparison",
        "input_documents": len(documents),
        "configurations_compared": len(configurations),
        "results": results,
        "interpretation": (
            "Estas métricas describen la segmentación. La configuración final "
            "debe decidirse también mediante pruebas de retrieval."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    """Define los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Compara varias configuraciones de chunking."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="JSON con los documentos cargados.",
    )
    parser.add_argument(
        "--config",
        action="append",
        type=parse_configuration,
        dest="configurations",
        help="Configuración SIZE:OVERLAP. Puede repetirse.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Ruta del informe JSON resultante.",
    )
    return parser


def main() -> None:
    """Ejecuta el experimento y guarda sus resultados."""
    parser = build_parser()
    arguments = parser.parse_args()

    configurations = arguments.configurations or [(500, 50), (800, 100)]
    documents = load_documents(arguments.input)
    report = compare_configurations(documents, configurations)

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Documentos analizados: {report['input_documents']}")
    print(f"Configuraciones comparadas: {report['configurations_compared']}")

    for result in report["results"]:
        configuration = result["configuration"]
        print(
            f"- {configuration['chunk_size']}:{configuration['chunk_overlap']} "
            f"-> {result['total_chunks']} chunks"
        )

    print(f"Informe guardado en: {arguments.output}")


if __name__ == "__main__":
    main()
