"""Checkpoint persistente para reanudar la generación de embeddings."""

import hashlib
import json
import math
from pathlib import Path
from typing import Any


_CHECKPOINT_VERSION = 1


def _text_hash(text: str) -> str:
    """Calcula una huella estable del texto realmente enviado al modelo."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("El texto del chunk debe ser texto no vacío.")

    normalized_text = text.strip()
    return hashlib.sha256(
        normalized_text.encode("utf-8")
    ).hexdigest()


def _validate_vector(vector: Any) -> list[float]:
    """Convierte y valida un vector antes de guardarlo o reutilizarlo."""
    if not isinstance(vector, (list, tuple)) or not vector:
        raise ValueError("El vector debe ser una secuencia no vacía.")

    converted: list[float] = []

    for value in vector:
        if isinstance(value, bool):
            raise TypeError("Los valores del vector deben ser numéricos.")

        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise TypeError(
                "Los valores del vector deben ser numéricos."
            ) from error

        if not math.isfinite(number):
            raise ValueError(
                "El vector contiene valores NaN o infinitos."
            )

        converted.append(number)

    return converted


def _validate_chunk(chunk: dict) -> None:
    """Comprueba los campos necesarios para identificar el embedding."""
    if not isinstance(chunk, dict):
        raise TypeError("Cada chunk debe ser un diccionario.")

    for field in ("chunk_id", "text"):
        value = chunk.get(field)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"El chunk debe contener '{field}' como texto no vacío."
            )


class EmbeddingCheckpoint:
    """Guarda y recupera embeddings válidos entre ejecuciones.

    Una entrada solo se reutiliza cuando coinciden el modelo, el chunk_id y
    la huella SHA-256 del texto. De esta forma, modificar el texto o cambiar
    de modelo invalida automáticamente el vector anterior.
    """

    def __init__(
        self,
        path: str | Path,
        model: str,
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("El modelo del checkpoint no puede estar vacío.")

        self.path = Path(path)
        self.model = model.strip()
        self._entries: dict[str, dict] = {}

        self._load()

    def _load(self) -> None:
        """Carga un checkpoint existente y detecta archivos corruptos."""
        if not self.path.exists():
            return

        try:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"No se pudo leer el checkpoint {self.path}."
            ) from error

        if not isinstance(payload, dict):
            raise RuntimeError(
                f"El checkpoint {self.path} no contiene un objeto JSON."
            )

        if payload.get("version") != _CHECKPOINT_VERSION:
            raise RuntimeError(
                f"Versión de checkpoint no compatible en {self.path}."
            )

        stored_model = payload.get("model")
        entries = payload.get("entries")

        if not isinstance(stored_model, str) or not isinstance(entries, dict):
            raise RuntimeError(
                f"Estructura de checkpoint inválida en {self.path}."
            )

        # Un checkpoint de otro modelo no puede reutilizarse.
        if stored_model != self.model:
            return

        self._entries = entries

    def get(self, chunk: dict) -> list[float] | None:
        """Devuelve una copia del vector si la entrada sigue siendo válida."""
        _validate_chunk(chunk)

        chunk_id = chunk["chunk_id"].strip()
        entry = self._entries.get(chunk_id)

        if not isinstance(entry, dict):
            return None

        if entry.get("text_hash") != _text_hash(chunk["text"]):
            return None

        if entry.get("model") != self.model:
            return None

        try:
            vector = _validate_vector(entry.get("vector"))
        except (TypeError, ValueError):
            return None

        stored_dimension = entry.get("dimension")

        if (
            not isinstance(stored_dimension, int)
            or isinstance(stored_dimension, bool)
            or stored_dimension != len(vector)
        ):
            return None

        return list(vector)

    def save_batch(
        self,
        chunks: list[dict],
        vectors: list[list[float]],
    ) -> None:
        """Guarda atómicamente un lote sin eliminar los lotes anteriores."""
        if len(chunks) != len(vectors):
            raise ValueError(
                "La cantidad de chunks y vectores debe coincidir."
            )

        if not chunks:
            return

        validated_vectors: list[list[float]] = []

        for chunk, vector in zip(chunks, vectors, strict=True):
            _validate_chunk(chunk)
            validated_vectors.append(_validate_vector(vector))

        dimensions = {
            len(vector)
            for vector in validated_vectors
        }

        if len(dimensions) != 1:
            raise ValueError(
                "Los vectores del lote tienen dimensiones diferentes."
            )

        new_dimension = next(iter(dimensions))
        existing_dimensions = {
            entry.get("dimension")
            for entry in self._entries.values()
            if isinstance(entry, dict)
            and isinstance(entry.get("dimension"), int)
        }

        if existing_dimensions and existing_dimensions != {new_dimension}:
            raise ValueError(
                "Los vectores nuevos tienen dimensiones diferentes "
                "a las almacenadas."
            )

        for chunk, vector in zip(
            chunks,
            validated_vectors,
            strict=True,
        ):
            chunk_id = chunk["chunk_id"].strip()

            self._entries[chunk_id] = {
                "text_hash": _text_hash(chunk["text"]),
                "model": self.model,
                "dimension": len(vector),
                "vector": vector,
            }

        self._write_atomically()

    def _write_atomically(self) -> None:
        """Sustituye el archivo solo después de escribir un JSON completo."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "version": _CHECKPOINT_VERSION,
            "model": self.model,
            "entries": self._entries,
        }

        temporary_path = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )

        try:
            temporary_path.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            temporary_path.replace(self.path)
        except OSError as error:
            raise RuntimeError(
                f"No se pudo guardar el checkpoint {self.path}."
            ) from error

    def count(self) -> int:
        """Devuelve el número de embeddings almacenados para este modelo."""
        return len(self._entries)
