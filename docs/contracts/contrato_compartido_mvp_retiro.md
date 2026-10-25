# Contrato compartido del MVP · Retiro RAG

**Estado:** propuesta corregida para aprobación del equipo  
**Alcance:** arquitectura RAG del Project Break, ajustada al MVP del bootcamp  
**Objetivo:** permitir que carga, chunking, embeddings, indexación, retrieval, generación e interfaz se desarrollen de forma autónoma sin romper la integración.

## 1. Principios del contrato

1. Cada etapa recibe y devuelve estructuras conocidas por todo el equipo.
2. Los identificadores deben ser estables y reproducibles con la misma entrada y configuración.
3. Cada chunk debe poder rastrearse hasta su documento, página y fuente.
4. La clasificación temática del contenido no debe confundirse con el reparto de trabajo.
5. ChromaDB solo recibirá metadata plana y sin valores `None`.
6. `responder()` será la interfaz interna común para CLI, Streamlit y posibles consumidores posteriores.
7. Un cambio en campos, tipos o significado exige actualizar fixtures, productores, consumidores y pruebas de contrato.

## 2. Flujo compartido

```text
PDF / TXT / MD / CSV
        │
        ▼
     load.py
        │  LoadedDocument
        ▼
    chunk.py
        │  ChunkRecord
        ▼
     embed.py
        │  vectores
        ▼
     index.py ──────► ChromaDB
                         │
                         ▼
                    retrieve.py
                         │  RetrievedChunk[]
                         ▼
                    generate.py
                         │
                         ▼
                      responder()
                         │  RAGResponse
                ┌────────┼────────┐
                ▼        ▼        ▼
               CLI   Streamlit  tests
```

## 3. Contrato 1: documento cargado

Intercambio entre `load.py` y `chunk.py`.

```json
{
  "document_id": "mock-folleto-retiro",
  "text": "El parque permanece abierto todos los días...",
  "source": "mock_folleto_retiro.pdf",
  "category": "informacion_practica",
  "corpus_group": "itinerarios_informacion_practica_seguridad",
  "page": 1
}
```

### Reglas

- `document_id`: obligatorio, único y estable dentro del corpus.
- `text`: obligatorio y no vacío después de aplicar `strip()`.
- `source`: obligatorio; nombre mostrable del documento original.
- `category`: obligatorio; tema semántico real del contenido.
- `corpus_group`: obligatorio en el MVP; identifica el bloque organizativo del corpus.
- `page`: entero positivo y 1-based cuando el elemento procede de una página. Si no aplica, la clave se omite completamente.
- Para PDF, `load.py` devuelve preferentemente un `LoadedDocument` por página. Así, los chunks pueden heredar una página inequívoca.

## 4. Contrato 2: chunk

Intercambio entre `chunk.py` y `embed.py` / `index.py`. También es la estructura serializable en JSONL.

```json
{
  "chunk_id": "mock-folleto-retiro__0000",
  "document_id": "mock-folleto-retiro",
  "text": "El parque permanece abierto todos los días...",
  "source": "mock_folleto_retiro.pdf",
  "chunk_index": 0,
  "category": "informacion_practica",
  "corpus_group": "itinerarios_informacion_practica_seguridad",
  "page": 1
}
```

### Reglas

- `chunk_id`: obligatorio y único.
- `document_id`: se hereda sin cambios del documento cargado.
- `text`: contiene exclusivamente el texto del fragmento.
- `chunk_index`: entero 0-based, consecutivo dentro del documento completo; no se reinicia en cada página.
- `source`, `category`, `corpus_group` y `page` se heredan del documento.
- Si `page` no existe en el documento, tampoco se incluye en el chunk.
- Con la misma entrada y la misma configuración de chunking, se deben producir los mismos IDs.

## 5. Identificadores

### `document_id`

Se genera como un slug estable, sin espacios, tildes ni dependencia del orden de carga:

```text
mock_folleto_retiro.pdf → mock-folleto-retiro
```

El corpus o manifiesto debe impedir colisiones entre dos documentos que produzcan el mismo slug. Si existe una colisión, deberá resolverse antes de indexar añadiendo un sufijo estable acordado por el equipo.

### `chunk_id`

```python
chunk_id = f"{document_id}__{chunk_index:04d}"
```

Ejemplos:

```text
mock-folleto-retiro__0000
mock-folleto-retiro__0001
mock-folleto-retiro__0002
```

