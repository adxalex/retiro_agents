"""Comprueba que la salida de load.py y chunk.py respeta el contrato compartido.

Uso (desde la raíz del repo):
    python scripts/validation/check_pdf_contract.py
    python scripts/validation/check_pdf_contract.py --source itinerarios__rutas_caminar__retiro__v01.pdf

Errores (exit 1): campos obligatorios vacíos, document_id que no es slug (§5),
page que no es entero 1-based (§3), varios document_id por fichero, sufijo -pN,
páginas repetidas o desordenadas, chunk_index no consecutivo (§4), chunk_id mal
formado (§5), category y corpus_group incoherentes (§6). Avisos: pies de página o viñetas huérfanas en chunks.
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from config import CHUNK_OVERLAP, CHUNK_SIZE, DATA_DIR  # noqa: E402
from src.chunk import chunk_documents  # noqa: E402
from src.load import load_documents  # noqa: E402

CATEGORY_TO_GROUP = {
    "historia": "historia_monumentos_jardines",
    "monumentos": "historia_monumentos_jardines",
    "jardines": "historia_monumentos_jardines",
    "flora_fauna": "flora_fauna_arte_cultura_actividades",
    "arte_cultura": "flora_fauna_arte_cultura_actividades",
    "actividades": "flora_fauna_arte_cultura_actividades",
    "itinerarios": "itinerarios_informacion_practica_seguridad",
    "informacion_practica": "itinerarios_informacion_practica_seguridad",
    "seguridad": "itinerarios_informacion_practica_seguridad",
}
PAGE_SUFFIX = re.compile(r"-p\d+$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")  # contrato §5: slug sin espacios, tildes ni "_"
REQUIRED_TEXT_FIELDS = ("document_id", "text", "source", "category", "corpus_group")
NOISE_LINE = re.compile(r"^\s*(?:\d{1,2}\.|[•·▪◦\-–])\s*$|P[áa]gina\s+\d+\s*$", re.IGNORECASE)


def check_documents(docs: list[dict], errors: list[str]) -> None:
    ids_by_source: dict[str, set[str]] = defaultdict(set)
    pages_by_source: dict[str, list[int]] = defaultdict(list)
    seen_pairs: set[tuple[str, int]] = set()

    for doc in docs:
        missing = [f for f in REQUIRED_TEXT_FIELDS if not isinstance(doc.get(f), str) or not doc[f].strip()]
        if missing:
            errors.append(f"{doc.get('source', '?')}: campos obligatorios vacíos o ausentes {missing} (contrato §3).")
            continue
        source, doc_id, page = doc["source"], doc["document_id"], doc.get("page")
        if not SLUG.fullmatch(doc_id):
            errors.append(f"{source}: document_id '{doc_id}' no es un slug válido (contrato §5).")
        if "page" in doc and (not isinstance(page, int) or isinstance(page, bool) or page < 1):
            errors.append(f"{source}: 'page' debe ser entero 1-based o no existir, no {page!r} (contrato §3).")
            page = None
        ids_by_source[source].add(doc_id)
        if PAGE_SUFFIX.search(doc_id):
            errors.append(f"{source}: document_id '{doc_id}' incluye la página; usa el campo 'page'.")
        expected = CATEGORY_TO_GROUP.get(doc["category"])
        if expected != doc["corpus_group"]:
            errors.append(f"{source}: category '{doc['category']}' no corresponde a '{doc['corpus_group']}'.")
        if page is None:
            continue
        pair = (doc_id, page)
        if pair in seen_pairs:
            errors.append(f"{source}: combinación document_id + page repetida {pair}.")
        seen_pairs.add(pair)
        pages_by_source[source].append(page)

    for source, pages in pages_by_source.items():
        if len(ids_by_source[source]) > 1:
            errors.append(f"{source}: {len(ids_by_source[source])} document_id distintos (debe ser uno por fichero).")
        if pages != sorted(pages):
            errors.append(f"{source}: páginas entregadas fuera de orden {pages}.")


def check_chunks(chunks: list[dict], errors: list[str], warnings: list[str]) -> dict[str, dict]:
    summary: dict[str, dict] = defaultdict(lambda: {"source": "", "pages": set(), "chunks": 0, "noisy": []})
    indexes: dict[str, list[int]] = defaultdict(list)

    for chunk in chunks:
        doc_id = chunk["document_id"]
        row = summary[doc_id]
        row["source"] = chunk["source"]
        row["chunks"] += 1
        if "page" in chunk:
            row["pages"].add(chunk["page"])
        indexes[doc_id].append(chunk["chunk_index"])
        if chunk["chunk_id"] != f"{doc_id}__{chunk['chunk_index']:04d}":
            errors.append(f"{doc_id}: chunk_id mal formado '{chunk['chunk_id']}'.")
        if any(NOISE_LINE.search(line) for line in chunk["text"].splitlines()):
            row["noisy"].append(chunk["chunk_id"])

    for doc_id, idx in indexes.items():
        if idx != list(range(len(idx))):
            errors.append(f"{doc_id}: chunk_index no consecutivo ({idx[:8]}...).")
        if summary[doc_id]["noisy"]:
            warnings.append(f"{doc_id}: {len(summary[doc_id]['noisy'])} chunks con pie de página o viñetas huérfanas: "
                            + ", ".join(summary[doc_id]["noisy"]))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida el contrato load -> chunk.")
    parser.add_argument("--data", default=DATA_DIR)
    parser.add_argument("--source", help="Nombre de fichero concreto a revisar")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=CHUNK_OVERLAP)
    args = parser.parse_args()

    try:
        docs = load_documents(args.data)
    except Exception as error:
        print(f"[ERROR] load_documents falló: {error}")
        return 1
    if args.source:
        docs = [doc for doc in docs if doc["source"] == args.source]
    if not docs:
        print("[ERROR] No se cargó ningún documento con ese filtro.")
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    check_documents(docs, errors)
    chunks = chunk_documents(docs, args.chunk_size, args.chunk_overlap, quitar_repetidos=True)
    summary = check_chunks(chunks, errors, warnings)

    print(f"{'document_id':<48} {'páginas':>7} {'chunks':>6} {'ruido':>5}")
    for doc_id, row in sorted(summary.items()):
        print(f"{doc_id:<48} {len(row['pages']) or '-':>7} {row['chunks']:>6} {len(row['noisy']):>5}")
    for message in warnings:
        print(f"[AVISO] {message}")
    for message in errors:
        print(f"[ERROR] {message}")
    print("OK: contrato respetado." if not errors else f"{len(errors)} errores.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
