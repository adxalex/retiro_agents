> Base: RAG del Retiro, copiado de adxalex/retiro_rag (commit 724c832). El agente se construye encima.
# Retiro RAG

Sistema RAG sobre el Parque de El Retiro. El proyecto carga y fragmenta un corpus documental curado, genera embeddings con Gemini, construye un índice persistente en ChromaDB y recupera contexto trazable para responder preguntas con fuentes.

## Estado del proyecto

El proyecto se encuentra en fase avanzada de integración del MVP.

Actualmente están implementados:

- Carga y validación de documentos PDF, Markdown y CSV.
- Chunking configurable, deduplicado y trazable.
- Generación de embeddings por lotes con reintentos ante límites de cuota.
- Checkpoint persistente y reanudable para conservar embeddings completados.
- Indexación persistente en ChromaDB.
- Retrieval con distancia coseno, filtros de metadata y `top_k`.
- Generación de respuestas fundamentadas con fuentes y mecanismo de abstención.
- CLI para indexación, retrieval y respuesta completa.
- Interfaz de Streamlit.
- Autenticación y validación de modelos de Gemini.
- Pruebas unitarias y de integración.
- Evaluación de retrieval con el corpus completo y embeddings reales.
- Experimento con dos configuraciones de chunking.

Continúan pendientes de validación o cierre:

- Evaluación end-to-end de generación sobre el banco completo de preguntas.
- Calibración definitiva del umbral de abstención.
- Validación final de la interfaz de Streamlit.
- Consolidación de la documentación y de las evidencias del MVP.

## Arquitectura

```text
Pipeline offline

Documentos
    → load
    → chunk
    → embed
    → index
    → ChromaDB

Pipeline online

Pregunta
    → embed_query
    → retrieve
    → generate
    → responder
    → CLI / Streamlit
```

El pipeline offline se coordina desde `src/pipeline.py`. La interfaz de terminal para construir el índice está en `scripts/index_corpus.py`.

## Estructura principal

```text
data/
└── processed/
    ├── historia_monumentos_jardines/
    ├── flora_fauna/
    ├── flora_fauna_arte_cultura_actividades/
    └── itinerarios_informacion_practica_seguridad/

docs/
├── architecture/
├── contracts/
├── contributing/
├── corpus/
└── evaluation/

entregables/
├── evidencias/
├── experimentos/
└── informe_decisiones.md

queries/
├── banco_preguntas_bloque_b.md
└── banco_preguntas_bloque_c.md

scripts/
├── corpus/
├── etl/
├── experiments/
├── validation/
└── index_corpus.py

src/
├── load.py
├── chunk.py
├── embed.py
├── embedding_cache.py
├── index.py
├── pipeline.py
├── retrieve.py
├── generate.py
└── gemini_auth.py

tests/
├── fixtures/
├── test_block_b_pipeline.py
├── test_chunk.py
├── test_embed.py
├── test_embedding_cache.py
├── test_generate.py
├── test_index.py
├── test_main.py
├── test_pipeline.py
├── test_pipeline_retrieve.py
└── test_retrieve.py
```

## Documentación

- [Contrato compartido](docs/contracts/contrato_compartido_mvp_retiro.md)
- [Arquitectura del pipeline](docs/architecture/pipeline_rag.md)
- [Alcance y fuentes](docs/corpus/alcance_y_fuentes.md)
- [Flujo de trabajo con Git](docs/contributing/flujo_git.md)
- [Informe de decisiones](entregables/informe_decisiones.md)

## Requisitos

- Python 3.10 o superior.
- Git.
- Una clave válida para la API de Gemini.
- Dependencias incluidas en `requirements.txt`.
- `pytest` y dependencias de desarrollo para ejecutar las pruebas.

## Instalación