Si cambia el tamaño, overlap, separadores o estrategia de chunking, se reconstruye la colección. No se mezclan chunks generados con configuraciones incompatibles.

## 6. Clasificación del corpus

Se separan dos conceptos que antes estaban mezclados:

- `category`: describe el tema real y permite filtros semánticos útiles.
- `corpus_group`: conserva los tres bloques utilizados para repartir la curación del corpus.

### Valores de `category`

Vocabulario inicial cerrado para el MVP:

```text
historia
monumentos
jardines
flora_fauna
arte_cultura
actividades
itinerarios
informacion_practica
seguridad
```

### Valores de `corpus_group`

```text
historia_monumentos_jardines
flora_fauna_arte_cultura_actividades
itinerarios_informacion_practica_seguridad
```

Cada documento recibe exactamente un valor de cada vocabulario. La clasificación debe corresponder al contenido, no a la persona que lo haya recopilado.

## 7. Persistencia en ChromaDB

Cada `ChunkRecord` se traduce así:

- `chunk_id` → ID del registro en ChromaDB.
- `text` → `document` que se convierte en embedding.
- Los demás campos → metadata plana.

Ejemplo de metadata:

```json
{
  "document_id": "mock-folleto-retiro",
  "source": "mock_folleto_retiro.pdf",
  "chunk_index": 0,
  "category": "informacion_practica",
  "corpus_group": "itinerarios_informacion_practica_seguridad",
  "page": 1
}
```

Antes de indexar se eliminan las claves cuyo valor sea `None`. La colección utilizará distancia coseno de forma explícita:

```python
metadata={"hnsw:space": "cosine"}
```

La indexación debe ser repetible. Ejecutarla dos veces con los mismos IDs no puede crear duplicados; se utilizará `upsert` o una reconstrucción controlada de la colección.

## 8. Contrato 3: resultado de retrieval

Intercambio entre `retrieve.py` y `generate.py`.

```json
{
  "chunk_id": "mock-folleto-retiro__0000",
  "document_id": "mock-folleto-retiro",
  "text": "El parque permanece abierto todos los días...",
  "source": "mock_folleto_retiro.pdf",
  "chunk_index": 0,
  "category": "informacion_practica",
  "corpus_group": "itinerarios_informacion_practica_seguridad",
  "page": 1,
  "score": 0.83
}
```

### Reglas

- Retrieval devuelve el chunk original y añade `score`.
- `score` representa relevancia normalizada: cuanto mayor sea, más relevante es el resultado.
- ChromaDB devuelve una distancia. Como la colección se fija en coseno, `retrieve.py` realizará la adaptación:

```python
score = max(0.0, min(1.0, 1.0 - distance))
```

- Esta conversión pertenece a `retrieve.py`, no a `chunk.py` ni a `index.py`.
- Los resultados se devuelven ordenados de mayor a menor `score`.
- Si en el futuro se cambia la métrica de Chroma, también deberá cambiar el adaptador. No se aplicará `1 - distance` de forma genérica a otras métricas.

## 9. Contrato 4: respuesta final

Salida pública de `responder()` y única estructura que necesitan CLI, Streamlit u otro consumidor.

```json
{
  "respuesta": "El parque abre a las 06:00...",
  "fuentes": ["informacion_practica_guia_visitante_retiro.pdf"],
  "citas": [
    {
      "n": 1,
      "source": "informacion_practica_guia_visitante_retiro.pdf",
      "page": 1,
      "chunk_id": "informacion-practica-guia-visitante-retiro__0000",
      "score": 0.83,
      "titulo": "Guía del visitante del Retiro",
      "organismo": "esMadrid, Turismo de Madrid",
      "oficial": true,
      "etiqueta": "fuente oficial",
      "texto": "Guía del visitante del Retiro · esMadrid, Turismo de Madrid, página 1"
    }
  ],
  "chunks": [
    {
      "chunk_id": "informacion-practica-guia-visitante-retiro__0000",
      "document_id": "informacion-practica-guia-visitante-retiro",
      "text": "El parque permanece abierto todos los días...",
      "source": "informacion_practica_guia_visitante_retiro.pdf",
      "chunk_index": 0,
      "category": "informacion_practica",
      "corpus_group": "itinerarios_informacion_practica_seguridad",
      "page": 1,
      "score": 0.83
    }
  ],
  "abstuvo": false,
  "motivo_abstencion": null
}
```

Las citas se enriquecen mediante `src/fuentes.py`. El catálogo traduce el
nombre técnico del archivo a una representación destinada a usuario:

