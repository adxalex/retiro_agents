# Spec 000 — Base RAG del Retiro (sistema actual)

> Estado: Aprobada · Fecha: 2026-10-13

## Contexto y objetivo
El repositorio parte del RAG del Retiro, importado de `retiro_rag` (commit `724c832`). Esta spec documenta lo que el sistema hace **hoy**, señalado en el código, como línea base antes de construir el agente multiagente del PB2. No describe mejoras: lo que falta o es frágil está en "Huecos detectados". El agente reutilizará sobre todo `responder()` y `rag_ask()`, la forma de las fuentes y citas, y el contexto de visita; por eso esos bloques tienen más detalle. Los RF describen comportamiento; los archivos y funciones que lo implementan están en la tabla de trazabilidad.

## Usuarios / actores
- Visitante del parque: pregunta por CLI o Streamlit.
- Equipo de desarrollo: construye el índice, valida y depura el retrieval.
- Futuro agente del PB2: consume `responder()`, `rag_ask()` y el contexto de visita como funciones de Python.

## Historias de usuario
- H1: Como visitante quiero preguntar por el Retiro y recibir una respuesta breve con sus fuentes para fiarme de ella.
- H2: Como visitante quiero que el asistente diga que no lo sabe cuando el corpus no lo cubre, en lugar de inventarlo.
- H3: Como visitante quiero saber al entrar si el parque está abierto y qué tiempo hace.
- H4: Como desarrollador quiero construir o descargar el índice y depurar qué fragmentos se recuperan.

## Requisitos funcionales (criterios de aceptación en EARS)

### A. Ingesta
- RF-1: CUANDO se cargue el corpus, EL SISTEMA recorrerá `DATA_DIR` de forma recursiva y producirá un documento por archivo Markdown, uno por página con texto de cada PDF (`page` empezando en 1) y uno por fila con `descripcion` de cada CSV, omitiendo las carpetas excluidas.
- RF-2: SI un Markdown o PDF no figura en el manifiesto del corpus, una `category`/`corpus_group` está fuera del vocabulario cerrado, un archivo no produce texto o se repite la pareja `document_id`+`page`, ENTONCES EL SISTEMA detendrá la carga con un error de validación.
- RF-3: CUANDO se fragmenten los documentos, EL SISTEMA generará chunks con `chunk_id = <document_id>__NNNN` consecutivo por documento (también entre páginas de un PDF), con la metadata del documento sin valores nulos, y la misma entrada producirá los mismos chunks.
- RF-4: SI `chunk_size` ≤ 0, `chunk_overlap` < 0, `chunk_overlap` ≥ `chunk_size`, los valores no son enteros o un documento incumple el contrato, ENTONCES EL SISTEMA rechazará el fragmentado con un error de validación.
- RF-5: DONDE se active la limpieza de líneas repetidas, EL SISTEMA eliminará las líneas de hasta 120 caracteres que se repitan en al menos el 60 % de las páginas (mínimo 3) de un mismo documento.

### B. Índice
- RF-6: CUANDO se generen embeddings del corpus, EL SISTEMA añadirá `vector`, `embedding_model` y `embedding_dimension` a cada chunk, en el orden de entrada, pidiendo lotes de `EMBED_BATCH_SIZE` con `task_type=RETRIEVAL_DOCUMENT`.
- RF-7: SI Gemini responde con 429 o `RESOURCE_EXHAUSTED`, ENTONCES EL SISTEMA reintentará el lote hasta `EMBED_MAX_RETRIES` veces esperando `EMBED_RETRY_DELAY_SECONDS`; cualquier otro error se propaga sin reintentos.
- RF-8: DONDE `EMBED_RESUME` esté activo, EL SISTEMA reutilizará un vector del checkpoint solo si coinciden el modelo, el `chunk_id` y el SHA-256 del texto, y guardará cada lote nuevo en cuanto se valide.
- RF-9: CUANDO se indexen chunks, EL SISTEMA hará upsert por lotes de `INDEX_BATCH_SIZE` en la colección `COLLECTION_NAME`, creada con métrica coseno y una huella del modelo y la dimensión de los embeddings.
- RF-10: SI la colección existente no está vacía y difiere en métrica, modelo o dimensión, o no tiene huella, ENTONCES EL SISTEMA rechazará la indexación pidiendo regenerar la colección.
- RF-11: DONDE se pida recrear la colección, EL SISTEMA la borrará antes de indexar; sin esa opción, el upsert conserva los registros que ya no estén en la entrada.
- RF-12: CUANDO se descargue el índice preconstruido, EL SISTEMA bajará el ZIP de `INDEX_URL`, comprobará su SHA-256 contra `INDEX_SHA256` y lo extraerá en `CHROMA_DIR`, rechazando rutas que salgan del destino; SI `CHROMA_DIR` existe y no se pasa `--force`, ENTONCES no lo sobrescribirá.

