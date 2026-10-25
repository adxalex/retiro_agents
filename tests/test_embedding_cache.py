import json
import math

import pytest

from src.embedding_cache import EmbeddingCheckpoint


def make_chunk(
    index: int = 0,
    text: str = "Texto de prueba.",
) -> dict:
    return {
        "chunk_id": f"documento__{index:04d}",
        "document_id": "documento",
        "text": text,
        "source": "documento.md",
        "chunk_index": index,
        "category": "flora_fauna",
        "corpus_group": "flora_fauna_arte_cultura_actividades",
    }


def test_checkpoint_returns_none_when_file_does_not_exist(tmp_path):
    checkpoint = EmbeddingCheckpoint(
        path=tmp_path / "embeddings.json",
        model="gemini-embedding-001",
    )

    assert checkpoint.get(make_chunk()) is None


def test_checkpoint_saves_and_recovers_vector(tmp_path):
    path = tmp_path / "embeddings.json"
    chunk = make_chunk()
    vector = [0.1, 0.2, 0.3]

    checkpoint = EmbeddingCheckpoint(
        path=path,
        model="gemini-embedding-001",
    )
    checkpoint.save_batch([chunk], [vector])

    recovered = EmbeddingCheckpoint(
        path=path,
        model="gemini-embedding-001",
    ).get(chunk)

    assert recovered == vector
    assert recovered is not vector


def test_checkpoint_invalidates_vector_when_text_changes(tmp_path):
    path = tmp_path / "embeddings.json"
    original = make_chunk(text="Texto original.")
    modified = make_chunk(text="Texto modificado.")

    checkpoint = EmbeddingCheckpoint(
        path=path,
        model="gemini-embedding-001",
    )
    checkpoint.save_batch([original], [[0.1, 0.2]])

    assert checkpoint.get(modified) is None


def test_checkpoint_invalidates_entries_from_another_model(tmp_path):
    path = tmp_path / "embeddings.json"
    chunk = make_chunk()

    first_model = EmbeddingCheckpoint(
        path=path,
        model="gemini-embedding-001",
    )
    first_model.save_batch([chunk], [[0.1, 0.2]])

    another_model = EmbeddingCheckpoint(
        path=path,
        model="gemini-embedding-2",
    )

    assert another_model.get(chunk) is None


@pytest.mark.parametrize(
    "vector",
    [
        [],
        [math.nan, 0.2],
        [math.inf, 0.2],
        ["no-numérico", 0.2],
    ],
)
def test_checkpoint_rejects_invalid_vectors(tmp_path, vector):
    checkpoint = EmbeddingCheckpoint(
        path=tmp_path / "embeddings.json",
        model="gemini-embedding-001",
    )

    with pytest.raises((TypeError, ValueError)):
        checkpoint.save_batch([make_chunk()], [vector])


def test_checkpoint_rejects_different_vector_dimensions(tmp_path):
    checkpoint = EmbeddingCheckpoint(
        path=tmp_path / "embeddings.json",
        model="gemini-embedding-001",
    )

    with pytest.raises(ValueError, match="dimensiones"):
        checkpoint.save_batch(
            [make_chunk(0), make_chunk(1)],
            [[0.1, 0.2], [0.1, 0.2, 0.3]],
        )


def test_checkpoint_rejects_different_chunk_and_vector_counts(tmp_path):
    checkpoint = EmbeddingCheckpoint(
        path=tmp_path / "embeddings.json",
        model="gemini-embedding-001",
    )

    with pytest.raises(ValueError, match="cantidad"):
        checkpoint.save_batch(
            [make_chunk(0), make_chunk(1)],
            [[0.1, 0.2]],
        )


def test_checkpoint_preserves_previous_batches(tmp_path):
    path = tmp_path / "embeddings.json"
    first_chunk = make_chunk(0)
    second_chunk = make_chunk(1)

    checkpoint = EmbeddingCheckpoint(
        path=path,
        model="gemini-embedding-001",
    )
    checkpoint.save_batch([first_chunk], [[0.1, 0.2]])
    checkpoint.save_batch([second_chunk], [[0.3, 0.4]])

    reloaded = EmbeddingCheckpoint(
        path=path,
        model="gemini-embedding-001",
    )

    assert reloaded.get(first_chunk) == [0.1, 0.2]
    assert reloaded.get(second_chunk) == [0.3, 0.4]


def test_checkpoint_writes_valid_json(tmp_path):
    path = tmp_path / "embeddings.json"
    checkpoint = EmbeddingCheckpoint(
        path=path,
        model="gemini-embedding-001",
    )

    checkpoint.save_batch([make_chunk()], [[0.1, 0.2]])

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["version"] == 1
    assert payload["model"] == "gemini-embedding-001"
    assert "documento__0000" in payload["entries"]


def test_checkpoint_rejects_corrupted_json(tmp_path):
    path = tmp_path / "embeddings.json"
    path.write_text("{contenido roto", encoding="utf-8")

    with pytest.raises(RuntimeError, match="checkpoint"):
        EmbeddingCheckpoint(
            path=path,
            model="gemini-embedding-001",
        )
