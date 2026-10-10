"""Generación validada de embeddings Gemini para el RAG de El Retiro."""

import math
import time
from collections import defaultdict
from typing import Any

from google import genai
from google.genai import types

from config import (
    EMBED_BATCH_SIZE,
    EMBEDDING_MODEL,
    EMBED_MAX_RETRIES,
    EMBED_RETRY_DELAY_SECONDS,
)
from src.gemini_auth import get_gemini_client
from src.embedding_cache import EmbeddingCheckpoint

_DOCUMENT_TASK_TYPE = "RETRIEVAL_DOCUMENT"
_QUERY_TASK_TYPE = "RETRIEVAL_QUERY"


def _es_error_de_cuota(error: Exception) -> bool:
    """Indica si Gemini rechazó temporalmente la petición por cuota."""
    status_code = getattr(error, "status_code", None)
    return (
        status_code == 429
        or "RESOURCE_EXHAUSTED" in str(error)
        or "429" in str(error)
    )


def _validar_configuracion_reintentos() -> None:
    """Valida los parámetros utilizados para recuperar errores de cuota."""
    if (
        not isinstance(EMBED_MAX_RETRIES, int)
        or isinstance(EMBED_MAX_RETRIES, bool)
        or EMBED_MAX_RETRIES < 0
    ):
        raise ValueError(
            "EMBED_MAX_RETRIES debe ser un entero mayor o igual que 0."
        )

    if (
        not isinstance(EMBED_RETRY_DELAY_SECONDS, (int, float))
        or isinstance(EMBED_RETRY_DELAY_SECONDS, bool)
        or not math.isfinite(EMBED_RETRY_DELAY_SECONDS)
        or EMBED_RETRY_DELAY_SECONDS < 0
    ):
        raise ValueError(
            "EMBED_RETRY_DELAY_SECONDS debe ser un número finito "
            "mayor o igual que 0."
        )


def _extraer_vector(embedding_obj: Any) -> list[float]:
    """Convierte la respuesta del SDK en una lista de números."""
    values = getattr(embedding_obj, "values", embedding_obj)
    if values is None:
        raise ValueError("Gemini devolvió un embedding sin valores.")
    try:
        return [float(value) for value in values]
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Gemini devolvió un embedding no numérico.") from error


def _validar_vectores(vectores: list[list[float]], esperados: int) -> int:
    """Comprueba cardinalidad, dimensión y valores numéricos finitos."""
    if len(vectores) != esperados:
        raise RuntimeError(
            "Número inesperado de embeddings: "
            f"esperados={esperados}, recibidos={len(vectores)}."
        )
    if not vectores:
        raise RuntimeError("Gemini no devolvió embeddings.")

    dimensiones = {len(vector) for vector in vectores}
    if len(dimensiones) != 1:
        raise ValueError(
            f"Dimensiones de embedding inconsistentes: {dimensiones}.")

    dimension = next(iter(dimensiones))
    if dimension == 0:
        raise ValueError("Los embeddings no pueden estar vacíos.")
    if any(not math.isfinite(value) for vector in vectores for value in vector):
        raise ValueError("Los embeddings contienen NaN o valores infinitos.")
    return dimension


def _embeddear_lote(
    client: genai.Client,
    textos: list[str],
    task_type: str,
) -> list[list[float]]:
    if not textos:
        return []

    contents = [types.Content(parts=[types.Part(text=texto)])
                for texto in textos]
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=contents,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    embeddings = getattr(result, "embeddings", None)
    if embeddings is None:
        raise RuntimeError("La respuesta de Gemini no contiene 'embeddings'.")

    vectores = [_extraer_vector(embedding) for embedding in embeddings]
    _validar_vectores(vectores, esperados=len(textos))
    return vectores


def _embeddear_lote_con_reintentos(
    client: genai.Client,
    textos: list[str],
    task_type: str,
) -> list[list[float]]:
    """Reintenta el lote actual cuando Gemini devuelve un error 429."""
    intento = 0

    while True:
        try:
            return _embeddear_lote(
                client,
                textos,
                task_type=task_type,
            )
        except Exception as error:
            if not _es_error_de_cuota(error):
                raise

            if intento >= EMBED_MAX_RETRIES:
                raise

            intento += 1
            print(
                "[EMBED] cuota temporal agotada; "
                f"esperando {EMBED_RETRY_DELAY_SECONDS:.0f} s "
                f"antes del reintento {intento}/{EMBED_MAX_RETRIES}"
            )
            time.sleep(EMBED_RETRY_DELAY_SECONDS)


