"""Pruebas de la orquestación del pipeline offline."""

from copy import deepcopy

import pytest

import src.pipeline as pipeline_module
from scripts.index_corpus import print_report


def make_documents() -> list[dict]:
    """Crea documentos mínimos que cumplen el contrato de carga."""
    return [
        {
            "document_id": "doc-a",
            "text": "Historia del Parque del Retiro.",
            "source": "historia.md",
            "category": "historia",
            "corpus_group": "historia_monumentos_jardines",
        },
        {
            "document_id": "doc-b",
            "text": "Arbolado y vegetación del Retiro.",
            "source": "flora.md",
            "category": "flora_fauna",
            "corpus_group": "flora_fauna_arte_cultura_actividades",
        },
    ]


def make_chunks() -> list[dict]:
    """Crea chunks mínimos que cumplen el contrato de chunking."""
    return [
        {
            "chunk_id": "doc-a__0000",
            "document_id": "doc-a",
            "text": "Historia del Parque del Retiro.",
            "source": "historia.md",
            "chunk_index": 0,
            "category": "historia",
            "corpus_group": "historia_monumentos_jardines",
        },
        {
            "chunk_id": "doc-b__0000",
            "document_id": "doc-b",
            "text": "Arbolado y vegetación del Retiro.",
            "source": "flora.md",
            "chunk_index": 0,
            "category": "flora_fauna",
            "corpus_group": "flora_fauna_arte_cultura_actividades",
        },
    ]


# Comprueba que un corpus vacío se detenga antes del chunking.
def test_prepare_corpus_rejects_empty_load(monkeypatch):
    monkeypatch.setattr(
        pipeline_module,
        "load_documents",
        lambda data_dir: [],
    )

    with pytest.raises(ValueError, match="No se encontraron documentos"):
        pipeline_module.prepare_corpus("data-test")


# Comprueba que una salida vacía de chunking se considere inválida.
def test_prepare_corpus_rejects_empty_chunks(monkeypatch):
    monkeypatch.setattr(
        pipeline_module,
        "load_documents",
        lambda data_dir: make_documents(),
    )
    monkeypatch.setattr(
        pipeline_module,
        "chunk_documents",
        lambda *args, **kwargs: [],
    )

    with pytest.raises(ValueError, match="no produjo ningún chunk"):
        pipeline_module.prepare_corpus("data-test")


# Comprueba que prepare_corpus conecte carga y chunking.
def test_prepare_corpus_returns_documents_and_chunks(monkeypatch):
    documents = make_documents()
    chunks = make_chunks()
    received = {}

    monkeypatch.setattr(
        pipeline_module,
        "load_documents",
        lambda data_dir: deepcopy(documents),
    )

    def fake_chunk_documents(
        loaded_documents,
        chunk_size,
        chunk_overlap,
        quitar_repetidos,
    ):
        received["documents"] = loaded_documents
        received["chunk_size"] = chunk_size
        received["chunk_overlap"] = chunk_overlap
        received["quitar_repetidos"] = quitar_repetidos
        return deepcopy(chunks)

    monkeypatch.setattr(
        pipeline_module,
        "chunk_documents",
        fake_chunk_documents,
    )

    result_documents, result_chunks = pipeline_module.prepare_corpus(
        "data-test"
    )

    assert result_documents == documents
    assert result_chunks == chunks
    assert received["documents"] == documents
    assert received["chunk_size"] == pipeline_module.CHUNK_SIZE
    assert received["chunk_overlap"] == pipeline_module.CHUNK_OVERLAP
    assert received["quitar_repetidos"] is True


# Comprueba que el resumen contabilice fuentes, documentos y grupos.
def test_summarize_corpus_counts_traceability():
    report = pipeline_module.summarize_corpus(
        make_documents(),
        make_chunks(),
    )

    assert report["documents"] == 2
    assert report["sources"] == 2
    assert report["chunks"] == 2
    assert report["documents_by_group"] == {
        "flora_fauna_arte_cultura_actividades": 1,
        "historia_monumentos_jardines": 1,
    }
    assert report["chunks_by_group"] == {
        "flora_fauna_arte_cultura_actividades": 1,
        "historia_monumentos_jardines": 1,
    }


# Comprueba que dry_run no llame a Gemini ni a Chroma.
def test_build_index_dry_run_skips_external_services(monkeypatch):
    monkeypatch.setattr(
        pipeline_module,
        "prepare_corpus",
        lambda data_dir: (make_documents(), make_chunks()),
    )

    def forbidden_call(*args, **kwargs):
        raise AssertionError("No debía llamarse en dry_run.")

    monkeypatch.setattr(
        pipeline_module,
        "embed_chunks",
        forbidden_call,
    )
    monkeypatch.setattr(
        pipeline_module,
        "index_chunks",
        forbidden_call,
    )

    report = pipeline_module.build_index(
        "data-test",
        dry_run=True,
    )

    assert report["indexed"] is False
    assert report["collection_count"] is None
    assert report["chunks"] == 2


