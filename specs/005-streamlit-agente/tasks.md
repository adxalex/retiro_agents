# Tareas — Spec 005

> Una tarea cada vez: `/sdd-implementar Tn`. Tests primero. Marca `[x]` al terminar.
> En las comprobaciones manuales con `streamlit run app_agent.py` no se envía ningún mensaje salvo que se indique, para no gastar API.

## Requisito previo
- [x] T1. Traer a `feature/streamlit-ui` la PR #6 de `develop` (corrección del evento HITL `"aprobar"`, commit `a6159b7`). (Dependencia de la spec)
      Hecho cuando: `git branch --contains a6159b7` incluye `feature/streamlit-ui` y `pytest` sale en verde.

## Bloque 1 — MVP funcional
- [x] T2. Añadir a `config.py` la sección "Interfaz Streamlit del agente" con `IMAGEN_MAX_BYTES = 5 * 1024 * 1024` e `IMAGEN_MIME_PERMITIDOS = ("image/png", "image/jpeg")`. Tests primero. (RF-10, RF-15)
      Hecho cuando: `pytest tests/test_ui_agente.py::test_config_limites_imagen` en verde.
- [x] T3. Crear `src/ui_agente.py` con `nueva_sesion()`: `thread_id` uuid4, `mensajes` vacíos, `ultimo=None` y `uploader_key=0`. Tests primero. (RF-38, RF-39)
      Hecho cuando: `pytest tests/test_ui_agente.py::test_nueva_sesion_genera_thread_id_uuid4` en verde.
- [x] T4. Implementar `enviar_turno(sesion, texto, mime, datos, procesar)` para el caso sin imagen (`mime=datos=None`). Añade el mensaje de usuario, llama a `procesar` con el `thread_id` de la sesión y añade la respuesta y el plan del agente. No llama al agente si el texto está vacío. La validación de imagen llega en T10. Tests primero, con el doble `procesar_falso`. (RF-1, RF-2, RF-3, RF-5, RF-6, RF-39)
      Hecho cuando: en verde `test_mensajes_en_orden_cronologico`, `test_enviar_turno_llama_con_thread_id_activo`, `test_texto_vacio_no_llama_al_agente`, `test_respuesta_no_vacia_se_anade`, `test_respuesta_y_plan_vacios_no_anaden_mensaje` y `test_plan_se_guarda_como_lista` de `tests/test_ui_agente.py`.
- [x] T5. Añadir `llamar_seguro`, `registrar` (sustituye `ultimo`) y `pendiente(sesion)`. Los errores y las excepciones del agente se convierten en mensajes de aviso. Tests primero. (RF-7, RF-17, RF-30, RF-36, RF-45)
      Hecho cuando: en verde `test_error_se_muestra_como_aviso`, `test_excepcion_del_agente_se_convierte_en_aviso`, `test_error_plan_pendiente_como_aviso`, `test_error_plan_pendiente_no_duplica_respuesta`, `test_traza_se_reemplaza`, `test_chat_bloqueado_con_plan_pendiente` y `test_estado_solo_desde_banderas` de `tests/test_ui_agente.py`.
- [x] T6. Implementar `decidir(sesion, aprobado, comentario, aprobar)`:
      - Muestra "Plan aprobado" solo si `done` es verdadero y no hay error.
      - Muestra "Plan rechazado, puedes hacer otra petición" si se rechaza sin error.
      - En cualquier otro caso añade un aviso.
      - Conserva los mensajes anteriores.
      Tests primero, con el doble `aprobar_falso`. (RF-21, RF-22, RF-23, RF-24, RF-25, RF-26, RF-27, RF-28, RF-29, RF-39)
      Hecho cuando: en verde `test_aprobar_llama_con_true_y_comentario`, `test_rechazar_llama_con_false_y_comentario`, `test_aprobacion_con_done_muestra_plan_aprobado`, `test_rechazo_muestra_mensaje`, `test_decision_conserva_mensajes`, `test_decision_desbloquea_chat`, `test_aprobacion_con_error_no_muestra_aprobado`, `test_aprobacion_sin_done_no_muestra_aprobado`, `test_turno_pendiente_no_llama_a_aprobar`, `test_mensajes_de_decision_textos_exactos`, `test_decision_usa_mismo_thread_id`, `test_decision_con_excepcion_mantiene_plan_pendiente`, `test_decision_con_error_del_nucleo_usa_su_bandera` y `test_turno_con_excepcion_deja_chat_libre`.