```bash
git clone https://github.com/adxalex/retiro_rag.git
cd retiro_rag

python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Para instalar también las dependencias de testing:

```bash
python -m pip install -r requirements-dev.txt
```

A continuación hay que crear el archivo `.env` con las claves, tal como se
describe en [Variables de entorno](#variables-de-entorno). Sin él, el sistema
falla al ejecutar la primera consulta:

```bash
cp .env.example .env      # copy .env.example .env en Windows
```

### Activación del entorno

En Linux o macOS:

```bash
source .venv/bin/activate
```

En PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

## Variables de entorno

Copia `.env.example` como `.env` y añade una clave válida:

```dotenv
GEMINI_API_KEY=
LLM_MODEL=gemini-3.6-flash
EMBEDDING_MODEL=gemini-embedding-001

# Ruta local del índice Chroma preconstruido.
CHROMA_DIR=chroma
```

También se admite `GOOGLE_API_KEY` como nombre alternativo para la clave.

El archivo `.env` contiene información sensible y no debe subirse al repositorio.

`CHROMA_DIR` define la ruta local donde se encuentra la colección persistente de ChromaDB.
Por defecto se utiliza `chroma`.

En una instalación normal, el índice preconstruido se descarga con:

```bash
python -m scripts.download_index
```

El script instala el índice en la ruta indicada por `CHROMA_DIR`, por lo que no es necesario regenerar los embeddings ni reconstruir la colección para ejecutar el sistema.

## Índice Chroma preconstruido

El índice vectorial validado del proyecto se distribuye como un artefacto preconstruido para evitar regenerar embeddings y reconstruir ChromaDB en cada instalación.

La colección incluida es:

```text
COLLECTION_NAME=retiro_madrid
EMBEDDING_MODEL=gemini-embedding-001
HNSW_SPACE=cosine
```

El artefacto se publica en la release `index-v1` del repositorio.

### Descargar el índice

Con el entorno virtual activado y las dependencias instaladas:

```bash
python -m scripts.download_index
```

El script:

- descarga `chroma_retiro_madrid.zip` desde la release oficial;
- verifica su integridad mediante SHA-256;
- extrae el contenido en `CHROMA_DIR`;
- utiliza `chroma` como ruta por defecto;
- no sobrescribe un índice existente salvo que se solicite explícitamente.

La ruta puede configurarse mediante `.env`:

```dotenv
CHROMA_DIR=chroma
```

Si el índice ya existe y se desea sustituir deliberadamente:

```bash
python -m scripts.download_index --force
```

`--force` elimina el directorio configurado en `CHROMA_DIR` antes de instalar el índice descargado, por lo que debe utilizarse únicamente cuando se quiera reemplazar de forma consciente una copia local existente.

### Ejecutar el sistema con el índice preconstruido

Una vez descargado el índice, no es necesario ejecutar la pipeline offline de embeddings e indexación.

Para comprobar el retrieval:

```bash
python main.py --query "¿A qué hora abre el Retiro?"
```

Para ejecutar una respuesta RAG completa:

```bash
python main.py --ask "¿A qué hora abre el Retiro?"
```

Para iniciar la interfaz:

```bash
streamlit run app.py
```

El flujo normal de ejecución queda así:

```text
Pregunta
    → embedding de la consulta
    → retrieval sobre el índice Chroma preconstruido
    → generación de respuesta
    → CLI / Streamlit
```

La consulta del usuario sigue necesitando generar su embedding en tiempo de ejecución, y la respuesta completa utiliza el modelo generativo configurado. Lo que se evita es regenerar los embeddings de todo el corpus y reconstruir la colección ChromaDB.

### Cuándo reconstruir el índice

No debe reconstruirse el índice para una ejecución normal.

La reconstrucción solo es necesaria cuando cambia alguno de estos elementos:

- el corpus indexado;
- la estrategia de chunking;
- el modelo de embeddings;
- la dimensión de los vectores;
- la métrica de la colección.

Los comandos de indexación quedan reservados para mantenimiento o regeneración deliberada:

```bash
python main.py --index
python main.py --index --recreate-index
python -m scripts.index_corpus
```

Para una instalación normal desde `develop`, el flujo recomendado es:

```bash
git clone https://github.com/adxalex/retiro_rag.git
cd retiro_rag

