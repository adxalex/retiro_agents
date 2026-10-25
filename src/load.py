"""Carga de documentos crudos desde DATA_DIR (PDF, Markdown y CSV) y los
convierte en LoadedDocument segun el contrato compartido del equipo.
"""

import csv
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

CARPETAS_EXCLUIDAS = {"flora_fauna"}
# Vocabulario cerrado de category/corpus_group definido en el contrato.
CATEGORIAS_VALIDAS = {
    "historia", "monumentos", "jardines", "flora_fauna", "arte_cultura",
    "actividades", "itinerarios", "informacion_practica", "seguridad",
}
CORPUS_GROUPS_VALIDOS = {
    "historia_monumentos_jardines",
    "flora_fauna_arte_cultura_actividades",
    "itinerarios_informacion_practica_seguridad",
}

# Manifiesto: asigna category/corpus_group a cada archivo Markdown o PDF.
# Los archivos CSV llevan su propia categoria/corpus_group por fila y no
# necesitan entrada aqui.
MANIFIESTO = {
    "retiro_historia.md": {
        "category": "historia",
        "corpus_group": "historia_monumentos_jardines",
    },
    "retiro_jardines.md": {
        "category": "jardines",
        "corpus_group": "historia_monumentos_jardines",
    },
    "retiro_palacio_cristal_velazquez.md": {
        "category": "monumentos",
        "corpus_group": "historia_monumentos_jardines",
    },
    "actividades__guia_retiro__fuentes_mixtas__v01.md": {
        "category": "actividades",
        "corpus_group": "flora_fauna_arte_cultura_actividades",
    },
    "arte_cultura__palacio_cristal_velazquez__museo_reina_sofia__v01.md": {
        "category": "arte_cultura",
        "corpus_group": "flora_fauna_arte_cultura_actividades",
    },
    "arte_cultura__retiro_paisaje_de_la_luz__fuentes_academicas_unesco__v01.md": {
        "category": "arte_cultura",
        "corpus_group": "flora_fauna_arte_cultura_actividades",
    },
    "flora_fauna__fauna_estanque_grande_retiro__fuentes_contrastadas__v01.md": {
        "category": "flora_fauna",
        "corpus_group": "flora_fauna_arte_cultura_actividades",
    },
    "flora_fauna__guia_aves_comunes__madrid__v01.pdf": {
        "category": "flora_fauna",
        "corpus_group": "flora_fauna_arte_cultura_actividades",
    },
    "flora_fauna__plan_director_arbolado__madrid__v01.pdf": {
        "category": "flora_fauna",
        "corpus_group": "flora_fauna_arte_cultura_actividades",
    },
    "flora_fauna__resumen_inventario_arbolado_retiro__madrid__v01.md": {
        "category": "flora_fauna",
        "corpus_group": "flora_fauna_arte_cultura_actividades",
    },
    "flora_fauna__senda_botanica__madrid__v01.pdf": {
        "category": "flora_fauna",
        "corpus_group": "flora_fauna_arte_cultura_actividades",
    },
    "itinerarios_pie_retiro_.pdf": {
        "category": "itinerarios",
        "corpus_group": "itinerarios_informacion_practica_seguridad",
    },
    "itinerarios_running_retiro_.pdf": {
        "category": "itinerarios",
        "corpus_group": "itinerarios_informacion_practica_seguridad",
    },
    "informacion_practica_bicicleta_retiro.pdf": {
        "category": "informacion_practica",
        "corpus_group": "itinerarios_informacion_practica_seguridad",
    },
    "informacion_practica_guia_visitante_retiro.pdf": {
        "category": "informacion_practica",
        "corpus_group": "itinerarios_informacion_practica_seguridad",
    },
    "seguridad_protocolo_alertas_retiro.pdf": {
        "category": "seguridad",
        "corpus_group": "itinerarios_informacion_practica_seguridad",
    },
}


def _slugify(nombre: str) -> str:
    """Convierte un nombre en un slug estable: minusculas, sin tildes,
    sin espacios ni caracteres especiales.
    """
    sin_tildes = unicodedata.normalize("NFKD", nombre)
    sin_tildes = sin_tildes.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", sin_tildes).strip("-").lower()
    return slug


def _document_id_desde_archivo(ruta: Path) -> str:
    return _slugify(ruta.stem)