- [x] T7. Implementar los datos del panel de depuración. `filas_traza(traza)` devuelve los cinco campos en orden. `comentario_hitl(traza)` devuelve el comentario del último evento `hitl` si no está vacío. `estado_depuracion(sesion)` reúne `thread_id`, `pendiente_aprobacion`, `done`, las filas y el comentario. Tests primero. (RF-32, RF-33, RF-34, RF-35, RF-37)
      Hecho cuando: en verde `test_filas_traza_campos_y_orden`, `test_comentario_hitl_ultimo_evento`, `test_comentario_hitl_vacio_no_se_muestra` y `test_estado_depuracion`.
- [x] T8. Crear la versión mínima de `app_agent.py`:
      - Chat con los mensajes por rol y el plan como lista.
      - `chat_input` desactivado y aviso "Hay un plan pendiente: apruébalo o recházalo para continuar" mientras haya un plan pendiente.
      - Sidebar con un campo de comentario y los botones Aprobar y Rechazar, deshabilitados si no hay plan pendiente.
      - Spinner y `st.rerun()` tras cada acción.
      - Expander "Depuración" cerrado por defecto.
      - Las llamadas al agente se hacen por atributo (`agent.procesar_turno`, `agent.aprobar_plan`).
      Tests primero: el test estático de capas. (RF-1, RF-4, RF-6, RF-16, RF-17, RF-18, RF-19, RF-20, RF-31, RF-44)
      Hecho cuando:
      - `pytest tests/test_app_agent.py::test_capas_sin_logica_de_grafo` en verde.
      - `streamlit run app_agent.py` abre sin errores y, sin enviar nada, muestra la caja de chat activa, los botones Aprobar y Rechazar deshabilitados y el expander "Depuración" cerrado, que al abrirlo enseña el `thread_id`.

## Bloque 2 — Imagen, secretos y nueva conversación
- [x] T9. Implementar `validar_imagen(mime, datos)`: comprueba el MIME y la firma de bytes de PNG y JPG, rechaza lo que supere `IMAGEN_MAX_BYTES` y acepta el límite exacto. Tests primero. (RF-10, RF-14, RF-15)
      Hecho cuando: en verde `test_validar_imagen_acepta_png_y_jpg`, `test_validar_imagen_formato_no_admitido`, `test_validar_imagen_mime_falseado`, `test_validar_imagen_supera_limite` y `test_validar_imagen_en_limite_exacto`.
- [x] T10. Integrar la imagen en `enviar_turno`:
      - Si la imagen no es válida, muestra un aviso y no envía el mensaje.
      - Si es válida, la pasa al agente como `{"bytes", "mime"}` sin describirla.
      - Después del envío incrementa `uploader_key`.
      Tests primero. (RF-12, RF-13, RF-14, RF-15, RF-16)
      Hecho cuando: en verde `test_imagen_invalida_no_envia_mensaje`, `test_imagen_se_pasa_en_formato_contrato` y `test_imagen_se_descarta_tras_envio`.
- [x] T11. Añadir a `app_agent.py` un `st.file_uploader` con un solo archivo, tipos png/jpg/jpeg y `key` ligada a `uploader_key`. Muestra la miniatura con `st.image` y avisa en cuanto se adjunta un archivo no válido. (RF-9, RF-11, RF-13, RF-14)
      Hecho cuando: con `streamlit run app_agent.py` y sin enviar mensaje:
      - Al adjuntar un PNG de menos de 5 MB se ve su miniatura.
      - El selector no permite elegir dos archivos.
      - Al adjuntar un PNG de más de 5 MB aparece el aviso de tamaño.
      - `pytest` sigue en verde.
