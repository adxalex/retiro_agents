"""Configuracion centralizada del sistema RAG - Parque de El Retiro."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Rutas ---
DATA_DIR = "data"
CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma")
COLLECTION_NAME = "retiro_madrid"

# Modelos estables seleccionados para el MVP.
# gemini-embedding-001 devuelve un vector por texto y mantiene compatibilidad
# con el procesamiento por lotes actual de embed.py.
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.6-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

# --- Chunking ---
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# --- Embeddings ---
EMBED_BATCH_SIZE = 32  # chunks por lote enviado a la API de Gemini embeddings

# Control de cuota para indexaciones grandes con el nivel gratuito de Gemini.
# Solo se aplica cuando Gemini responde con 429 RESOURCE_EXHAUSTED.
EMBED_MAX_RETRIES = int(os.getenv("EMBED_MAX_RETRIES", "3"))
EMBED_RETRY_DELAY_SECONDS = float(
    os.getenv("EMBED_RETRY_DELAY_SECONDS", "60")
)

# Checkpoint local para reanudar indexaciones interrumpidas.
EMBED_CHECKPOINT_PATH = os.getenv(
    "EMBED_CHECKPOINT_PATH",
    ".cache/embeddings/retiro_madrid.json",
)

EMBED_RESUME = (
    os.getenv("EMBED_RESUME", "true").strip().lower()
    in {"1", "true", "yes", "on"}
)

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
