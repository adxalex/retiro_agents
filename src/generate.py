"""Generacion de respuesta anclada al contexto recuperado.

Flujo de responder():

    pregunta -> retrieve() -> compuerta de score -> build_prompt() ->
    generate_answer() -> compuerta del centinela -> dict de salida

La abstencion tiene dos compuertas, porque Chroma siempre devuelve vecinos,
tambien cuando el corpus no contiene la respuesta:

1. Compuerta de retrieval: si el mejor score no llega a SCORE_MINIMO, se
   abstiene sin llamar al LLM. Es determinista y ahorra coste.
2. Compuerta de generacion: el prompt obliga al modelo a devolver el
   centinela SIN_EVIDENCIA cuando el contexto no sostiene la respuesta.

SCORE_MINIMO se lee de .env (RAG_SCORE_MINIMO). El valor por defecto es
provisional: hay que fijarlo comparando la distribucion de scores de las
preguntas respondibles y las de abstencion de queries/, con el indice real y
gemini-embedding-001.
"""

from __future__ import annotations

import os
from typing import Any

from config import LLM_MODEL, TOP_K
from src.gemini_auth import get_gemini_client
from src.fuentes import describir_citas
from src.logging_utils import Cronometro, log_query
from src.retrieve import retrieve

CENTINELA_SIN_EVIDENCIA = "SIN_EVIDENCIA"

# Texto fijo en espanol. Si el banco de preguntas crece en otros idiomas,
# convendria traducirlo segun el idioma detectado en la consulta.
MENSAJE_ABSTENCION = (
    "No he encontrado esa informacion en los documentos del Parque del Retiro "
    "que tengo disponibles. Puedes consultarlo en la web municipal "
    "(madrid.es) o en esmadrid.com."
)

# Sin calibrar todavia. 0.0 significa que la compuerta de score no descarta nada
# y la abstencion recae en el centinela del prompt: es preferible a inventarse un
# umbral que silencie respuestas correctas. Calibrarlo con
# scripts/validation/calibrar_umbral.py sobre el indice real y fijarlo en .env.
SCORE_MINIMO = float(os.getenv("RAG_SCORE_MINIMO", "0.0"))

INSTRUCCIONES = f"""Eres el asistente del Parque de El Retiro de Madrid. Hablas con un visitante.

Como responder:
1. Empieza por la respuesta util. La primera frase debe contestar lo que se pregunta, con el dato concreto: el lugar, la hora, la distancia o el nombre.
2. Responde en el mismo idioma en que esta escrita la pregunta. Si preguntan en ingles, responde en ingles; si preguntan en catalan, en catalan.
3. Se breve: entre una y cuatro frases. Escribe como se lo explicarias a alguien en el parque.
4. Usa unicamente la informacion del CONTEXTO. No uses conocimiento propio.
5. Cita los fragmentos con [1], [2] al final de la frase que sostienen.
6. Si el contexto no contiene la respuesta, responde exactamente {CENTINELA_SIN_EVIDENCIA} y nada mas.
7. Si el contexto solo responde una parte, contesta esa parte primero y despues di brevemente que del resto no tienes informacion.

Advertencias (van al FINAL, nunca al principio):
8. Avisa solo cuando el dato pueda haber cambiado y eso afecte a la visita: precios, horarios, obras o cierres temporales con varios anos de antiguedad. Una frase de menos de ocho palabras: "Es un dato de 2017, conviene confirmarlo."
9. No valores la fiabilidad de las fuentes en la respuesta. No digas si son oficiales o no, ni quien las publico, ni la fecha exacta de publicacion: eso aparece en la lista de fuentes que acompana a la respuesta.
10. No expliques que falta en el corpus ni como estan organizados los documentos. Al visitante no le sirve.
11. No inventes horarios, precios, distancias ni nombres que no aparezcan en el contexto."""


def _formatear_chunk(numero: int, chunk: dict) -> str:
    """Convierte un chunk en un fragmento numerado y citable del prompt."""
    cabecera = f"[{numero}] fuente: {chunk.get('source', 'desconocida')}"
    if chunk.get("page"):
        cabecera += f", pagina {chunk['page']}"
    if chunk.get("category"):
        cabecera += f", categoria: {chunk['category']}"
    return f"{cabecera}\n{chunk.get('text', '').strip()}"


