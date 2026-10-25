"""Tests del catalogo de fuentes legibles."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.fuentes import CATALOGO, describir, describir_citas  # noqa: E402


def test_una_fuente_oficial_se_describe_con_su_organismo():
    d = describir("informacion_practica_guia_visitante_retiro.pdf")
    assert d["titulo"] == "Guía del visitante del Retiro"
    assert d["organismo"] == "esMadrid, Turismo de Madrid"
    assert d["oficial"] is True
    assert d["etiqueta"] == "fuente oficial"
    assert "oficial" not in d["texto"], "La etiqueta va aparte, no en el texto."


def test_una_fuente_no_oficial_queda_marcada():
    d = describir("itinerarios_running_retiro_.pdf")
    assert d["oficial"] is False
    assert d["etiqueta"] == "fuente no oficial"
    assert d["texto"] == "Circuitos para correr en el Retiro · VG Running"


def test_un_documento_fuera_del_catalogo_no_rompe():
    """Un documento nuevo se muestra legible, sin nombre de fichero crudo."""
    d = describir("otro__documento_de_prueba__madrid__v01.md")
    assert ".md" not in d["texto"]
    assert "_" not in d["titulo"]
    assert d["oficial"] is False, "Por defecto no se presume oficial."


def test_el_catalogo_no_deja_titulos_vacios():
    for source, (titulo, _organismo, _oficial) in CATALOGO.items():
        assert titulo.strip(), f"{source} sin titulo legible."


def test_las_citas_conservan_su_numero_y_anaden_el_titulo():
    citas = describir_citas([
        {"n": 1, "source": "seguridad_protocolo_alertas_retiro.pdf", "page": 2},
        {"n": 2, "source": "retiro_historia.md", "page": None},
    ])
    assert [c["n"] for c in citas] == [1, 2]
    assert "Protocolo de alertas" in citas[0]["titulo"]
    assert "página 2" in citas[0]["texto"]
    assert "página" not in citas[1]["texto"]


def test_describir_citas_no_pierde_los_campos_originales():
    citas = describir_citas([
        {"n": 1, "source": "retiro_jardines.md", "chunk_id": "x__0001", "score": 0.74},
    ])
    assert citas[0]["chunk_id"] == "x__0001"
    assert citas[0]["score"] == 0.74
