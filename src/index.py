"""Indexación validada de chunks con embeddings en ChromaDB."""

import math
import os
from typing import Any

import chromadb

from config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    HNSW_SPACE,
    INDEX_BATCH_SIZE,
)

_CAMPOS_NO_METADATA = {"chunk_id", "text", "vector"}
_CAMPOS_OBLIGATORIOS = {"chunk_id", "document_id", "text", "vector"}
_TIPOS_METADATA = (str, int, float, bool)


def _sanitizar_metadata(chunk: dict) -> dict:
    """Omite None y rechaza estructuras difíciles de filtrar en Chroma."""
    metadata: dict[str, str | int | float | bool] = {}
    for clave, valor in chunk.items():
        if clave in _CAMPOS_NO_METADATA or valor is None:
            continue
        if not isinstance(valor, _TIPOS_METADATA):
            raise TypeError(
                f"Metadata no compatible en '{clave}': {type(valor).__name__}."
            )
        if isinstance(valor, float) and not math.isfinite(valor):
            raise ValueError(f"La metadata '{clave}' contiene NaN o infinito.")
        metadata[clave] = valor
    return metadata


def _validar_batch_size() -> None:
    if (
        not isinstance(INDEX_BATCH_SIZE, int)
        or isinstance(INDEX_BATCH_SIZE, bool)
        or INDEX_BATCH_SIZE <= 0
    ):
        raise ValueError("INDEX_BATCH_SIZE debe ser un entero mayor que 0.")


def _validar_chunks(chunks: list[dict]) -> tuple[int, str]:
    """Valida todos los registros antes del primer upsert."""
    if not chunks:
        raise ValueError("No hay chunks con vector que indexar.")

    ids: list[str] = []
    dimensiones: set[int] = set()
    modelos: set[str] = set()

    for posicion, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            raise TypeError(
                f"El chunk en posición {posicion} debe ser un diccionario.")
        faltantes = _CAMPOS_OBLIGATORIOS - set(chunk)
        if faltantes:
            raise ValueError(
                f"El chunk en posición {posicion} no contiene: {sorted(faltantes)}."
            )

        for campo in ("chunk_id", "document_id", "text"):
            if not isinstance(chunk[campo], str) or not chunk[campo].strip():
                raise ValueError(
                    f"El campo '{campo}' del chunk en posición {posicion} "
                    "debe ser texto no vacío."
                )

        vector = chunk["vector"]
        if not isinstance(vector, (list, tuple)) or not vector:
            raise ValueError(
                f"El vector del chunk '{chunk['chunk_id']}' está vacío.")
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            for value in vector
        ):
            raise ValueError(
                f"El vector del chunk '{chunk['chunk_id']}' no es válido.")

        ids.append(chunk["chunk_id"].strip())
        dimensiones.add(len(vector))
        modelos.add(str(chunk.get("embedding_model", EMBEDDING_MODEL)).strip())
        _sanitizar_metadata(chunk)

    if len(ids) != len(set(ids)):
        duplicados = sorted(
            {chunk_id for chunk_id in ids if ids.count(chunk_id) > 1})
        raise ValueError(f"Hay chunk_id duplicados: {duplicados[:10]}.")
    if len(dimensiones) != 1:
        raise ValueError(
            f"Dimensiones de embedding inconsistentes: {dimensiones}.")
    if len(modelos) != 1:
        raise ValueError(f"Se han mezclado modelos de embeddings: {modelos}.")

    return next(iter(dimensiones)), next(iter(modelos))


def obtener_cliente_chroma() -> chromadb.PersistentClient:
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DIR)


def _nombres_colecciones(client: Any) -> set[str]:
    """Tolera versiones que devuelven nombres o objetos Collection."""
    return {
        item if isinstance(item, str) else item.name
        for item in client.list_collections()
    }


def borrar_coleccion(client: Any) -> bool:
    """Elimina la colección si existe sin ocultar errores reales de Chroma."""
    if COLLECTION_NAME not in _nombres_colecciones(client):
        print(f"[INDEX] colección '{COLLECTION_NAME}' no existía.")
        return False
    client.delete_collection(name=COLLECTION_NAME)
    print(f"[INDEX] colección '{COLLECTION_NAME}' eliminada.")
    return True


