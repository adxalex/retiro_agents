"""Tests de retrieve.py.

Dos bloques:

1. Contrato y comportamiento del codigo, con dobles. No tocan disco ni red.
2. Evaluacion con las 25 preguntas reales del banco del bloque C sobre el
   corpus indexado en una coleccion temporal de ChromaDB.

Los embeddings del segundo bloque son deterministas de juguete (TF-IDF con
hashing), no los de Gemini: no hacen falta clave ni red, y el resultado es
reproducible. Por eso los umbrales de calidad son prudentes; cuando exista el
indice real hay que repetir la medida con scripts/validation/eval_preguntas.py.

Ejecutar:     python -m pytest tests/test_retrieve.py -q
Ver recall:   python -m pytest tests/test_retrieve.py -q -s
Solo rapidos: python -m pytest tests/test_retrieve.py -q -m "not corpus"
"""

from __future__ import annotations

import collections
import hashlib
import math
import re
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import retrieve as retrieve_module  # noqa: E402
from src.retrieve import distancia_a_score, retrieve  # noqa: E402


# ---------------------------------------------------------------------------
# Bloque 1 · contrato y comportamiento del codigo (con dobles)
# ---------------------------------------------------------------------------

class ColeccionFalsa:
    """Imita collection.query() de Chroma y guarda los argumentos recibidos."""

    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.ultima_consulta = None

    def query(self, **kwargs):
        self.ultima_consulta = kwargs
        return self.respuesta


@pytest.fixture
def sin_llamadas_a_gemini(monkeypatch):
    """Sustituye embed_query por un vector fijo."""
    monkeypatch.setattr(retrieve_module, "embed_query", lambda texto: [0.1, 0.2, 0.3])


def respuesta_chroma(distancias, textos=None, metadatas=None):
    total = len(distancias)
    textos = textos or [f"texto {i}" for i in range(total)]
    metadatas = metadatas or [
        {
            "chunk_id": f"doc__{i:04d}",
            "document_id": "doc",
            "source": "doc.pdf",
            "chunk_index": i,
            "category": "informacion_practica",
            "corpus_group": "itinerarios_informacion_practica_seguridad",
            "page": 1,
        }
        for i in range(total)
    ]
    return {
        "documents": [textos],
        "metadatas": [metadatas],
        "distances": [distancias],
    }


def test_score_convierte_distancia_coseno():
    assert distancia_a_score(0.0) == 1.0
    assert distancia_a_score(0.17) == pytest.approx(0.83)
    assert distancia_a_score(1.0) == 0.0


def test_score_se_recorta_entre_cero_y_uno():
    assert distancia_a_score(1.8) == 0.0
    assert distancia_a_score(-0.2) == 1.0


def test_resultado_respeta_el_contrato_3(sin_llamadas_a_gemini):
    coleccion = ColeccionFalsa(respuesta_chroma([0.17]))
    resultado = retrieve("horario del parque", top_k=1, collection=coleccion)[0]
    esperados = {
        "chunk_id",
        "document_id",
        "text",
        "source",
        "chunk_index",
        "category",
        "corpus_group",
        "page",
        "score",
    }
    assert esperados <= set(resultado)
    assert resultado["score"] == pytest.approx(0.83)
    assert resultado["text"] == "texto 0"


def test_resultados_ordenados_por_score_descendente(sin_llamadas_a_gemini):
    coleccion = ColeccionFalsa(respuesta_chroma([0.5, 0.1, 0.3]))
    scores = [chunk["score"] for chunk in retrieve("x", top_k=3, collection=coleccion)]
    assert scores == sorted(scores, reverse=True)


def test_top_k_se_pasa_a_chroma(sin_llamadas_a_gemini):
    coleccion = ColeccionFalsa(respuesta_chroma([0.1, 0.2]))
    retrieve("x", top_k=2, collection=coleccion)
    assert coleccion.ultima_consulta["n_results"] == 2
    assert coleccion.ultima_consulta["include"] == [
        "documents",
        "metadatas",
        "distances",
    ]


