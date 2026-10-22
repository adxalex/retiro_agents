# Plan técnico — Spec 005

> Basado en `spec.md` (estado: Aprobada). No añade comportamiento que no esté en la spec.

## Archivos afectados
| Archivo | Crear / Modificar | Qué cambia | RF |
|---|---|---|---|
| `config.py` | Modificar | Añade `IMAGEN_MAX_BYTES = 5 * 1024 * 1024` y `IMAGEN_MIME_PERMITIDOS = ("image/png", "image/jpeg")` en una sección "Interfaz Streamlit del agente" | RF-10, RF-14, RF-15 |
| `src/ui_agente.py` | Crear | Lógica pura de la UI, sin Streamlit ni grafo: sesión, validación de imagen, envío de turno y de decisión con las funciones del agente inyectadas, derivación de estado, filas de traza, comentario HITL y ocultación de secretos | RF-1 a RF-3, RF-5 a RF-8, RF-10, RF-12 a RF-17, RF-21 a RF-30, RF-32 a RF-39, RF-41 a RF-45 |
| `app_agent.py` | Crear | Capa de presentación en Streamlit: pinta el chat, el uploader con miniatura, la sidebar (Aprobar, Rechazar, comentario y Nueva conversación) y el expander de depuración. Llama a `src.ui_agente` pasándole `procesar_turno` y `aprobar_plan` | RF-1, RF-4, RF-9, RF-11, RF-17 a RF-20, RF-31, RF-40 |
| `tests/test_ui_agente.py` | Crear | Tests unitarios de `src/ui_agente.py` con dobles del agente | ver trazabilidad |
| `tests/test_app_agent.py` | Crear | Tests de la app con `streamlit.testing.v1.AppTest`, el agente sustituido por dobles y un test estático de capas | ver trazabilidad |
| `AGENTS.md` | Modificar | Mapa del código (`app_agent.py`, `src/ui_agente.py`) y comando `streamlit run app_agent.py` ⚠️ | — (documentación) |

`app.py`, `src/agent.py`, `src/graph.py`, las tools y `docs/contrato.md` no se tocan.

## Contrato
**Funciones públicas del agente: sin cambios.** La UI consume `procesar_turno(texto, thread_id, imagen=None)` y `aprobar_plan(thread_id, aprobado, comentario="")` tal como fija `docs/contrato.md`.

**Nuevo comando:** `streamlit run app_agent.py` ⚠️ gasta API (lo hace el agente real).

Ejemplo de turno con imagen y plan:
```python
procesar_turno(
    "Quiero ir al Palacio de Cristal esta tarde",
    "3f1c…-uuid4",
    imagen={"bytes": b"\x89PNG\r\n\x1a\n…", "mime": "image/png"},
)
# → {"thread_id": "3f1c…", "respuesta": "Esta tarde…", "plan": ["Entrar por Puerta de Alcalá", "…"],
#    "pendiente_aprobacion": True, "done": False,
#    "traza": [{"ts": "…", "origen": "supervisor", "nombre": "entorno", …},
#              {"ts": "…", "origen": "hitl", "nombre": "pausa", "status": "pending", …}],
#    "error": None}
```
Decisión con comentario:
```python
aprobar_plan("3f1c…", True, "Prefiero empezar por el estanque")
# → {…, "pendiente_aprobacion": False, "done": True,
#    "traza": [<eventos del turno>…, {"origen": "hitl", "nombre": "aprobar",
#              "args": {"comentario": "Prefiero empezar por el estanque"}, "status": "ok", …}],
#    "error": None}
```

**Contrato interno de `src/ui_agente.py`.** Opera sobre un `dict` de sesión, que en la app se guarda en `st.session_state["agente"]`:
```text
sesion = {
  "thread_id": str,                 # uuid4
  "mensajes": [ {"rol": "usuario"|"agente"|"sistema"|"aviso", "texto": str, "plan": list[str]} ],
  "ultimo": dict | None,            # último resultado del agente, con secretos ya ocultos
  "uploader_key": int,              # cambia para vaciar el uploader
}
```

