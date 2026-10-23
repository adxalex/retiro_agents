"""Configuracion centralizada del sistema RAG - Parque de El Retiro."""
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# --- Rutas ---
DATA_DIR = "data"
CHROMA_DIR = "chroma"
COLLECTION_NAME = "retiro_madrid"
PROYECT_DIR=Path(__file__).resolve().parent
FALLBACK_JSON=PROYECT_DIR/'src'/'tools'/'fallback'/'aemet.json'
IMAGE_DEFAULT_NAME='Historia_Retiro.png'
IMAGE_DEFAULT_PATH=PROYECT_DIR/'src'/'tools'/'fallback'/IMAGE_DEFAULT_NAME

# Modelos estables seleccionados para el MVP.
# gemini-embedding-001 devuelve un vector por texto y mantiene compatibilidad
# con el procesamiento por lotes actual de embed.py.
LLM_MODEL = "gemini-3.6-flash"
EMBEDDING_MODEL = "gemini-embedding-001"

# --- Chunking ---
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# --- Embeddings ---
EMBED_BATCH_SIZE = 32  # chunks por lote enviado a la API de Gemini embeddings

# Control de cuota para indexaciones grandes con el nivel gratuito de Gemini.
# Solo se aplica cuando Gemini responde con 429 RESOURCE_EXHAUSTED.
EMBED_MAX_RETRIES = 3
EMBED_RETRY_DELAY_SECONDS = 60

# Checkpoint local para reanudar indexaciones interrumpidas.
EMBED_CHECKPOINT_PATH = ".cache/embeddings/retiro_madrid.json"

EMBED_RESUME = "true"

# --- Indexación ---
INDEX_BATCH_SIZE = 100  # vectores por lote en collection.upsert()
HNSW_SPACE = "cosine"  # métrica del índice (contrato compartido)

# --- Retrieval ---
TOP_K = 3

# Límite opcional para experimentos de indexación.
# None indica que se procesa el corpus completo.
# Si se establece un límite, el orquestador debe aplicarlo antes de generar
# embeddings mediante embed.limitar_chunks().
MAX_CHUNKS = None

# Fichero JSONL donde se anota cada consulta (output/ está en .gitignore).
LOG_FILE = "output/consultas.jsonl"


# --- Contexto de visita (AEMET y horario del parque) ---
ESTACION_RETIRO = "3195"  # estación AEMET Madrid-Retiro
CODIGO_MUNICIPAL="28079"
AREA_ALERTA="72"

URL_AEMET = (
    "https://opendata.aemet.es/opendata/api/observacion/convencional/datos/estacion/"
)

BASE_URL_AEMET = "https://opendata.aemet.es/opendata/api/"

EP_OBSERVACIONES= f"observacion/convencional/datos/estacion/{ESTACION_RETIRO}"
EP_PREVISIONES= f"prediccion/especifica/municipio/horaria/{CODIGO_MUNICIPAL}"
EP_AVISOS=f"avisos_cap/ultimoelaborado/area/{AREA_ALERTA}"

TIEMPO_MAXIMO = 8  # segundos de espera por petición a AEMET

# Umbrales de viento del protocolo del Retiro 2026
# (corpus: seguridad_protocolo_alertas_retiro.pdf).
VIENTO_NARANJA_KMH = 45.0
VIENTO_ROJA_KMH = 60.0

# Horario del parque (corpus: informacion_practica_guia_visitante_retiro.pdf).
HORA_APERTURA = 6
HORA_CIERRE_INVIERNO = 22  # octubre a marzo
HORA_CIERRE_VERANO = 24  # abril a septiembre
MESES_VERANO = range(4, 10)

# El horario es hora local de Madrid, no la del servidor.
ZONA_HORARIA = "Europe/Madrid"

AVISO_NO_OFICIAL = (
    "Comparación orientativa con los umbrales del protocolo. El estado oficial "
    "del parque se publica en los paneles de los accesos y en @MADRID."
)


# --- Generación ---
# Sin calibrar todavía. 0.0 significa que la compuerta de score no descarta nada
# y la abstención recae en el centinela del prompt: es preferible a inventarse un
# umbral que silencie respuestas correctas. Calibrarlo con
# scripts/validation/calibrar_umbral.py sobre el índice real y fijarlo en .env.
SCORE_MINIMO = 0.65

# Texto fijo en español. Si el banco de preguntas crece en otros idiomas,
# convendría traducirlo según el idioma detectado en la consulta.
MENSAJE_ABSTENCION = (
    "No he encontrado esa informacion en los documentos del Parque del Retiro "
    "que tengo disponibles. Puedes consultarlo en la web municipal "
    "(madrid.es) o en esmadrid.com."
)

# --- Índice preconstruido ---
INDEX_URL = "https://github.com/adxalex/retiro_rag/releases/download/index-v1/chroma_retiro_madrid.zip"
# SHA-256 esperado de chroma_retiro_madrid.zip.
INDEX_SHA256 = "176c11459f4d681da77b92b5b62daabefb85c628d612d19da099755f2143a882"