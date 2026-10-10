"""Orquestación del pipeline offline del sistema RAG."""

from __future__ import annotations

from collections import Counter
from typing import Any

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DATA_DIR,
    EMBEDDING_MODEL,
    EMBED_CHECKPOINT_PATH,
    EMBED_RESUME,
)
from src.chunk import chunk_documents
from src.embed import embed_chunks
from src.embedding_cache import EmbeddingCheckpoint
from src.index import index_chunks
from src.load import load_documents


def prepare_corpus(
    data_dir: str = DATA_DIR,
) -> tuple[list[dict], list[dict]]:
    """Carga el corpus completo y lo transforma en chunks."""
    documents = load_documents(data_dir)

    if not documents:
        raise ValueError(f"No se encontraron documentos en {data_dir!r}.")

    chunks = chunk_documents(
        documents,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        quitar_repetidos=True,
    )

    if not chunks:
        raise ValueError("El corpus no produjo ningún chunk.")

    return documents, chunks


def summarize_corpus(
    documents: list[dict],
    chunks: list[dict],
) -> dict[str, Any]:
    """Resume el corpus preparado sin modificarlo."""
    return {
        "documents": len(documents),
        "sources": len({document["source"] for document in documents}),
        "chunks": len(chunks),
        "documents_by_group": dict(
            sorted(
                Counter(
                    document["corpus_group"]
                    for document in documents
                ).items()
            )
        ),
        "chunks_by_group": dict(
            sorted(
                Counter(
                    chunk["corpus_group"]
                    for chunk in chunks
                ).items()
            )
        ),
    }


def build_index(
    data_dir: str = DATA_DIR,
    *,
    recreate: bool = True,
    dry_run: bool = False,
    embedding_client: Any | None = None,
    chroma_client: Any | None = None,
    checkpoint: EmbeddingCheckpoint | None = None,
) -> dict[str, Any]:
    """Ejecuta load → chunk → embed → index sobre el corpus completo.

    ``dry_run`` valida la carga y el chunking sin llamar a Gemini ni Chroma.
    Por defecto, la colección se reconstruye para no conservar chunks antiguos.
    """
    documents, chunks = prepare_corpus(data_dir)
    report = summarize_corpus(documents, chunks)

    if dry_run:
        report["indexed"] = False
        report["collection_count"] = None
        return report

    active_checkpoint = checkpoint

    if active_checkpoint is None and EMBED_RESUME:
        active_checkpoint = EmbeddingCheckpoint(
            path=EMBED_CHECKPOINT_PATH,
            model=EMBEDDING_MODEL,
        )

    chunks_with_vectors = embed_chunks(
        chunks,
        client=embedding_client,
        checkpoint=active_checkpoint,
    )

    collection_count = index_chunks(
        chunks_with_vectors,
        recreate=recreate,
        client=chroma_client,
    )

    report["indexed"] = True
    report["collection_count"] = collection_count
    return report
