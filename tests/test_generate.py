"""Tests de generate.py: prompt, compuertas de abstencion y formato de salida.

No llaman a Gemini ni a ChromaDB: se inyectan una coleccion y un cliente falsos.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import retrieve as retrieve_module  # noqa: E402
from src.generate import (  # noqa: E402
    CENTINELA_SIN_EVIDENCIA,
    MENSAJE_ABSTENCION,
    build_prompt,
    generate_answer,
    rag_ask,
    responder,
)

CAMPOS_DE_SALIDA = {"respuesta", "fuentes", "citas", "chunks", "abstuvo",
                    "motivo_abstencion"}


def chunk(score, source="guia.pdf", texto="El parque abre de 6:00 a 22:00.", **extra):
    base = {
        "chunk_id": f"{source}__0000",
        "document_id": source.split(".")[0],
        "text": texto,
        "source": source,
        "chunk_index": 0,
        "category": "informacion_practica",
        "corpus_group": "itinerarios_informacion_practica_seguridad",
        "page": 1,
        "score": score,
    }
    base.update(extra)
    return base


class ColeccionFalsa:
    """Devuelve los chunks indicados sin tocar Chroma."""

    def __init__(self, chunks):
        self.chunks = chunks

    def query(self, **kwargs):
        n = kwargs.get("n_results", len(self.chunks))
        seleccion = self.chunks[:n]
        return {
            "documents": [[c["text"] for c in seleccion]],
            "metadatas": [
                [{k: v for k, v in c.items() if k not in ("text", "score")} for c in seleccion]
            ],
            "distances": [[1.0 - c["score"] for c in seleccion]],
        }


class ClienteFalso:
    """Imita client.models.generate_content() y registra el prompt recibido."""

    def __init__(self, texto="El parque abre de 6:00 a 22:00 [1]."):
        self.texto = texto
        self.prompt_recibido = None
        self.llamadas = 0
        self.models = SimpleNamespace(generate_content=self._generar)

    def _generar(self, model=None, contents=None):
        self.llamadas += 1
        self.prompt_recibido = contents
        return SimpleNamespace(text=self.texto)


@pytest.fixture(autouse=True)
def sin_llamadas_a_gemini(monkeypatch):
    """embed_query no debe llamar a la API en ningun test."""
    monkeypatch.setattr(retrieve_module, "embed_query", lambda texto: [0.1, 0.2, 0.3])


# --- build_prompt ----------------------------------------------------------


def test_prompt_incluye_instrucciones_contexto_y_pregunta():
    prompt = build_prompt("¿A que hora cierra?", [chunk(0.8)])
    assert "CONTEXTO:" in prompt
    assert "PREGUNTA: ¿A que hora cierra?" in prompt
    assert "El parque abre de 6:00 a 22:00." in prompt
    assert CENTINELA_SIN_EVIDENCIA in prompt


def test_prompt_numera_los_fragmentos_para_poder_citarlos():
    prompt = build_prompt("x", [chunk(0.8, "a.pdf"), chunk(0.7, "b.pdf")])
    assert "[1] fuente: a.pdf" in prompt
    assert "[2] fuente: b.pdf" in prompt


def test_prompt_incluye_pagina_y_categoria_cuando_existen():
    prompt = build_prompt("x", [chunk(0.8, page=4, category="seguridad")])
    assert "pagina 4" in prompt
    assert "categoria: seguridad" in prompt


def test_prompt_sin_chunks_lo_declara():
    assert "ningun fragmento" in build_prompt("x", [])


@pytest.mark.parametrize("pregunta", ["", "   ", None])
def test_prompt_rechaza_pregunta_vacia(pregunta):
    with pytest.raises((ValueError, TypeError)):
        build_prompt(pregunta, [chunk(0.8)])


# --- generate_answer -------------------------------------------------------


def test_generate_answer_usa_el_cliente_inyectado():
    cliente = ClienteFalso("respuesta del modelo")
    assert generate_answer("prompt de prueba", client=cliente) == "respuesta del modelo"
    assert cliente.llamadas == 1


def test_generate_answer_falla_si_el_modelo_devuelve_vacio():
    with pytest.raises(ValueError):
        generate_answer("prompt", client=ClienteFalso("   "))


@pytest.mark.parametrize("prompt", ["", "   ", None])
def test_generate_answer_rechaza_prompt_vacio(prompt):
    with pytest.raises((ValueError, TypeError)):
        generate_answer(prompt, client=ClienteFalso())


# --- compuerta 1: score ----------------------------------------------------


def test_score_alto_genera_respuesta():
    cliente = ClienteFalso()
    salida = responder(
        "¿A que hora cierra?",
        collection=ColeccionFalsa([chunk(0.82)]),
        client=cliente,
        score_minimo=0.30,
    )
    assert salida["abstuvo"] is False
    assert salida["respuesta"] == "El parque abre de 6:00 a 22:00 [1]."
    assert salida["fuentes"] == ["guia.pdf"]
    assert cliente.llamadas == 1


def test_score_bajo_se_abstiene_sin_llamar_al_modelo():
    cliente = ClienteFalso()
    salida = responder(
        "¿Que fauna hay en el estanque?",
        collection=ColeccionFalsa([chunk(0.12)]),
        client=cliente,
        score_minimo=0.30,
    )
    assert salida["abstuvo"] is True
    assert salida["respuesta"] == MENSAJE_ABSTENCION
    assert salida["fuentes"] == []
    assert cliente.llamadas == 0, "No debe gastarse una llamada al LLM."
    assert "score_bajo" in salida["motivo_abstencion"]


def test_la_abstencion_conserva_los_chunks_para_poder_depurar():
    salida = responder(
        "x",
        collection=ColeccionFalsa([chunk(0.10)]),
        client=ClienteFalso(),
        score_minimo=0.30,
    )
    assert salida["chunks"], "Los chunks recuperados siguen disponibles."


def test_coleccion_vacia_se_abstiene():
    salida = responder("x", collection=ColeccionFalsa([]), client=ClienteFalso())
    assert salida["abstuvo"] is True
    assert salida["motivo_abstencion"] == "sin_resultados"


def test_el_umbral_es_ajustable():
    coleccion = ColeccionFalsa([chunk(0.45)])
    assert responder("x", collection=coleccion, client=ClienteFalso(),
                     score_minimo=0.40)["abstuvo"] is False
    assert responder("x", collection=coleccion, client=ClienteFalso(),
                     score_minimo=0.60)["abstuvo"] is True


# --- compuerta 2: centinela ------------------------------------------------


def test_centinela_del_modelo_se_convierte_en_abstencion():
    salida = responder(
        "¿Que estilo tiene el palacio?",
        collection=ColeccionFalsa([chunk(0.75)]),
        client=ClienteFalso(CENTINELA_SIN_EVIDENCIA),
        score_minimo=0.30,
    )
    assert salida["abstuvo"] is True
    assert salida["respuesta"] == MENSAJE_ABSTENCION
    assert salida["motivo_abstencion"] == "el_modelo_no_vio_evidencia"


def test_centinela_se_detecta_aunque_venga_con_texto_alrededor():
    salida = responder(
        "x",
        collection=ColeccionFalsa([chunk(0.75)]),
        client=ClienteFalso(f"Lo siento, {CENTINELA_SIN_EVIDENCIA}."),
        score_minimo=0.30,
    )
    assert salida["abstuvo"] is True


# --- formato de salida -----------------------------------------------------


def test_la_salida_tiene_siempre_los_mismos_campos():
    coleccion = ColeccionFalsa([chunk(0.75)])
    respondida = responder("x", collection=coleccion, client=ClienteFalso(),
                           score_minimo=0.30)
    abstenida = responder("x", collection=ColeccionFalsa([chunk(0.05)]),
                          client=ClienteFalso(), score_minimo=0.30)
    assert CAMPOS_DE_SALIDA == set(respondida) == set(abstenida)


def test_las_fuentes_no_se_repiten_y_conservan_el_orden():
    coleccion = ColeccionFalsa(
        [chunk(0.9, "a.pdf"), chunk(0.8, "b.pdf"), chunk(0.7, "a.pdf")]
    )
    salida = responder("x", top_k=3, collection=coleccion,
                       client=ClienteFalso(), score_minimo=0.30)
    assert salida["fuentes"] == ["a.pdf", "b.pdf"]


def test_top_k_llega_hasta_el_prompt():
    cliente = ClienteFalso()
    coleccion = ColeccionFalsa(
        [chunk(0.9, "a.pdf"), chunk(0.8, "b.pdf"), chunk(0.7, "c.pdf")]
    )
    responder("x", top_k=2, collection=coleccion, client=cliente, score_minimo=0.30)
    assert "[1] fuente: a.pdf" in cliente.prompt_recibido
    assert "[2] fuente: b.pdf" in cliente.prompt_recibido
    assert "c.pdf" not in cliente.prompt_recibido


@pytest.mark.parametrize("pregunta", ["", "   ", None])
def test_responder_rechaza_pregunta_vacia(pregunta):
    with pytest.raises((ValueError, TypeError)):
        responder(pregunta, collection=ColeccionFalsa([chunk(0.8)]),
                  client=ClienteFalso())


def test_rag_ask_devuelve_solo_el_texto():
    texto = rag_ask(
        "x",
        collection=ColeccionFalsa([chunk(0.8)]),
        client=ClienteFalso("respuesta corta"),
        score_minimo=0.30,
    )
    assert texto == "respuesta corta"


def test_rag_ask_devuelve_el_mensaje_de_abstencion():
    texto = rag_ask(
        "x",
        collection=ColeccionFalsa([chunk(0.05)]),
        client=ClienteFalso(),
        score_minimo=0.30,
    )
    assert texto == MENSAJE_ABSTENCION


# --- integracion con el logging ------------------------------------------


def test_responder_registra_la_consulta(tmp_path, monkeypatch):
    """Cada llamada a responder() deja una linea en el fichero de registro."""
    import json

    from src import logging_utils

    ruta = tmp_path / "consultas.jsonl"
    monkeypatch.setattr(logging_utils, "RUTA_LOG", ruta)

    responder("¿A que hora cierra?", collection=ColeccionFalsa([chunk(0.82)]),
              client=ClienteFalso(), score_minimo=0.30)
    responder("¿Que fauna hay?", collection=ColeccionFalsa([chunk(0.05)]),
              client=ClienteFalso(), score_minimo=0.30)

    registros = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines()]
    assert len(registros) == 2
    assert registros[0]["abstuvo"] is False
    assert registros[1]["abstuvo"] is True
    assert "score_bajo" in registros[1]["motivo_abstencion"]
    assert registros[0]["score_top1"] == pytest.approx(0.82)
    assert registros[0]["tiempo_s"] >= 0


# --- correspondencia entre numeros de cita y fragmentos --------------------


def test_las_citas_siguen_la_numeracion_del_prompt():
    """El prompt numera 1..top_k, aunque los chunks sean del mismo documento."""
    coleccion = ColeccionFalsa(
        [chunk(0.9, "guia.pdf"), chunk(0.8, "guia.pdf"), chunk(0.7, "guia.pdf")]
    )
    salida = responder("x", top_k=3, collection=coleccion,
                       client=ClienteFalso(), score_minimo=0.30)
    assert [c["n"] for c in salida["citas"]] == [1, 2, 3]
    assert salida["fuentes"] == ["guia.pdf"], "fuentes agrupa por documento"
    assert len(salida["citas"]) == 3, "citas mantiene una entrada por fragmento"


def test_cada_cita_lleva_documento_pagina_y_chunk():
    coleccion = ColeccionFalsa([chunk(0.9, "guia.pdf")])
    cita = responder("x", collection=coleccion, client=ClienteFalso(),
                     score_minimo=0.30)["citas"][0]
    assert cita["source"] == "guia.pdf"
    assert cita["page"] == 1
    assert cita["chunk_id"] == "guia.pdf__0000"


def test_la_abstencion_no_lleva_citas():
    salida = responder("x", collection=ColeccionFalsa([chunk(0.05)]),
                       client=ClienteFalso(), score_minimo=0.30)
    assert salida["citas"] == []


def test_las_citas_llevan_el_nombre_legible_de_la_fuente():
    """El usuario no debe leer nombres de fichero."""
    coleccion = ColeccionFalsa(
        [chunk(0.8, "informacion_practica_guia_visitante_retiro.pdf")]
    )
    cita = responder("x", collection=coleccion, client=ClienteFalso(),
                     score_minimo=0.30)["citas"][0]
    assert cita["titulo"] == "Guía del visitante del Retiro"
    assert cita["oficial"] is True
    assert ".pdf" not in cita["texto"]
    assert cita["source"] == "informacion_practica_guia_visitante_retiro.pdf"


def test_el_prompt_pide_responder_en_el_idioma_de_la_pregunta():
    prompt = build_prompt("What time does the park close?", [chunk(0.8)])
    assert "mismo idioma" in prompt