def obtener_coleccion(
    client: Any,
    crear: bool = True,
    embedding_dimension: int | None = None,
    embedding_model: str | None = None,
):
    if not crear:
        return client.get_collection(name=COLLECTION_NAME)

    metadata: dict[str, str | int] = {"hnsw:space": HNSW_SPACE}
    if embedding_dimension is not None:
        metadata["embedding_dimension"] = embedding_dimension
    if embedding_model:
        metadata["embedding_model"] = embedding_model

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata=metadata,
    )
    return collection


def _validar_configuracion_coleccion(
    collection: Any,
    embedding_dimension: int,
    embedding_model: str,
) -> None:
    """Impide mezclar configuraciones en una colección persistente."""
    if collection.count() == 0:
        return

    metadata = collection.metadata or {}
    existing_space = metadata.get("hnsw:space")
    existing_model = metadata.get("embedding_model")
    existing_dimension = metadata.get("embedding_dimension")

    incompatibilities: list[str] = []
    if existing_space and existing_space != HNSW_SPACE:
        incompatibilities.append(
            f"métrica {existing_space!r} != {HNSW_SPACE!r}")
    if existing_model and existing_model != embedding_model:
        incompatibilities.append(
            f"modelo {existing_model!r} != {embedding_model!r}")
    if existing_dimension is not None and int(existing_dimension) != embedding_dimension:
        incompatibilities.append(
            f"dimensión {existing_dimension!r} != {embedding_dimension!r}"
        )

    # Una colección antigua sin fingerprint tampoco es segura para mezclar.
    if not existing_model or existing_dimension is None:
        incompatibilities.append(
            "la colección existente no identifica modelo y dimensión")

    if incompatibilities:
        raise ValueError(
            "La colección existente es incompatible: "
            + "; ".join(incompatibilities)
            + ". Regenera el índice con recreate=True."
        )


def index_chunks(
    chunks_con_vector: list[dict],
    recreate: bool = False,
    client: Any | None = None,
) -> int:
    """Valida e indexa chunks mediante upsert.

    ``upsert`` evita duplicados con el mismo ID, pero no elimina registros que
    ya no estén en la entrada. Usa ``recreate=True`` para una reconstrucción
    completa tras cambiar corpus, chunking, modelo, dimensión o métrica.
    """
    _validar_batch_size()
    dimension, model = _validar_chunks(chunks_con_vector)
    client = client or obtener_cliente_chroma()

    if recreate:
        borrar_coleccion(client)

    # Consulta primero la existencia para validar la metadata original. Pasar
    # metadata a get_or_create_collection sobre una colección ya existente no
    # debe utilizarse como mecanismo de validación.
    if COLLECTION_NAME in _nombres_colecciones(client):
        collection = obtener_coleccion(client, crear=False)
        _validar_configuracion_coleccion(collection, dimension, model)
    else:
        collection = obtener_coleccion(
            client,
            crear=True,
            embedding_dimension=dimension,
            embedding_model=model,
        )

    for numero_lote, inicio in enumerate(
        range(0, len(chunks_con_vector), INDEX_BATCH_SIZE),
        start=1,
    ):
        lote = chunks_con_vector[inicio: inicio + INDEX_BATCH_SIZE]
        try:
            collection.upsert(
                ids=[chunk["chunk_id"].strip() for chunk in lote],
                embeddings=[list(chunk["vector"]) for chunk in lote],
                documents=[chunk["text"].strip() for chunk in lote],
                metadatas=[_sanitizar_metadata(chunk) for chunk in lote],
            )
        except Exception as error:
            raise RuntimeError(
                f"Falló el lote de indexación {numero_lote} "
                f"(chunks {inicio}:{inicio + len(lote)})."
            ) from error

    total = collection.count()
    print(
        f"[INDEX] upsert de {len(chunks_con_vector)} chunks · "
        f"colección '{COLLECTION_NAME}' ({total} chunks en total)"
    )
    return total


def contar_por_filtro(where: dict) -> int:
    """Cuenta chunks utilizando la sintaxis explícita de filtros de Chroma."""
    if not isinstance(where, dict) or not where:
        raise ValueError("where debe ser un diccionario de filtro no vacío.")
    client = obtener_cliente_chroma()
    collection = obtener_coleccion(client, crear=False)
    resultado = collection.get(where=where, include=[])
    return len(resultado.get("ids", []))
