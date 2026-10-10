"""Smoke test de la frontera entre indexación y retrieval."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import chromadb
import pytest

import src.pipeline as pipeline_module
import src.retrieve as retrieve_module
from src.index import obtener_coleccion


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "loaded_documents_block_b.json"
)


def load_fixture() -> list[dict]:
    """Carga los LoadedDocument compartidos para la integración."""
    return json.loads(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )


def deterministic_vector(text: str) -> list[float]:
    """Genera vectores controlados sin utilizar Gemini."""
    normalized = text.lower()

    if "paisaje" in normalized or "paseo del prado" in normalized:
        return [1.0, 0.0, 0.0]

    if "petirrojo" in normalized:
        return [0.0, 1.0, 0.0]

    return [0.0, 0.0, 1.0]


def fake_embed_chunks(
    chunks: list[dict],
    client=None,
    checkpoint=None,
) -> list[dict]:
    """Añade embeddings deterministas conservando la metadata."""
    return [
        {
            **deepcopy(chunk),
            "vector": deterministic_vector(chunk["text"]),
            "embedding_model": "deterministic-test-model",
            "embedding_dimension": 3,
        }
        for chunk in chunks
    ]


# Comprueba el recorrido contrato A → bloque B → frontera con bloque C.
def test_pipeline_index_can_be_consumed_by_retrieve(
    monkeypatch,
    tmp_path,
):
    documents = load_fixture()

    monkeypatch.setattr(
        pipeline_module,
        "load_documents",
        lambda data_dir: deepcopy(documents),
    )
    monkeypatch.setattr(
        pipeline_module,
        "embed_chunks",
        fake_embed_chunks,
    )

    client = chromadb.PersistentClient(
        path=str(tmp_path / "chroma"),
    )

    report = pipeline_module.build_index(
        "fixture-data",
        recreate=True,
        chroma_client=client,
    )

    collection = obtener_coleccion(
        client,
        crear=False,
    )

    monkeypatch.setattr(
        retrieve_module,
        "embed_query",
        lambda query: deterministic_vector(query),
    )

    results = retrieve_module.retrieve(
        "¿Qué relación tiene el Retiro con el Paisaje de la Luz?",
        top_k=2,
        collection=collection,
    )

    assert report["indexed"] is True
    assert report["collection_count"] == report["chunks"]
    assert collection.count() == report["chunks"]

    assert len(results) == 2
    assert results[0]["document_id"] == "retiro-paisaje-de-la-luz"
    assert results[0]["category"] == "arte_cultura"
    assert results[0]["corpus_group"] == (
        "flora_fauna_arte_cultura_actividades"
    )
    assert results[0]["source"] == (
        "arte_cultura__retiro_paisaje_de_la_luz__v01.md"
    )
    assert results[0]["score"] == pytest.approx(1.0)
    assert "vector" not in results[0]
