"""Fragmentación de documentos cargados en chunks trazables."""

from collections import defaultdict
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

_REQUIRED_TEXT_FIELDS = (
    "document_id",
    "text",
    "source",
    "category",
    "corpus_group",
)
_MAX_REPEATED_LINE_LENGTH = 120


def _validate_chunk_config(chunk_size: int, chunk_overlap: int) -> None:
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool):
        raise TypeError("chunk_size debe ser un entero.")
    if not isinstance(chunk_overlap, int) or isinstance(chunk_overlap, bool):
        raise TypeError("chunk_overlap debe ser un entero.")
    if chunk_size <= 0:
        raise ValueError("chunk_size debe ser mayor que 0.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap no puede ser negativo.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap debe ser menor que chunk_size.")


def _validate_document(document: dict[str, Any]) -> None:
    """Comprueba que el documento cumple el contrato compartido."""
    if not isinstance(document, dict):
        raise TypeError("Cada documento debe ser un diccionario.")

    missing = [field for field in _REQUIRED_TEXT_FIELDS if field not in document]
    if missing:
        raise ValueError(f"Faltan campos obligatorios: {missing}.")

    for field in _REQUIRED_TEXT_FIELDS:
        value = document[field]
        if not isinstance(value, str):
            raise TypeError(
                f"El campo '{field}' debe ser una cadena de texto.")
        if not value.strip():
            raise ValueError(f"El campo '{field}' no puede estar vacío.")

    page = document.get("page")
    if page is not None:
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise ValueError(
                "El campo 'page' debe ser un entero positivo 1-based.")


def _create_splitter(
    chunk_size: int,
    chunk_overlap: int,
) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        keep_separator="end",
        separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ": ", ", ", " ", ""],
    )


def _detect_repeated_lines(
    documents: list[dict[str, Any]],
    min_pages: int = 3,
    min_ratio: float = 0.6,
) -> dict[str, set[str]]:
    """Detecta líneas cortas idénticas repetidas entre páginas de un documento."""
    pages_by_document: dict[str, list[str]] = defaultdict(list)
    for document in documents:
        pages_by_document[document["document_id"].strip()].append(
            document["text"])

    repeated: dict[str, set[str]] = {}
    for document_id, texts in pages_by_document.items():
        if len(texts) < min_pages:
            continue

        occurrences: dict[str, int] = defaultdict(int)
        for text in texts:
            unique_lines = {
                line.strip()
                for line in text.splitlines()
                if line.strip() and len(line.strip()) <= _MAX_REPEATED_LINE_LENGTH
            }
            for line in unique_lines:
                occurrences[line] += 1

        threshold = max(min_pages, int(len(texts) * min_ratio + 0.999999))
        repeated[document_id] = {
            line for line, count in occurrences.items() if count >= threshold
        }
    return repeated


def _remove_lines(text: str, lines_to_remove: set[str]) -> str:
    if not lines_to_remove:
        return text
    return "\n".join(
        line for line in text.splitlines() if line.strip() not in lines_to_remove
    )


def _metadata_without_none(document: dict[str, Any]) -> dict[str, Any]:
    """Evita valores None, incompatibles con la metadata de ChromaDB."""
    return {key: value for key, value in document.items() if value is not None}


def chunk_documents(
    documents: list[dict[str, Any]],
    chunk_size: int,
    chunk_overlap: int,
    quitar_repetidos: bool = False,
) -> list[dict[str, Any]]:
    """Divide documentos y conserva su metadata y trazabilidad.

    El orden de entrada debe ser determinista. Si un PDF se representa por
    páginas, ``load.py`` debe entregarlas ordenadas ascendentemente por ``page``.
    """
    _validate_chunk_config(chunk_size, chunk_overlap)
    if not documents:
        return []

    for document in documents:
        _validate_document(document)

    repeated_by_document = _detect_repeated_lines(
        documents) if quitar_repetidos else {}
    splitter = _create_splitter(chunk_size, chunk_overlap)
    next_index: dict[str, int] = defaultdict(int)
    chunks: list[dict[str, Any]] = []

    for document in documents:
        document_id = document["document_id"].strip()
        text = document["text"].strip()

        if quitar_repetidos:
            text = _remove_lines(text, repeated_by_document.get(
                document_id, set())).strip()
            if not text:
                continue

        for chunk_text in splitter.split_text(text):
            clean_text = chunk_text.strip()
            if not clean_text:
                continue

            chunk_index = next_index[document_id]
            next_index[document_id] += 1
            chunk = {
                **_metadata_without_none(document),
                "document_id": document_id,
                "chunk_id": f"{document_id}__{chunk_index:04d}",
                "chunk_index": chunk_index,
                "text": clean_text,
            }
            chunks.append(chunk)

    return chunks
