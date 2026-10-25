# AGENTS.md — Retiro Agents

## Proyecto
Este repositorio parte del RAG del Retiro (importado de `retiro_rag`, commit `724c832`) y sobre él se construye el agente multiagente con LangGraph del Project Break 2: supervisor, especialistas, HITL, tools con allowlist, CLI y Streamlit. El enunciado oficial del PB2 manda sobre cualquier spec.

Base actual: asistente RAG en español sobre el Parque de El Retiro (Madrid): historia, monumentos y jardines, flora y fauna, arte y cultura, actividades, itinerarios, información práctica y seguridad. El corpus curado está en `data/processed/` (PDF, Markdown y CSV de fuentes municipales, académicas y propias). Pipeline offline: `load` → `chunk` → `embed` (Gemini `gemini-embedding-001`) → `index` (ChromaDB, coseno); pipeline online: pregunta → `embed_query` → `retrieve` → `build_prompt` → LLM Gemini → `responder()` con fuentes o abstención. Interfaces: CLI (`main.py`) y Streamlit (`app.py`).

## Mapa del código
| Archivo | Responsabilidad |
|---|---|
| `config.py` | Constantes centralizadas: rutas, modelos, chunking, lotes y reintentos de embeddings, `TOP_K`, umbral de abstención, AEMET/horario del parque e índice preconstruido |
| `main.py` | CLI: `--index` (`--recreate-index`, `--dry-run`), `--query` (solo retrieval), `--ask` (RAG completo; `--top-k`, `--category`, `--score-minimo`, `--contexto`, `--json`) y `--saludo` |
| `app.py` | App Streamlit: banner del tiempo, chat, contexto recuperado y tabla de métricas |
| `app_agent.py` | App Streamlit del agente: chat con imagen opcional, Aprobar/Rechazar con comentario en la sidebar, expander de depuración y nueva conversación; solo llama a `procesar_turno` y `aprobar_plan` |
| `src/load.py` | Carga PDF, Markdown y CSV desde `DATA_DIR` y asigna `category`/`corpus_group` según el manifiesto del contrato |
| `src/chunk.py` | Fragmentación en chunks trazables, con limpieza de líneas repetidas y validación de configuración |
| `src/embed.py` | Embeddings Gemini por lotes con reintentos ante 429, `embed_query` y `limitar_chunks` |
| `src/embedding_cache.py` | Checkpoint persistente (`EmbeddingCheckpoint`) para reanudar embeddings interrumpidos |
| `src/index.py` | Cliente y colección ChromaDB, validación de chunks y upsert por lotes |
| `src/pipeline.py` | Orquestación offline: `prepare_corpus`, `summarize_corpus`, `build_index` |
| `src/retrieve.py` | Retrieval con `top_k`, filtros de metadata y conversión distancia → score |
| `src/generate.py` | Prompt anclado al contexto, llamada al LLM, citas y abstención; funciones principales `responder()` y `rag_ask()` |
| `src/gemini_auth.py` | Carga de la API key y cliente Gemini compartido |
| `src/fuentes.py` | Nombres legibles y organismo de cada fuente para las citas |
| `src/contexto_visita.py` | Saludo contextual: hora de Madrid, horario del parque y viento AEMET frente a los umbrales del protocolo |
| `src/logging_utils.py` | Registro JSONL de consultas, cronómetro y resumen de métricas |
| `src/ui_agente.py` | Lógica pura de la app del agente, sin Streamlit ni grafo: sesión, validación de imagen, envío de turnos y decisiones, ocultación de secretos y datos de depuración |
| `scripts/index_corpus.py` | CLI alternativa de indexación (`--dry-run`, `--keep-existing`, `--json`) |
| `scripts/download_index.py` | Descarga e instala el índice Chroma preconstruido (verifica SHA-256) |
| `scripts/validation/` | Validación de corpus, contrato PDF, modelos Gemini, smoke test de embeddings, evaluación de preguntas y calibración del umbral |
| `scripts/experiments/`, `scripts/etl/`, `scripts/corpus/` | Comparación de chunking, filtrado del inventario de arbolado y generación de PDF del corpus |
| `tests/` | Tests con pytest y dobles de prueba (sin API); el marcador `corpus` indexa el corpus real en una Chroma temporal con embeddings deterministas |

## Comandos
- Instalar: `pip install -r requirements.txt` (desarrollo: `pip install -r requirements-dev.txt`)
- Tests: `pytest` (no necesita API key); sin los tests lentos del corpus: `pytest -m "not corpus"`
- Descargar índice preconstruido: `python -m scripts.download_index` (no gasta API; `--force` borra `CHROMA_DIR`)
- Validar carga y chunking sin API: `python main.py --index --dry-run`
- Preparar e indexar: `python main.py --index` (`--recreate-index` para reconstruir) o `python -m scripts.index_corpus` (reconstruye la colección por defecto; `--keep-existing` la conserva) ⚠️ gasta API
- Solo retrieval: `python main.py --query "..."` ⚠️ gasta API (embedding de la consulta)
- Preguntar: `python main.py --ask "..."` ⚠️ gasta API
- Saludo con el tiempo del Retiro: `python main.py --saludo` (consulta AEMET con `AEMET_API_KEY`, no usa Gemini)
- Web: `streamlit run app.py` ⚠️ gasta API
- Web del agente: `streamlit run app_agent.py` ⚠️ gasta API

## Flujo SDD de este repositorio
- Constitución: `docs/constitution.md`. Léela siempre.
- Specs: `specs/NNN-nombre/` con `spec.md`, `plan.md`, `tasks.md` y `validacion.md`. La spec activa es la de número más alto, salvo que se indique otra.
- Plantillas: `docs/plantillas/`. Chuleta de EARS: `docs/chuleta_ears.md`. Cómo testear sin API: `docs/tests_sin_api.md`.
- Comandos por fase: `.claude/commands/` (`/sdd-contexto`, `/sdd-constitucion`, `/sdd-spec`, `/sdd-clarificar`, `/sdd-plan`, `/sdd-tareas`, `/sdd-implementar`, `/sdd-validar`, `/sdd-cambio`, `/sdd-spec-inversa`).

## Reglas
- Lee `docs/constitution.md` y la spec activa antes de tocar nada.
- Respeta la fase en la que estamos. En spec, clarificación, plan y tareas NO se escribe código.
- En implementación: una sola tarea de `tasks.md` cada vez, tests primero, y te paras al terminarla.
- No modifiques `specs/` salvo que la fase lo pida.
- No añadas dependencias ni cambies el contrato de la función principal (`responder()` o `rag_ask()` en `src/generate.py`) si la spec no lo dice.
- Las constantes configurables van en `config.py`; no se definen en los módulos.
- Los comentarios del código son breves y neutrales, sin nombres de personas ni referencias a herramientas de IA.
- No ejecutes comandos marcados con ⚠️ salvo que te lo pida: cuestan dinero y tiempo. Para verificar, usa `pytest`.
- Nunca leas ni muestres el contenido de `.env`.

## Al terminar cualquier tarea
- Ejecuta `pytest` y pega el resumen del resultado.
- Indica qué RF de la spec cubre lo que has hecho.