## Lógica clave
```text
nueva_sesion(ids_previos=()) -> sesion
    thread_id = str(uuid4()) distinto de ids_previos
    mensajes = [], ultimo = None, uploader_key = 0

validar_imagen(mime, datos) -> (imagen | None, aviso | None)
    si datos es None: (None, None)
    si mime no está en IMAGEN_MIME_PERMITIDOS o la firma no encaja (PNG \x89PNG, JPG \xff\xd8\xff):
        (None, "Formato no admitido: solo PNG o JPG")
    si len(datos) > IMAGEN_MAX_BYTES: (None, "La imagen supera 5 MB")
    si no: ({"bytes": datos, "mime": mime}, None)

enviar_turno(sesion, texto, mime, datos, procesar)      # mime/datos = None si no hay imagen
    si texto.strip() == "": return                          # RF-3
    imagen, aviso = validar_imagen(mime, datos)
    si aviso: añadir aviso; return                         # RF-14, RF-15: no se envía
    añadir {"usuario", texto}
    resultado = llamar_seguro(procesar, texto, sesion.thread_id, imagen)
    registrar(sesion, resultado)
    si resultado.respuesta o resultado.plan: añadir {"agente", respuesta, plan}
    si resultado.error: añadir {"aviso", error}            # incluye "plan pendiente" (RF-30)
    si imagen: sesion.uploader_key += 1                    # RF-13

decidir(sesion, aprobado, comentario, aprobar)
    resultado = llamar_seguro(aprobar, sesion.thread_id, aprobado, comentario.strip())
    registrar(sesion, resultado)
    si resultado.error: añadir {"aviso", error}
    si no, si aprobado y resultado.done: añadir {"sistema", "Plan aprobado"}
    si no, si aprobado: añadir {"aviso", "El plan no se ha completado."}   # RF-27
    si no: añadir {"sistema", "Plan rechazado, puedes hacer otra petición"}

llamar_seguro(f, *args)      # defensa extra: el contrato dice que no lanza
    try f(*args) except Exception -> resultado vacío con error genérico

registrar(sesion, resultado)
    sesion.ultimo = resultado con textos pasados por ocultar_secretos   # RF-8, RF-36 (reemplaza)

pendiente(sesion) = bool(sesion.ultimo and sesion.ultimo.pendiente_aprobacion)   # RF-45
filas_traza(traza) = [{ts, origen, nombre, status, preview} por evento, en orden]
comentario_hitl(traza) = args.comentario del último evento origen=="hitl", si no está vacío; si no, None
ocultar_secretos(texto): sustituye por "***" los valores de GEMINI_API_KEY, GOOGLE_API_KEY y
    AEMET_API_KEY presentes en el entorno y el patrón de clave Google AIza[0-9A-Za-z_-]{35}

app_agent.py (en cada ejecución)
    sesion = st.session_state.setdefault("agente", nueva_sesion())
    sidebar: Nueva conversación (siempre); comentario + Aprobar/Rechazar (disabled = not pendiente)
    pintar mensajes; si pendiente: st.warning("Hay un plan pendiente: …")
    uploader (png/jpg, uno, key=uploader_key) + miniatura st.image
    texto = st.chat_input(disabled=pendiente)
    expander "Depuración" (expanded=False): thread_id, pendiente_aprobacion, done, tabla filas_traza, comentario
    ante una acción: with st.spinner(...): enviar_turno/decidir(...) y después st.rerun()
```

## Decisiones técnicas
| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Separar la lógica de la UI en `src/ui_agente.py`, puro y testeable, y dejar `app_agent.py` solo para pintar | Toda la lógica en `app_agent.py` | La constitución pide tests como puerta y capas separadas. Con funciones puras casi todos los RF se prueban sin Streamlit |
| Inyectar `procesar` y `aprobar` como parámetros de las funciones de `ui_agente` | Que `ui_agente` importe `src.agent` y parchearlo con monkeypatch | Así los tests unitarios no importan el grafo y queda explícito que la UI solo usa esas dos funciones (RF-44) |
| `AppTest` de Streamlit para comprobar widgets (chat desactivado, botones, aviso, expander) | Validarlo solo a mano, como dice `docs/tests_sin_api.md` | La spec exige test para todos los RF. `AppTest` viene con Streamlit 1.65, así que no añade ninguna dependencia |
| Imagen con `st.file_uploader` (`accept_multiple_files=False`, `type=["png","jpg","jpeg"]`) más `st.image` de miniatura | `st.chat_input(accept_file=True)` | El uploader permite mostrar la miniatura antes de enviar (RF-11) y vaciarlo cambiando la `key` (RF-13) |
| Validar el formato por MIME y por firma de bytes, sin abrir la imagen | Abrirla con Pillow | Evita depender de Pillow de forma explícita y detecta una extensión falseada |
| 5 MB = 5 × 1024 × 1024 bytes, y exactamente el límite se acepta | 5 × 10⁶ | Es la convención habitual en los uploaders. La spec dice "supera 5 MB", así que el valor frontera entra |
| Procesar la acción en el cuerpo del script con `st.spinner` y después `st.rerun()` | Callbacks `on_click` / `on_submit` | Dentro de un callback el spinner no se ve bien (RF-4). El rerun repinta la sidebar y la caja de chat con el estado nuevo (RF-17, RF-26) |
| El comentario se lee solo del último evento `hitl` de la traza, sea cual sea su `nombre` | Guardar aparte el comentario enviado | La spec (RF-37 y Dependencias) establece la traza como única fuente. No filtrar por nombre cubre el riesgo descrito abajo |
| Ocultar secretos en la UI aunque el núcleo ya debería evitarlos | Confiar solo en el núcleo | El núcleo incluye `str(exc)` en `error`, y RF-8 exige que no llegue ningún secreto a pantalla |
| Textos de la UI como constantes internas de `ui_agente` | Ponerlos en `config.py` | No son configurables (principio 10). Los configurables, que son el límite y los formatos, sí van en `config.py` |

