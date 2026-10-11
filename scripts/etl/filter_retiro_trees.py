"""Filtra y resume el inventario municipal de arbolado de El Retiro."""

from argparse import ArgumentParser
from pathlib import Path

import pandas as pd


FILTERED_FILENAME = (
    "flora_fauna__inventario_arbolado_retiro__madrid__v01_filtrado.csv"
)

SPECIES_FILENAME = (
    "flora_fauna__resumen_especies_retiro__madrid__v01.csv"
)

HEIGHTS_FILENAME = (
    "flora_fauna__distribucion_alturas_retiro__madrid__v01.csv"
)

SUMMARY_FILENAME = (
    "flora_fauna__informe_etl_arbolado_retiro__madrid__v01.md"
)

REQUIRED_COLUMNS = {
    "ASSETNUM",
    "NUM_PARQUE",
    "NBRE_DISTRITO",
    "NBRE_BARRIO",
    "ESPECIE",
    "ALTURA_TOTAL",
}


def parse_args():
    """Obtiene las rutas de entrada y salida desde la terminal."""

    parser = ArgumentParser(
        description=(
            "Filtra el inventario municipal para conservar los árboles "
            "de El Retiro y genera resúmenes estadísticos."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Ruta del CSV municipal original.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Carpeta donde se guardarán los resultados.",
    )

    return parser.parse_args()


def validate_input(input_path: Path) -> None:
    """Comprueba que el archivo de entrada existe y es un CSV."""

    if not input_path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de entrada: {input_path}"
        )

    if not input_path.is_file():
        raise ValueError(
            f"La ruta de entrada no corresponde a un archivo: {input_path}"
        )

    if input_path.suffix.lower() != ".csv":
        raise ValueError(
            f"El archivo de entrada debe tener extensión .csv: {input_path}"
        )


