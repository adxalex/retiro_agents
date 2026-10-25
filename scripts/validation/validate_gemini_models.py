"""Comprueba que los modelos configurados sigan disponibles."""

from __future__ import annotations

import argparse
import json
from typing import Any

from config import EMBEDDING_MODEL, LLM_MODEL
from src.gemini_auth import get_gemini_client


def normalize_model_name(name: str) -> str:
    """Elimina el prefijo opcional models/."""
    return name.removeprefix("models/")


def model_actions(model: Any) -> set[str]:
    """Obtiene las operaciones anunciadas por la API."""
    actions = getattr(model, "supported_actions", None)

    if actions is None:
        actions = getattr(
            model,
            "supported_generation_methods",
            [],
        )

    return set(actions or [])


def list_available_models(client: Any) -> dict[str, list[str]]:
    """Agrupa los modelos disponibles por operación."""
    available = {
        "generateContent": [],
        "embedContent": [],
    }

    for model in client.models.list():
        name = normalize_model_name(model.name)
        actions = model_actions(model)

        for action in available:
            if action in actions:
                available[action].append(name)

    for names in available.values():
        names.sort()

    return available


def validate_model(
    configured_model: str,
    required_action: str,
    available: dict[str, list[str]],
) -> dict[str, Any]:
    """Comprueba un modelo contra la lista obtenida de Gemini."""
    normalized = normalize_model_name(configured_model)
    candidates = available[required_action]

    return {
        "configured_model": normalized,
        "required_action": required_action,
        "available": normalized in candidates,
        "available_models_for_action": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Valida los modelos configurados para el RAG."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Muestra el informe como JSON.",
    )
    args = parser.parse_args()

    client = get_gemini_client()
    available = list_available_models(client)

    report = {
        "llm": validate_model(
            LLM_MODEL,
            "generateContent",
            available,
        ),
        "embedding": validate_model(
            EMBEDDING_MODEL,
            "embedContent",
            available,
        ),
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for role, result in report.items():
            status = "OK" if result["available"] else "NO DISPONIBLE"
            print(
                f"{role}: {result['configured_model']} -> {status}"
            )

    if not all(item["available"] for item in report.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()