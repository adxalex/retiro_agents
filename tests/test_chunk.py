import json
from pathlib import Path

import pytest

from src.chunk import chunk_documents


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_valid_documents() -> list[dict]:
    fixture_path = FIXTURES_DIR / "loaded_documents_valid.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def make_valid_document(**overrides) -> dict:
    document = {
        "document_id": "flora_fauna__prueba__madrid__v01",
        "text": "El Retiro contiene diferentes especies vegetales.",
        "source": "flora_fauna__prueba__madrid__v01.md",
        "category": "flora_fauna",
        "corpus_group": "flora_fauna_arte_cultura_actividades",
    }
    document.update(overrides)
    return document

# Comprueba que no se generan chunks cuando no hay documentos.


def test_empty_document_list_returns_empty_list():
    assert chunk_documents([], chunk_size=100, chunk_overlap=10) == []

# Comprueba que el tamaño del chunk sea siempre mayor que cero.


@pytest.mark.parametrize("chunk_size", [0, -1])
def test_rejects_non_positive_chunk_size(chunk_size):
    with pytest.raises(ValueError):
        chunk_documents(
            [make_valid_document()],
            chunk_size=chunk_size,
            chunk_overlap=0,
        )

# Comprueba que el overlap no sea negativo ni igual o mayor que el chunk.


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [
        (100, -1),
        (100, 100),
        (100, 101),
    ],
)
def test_rejects_invalid_overlap(chunk_size, chunk_overlap):
    with pytest.raises(ValueError):
        chunk_documents(
            [make_valid_document()],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

# Comprueba que chunk_size y chunk_overlap sean enteros y no booleanos.


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [
        ("100", 10),
        (100, "10"),
        (True, 0),
        (100, False),
    ],
)
def test_rejects_non_integer_configuration(chunk_size, chunk_overlap):
    with pytest.raises(TypeError):
        chunk_documents(
            [make_valid_document()],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

# Comprueba que todo documento incluya los campos obligatorios del contrato.


@pytest.mark.parametrize(
    "missing_field",
    [
        "document_id",
        "text",
        "source",
        "category",
        "corpus_group",
    ],
)
def test_rejects_missing_required_fields(missing_field):
    document = make_valid_document()
    document.pop(missing_field)

    with pytest.raises(ValueError):
        chunk_documents([document], chunk_size=100, chunk_overlap=10)

# Comprueba que los campos obligatorios no estén vacíos.


@pytest.mark.parametrize(
    "field",
    [
        "document_id",
        "text",
        "source",
        "category",
        "corpus_group",
    ],
)
def test_rejects_empty_required_fields(field):
    document = make_valid_document(**{field: "   "})

    with pytest.raises(ValueError):
        chunk_documents([document], chunk_size=100, chunk_overlap=10)


# Comprueba que los campos obligatorios sean cadenas de texto.
@pytest.mark.parametrize(
    "field",
    [
        "document_id",
        "text",
        "source",
        "category",
        "corpus_group",
    ],
)
def test_rejects_non_string_required_fields(field):
    document = make_valid_document(**{field: 123})

    with pytest.raises(TypeError):
        chunk_documents(
            [document],
            chunk_size=100,
            chunk_overlap=10,
        )


# Comprueba que page sea un entero positivo y no un texto o booleano.

@pytest.mark.parametrize("page", [0, -1, "1", True])
def test_rejects_invalid_page(page):
    document = make_valid_document(page=page)

    with pytest.raises(ValueError):
        chunk_documents([document], chunk_size=100, chunk_overlap=10)


# Comprueba que los chunks tengan texto, IDs y metadata trazable.
def test_generates_non_empty_traceable_chunks():
    documents = load_valid_documents()

    chunks = chunk_documents(
        documents,
        chunk_size=90,
        chunk_overlap=10,
    )

    assert chunks

    for chunk in chunks:
        assert chunk["text"].strip()
        assert len(chunk["text"]) <= 90
        assert chunk["document_id"]
        assert chunk["chunk_id"]
        assert isinstance(chunk["chunk_index"], int)
        assert chunk["source"]
        assert chunk["category"]
        assert chunk["corpus_group"]


# Comprueba que los índices continúen entre las páginas del mismo PDF.
def test_chunk_ids_are_consecutive_across_pdf_pages():
    documents = load_valid_documents()

    chunks = chunk_documents(
        documents,
        chunk_size=90,
        chunk_overlap=10,
    )

    pdf_document_id = "flora_fauna__senda_botanica__madrid__v01"
    pdf_chunks = [
        chunk
        for chunk in chunks
        if chunk["document_id"] == pdf_document_id
    ]

    expected_ids = [
        f"{pdf_document_id}__{index:04d}"
        for index in range(len(pdf_chunks))
    ]

    assert [chunk["chunk_id"] for chunk in pdf_chunks] == expected_ids
    assert [
        chunk["chunk_index"]
        for chunk in pdf_chunks
    ] == list(range(len(pdf_chunks)))


# Comprueba que el PDF conserve page y que Markdown no reciba una página artificial.
def test_preserves_pdf_page_and_omits_page_for_markdown():
    documents = load_valid_documents()

    chunks = chunk_documents(
        documents,
        chunk_size=90,
        chunk_overlap=10,
    )

    pdf_chunks = [
        chunk
        for chunk in chunks
        if chunk["source"].endswith(".pdf")
    ]
    markdown_chunks = [
        chunk
        for chunk in chunks
        if chunk["source"].endswith(".md")
    ]

    assert pdf_chunks
    assert markdown_chunks
    assert all(chunk["page"] in {1, 2} for chunk in pdf_chunks)
    assert all("page" not in chunk for chunk in markdown_chunks)


# Comprueba que la misma entrada y configuración generen exactamente el mismo resultado.
def test_same_input_and_configuration_produce_same_chunks():
    documents = load_valid_documents()

    first_result = chunk_documents(
        documents,
        chunk_size=90,
        chunk_overlap=10,
    )
    second_result = chunk_documents(
        documents,
        chunk_size=90,
        chunk_overlap=10,
    )

    assert first_result == second_result


# Compara el comportamiento con y sin eliminación de cabeceras repetidas.
def test_optional_repeated_line_removal():
    documents = [
        make_valid_document(
            text=(
                "Ayuntamiento de Madrid\n"
                "Contenido específico de la primera página."
            ),
            page=1,
        ),
        make_valid_document(
            text=(
                "Ayuntamiento de Madrid\n"
                "Contenido específico de la segunda página."
            ),
            page=2,
        ),
        make_valid_document(
            text=(
                "Ayuntamiento de Madrid\n"
                "Contenido específico de la tercera página."
            ),
            page=3,
        ),
    ]

    chunks_without_cleanup = chunk_documents(
        documents,
        chunk_size=200,
        chunk_overlap=20,
        quitar_repetidos=False,
    )
    chunks_with_cleanup = chunk_documents(
        documents,
        chunk_size=200,
        chunk_overlap=20,
        quitar_repetidos=True,
    )

    assert any(
        "Ayuntamiento de Madrid" in chunk["text"]
        for chunk in chunks_without_cleanup
    )
    assert all(
        "Ayuntamiento de Madrid" not in chunk["text"]
        for chunk in chunks_with_cleanup
    )