### C. Recuperación
- RF-13: CUANDO se recupere contexto para una consulta, EL SISTEMA devolverá como máximo `top_k` chunks con los campos indexados (`chunk_id`, `document_id`, `text`, `source`, `chunk_index`, `category`, `corpus_group` y `page` si existe) más `score = max(0, min(1, 1 − distancia coseno))`, ordenados de mayor a menor score.
- RF-14: DONDE se indique un filtro de metadata (`where`), EL SISTEMA lo aplicará en la consulta a Chroma.
- RF-15: SI la consulta está vacía, `top_k` no es un entero positivo o Chroma devuelve listas de distinta longitud, ENTONCES EL SISTEMA lanzará un error de validación; si la colección está vacía, no devolverá ningún chunk.

### D. Generación: contrato de `responder()` y `rag_ask()`
- RF-16: EL SISTEMA expondrá `responder(pregunta, top_k=TOP_K, score_minimo=None, collection=None, client=None, where=None) -> dict`, que devolverá siempre exactamente las claves `respuesta` (str), `fuentes` (list[str]), `citas` (list[dict]), `chunks` (list[dict]), `abstuvo` (bool) y `motivo_abstencion` (str | None).
- RF-17: SI la pregunta no es texto o está vacía, ENTONCES `responder()` lanzará `ValueError` antes de recuperar nada.
- RF-18: SI la recuperación no devuelve ningún chunk, ENTONCES `responder()` se abstendrá con `motivo_abstencion = "sin_resultados"` sin llamar al LLM.
- RF-19: SI el score del mejor chunk es menor que el umbral (`score_minimo` o, si es `None`, `SCORE_MINIMO` de `RAG_SCORE_MINIMO`, por defecto `0.0`), ENTONCES `responder()` se abstendrá con `motivo_abstencion = "score_bajo (<score> < <umbral>)"` sin llamar al LLM.
- RF-20: SI el texto del LLM contiene `SIN_EVIDENCIA` (sin distinguir mayúsculas), ENTONCES `responder()` se abstendrá con `motivo_abstencion = "el_modelo_no_vio_evidencia"`.
- RF-21: MIENTRAS `abstuvo` sea `True`, `responder()` devolverá `respuesta = MENSAJE_ABSTENCION`, `fuentes = []` y `citas = []`, y conservará los `chunks` recuperados para depurar.
- RF-22: CUANDO no se abstenga, `responder()` devolverá en `respuesta` el texto del LLM con marcas `[n]`, y en `fuentes` los `source` sin repetir y en el orden de recuperación.
- RF-23: CUANDO no se abstenga, `responder()` devolverá una cita por chunk recuperado con `n` (1…k, la misma numeración del prompt), `source`, `page`, `chunk_id`, `score`, `titulo`, `organismo`, `oficial`, `etiqueta` (`"fuente oficial"` o `"fuente no oficial"`) y `texto` (`"titulo · organismo"`, más `", página p"` si hay página); una fuente que no está en el catálogo recibe un título derivado del nombre del archivo y `oficial = False`.
- RF-24: EL SISTEMA construirá el prompt con instrucciones fijas (usar solo el contexto, responder en el idioma de la pregunta, en 1-4 frases, citar con `[n]` y devolver `SIN_EVIDENCIA` si el contexto no contiene la respuesta), los fragmentos numerados con fuente, página y categoría, y la pregunta.
- RF-25: SI el LLM devuelve un texto vacío, ENTONCES `responder()` lanzará `ValueError`; los errores del LLM, de los embeddings o de Chroma se propagan fuera de `responder()` sin capturarse.
- RF-26: CUANDO se llame a `rag_ask(consulta, **kwargs)`, EL SISTEMA devolverá solo `responder(consulta, **kwargs)["respuesta"]`, incluido el mensaje de abstención.

