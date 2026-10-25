# Arquitectura del pipeline RAG · Retiro RAG

## 1. Objetivo

Construir un sistema RAG modular que permita preparar e indexar el corpus de El Retiro, recuperar contexto relevante y generar respuestas sustentadas exclusivamente en ese contexto. La lógica RAG debe poder utilizarse sin Streamlit.

## 2. Pipeline offline

```text
Documentos → load → chunk → embed → EmbeddingCheckpoint → index → ChromaDB persistente
```

- `src/load.py`: carga PDF, Markdown y el tercer formato acordado; genera `LoadedDocument`.
- `src/chunk.py`: normaliza lo necesario para fragmentar y genera `ChunkRecord` trazables.
- `src/embed.py`: transforma el texto de cada chunk en un vector.
- `src/embedding_cache.py`: `EmbeddingCheckpoint` recupera vectores todavía válidos y guarda atómicamente cada lote nuevo antes de que el conjunto completo pase a indexación.
- `src/index.py`: guarda ID, texto, vector y metadata en ChromaDB.

Este pipeline se ejecuta para crear o regenerar el índice, no con cada pregunta.

## 3. Pipeline online

```text
Pregunta → retrieval top-k → contexto → prompt → LLM → respuesta y evidencias
```

- `src/retrieve.py`: consulta ChromaDB y genera `RetrievedChunk`.
- `src/generate.py`: construye el prompt, aplica grounding y gestiona la abstención.
- `responder()`: API interna común.
- `main.py`: expone `--query` y `--ask`.
- `app.py`: presenta el asistente RAG mediante Streamlit.

## 4. Fronteras

### Alex · corpus e ingesta

Entrega a Alejandra `LoadedDocument` conformes al contrato. La carga se ocupa de extracción, páginas vacías, texto ilegible y metadata documental.

### Alejandra · chunking e indexación

Recibe `LoadedDocument`, realiza la normalización necesaria para fragmentar, genera IDs estables, embeddings y una colección ChromaDB persistente y regenerable.

### David · retrieval y aplicación

Recibe la colección, recupera chunks, adapta la distancia a `score`, genera la respuesta y expone CLI y Streamlit.

## 5. Configuración centralizada

Declarar en `config.py` o mediante variables de entorno documentadas:

```text
CHUNK_SIZE
CHUNK_OVERLAP
MAX_CHUNKS
TOP_K
EMBEDDING_MODEL
LLM_MODEL
CHROMA_DIR
COLLECTION_NAME
EMBED_RESUME
EMBED_CHECKPOINT_PATH
```

`MAX_CHUNKS` limita, si se utiliza, los chunks indexados. `TOP_K` determina cuántos solicita retrieval. Se debe comparar al menos dos valores de K.

`EMBED_RESUME` activa o desactiva la reutilización del checkpoint y vale `true` por defecto. Si está desactivado, el pipeline solicita de nuevo todos los embeddings y no carga ni crea el checkpoint. `EMBED_CHECKPOINT_PATH` indica la ruta del archivo JSON reanudable; su valor predeterminado es `.cache/embeddings/retiro_madrid.json`. Cada lote validado se guarda de forma atómica para poder continuar una ejecución interrumpida sin repetir los embeddings válidos.

## 6. Comandos previstos

```bash
python -m scripts.index_corpus --dry-run
python -m scripts.index_corpus
python main.py --index
python main.py --query "¿Qué es el Palacio de Cristal?"
python main.py --ask "¿Qué es el Palacio de Cristal?"
python main.py --ask "..." --top-k 5 --category seguridad --score-minimo 0.35
python main.py --ask "..." --contexto --json
python main.py --saludo
streamlit run app.py
```

`python -m scripts.index_corpus` reconstruye la colección por defecto. `python main.py --index` conserva la colección existente; para reconstruirla desde esta CLI se utiliza `python main.py --index --recreate-index`.

El modo `dry_run` solo ejecuta carga, chunking y resumen. Retorna antes de la etapa de embeddings: no llama a Gemini, no accede a ChromaDB y no instancia, crea ni modifica `EmbeddingCheckpoint`.

`--top-k` fija cuántos fragmentos recupera `--query`/`--ask`; `--category` filtra por categoría; `--score-minimo` sobrescribe el umbral de abstención para esa consulta; `--contexto` añade a `--ask` los fragmentos usados; `--json` cambia la salida a JSON; `--saludo` muestra el saludo contextual con el tiempo del Retiro.

## 7. Regeneración del índice

Los embeddings almacenados dejan de ser reutilizables cuando cambia el texto del chunk, el modelo de embeddings o la dimensión de los vectores. Los cambios de chunking —tamaño, solapamiento, separadores o estrategia— y los cambios de corpus —contenido, documentos incluidos o selección mediante `MAX_CHUNKS`— también invalidan el resultado porque modifican los textos, identificadores o conjunto de chunks.

`EmbeddingCheckpoint` reutiliza una entrada únicamente si coinciden `chunk_id`, hash del texto y modelo de embeddings, y si el vector y su dimensión son válidos. Por tanto, al cambiar cualquiera de los elementos anteriores se deben regenerar los embeddings afectados y reconstruir la colección para evitar registros antiguos. En particular, reconstruir la colección si cambia:

- Modelo o dimensión de embeddings.
- `CHUNK_SIZE` o `CHUNK_OVERLAP`.
- Separadores o estrategia de chunking.
- `MAX_CHUNKS` o selección del corpus.
- Contrato de metadata incompatible.

No deben mezclarse vectores de configuraciones diferentes.

`LLM_MODEL` solo controla la generación de la respuesta online. Cambiar únicamente `LLM_MODEL` no modifica los embeddings ni obliga a reconstruir el índice.

## 8. Logging mínimo

Registrar pregunta, `top_k`, número de chunks, tiempo total, modelo de embeddings y modelo de generación. También es recomendable registrar la abstención. Nunca se registran claves.

## 9. Manejo de errores

- Una pregunta vacía produce un error sin llamar al LLM.
- Debe definirse un límite para preguntas excesivamente largas.
- Un corpus vacío no crea silenciosamente un índice inútil.
- Un documento ilegible se identifica con claridad.
- Sin evidencia suficiente, el sistema se abstiene.

## 10. Interfaz

El asistente RAG muestra chat, respuesta, fuentes, chunks recuperados y una tabla con K, número de chunks, tiempo y modelo. Streamlit llama a `responder()` y no reimplementa la lógica RAG.