- `titulo`: nombre legible de la fuente.
- `organismo`: organismo o autor responsable.
- `oficial`: indica si la fuente está catalogada como oficial.
- `etiqueta`: `"fuente oficial"` o `"fuente no oficial"`.
- `texto`: representación legible utilizada por la interfaz.

Si una fuente no figura en el catálogo, se genera un título legible a partir
del nombre del archivo y se considera no oficial por defecto.

Firma implementada:

```python
def responder(
    pregunta: str,
    top_k: int = TOP_K,
    score_minimo: float | None = None,
    collection: Any | None = None,
    client: Any | None = None,
    where: dict | None = None,
) -> dict:
```

- pregunta: consulta del usuario.
- top_k: número máximo de chunks recuperados.
- score_minimo: permite sobrescribir el umbral de abstención configurado para una consulta concreta.
- collection: permite inyectar una colección ChromaDB, especialmente en pruebas.
- client: permite inyectar el cliente generativo, evitando llamadas reales al modelo en pruebas.
- where: permite aplicar filtros de metadata durante retrieval.

La inyección de collection y client permite probar el flujo de respuesta sin depender de una colección ChromaDB persistente ni realizar llamadas reales al modelo generativo. where no es una dependencia inyectable, sino un filtro opcional de retrieval.

### Reglas

- Siempre devuelve `respuesta`, `fuentes`, `citas`, `chunks`, `abstuvo` y `motivo_abstencion`.
- `fuentes` no contiene duplicados.
- `citas` contiene la correspondencia entre las referencias numeradas utilizadas en la respuesta y los chunks recuperados, enriquecida con la información legible del catálogo de fuentes.
- `abstuvo` es `true` cuando el sistema no dispone de contexto suficiente para responder con fundamento.
- `motivo_abstencion` indica la causa cuando `abstuvo` es `true`.
- CLI y Streamlit llaman a la misma función; no duplican la lógica RAG.
- El MVP no necesita una API HTTP entre módulos para que este contrato sea válido.
- Las métricas pueden añadirse posteriormente como campo opcional o registrarse mediante logging sin romper el contrato mínimo.

### Criterio de abstención

El sistema aplica dos compuertas consecutivas:

1. **Umbral de retrieval.**  
   El umbral por defecto se obtiene de la variable de entorno `RAG_SCORE_MINIMO`:
   `SCORE_MINIMO = float(os.getenv("RAG_SCORE_MINIMO", "0.0"))`
   Si `score_minimo` se proporciona explícitamente a `responder()`, ese valor prevalece para la consulta.
   Si no se recupera ningún chunk, el sistema se abstiene con el motivo `sin_resultados`.
   Si el mejor resultado recuperado cumple:
   `top1.score < score_minimo`
   el sistema se abstiene sin llamar al modelo generativo.

   En ese caso, `motivo_abstencion` toma un valor con la forma:
   `score_bajo` (<score> < <umbral>)

2. **Abstención generativa.**
   Si el retrieval supera el umbral, se construye el prompt con los chunks recuperados y se llama al modelo generativo.
   El prompt obliga al modelo a devolver exactamente:
   `SIN_EVIDENCIA`
   cuando el contexto recuperado no permite responder con fundamento.
   Si el modelo devuelve ese centinela, el sistema se abstiene y establece:
   `motivo_abstencion = "el_modelo_no_vio_evidencia"`

Por tanto, los motivos de abstención previstos son:

- sin_resultados
- score_bajo (...)
- el_modelo_no_vio_evidencia

El umbral `RAG_SCORE_MINIMO` forma parte de la configuración del comportamiento del RAG y debe calibrarse con el índice real y el banco de preguntas. Un valor 0.0 desactiva en la práctica la compuerta por score y deja la decisión de abstención principalmente en manos del centinela generativo.

## 10. Reparto simplificado

### Integrante A: Alex · corpus e ingesta

- Curación de historia, monumentos y jardines.
- Búsqueda y documentación de fuentes.
- Implementación de `load.py`.
- Lectura de PDF, Markdown y un segundo formato acordado.
- Producción y validación de la metadata mínima.
- Pruebas de carga.

**Entregable:** los formatos elegidos cargan correctamente y conservan su fuente.

### Integrante B: Alejandra · chunking e indexación

