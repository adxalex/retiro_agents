"""Prueba de integración del bloque B: chunk, embed e index."""

import json
from pathlib import Path
from types import SimpleNamespace

import src.embed as embed_module
import src.index as index_module
from src.chunk import chunk_documents


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "loaded_documents_block_b.json"
)


class FakeEmbeddingModels:
    """Simula la operación embed_content de Gemini."""

    def __init__(self):
        self.calls = []

    def embed_content(self, model, contents, config):
        self.calls.append(
            {
                "model": model,
                "contents": contents,
                "config": config,
            }
        )

        embeddings = []
        for content in contents:
            text = content.parts[0].text
            vector = [
                float(len(text)) / 1000,
                float(sum(map(ord, text)) % 100) / 100,
                1.0,
            ]
            embeddings.append(SimpleNamespace(values=vector))

        return SimpleNamespace(embeddings=embeddings)


class FakeGeminiClient:
    """Expone la misma interfaz mínima que el cliente de Gemini."""

    def __init__(self):
        self.models = FakeEmbeddingModels()


def load_fixture() -> list[dict]:
    """Carga los LoadedDocument utilizados por la integración."""
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# Comprueba el recorrido completo de B sin API externa ni índice real.
def test_block_b_pipeline_chunks_embeds_and_indexes(
    tmp_path,
    monkeypatch,
):
    documents = load_fixture()

    monkeypatch.setattr(embed_module, "EMBED_BATCH_SIZE", 2)
    monkeypatch.setattr(
        embed_module,
        "EMBEDDING_MODEL",
        "modelo-integracion-prueba",
    )
    monkeypatch.setattr(
        index_module,
        "CHROMA_DIR",
        str(tmp_path / "chroma"),
    )
    monkeypatch.setattr(
        index_module,
        "COLLECTION_NAME",
        "retiro_integracion_test",
    )
    monkeypatch.setattr(index_module, "INDEX_BATCH_SIZE", 2)

    chunks = chunk_documents(
        documents,
        chunk_size=80,
        chunk_overlap=10,
    )

    bird_chunks = [
        chunk
        for chunk in chunks
        if chunk["document_id"] == "guia-aves-retiro"
    ]

    # Las páginas del PDF mantienen una única secuencia de chunks.
    assert [chunk["chunk_index"] for chunk in bird_chunks] == list(
        range(len(bird_chunks))
    )
    assert {chunk["page"] for chunk in bird_chunks} == {1, 2}

    # El Markdown no inventa una página inexistente.
    markdown_chunks = [
        chunk
        for chunk in chunks
        if chunk["document_id"] == "retiro-paisaje-de-la-luz"
    ]
    assert markdown_chunks
    assert all("page" not in chunk for chunk in markdown_chunks)

    # Todos los chunks tienen un identificador único.
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    assert len(chunk_ids) == len(set(chunk_ids))

    fake_client = FakeGeminiClient()
    embedded_chunks = embed_module.embed_chunks(
        chunks,
        client=fake_client,
    )

    # Cada chunk recibe un vector compatible.
    assert len(embedded_chunks) == len(chunks)
    assert all(len(chunk["vector"]) == 3 for chunk in embedded_chunks)
    assert all(
        chunk["embedding_model"] == "modelo-integracion-prueba"
        for chunk in embedded_chunks
    )

    chroma_client = index_module.obtener_cliente_chroma()
    total = index_module.index_chunks(
        embedded_chunks,
        client=chroma_client,
    )

    collection = chroma_client.get_collection(
        name="retiro_integracion_test"
    )
    stored = collection.get(include=["metadatas"])

    # Todo lo producido por embeddings llega al índice.
    assert total == len(embedded_chunks)
    assert collection.count() == len(embedded_chunks)
    assert set(stored["ids"]) == set(chunk_ids)

    # La metadata contractual continúa disponible en ChromaDB.
    assert all(
        metadata["document_id"]
        in {"guia-aves-retiro", "retiro-paisaje-de-la-luz"}
        for metadata in stored["metadatas"]
    )
    assert all(
        metadata["corpus_group"]
        == "flora_fauna_arte_cultura_actividades"
        for metadata in stored["metadatas"]
    )

    # La simulación confirma que embed.py procesó varios lotes.
    assert len(fake_client.models.calls) >= 2


# Comprueba que repetir el flujo B no duplique los chunks indexados.
def test_block_b_pipeline_can_be_reindexed(
    tmp_path,
    monkeypatch,
):
    documents = load_fixture()

    monkeypatch.setattr(embed_module, "EMBED_BATCH_SIZE", 10)
    monkeypatch.setattr(
        embed_module,
        "EMBEDDING_MODEL",
        "modelo-integracion-prueba",
    )
    monkeypatch.setattr(
        index_module,
        "CHROMA_DIR",
        str(tmp_path / "chroma"),
    )
    monkeypatch.setattr(
        index_module,
        "COLLECTION_NAME",
        "retiro_integracion_test",
    )
    monkeypatch.setattr(index_module, "INDEX_BATCH_SIZE", 10)

    chunks = chunk_documents(
        documents,
        chunk_size=80,
        chunk_overlap=10,
    )
    embedded_chunks = embed_module.embed_chunks(
        chunks,
        client=FakeGeminiClient(),
    )

    client = index_module.obtener_cliente_chroma()

    first_total = index_module.index_chunks(
        embedded_chunks,
        client=client,
    )
    second_total = index_module.index_chunks(
        embedded_chunks,
        client=client,
    )

    assert first_total == len(embedded_chunks)
    assert second_total == len(embedded_chunks)
    assert client.get_collection(
        name="retiro_integracion_test"
    ).count() == len(embedded_chunks)