## Estrategia de tests
Ningún test llama a Gemini, a AEMET ni al grafo real.

Cobertura: 42 RF con test automático y 3 solo manuales (RF-4, RF-9 y RF-11). RF-13 y RF-31 tienen test automático y además una comprobación manual de lo que se ve.

- **`tests/test_ui_agente.py` (unitarios puros):**
  - El agente se sustituye por dos dobles, `procesar_falso` y `aprobar_falso`. Devuelven dicts del contrato configurables por test y registran sus llamadas (argumentos y recuento).
  - Las imágenes son bytes mínimos con firma PNG o JPG (`b"\x89PNG\r\n\x1a\n" + b"0"*n`) y un GIF para el caso negativo.
  - Los secretos se simulan con `monkeypatch.setenv("GEMINI_API_KEY", "AIza" + "x"*35)`.
- **`tests/test_app_agent.py` (`AppTest`):**
  - Antes de `AppTest.from_file("app_agent.py").run()` se hace `monkeypatch.setattr(src.agent, "procesar_turno", …)`, y lo mismo con `aprobar_plan`. `app_agent.py` llama a `agent.procesar_turno` por atributo, de modo que el doble se aplica.
  - Importar `src.agent` construye el grafo con `MemorySaver`, pero no llama al LLM: las importaciones de Gemini en `graph.py` son perezosas.
  - Se interactúa con `at.chat_input[0].set_value(...).run()`, `at.sidebar.button[...]`, `.click().run()`, `at.warning` y `at.expander`.
- **Test estático de capas (RF-44 y RF-16):** analiza con `ast` `app_agent.py` y `src/ui_agente.py` y comprueba que no importan `langgraph`, `langchain*`, `google*`, `src.graph`, `src.tools` ni `src.state`, y que de `src.agent` solo usan `procesar_turno` y `aprobar_plan`.
- **Comprobación manual, que irá en `validacion.md`:** `AppTest` no simula `st.file_uploader` ni deja ver el spinner ni el estado plegado del expander. Con `streamlit run app_agent.py`:
  - **RF-4:** al enviar aparece el indicador de espera.
  - **RF-9:** el uploader no deja seleccionar dos archivos.
  - **RF-11:** se ve la miniatura al adjuntar.
  - **RF-13:** el uploader queda vacío tras enviar.
  - **RF-31:** el expander aparece cerrado al cargar.
  - Además se repite la demo de los criterios de finalización.

## Riesgos
- **Nombre del evento de aprobación:** en la rama actual, `src/graph.py` todavía registra la aprobación con `nombre="aplicar"`. Ya está corregido a `"aprobar"` en la rama de la PR #6 (commit `a6159b7`); falta traerlo a esta rama cuando se mergee en `develop`.
  - *Mitigación:* no se empieza a implementar hasta tener la PR #6 en `develop`. Además, `comentario_hitl` busca el último evento con `origen == "hitl"` sin filtrar por nombre.
- **Texto perdido al rechazar una imagen:** si la imagen no es válida, `st.chat_input` ya ha vaciado el texto escrito.
  - *Mitigación:* la imagen se valida y avisa en cuanto se adjunta, antes de escribir. El aviso al enviar indica que el mensaje no se ha enviado.