python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m scripts.download_index
streamlit run app.py
```

## Configuración

La configuración común se encuentra en `config.py`.

Valores principales:

```text
DATA_DIR=data
CHROMA_DIR=chroma
COLLECTION_NAME=retiro_madrid

CHUNK_SIZE=500
CHUNK_OVERLAP=50

EMBED_BATCH_SIZE=32
EMBED_MAX_RETRIES=3
EMBED_RETRY_DELAY_SECONDS=60
EMBED_RESUME=True
EMBED_CHECKPOINT_PATH=.cache/embeddings/retiro_madrid.json
INDEX_BATCH_SIZE=100
HNSW_SPACE=cosine

TOP_K=3
MAX_CHUNKS=None

LLM_MODEL=gemini-3.6-flash
RAG_SCORE_MINIMO=0.65
```

`MAX_CHUNKS=None` indica que el pipeline normal procesa el corpus completo. La limitación de chunks queda reservada para experimentos y no se utiliza para construir el índice definitivo.

## Modelos de Gemini

El proyecto separa el modelo generativo del modelo utilizado para construir
y consultar el índice:

- `LLM_MODEL`: generación de respuestas.
- `gemini-embedding-001`: embeddings de documentos y consultas.

El índice validado se construyó con `gemini-embedding-001`, vectores de 3072
dimensiones y distancia coseno. El modelo generativo no forma parte de los
criterios de reutilización del checkpoint ni de la metadata vectorial; por
tanto, cambiar únicamente `LLM_MODEL` no obliga a reconstruir el índice.

`gemini-3.6-flash` es el valor predeterminado versionado en `config.py` y
`.env.example`. Se migró desde `gemini-2.5-flash`, que Google dejó de servir a
cuentas nuevas durante el desarrollo y devuelve un error 404.

El cambio se validó ejecutando el banco completo de 25 preguntas por CLI, más
comprobaciones de respuesta con citas, abstención y la interfaz de Streamlit.

Antes de utilizar los modelos, se recomienda comprobar su disponibilidad:

```bash
python -m scripts.validation.validate_gemini_models
python -m scripts.validation.validate_gemini_models --json
```

El validador comprueba la autenticación y la disponibilidad de las operaciones
de generación y embeddings. La opción `--json` muestra el informe completo en
formato JSON. Esta validación no modifica `config.py`.

## Corpus

El corpus cubre:

- Historia.
- Monumentos.
- Jardines.
- Flora y fauna.
- Arbolado.
- Arte y cultura.
- Actividades.
- Itinerarios.
- Información práctica.
- Seguridad.

Los documentos destinados al RAG se encuentran en `data/processed/`. Las fuentes originales, archivos de trabajo y documentos descartados pueden mantenerse fuera del corpus indexable.

Los bancos de preguntas se almacenan en `queries/`; no forman parte del corpus documental.

### Contrato documental

Cada documento cargado debe conservar como mínimo:

```text
document_id
text
source
category
corpus_group
```

Los PDF incorporan además `page` cuando la página contiene texto extraíble.

Todas las páginas de un mismo PDF conservan el mismo `document_id`. La página se diferencia mediante `page`.

Los chunks incorporan:

```text
chunk_id
document_id
text
source
chunk_index
category
corpus_group
page, cuando existe
```

El patrón contractual del identificador de chunk es:

```text
document-id__0000
document-id__0001
```

El doble guion bajo es obligatorio para separar el identificador del documento y el índice del chunk. No es obligatorio utilizarlo en los nombres originales de los archivos.

## Validación segura del corpus

Antes de llamar a Gemini puede ejecutarse el pipeline en modo `dry-run`:

```bash
python -m scripts.index_corpus --dry-run
```

Este modo realiza:

```text
load → chunk → resumen
```

No genera embeddings y no modifica ChromaDB.

Para obtener el resumen como JSON:

```bash
python -m scripts.index_corpus --dry-run --json
```

En la fotografía validada del corpus, el resultado exacto es:

```text
255 registros cargados
17 fuentes diferentes
1177 chunks
```

Estas cifras corresponden al corpus y a la configuración de chunking actuales:
`CHUNK_SIZE=500`, `CHUNK_OVERLAP=50` y `MAX_CHUNKS=None`.

## Construcción y reanudación del índice

Para generar los embeddings de todo el corpus y reconstruir la colección persistente:

```bash
python -m scripts.index_corpus
```

`python -m scripts.index_corpus` reconstruye Chroma por defecto. Este
comportamiento evita conservar chunks correspondientes a documentos eliminados
o versiones anteriores del corpus.

La generación de embeddings utiliza un checkpoint local reanudable:
`.cache/embeddings/retiro_madrid.json`.

Cada lote completado se valida y se guarda atómicamente antes de continuar. Si
la ejecución se interrumpe o se produce un error de cuota, puede repetirse el
comando: se reutilizan los embeddings cuyo `chunk_id`, hash del texto y modelo
siguen siendo válidos, y solo se solicitan los chunks pendientes.

Para realizar un `upsert` sin eliminar previamente la colección:

```bash
python -m scripts.index_corpus --keep-existing
```

`python -m scripts.index_corpus --keep-existing` conserva la colección y
realiza un `upsert`. Puede utilizarse durante el desarrollo, pero no sustituye a
una reconstrucción cuando el corpus cambia: actualiza los identificadores
presentes, pero no elimina registros antiguos que hayan desaparecido del corpus.

La CLI principal también está conectada con el pipeline:

```bash
python main.py --index
```

Este comando conserva la colección existente. La reconstrucción explícita mediante la CLI se solicita con:

```bash
python main.py --index --recreate-index
```

El índice local validado presenta este estado:

- Colección: `retiro_madrid`.
- Registros: 1177.
- Modelo de embeddings: `gemini-embedding-001`.
- Dimensión: 3072.
- Métrica: coseno (`HNSW_SPACE=cosine`).

La colección debe reconstruirse cuando cambie cualquiera de estos elementos:

- Corpus.
- Estrategia de chunking.
- `CHUNK_SIZE`.
- `CHUNK_OVERLAP`.
- Modelo de embeddings.
- Dimensión de los vectores.
- Métrica de ChromaDB.
- Convención de `chunk_id`.

Cambiar únicamente `LLM_MODEL` no afecta a los embeddings ni obliga a
reconstruir el índice.

El checkpoint y la colección Chroma son artefactos derivados locales. Están
excluidos de Git y no deben versionarse:

- `.cache/embeddings/`
- `chroma/`

## Retrieval

Una vez construida la colección, `src/retrieve.py`:

1. Valida la consulta.
2. Genera su embedding con `RETRIEVAL_QUERY`.
3. Consulta ChromaDB.
4. Recupera los `top_k` chunks.
5. Convierte la distancia coseno en un `score`.
6. Ordena los resultados de mayor a menor relevancia.
7. Conserva la metadata utilizada para trazabilidad y citas.

La conversión aplicada es:

```text
score = max(0, min(1, 1 - distance))
```

El retrieval admite filtros opcionales de metadata mediante `where`.

## Evaluación

Los bancos de preguntas se encuentran en `queries/` y contienen casos:

- Respondibles.
- Parcialmente respondibles.
- Fuera del corpus.
- De comprobación de fuentes, grounding, citas y abstención.

### Evaluación simulada

El banco de retrieval puede ejecutarse con embeddings deterministas de juguete:

```bash
python -m scripts.validation.eval_preguntas --simulado --top-k 3
python -m scripts.validation.eval_preguntas --simulado --top-k 5
```

Con estos embeddings simulados se obtiene:

```text
Recall@3 = 47 %
Recall@5 = 60 %
```

Estas cifras validan el recorrido técnico del evaluador, pero no representan la calidad del índice real.

### Evaluación con embeddings reales

La evaluación de retrieval se repitió sobre la colección completa, construida
con `gemini-embedding-001`:

```bash
python -m scripts.validation.eval_preguntas --top-k 3 --detalle
python -m scripts.validation.eval_preguntas --top-k 5 --detalle
```

Resultados de recuperación de la fuente esperada:

| Configuración | Fuentes encontradas | Recall de fuente |
| ------------- | ------------------: | ---------------: |
| `top_k=3`     |               11/15 |           73,3 % |
| `top_k=5`     |               12/15 |           80,0 % |

El denominador está formado por las 15 preguntas que tienen una fuente esperada declarada. Las 10 preguntas de abstención quedan fuera de esta métrica.

El recall de fuente comprueba si el nombre de la fuente esperada aparece entre
los resultados recuperados. Esta evaluación de retrieval no valida la respuesta
final, su grounding, la calidad de las citas ni la abstención end-to-end.

Las evidencias textuales sanitizadas se conservan en:

- [`eval_top_k_3.txt`](entregables/evidencias/evaluacion_real/eval_top_k_3.txt)
- [`eval_top_k_5.txt`](entregables/evidencias/evaluacion_real/eval_top_k_5.txt)
- [`umbral_top_k_3.txt`](entregables/evidencias/evaluacion_real/umbral_top_k_3.txt)
- [`umbral_top_k_5.txt`](entregables/evidencias/evaluacion_real/umbral_top_k_5.txt)

Regenerar estas evaluaciones reales consume API y los comandos con redirección
sobrescriben los archivos de evidencia existentes.

### Abstención y umbral

Los informes de calibración producen una recomendación automática de `0.70`.
Este valor es provisional, no un umbral definitivo: existe solapamiento entre
los scores de preguntas respondibles y preguntas fuera del corpus.

El evaluador actual mide retrieval y fuentes, pero no ejecuta la generación end-to-end. Por tanto, las 10 preguntas de abstención todavía deben validarse mediante el modelo generativo antes de adoptar un umbral definitivo.

## Experimento de chunking

El proyecto compara dos configuraciones:

```text
500 caracteres con overlap 50
800 caracteres con overlap 100
```

Para reproducir el experimento:

```bash
python -m scripts.experiments.compare_chunking \
  --input tests/fixtures/loaded_documents_chunking_experiment.json \
  --config 500:50 \
  --config 800:100 \
  --output entregables/experimentos/comparacion_chunking.json
