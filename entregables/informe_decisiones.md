# Informe de decisiones · Agente del Retiro (Project Break 2)

El agente responde preguntas sobre el Parque de El Retiro y propone planes de visita que una persona debe aprobar o rechazar antes de darlos por cerrados.
Está construido con LangGraph sobre el RAG del proyecto anterior. El RAG base está documentado en [informe_pb1_rag.md](informe_pb1_rag.md).
El equipo se repartió el trabajo en tres bloques: Mihaela, el núcleo del agente (`src/graph.py`, `src/agent.py`, `src/state.py`); Guillermo, las tools (`src/tools/`); y Adixon, la interfaz (`app_agent.py`, `src/ui_agente.py`) y el contrato.
Los tres bloques se comunican solo a través del contrato de `docs/contrato.md`: `procesar_turno` y `aprobar_plan` en un sentido, `ejecutar_tool` en el otro.
Todas las cifras de este informe se comprobaron en el repositorio. En cada sección, la evidencia automática (tests) va separada de la manual (prueba real).

## 1. Grafo

**Flujo.** `supervisor → especialistas (normas, entorno) → sintetizar → aplicar`.
- `normas` consulta el RAG con la tool `rag_ask`.
- `entorno` consulta `hora_actual` y `api_dominio`, y `describir_imagen` solo si el turno trae imagen.
- `sintetizar` une las notas y extrae el plan. Si el plan queda vacío, el grafo termina sin pausa (`_ruta_tras_sintesis`).
- El grafo se compila con `MemorySaver` e `interrupt_before=["aplicar"]` (`build_graph` en `src/graph.py`). Así, cada plan se detiene antes de aplicarse y la conversación se recupera por `thread_id`.

**Límites.** Están en `config.py`: `MAX_ITER = 6` pasadas del supervisor y `MAX_STEPS_ESPECIALISTA = 3` por especialista. El supervisor reserva la última pasada para `sintetizar`, de modo que nunca supera el límite.

**Fallback del supervisor.** El supervisor pide la ruta al LLM. Si el LLM falla, responde algo que no es `normas`, `entorno` ni `sintetizar`, o elige un especialista agotado, Python usa `_ruta_fallback`. Esa función elige por palabras clave de la petición y por los especialistas que faltan.

**Decisión: el modelo propone, Python decide.** El LLM sugiere rutas y redacta notas. Python valida cada ruta, aplica los límites, decide si hay plan y es el único que pone `done = True`, en el nodo `aplicar` y solo si `aprobado is True`. La síntesis nunca marca `done`.

**Evidencia automática** (`tests/test_graph.py`, `tests/test_agent.py`):
- `test_max_iter_es_seis` y `test_max_steps_especialista_es_tres`
- `test_fallback_sintetiza_al_alcanzar_max_iter` y `test_supervisor_reserva_la_ultima_pasada_para_sintesis`
- `test_aplicar_marca_done_true_con_plan_aprobado`, `test_aplicar_no_completa_un_plan_rechazado` y `test_aplicar_no_completa_sin_aprobacion_explicita`
- `test_supervisor_respeta_limite_de_iteraciones`

## 2. Tools

**Allowlist.** `TOOL_REGISTRY` en `src/tools/__init__.py` contiene `rag_ask`, `api_dominio`, `hora_actual` y `describir_imagen`. Si se pide un nombre que no está, `ejecutar_tool` devuelve `status = "blocked"` sin ejecutar nada. Además, cada especialista llama solo a sus propias tools, fijadas en el código de su nodo.

**Salida homogénea.** `ejecutar_tool` nunca lanza excepciones. Devuelve siempre `{tool, status, data, error, traza}`, con `status` igual a `ok`, `error` o `blocked`, y un evento de traza ya construido.

**Validación de argumentos** (`args_validation`):
- `args` tiene que ser un diccionario.
- `rag_ask` recibe solo `pregunta`, como texto limpio.
- `api_dominio` y `hora_actual` no reciben argumentos.
- `describir_imagen` exige `mime` PNG o JPEG y bytes no vacíos.

