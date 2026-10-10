from copy import deepcopy
from types import SimpleNamespace

import pytest

import src.embed as embed_module
from src.embed import embed_chunks, embed_query, limitar_chunks
from src.embedding_cache import EmbeddingCheckpoint


def make_chunk(index: int, group: str = "grupo_a") -> dict:
    """Crea un chunk mínimo válido para las pruebas."""
    return {
        "chunk_id": f"documento__{index:04d}",
        "document_id": "documento",
        "text": f"Texto del fragmento número {index}.",
        "source": "documento.md",
        "chunk_index": index,
        "category": "flora_fauna",
        "corpus_group": group,
    }


class FakeModels:
    """Simula client.models y registra las llamadas realizadas."""

    def __init__(self):
        self.calls = []

    def embed_content(self, *, model, contents, config):
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
            embeddings.append(
                SimpleNamespace(
                    values=[
                        float(len(text)),
                        1.0,
                        2.0,
                    ]
                )
            )

        return SimpleNamespace(embeddings=embeddings)


class FakeClient:
    """Cliente Gemini falso con la misma interfaz usada por embed.py."""

    def __init__(self, models=None):
        self.models = models or FakeModels()


class IncompleteModels(FakeModels):
    """Simula que Gemini devuelve menos vectores de los solicitados."""

    def embed_content(self, *, model, contents, config):
        result = super().embed_content(
            model=model,
            contents=contents,
            config=config,
        )
        result.embeddings = result.embeddings[:-1]
        return result


class InconsistentModels(FakeModels):
    """Simula vectores con dimensiones diferentes."""

    def embed_content(self, *, model, contents, config):
        result = super().embed_content(
            model=model,
            contents=contents,
            config=config,
        )
        if len(result.embeddings) >= 2:
            result.embeddings[1].values = [1.0, 2.0]
        return result


class NonFiniteModels(FakeModels):
    """Simula un embedding que contiene un valor NaN."""

    def embed_content(self, *, model, contents, config):
        result = super().embed_content(
            model=model,
            contents=contents,
            config=config,
        )
        result.embeddings[0].values = [1.0, float("nan"), 2.0]
        return result


class MissingEmbeddingsModels(FakeModels):
    """Simula una respuesta de Gemini sin el campo embeddings."""

    def embed_content(self, *, model, contents, config):
        self.calls.append(
            {
                "model": model,
                "contents": contents,
                "config": config,
            }
        )
        return SimpleNamespace()


# Comprueba que una entrada vacía no realiza llamadas al proveedor.
def test_empty_chunks_return_empty_list_without_api_call():
    client = FakeClient()

    result = embed_chunks([], client=client)

    assert result == []
    assert client.models.calls == []


# Comprueba que cada chunk recibe exactamente un vector.
def test_embed_chunks_adds_one_vector_per_chunk():
    chunks = [make_chunk(0), make_chunk(1), make_chunk(2)]
    client = FakeClient()

    result = embed_chunks(chunks, client=client)

    assert len(result) == len(chunks)
    assert all("vector" in chunk for chunk in result)
    assert all(len(chunk["vector"]) == 3 for chunk in result)


# Comprueba que la función conserva el orden de entrada.
def test_embed_chunks_preserves_input_order():
    chunks = [make_chunk(0), make_chunk(1), make_chunk(2)]
    client = FakeClient()

    result = embed_chunks(chunks, client=client)

    assert [chunk["chunk_id"] for chunk in result] == [
        chunk["chunk_id"]
        for chunk in chunks
    ]


# Comprueba que embed_chunks no modifica los diccionarios originales.
def test_embed_chunks_does_not_mutate_input():
    chunks = [make_chunk(0), make_chunk(1)]
    original = deepcopy(chunks)
    client = FakeClient()

    result = embed_chunks(chunks, client=client)

    assert chunks == original
    assert result is not chunks
    assert all("vector" not in chunk for chunk in chunks)