### E. Contexto de visita y logging
- RF-27: CUANDO se consulte el estado del parque, EL SISTEMA devolverá `abierto`, `hora_apertura`, `hora_cierre`, `temporada` y `horario`, con apertura a las `HORA_APERTURA` (6 h) y cierre a las 24 h de abril a septiembre y a las 22 h de octubre a marzo, usando la hora de `Europe/Madrid` cuando no se indica el momento.
- RF-28: CUANDO se pida la observación meteorológica con `AEMET_API_KEY` definida, EL SISTEMA consultará la estación 3195 de AEMET en dos pasos con un timeout de `TIEMPO_MAXIMO` segundos y devolverá `estacion`, `hora_utc`, `temperatura_c`, `humedad_pct`, `precipitacion_mm`, `viento_kmh`, `racha_kmh` (m/s × 3,6) y `fuente`.
- RF-29: SI no hay clave de AEMET o falla la red, el HTTP, el JSON o la forma de la respuesta, ENTONCES EL SISTEMA no devolverá observación (`None`) y no lanzará excepciones.
- RF-30: CUANDO se evalúe la racha de viento, EL SISTEMA devolverá el nivel `rojo` desde `VIENTO_ROJA_KMH` (60), `naranja` desde `VIENTO_NARANJA_KMH` (45), `verde` por debajo y `desconocido` sin dato, con mensaje solo en naranja y rojo.
- RF-31: CUANDO se genere el saludo contextual, EL SISTEMA devolverá siempre `saludo`, `estado`, `observacion`, `viento`, `peculiaridades` y `fuente`; las peculiaridades indican si el parque está cerrado, si cierra en una hora o menos o la hora de cierre, el aviso de viento seguido de `AVISO_NO_OFICIAL` y si llueve (precipitación > 0).
- RF-32: CUANDO `responder()` termine sin excepción, EL SISTEMA registrará la consulta como una línea JSONL en `LOG_FILE` (`timestamp`, `pregunta`, `top_k`, `n_chunks`, `tiempo_s`, `modelo`, `abstuvo`, `motivo_abstencion`, `score_top1`, `fuentes`) y una línea por consola; SI no puede escribir el fichero, ENTONCES avisará y seguirá.

### F. Interfaces
- RF-33: CUANDO se ejecute `python main.py --query`, EL SISTEMA mostrará solo los chunks recuperados con su score y su procedencia (o JSON con `--json`), y SI no hay resultados, ENTONCES avisará de que hay que indexar y saldrá con código 1.
- RF-34: CUANDO se ejecute `python main.py --ask`, EL SISTEMA mostrará la respuesta y sus fuentes o el motivo de abstención, los fragmentos usados con `--contexto` y la salida de `responder()` en JSON con `--json`, pasando `--top-k`, `--category` y `--score-minimo`.
- RF-35: CUANDO se ejecute `python main.py --index`, EL SISTEMA hará upsert sobre la colección existente; con `--recreate-index` la reconstruirá y con `--dry-run` solo cargará y fragmentará, sin llamar a Gemini ni a Chroma.
- RF-36: CUANDO se ejecute `python -m scripts.index_corpus`, EL SISTEMA reconstruirá la colección por defecto, y con `--keep-existing` hará upsert sobre la existente.
- RF-37: CUANDO se ejecute `python main.py --saludo`, EL SISTEMA imprimirá el saludo contextual en texto plano, con la frase "(Sin datos meteorológicos ahora mismo.)" si no hay observación.
- RF-38: SI una orden de la CLI falla, ENTONCES EL SISTEMA mostrará un mensaje sin traza, sugerirá `--index` si la colección no existe y saldrá con código 1; `--top-k` ≤ 0 se rechaza como error de argumentos.
- RF-39: CUANDO el usuario pregunte en Streamlit, EL SISTEMA llamará a `responder()` con `TOP_K`, mostrará la respuesta (o un aviso si se abstiene), cada cita con `⚠` si la fuente no es oficial, los chunks en un desplegable y una tabla de métricas de la sesión, bajo un banner con el saludo contextual.

## Trazabilidad