Una decisión discutible: si la imagen no es válida, la tool describe una imagen por defecto (`IMAGE_DEFAULT_PATH`) en lugar de devolver un error. En la práctica no se llega a ese caso, porque el grafo solo llama a la tool si hay imagen y la interfaz valida la imagen antes de enviarla (sección 4).

**AEMET con respaldo** (`src/tools/aemet_api.py`):
- `api_dominio` pide primero las observaciones a AEMET. Si falla, las lee de `src/tools/fallback/aemet.json` (`FALLBACK_JSON`).
- El campo `origen` dice de dónde vienen los datos: `aemet` o `respaldo`.
- Previsiones y avisos solo se consultan si AEMET respondió. Si fallan, o si se usó el respaldo, quedan en `None`, que significa "no disponible".

**Evidencia automática:**
- `tests/test_aemet_api.py`: `test_api_dominio_returns_aemet_data`, `test_api_dominio_uses_fallback_when_observations_fail`, `test_api_dominio_keeps_observations_if_forecast_or_alerts_fail` y `test_api_dominio_reports_fallback_failure`.
- `tests/test_rag_tool.py`, `tests/test_hora_actual.py` y `tests/test_image_decrip.py`: cubren cada tool por separado.

**Hueco conocido.** No hay tests de `ejecutar_tool` ni de `args_validation`. Ni la allowlist, ni el estado `blocked`, ni la captura de excepciones tienen test; solo los respalda el código.

## 3. HITL: aprobar y rechazar

**Cómo funciona.**
1. Cuando la síntesis produce un plan, el grafo se detiene antes de `aplicar` y registra el evento `hitl/pausa` con status `pending`.
2. `aprobar_plan(thread_id, aprobado, comentario)` guarda la decisión y reanuda el mismo hilo.
3. Al aprobar, `aplicar` registra `hitl/aprobar` y pone `done = True`.
4. Al rechazar, registra `hitl/rechazar`, borra el pedido, las notas, la respuesta y el plan, y deja `done = False`. La conversación sigue en el mismo `thread_id`.
5. El comentario queda en `args.comentario` del evento.

**Evidencia manual** (prueba real con Gemini en `streamlit run app_agent.py`):

| | Aprobación | Rechazo |
|---|---|---|
| Captura | [hitl_aprobar.png](evidencias/pb2/hitl_aprobar.png) | [hitl_rechazar.png](evidencias/pb2/hitl_rechazar.png) |
| `thread_id` | `194fa4ea-282b-4c32-be53-47b997ac386e` | el mismo |
| Traza | `hitl/pausa` (`pending`) → `hitl/aprobar` (`ok`) | `hitl/pausa` (`pending`) → `hitl/rechazar` (`ok`) |
| Comentario | "aprobado" | "no me gusta este plan" |
| Estado final | `pendiente_aprobacion = False`, `done = True` | `pendiente_aprobacion = False`, `done = False` |
| Mensaje en el chat | "Plan aprobado" | "Plan rechazado, puedes hacer otra petición" |

El rechazo corresponde a la segunda petición de la misma conversación. Las dos capturas muestran el mismo `thread_id`.

**Por qué la interfaz bloquea el chat con un plan pendiente.** Mientras el grafo está detenido antes de `aplicar`, `procesar_turno` no acepta un turno nuevo en ese hilo y devuelve un error de plan pendiente (`src/agent.py`).
- Si el chat siguiera abierto, el mensaje se perdería y solo aparecería un aviso.
- Bloquearlo hace visible que falta una decisión humana. Es el principio 5 de la constitución: el plan no se cierra sin aprobar o rechazar.
- Los botones Aprobar y Rechazar solo se activan con un plan pendiente.
- La interfaz no decide nada por su cuenta: lee `pendiente_aprobacion` y `done` del resultado del agente.

**Evidencia automática:**
- `tests/test_agent.py`: `test_el_grafo_se_pausa_antes_de_aplicar`, `test_aprobar_plan_marca_done_como_true`, `test_rechazar_plan_limpia_el_pedido` y `test_se_puede_iniciar_otro_pedido_tras_rechazar`.
- `tests/test_app_agent.py`: `test_app_plan_pendiente_bloquea_chat_y_avisa`, `test_app_aprobar_desde_sidebar`, `test_app_rechazar_desde_sidebar` y `test_app_sin_aprobacion_automatica`.