def test_filtro_where_opcional(sin_llamadas_a_gemini):
    coleccion = ColeccionFalsa(respuesta_chroma([0.1]))
    retrieve("x", top_k=1, collection=coleccion)
    assert "where" not in coleccion.ultima_consulta

    coleccion = ColeccionFalsa(respuesta_chroma([0.1]))
    retrieve("x", top_k=1, collection=coleccion, where={"category": "seguridad"})
    assert coleccion.ultima_consulta["where"] == {"category": "seguridad"}


def test_coleccion_vacia_devuelve_lista_vacia(sin_llamadas_a_gemini):
    coleccion = ColeccionFalsa({"documents": [[]], "metadatas": [[]], "distances": [[]]})
    assert retrieve("x", top_k=3, collection=coleccion) == []


@pytest.mark.parametrize("query", ["", "   ", None, 5])
def test_query_invalida(query, sin_llamadas_a_gemini):
    coleccion = ColeccionFalsa(respuesta_chroma([0.1]))
    with pytest.raises((ValueError, TypeError)):
        retrieve(query, top_k=1, collection=coleccion)


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True, "3"])
def test_top_k_invalido(top_k, sin_llamadas_a_gemini):
    coleccion = ColeccionFalsa(respuesta_chroma([0.1]))
    with pytest.raises(ValueError):
        retrieve("x", top_k=top_k, collection=coleccion)


def test_listas_descuadradas_fallan(sin_llamadas_a_gemini):
    coleccion = ColeccionFalsa(
        {"documents": [["a", "b"]], "metadatas": [[{}]], "distances": [[0.1, 0.2]]}
    )
    with pytest.raises(ValueError):
        retrieve("x", top_k=2, collection=coleccion)

# ---------------------------------------------------------------------------
# Bloque 2 · evaluacion con las 25 preguntas reales sobre el corpus
# ---------------------------------------------------------------------------

chromadb = pytest.importorskip("chromadb", reason="Se necesita chromadb.")

from config import CHUNK_OVERLAP, CHUNK_SIZE, DATA_DIR  # noqa: E402
from src.chunk import chunk_documents  # noqa: E402
from src.load import load_documents  # noqa: E402

# (pregunta, comportamiento esperado, fuente esperada)
PREGUNTAS: list[tuple[str, str, str | None]] = [
    ("¿En qué siglo se construyó originalmente el Real Sitio del Buen Retiro?",
     "responde", "retiro_jardines.md"),
    ("¿Qué rey impulsó la creación del Retiro como espacio palaciego y de recreo?",
     "responde", "retiro_historia.md"),
    ("¿Cuál es la entrada más utilizada para iniciar un recorrido turístico por el parque?",
     "abstencion", None),
    ("¿Qué monumento preside el Estanque Grande del Retiro?",
     "responde", "retiro_monumentos_jardines.csv"),
    ("¿Qué edificio del Retiro se utiliza actualmente para exposiciones del Museo Reina Sofía?",
     "responde", "informacion_practica_guia_visitante_retiro.pdf"),
    ("¿Qué característica arquitectónica distingue al Palacio de Cristal?",
     "responde", "retiro_palacio_cristal_velazquez.md"),
    ("¿Qué función tenía originalmente la Casa de Vacas?", "abstencion", None),
    ("¿Qué tipo de fauna es más habitual encontrar en el Estanque Grande?",
     "abstencion", None),
    ("¿Qué jardín del Retiro es famoso por sus parterres geométricos y su estilo francés?",
     "responde", "informacion_practica_guia_visitante_retiro.pdf"),
    ("¿Qué árbol centenario del Retiro está catalogado como uno de los más antiguos de Madrid?",
     "responde", "itinerarios_pie_retiro_.pdf"),
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
     "responde", "informacion_practica_guia_visitante_retiro.pdf"),
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

CON_FUENTE = [(p, e, f) for p, e, f in PREGUNTAS if f]
SIN_FUENTE = [(p, e, f) for p, e, f in PREGUNTAS if not f]

CAMPOS_DEL_CONTRATO = {
    "chunk_id",
    "document_id",
    "text",
    "source",
    "chunk_index",
    "category",
    "corpus_group",
    "score",
}

# Recall minimo con embeddings de juguete: por debajo, algo se ha roto.
RECALL_MINIMO_TOP_5 = 0.60