def build_prompt(pregunta: str, chunks: list[dict]) -> str:
    """Construye el prompt con instrucciones, contexto numerado y pregunta."""
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacia.")

    if chunks:
        contexto = "\n\n".join(
            _formatear_chunk(numero, chunk)
            for numero, chunk in enumerate(chunks, start=1)
        )
    else:
        contexto = "(no se ha recuperado ningun fragmento)"

    return (
        f"{INSTRUCCIONES}\n\n"
        f"CONTEXTO:\n{contexto}\n\n"
        f"PREGUNTA: {pregunta.strip()}\n\n"
        "RESPUESTA:"
    )


def generate_answer(prompt: str, client: Any | None = None) -> str:
    """Llama al LLM con el prompt construido y devuelve el texto."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("El prompt no puede estar vacio.")

    client = client if client is not None else get_gemini_client()
    respuesta = client.models.generate_content(
        model=LLM_MODEL,
        contents=prompt,
    )
    texto = getattr(respuesta, "text", None)
    if not texto or not texto.strip():
        raise ValueError("El modelo devolvio una respuesta vacia.")
    return texto.strip()


def _fuentes_de(chunks: list[dict]) -> list[str]:
    """Lista de documentos citados, sin repetir y en el orden recuperado."""
    return list(dict.fromkeys(chunk.get("source", "desconocida") for chunk in chunks))


def _citas_de(chunks: list[dict]) -> list[dict]:
    """Mapa de cada numero de cita del prompt a su fragmento.

    El prompt numera los fragmentos del 1 al top_k, asi que el modelo puede
    citar [3] aunque los tres fragmentos vengan del mismo documento. La lista
    'fuentes' agrupa por documento y no sirve para resolver esas citas: por eso
    se expone tambien esta correspondencia numero -> fragmento.
    """
    return [
        {
            "n": numero,
            "source": chunk.get("source", "desconocida"),
            "page": chunk.get("page"),
            "chunk_id": chunk.get("chunk_id"),
            "score": chunk.get("score"),
        }
        for numero, chunk in enumerate(chunks, start=1)
    ]


def _abstencion(pregunta: str, chunks: list[dict], motivo: str) -> dict:
    return {
        "respuesta": MENSAJE_ABSTENCION,
        "fuentes": [],
        "citas": [],
        "chunks": chunks,
        "abstuvo": True,
        "motivo_abstencion": motivo,
    }


def responder(
    pregunta: str,
    top_k: int = TOP_K,
    score_minimo: float | None = None,
    collection: Any | None = None,
    client: Any | None = None,
    where: dict | None = None,
) -> dict:
    """Responde una pregunta con RAG, o se abstiene si no hay evidencia.

    Devuelve {"respuesta", "fuentes", "chunks", "abstuvo", "motivo_abstencion"}.
    collection y client son inyectables para los tests.
    """
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacia.")

    umbral = SCORE_MINIMO if score_minimo is None else float(score_minimo)

    with Cronometro() as crono:
        chunks = retrieve(pregunta, top_k=top_k, collection=collection, where=where)
        salida = _responder_con_chunks(pregunta, chunks, umbral, client)

    log_query(
        pregunta=pregunta,
        k=top_k,
        n_chunks=len(chunks),
        tiempo=crono.segundos,
        modelo=LLM_MODEL,
        abstuvo=salida["abstuvo"],
        motivo_abstencion=salida["motivo_abstencion"],
        score_top1=round(chunks[0]["score"], 4) if chunks else None,
        fuentes=salida["fuentes"],
    )
    return salida


def _responder_con_chunks(
    pregunta: str,
    chunks: list[dict],
    umbral: float,
    client: Any | None,
) -> dict:
    """Aplica las dos compuertas de abstencion sobre los chunks recuperados."""
    if not chunks:
        return _abstencion(pregunta, chunks, "sin_resultados")

    mejor_score = chunks[0]["score"]
    if mejor_score < umbral:
        return _abstencion(
            pregunta, chunks, f"score_bajo ({mejor_score:.3f} < {umbral:.3f})"
        )

    texto = generate_answer(build_prompt(pregunta, chunks), client=client)

    if CENTINELA_SIN_EVIDENCIA in texto.upper():
        return _abstencion(pregunta, chunks, "el_modelo_no_vio_evidencia")

    return {
        "respuesta": texto,
        "fuentes": _fuentes_de(chunks),
        "citas": describir_citas(_citas_de(chunks)),
        "chunks": chunks,
        "abstuvo": False,
        "motivo_abstencion": None,
    }


def rag_ask(consulta: str, **kwargs: Any) -> str:
    """Envuelve responder() devolviendo solo el texto de la respuesta."""
    return responder(consulta, **kwargs)["respuesta"]