- [x] T12. Implementar `ocultar_secretos(texto)`: enmascara los valores de `GEMINI_API_KEY`, `GOOGLE_API_KEY` y `AEMET_API_KEY` presentes en el entorno y el patrón `AIza…`. Se aplica en `registrar` a `respuesta`, `error`, `plan` y a `preview` y `args.comentario` de la traza. Tests primero, con `monkeypatch.setenv`. (RF-8)
      Hecho cuando: `pytest tests/test_ui_agente.py::test_ocultar_secretos_en_error_preview_y_respuesta` en verde.
- [ ] T13. Ampliar `nueva_sesion(ids_previos=())`, con `ids_previos` opcional y vacío por defecto para que el test de T3 siga valiendo, para que genere un id distinto de los anteriores y deje mensajes, `ultimo` y uploader vacíos, sin llamar a `aprobar` aunque haya un plan pendiente. Tests primero. (RF-41, RF-42, RF-43)
      Hecho cuando: en verde `test_nueva_conversacion_genera_id_distinto`, `test_nueva_conversacion_vacia_estado` y `test_nueva_conversacion_con_plan_pendiente_no_decide`.
- [ ] T14. Añadir a la sidebar de `app_agent.py` el botón "Nueva conversación", siempre habilitado. Crea una sesión nueva con los ids previos y vacía el campo de comentario. (RF-40, RF-42)
      Hecho cuando: con `streamlit run app_agent.py`, al pulsar "Nueva conversación" el `thread_id` del expander cambia, el chat queda vacío y `pytest` sigue en verde.
- [ ] T15. Actualizar `AGENTS.md`: añadir `app_agent.py` y `src/ui_agente.py` al mapa del código y el comando `streamlit run app_agent.py` ⚠️ a Comandos. (Documentación)
      Hecho cuando: `AGENTS.md` incluye las dos filas y el comando, y `pytest` sale en verde.

## Bloque 3 — Tests de la app con AppTest
- [ ] T16. Crear en `tests/test_app_agent.py` el fixture con `AppTest.from_file("app_agent.py")` y dobles de `src.agent.procesar_turno` y `src.agent.aprobar_plan` con `monkeypatch`, que cuentan llamadas. Añadir los tests de arranque y chat. (RF-1, RF-2, RF-5, RF-32, RF-38)
      Hecho cuando: en verde `test_app_arranca_con_thread_id` y `test_app_chat_y_respuesta`.
- [ ] T17. Añadir los tests de plan pendiente: caja de chat desactivada, aviso visible, botones habilitados solo con plan y ninguna llamada a `aprobar_plan` sin pulsar un botón. (RF-17, RF-18, RF-19, RF-20, RF-28)
      Hecho cuando: en verde `test_app_plan_pendiente_bloquea_chat_y_avisa`, `test_app_botones_habilitados_solo_con_plan` y `test_app_sin_aprobacion_automatica`.
- [ ] T18. Añadir los tests de decisión desde la sidebar: Aprobar y Rechazar llaman al doble con el comentario escrito, muestran el mensaje del sistema y reactivan el chat. (RF-21, RF-22, RF-23, RF-24, RF-26)
      Hecho cuando: en verde `test_app_aprobar_desde_sidebar` y `test_app_rechazar_desde_sidebar`.
- [ ] T19. Añadir los tests de "Nueva conversación" (visible, habilitado y cambia el `thread_id`) y del expander de depuración (existe y muestra `pendiente_aprobacion` y `done`). (RF-31, RF-33, RF-40, RF-41)
      Hecho cuando: en verde `test_app_nueva_conversacion_siempre_visible` y `test_app_expander_depuracion`.
## Validación
- [ ] T20. Validación final RF por RF (`/sdd-validar`), con las comprobaciones manuales de RF-4, RF-9, RF-11, RF-13 y RF-31 y la demo de los criterios de finalización. (Todos)
      Hecho cuando: `validacion.md` con veredicto "Sí".
      Evidencia ya conseguida (25/10): comprobación manual de T8 superada con una prueba real con Gemini en `streamlit run app_agent.py`. Se generó un plan, el chat quedó bloqueado mientras estaba pendiente y se aprobó y rechazó con comentario.
