"""Pruebas unitarias de validación y metadata para src.index."""

from copy import deepcopy
import math

import pytest

import src.index as index_module
from src.index import _sanitizar_metadata, _validar_chunks


def make_valid_chunk(**overrides) -> dict:
    """Crea un chunk válido y permite modificar campos concretos."""
    chunk = {
        "chunk_id": "flora-retiro__0000",
        "document_id": "flora-retiro",
        "text": "El Retiro contiene numerosas especies vegetales.",
        "source": "flora.md",
        "category": "flora_fauna",
        "corpus_group": "flora_fauna_arte_cultura_actividades",
        "chunk_index": 0,
        "vector": [0.1, 0.2, 0.3],
        "embedding_model": "modelo-prueba",
    }
    chunk.update(overrides)
    return chunk


# Comprueba que los campos técnicos no se envíen como metadata a ChromaDB.
def test_sanitizar_metadata_excludes_technical_fields():
    chunk = make_valid_chunk()

    metadata = _sanitizar_metadata(chunk)

    assert "chunk_id" not in metadata
    assert "text" not in metadata
    assert "vector" not in metadata


# Comprueba que la metadata necesaria para trazabilidad se conserve.
def test_sanitizar_metadata_preserves_traceability():
    chunk = make_valid_chunk(page=2)

    metadata = _sanitizar_metadata(chunk)

    assert metadata["document_id"] == "flora-retiro"
    assert metadata["source"] == "flora.md"
    assert metadata["category"] == "flora_fauna"
    assert metadata["corpus_group"] == (
        "flora_fauna_arte_cultura_actividades"
    )
    assert metadata["chunk_index"] == 0
    assert metadata["page"] == 2


# Comprueba que los valores None se omitan porque ChromaDB no los admite.
def test_sanitizar_metadata_omits_none_values():
    chunk = make_valid_chunk(page=None)

    metadata = _sanitizar_metadata(chunk)

    assert "page" not in metadata


# Comprueba que estructuras anidadas no lleguen a la metadata plana.
@pytest.mark.parametrize(
    "invalid_value",
    [
        ["flora", "fauna"],
        {"tipo": "flora"},
        ("flora", "fauna"),
    ],
)
def test_sanitizar_metadata_rejects_nested_values(invalid_value):
    chunk = make_valid_chunk(extra_metadata=invalid_value)

    with pytest.raises(TypeError):
        _sanitizar_metadata(chunk)


