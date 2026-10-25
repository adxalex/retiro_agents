"""Validación de solo lectura del inventario, documentos cargados y chunks."""

import re
from pathlib import Path

import pandas as pd

SHEET_NAME = "Inventario_documental"
HEADER_ROW = 3
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
DOCUMENT_ID_PATTERN = re.compile(
    r"^[a-z0-9]+(?:_[a-z0-9]+)*__[a-z0-9]+(?:_[a-z0-9]+)*__"
    r"[a-z0-9]+(?:_[a-z0-9]+)*__v\d{2}(?:_[a-z0-9]+)*$"
)
REQUIRED_COLUMNS = {"decision", "document_id", "categoria", "corpus_group"}


def load_inventory(path: str, sheet: str = SHEET_NAME) -> pd.DataFrame:
    dataframe = pd.read_excel(path, sheet_name=sheet, header=HEADER_ROW)
    missing = REQUIRED_COLUMNS - set(dataframe.columns)
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {sorted(missing)}")
    return dataframe


def selected_rows(dataframe: pd.DataFrame) -> pd.DataFrame:
    decision = dataframe["decision"].astype("string").str.strip().str.casefold()
    selected = dataframe[decision.eq("conservar") & dataframe["document_id"].notna()].copy()
    for column in ("document_id", "categoria", "corpus_group"):
        selected[column] = selected[column].astype("string").str.strip()
    return selected


def validate_metadata(dataframe: pd.DataFrame) -> list[str]:
    problems: list[str] = []
    duplicated = dataframe["document_id"].duplicated(keep=False)
    for position, (_, row) in enumerate(dataframe.iterrows()):
        document_id = row["document_id"]
        category = row["categoria"]
        corpus_group = row["corpus_group"]
        expected_group = CATEGORY_TO_GROUP.get(category)
        if expected_group is None:
            problems.append(f"{document_id}: categoría '{category}' no válida.")
        elif corpus_group != expected_group:
            problems.append(
                f"{document_id}: corpus_group '{corpus_group}' no corresponde a '{category}'."
            )
        if not DOCUMENT_ID_PATTERN.fullmatch(document_id):
            problems.append(f"{document_id}: formato de document_id no válido.")
        if duplicated.iloc[position]:
            problems.append(f"{document_id}: document_id duplicado.")
    return sorted(set(problems))


def compare_loaded(dataframe: pd.DataFrame, loaded_document_ids: set[str]) -> dict[str, list[str]]:
    declared = set(dataframe["document_id"])
    loaded = {str(value).strip() for value in loaded_document_ids}
    return {
        "declarados_no_cargados": sorted(declared - loaded),
        "cargados_no_declarados": sorted(loaded - declared),
    }


def count_chunks(chunks: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for chunk in chunks:
        document_id = str(chunk["document_id"]).strip()
        counts[document_id] = counts.get(document_id, 0) + 1
    return counts


def build_report(
    inventory_path: str,
    loaded_document_ids: set[str],
    chunks: list[dict] | None = None,
) -> str:
    selected = selected_rows(load_inventory(inventory_path))
    problems = validate_metadata(selected)
    comparison = compare_loaded(selected, loaded_document_ids)
    lines = ["# Validación del corpus", "", "## Metadata"]
    lines.extend(f"- {problem}" for problem in problems)
    if not problems:
        lines.append("Sin problemas.")

    lines.extend(["", "## Inventario frente a carga"])
    for label, values in comparison.items():
        lines.append(f"### {label}")
        lines.extend(f"- {value}" for value in values) if values else lines.append("Ninguno.")

    if chunks is not None:
        lines.extend(["", "## Chunks por documento", "", "| document_id | chunk_count |", "|---|---:|"])
        lines.extend(f"| {doc_id} | {count} |" for doc_id, count in sorted(count_chunks(chunks).items()))
    return "\n".join(lines) + "\n"


def save_report(report: str, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