| RF | Implementación (archivo · función) | Test |
|---|---|---|
| RF-1 | `src/load.py` · `load_documents`, `_leer_markdown`, `_leer_pdf`, `_leer_csv` (exclusiones en `CARPETAS_EXCLUIDAS`) | Indirecto: `test_retrieve.py::test_cada_pregunta_devuelve_resultados_validos` (marcador `corpus`) |
| RF-2 | `src/load.py` · `_validar_categoria`, `_leer_*`, `load_documents` (manifiesto en `MANIFIESTO`) | sin test |
| RF-3 | `src/chunk.py` · `chunk_documents` | `test_chunk.py::test_generates_non_empty_traceable_chunks`, `test_chunk_ids_are_consecutive_across_pdf_pages`, `test_preserves_pdf_page_and_omits_page_for_markdown`, `test_same_input_and_configuration_produce_same_chunks` |
| RF-4 | `src/chunk.py` · `_validate_chunk_config`, `_validate_document` | `test_chunk.py::test_rejects_*` |
| RF-5 | `src/chunk.py` · `_detect_repeated_lines`, `_remove_lines` (parámetro `quitar_repetidos`) | `test_chunk.py::test_optional_repeated_line_removal` |
| RF-6 | `src/embed.py` · `embed_chunks`, `_embeddear_lote` | `test_embed.py::test_embed_chunks_adds_one_vector_per_chunk`, `test_embed_chunks_preserves_input_order`, `test_embed_chunks_uses_configured_batch_size`, `test_embed_chunks_uses_document_task_type` |
| RF-7 | `src/embed.py` · `_embeddear_lote_con_reintentos`, `_es_error_de_cuota` | `test_embed.py::test_retry_batch_*`, `test_rate_limit_error_detection_*` |
| RF-8 | `src/embedding_cache.py` · `EmbeddingCheckpoint`; `src/embed.py` · `embed_chunks` | `test_embedding_cache.py` (10 tests), `test_embed.py::test_embed_chunks_reuses_all_cached_vectors`, `test_embed_chunks_keeps_completed_batches_after_failure` |
| RF-9 | `src/index.py` · `index_chunks`, `obtener_coleccion` | `test_index.py::test_index_chunks_uses_configured_batches`, `test_obtener_coleccion_creates_collection_with_configuration`, `test_index_chunks_is_idempotent` |
| RF-10 | `src/index.py` · `_validar_configuracion_coleccion` | `test_index.py::test_validar_configuracion_rejects_different_dimension`, `test_validar_configuracion_rejects_different_model` |
| RF-11 | `src/index.py` · `index_chunks` (`recreate`), `borrar_coleccion` | `test_index.py::test_index_chunks_recreates_collection_when_requested` |
| RF-12 | `scripts/download_index.py` · `instalar_indice`, `_extraer_seguro`, `calcular_sha256` | `test_download_index.py` (SHA-256 y extracción); la negativa a sobrescribir y `--force`: sin test |
| RF-13 | `src/retrieve.py` · `retrieve`, `distancia_a_score` | `test_retrieve.py::test_score_convierte_distancia_coseno`, `test_resultado_respeta_el_contrato_3`, `test_resultados_ordenados_por_score_descendente`, `test_top_k_se_pasa_a_chroma` |
| RF-14 | `src/retrieve.py` · `retrieve` | `test_retrieve.py::test_filtro_where_opcional`, `test_filtro_por_categoria_de_seguridad` |
| RF-15 | `src/retrieve.py` · `_validar_query`, `_validar_top_k`, `retrieve` | `test_retrieve.py::test_query_invalida`, `test_top_k_invalido`, `test_listas_descuadradas_fallan`, `test_coleccion_vacia_devuelve_lista_vacia` |
| RF-16 | `src/generate.py` · `responder` | `test_generate.py::test_la_salida_tiene_siempre_los_mismos_campos` |
| RF-17 | `src/generate.py` · `responder` | `test_generate.py::test_responder_rechaza_pregunta_vacia` |
| RF-18 | `src/generate.py` · `_responder_con_chunks` | `test_generate.py::test_coleccion_vacia_se_abstiene` |
| RF-19 | `src/generate.py` · `responder`, `_responder_con_chunks` | `test_generate.py::test_score_bajo_se_abstiene_sin_llamar_al_modelo`, `test_el_umbral_es_ajustable` |
| RF-20 | `src/generate.py` · `_responder_con_chunks` (`CENTINELA_SIN_EVIDENCIA`) | `test_generate.py::test_centinela_del_modelo_se_convierte_en_abstencion`, `test_centinela_se_detecta_aunque_venga_con_texto_alrededor` |
| RF-21 | `src/generate.py` · `_abstencion` | `test_generate.py::test_la_abstencion_conserva_los_chunks_para_poder_depurar`, `test_la_abstencion_no_lleva_citas` |
| RF-22 | `src/generate.py` · `_responder_con_chunks`, `_fuentes_de` | `test_generate.py::test_score_alto_genera_respuesta`, `test_las_fuentes_no_se_repiten_y_conservan_el_orden` |
| RF-23 | `src/generate.py` · `_citas_de`; `src/fuentes.py` · `describir`, `describir_citas`, `CATALOGO` | `test_generate.py::test_las_citas_siguen_la_numeracion_del_prompt`, `test_cada_cita_lleva_documento_pagina_y_chunk`, `test_las_citas_llevan_el_nombre_legible_de_la_fuente`; `test_fuentes.py` (6 tests) |
| RF-24 | `src/generate.py` · `build_prompt`, `_formatear_chunk`, `INSTRUCCIONES` | `test_generate.py::test_prompt_*`, `test_el_prompt_pide_responder_en_el_idioma_de_la_pregunta`, `test_top_k_llega_hasta_el_prompt` |
| RF-25 | `src/generate.py` · `generate_answer`, `responder` | `test_generate.py::test_generate_answer_falla_si_el_modelo_devuelve_vacio`; la propagación de errores del LLM o de Chroma: sin test |
| RF-26 | `src/generate.py` · `rag_ask` | `test_generate.py::test_rag_ask_devuelve_solo_el_texto`, `test_rag_ask_devuelve_el_mensaje_de_abstencion` |
| RF-27 | `src/contexto_visita.py` · `estado_del_parque`, `hora_de_cierre`, `ahora_en_madrid` | `test_contexto_visita.py::test_horario_de_verano_y_de_invierno`, `test_a_las_23_abierto_en_verano_y_cerrado_en_invierno`, `test_el_horario_usa_la_hora_de_madrid_no_la_del_servidor` |
| RF-28 | `src/contexto_visita.py` · `obtener_observacion`, `_kmh` | `test_contexto_visita.py::test_usa_la_estacion_del_retiro`, `test_convierte_el_viento_de_ms_a_kmh` |
| RF-29 | `src/contexto_visita.py` · `obtener_observacion` | `test_contexto_visita.py::test_sin_api_key_devuelve_none`, `test_un_error_de_red_no_lanza_excepcion`, `test_respuesta_sin_campo_datos_devuelve_none`, `test_una_respuesta_de_error_de_aemet_no_rompe_la_app` |
| RF-30 | `src/contexto_visita.py` · `nivel_de_viento` | `test_contexto_visita.py::test_nivel_segun_los_umbrales_del_protocolo`, `test_sin_viento_fuerte_no_hay_mensaje` |
| RF-31 | `src/contexto_visita.py` · `saludo_contextual` | `test_contexto_visita.py::test_saludo_segun_la_hora`, `test_el_parque_cerrado_se_avisa`, `test_el_viento_fuerte_aparece_como_peculiaridad_con_su_aviso`, `test_la_lluvia_aparece_como_peculiaridad`, `test_el_saludo_sigue_saliendo_si_aemet_falla` |
| RF-32 | `src/logging_utils.py` · `log_query`; `src/generate.py` · `responder` | `test_logging_utils.py::test_escribe_una_linea_por_consulta`, `test_un_fallo_de_escritura_no_rompe_la_consulta`; `test_generate.py::test_responder_registra_la_consulta` |
| RF-33 | `main.py` · `cmd_query` | `test_main.py::test_query_*` |
| RF-34 | `main.py` · `cmd_ask` | `test_main.py::test_ask_*` |
| RF-35 | `main.py` · `cmd_index`; `src/pipeline.py` · `build_index`, `prepare_corpus`, `summarize_corpus` | `test_main.py::test_index_no_recrea_la_coleccion_por_defecto`, `test_recreate_index_solo_cuando_se_pide`, `test_index_con_dry_run_no_indexa`; `test_pipeline.py::test_build_index_dry_run_skips_external_services` |
| RF-36 | `scripts/index_corpus.py` · `main` | sin test (solo `print_report` en `test_pipeline.py`) |
| RF-37 | `main.py` · `main`; `src/contexto_visita.py` · `texto_de_bienvenida`, `saludo_contextual` | `test_contexto_visita.py::test_texto_de_bienvenida_*`; la ruta `--saludo` de la CLI: sin test |
| RF-38 | `main.py` · `main` | `test_main.py::test_un_error_no_muestra_traza`, `test_coleccion_inexistente_explica_como_indexar`, `test_top_k_invalido_es_error` |
| RF-39 | `app.py` · `main`, `_procesar_pregunta`, `_renderizar_respuesta`, `_renderizar_banner_clima` | sin test |