# Comprueba que la metadata original se conserva en la salida.
def test_embed_chunks_preserves_metadata():
    chunks = [make_chunk(0)]
    client = FakeClient()

    result = embed_chunks(chunks, client=client)

    for field in (
        "chunk_id",
        "document_id",
        "text",
        "source",
        "chunk_index",
        "category",
        "corpus_group",
    ):
        assert result[0][field] == chunks[0][field]


# Comprueba que se registran el modelo y la dimensión del embedding.
def test_embed_chunks_adds_embedding_metadata():
    chunks = [make_chunk(0)]
    client = FakeClient()

    result = embed_chunks(chunks, client=client)

    assert result[0]["embedding_model"] == embed_module.EMBEDDING_MODEL
    assert result[0]["embedding_dimension"] == 3


# Comprueba que los textos se distribuyen según el tamaño de lote.
def test_embed_chunks_uses_configured_batch_size(monkeypatch):
    monkeypatch.setattr(embed_module, "EMBED_BATCH_SIZE", 2)
    chunks = [make_chunk(index) for index in range(5)]
    client = FakeClient()

    embed_chunks(chunks, client=client)

    assert len(client.models.calls) == 3
    assert [
        len(call["contents"])
        for call in client.models.calls
    ] == [2, 2, 1]


# Comprueba que los chunks usan el tipo de tarea documental.
def test_embed_chunks_uses_document_task_type():
    client = FakeClient()

    embed_chunks([make_chunk(0)], client=client)

    config = client.models.calls[0]["config"]
    assert config.task_type == "RETRIEVAL_DOCUMENT"


# Comprueba que una consulta usa el tipo de tarea de retrieval.
def test_embed_query_uses_query_task_type():
    client = FakeClient()

    vector = embed_query("¿Qué árboles hay en El Retiro?", client=client)

    config = client.models.calls[0]["config"]
    assert config.task_type == "RETRIEVAL_QUERY"
    assert len(vector) == 3


# Comprueba que las consultas vacías o no textuales se rechazan.
@pytest.mark.parametrize("query", ["", "   ", None, 123])
def test_embed_query_rejects_invalid_text(query):
    with pytest.raises(ValueError):
        embed_query(query, client=FakeClient())


# Comprueba que los chunks deben ser diccionarios.
def test_embed_chunks_rejects_non_dictionary_chunk():
    with pytest.raises(TypeError):
        embed_chunks(["chunk inválido"], client=FakeClient())


# Comprueba que cada chunk contiene los campos mínimos de embeddings.
@pytest.mark.parametrize(
    "missing_field",
    ["chunk_id", "document_id", "text"],
)
def test_embed_chunks_rejects_missing_required_field(missing_field):
    chunk = make_chunk(0)
    chunk.pop(missing_field)

    with pytest.raises(ValueError):
        embed_chunks([chunk], client=FakeClient())


# Comprueba que los campos mínimos no estén vacíos.
@pytest.mark.parametrize(
    "field",
    ["chunk_id", "document_id", "text"],
)
def test_embed_chunks_rejects_empty_required_field(field):
    chunk = make_chunk(0)
    chunk[field] = "   "

    with pytest.raises(ValueError):
        embed_chunks([chunk], client=FakeClient())


# Comprueba que un tamaño de lote inválido detiene la operación.
@pytest.mark.parametrize("batch_size", [0, -1, True, "2"])
def test_embed_chunks_rejects_invalid_batch_size(
    monkeypatch,
    batch_size,
):
    monkeypatch.setattr(
        embed_module,
        "EMBED_BATCH_SIZE",
        batch_size,
    )

    with pytest.raises(ValueError):
        embed_chunks([make_chunk(0)], client=FakeClient())


# Comprueba que se detecta la pérdida de embeddings en una respuesta.
def test_embed_chunks_rejects_missing_vectors():
    client = FakeClient(models=IncompleteModels())

    with pytest.raises(
        RuntimeError,
        match="Falló el lote de embeddings",
    ):
        embed_chunks([make_chunk(0), make_chunk(1)], client=client)