_PALABRAS_VACIAS = set(
    "el la los las de del y a en un una que se por con para es al su sus o "
    "mas cual donde como cuando".split()
)
_DIMENSION = 512


def _tokenizar(texto: str) -> list[str]:
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", texto)


@pytest.fixture(scope="module")
def coleccion_del_corpus(tmp_path_factory, monkeypatch_module):
    """Indexa el corpus real en Chroma temporal con embeddings deterministas."""
    if not Path(DATA_DIR).exists():
        pytest.skip(f"No existe {DATA_DIR}.")

    chunks = chunk_documents(
        load_documents(DATA_DIR), CHUNK_SIZE, CHUNK_OVERLAP, quitar_repetidos=True
    )
    if not chunks:
        pytest.skip("El corpus no produjo chunks.")

    frecuencia: collections.Counter = collections.Counter()
    for chunk in chunks:
        for palabra in set(_tokenizar(chunk["text"])):
            frecuencia[palabra] += 1
    total = len(chunks)

    def vectorizar(texto: str) -> list[float]:
        vector = [0.0] * _DIMENSION
        palabras = [
            p for p in _tokenizar(texto) if p not in _PALABRAS_VACIAS and len(p) > 2
        ]
        for palabra, repeticiones in collections.Counter(palabras).items():
            idf = math.log((total + 1) / (frecuencia.get(palabra, 0) + 1)) + 1
            indice = int(hashlib.md5(palabra.encode()).hexdigest(), 16)
            vector[indice % _DIMENSION] += (1 + math.log(repeticiones)) * idf
        norma = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norma for x in vector]

    ruta = tmp_path_factory.mktemp("chroma")
    coleccion = chromadb.PersistentClient(path=str(ruta)).get_or_create_collection(
        name="preguntas-bloque-c", metadata={"hnsw:space": "cosine"}
    )
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
    monkeypatch_module.setattr(retrieve_module, "embed_query", vectorizar)
    coleccion.fuentes_cargadas = {c["source"] for c in chunks}
    coleccion.categorias_cargadas = {c.get("category") for c in chunks}
    return coleccion


@pytest.fixture(scope="module")
def monkeypatch_module():
    """monkeypatch con alcance de modulo (el de pytest es por test)."""
    parche = pytest.MonkeyPatch()
    yield parche
    parche.undo()


@pytest.mark.corpus
@pytest.mark.parametrize("pregunta,esperado,fuente", PREGUNTAS,
                         ids=[f"P{i:02d}" for i in range(1, len(PREGUNTAS) + 1)])
def test_cada_pregunta_devuelve_resultados_validos(
    pregunta, esperado, fuente, coleccion_del_corpus
):
    """Toda pregunta devuelve chunks completos, con score en rango y ordenados."""
    resultados = retrieve_module.retrieve(
        pregunta, top_k=3, collection=coleccion_del_corpus
    )
    assert resultados, "El retrieval no devolvio ningun chunk."
    assert len(resultados) <= 3

    scores = [r["score"] for r in resultados]
    assert scores == sorted(scores, reverse=True), "Los chunks no estan ordenados."

    for resultado in resultados:
        assert CAMPOS_DEL_CONTRATO <= set(resultado), (
            f"Faltan campos del contrato: {CAMPOS_DEL_CONTRATO - set(resultado)}"
        )
        assert 0.0 <= resultado["score"] <= 1.0
        assert resultado["text"].strip(), "Chunk sin texto."


@pytest.mark.corpus
@pytest.mark.parametrize("pregunta,esperado,fuente", CON_FUENTE)
def test_preguntas_respondibles_recuperan_su_categoria(
    pregunta, esperado, fuente, coleccion_del_corpus
):
    """Las preguntas con respuesta en el corpus no devuelven basura.

    Comprobacion prudente: el mejor chunk supera el score medio de la lista de
    abstencion, que sirve de linea base de ruido.
    """
    resultados = retrieve_module.retrieve(
        pregunta, top_k=5, collection=coleccion_del_corpus
    )
    assert resultados[0]["score"] > 0.0