## Requisitos no funcionales
- Idioma: mensajes e instrucciones en español; el LLM responde en el idioma de la pregunta (RF-24).
- Separación de fuentes: los datos de AEMET y del horario nunca entran en el prompt ni en las citas.
- Coste: `--index --dry-run`, `--saludo`, la descarga del índice y `pytest` no llaman a Gemini.
- Red: cada petición a AEMET tiene un timeout de 8 s (`TIEMPO_MAXIMO`).

## Casos límite
- Pregunta vacía → `ValueError` (RF-17); en la CLI, mensaje sin traza (RF-38).
- Colección inexistente → error de Chroma propagado (RF-25) y la CLI sugiere `--index` (RF-38).
- Colección vacía → ningún chunk (RF-15) y abstención `sin_resultados` (RF-18).
- Página de PDF sin texto → se omite; un PDF sin ninguna página con texto → error de validación (RF-1, RF-2).
- AEMET sin clave, caído o con cuota agotada → sin observación y saludo sin datos meteorológicos (RF-29, RF-31, RF-37).
- 23:00 en julio: el parque está abierto; en enero, cerrado (RF-27).

## Fuera de alcance
- Todo lo del agente del PB2: supervisor, especialistas, HITL, tools y grafo.
- Los scripts de `scripts/validation/`, `scripts/experiments/`, `scripts/etl/` y `scripts/corpus/`, que son herramientas de evaluación y preparación, no comportamiento del producto.

## Criterios de finalización
Línea base aceptada cuando el equipo aprueba esta spec y `pytest` sigue en verde (341 tests a 2026-10-13).