def _validar_chunks(chunks: list[dict]) -> None:
    for posicion, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            raise TypeError(
                f"El chunk en posición {posicion} debe ser un diccionario.")
        for campo in ("chunk_id", "document_id", "text"):
            if campo not in chunk:
                raise ValueError(
                    f"El chunk en posición {posicion} no contiene '{campo}'.")
            if not isinstance(chunk[campo], str) or not chunk[campo].strip():
                raise ValueError(
                    f"El campo '{campo}' del chunk en posición {posicion} "
                    "debe ser texto no vacío."
                )


def _validar_batch_size() -> None:
    if (
        not isinstance(EMBED_BATCH_SIZE, int)
        or isinstance(EMBED_BATCH_SIZE, bool)
        or EMBED_BATCH_SIZE <= 0
    ):
        raise ValueError("EMBED_BATCH_SIZE debe ser un entero mayor que 0.")


def embed_chunks(
    chunks: list[dict],
    client: genai.Client | None = None,
    checkpoint: EmbeddingCheckpoint | None = None,
) -> list[dict]:
    """Añade un vector a cada chunk, reutilizando checkpoints válidos.

    Los embeddings recuperados y los recién generados se devuelven en el
    mismo orden que los chunks de entrada. Cada lote nuevo se guarda en el
    checkpoint inmediatamente después de validarlo.
    """
    if not chunks:
        return []

    _validar_chunks(chunks)
    _validar_batch_size()
    _validar_configuracion_reintentos()

    inicio = time.perf_counter()

    vectores_por_posicion: list[list[float] | None] = [
        None
        for _ in chunks
    ]
    pendientes: list[tuple[int, dict]] = []
    reutilizados = 0

    for posicion, chunk in enumerate(chunks):
        vector_guardado = (
            checkpoint.get(chunk)
            if checkpoint is not None
            else None
        )

        if vector_guardado is None:
            pendientes.append((posicion, chunk))
        else:
            vectores_por_posicion[posicion] = vector_guardado
            reutilizados += 1

    if pendientes:
        client = (
            client
            if client is not None
            else get_gemini_client()
        )

    generados = 0

    for numero_lote, inicio_lote in enumerate(
        range(0, len(pendientes), EMBED_BATCH_SIZE),
        start=1,
    ):
        elementos_lote = pendientes[
            inicio_lote: inicio_lote + EMBED_BATCH_SIZE
        ]
        chunks_lote = [
            chunk
            for _, chunk in elementos_lote
        ]
        textos_lote = [
            chunk["text"].strip()
            for chunk in chunks_lote
        ]

        try:
            vectores_lote = _embeddear_lote_con_reintentos(
                client,
                textos_lote,
                task_type=_DOCUMENT_TASK_TYPE,
            )

            if checkpoint is not None:
                checkpoint.save_batch(
                    chunks_lote,
                    vectores_lote,
                )

            for (
                posicion_original,
                _,
            ), vector in zip(
                elementos_lote,
                vectores_lote,
                strict=True,
            ):
                vectores_por_posicion[posicion_original] = vector

            generados += len(vectores_lote)

        except Exception as error:
            inicio_pendiente = inicio_lote
            final_pendiente = inicio_lote + len(elementos_lote)

            raise RuntimeError(
                f"Falló el lote de embeddings {numero_lote} "
                f"(chunks pendientes "
                f"{inicio_pendiente}:{final_pendiente})."
            ) from error

    if any(vector is None for vector in vectores_por_posicion):
        raise RuntimeError(
            "No se obtuvo un vector para todos los chunks."
        )

    vectores = [
        vector
        for vector in vectores_por_posicion
        if vector is not None
    ]

    dimension = _validar_vectores(
        vectores,
        esperados=len(chunks),
    )
    latencia_ms = (time.perf_counter() - inicio) * 1000

    print(
        f"[EMBED] {len(chunks)} chunks · "
        f"reutilizados={reutilizados} · "
        f"generados={generados} · "
        f"modelo={EMBEDDING_MODEL} · "
        f"dim={dimension} · "
        f"{latencia_ms:.0f} ms"
    )

    return [
        {
            **chunk,
            "vector": vector,
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dimension": dimension,
        }
        for chunk, vector in zip(
            chunks,
            vectores,
            strict=True,
        )
    ]


