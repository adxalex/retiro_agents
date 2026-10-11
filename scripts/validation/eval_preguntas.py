"""Ejecuta el banco de preguntas del bloque C contra retrieve.py.

Uso (desde la raiz del repo):
    python scripts/validation/eval_preguntas.py                 # indice real, top_k=3
    python scripts/validation/eval_preguntas.py --top-k 5
    python scripts/validation/eval_preguntas.py --simulado      # sin clave ni indice

El modo --simulado construye un indice temporal de ChromaDB con embeddings
deterministas de juguete (TF-IDF con hashing). Sirve para comprobar el flujo y
comparar preguntas entre si, no para medir la calidad real del retrieval.

Cada pregunta declara el comportamiento esperado (responde / parcial / abstencion)
y, cuando procede, la fuente que deberia aparecer en el top_k. El script informa
de si esa fuente aparece, pero no decide por si mismo si el sistema debe
abstenerse: esa logica vive en generate.py.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import math
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from config import CHUNK_OVERLAP, CHUNK_SIZE, DATA_DIR, TOP_K  # noqa: E402
from src import retrieve as retrieve_module  # noqa: E402

# (pregunta, comportamiento esperado, fuente o fuentes aceptables)
#
# Varias fuentes pueden responder legitimamente la misma pregunta desde que el
# corpus crecio. Se acepta una lista: basta con que aparezca una de ellas.
PREGUNTAS: list[tuple[str, str, str | list[str] | None]] = [
    ("¿En qué siglo se construyó originalmente el Real Sitio del Buen Retiro?",
     "responde", "retiro_jardines.md"),
    ("¿Qué rey impulsó la creación del Retiro como espacio palaciego y de recreo?",
     "responde", "retiro_historia.md"),
    ("¿Cuál es la entrada más utilizada para iniciar un recorrido turístico por el parque?",
     "abstencion", None),
    ("¿Qué monumento preside el Estanque Grande del Retiro?",
     "responde", "retiro_monumentos_jardines.csv"),
    ("¿Qué edificio del Retiro se utiliza actualmente para exposiciones del Museo Reina Sofía?",
     "responde", ["informacion_practica_guia_visitante_retiro.pdf",
                  "arte_cultura__palacio_cristal_velazquez__museo_reina_sofia__v01.md",
                  "retiro_palacio_cristal_velazquez.md"]),
    ("¿Qué característica arquitectónica distingue al Palacio de Cristal?",
     "responde", ["retiro_monumentos_jardines.csv",
                  "retiro_palacio_cristal_velazquez.md",
                  "arte_cultura__palacio_cristal_velazquez__museo_reina_sofia__v01.md"]),
    ("¿Qué función tenía originalmente la Casa de Vacas?", "abstencion", None),
    # Cubierta desde que se integro la fuente contrastada de fauna (VEG-24).
    ("¿Qué tipo de fauna es más habitual encontrar en el Estanque Grande?",
     "responde", "flora_fauna__fauna_estanque_grande_retiro__fuentes_contrastadas__v01.md"),
    ("¿Qué jardín del Retiro es famoso por sus parterres geométricos y su estilo francés?",
     "responde", "informacion_practica_guia_visitante_retiro.pdf"),
    ("¿Qué árbol centenario del Retiro está catalogado como uno de los más antiguos de Madrid?",
     "responde", "informacion_practica_guia_visitante_retiro.pdf"),
    ("¿Qué evento deportivo multitudinario suele atravesar el Retiro cada año?",
     "abstencion", None),
    ("¿Qué norma de seguridad se recomienda especialmente en zonas cercanas al Estanque?",
     "abstencion", None),
    ("¿Qué edificio del Retiro fue utilizado como cuartel durante la Guerra de la Independencia?",
     "parcial", "retiro_historia.md"),
    ("¿Qué espacio del parque es conocido por sus actividades de lectura y cuentacuentos?",
     "abstencion", None),
    ("¿Qué ruta del Retiro incluye el Palacio de Cristal, el Estanque y el Parterre?",
     "responde", "itinerarios_pie_retiro_.pdf"),
    ("¿Qué institución oficial respalda la información turística del Retiro?",
     "responde", ["informacion_practica_guia_visitante_retiro.pdf",
                  "actividades__guia_retiro__fuentes_mixtas__v01.md"]),
    ("¿Qué horario aproximado tiene el parque durante los meses de verano?",
     "responde", "informacion_practica_guia_visitante_retiro.pdf"),
    ("¿Qué zona del Retiro es considerada de especial interés para fotógrafos por su luz natural?",
     "abstencion", None),
    ("¿Qué elemento del Retiro está dedicado a Alfonso XII?",
     "responde", "retiro_monumentos_jardines.csv"),
    ("¿Qué edificio del Retiro se caracteriza por su estilo neomudéjar?",
     "abstencion", None),
    ("¿Qué punto del parque se considera ideal para iniciar una ruta de «Lo esencial»?",
     "responde", "itinerarios_pie_retiro_.pdf"),
    ("¿Qué protocolo se recomienda seguir si un visitante se pierde dentro del parque?",
     "abstencion", None),
    ("Me encuentro mal del estómago y necesito ir al baño, estoy justo en la estatua "
     "del Ángel Caído, ¿dónde tengo el baño más cerca?",
     "parcial", "informacion_practica_guia_visitante_retiro.pdf"),
    ("¿Qué harías si durante el recorrido alguien asegura haber visto una estatua "
     "que se movió cuando nadie miraba?", "abstencion", None),
    ("Hay alerta naranja y estoy en el lago, ¿qué hago?",
     "responde", "seguridad_protocolo_alertas_retiro.pdf"),
]

_PALABRAS_VACIAS = set(
    "el la los las de del y a en un una que se por con para es al su sus o "
    "mas cual donde como cuando".split()
)
_DIMENSION_SIMULADA = 512


def _tokenizar(texto: str) -> list[str]:
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", texto)


def _coleccion_simulada():
    """Indexa el corpus en Chroma temporal con embeddings de juguete."""
    import chromadb

    from src.chunk import chunk_documents
    from src.load import load_documents

    chunks = chunk_documents(
        load_documents(DATA_DIR), CHUNK_SIZE, CHUNK_OVERLAP, quitar_repetidos=True
    )
    frecuencia_documental: collections.Counter = collections.Counter()
    for chunk in chunks:
        for palabra in set(_tokenizar(chunk["text"])):
            frecuencia_documental[palabra] += 1
    total = len(chunks)

    def vectorizar(texto: str) -> list[float]:
        vector = [0.0] * _DIMENSION_SIMULADA
        palabras = [
            p for p in _tokenizar(texto) if p not in _PALABRAS_VACIAS and len(p) > 2
        ]
        for palabra, repeticiones in collections.Counter(palabras).items():
            idf = math.log((total + 1) / (frecuencia_documental.get(palabra, 0) + 1)) + 1
            indice = int(hashlib.md5(palabra.encode()).hexdigest(), 16)
            vector[indice % _DIMENSION_SIMULADA] += (1 + math.log(repeticiones)) * idf
        norma = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norma for x in vector]

    coleccion = chromadb.PersistentClient(
        path=tempfile.mkdtemp()
    ).get_or_create_collection(name="evaluacion", metadata={"hnsw:space": "cosine"})
    for inicio in range(0, len(chunks), 200):
        lote = chunks[inicio: inicio + 200]
        coleccion.upsert(
            ids=[c["chunk_id"] for c in lote],
            embeddings=[vectorizar(c["text"]) for c in lote],
            documents=[c["text"] for c in lote],
            metadatas=[
                {k: v for k, v in c.items() if k != "text" and v is not None}
                for c in lote
            ],
        )
    retrieve_module.embed_query = vectorizar
    print(f"[SIMULADO] {len(chunks)} chunks indexados con embeddings de juguete.\n")
    return coleccion


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalua el banco de preguntas.")
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument(
        "--simulado",
        action="store_true",
        help="Usa un indice temporal con embeddings de juguete.",
    )
    parser.add_argument("--detalle", action="store_true", help="Muestra los chunks.")
    args = parser.parse_args()

    coleccion = _coleccion_simulada() if args.simulado else None
    aciertos = fallos = 0

    for numero, (pregunta, esperado, fuente_esperada) in enumerate(PREGUNTAS, start=1):
        try:
            resultados = retrieve_module.retrieve(
                pregunta, top_k=args.top_k, collection=coleccion
            )
        except Exception as error:  # noqa: BLE001
            print(f"P{numero:02d} [ERROR] {type(error).__name__}: {error}")
            fallos += 1
            continue

        fuentes = [r.get("source", "?") for r in resultados]
        mejor = resultados[0]["score"] if resultados else 0.0
        aceptables = (
            [] if fuente_esperada is None
            else [fuente_esperada] if isinstance(fuente_esperada, str)
            else list(fuente_esperada)
        )
        if not aceptables:
            marca = "   "
        elif any(f in fuentes for f in aceptables):
            marca = "OK "
            aciertos += 1
        else:
            marca = "KO "
            fallos += 1

        print(f"{marca}P{numero:02d} [{esperado:10}] score_top1={mejor:.3f}  {pregunta[:68]}")
        print(f"        fuentes: {', '.join(dict.fromkeys(fuentes))}")
        if aceptables and not any(f in fuentes for f in aceptables):
            print(f"        esperaba una de: {', '.join(aceptables)}")
        if args.detalle:
            for resultado in resultados:
                print(f"        {resultado['score']:.3f} {resultado['text'][:100]}")

    con_fuente = aciertos + fallos
    print(
        f"\ntop_k={args.top_k} · fuente esperada encontrada en {aciertos}/{con_fuente} "
        f"preguntas con fuente declarada · {len(PREGUNTAS) - con_fuente} de abstencion"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