## Huecos detectados
Prioridad: **Bloquea al agente** (hay que resolverlo antes o durante la integración), **Calibración** (necesita datos reales y API) o **Mejora** (deuda sin urgencia).

1. **[Bloquea al agente] AEMET sin fallback local de datos.** Si la consulta falla, no hay observación (RF-29): no hay caché, ni última observación guardada, ni reintento. Solo el horario y el estado del parque se calculan en local (RF-27), así que el saludo se degrada pero no se cae. No cumple el P7 de la constitución ("una API externa siempre tiene fallback local").
2. **[Bloquea al agente] `responder()` propaga las excepciones y no registra.** Los fallos del LLM, de los embeddings o de Chroma salen de `responder()` (RF-25) y la consulta **no se registra** (RF-32 solo se cumple si no hay excepción). Choca con P7 (tools `ok`/`error`/`blocked` sin excepciones) y P8 (trazabilidad) en cuanto el agente lo use como tool.
   - La tool RAG de los agentes debe usar `responder()`, no `rag_ask()`, para conservar fuentes y citas.
3. **[Bloquea al agente] `hora_utc` sin convertir a hora de Madrid.** La observación guarda la hora de AEMET en UTC y el texto de bienvenida la muestra como "medidos a las …" sin convertirla, mientras que el horario del parque sí usa `Europe/Madrid`.
4. **[Bloquea al agente] El centinela anula las respuestas parciales.** Cualquier aparición de `SIN_EVIDENCIA` convierte toda la salida en abstención (RF-20), aunque el prompt permite contestar la parte que sí está en el contexto.
5. **[Calibración] Umbral de abstención sin calibrar.** `SCORE_MINIMO` vale `0.0` por defecto y el score está acotado a [0, 1], así que la compuerta de score (RF-19) **nunca se dispara** sin `RAG_SCORE_MINIMO`. Hoy la abstención depende solo de `sin_resultados` y del centinela del LLM. `scripts/validation/calibrar_umbral.py` existe, pero necesita la API.
6. **[Mejora] `--index` frente a `scripts.index_corpus`.** `python main.py --index` hace upsert (RF-35), mientras que `scripts.index_corpus` y `build_index()` reconstruyen por defecto (RF-36). El upsert no borra los chunks que ya no existen (RF-11), así que, tras cambiar el corpus o el chunking, `--index` deja chunks obsoletos. El comportamiento por defecto de `index_corpus` no tiene test.
7. **[Mejora] Constantes configurables fuera de `config.py`.**
   - `contexto_visita._saludo_por_hora`: las franjas 6/13/21 h.
   - `saludo_contextual`: el umbral de "cierra dentro de poco" (`faltan <= 1`).
   - `chunk._detect_repeated_lines`: `min_pages=3` y `min_ratio=0.6`, más `_MAX_REPEATED_LINE_LENGTH=120`.
   - `main.py`: `ANCHO=78` y el corte de 300 caracteres de `_fragmento`.
   - Los truncados de traza `[:60]` y `[:70]` de `retrieve` y `log_query`.
   - `AEMET_API_KEY` se lee con `os.getenv` dentro de `contexto_visita`.
   - Al revés: `MAX_CHUNKS` está en `config.py` pero **nadie lo aplica**, aunque el comentario dice que el orquestador debe hacerlo.
   - `CARPETAS_EXCLUIDAS` e `INSTRUCCIONES` se consideran internas (decisión provisional).
8. **[Mejora] El docstring de `responder()` no menciona `citas`**, aunque forma parte de la salida (RF-16).
9. **[Mejora] Streamlit.**
   - Ante un error construye un dict sin `citas` ni `motivo_abstencion` y lo marca como `abstuvo=True`, así que la tabla de métricas mezcla errores con abstenciones.
   - Usa siempre `TOP_K`.
   - `app.py` no tiene ningún test.
   - Un comentario de `app.py` nombra a una persona (línea 24), cosa que la regla de comentarios de `AGENTS.md` prohíbe.
10. **[Mejora] La inyección en `retrieve()` es incompleta.** Acepta `collection`, pero llama siempre a `embed_query()` sin cliente inyectable: los tests tienen que usar monkeypatch.
11. **[Mejora] Las trazas usan `print`.** `retrieve`, `embed` e `index` escriben con `print`, no con el logger de `logging_utils`.
12. **[Mejora] Faltan tests directos** de `src/load.py` (RF-1, RF-2), de la negativa a sobrescribir de `download_index` (RF-12), de la ruta `--saludo` de la CLI (RF-37) y de `index_corpus` (RF-36).

