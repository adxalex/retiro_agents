"""Nombres legibles de las fuentes del corpus.

El usuario no deberia leer nombres de fichero como
`informacion_practica_guia_visitante_retiro.pdf`. Este modulo traduce cada
documento a un titulo comprensible, su organismo y si la fuente es oficial.

Que la procedencia se vea SIEMPRE, en todas las respuestas, es mejor que
mencionarla a veces dentro del texto: un aviso que aparece de forma irregular
da a entender que las demas respuestas son incuestionables.

Para anadir un documento nuevo, basta con una entrada mas en CATALOGO. Si falta,
se muestra el nombre del fichero sin extension, de forma legible.
"""

from __future__ import annotations

from pathlib import Path

# source -> (titulo legible, organismo o autor, es_oficial)
CATALOGO: dict[str, tuple[str, str, bool]] = {
    "actividades__guia_retiro__fuentes_mixtas__v01.md": (
        "Guía de actividades del Retiro", "Fuentes mixtas", False),
    "arte_cultura__palacio_cristal_velazquez__museo_reina_sofia__v01.md": (
        "Palacios de Cristal y Velázquez", "Museo Reina Sofía", True),
    "arte_cultura__retiro_paisaje_de_la_luz__fuentes_academicas_unesco__v01.md": (
        "El Retiro como Paisaje de la Luz", "UNESCO y fuentes académicas", True),
    "flora_fauna__fauna_estanque_grande_retiro__fuentes_contrastadas__v01.md": (
        "Fauna del Estanque Grande", "Fuentes contrastadas", False),
    "flora_fauna__guia_aves_comunes__madrid__v01.pdf": (
        "Guía de aves comunes de Madrid", "Ayuntamiento de Madrid", True),
    "flora_fauna__plan_director_arbolado__madrid__v01.pdf": (
        "Plan director del arbolado", "Ayuntamiento de Madrid", True),
    "flora_fauna__resumen_inventario_arbolado_retiro__madrid__v01.md": (
        "Inventario del arbolado del Retiro", "Ayuntamiento de Madrid", True),
    "flora_fauna__senda_botanica__madrid__v01.pdf": (
        "Senda botánica del Retiro", "Ayuntamiento de Madrid", True),
    "informacion_practica_bicicleta_retiro.pdf": (
        "Bicicleta en el Retiro", "Ayuntamiento de Madrid y Zona Retiro", False),
    "informacion_practica_guia_visitante_retiro.pdf": (
        "Guía del visitante del Retiro", "esMadrid, Turismo de Madrid", True),
    "itinerarios_pie_retiro_.pdf": (
        "Rutas a pie por el Retiro", "esMadrid y elaboración propia", False),
    "itinerarios_running_retiro_.pdf": (
        "Circuitos para correr en el Retiro", "VG Running", False),
    "retiro_historia.md": (
        "Historia del Real Sitio del Buen Retiro", "Ayuntamiento de Madrid", True),
    "retiro_jardines.md": (
        "Jardines del Retiro", "Ayuntamiento de Madrid", True),
    "retiro_monumentos_jardines.csv": (
        "Monumentos y jardines del Retiro", "Ayuntamiento de Madrid", True),
    "retiro_palacio_cristal_velazquez.md": (
        "Palacio de Cristal y Palacio de Velázquez", "Ayuntamiento de Madrid", True),
    "seguridad_protocolo_alertas_retiro.pdf": (
        "Protocolo de alertas meteorológicas", "Ayuntamiento de Madrid", True),
}

ETIQUETA_OFICIAL = "fuente oficial"
ETIQUETA_NO_OFICIAL = "fuente no oficial"


def _titulo_por_defecto(source: str) -> str:
    """Nombre presentable cuando el documento no esta en el catalogo."""
    nombre = Path(source).stem.replace("__", " · ").replace("_", " ").strip(" ·")
    return nombre[:1].upper() + nombre[1:] if nombre else source


def describir(source: str) -> dict:
    """Devuelve titulo, organismo, si es oficial y un texto ya montado.

    'texto' NO incluye la etiqueta de fiabilidad: se deja aparte en 'etiqueta'
    y 'oficial' para que la interfaz la muestre como marca visual, sin
    ensuciar la linea de la fuente.
    """
    titulo, organismo, oficial = CATALOGO.get(
        source, (_titulo_por_defecto(source), "", False)
    )
    partes = [titulo]
    if organismo:
        partes.append(organismo)
    return {
        "source": source,
        "titulo": titulo,
        "organismo": organismo,
        "oficial": oficial,
        "etiqueta": ETIQUETA_OFICIAL if oficial else ETIQUETA_NO_OFICIAL,
        "texto": " · ".join(partes),
    }


def describir_citas(citas: list[dict]) -> list[dict]:
    """Enriquece las citas de responder() con el nombre legible de la fuente."""
    resultado = []
    for cita in citas:
        entrada = dict(cita)
        entrada.update(describir(cita.get("source", "")))
        if cita.get("page"):
            entrada["texto"] = f"{entrada['texto']}, página {cita['page']}"
        resultado.append(entrada)
    return resultado