# Comprueba que ChromaDB no reciba NaN o valores infinitos como metadata.
@pytest.mark.parametrize(
    "invalid_value",
    [
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_sanitizar_metadata_rejects_non_finite_numbers(invalid_value):
    chunk = make_valid_chunk(quality_score=invalid_value)

    with pytest.raises(ValueError):
        _sanitizar_metadata(chunk)


# Comprueba que no pueda iniciarse una indexación sin chunks.
def test_validar_chunks_rejects_empty_list():
    with pytest.raises(ValueError):
        _validar_chunks([])


# Comprueba que cada elemento recibido sea un diccionario.
def test_validar_chunks_rejects_non_dictionary():
    with pytest.raises(TypeError):
        _validar_chunks(["invalid-chunk"])


# Comprueba individualmente la presencia de los campos obligatorios.
@pytest.mark.parametrize(
    "missing_field",
    [
        "chunk_id",
        "document_id",
        "text",
        "vector",
    ],
)
def test_validar_chunks_rejects_missing_required_field(missing_field):
    chunk = make_valid_chunk()
    chunk.pop(missing_field)

    with pytest.raises(ValueError):
        _validar_chunks([chunk])


# Comprueba que los identificadores y el texto no estén vacíos.
@pytest.mark.parametrize(
    "field",
    [
        "chunk_id",
        "document_id",
        "text",
    ],
)
@pytest.mark.parametrize("invalid_value", ["", "   ", None, 123])
def test_validar_chunks_rejects_invalid_text_fields(
    field,
    invalid_value,
):
    chunk = make_valid_chunk(**{field: invalid_value})

    with pytest.raises(ValueError):
        _validar_chunks([chunk])


# Comprueba que el vector exista y contenga al menos una dimensión.
@pytest.mark.parametrize(
    "invalid_vector",
    [
        None,
        [],
        (),
        "0.1, 0.2",
    ],
)
def test_validar_chunks_rejects_missing_or_invalid_vector(
    invalid_vector,
):
    chunk = make_valid_chunk(vector=invalid_vector)

    with pytest.raises(ValueError):
        _validar_chunks([chunk])


# Comprueba que el vector solo contenga números finitos y no booleanos.
@pytest.mark.parametrize(
    "invalid_vector",
    [
        [0.1, "0.2", 0.3],
        [0.1, None, 0.3],
        [0.1, True, 0.3],
        [0.1, math.nan, 0.3],
        [0.1, math.inf, 0.3],
    ],
)
def test_validar_chunks_rejects_invalid_vector_values(
    invalid_vector,
):
    chunk = make_valid_chunk(vector=invalid_vector)

    with pytest.raises(ValueError):
        _validar_chunks([chunk])


# Comprueba que dos chunks no puedan compartir el mismo chunk_id.
def test_validar_chunks_rejects_duplicate_chunk_ids():
    first = make_valid_chunk()
    second = make_valid_chunk(text="Segundo fragmento.")

    with pytest.raises(ValueError):
        _validar_chunks([first, second])


# Comprueba que todos los embeddings tengan la misma dimensión.
def test_validar_chunks_rejects_inconsistent_dimensions():
    first = make_valid_chunk()
    second = make_valid_chunk(
        chunk_id="flora-retiro__0001",
        vector=[0.1, 0.2],
    )

    with pytest.raises(ValueError):
        _validar_chunks([first, second])


# Comprueba que no se mezclen modelos de embeddings.
def test_validar_chunks_rejects_mixed_embedding_models():
    first = make_valid_chunk()
    second = make_valid_chunk(
        chunk_id="flora-retiro__0001",
        embedding_model="otro-modelo",
    )

    with pytest.raises(ValueError):
        _validar_chunks([first, second])


# Comprueba que la validación no altere los chunks recibidos.
def test_validar_chunks_does_not_mutate_input():
    chunks = [make_valid_chunk()]
    original = deepcopy(chunks)

    _validar_chunks(chunks)

    assert chunks == original


# Comprueba que la validación devuelva dimensión y modelo detectados.
def test_validar_chunks_returns_dimension_and_model():
    chunks = [make_valid_chunk()]

    dimension, model = _validar_chunks(chunks)

    assert dimension == 3
    assert model == "modelo-prueba"


class FakeCollection:
    """Simula una colección ChromaDB en memoria."""

    def __init__(self, name, metadata=None):
        self.name = name
        self.metadata = metadata or {}
        self.records = {}
        self.upsert_calls = []

    def count(self):
        return len(self.records)

    def upsert(self, ids, documents, embeddings, metadatas):
        self.upsert_calls.append(
            {
                "ids": ids,
                "documents": documents,
                "embeddings": embeddings,
                "metadatas": metadatas,
            }
        )

        for position, chunk_id in enumerate(ids):
            self.records[chunk_id] = {
                "document": documents[position],
                "embedding": embeddings[position],
                "metadata": metadatas[position],
            }


class FakeClient:
    """Simula las operaciones del cliente Chroma utilizadas por index.py."""

    def __init__(self):
        self.collections = {}
        self.deleted_names = []

    def list_collections(self):
        return list(self.collections.values())

    def get_collection(self, name):
        return self.collections[name]

    def get_or_create_collection(self, name, metadata=None):
        if name not in self.collections:
            self.collections[name] = FakeCollection(
                name=name,
                metadata=metadata,
            )
        return self.collections[name]

    def delete_collection(self, name):
        self.deleted_names.append(name)
        del self.collections[name]


def make_chunks(quantity: int) -> list[dict]:
    """Genera varios chunks válidos con IDs consecutivos."""
    return [
        make_valid_chunk(
            chunk_id=f"flora-retiro__{index:04d}",
            text=f"Fragmento número {index}.",
            chunk_index=index,
        )
        for index in range(quantity)
    ]


# Comprueba que se reconozcan colecciones devueltas como objetos.
def test_nombres_colecciones_accepts_collection_objects():
    client = FakeClient()
    client.get_or_create_collection("retiro_test")

    names = index_module._nombres_colecciones(client)

    assert names == {"retiro_test"}


# Comprueba que borrar una colección inexistente no provoque error.
def test_borrar_coleccion_returns_false_when_missing(monkeypatch):
    monkeypatch.setattr(
        index_module,
        "COLLECTION_NAME",
        "retiro_test",
    )
    client = FakeClient()

    deleted = index_module.borrar_coleccion(client)

    assert deleted is False
    assert client.deleted_names == []


# Comprueba que una colección existente se elimine correctamente.
def test_borrar_coleccion_deletes_existing_collection(monkeypatch):
    monkeypatch.setattr(
        index_module,
        "COLLECTION_NAME",
        "retiro_test",
    )
    client = FakeClient()
    client.get_or_create_collection("retiro_test")

    deleted = index_module.borrar_coleccion(client)

    assert deleted is True
    assert "retiro_test" not in client.collections
    assert client.deleted_names == ["retiro_test"]


# Comprueba la metadata utilizada al crear una colección nueva.
def test_obtener_coleccion_creates_collection_with_configuration(
    monkeypatch,
):
    monkeypatch.setattr(
        index_module,
        "COLLECTION_NAME",
        "retiro_test",
    )
    monkeypatch.setattr(index_module, "HNSW_SPACE", "cosine")
    client = FakeClient()

    collection = index_module.obtener_coleccion(
        client,
        crear=True,
        embedding_dimension=3,
        embedding_model="modelo-prueba",
    )

    assert collection.name == "retiro_test"
    assert collection.metadata == {
        "hnsw:space": "cosine",
        "embedding_dimension": 3,
        "embedding_model": "modelo-prueba",
    }


# Comprueba que una colección vacía acepte la primera configuración.
def test_validar_configuracion_accepts_empty_collection():
    collection = FakeCollection(
        name="retiro_test",
        metadata={},
    )

    index_module._validar_configuracion_coleccion(
        collection,
        embedding_dimension=3,
        embedding_model="modelo-prueba",
    )


# Comprueba que una colección compatible pueda reutilizarse.
def test_validar_configuracion_accepts_compatible_collection(
    monkeypatch,
):
    monkeypatch.setattr(index_module, "HNSW_SPACE", "cosine")
    collection = FakeCollection(
        name="retiro_test",
        metadata={
            "hnsw:space": "cosine",
            "embedding_dimension": 3,
            "embedding_model": "modelo-prueba",
        },
    )
    collection.records["existing"] = {}

    index_module._validar_configuracion_coleccion(
        collection,
        embedding_dimension=3,
        embedding_model="modelo-prueba",
    )


# Comprueba que no se mezcle una dimensión diferente.
def test_validar_configuracion_rejects_different_dimension(
    monkeypatch,
):
    monkeypatch.setattr(index_module, "HNSW_SPACE", "cosine")
    collection = FakeCollection(
        name="retiro_test",
        metadata={
            "hnsw:space": "cosine",
            "embedding_dimension": 2,
            "embedding_model": "modelo-prueba",
        },
    )
    collection.records["existing"] = {}

    with pytest.raises(ValueError):
        index_module._validar_configuracion_coleccion(
            collection,
            embedding_dimension=3,
            embedding_model="modelo-prueba",
        )


# Comprueba que no se mezclen modelos de embeddings.
def test_validar_configuracion_rejects_different_model(
    monkeypatch,
):
    monkeypatch.setattr(index_module, "HNSW_SPACE", "cosine")
    collection = FakeCollection(
        name="retiro_test",
        metadata={
            "hnsw:space": "cosine",
            "embedding_dimension": 3,
            "embedding_model": "otro-modelo",
        },
    )
    collection.records["existing"] = {}

    with pytest.raises(ValueError):
        index_module._validar_configuracion_coleccion(
            collection,
            embedding_dimension=3,
            embedding_model="modelo-prueba",
        )


# Comprueba que los chunks se envíen a ChromaDB por lotes.
def test_index_chunks_uses_configured_batches(monkeypatch):
    monkeypatch.setattr(
        index_module,
        "COLLECTION_NAME",
        "retiro_test",
    )
    monkeypatch.setattr(index_module, "HNSW_SPACE", "cosine")
    monkeypatch.setattr(index_module, "INDEX_BATCH_SIZE", 2)

    client = FakeClient()
    chunks = make_chunks(5)

    total = index_module.index_chunks(chunks, client=client)

    collection = client.collections["retiro_test"]

    assert total == 5
    assert len(collection.upsert_calls) == 3
    assert [len(call["ids"]) for call in collection.upsert_calls] == [
        2,
        2,
        1,
    ]


# Comprueba la traducción del chunk a los campos de ChromaDB.
def test_index_chunks_maps_chunk_fields_to_chroma(monkeypatch):
    monkeypatch.setattr(
        index_module,
        "COLLECTION_NAME",
        "retiro_test",
    )
    monkeypatch.setattr(index_module, "INDEX_BATCH_SIZE", 10)

    client = FakeClient()
    chunk = make_valid_chunk(page=None)

    index_module.index_chunks([chunk], client=client)

    record = client.collections["retiro_test"].records[
        "flora-retiro__0000"
    ]

    assert record["document"] == chunk["text"]
    assert record["embedding"] == chunk["vector"]
    assert record["metadata"]["document_id"] == "flora-retiro"
    assert record["metadata"]["source"] == "flora.md"
    assert "page" not in record["metadata"]
    assert "vector" not in record["metadata"]


# Comprueba que reindexar los mismos IDs no cree duplicados.
def test_index_chunks_is_idempotent(monkeypatch):
    monkeypatch.setattr(
        index_module,
        "COLLECTION_NAME",
        "retiro_test",
    )
    monkeypatch.setattr(index_module, "INDEX_BATCH_SIZE", 10)

    client = FakeClient()
    chunks = make_chunks(3)

    first_total = index_module.index_chunks(chunks, client=client)
    second_total = index_module.index_chunks(chunks, client=client)

    assert first_total == 3
    assert second_total == 3
    assert client.collections["retiro_test"].count() == 3


# Comprueba que reconstruir elimine la colección anterior.
def test_index_chunks_recreates_collection_when_requested(
    monkeypatch,
):
    monkeypatch.setattr(
        index_module,
        "COLLECTION_NAME",
        "retiro_test",
    )
    monkeypatch.setattr(index_module, "INDEX_BATCH_SIZE", 10)

    client = FakeClient()
    old_collection = client.get_or_create_collection(
        "retiro_test",
        metadata={
            "hnsw:space": index_module.HNSW_SPACE,
            "embedding_dimension": 3,
            "embedding_model": "modelo-prueba",
        },
    )
    old_collection.records["old-chunk"] = {}

    total = index_module.index_chunks(
        make_chunks(2),
        client=client,
        recreate=True,
    )

    assert total == 2
    assert client.deleted_names == ["retiro_test"]
    assert "old-chunk" not in client.collections[
        "retiro_test"
    ].records


# Comprueba el ciclo real de indexación usando una ChromaDB temporal.
def test_index_chunks_with_temporary_chroma(
    tmp_path,
    monkeypatch,
):
    chroma_path = tmp_path / "chroma_test"

    monkeypatch.setattr(
        index_module,
        "CHROMA_DIR",
        str(chroma_path),
    )
    monkeypatch.setattr(
        index_module,
        "COLLECTION_NAME",
        "retiro_test",
    )
    monkeypatch.setattr(index_module, "INDEX_BATCH_SIZE", 2)
    monkeypatch.setattr(index_module, "HNSW_SPACE", "cosine")

    client = index_module.obtener_cliente_chroma()
    chunks = make_chunks(3)

    total = index_module.index_chunks(
        chunks,
        client=client,
    )

    collection = client.get_collection(name="retiro_test")
    stored = collection.get(
        ids=["flora-retiro__0000"],
        include=["documents", "metadatas"],
    )

    assert total == 3
    assert collection.count() == 3
    assert stored["documents"] == ["Fragmento número 0."]
    assert stored["metadatas"][0]["document_id"] == "flora-retiro"
    assert stored["metadatas"][0]["category"] == "flora_fauna"


# Comprueba con ChromaDB real que upsert no duplique registros.
def test_real_chroma_reindexing_is_idempotent(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        index_module,
        "CHROMA_DIR",
        str(tmp_path / "chroma_test"),
    )
    monkeypatch.setattr(
        index_module,
        "COLLECTION_NAME",
        "retiro_test",
    )
    monkeypatch.setattr(index_module, "INDEX_BATCH_SIZE", 10)

    client = index_module.obtener_cliente_chroma()
    chunks = make_chunks(3)

    first_total = index_module.index_chunks(
        chunks,
        client=client,
    )
    second_total = index_module.index_chunks(
        chunks,
        client=client,
    )

    assert first_total == 3
    assert second_total == 3
    assert client.get_collection(
        name="retiro_test"
    ).count() == 3