## 4. Multimodal: imagen → `describir_imagen`

**Recorrido.**
1. La persona adjunta una imagen en Streamlit.
2. La interfaz la valida y la envía con `procesar_turno(texto, thread_id, imagen={"bytes", "mime"})`.
3. El especialista `entorno` llama a `describir_imagen` y usa la descripción en su nota.

**Validación en la interfaz** (`validar_imagen` en `src/ui_agente.py`; valores en `config.py`):
- El tipo MIME tiene que estar en `IMAGEN_MIME_PERMITIDOS`: PNG o JPEG.
- Los primeros bytes tienen que coincidir con la firma del formato (`FIRMAS_IMAGEN`). Así se detecta un archivo con la extensión cambiada.
- El tamaño no puede superar `IMAGEN_MAX_BYTES`: 5 MB, y el valor exacto se acepta.
- El selector admite un solo archivo.
- Si la imagen no es válida, se muestra un aviso y el mensaje no se envía.

**La traza nunca lleva bytes.** En `src/graph.py`, `_args_para_traza` cambia los bytes de la imagen por `{"mime", "bytes_len"}`. Se aplica a todos los eventos de tool, tanto en `_ejecutar_tool` como en el nodo `entorno`. La tool sí recibe los bytes originales; solo se resume lo que va a la traza.

**Evidencia manual:**
- [ui_espera.png](evidencias/pb2/ui_espera.png) muestra `Plano_Retiro.png` (2,8 MB) adjunta con su miniatura, mientras se ve "El agente está trabajando...".
- En las dos capturas de la sección 3, la traza muestra `describir_imagen` con status `ok` y una descripción en texto como vista previa.

**Evidencia automática:**
- `tests/test_ui_agente.py`: `test_validar_imagen_acepta_png_y_jpg`, `test_validar_imagen_mime_falseado`, `test_validar_imagen_supera_limite`, `test_validar_imagen_en_limite_exacto` y `test_imagen_se_pasa_en_formato_contrato`.
- `tests/test_app_agent.py`: `test_app_selector_un_solo_archivo_png_jpg`.
- `tests/test_image_decrip.py`: la tool en sí.

**Hueco conocido.** No hay test de `_args_para_traza`. Que no haya bytes en la traza se comprueba en el código y en las capturas.

## 5. Fallos conocidos

### a) Gemini devolvía el contenido como lista de bloques
- **Qué pasó.** El plan salía vacío y no aparecía ningún error.
- **Cómo se detectó.** En la primera prueba real con Gemini en Streamlit no salía ningún plan. Una prueba con una línea de Python mostró que `content` era una lista de bloques y no un texto.
- **Causa.** El código leía `resultado.content` y daba por hecho que era texto, pero el modelo configurado devolvía una lista de bloques.
  - `_generar_nota_especialista` descartaba lo que no era texto y devolvía `None`, así que el especialista se quedaba con los datos sin redactar, sin viñetas de plan.
  - En el supervisor, `.content.strip()` lanzaba una excepción, que se capturaba, y se pasaba al fallback.
  - Como todo se capturaba, no aparecía ningún error.
- **Arreglo.** Commit `c00f7fd` ("fix: handle Gemini text blocks in graph"): lee primero `.text`, recurre a `.content` si hace falta y, si sigue sin haber texto, usa el fallback. Entró en `develop` con los PR #10 y #11; el commit está en los dos.
- **Tests.** `test_generar_nota_especialista_acepta_bloques_de_texto` y `test_seleccionar_ruta_acepta_bloques_de_texto` en `tests/test_graph.py`. Observación: `test_seleccionar_ruta_acepta_bloques_de_texto` está definido dos veces en ese archivo (líneas 14 y 206). Python se queda con el segundo y el primero nunca se ejecuta.
- **Estado.** Arreglado.