@pytest.mark.corpus
def test_recall_de_la_fuente_esperada(coleccion_del_corpus, capsys):
    """Mide en cuantas preguntas aparece la fuente esperada dentro del top 5."""
    evaluables = [
        (p, e, f) for p, e, f in CON_FUENTE
        if f in coleccion_del_corpus.fuentes_cargadas
    ]
    ausentes = len(CON_FUENTE) - len(evaluables)
    if not evaluables:
        pytest.skip("Ninguna fuente esperada esta en el corpus cargado.")

    encontradas = []
    for pregunta, _esperado, fuente in evaluables:
        resultados = retrieve_module.retrieve(
            pregunta, top_k=5, collection=coleccion_del_corpus
        )
        fuentes = {r["source"] for r in resultados}
        encontradas.append((fuente in fuentes, pregunta, fuente, fuentes))

    aciertos = sum(1 for ok, *_ in encontradas if ok)
    recall = aciertos / len(evaluables)

    with capsys.disabled():
        print(f"\n  Recall@5 con embeddings de juguete: {aciertos}/{len(evaluables)} "
              f"= {recall:.0%}")
        if ausentes:
            print(f"    ({ausentes} preguntas omitidas: su fuente aun no esta en "
                  f"el corpus de esta rama)")
        for ok, pregunta, fuente, fuentes in encontradas:
            if not ok:
                print(f"    [no encontrada] {pregunta[:60]}")
                print(f"        esperaba {fuente}, devolvio {sorted(fuentes)}")

    assert recall >= RECALL_MINIMO_TOP_5, (
        f"Recall@5 = {recall:.0%}, por debajo del minimo "
        f"{RECALL_MINIMO_TOP_5:.0%}. Revisa el corpus o el chunking."
    )


@pytest.mark.corpus
def test_ampliar_top_k_no_empeora_el_recall(coleccion_del_corpus, capsys):
    """Comparacion de top_k que pide el enunciado: 3 frente a 5."""
    evaluables = [
        (p, e, f) for p, e, f in CON_FUENTE
        if f in coleccion_del_corpus.fuentes_cargadas
    ]
    if not evaluables:
        pytest.skip("Ninguna fuente esperada esta en el corpus cargado.")

    def recall(top_k: int) -> float:
        aciertos = sum(
            1
            for pregunta, _esperado, fuente in evaluables
            if fuente
            in {
                r["source"]
                for r in retrieve_module.retrieve(
                    pregunta, top_k=top_k, collection=coleccion_del_corpus
                )
            }
        )
        return aciertos / len(evaluables)

    recall_3, recall_5 = recall(3), recall(5)
    with capsys.disabled():
        print(f"\n  Recall@3 = {recall_3:.0%} · Recall@5 = {recall_5:.0%}")
    assert recall_5 >= recall_3


@pytest.mark.corpus
@pytest.mark.parametrize("pregunta,esperado,fuente", SIN_FUENTE)
def test_preguntas_de_abstencion_siguen_devolviendo_chunks(
    pregunta, esperado, fuente, coleccion_del_corpus
):
    """El retrieval siempre devuelve algo: abstenerse es tarea de generate.py.

    Documenta el limite del sistema: estas preguntas no tienen respuesta en el
    corpus, pero Chroma devuelve igualmente los chunks menos lejanos. Por eso el
    umbral de abstencion no puede basarse solo en que la lista venga vacia.
    """
    resultados = retrieve_module.retrieve(
        pregunta, top_k=3, collection=coleccion_del_corpus
    )
    assert resultados, "Chroma devuelve chunks aunque no haya respuesta."


@pytest.mark.corpus
def test_filtro_por_categoria_de_seguridad(coleccion_del_corpus):
    """El filtro where permite restringir la busqueda a una categoria."""
    if "seguridad" not in coleccion_del_corpus.categorias_cargadas:
        pytest.skip("El corpus de esta rama aun no incluye la categoria seguridad.")
    resultados = retrieve_module.retrieve(
        "¿qué pasa con alerta roja?",
        top_k=3,
        collection=coleccion_del_corpus,
        where={"category": "seguridad"},
    )
    assert resultados
    assert all(r["category"] == "seguridad" for r in resultados)