# Comprueba que no se aceptan vectores con dimensiones diferentes.
def test_embed_chunks_rejects_inconsistent_dimensions():
    client = FakeClient(models=InconsistentModels())

    with pytest.raises(
        RuntimeError,
        match="Falló el lote de embeddings",
    ):
        embed_chunks([make_chunk(0), make_chunk(1)], client=client)


# Comprueba que no se aceptan valores NaN o infinitos.
def test_embed_chunks_rejects_non_finite_values():
    client = FakeClient(models=NonFiniteModels())

    with pytest.raises(
        RuntimeError,
        match="Falló el lote de embeddings",
    ):
        embed_chunks([make_chunk(0)], client=client)


# Comprueba que se detecta una respuesta sin embeddings.
def test_embed_chunks_rejects_response_without_embeddings():
    client = FakeClient(models=MissingEmbeddingsModels())

    with pytest.raises(
        RuntimeError,
        match="Falló el lote de embeddings",
    ):
        embed_chunks([make_chunk(0)], client=client)


# Comprueba que un error 429 reintenta únicamente el lote afectado.
def test_retry_batch_after_rate_limit(monkeypatch):
    calls = []
    sleeps = []

    def fake_embed_batch(client, texts, task_type):
        calls.append((client, texts, task_type))

        if len(calls) == 1:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

        return [[0.1, 0.2, 0.3]]

    monkeypatch.setattr(
        embed_module,
        "_embeddear_lote",
        fake_embed_batch,
    )
    monkeypatch.setattr(
        embed_module,
        "EMBED_MAX_RETRIES",
        2,
    )
    monkeypatch.setattr(
        embed_module,
        "EMBED_RETRY_DELAY_SECONDS",
        0.25,
    )
    monkeypatch.setattr(
        embed_module.time,
        "sleep",
        lambda seconds: sleeps.append(seconds),
    )

    client = object()

    result = embed_module._embeddear_lote_con_reintentos(
        client,
        ["texto de prueba"],
        task_type="RETRIEVAL_DOCUMENT",
    )

    assert result == [[0.1, 0.2, 0.3]]
    assert len(calls) == 2
    assert sleeps == [0.25]


# Comprueba que los errores distintos de 429 no se reintentan.
def test_retry_batch_does_not_retry_other_errors(monkeypatch):
    calls = []
    sleeps = []

    def fake_embed_batch(client, texts, task_type):
        calls.append((client, texts, task_type))
        raise ValueError("Respuesta de embeddings inválida.")

    monkeypatch.setattr(
        embed_module,
        "_embeddear_lote",
        fake_embed_batch,
    )
    monkeypatch.setattr(
        embed_module,
        "EMBED_MAX_RETRIES",
        3,
    )
    monkeypatch.setattr(
        embed_module.time,
        "sleep",
        lambda seconds: sleeps.append(seconds),
    )

    with pytest.raises(
        ValueError,
        match="Respuesta de embeddings inválida",
    ):
        embed_module._embeddear_lote_con_reintentos(
            object(),
            ["texto de prueba"],
            task_type="RETRIEVAL_DOCUMENT",
        )

    assert len(calls) == 1
    assert sleeps == []


# Comprueba que el lote falla al agotar el máximo de reintentos.
def test_retry_batch_stops_after_maximum_retries(monkeypatch):
    calls = []
    sleeps = []

    def fake_embed_batch(client, texts, task_type):
        calls.append((client, texts, task_type))
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(
        embed_module,
        "_embeddear_lote",
        fake_embed_batch,
    )
    monkeypatch.setattr(
        embed_module,
        "EMBED_MAX_RETRIES",
        2,
    )
    monkeypatch.setattr(
        embed_module,
        "EMBED_RETRY_DELAY_SECONDS",
        0.5,
    )
    monkeypatch.setattr(
        embed_module.time,
        "sleep",
        lambda seconds: sleeps.append(seconds),
    )

    with pytest.raises(
        RuntimeError,
        match="429 RESOURCE_EXHAUSTED",
    ):
        embed_module._embeddear_lote_con_reintentos(
            object(),
            ["texto de prueba"],
            task_type="RETRIEVAL_DOCUMENT",
        )

    assert len(calls) == 3
    assert sleeps == [0.5, 0.5]


