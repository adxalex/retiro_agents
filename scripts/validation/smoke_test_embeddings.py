"""Prueba manual de embeddings reales con más de un lote."""

from __future__ import annotations

import argparse
import math
from copy import deepcopy

from config import EMBED_BATCH_SIZE
from src.embed import embed_chunks


TOPICS = [
    "Historia del Parque del Retiro",
    "Árboles y vegetación del parque",
    "Palacio de Cristal",
    "Palacio de Velázquez",
    "Estanque Grande",
    "Actividades culturales",
    "Rutas para caminar",
    "Información práctica",
    "Monumentos y jardines",
    "Aves comunes de Madrid",
]


def build_chunks(count: int) -> list[dict]:
    """Genera chunks pequeños con metadata representativa."""
    return [
        {
            "chunk_id": f"smoke-embedding__{index:04d}",
            "document_id": "smoke-embedding",
            "text": (
                f"{TOPICS[index % len(TOPICS)]}. "
                f"Fragmento de validación número {index}."
            ),
            "source": "smoke_test_embeddings.py",
            "category": "flora_fauna",
            "corpus_group": (
                "flora_fauna_arte_cultura_actividades"
            ),
            "chunk_index": index,
        }
        for index in range(count)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ejecuta una prueba real de embeddings por lotes."
    )
    parser.add_argument("--count", type=int, default=35)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    if args.count <= 0:
        raise ValueError("--count debe ser mayor que cero")

    if args.batch_size <= 0:
        raise ValueError("--batch-size debe ser mayor que cero")

    chunks = build_chunks(args.count)
    original_chunks = deepcopy(chunks)

    embedded = embed_chunks(chunks)

    if chunks != original_chunks:
        raise AssertionError(
            "embed_chunks ha modificado los chunks originales"
        )

    if len(embedded) != len(chunks):
        raise AssertionError(
            f"Se esperaban {len(chunks)} resultados y se "
            f"recibieron {len(embedded)}"
        )

    expected_ids = [chunk["chunk_id"] for chunk in chunks]
    returned_ids = [chunk["chunk_id"] for chunk in embedded]

    if returned_ids != expected_ids:
        raise AssertionError(
            "El orden o los chunk_id no se han conservado"
        )

    dimensions = {len(chunk["vector"]) for chunk in embedded}

    if len(dimensions) != 1:
        raise AssertionError(
            f"Se han recibido dimensiones diferentes: {dimensions}"
        )

    dimension = dimensions.pop()

    if dimension <= 0:
        raise AssertionError("Los vectores están vacíos")

    if not all(
        math.isfinite(value)
        for chunk in embedded
        for value in chunk["vector"]
    ):
        raise AssertionError(
            "Algún vector contiene NaN o valores infinitos"
        )

    if not all(
        chunk["source"] == "smoke_test_embeddings.py"
        and chunk["category"] == "flora_fauna"
        for chunk in embedded
    ):
        raise AssertionError(
            "No se ha conservado correctamente la metadata"
        )

    batches = (
        len(chunks) + EMBED_BATCH_SIZE - 1
    ) // EMBED_BATCH_SIZE

    print("Prueba real de embeddings superada")
    print(f"Chunks enviados: {len(chunks)}")
    print(f"Lotes esperados: {batches}")
    print(f"Vectores recibidos: {len(embedded)}")
    print(f"Dimensión común: {dimension}")
    print("Orden conservado: sí")
    print("Metadata conservada: sí")
    print("Chunks originales modificados: no")
    print("Valores finitos: sí")


if __name__ == "__main__":
    main()