def embed_query(
    text: str,
    client: genai.Client | None = None,
) -> list[float]:
    """Genera el vector de una consulta en el espacio del índice documental."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("El texto de la consulta no puede estar vacío.")
    client = client if client is not None else get_gemini_client()
    return _embeddear_lote(
        client,
        [text.strip()],
        task_type=_QUERY_TASK_TYPE,
    )[0]


def _repartir_proporcional(total: int, tamanos: list[int]) -> list[int]:
    """Reparte un cupo mediante restos mayores, respetando capacidades."""
    if total < 0:
        raise ValueError("total no puede ser negativo.")
    if any(tamano < 0 for tamano in tamanos):
        raise ValueError("Los tamaños de grupo no pueden ser negativos.")
    if not tamanos or total == 0 or sum(tamanos) == 0:
        return [0] * len(tamanos)

    total = min(total, sum(tamanos))
    cupos = [0] * len(tamanos)

    # Cuando hay capacidad, reserva una posición por cada grupo no vacío.
    grupos_no_vacios = [i for i, tamano in enumerate(tamanos) if tamano > 0]
    if total >= len(grupos_no_vacios):
        for indice in grupos_no_vacios:
            cupos[indice] = 1

    restante = total - sum(cupos)
    while restante > 0:
        capacidades = [tamanos[i] - cupos[i] for i in range(len(tamanos))]
        capacidad_total = sum(capacidades)
        if capacidad_total == 0:
            break

        ideales = [restante * capacidad /
                   capacidad_total for capacidad in capacidades]
        incremento = [min(capacidades[i], int(ideales[i]))
                      for i in range(len(tamanos))]
        asignado = sum(incremento)
        for i, valor in enumerate(incremento):
            cupos[i] += valor
        restante -= asignado

        if restante:
            orden = sorted(
                range(len(tamanos)),
                key=lambda i: (
                    ideales[i] - int(ideales[i]), capacidades[i], -i),
                reverse=True,
            )
            for i in orden:
                if restante == 0:
                    break
                if cupos[i] < tamanos[i]:
                    cupos[i] += 1
                    restante -= 1
    return cupos


def limitar_chunks(
    chunks: list[dict],
    max_chunks: int | None,
    agrupar_por: str = "corpus_group",
) -> list[dict]:
    """Aplica un límite experimental reduciendo el sesgo por orden global.

    Solo se garantiza al menos un chunk por grupo no vacío cuando el límite es
    igual o superior al número de grupos. En operación normal debe utilizarse
    ``max_chunks=None`` para indexar todo el corpus aprobado.
    """
    if max_chunks is not None:
        if not isinstance(max_chunks, int) or isinstance(max_chunks, bool):
            raise TypeError("max_chunks debe ser un entero o None.")
        if max_chunks < 0:
            raise ValueError("max_chunks no puede ser negativo.")
    if not isinstance(agrupar_por, str) or not agrupar_por.strip():
        raise ValueError("agrupar_por debe ser un nombre de campo no vacío.")
    if max_chunks is None or len(chunks) <= max_chunks:
        return list(chunks)

    por_grupo: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        valor = chunk.get(agrupar_por)
        nombre_grupo = str(valor).strip() if valor is not None else "sin_grupo"
        por_grupo[nombre_grupo or "sin_grupo"].append(chunk)

    grupos = list(por_grupo.items())
    cupos = _repartir_proporcional(
        max_chunks, [len(items) for _, items in grupos])
    seleccionados: list[dict] = []
    descartados: dict[str, int] = {}
    for (nombre, items), cupo in zip(grupos, cupos, strict=True):
        seleccionados.extend(items[:cupo])
        if cupo < len(items):
            descartados[nombre] = len(items) - cupo

    print(
        f"[LIMITE] max_chunks={max_chunks} ({agrupar_por}): "
        f"{len(seleccionados)}/{len(chunks)} chunks seleccionados"
    )
    if descartados:
        print(f"[LIMITE] excluidos por grupo: {descartados}")
    return seleccionados