- Curación de flora/fauna, arte/cultura y actividades.
- Implementación de `chunk.py`, `embed.py` e `index.py`.
- Chunking configurable.
- Generación de embeddings.
- ChromaDB persistente.
- Comparación de dos configuraciones de chunking.
- Pruebas de reindexado.

**Entregable:** el corpus produce chunks trazables y un índice regenerable.

### Integrante C: David · retrieval y aplicación

- Curación de itinerarios, información práctica y seguridad.
- Implementación de `retrieve.py` y `generate.py`.
- API interna `responder()`.
- Estrategia de abstención.
- CLI con `--query` y `--ask`.
- Aplicación asistente RAG en Streamlit.

**Entregable:** una pregunta devuelve respuesta, chunks, fuentes y métricas.

### Trabajo compartido

- Crear entre 8 y 15 preguntas de evaluación.
- Comparar al menos dos valores de `top_k`.
- Revisar las pull requests de otros integrantes.
- Acordar y aplicar logging básico.
- Completar el README.
- Redactar el informe de decisiones.
- Preparar la presentación final.

## 11. Responsabilidades detalladas y límites

### 11.1. Integrante A: Alex · corpus e ingesta

**Rama propuesta:** `feature/corpus-loaders`

#### Entrada de A

- Fuentes documentales seleccionadas y registradas.
- Archivos de historia, monumentos y jardines.
- Vocabulario de metadata aprobado en este contrato.

#### Trabajo de A

1. Buscar y documentar fuentes fiables para sus bloques del corpus.
2. Registrar el origen y el criterio de selección de cada documento.
3. Preparar archivos utilizables en PDF, Markdown y un segundo formato acordado.
4. Implementar `load.py` para los tres formatos.
5. Extraer el texto sin perder la relación con el archivo de origen.
6. Generar `document_id` estable y asignar `source`, `category` y `corpus_group`.
7. En PDF, devolver preferentemente un `LoadedDocument` por página con `page` 1-based.
8. Omitir `page` cuando el formato no tenga páginas.
9. Validar los campos obligatorios y rechazar documentos vacíos o ilegibles con errores claros.
10. Crear fixtures de `LoadedDocument` con y sin página para desbloquear a B.
11. Añadir pruebas unitarias, de integración y de contrato para la carga.

#### Salida de A

- Corpus documentado de historia, monumentos y jardines.
- Secuencia de `LoadedDocument` conforme al contrato.
- Fixtures representativos para desarrollar chunking.
- Pruebas que demuestren carga, metadata y trazabilidad.

#### Fuera del alcance de A

- Decidir cómo se fragmenta el texto o generar `chunk_id`: bloque B.
- Generar embeddings o escribir en ChromaDB: bloque B.
- Recuperar contexto, convertir distancias o generar respuestas: bloque C.
- Implementar CLI o Streamlit: bloque C.

#### Criterios de aceptación de A

1. Los tres formatos elegidos cargan correctamente.
2. Cada salida contiene `document_id`, texto no vacío, fuente y clasificación válida.
3. Los PDF conservan su página real conforme a la decisión del equipo.
4. Los formatos sin páginas no contienen `page` ni valores `None` destinados a ChromaDB.
5. Los fixtures de A pasan las pruebas de contrato y pueden ser consumidos por `chunk.py`.

### 11.2. Integrante B: Alejandra · chunking e indexación

**Rama propuesta:** `feature/chunking-embeddings-index`

#### Entrada de B

Una secuencia de `LoadedDocument` válidos producidos por el bloque A.

#### Trabajo de B

1. Implementar `chunk.py` con la estrategia y configuración acordadas.
2. Conservar toda la metadata recibida y generar `chunk_index` y `chunk_id` estables.
3. Omitir `page` cuando no aplique, sin enviar `None` a ChromaDB.
4. Permitir la serialización de los chunks a JSONL si el repositorio mantiene esa salida intermedia.
5. Implementar `embed.py` con el modelo provisional acordado por el equipo.
6. Configurar la colección ChromaDB con métrica coseno.
7. Implementar `index.py` y traducir correctamente cada chunk a ID, texto y metadata.
8. Garantizar que reindexar los mismos chunks no genera duplicados.
9. Entregar fixtures pequeños para que el bloque C pueda desarrollar retrieval sin esperar al corpus definitivo.
10. Añadir pruebas unitarias, de integración y de contrato correspondientes a este bloque.

#### Salida de B

- `ChunkRecord[]` conformes al contrato.
- Embeddings generados con un único modelo y configuración conocidos.
- Colección ChromaDB creada e indexada.
- Fixtures y tests que permitan verificar la integración con el bloque C.

