"""Diagnóstico de cobertura documental del retrieval; no mide relevancia."""

import json
from collections.abc import Callable
from pathlib import Path


def load_questions(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    questions = data if isinstance(data, list) else data.get("preguntas", [])
    if not isinstance(questions, list):
        raise ValueError("El fichero debe contener una lista de preguntas.")
    return questions


def observed_coverage(
    questions: list[dict],
    respond: Callable[[str], dict],
) -> dict[str, set[str]]:
    coverage: dict[str, set[str]] = {}
    for item in questions:
        text = item.get("texto") or item.get("pregunta")
        if not text:
            continue
        question_id = str(item.get("id") or text)
        result = respond(text)
        if not isinstance(result, dict):
            raise TypeError("respond() debe devolver un diccionario.")
        for chunk in result.get("chunks") or []:
            document_id = chunk.get("document_id")
            if document_id:
                coverage.setdefault(str(document_id).strip(), set()).add(question_id)
    return coverage


def expected_hits(
    questions: list[dict],
    respond: Callable[[str], dict],
) -> dict[str, bool]:
    """Comprueba si algún expected_document_id aparece en los chunks recuperados."""
    hits: dict[str, bool] = {}
    for item in questions:
        text = item.get("texto") or item.get("pregunta")
        if not text:
            continue
        question_id = str(item.get("id") or text)
        expected = {str(value).strip() for value in item.get("expected_document_ids", [])}
        result = respond(text)
        retrieved = {
            str(chunk["document_id"]).strip()
            for chunk in (result.get("chunks") or [])
            if chunk.get("document_id")
        }
        hits[question_id] = bool(expected & retrieved) if expected else False
    return hits


def build_coverage_report(
    indexed_document_ids: set[str],
    coverage: dict[str, set[str]],
) -> str:
    indexed = {str(value).strip() for value in indexed_document_ids}
    recovered = set(coverage)
    valid_recovered = recovered & indexed
    never_recovered = sorted(indexed - recovered)
    recovered_not_indexed = sorted(recovered - indexed)
    lines = [
        "# Cobertura documental observada",
        "",
        "> Esta medida indica aparición, no corrección ni relevancia.",
        "",
        f"- Documentos indexados: {len(indexed)}",
        f"- Documentos indexados recuperados al menos una vez: {len(valid_recovered)}",
        f"- Cobertura: {len(valid_recovered) / len(indexed):.1%}" if indexed else "- Cobertura: N/A",
        "",
        "## Indexados nunca recuperados",
    ]
    lines.extend(f"- {value}" for value in never_recovered) if never_recovered else lines.append("Ninguno.")
    lines.extend(["", "## Recuperados pero ausentes de la lista indexada"])
    lines.extend(f"- {value}" for value in recovered_not_indexed) if recovered_not_indexed else lines.append("Ninguno.")
    return "\n".join(lines) + "\n"