def _validar_categoria(category: str, corpus_group: str, origen: str) -> None:
    if category not in CATEGORIAS_VALIDAS:
        raise ValueError(f"category invalida en {origen}: {category!r}")
    if corpus_group not in CORPUS_GROUPS_VALIDOS:
        raise ValueError(
            f"corpus_group invalido en {origen}: {corpus_group!r}")


def _leer_markdown(ruta: Path) -> list[dict]:
    """Un archivo .md produce un unico LoadedDocument (no tiene paginas)."""
    if ruta.name not in MANIFIESTO:
        raise ValueError(f"{ruta.name} no tiene entrada en MANIFIESTO")

    texto = ruta.read_text(encoding="utf-8").strip()
    if not texto:
        raise ValueError(f"{ruta.name} esta vacio")

    meta = MANIFIESTO[ruta.name]
    _validar_categoria(meta["category"], meta["corpus_group"], ruta.name)

    documento = {
        "document_id": _document_id_desde_archivo(ruta),
        "text": texto,
        "source": ruta.name,
        "category": meta["category"],
        "corpus_group": meta["corpus_group"],
    }
    return [documento]


def _leer_pdf(ruta: Path) -> list[dict]:
    """Un PDF produce un LoadedDocument por pagina, con page 1-based."""
    if ruta.name not in MANIFIESTO:
        raise ValueError(f"{ruta.name} no tiene entrada en MANIFIESTO")

    meta = MANIFIESTO[ruta.name]
    _validar_categoria(meta["category"], meta["corpus_group"], ruta.name)

    reader = PdfReader(str(ruta))
    document_id_base = _document_id_desde_archivo(ruta)

    documentos = []
    for numero_pagina, pagina in enumerate(reader.pages, start=1):
        texto = (pagina.extract_text() or "").strip()
        if not texto:
            continue  # pagina sin texto extraible (ej. escaneada); se omite

        documentos.append({
            "document_id": document_id_base,
            "text": texto,
            "source": ruta.name,
            "category": meta["category"],
            "corpus_group": meta["corpus_group"],
            "page": numero_pagina,
        })

    if not documentos:
        raise ValueError(
            f"{ruta.name} no tiene texto extraible en ninguna pagina")

    return documentos


def _leer_csv(ruta: Path) -> list[dict]:
    """Cada fila del CSV produce un LoadedDocument. category/corpus_group
    se leen de las columnas del propio archivo, no del MANIFIESTO.
    """
    documentos = []
    with ruta.open(encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f)
        for i, fila in enumerate(lector):
            texto = (fila.get("descripcion") or "").strip()
            if not texto:
                continue

            category = fila["categoria"]
            corpus_group = fila["corpus_group"]
            _validar_categoria(category, corpus_group, f"{ruta.name} fila {i}")

            nombre = fila["nombre"]
            documentos.append({
                "document_id": f"{_document_id_desde_archivo(ruta)}-{_slugify(nombre)}",
                "text": f"{nombre}: {texto}",
                "source": ruta.name,
                "category": category,
                "corpus_group": corpus_group,
            })

    if not documentos:
        raise ValueError(f"{ruta.name} no produjo ningun documento valido")

    return documentos


def _extract_text(path: Path) -> list[dict]:
    """Despacha segun extension y devuelve la lista de LoadedDocument
    correspondiente a ese archivo.
    """
    if path.suffix == ".md":
        return _leer_markdown(path)
    if path.suffix == ".pdf":
        return _leer_pdf(path)
    if path.suffix == ".csv":
        return _leer_csv(path)
    raise ValueError(f"Formato no soportado: {path.suffix}")


def load_documents(data_dir: str) -> list[dict]:
    """Recorre data_dir, incluyendo subcarpetas, y devuelve la lista completa de LoadedDocument."""
    documentos: list[dict] = []
    ids_vistos: set[tuple[str, int | None]] = set()

    for ruta in sorted(Path(data_dir).rglob("*")):
        if not ruta.is_file():
            continue
        if ruta.parent.name in CARPETAS_EXCLUIDAS:
            continue
        if ruta.suffix not in (".md", ".pdf", ".csv"):
            continue

        for doc in _extract_text(ruta):
            clave = (doc["document_id"], doc.get("page"))
            if clave in ids_vistos:
                raise ValueError(
                    f"Combinacion document_id+page duplicada: {clave}")
            ids_vistos.add(clave)
            documentos.append(doc)

    return documentos


if __name__ == "__main__":
    docs = load_documents("data")
    print(f"Documentos cargados: {len(docs)}")
    for d in docs:
        print(
            f"  - {d['document_id']} ({d['category']}, {len(d['text'])} chars)")