#### Fuera del alcance de B

- Extracción y carga de PDF: bloque A.
- Curación o clasificación manual del corpus: responsabilidad de quien prepara cada documento.
- Conversión de distancia a `score`: bloque C, dentro de `retrieve.py`.
- Generación de la respuesta, abstención y fuentes finales: bloque C.
- CLI, Streamlit y API central del proyecto: bloque C o integración conjunta según el reparto final.
- Extensiones que no formen parte del MVP acordado.

#### Criterios de aceptación de B

1. Recibe los fixtures de `LoadedDocument` acordados con A.
2. Devuelve chunks válidos y trazables conforme a este documento.
3. Compara dos configuraciones de chunking con los mismos documentos y métricas acordadas.
4. Genera embeddings reproducibles con el modelo y versión fijados.
5. Construye una colección ChromaDB persistente, consultable y sin duplicados.
6. Pasa las pruebas unitarias, de integración y de reindexado del bloque.
7. Entrega a C una rutina de indexación y fixtures suficientes para implementar retrieval.
8. Documenta tamaño, overlap, separadores, modelo, nombre de colección, ruta persistente y métrica.

### 11.3. Integrante C: David · retrieval y aplicación

**Rama propuesta:** `feature/retrieval-application`

#### Entrada de C

- Colección ChromaDB o rutina de construcción proporcionada por B.
- `ChunkRecord` y metadata conformes al contrato.
- Pregunta del usuario y valor de `top_k`.

#### Trabajo de C

1. Implementar `retrieve.py` contra la colección persistente.
2. Recuperar `top_k` resultados conservando IDs, texto, fuente y metadata.
3. Convertir la distancia coseno de ChromaDB al `score` definido por el contrato.
4. Ordenar los resultados de mayor a menor relevancia.
5. Implementar `generate.py` usando únicamente el contexto recuperado.
6. Definir y probar una regla sencilla y documentada de abstención.
7. Implementar la API interna `responder(pregunta, top_k)`.
8. Devolver siempre `respuesta`, `fuentes`, `citas`, `chunks`, `abstuvo` y `motivo_abstencion`.
9. La CLI expone las siguientes operaciones y modificadores:
   - `--query`: ejecuta únicamente retrieval.
   - `--ask`: ejecuta retrieval y generación completa.
   - `--top-k`: modifica el número de chunks recuperados.
   - `--category`: filtra el retrieval por categoría.
   - `--score-minimo`: sobrescribe para esa consulta el umbral de abstención.
   - `--contexto`: muestra también los chunks utilizados en una respuesta.
   - `--json`: produce salida JSON para consumo programático.
   - `--saludo`: muestra el saludo contextual y, cuando está disponible, información meteorológica.
   - `--index`: ejecuta la indexación del corpus.
   - `--recreate-index`: fuerza la reconstrucción de la colección al indexar.
   - `--dry-run`: valida carga y chunking sin generar embeddings ni modificar ChromaDB.
10. Implementar el asistente RAG en Streamlit sin duplicar la lógica RAG.
11. Mostrar respuesta, fuentes, chunks y métricas exigidas por el enunciado.
12. Añadir pruebas unitarias, de integración y de contrato para retrieval y respuesta.

En la ejecución ordinaria del asistente con un índice ya construido no es necesario ejecutar `--index`. Las consultas usan la colección persistente existente.

#### Salida de C

- Lista de `RetrievedChunk` conforme al contrato.
- `RAGResponse` consumible sin Streamlit.
- CLI funcional.
- Aplicación del asistente RAG funcional en Streamlit.
- Pruebas de retrieval, abstención y presentación de fuentes.

#### Fuera del alcance de C

- Modificar cómo A interpreta o clasifica los documentos.
- Modificar IDs, texto o metadata ya indexados por B.
- Cambiar el modelo de embeddings sin reconstruir el índice y coordinarlo con B.
- Duplicar la lógica de retrieval o generación dentro de CLI o Streamlit.

#### Criterios de aceptación de C

1. Una pregunta devuelve una estructura `RAGResponse` válida.
2. Cada chunk recuperado conserva su trazabilidad y tiene un `score` coherente.
3. Las fuentes finales se deduplican y corresponden a los chunks utilizados.
4. El sistema se abstiene cuando no dispone de contexto suficiente.
5. CLI y Streamlit consumen la misma función `responder()`.
6. Se muestran las métricas mínimas acordadas por el equipo.
7. Las pruebas funcionan con los fixtures de B y con la colección integrada.