```

En PowerShell:

```powershell
python -m scripts.experiments.compare_chunking `
  --input "tests\fixtures\loaded_documents_chunking_experiment.json" `
  --config "500:50" `
  --config "800:100" `
  --output "entregables\experimentos\comparacion_chunking.json"
```

Resultado del fixture representativo:

| Configuración | Chunks | Longitud media | Mediana | Máximo |
| ------------- | -----: | -------------: | ------: | -----: |
| 500:50        |     21 |         398,90 |     450 |    491 |
| 800:100       |     13 |         667,38 |     723 |    777 |

La configuración `500:50` produce fragmentos más pequeños y numerosos. La configuración `800:100` reduce el número de fragmentos y conserva contextos más extensos.

Este experimento no limita el corpus utilizado en la indexación final.

## Pruebas

Para ejecutar toda la batería:

```bash
python -m pytest -q
```

Para mostrar cada prueba:

```bash
python -m pytest -v
```

La batería actual incluye pruebas de:

- Contrato de documentos y chunks.
- Configuración de chunking.
- Trazabilidad.
- Determinismo.
- Procesamiento de embeddings por lotes.
- Reintentos ante errores de cuota.
- Persistencia e invalidación del checkpoint.
- Reutilización de embeddings y conservación del orden.
- Conservación de lotes completados después de un fallo.
- Dimensión y validez de vectores.
- Conservación de metadata.
- Sanitización para ChromaDB.
- Idempotencia.
- Reconstrucción de la colección.
- Integración entre pipeline, Chroma y retrieval.
- CLI de indexación, consulta y respuesta.
- Retrieval.
- Filtros.
- Conversión de distancia a score.
- Generación y abstención mediante dobles.
- Evaluación simulada.

Resultado de la ejecución registrada:

```text
290 tests superados, 2 warnings de dependencias
```

La ejecución registrada utilizó dobles, clientes simulados y colecciones
temporales; no hizo llamadas reales a Gemini. Los smoke tests reales se ejecutan
por separado.

## Validaciones auxiliares

### Validación de modelos

```bash
python -m scripts.validation.validate_gemini_models
```

### Smoke test real de embeddings

```bash
python -m scripts.validation.smoke_test_embeddings --count 35
```

Este comando consume la API y requiere una clave válida.

### Validación del corpus

```bash
python -m scripts.validation.validate_corpus
```

### Cobertura documental del retrieval

`scripts/validation/retrieval_coverage.py` contiene funciones diagnósticas de
cobertura, pero actualmente no define `main()` y no se presenta como una CLI
operativa. Que un documento no aparezca en una pregunta no implica
necesariamente que esté mal indexado: también puede indicar que el banco no
contiene una pregunta que lo cubra.

## Limitaciones conocidas

- Algunos PDF generan el aviso recuperable `incorrect startxref pointer`.
- Esos PDF continúan siendo legibles y sus páginas contienen texto extraíble.
- Los PDF sin texto en una página omiten esa página durante la carga.
- El bloque de flora, fauna y arbolado representa una parte grande del corpus.
- La guía de aves contiene información general de la Comunidad de Madrid y no constituye un inventario específico del Retiro.
- La evaluación real realizada cubre retrieval de fuente, pero no valida la generación end-to-end, el grounding, las citas ni la abstención final.
- La recomendación automática de umbral `0.70` es provisional y requiere calibración definitiva.
- `generate.py`, `responder()` y Streamlit están implementados; falta completar su validación final en CLI y en la interfaz.
- El warning de AFC (`Automatic Function Calling`) procede de una limitación conocida del SDK y no afecta a la ejecución registrada.
- El índice actual está validado contra 255 registros, 17 fuentes y 1177 chunks; debe reconstruirse si cambia el corpus o la configuración vectorial.

## Seguridad

- No subir `.env`.
- No incluir claves en código, logs o capturas.
- No versionar `.venv/`.
- No versionar `__pycache__/`.
- No versionar `.pytest_cache/`.
- No compartir la colección Chroma si contiene datos locales o tiene un tamaño excesivo.
- Documentar siempre cómo reconstruir el índice.
- Validar manualmente cualquier cambio de modelo.

## Flujo recomendado antes de la entrega

1. Verificar mediante `dry-run` los 255 registros, 17 fuentes y 1177 chunks.
2. Ejecutar la suite completa.
3. Validar la disponibilidad de los modelos Gemini.
4. Verificar la integridad del checkpoint y de la colección local.
5. No reconstruir el índice salvo que cambie el corpus o la configuración.
6. Evaluar retrieval con `top_k=3` y `top_k=5`.
7. Validar generación, grounding, citas y abstención end-to-end.
8. Validar el flujo final en Streamlit.
9. Completar el informe de decisiones y versionar evidencias sanitizadas.

## Reparto técnico

- Bloque A: corpus e ingesta.
- Bloque B: chunking, embeddings, indexación y pipeline offline.
- Bloque C: retrieval, generación, respuesta y aplicación.

Las modificaciones que afecten a la interfaz entre bloques deben revisarse contra el contrato compartido.

## Evidencias para el cierre

Las evidencias textuales sanitizadas son prioritarias. Las capturas pueden
complementarlas, pero no son obligatorias ni las sustituyen. Pueden cubrir:

- Construcción correcta del índice.
- Consulta con recuperación relevante.
- Respuesta final con fuentes.
- Chunks y metadata recuperados.
- Comparación de valores de `top_k`.
- Ejemplo de abstención.
- Aplicación Streamlit.
