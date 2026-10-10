"""Retrieval de los chunks mas relevantes para una consulta.

Convierte la pregunta en un vector con embed.embed_query(), la busca en la
coleccion de ChromaDB y devuelve los chunks ordenados por relevancia.

Contrato 3 del contrato compartido: cada resultado es el chunk original mas
un campo score. La coleccion usa metrica coseno, por lo que la conversion de
distancia a score es score = max(0.0, min(1.0, 1.0 - distance)). Si el equipo
cambia HNSW_SPACE, hay que cambiar tambien este adaptador.
"""

from __future__ import annotations

from typing import Any

from config import HNSW_SPACE, TOP_K
from src.embed import embed_query
from src.index import obtener_cliente_chroma, obtener_coleccion

_CAMPOS_INCLUIDOS = ["documents", "metadatas", "distances"]


def distancia_a_score(distance: float) -> float:
    """Convierte una distancia coseno de Chroma en un score entre 0 y 1."""
    if HNSW_SPACE != "cosine":
        raise ValueError(
            f"El adaptador de score solo cubre la metrica coseno, no {HNSW_SPACE!r}."
        )
    if not isinstance(distance, (int, float)) or isinstance(distance, bool):
        raise TypeError(
            f"La distancia debe ser numerica, no {type(distance).__name__}."
        )
    return max(0.0, min(1.0, 1.0 - float(distance)))


def _validar_top_k(top_k: int) -> int:
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ValueError("top_k debe ser un entero mayor que 0.")
    return top_k


def _validar_query(query: str) -> str:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("La consulta no puede estar vacia.")
    return query.strip()


def _construir_resultado(
    text: str,
    metadata: dict | None,
    distance: float,
) -> dict:
    """Rehace el chunk original y le anade el score."""
    resultado = dict(metadata or {})
    resultado["text"] = text or ""
    resultado["score"] = distancia_a_score(distance)
    return resultado


def retrieve(
    query: str,
    top_k: int = TOP_K,
    collection: Any | None = None,
    client: Any | None = None,
    where: dict | None = None,
) -> list[dict]:
    """Devuelve los top_k chunks mas relevantes, de mayor a menor score.

    Cada elemento conserva los campos del chunk indexado (chunk_id,
    document_id, text, source, chunk_index, category, corpus_group y page
    cuando existe) y anade score.

    collection y client son opcionales para poder inyectar dobles en los
    tests sin llamar a ChromaDB ni a la API de Gemini.
    """
    query = _validar_query(query)
    top_k = _validar_top_k(top_k)

    if collection is None:
        collection = obtener_coleccion(
            client or obtener_cliente_chroma(),
            crear=False,
        )

    vector = embed_query(query)

    consulta: dict[str, Any] = {
        "query_embeddings": [vector],
        "n_results": top_k,
        "include": _CAMPOS_INCLUIDOS,
    }
    if where:
        consulta["where"] = where

    respuesta = collection.query(**consulta)

    documentos = (respuesta.get("documents") or [[]])[0]
    metadatas = (respuesta.get("metadatas") or [[]])[0]
    distancias = (respuesta.get("distances") or [[]])[0]

    if not (len(documentos) == len(metadatas) == len(distancias)):
        raise ValueError(
            "Chroma devolvio listas de distinta longitud: "
            f"{len(documentos)} textos, {len(metadatas)} metadatas, "
            f"{len(distancias)} distancias."
        )

    resultados = [
        _construir_resultado(texto, metadata, distancia)
        for texto, metadata, distancia in zip(documentos, metadatas, distancias)
    ]
    resultados.sort(key=lambda chunk: chunk["score"], reverse=True)

    print(
        f"[RETRIEVE] '{query[:60]}' -> {len(resultados)} chunks (top_k={top_k})"
    )
    return resultados