# Comprueba la transferencia de chunks y clientes entre embed e index.
def test_build_index_connects_embeddings_and_chroma(monkeypatch):
    documents = make_documents()
    chunks = make_chunks()
    embedded_chunks = [
        {**chunk, "vector": [0.1, 0.2, 0.3]}
        for chunk in chunks
    ]

    embedding_client = object()
    chroma_client = object()
    checkpoint = object()
    received = {}

    monkeypatch.setattr(
        pipeline_module,
        "prepare_corpus",
        lambda data_dir: (
            deepcopy(documents),
            deepcopy(chunks),
        ),
    )

    def fake_embed(
        input_chunks,
        client,
        checkpoint=None,
    ):
        received["embed_chunks"] = input_chunks
        received["embedding_client"] = client
        received["checkpoint"] = checkpoint
        return deepcopy(embedded_chunks)

    def fake_index(input_chunks, recreate, client):
        received["index_chunks"] = input_chunks
        received["recreate"] = recreate
        received["chroma_client"] = client
        return len(input_chunks)

    monkeypatch.setattr(
        pipeline_module,
        "embed_chunks",
        fake_embed,
    )
    monkeypatch.setattr(
        pipeline_module,
        "index_chunks",
        fake_index,
    )

    report = pipeline_module.build_index(
        "data-test",
        recreate=True,
        embedding_client=embedding_client,
        chroma_client=chroma_client,
        checkpoint=checkpoint,
    )

    assert received["embed_chunks"] == chunks
    assert received["embedding_client"] is embedding_client
    assert received["checkpoint"] is checkpoint
    assert received["index_chunks"] == embedded_chunks
    assert received["recreate"] is True
    assert received["chroma_client"] is chroma_client
    assert report["indexed"] is True
    assert report["collection_count"] == 2


# Comprueba que el pipeline crea el checkpoint configurado automáticamente.
def test_build_index_creates_configured_checkpoint(
    monkeypatch,
    tmp_path,
):
    documents = make_documents()
    chunks = make_chunks()
    embedded_chunks = [
        {
            **chunk,
            "vector": [0.1, 0.2, 0.3],
        }
        for chunk in chunks
    ]
    checkpoint_path = tmp_path / "embeddings.json"
    received = {}

    monkeypatch.setattr(
        pipeline_module,
        "prepare_corpus",
        lambda data_dir: (
            deepcopy(documents),
            deepcopy(chunks),
        ),
    )
    monkeypatch.setattr(
        pipeline_module,
        "EMBED_RESUME",
        True,
        raising=False,
    )
    monkeypatch.setattr(
        pipeline_module,
        "EMBED_CHECKPOINT_PATH",
        str(checkpoint_path),
        raising=False,
    )
    monkeypatch.setattr(
        pipeline_module,
        "EMBEDDING_MODEL",
        "gemini-embedding-001",
        raising=False,
    )

    class FakeCheckpoint:
        def __init__(self, path, model):
            received["checkpoint_path"] = path
            received["checkpoint_model"] = model

    monkeypatch.setattr(
        pipeline_module,
        "EmbeddingCheckpoint",
        FakeCheckpoint,
        raising=False,
    )

    def fake_embed(
        input_chunks,
        client,
        checkpoint=None,
    ):
        received["checkpoint"] = checkpoint
        return deepcopy(embedded_chunks)

    monkeypatch.setattr(
        pipeline_module,
        "embed_chunks",
        fake_embed,
    )
    monkeypatch.setattr(
        pipeline_module,
        "index_chunks",
        lambda input_chunks, recreate, client: len(input_chunks),
    )

    report = pipeline_module.build_index(
        "data-test",
        embedding_client=object(),
        chroma_client=object(),
    )

    assert received["checkpoint_path"] == str(checkpoint_path)
    assert received["checkpoint_model"] == "gemini-embedding-001"
    assert isinstance(received["checkpoint"], FakeCheckpoint)
    assert report["indexed"] is True


# Comprueba que la interfaz pueda presentar el informe como JSON.
def test_print_report_supports_json(capsys):
    report = {
        "documents": 2,
        "sources": 2,
        "chunks": 2,
        "documents_by_group": {"grupo": 2},
        "chunks_by_group": {"grupo": 2},
        "indexed": False,
        "collection_count": None,
    }

    print_report(report, as_json=True)

    output = capsys.readouterr().out

    assert '"documents": 2' in output
    assert '"indexed": false' in output
    assert '"collection_count": null' in output