## Dudas abiertas
- [NECESITA ACLARACIÓN: ¿qué valor de `RAG_SCORE_MINIMO` se adopta, y se calibra antes o después de integrar el agente?]
- [NECESITA ACLARACIÓN: ¿qué fallback local se espera para AEMET (última observación en caché, mensaje fijo…) para cumplir P7?]
- [NECESITA ACLARACIÓN: ¿se unifica el comportamiento por defecto de `--index` y `scripts.index_corpus`?]

# Spec 001


# Spec 002


# Spec 003 — Núcleo del agente multiagente

## 1. Objetivo

Implementar el núcleo de un agente multiagente para el Parque del Retiro mediante LangGraph. El sistema debe recibir peticiones del usuario, decidir qué especialista debe intervenir, reunir los resultados y preparar un plan que requiera aprobación humana antes de aplicarse.

## 2. Contexto

El proyecto reutiliza el RAG existente del Parque del Retiro. El agente no debe reconstruirlo, sino invocarlo a través de las herramientas que proporcionará el módulo de tools.

Se definen dos especialistas:

- **Especialista de conocimiento del Retiro:** responde sobre lugares, historia, instalaciones, servicios y normas a partir del RAG.
- **Especialista de planificación de visita:** ayuda a organizar una visita utilizando herramientas de contexto, tiempo, meteorología o fuentes externas que estén disponibles.

Ambos especialistas deben tener instrucciones diferenciadas y utilizar únicamente las herramientas autorizadas para su función.

## 3. Alcance

Este bloque incluye:

- Definición del estado compartido del grafo.
- Creación y conexión de los nodos de LangGraph.
- Orquestación mediante un supervisor.
- Integración de los dos especialistas.
- Síntesis de resultados y preparación de un plan.
- Persistencia de la conversación mediante `MemorySaver` y `thread_id`.
- Interrupción antes de aplicar el plan para solicitar aprobación humana.
- Control de límites de ejecución y condición de finalización desde Python.
- Exposición de una interfaz de programación reutilizable por la CLI y Streamlit.

Quedan fuera de este bloque la implementación interna de las herramientas y la interfaz visual de Streamlit.

## 4. Archivos afectados

- `src/state.py`: definición del estado compartido.
- `src/graph.py`: construcción y compilación del grafo.
- `src/agent.py`: funciones públicas para procesar turnos, gestionar decisiones humanas y ejecutar la demo.
- `requirements.txt`: incorporación de `langgraph`, si todavía no está declarado.

## 5. Requisitos funcionales

### RF-01. Estado compartido

El sistema debe disponer de un estado tipado y compartido entre los nodos que permita conservar, como mínimo:

- Mensaje o petición actual.
- Historial relevante de la conversación.
- Especialistas ejecutados y resultados obtenidos.
- Notas necesarias para sintetizar la respuesta.
- Respuesta final propuesta.
- Plan pendiente de aprobación.
- Decisión humana, cuando exista.
- Número de pasos o iteraciones ejecutados.
- Indicador de finalización `done`.
- Información de trazabilidad suficiente para mostrar el recorrido del agente.

Los campos concretos y sus tipos se definirán en la implementación, manteniendo un contrato estable para los consumidores del agente.

### RF-02. Supervisor

El supervisor debe seleccionar el siguiente paso según la petición y los resultados disponibles.

Puede dirigir el flujo hacia el especialista de conocimiento, el de planificación o la síntesis. Debe permitir que intervengan ambos especialistas cuando la petición lo requiera.

Si falla la decisión del LLM o su respuesta no es válida, debe existir una alternativa determinista implementada en Python.

El supervisor no podrá ignorar los límites de ejecución ni decidir por sí solo que una acción pendiente de aprobación ya está autorizada.

### RF-03. Especialistas

Cada especialista debe tener un propósito y unas instrucciones propias.

El especialista de conocimiento utilizará el RAG a través de la interfaz de herramientas acordada con el equipo.

El especialista de planificación utilizará las herramientas de contexto disponibles y no inventará resultados que dependan de ellas.

Si una herramienta falla o no devuelve evidencia suficiente, el sistema debe reflejar esa limitación en sus resultados.

### RF-04. Síntesis

El nodo de síntesis debe reunir los resultados relevantes de los especialistas y producir:

- Una respuesta comprensible para el usuario.
- Un plan propuesto, cuando corresponda.
- Las limitaciones o datos no disponibles que sean relevantes.
- Una indicación clara de que el plan está pendiente de aprobación humana.

La síntesis no equivale a ejecutar el plan ni a autorizarlo.

### RF-05. Aplicación y aprobación humana

El nodo `aplicar` debe quedar protegido mediante una interrupción de LangGraph antes de su ejecución, por ejemplo con `interrupt_before=["aplicar"]`.

El grafo debe detenerse después de preparar el plan y antes de aplicar los cambios o acciones correspondientes.

Cuando el usuario apruebe el plan, el flujo podrá continuar y Python deberá marcar `done=True` únicamente cuando la aplicación haya concluido correctamente.