# Comprueba que la detección reconoce las formas habituales del error de cuota.
@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("429"),
        RuntimeError("429 RESOURCE_EXHAUSTED"),
        RuntimeError("Quota exceeded: RESOURCE_EXHAUSTED"),
    ],
)
def test_rate_limit_error_detection_by_message(error):
    assert embed_module._es_error_de_cuota(error) is True

# Comprueba que un status_code 429 se reconoce aunque cambie el mensaje.


def test_rate_limit_error_detection_by_status_code():
    class FakeRateLimitError(Exception):
        status_code = 429

    error = FakeRateLimitError("límite temporal")

    assert embed_module._es_error_de_cuota(error) is True


# Comprueba que un error normal no se confunde con un límite de cuota.
def test_rate_limit_error_detection_rejects_other_errors():
    error = RuntimeError("Error interno del proveedor.")

    assert embed_module._es_error_de_cuota(error) is False


# Comprueba que None conserva todos los chunks sin reutilizar la lista.
def test_limitar_chunks_with_none_keeps_all_chunks():
    chunks = [make_chunk(0), make_chunk(1)]

    result = limitar_chunks(chunks, max_chunks=None)

    assert result == chunks
    assert result is not chunks


# Comprueba que un límite cero produce una selección vacía.
def test_limitar_chunks_with_zero_returns_empty_list():
    chunks = [make_chunk(0), make_chunk(1)]

    result = limitar_chunks(chunks, max_chunks=0)

    assert result == []


# Comprueba que el límite respeta exactamente el máximo solicitado.
def test_limitar_chunks_respects_maximum():
    chunks = [
        make_chunk(0, group="grupo_a"),
        make_chunk(1, group="grupo_a"),
        make_chunk(2, group="grupo_b"),
        make_chunk(3, group="grupo_b"),
    ]

    result = limitar_chunks(chunks, max_chunks=3)

    assert len(result) == 3


# Comprueba que, si hay cupo, ningún grupo queda sin representación.
def test_limitar_chunks_preserves_groups_when_capacity_allows():
    chunks = [
        make_chunk(0, group="grupo_a"),
        make_chunk(1, group="grupo_a"),
        make_chunk(2, group="grupo_b"),
        make_chunk(3, group="grupo_b"),
    ]

    result = limitar_chunks(chunks, max_chunks=2)

    assert {
        chunk["corpus_group"]
        for chunk in result
    } == {"grupo_a", "grupo_b"}


# Comprueba que los límites negativos o no enteros se rechazan.
@pytest.mark.parametrize("max_chunks", [-1, True, 2.5, "2"])
def test_limitar_chunks_rejects_invalid_limit(max_chunks):
    with pytest.raises((TypeError, ValueError)):
        limitar_chunks([make_chunk(0)], max_chunks=max_chunks)


# Comprueba que el nombre del campo de agrupación sea válido.
@pytest.mark.parametrize("agrupar_por", ["", "   ", None])
def test_limitar_chunks_rejects_invalid_group_field(agrupar_por):
    with pytest.raises(ValueError):
        limitar_chunks(
            [make_chunk(0)],
            max_chunks=1,
            agrupar_por=agrupar_por,
        )


# Comprueba que los vectores almacenados evitan nuevas llamadas a Gemini.
def test_embed_chunks_reuses_all_cached_vectors(tmp_path):
    chunks = [make_chunk(0), make_chunk(1)]
    checkpoint = EmbeddingCheckpoint(
        path=tmp_path / "embeddings.json",
        model=embed_module.EMBEDDING_MODEL,
    )
    checkpoint.save_batch(
        chunks,
        [[0.1, 0.2], [0.3, 0.4]],
    )

    class ModelsThatMustNotBeCalled:
        def embed_content(self, **kwargs):
            raise AssertionError("Gemini no debería ser llamado.")

    client = FakeClient(models=ModelsThatMustNotBeCalled())

    result = embed_chunks(
        chunks,
        client=client,
        checkpoint=checkpoint,
    )

    assert [item["vector"] for item in result] == [
        [0.1, 0.2],
        [0.3, 0.4],
    ]


