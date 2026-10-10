"""Logging basico de las consultas realizadas al sistema.

Cada consulta se anota en dos sitios:

- Por pantalla, una linea legible para ver que esta pasando.
- En output/consultas.jsonl, una linea JSON por consulta, para poder contarlas
  despues y llevar las cifras al informe.

El formato JSONL (un JSON por linea) se elige porque se puede ir anadiendo sin
releer el fichero y se abre con pandas en una linea:

    pandas.read_json("output/consultas.jsonl", lines=True)

output/ esta en .gitignore, asi que los registros no se versionan.
El fichero se puede cambiar con la variable de entorno RAG_LOG_FILE.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUTA_LOG = Path(os.getenv("RAG_LOG_FILE", "output/consultas.jsonl"))

_logger = logging.getLogger("retiro_rag")
if not _logger.handlers:
    _consola = logging.StreamHandler()
    _consola.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                                            datefmt="%H:%M:%S"))
    _logger.addHandler(_consola)
    _logger.setLevel(logging.INFO)


def log_query(
    pregunta: str,
    k: int,
    n_chunks: int,
    tiempo: float,
    modelo: str,
    abstuvo: bool = False,
    **extra: Any,
) -> dict:
    """Registra una consulta y devuelve el registro guardado.

    pregunta: la consulta del usuario.
    k: el top_k utilizado.
    n_chunks: cuantos chunks se recuperaron.
    tiempo: segundos que tardo la consulta.
    modelo: el modelo de generacion utilizado.
    abstuvo: True si el sistema no respondio por falta de evidencia.
    extra: campos opcionales (motivo_abstencion, score_top1, fuentes...).

    Nunca interrumpe la consulta: si el fichero no se puede escribir, avisa y
    sigue. Un fallo de registro no debe tumbar una respuesta al usuario.
    """
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pregunta": pregunta,
        "top_k": k,
        "n_chunks": n_chunks,
        "tiempo_s": round(float(tiempo), 3),
        "modelo": modelo,
        "abstuvo": bool(abstuvo),
    }
    registro.update(extra)

    estado = "ABSTENCION" if abstuvo else "RESPUESTA"
    _logger.info(
        "%s | %s | top_k=%d chunks=%d %.2fs | %s",
        estado,
        pregunta[:70],
        k,
        n_chunks,
        registro["tiempo_s"],
        modelo,
    )

    try:
        RUTA_LOG.parent.mkdir(parents=True, exist_ok=True)
        with RUTA_LOG.open("a", encoding="utf-8") as fichero:
            fichero.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except OSError as error:
        _logger.warning("No se pudo escribir en %s: %s", RUTA_LOG, error)

    return registro


class Cronometro:
    """Mide cuanto tarda un bloque de codigo.

        with Cronometro() as crono:
            ...
        crono.segundos
    """

    def __enter__(self) -> "Cronometro":
        self._inicio = time.perf_counter()
        self.segundos = 0.0
        return self

    def __exit__(self, *_excepcion: object) -> None:
        self.segundos = time.perf_counter() - self._inicio


def resumen_de_consultas(ruta: Path | str | None = None) -> dict:
    """Lee el fichero de registros y devuelve un resumen para el informe."""
    ruta = Path(ruta) if ruta else RUTA_LOG
    if not ruta.exists():
        return {"total": 0, "abstenciones": 0, "tasa_abstencion": 0.0,
                "tiempo_medio_s": 0.0}

    registros = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            registros.append(json.loads(linea))
        except json.JSONDecodeError:
            _logger.warning("Linea ilegible en %s, se omite.", ruta)

    total = len(registros)
    if total == 0:
        return {"total": 0, "abstenciones": 0, "tasa_abstencion": 0.0,
                "tiempo_medio_s": 0.0}

    abstenciones = sum(1 for r in registros if r.get("abstuvo"))
    tiempos = [r.get("tiempo_s", 0.0) for r in registros]
    return {
        "total": total,
        "abstenciones": abstenciones,
        "tasa_abstencion": round(abstenciones / total, 3),
        "tiempo_medio_s": round(sum(tiempos) / total, 3),
    }