Cuando el usuario rechace el plan, no debe marcarse como completado. El agente debe permitir continuar la conversación, modificar la propuesta o generar un nuevo plan.

No se permite la aprobación automática en el flujo interactivo.

### RF-06. Persistencia

El grafo debe compilarse con `MemorySaver` o el mecanismo de memoria exigido por el proyecto.

Cada conversación debe identificarse mediante un `thread_id` estable. Las llamadas posteriores de una misma conversación deberán reutilizarlo para recuperar el estado y continuar la ejecución.

Una conversación nueva debe poder utilizar un identificador distinto.

### RF-07. Límites y finalización

El número máximo de pasos o iteraciones debe estar controlado por Python mediante una constante o configuración explícita.

El agente no podrá ejecutar un bucle indefinido ni delegar exclusivamente en el LLM la decisión de continuar.

Al alcanzar el límite, debe detenerse de forma controlada, informar de que no ha podido completar el flujo y evitar marcar como completado un plan que no haya sido aplicado y confirmado.

### RF-08. Interfaz pública

`src/agent.py` debe exponer, como mínimo, las siguientes operaciones:

- `procesar_turno(...)`: iniciar o continuar un turno de conversación.
- `aprobar_plan(...)`: registrar la decisión humana y continuar el flujo.
- `run_demo(...)`: ejecutar un escenario de demostración reproducible.

Los parámetros y valores de retorno deben documentarse y mantenerse compatibles con los clientes CLI y Streamlit.

La lógica del grafo debe permanecer en `src/graph.py`, no duplicarse en las interfaces.

### RF-09. Trazabilidad y errores

El sistema debe permitir identificar los pasos ejecutados, el especialista utilizado, los errores relevantes y las pausas de aprobación.

Los errores del LLM o de las herramientas deben tratarse de forma controlada siempre que sea posible. No se deben mostrar secretos ni claves de API en los mensajes de error.

## 6. Requisitos no funcionales

- Modularidad: estado, grafo, herramientas e interfaces deben estar separados.
- Reutilización: el agente debe poder invocarse sin depender de Streamlit.
- Mantenibilidad: las constantes y los límites deben ser fáciles de localizar y modificar.
- Seguridad: solo se podrán ejecutar herramientas autorizadas y las acciones pendientes de aprobación no podrán aplicarse anticipadamente.
- Compatibilidad: el grafo debe conservar un contrato común para CLI y Streamlit.

## 7. Criterios de aceptación

- **CA-01:** una petición llega al supervisor y se dirige al especialista apropiado o a la síntesis cuando proceda.
- **CA-02:** una petición compleja puede utilizar ambos especialistas y combinar sus resultados.
- **CA-03:** si el supervisor falla, el fallback de Python permite continuar de forma controlada o detener el flujo con un error claro.
- **CA-04:** la síntesis genera una propuesta y el grafo se interrumpe antes de ejecutar `aplicar`.
- **CA-05:** una aprobación permite reanudar el mismo hilo y marcar `done=True` solo después de una aplicación correcta.
- **CA-06:** un rechazo no marca el flujo como completado y permite continuar con nuevas instrucciones.
- **CA-07:** dos turnos del mismo `thread_id` conservan el contexto esperado.
- **CA-08:** el límite de iteraciones se respeta incluso si el LLM solicita continuar indefinidamente.
- **CA-09:** el agente puede ser invocado desde un cliente distinto de Streamlit.
- **CA-10:** las pruebas verifican el comportamiento de aprobación, rechazo, fallback, límites y errores relevantes.

## 8. Pruebas previstas

- Pruebas unitarias del estado y de las decisiones de enrutamiento.
- Pruebas con respuestas simuladas del LLM para comprobar el fallback.
- Pruebas del flujo de interrupción, aprobación y rechazo.
- Pruebas de persistencia con un mismo `thread_id`.
- Pruebas de límites de ejecución.
- Pruebas de integración con las interfaces reales de las herramientas cuando estén disponibles.

Las pruebas deben poder ejecutarse sin depender innecesariamente de llamadas reales y costosas a modelos externos.

## 9. Dependencias y decisiones pendientes

- Confirmar los nombres y contratos definitivos de las herramientas con el responsable del módulo tools.
- Confirmar el modelo y mecanismo de invocación del LLM.
- Definir la estructura exacta de los resultados de cada especialista.
- Confirmar la política de reanudación tras un rechazo.
- Confirmar la versión de LangGraph compatible con el entorno del proyecto.

## 10. Definición de terminado

La especificación se considera implementada cuando existen los módulos definidos, el grafo compila, las pruebas de aceptación pasan y la interfaz pública puede utilizarse desde la CLI y desde Streamlit sin duplicar la lógica de orquestación.