## 12. Pruebas mínimas por bloque

### Bloque A: carga

- Carga correctamente PDF, Markdown y el tercer formato acordado.
- Rechaza archivos vacíos, ilegibles o con metadata obligatoria ausente.
- Genera `document_id` estable.
- Conserva `source`, `category` y `corpus_group`.
- Informa la página PDF como entero 1-based y omite la clave cuando no aplica.
- Sus fixtures cumplen el contrato de `LoadedDocument`.

### Bloque B: chunking, embeddings e indexación

#### Chunking

- Rechaza un documento sin `document_id`, sin `source`, sin categoría o con texto vacío.
- Produce chunks no vacíos.
- Respeta la configuración de tamaño y overlap.
- Mantiene `document_id`, `source`, `category`, `corpus_group` y `page`.
- Mantiene `page` ausente cuando no existe en la entrada.
- Produce IDs iguales al repetir la operación con la misma entrada y configuración.
- Mantiene `chunk_index` consecutivo a través de las páginas de un mismo PDF.

#### Embeddings

- Produce un vector por chunk.
- Todos los vectores tienen la misma dimensión.
- No mezcla modelos o dimensiones dentro de una colección.
- Informa claramente si el texto o el modelo no son válidos.

#### ChromaDB

- Indexa ID, documento y metadata según el contrato.
- No contiene metadata con valores `None`.
- Indexar dos veces no duplica registros.
- Permite filtrar por `category`, `corpus_group`, `source` y `document_id`.
- Una consulta mínima devuelve el `chunk_id` y la metadata original.

#### Integración con C

- C puede abrir o recibir la colección sin conocer detalles internos de chunking.
- El resultado bruto de Chroma conserva todos los campos necesarios para reconstruir un `RetrievedChunk`.
- Un fixture compartido permite probar el flujo antes de disponer del corpus completo.

### Bloque C: retrieval y aplicación

- Recupera como máximo `top_k` resultados y conserva todos los campos contractuales.
- Ordena los resultados de mayor a menor `score`.
- Convierte la distancia coseno sin alterar la metadata del chunk.
- Devuelve una respuesta con fuentes deduplicadas.
- Activa la abstención ante una pregunta sin contexto suficiente.
- `responder()` funciona independientemente de CLI y Streamlit.
- CLI y Streamlit muestran una salida coherente para la misma pregunta.
- Las pruebas pueden ejecutarse con los fixtures compartidos sin depender de todo el corpus real.

## 13. Política de cambios del contrato

El contrato está integrado en `develop`. Cualquier modificación de campos,
tipos o significado debe:

1. Realizarse en una rama independiente.
2. Actualizar productores y consumidores afectados.
3. Actualizar fixtures, mocks y pruebas de contrato.
4. Ser revisada por los responsables de los bloques implicados.
5. Fusionarse mediante pull request.

No deben introducirse cambios incompatibles directamente en `develop`.

## 14. Fixtures compartidos

El repositorio debe conservar al menos:

```text
tests/fixtures/loaded_documents.json
tests/fixtures/chunks.json
tests/fixtures/retrieved_chunks.json
tests/fixtures/rag_response.json
```

Los cuatro archivos actuarán como ejemplos ejecutables del contrato. Una modificación de su estructura deberá revisarse en equipo antes de fusionarse.

## 15. Decisiones contractuales consolidadas

Las siguientes decisiones están adoptadas para el MVP:

- [x] Los PDF producen un documento cargado por cada página con texto extraíble.
- [x] `category` y `corpus_group` son campos diferentes.
- [x] `chunk_index` es consecutivo dentro de cada documento.
- [x] La colección ChromaDB utiliza distancia coseno.
- [x] El modelo de embeddings se define en la configuración.
- [x] Un cambio de corpus, chunking, modelo, dimensión o métrica requiere evaluar la reconstrucción de la colección.
- [x] CLI y Streamlit consumen `responder()` sin duplicar la lógica RAG.
- [x] El umbral de abstención de retrieval se configura mediante `RAG_SCORE_MINIMO`.
- [x] La respuesta pública incluye `respuesta`, `fuentes`, `citas`, `chunks`, `abstuvo` y `motivo_abstencion`.

El contrato se considera consolidado para el MVP. Los cambios posteriores
deben seguir la política indicada en la sección 13.