- **Fragilidad de `AppTest`:** los selectores por índice cambian entre versiones de Streamlit.
  - *Mitigación:* se usan `key` explícitas en los widgets y se buscan por `key`.
- **Coste al importar `src.agent`:** importarlo construye el grafo. Si en el futuro hiciera llamadas de red al importarse, los tests de `AppTest` dejarían de ser "sin API".
  - *Mitigación:* un test comprueba que, con los dobles, ni `procesar_turno` ni `aprobar_plan` reales se ejecutan.
- **Estado efímero:** al recargar el navegador se pierde `st.session_state` y la conversación. Lo asume la spec (requisitos no funcionales).
- **Ocultación de secretos incompleta:** solo cubre las variables conocidas y el patrón de Google.
  - *Mitigación:* la lista de variables queda en una constante interna fácil de ampliar.

## Trazabilidad
| RF | Parte del plan | Test |
|---|---|---|
| RF-1 | `ui_agente.enviar_turno`/`decidir` (orden de `mensajes`), `app_agent` pinta en orden | `test_ui_agente.py::test_mensajes_en_orden_cronologico`, `test_app_agent.py::test_app_chat_y_respuesta` |
| RF-2 | `enviar_turno` llama a `procesar` con `thread_id` | `test_ui_agente.py::test_enviar_turno_llama_con_thread_id_activo`, `test_app_agent.py::test_app_chat_y_respuesta` |
| RF-3 | `enviar_turno`: texto vacío → return | `test_ui_agente.py::test_texto_vacio_no_llama_al_agente` |
| RF-4 | `app_agent`: `st.spinner` | Manual (validacion.md) |
| RF-5 | `enviar_turno`: añade mensaje de agente si hay respuesta | `test_ui_agente.py::test_respuesta_no_vacia_se_anade`, `::test_respuesta_y_plan_vacios_no_anaden_mensaje` |
| RF-6 | `enviar_turno`: `plan` en el mensaje; `app_agent` lo pinta como lista | `test_ui_agente.py::test_plan_se_guarda_como_lista` |
| RF-7 | `enviar_turno` + `llamar_seguro` | `test_ui_agente.py::test_error_se_muestra_como_aviso`, `::test_excepcion_del_agente_se_convierte_en_aviso` |
| RF-8 | `ocultar_secretos` en `registrar` | `test_ui_agente.py::test_ocultar_secretos_en_error_preview_y_respuesta` |
| RF-9 | `app_agent`: `file_uploader(accept_multiple_files=False)` | Manual (validacion.md) |
| RF-10 | `validar_imagen` + `config.IMAGEN_MIME_PERMITIDOS` | `test_ui_agente.py::test_validar_imagen_acepta_png_y_jpg` |
| RF-11 | `app_agent`: `st.image` de miniatura | Manual (validacion.md) |
| RF-12 | `enviar_turno` pasa `{"bytes","mime"}` | `test_ui_agente.py::test_imagen_se_pasa_en_formato_contrato` |
| RF-13 | `enviar_turno`: `uploader_key += 1` | `test_ui_agente.py::test_imagen_se_descarta_tras_envio` + manual |
| RF-14 | `validar_imagen`: MIME o firma no válidos → aviso, no envía | `test_ui_agente.py::test_validar_imagen_formato_no_admitido`, `::test_validar_imagen_mime_falseado`, `::test_imagen_invalida_no_envia_mensaje` |
| RF-15 | `validar_imagen` + `config.IMAGEN_MAX_BYTES` | `test_ui_agente.py::test_validar_imagen_supera_limite`, `::test_validar_imagen_en_limite_exacto` |
| RF-16 | `ui_agente` no describe la imagen; capas sin LLM | `test_ui_agente.py::test_imagen_se_pasa_en_formato_contrato`, `test_app_agent.py::test_capas_sin_logica_de_grafo` |
| RF-17 | `pendiente()` → `chat_input(disabled=…)` | `test_ui_agente.py::test_chat_bloqueado_con_plan_pendiente`, `test_app_agent.py::test_app_plan_pendiente_bloquea_chat_y_avisa` |
| RF-18 | `app_agent`: `st.warning` con el texto fijado | `test_app_agent.py::test_app_plan_pendiente_bloquea_chat_y_avisa` |
| RF-19 | `app_agent`: sidebar con botones habilitados y comentario | `test_app_agent.py::test_app_botones_habilitados_solo_con_plan` |
| RF-20 | `app_agent`: `disabled=not pendiente` | `test_app_agent.py::test_app_botones_habilitados_solo_con_plan` |
| RF-21 | `decidir(aprobado=True)` | `test_ui_agente.py::test_aprobar_llama_con_true_y_comentario`, `test_app_agent.py::test_app_aprobar_desde_sidebar` |
| RF-22 | `decidir(aprobado=False)` | `test_ui_agente.py::test_rechazar_llama_con_false_y_comentario`, `test_app_agent.py::test_app_rechazar_desde_sidebar` |
| RF-23 | `decidir`: `done` y sin error → "Plan aprobado" | `test_ui_agente.py::test_aprobacion_con_done_muestra_plan_aprobado` |
| RF-24 | `decidir`: rechazo sin error → mensaje | `test_ui_agente.py::test_rechazo_muestra_mensaje` |
| RF-25 | `decidir` solo añade y no borra | `test_ui_agente.py::test_decision_conserva_mensajes` |
| RF-26 | `pendiente()` falso tras decidir → chat activo | `test_ui_agente.py::test_decision_desbloquea_chat`, `test_app_agent.py::test_app_aprobar_desde_sidebar` |
| RF-27 | `decidir`: error o `done` falso → aviso | `test_ui_agente.py::test_aprobacion_con_error_no_muestra_aprobado`, `::test_aprobacion_sin_done_no_muestra_aprobado` |
| RF-28 | `aprobar` solo se llama desde los botones | `test_ui_agente.py::test_turno_pendiente_no_llama_a_aprobar`, `test_app_agent.py::test_app_sin_aprobacion_automatica` |
| RF-29 | Textos fijos de decisión | `test_ui_agente.py::test_mensajes_de_decision_textos_exactos` |
| RF-30 | `enviar_turno`: error del agente → aviso | `test_ui_agente.py::test_error_plan_pendiente_como_aviso` |
| RF-31 | `app_agent`: `st.expander(expanded=False)` | `test_app_agent.py::test_app_expander_depuracion` (existencia) + manual (cerrado) |
| RF-32 | Expander: `thread_id` | `test_ui_agente.py::test_estado_depuracion`, `test_app_agent.py::test_app_arranca_con_thread_id` |
| RF-33 | Expander: `pendiente_aprobacion` y `done` de `ultimo` | `test_ui_agente.py::test_estado_depuracion`, `test_app_agent.py::test_app_expander_depuracion` |
| RF-34 | `filas_traza` en el orden recibido | `test_ui_agente.py::test_filas_traza_campos_y_orden` |
| RF-35 | `filas_traza`: cinco campos | `test_ui_agente.py::test_filas_traza_campos_y_orden` |
| RF-36 | `registrar` reemplaza `ultimo` | `test_ui_agente.py::test_traza_se_reemplaza` |
| RF-37 | `comentario_hitl` | `test_ui_agente.py::test_comentario_hitl_ultimo_evento`, `::test_comentario_hitl_vacio_no_se_muestra` |
| RF-38 | `nueva_sesion` en el primer render | `test_ui_agente.py::test_nueva_sesion_genera_thread_id_uuid4`, `test_app_agent.py::test_app_arranca_con_thread_id` |
| RF-39 | `thread_id` de la sesión en todas las llamadas | `test_ui_agente.py::test_enviar_turno_llama_con_thread_id_activo`, `::test_decision_usa_mismo_thread_id` |
| RF-40 | `app_agent`: botón siempre visible y habilitado | `test_app_agent.py::test_app_nueva_conversacion_siempre_visible` |
| RF-41 | `nueva_sesion(ids_previos)` | `test_ui_agente.py::test_nueva_conversacion_genera_id_distinto`, `test_app_agent.py::test_app_nueva_conversacion_siempre_visible` |
| RF-42 | `nueva_sesion` vacía mensajes, `ultimo` y uploader; `app_agent` vacía el campo de comentario | `test_ui_agente.py::test_nueva_conversacion_vacia_estado` |
| RF-43 | Nueva conversación no llama a `aprobar` ni añade mensaje de sistema | `test_ui_agente.py::test_nueva_conversacion_con_plan_pendiente_no_decide` |
| RF-44 | Inyección de `procesar`/`aprobar`; sin imports de grafo | `test_app_agent.py::test_capas_sin_logica_de_grafo` |
| RF-45 | `pendiente()` y `decidir` usan solo las banderas | `test_ui_agente.py::test_estado_solo_desde_banderas` |