### b) Las tools fallaban al integrarse
- **Qué pasó.** Al conectar las tools con el registro común, las llamadas fallaban. Que fallaran todas lo indica el equipo; el repositorio muestra la causa, pero no el alcance.
- **Cómo se detectó.** En la revisión del PR #8: el commit `ca18847` se llama "fix: comments on PR". Después se añadieron tests de cada tool en `4f14836`.
- **Causas y arreglos**, todos en el PR #8:
  - Firma: el registro llamaba a `TOOL_REGISTRY[nombre](**clean)`, pero las tools no aceptaban esos argumentos. `ca18847` pasa el diccionario entero, y `2db23a4` hace que `api_dominio` y `hora_actual` acepten `args`.
  - `URL_AEMET`: la rama de tools la redefinía como URL base, y `src/contexto_visita.py` la usa para el saludo. `ca18847` crea `BASE_URL_AEMET` y deja `URL_AEMET` como estaba.
  - Ruta del respaldo: `PROYECT_DIR = Path('..').resolve()` dependía de la carpeta desde la que se ejecutara el programa. `5d648c1` la cambia por `Path(__file__).resolve().parent`.
- **Tests.** En el merge del PR #8 (`b85f0ed`) pytest recoge 415 tests.
- **Después:**
  - PR #9: `7172c73` hace que `hora_actual` use la zona de Madrid (`ZoneInfo(ZONA_HORARIA)`), `3f3b2e4` la ajusta al contrato y `bfb6f8f` corrige las claves de la imagen.
  - PR #14: `03e071f` adapta `tests/test_hora_actual.py` a esa zona horaria.
- **Estado.** Arreglado.

### c) `avisos = None` se leía como "no hay avisos"
- **Qué pasó.** Si AEMET no devuelve avisos, `api_dominio` deja `avisos = None`, y el LLM lo interpretaba como que no había avisos activos.
- **Cómo se detectó.** Por observación del equipo. No hay test ni registro en el repositorio que lo reproduzca.
- **Causa.** En esta rama, `PROMPT_ENTORNO` solo dice "Distingue los datos comprobados de la información no disponible". No explica qué significa `None`.
- **Arreglo.** El commit `1017d75` ("fix: clarify planning specialist prompt") añade al prompt: "Si un campo tiene el valor None, considéralo información no disponible. Nunca interpretes None como ausencia de avisos…". Ese commit solo está en `origin/feature/nucleo_agente`, según las referencias locales: no está en `develop` ni en esta rama.
- **Estado.** Conocido, pendiente de merge.
- **Propuesta:**
  1. Integrar `1017d75` mediante un PR a `develop`.
  2. No depender solo del prompt: que el especialista escriba "avisos: no disponible" en su contexto cuando el valor sea `None`.
  3. Añadir un test con un LLM falso que compruebe ese texto.
  4. Si se cambia la salida de `api_dominio`, pasarlo antes por `/sdd-cambio` sobre el contrato.

### Limitación conocida: itinerario repetido en el chat
El itinerario puede aparecer dos veces: el núcleo lo incluye en el texto de `respuesta`, y la interfaz lo pinta otra vez como lista a partir del campo `plan`. No incumple ningún requisito, pero se ve repetido. Está registrado en `specs/005-streamlit-agente/validacion.md`.

## Cómo se trabajó (SDD)
- Toda funcionalidad pasó por spec, plan, tareas, implementación y validación (`docs/constitution.md`, `AGENTS.md`).
- Cada fase se aprobaba antes de pasar a la siguiente.
- Specs del agente: `specs/003-nucleo-agente`, `specs/004-cli-hitl` y `specs/005-streamlit-agente`.
- El contrato entre bloques (`docs/contrato.md`) se fijó antes de programar. Cualquier cambio se hace primero en el contrato.
- En implementación: una tarea cada vez y los tests primero. Ningún test llama a Gemini, a AEMET ni a la red: se usan dobles, un LLM falso y `MemorySaver`.
- Hubo una rama por bloque, con PR a `develop`: núcleo (Mihaela), tools (Guillermo), e interfaz y contrato (Adixon).
- Al cierre de este informe, `pytest` da 484 passed en la rama `docs/readme-informe`.
- La interfaz tiene una validación RF por RF (`specs/005-streamlit-agente/validacion.md`), con veredicto "Sí".