# Comprueba que solo se solicitan a Gemini los chunks no almacenados.
def test_embed_chunks_only_requests_missing_vectors(
    tmp_path,
    monkeypatch,
):
    chunks = [
        make_chunk(0),
        make_chunk(1),
        make_chunk(2),
    ]
    checkpoint = EmbeddingCheckpoint(
        path=tmp_path / "embeddings.json",
        model=embed_module.EMBEDDING_MODEL,
    )
    checkpoint.save_batch(
        [chunks[0], chunks[2]],
        [[0.1, 0.2], [0.5, 0.6]],
    )

    calls = []

    def fake_embed_batch(client, texts, task_type):
        calls.append(list(texts))
        return [[0.3, 0.4] for _ in texts]

    monkeypatch.setattr(
        embed_module,
        "_embeddear_lote_con_reintentos",
        fake_embed_batch,
    )

    result = embed_chunks(
        chunks,
        client=object(),
        checkpoint=checkpoint,
    )

    assert calls == [[chunks[1]["text"]]]
    assert [item["vector"] for item in result] == [
        [0.1, 0.2],
        [0.3, 0.4],
        [0.5, 0.6],
    ]


# Comprueba que los resultados conservan el orden original al mezclar
# vectores recuperados y recién generados.
def test_embed_chunks_preserves_order_when_resuming(tmp_path, monkeypatch):
    chunks = [make_chunk(0), make_chunk(1), make_chunk(2)]
    checkpoint = EmbeddingCheckpoint(
        path=tmp_path / "embeddings.json",
        model=embed_module.EMBEDDING_MODEL,
    )
    checkpoint.save_batch(
        [chunks[1]],
        [[1.0, 1.0]],
    )

    generated_vectors = iter([
        [0.0, 0.0],
        [2.0, 2.0],
    ])

    def fake_embed_batch(client, texts, task_type):
        return [
            next(generated_vectors)
            for _ in texts
        ]

    monkeypatch.setattr(
        embed_module,
        "_embeddear_lote_con_reintentos",
        fake_embed_batch,
    )

    result = embed_chunks(
        chunks,
        client=object(),
        checkpoint=checkpoint,
    )

    assert [item["vector"] for item in result] == [
        [0.0, 0.0],
        [1.0, 1.0],
        [2.0, 2.0],
    ]


# Comprueba que un lote completado queda guardado aunque falle el siguiente.
def test_embed_chunks_keeps_completed_batches_after_failure(
    tmp_path,
    monkeypatch,
):
    chunks = [make_chunk(0), make_chunk(1)]
    path = tmp_path / "embeddings.json"
    checkpoint = EmbeddingCheckpoint(
        path=path,
        model=embed_module.EMBEDDING_MODEL,
    )
    calls = 0

    def fake_embed_batch(client, texts, task_type):
        nonlocal calls
        calls += 1

        if calls == 1:
            return [[0.1, 0.2]]

        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(
        embed_module,
        "EMBED_BATCH_SIZE",
        1,
    )
    monkeypatch.setattr(
        embed_module,
        "_embeddear_lote_con_reintentos",
        fake_embed_batch,
    )

    with pytest.raises(
        RuntimeError,
        match="Falló el lote de embeddings 2",
    ):
        embed_chunks(
            chunks,
            client=object(),
            checkpoint=checkpoint,
        )

    reloaded = EmbeddingCheckpoint(
        path=path,
        model=embed_module.EMBEDDING_MODEL,
    )

    assert reloaded.get(chunks[0]) == [0.1, 0.2]
    assert reloaded.get(chunks[1]) is None
