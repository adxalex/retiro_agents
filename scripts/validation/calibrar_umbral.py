"""Calibra el umbral de abstencion (RAG_SCORE_MINIMO) con el banco de preguntas.

Compara la distribucion de scores del mejor chunk en las preguntas que el corpus
puede responder y en las que no, y propone el umbral que mas aciertos da.

Uso (desde la raiz del repo):
    python scripts/validation/calibrar_umbral.py --simulado     # sin clave ni indice
    python scripts/validation/calibrar_umbral.py                # con el indice real
    python scripts/validation/calibrar_umbral.py --top-k 5

IMPORTANTE: el umbral definitivo debe calcularse con gemini-embedding-001 y la
coleccion real. Con --simulado los scores son de embeddings de juguete y solo
sirven para comprobar el metodo.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from config import TOP_K  # noqa: E402
from src import retrieve as retrieve_module  # noqa: E402
from scripts.validation.eval_preguntas import (  # noqa: E402
    PREGUNTAS,
    _coleccion_simulada,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibra el umbral de abstencion.")
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--simulado", action="store_true")
    args = parser.parse_args()

    coleccion = _coleccion_simulada() if args.simulado else None

    con_respuesta: list[tuple[float, str]] = []
    sin_respuesta: list[tuple[float, str]] = []

    for pregunta, esperado, _fuente in PREGUNTAS:
        resultados = retrieve_module.retrieve(
            pregunta, top_k=args.top_k, collection=coleccion
        )
        score = resultados[0]["score"] if resultados else 0.0
        destino = sin_respuesta if esperado == "abstencion" else con_respuesta
        destino.append((score, pregunta))

    def resumen(nombre: str, datos: list[tuple[float, str]]) -> None:
        scores = sorted(s for s, _ in datos)
        if not scores:
            return
        medio = scores[len(scores) // 2]
        print(
            f"{nombre:24} n={len(scores):2}  min={scores[0]:.3f}  "
            f"mediana={medio:.3f}  max={scores[-1]:.3f}"
        )

    print(f"\nDistribucion del score del mejor chunk (top_k={args.top_k})")
    resumen("Deberia responder", con_respuesta)
    resumen("Deberia abstenerse", sin_respuesta)

    candidatos = sorted({round(s, 3) for s, _ in con_respuesta + sin_respuesta})
    mejor_umbral, mejor_aciertos = 0.0, -1
    print("\numbral  responde_ok  abstiene_ok  total")
    for umbral in candidatos:
        responde_ok = sum(1 for s, _ in con_respuesta if s >= umbral)
        abstiene_ok = sum(1 for s, _ in sin_respuesta if s < umbral)
        total = responde_ok + abstiene_ok
        print(
            f"{umbral:6.3f}  {responde_ok:^11}  {abstiene_ok:^11}  "
            f"{total:2}/{len(PREGUNTAS)}"
        )
        if total > mejor_aciertos:
            mejor_umbral, mejor_aciertos = umbral, total

    # Se trunca hacia abajo, nunca se redondea: redondear al alza puede cruzar
    # el score de una pregunta respondible y silenciarla.
    sugerido = math.floor(mejor_umbral * 100) / 100
    print(
        f"\nMejor umbral con estos datos: {mejor_umbral:.3f} "
        f"({mejor_aciertos}/{len(PREGUNTAS)} aciertos)"
    )
    print(f"Para aplicarlo, en .env:  RAG_SCORE_MINIMO={sugerido:.2f}")

    minimo_respondible = min((s for s, _ in con_respuesta), default=None)
    if minimo_respondible is not None:
        margen = minimo_respondible - sugerido
        print(
            f"Score mas bajo entre las respondibles: {minimo_respondible:.3f} "
            f"(margen de {margen:.3f})."
        )
        if margen < 0.02:
            print(
                "AVISO: margen muy estrecho. El umbral esta ajustado a estos "
                "datos y una pregunta correcta ligeramente peor quedaria "
                "silenciada. Considera bajarlo y dejar que la abstencion la "
                "resuelva el centinela del prompt."
            )
    if args.simulado:
        print(
            "\nAVISO: scores de embeddings de juguete. Repite la calibracion con "
            "gemini-embedding-001 y la coleccion real antes de fijar el valor."
        )

    solapamiento = [
        (s, p) for s, p in sin_respuesta if s >= min(s for s, _ in con_respuesta)
    ]
    if solapamiento:
        print(f"\nPreguntas de abstencion con score alto ({len(solapamiento)}):")
        for score, pregunta in sorted(solapamiento, reverse=True)[:5]:
            print(f"  {score:.3f}  {pregunta[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