def load_inventory(input_path: Path) -> pd.DataFrame:
    """Carga el inventario municipal conservando los campos como texto."""

    df = pd.read_csv(
        input_path,
        sep=";",
        dtype=str,
        encoding="utf-8-sig",
    )

    missing_columns = REQUIRED_COLUMNS.difference(df.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(
            f"El CSV no contiene las columnas obligatorias: {missing}"
        )

    return df


def filter_retiro(df: pd.DataFrame) -> pd.DataFrame:
    """Conserva los registros cuyo NUM_PARQUE es 1."""

    retiro = df[
        df["NUM_PARQUE"]
        .fillna("")
        .str.strip()
        .eq("1")
    ].copy()

    if retiro.empty:
        raise ValueError(
            "El filtro NUM_PARQUE = 1 no ha devuelto ningún registro."
        )

    return retiro


def normalize_inventory(retiro: pd.DataFrame) -> pd.DataFrame:
    """Normaliza especies y transforma la altura en un valor numérico."""

    retiro["ESPECIE"] = (
        retiro["ESPECIE"]
        .fillna("ESPECIE NO INFORMADA")
        .str.strip()
        .str.upper()
    )

    retiro["ALTURA_TOTAL_NUM"] = pd.to_numeric(
        retiro["ALTURA_TOTAL"]
        .fillna("")
        .str.strip()
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )

    return retiro


def create_species_summary(retiro: pd.DataFrame) -> pd.DataFrame:
    """Calcula frecuencias y alturas por especie."""

    total_trees = len(retiro)

    summary = (
        retiro.groupby("ESPECIE", dropna=False)
        .agg(
            numero_ejemplares=("ASSETNUM", "count"),
            altura_media_m=("ALTURA_TOTAL_NUM", "mean"),
            altura_minima_m=("ALTURA_TOTAL_NUM", "min"),
            altura_maxima_m=("ALTURA_TOTAL_NUM", "max"),
            mediana_altura_m=("ALTURA_TOTAL_NUM", "median"),
        )
        .reset_index()
        .sort_values(
            by=["numero_ejemplares", "ESPECIE"],
            ascending=[False, True],
        )
    )

    summary["porcentaje_total"] = (
        summary["numero_ejemplares"]
        .div(total_trees)
        .mul(100)
        .round(2)
    )

    numeric_columns = [
        "altura_media_m",
        "altura_minima_m",
        "altura_maxima_m",
        "mediana_altura_m",
    ]

    summary[numeric_columns] = summary[numeric_columns].round(2)

    column_order = [
        "ESPECIE",
        "numero_ejemplares",
        "porcentaje_total",
        "altura_media_m",
        "altura_minima_m",
        "altura_maxima_m",
        "mediana_altura_m",
    ]

    return summary[column_order]


def create_height_distribution(retiro: pd.DataFrame) -> pd.DataFrame:
    """Agrupa los árboles por intervalos de altura."""

    intervals = [
        float("-inf"),
        2,
        5,
        10,
        15,
        20,
        30,
        float("inf"),
    ]

    labels = [
        "Hasta 2 m",
        "Más de 2 hasta 5 m",
        "Más de 5 hasta 10 m",
        "Más de 10 hasta 15 m",
        "Más de 15 hasta 20 m",
        "Más de 20 hasta 30 m",
        "Más de 30 m",
    ]

    height_ranges = pd.cut(
        retiro["ALTURA_TOTAL_NUM"],
        bins=intervals,
        labels=labels,
        include_lowest=True,
        right=True,
    )

    height_ranges = (
        height_ranges
        .cat.add_categories(["No disponible"])
        .fillna("No disponible")
    )

    distribution = (
        height_ranges
        .value_counts(sort=False)
        .rename_axis("rango_altura")
        .reset_index(name="numero_ejemplares")
    )

    distribution["porcentaje_total"] = (
        distribution["numero_ejemplares"]
        .div(len(retiro))
        .mul(100)
        .round(2)
    )

    return distribution


def create_markdown_summary(
    retiro: pd.DataFrame,
    species_summary: pd.DataFrame,
    height_distribution: pd.DataFrame,
) -> str:
    """Genera un resumen descriptivo preparado para el corpus RAG."""

    total_trees = len(retiro)
    total_species = retiro["ESPECIE"].nunique()
    valid_heights = int(retiro["ALTURA_TOTAL_NUM"].notna().sum())
    missing_heights = int(retiro["ALTURA_TOTAL_NUM"].isna().sum())
    duplicated_assets = int(retiro["ASSETNUM"].duplicated().sum())

    height_stats = retiro["ALTURA_TOTAL_NUM"].describe()

    top_species = species_summary.head(15)
    top_species_total = int(top_species["numero_ejemplares"].sum())
    top_species_percentage = (
        top_species_total / total_trees * 100
    )

    species_lines = []

    for position, row in enumerate(
        top_species.itertuples(index=False),
        start=1,
    ):
        species_lines.append(
            f"{position}. `{row.ESPECIE}`: "
            f"{row.numero_ejemplares} ejemplares; "
            f"{row.porcentaje_total:.2f} % del total; "
            f"altura media de {row.altura_media_m:.2f} metros."
        )

    height_lines = []

    for row in height_distribution.itertuples(index=False):
        height_lines.append(
            f"- {row.rango_altura}: "
            f"{row.numero_ejemplares} ejemplares "
            f"({row.porcentaje_total:.2f} %)."
        )

    species_text = "\n".join(species_lines)
    heights_text = "\n".join(height_lines)

    return f"""---
document_id: flora_fauna__resumen_inventario_arbolado_retiro__madrid__v01
title: Resumen descriptivo del inventario del arbolado de El Retiro
category: flora_fauna
topic: Inventario del arbolado
source_organization: Ayuntamiento de Madrid
language: es
version: 1
derived_from: flora_fauna__inventario_arbolado__madrid__v01
transformation: filtrado por NUM_PARQUE igual a 1 y agregación estadística
review_status: pendiente_revision
---

# Resumen descriptivo del inventario del arbolado de El Retiro

## Alcance

Este documento deriva del inventario municipal del arbolado de Madrid.
Se han conservado exclusivamente los registros cuyo campo `NUM_PARQUE`
tiene el valor `1`, correspondiente al parque de El Retiro.

Los resultados describen la versión del dataset utilizada. No constituyen
un recuento en tiempo real.

## Magnitudes generales

- Árboles registrados: {total_trees}.
- Especies diferentes: {total_species}.
- Registros con altura válida: {valid_heights}.
- Registros sin altura disponible: {missing_heights}.
- Identificadores `ASSETNUM` duplicados: {duplicated_assets}.

## Estadísticas de altura

- Altura media: {height_stats["mean"]:.2f} metros.
- Desviación estándar: {height_stats["std"]:.2f} metros.
- Altura mínima: {height_stats["min"]:.2f} metros.
- Primer cuartil: {height_stats["25%"]:.2f} metros.
- Mediana: {height_stats["50%"]:.2f} metros.
- Tercer cuartil: {height_stats["75%"]:.2f} metros.
- Altura máxima: {height_stats["max"]:.2f} metros.

La altura por sí sola no permite determinar la edad, salud,
el estado estructural o el riesgo de un árbol.

## Quince especies más frecuentes

{species_text}

Las quince especies más frecuentes reúnen {top_species_total} ejemplares,
aproximadamente el {top_species_percentage:.2f} % del inventario.

## Distribución por rangos de altura

{heights_text}

## Calidad de los datos

La agrupación por especie utiliza el texto del campo `ESPECIE` después
de eliminar espacios exteriores y convertirlo a mayúsculas.

No se ha realizado una reconciliación taxonómica de sinónimos,
variedades o posibles errores ortográficos.

El campo `PERIMETRO` se conserva en el CSV filtrado, pero no se utiliza
en este resumen porque la documentación consultada no especifica su
unidad de medida.

## Limitaciones

El inventario representa una fotografía administrativa del arbolado.
Las altas, bajas, sustituciones y correcciones posteriores pueden
modificar sus cifras.

El filtro utiliza `NUM_PARQUE = 1`. No incorpora registros del barrio
de Los Jerónimos que carezcan de número de parque o tengan un valor
diferente, porque no puede asegurarse que pertenezcan a El Retiro.

Las estadísticas no deben utilizarse para diagnósticos individuales,
evaluaciones de riesgo ni predicciones sobre ejemplares concretos.

## Transformación aplicada

1. Lectura del CSV municipal utilizando punto y coma como separador.
2. Filtrado de los registros con `NUM_PARQUE = 1`.
3. Normalización básica del campo `ESPECIE`.
4. Conversión de `ALTURA_TOTAL` a número decimal.
5. Comprobación de valores ausentes y duplicados.
6. Agrupación por especie.
7. Cálculo de estadísticas descriptivas y rangos de altura.
"""


def save_outputs(
    retiro: pd.DataFrame,
    species_summary: pd.DataFrame,
    height_distribution: pd.DataFrame,
    markdown_summary: str,
    output_dir: Path,
) -> list[Path]:
    """Guarda los resultados del proceso ETL."""

    output_dir.mkdir(parents=True, exist_ok=True)

    filtered_path = output_dir / FILTERED_FILENAME
    species_path = output_dir / SPECIES_FILENAME
    heights_path = output_dir / HEIGHTS_FILENAME
    summary_path = output_dir / SUMMARY_FILENAME

    retiro.to_csv(
        filtered_path,
        sep=";",
        index=False,
        encoding="utf-8-sig",
    )

    species_summary.to_csv(
        species_path,
        sep=";",
        index=False,
        encoding="utf-8-sig",
    )

    height_distribution.to_csv(
        heights_path,
        sep=";",
        index=False,
        encoding="utf-8-sig",
    )

    summary_path.write_text(
        markdown_summary,
        encoding="utf-8",
    )

    return [
        filtered_path,
        species_path,
        heights_path,
        summary_path,
    ]


def print_results(
    retiro: pd.DataFrame,
    species_summary: pd.DataFrame,
    output_paths: list[Path],
) -> None:
    """Muestra en la terminal un resumen del proceso."""

    total_trees = len(retiro)
    total_species = retiro["ESPECIE"].nunique()
    valid_heights = int(retiro["ALTURA_TOTAL_NUM"].notna().sum())
    missing_heights = int(retiro["ALTURA_TOTAL_NUM"].isna().sum())
    duplicated_assets = int(retiro["ASSETNUM"].duplicated().sum())

    print(f"Árboles de El Retiro: {total_trees}")
    print(f"Especies diferentes: {total_species}")
    print(f"Alturas válidas: {valid_heights}")
    print(f"Alturas no disponibles: {missing_heights}")
    print(f"ASSETNUM duplicados: {duplicated_assets}")

    print("\nEstadísticas de altura:")
    print(
        retiro["ALTURA_TOTAL_NUM"]
        .describe()
        .round(2)
    )

    print("\n15 especies más frecuentes:")
    print(
        species_summary[
            [
                "ESPECIE",
                "numero_ejemplares",
                "porcentaje_total",
                "altura_media_m",
            ]
        ]
        .head(15)
        .to_string(index=False)
    )

    print("\nArchivos generados:")

    for path in output_paths:
        print(f"- {path}")


def main() -> None:
    """Ejecuta el proceso ETL completo."""

    args = parse_args()

    validate_input(args.input)

    inventory = load_inventory(args.input)
    retiro = filter_retiro(inventory)
    retiro = normalize_inventory(retiro)

    species_summary = create_species_summary(retiro)
    height_distribution = create_height_distribution(retiro)

    markdown_summary = create_markdown_summary(
        retiro,
        species_summary,
        height_distribution,
    )

    output_paths = save_outputs(
        retiro,
        species_summary,
        height_distribution,
        markdown_summary,
        args.output_dir,
    )

    print_results(
        retiro,
        species_summary,
        output_paths,
    )


if __name__ == "__main__":
    main()
