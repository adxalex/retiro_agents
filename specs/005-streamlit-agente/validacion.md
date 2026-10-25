# Validación — Spec 005

> Fecha: 2026-10-25 · Resultado de `pytest`: 454 passed / 0 failed

Fuentes de evidencia:
- **Automático:** test de la suite (`ui` = `tests/test_ui_agente.py`, `app` = `tests/test_app_agent.py`), con dobles del agente y sin API.
- **Prueba real 25/10:** `streamlit run app_agent.py` con Gemini. Se observó:
  - mensaje "Quiero un plan de visita de 1 hora; te adjunto el plano." con imagen → "El agente está trabajando..." mientras se esperaba (captura de pantalla) → aviso de plan pendiente;
  - durante la espera, el campo de comentario y los botones Aprobar y Rechazar estaban deshabilitados (aún sin plan pendiente);
  - selector de imagen vacío tras enviar;
  - en "Depuración" de las dos peticiones aparece `describir_imagen` con status `ok` y un preview de texto, sin bytes;
  - aprobar con comentario → "Plan aprobado";
  - nueva solicitud en la misma conversación, otra vez con el plano → aviso de plan pendiente;
  - rechazar con comentario → "Plan rechazado, puedes hacer otra petición";
  - recargar la página → expander "Depuración" cerrado.
- **Checklist T11 (25/10):** miniatura visible con `valida.png` y `valida.jpg`; aviso sin miniatura con `grande.png` (tamaño) y `falsa.png` (formato).
- **Checklist T14 (25/10):** "Nueva conversación" cambia el `thread_id` y vacía el selector de imagen.

| RF | Cómo se comprueba | Test o comprobación manual | Resultado |
|---|---|---|---|
| RF-1 | Automático | `ui::test_mensajes_en_orden_cronologico`, `app::test_app_chat_y_respuesta` | ✅ |
| RF-2 | Automático | `ui::test_enviar_turno_llama_con_thread_id_activo`, `app::test_app_chat_y_respuesta` | ✅ |
| RF-3 | Automático | `ui::test_texto_vacio_no_llama_al_agente` | ✅ |
| RF-4 | Manual | Prueba real: "El agente está trabajando..." visible al esperar la respuesta (captura). El indicador "Enviando la decisión al agente..." no se observó; solo consta en el código (`st.spinner` en `_sidebar`) | ✅ |
| RF-5 | Automático | `ui::test_respuesta_no_vacia_se_anade`, `ui::test_respuesta_y_plan_vacios_no_anaden_mensaje`, `app::test_app_chat_y_respuesta` | ✅ |
| RF-6 | Automático | `ui::test_plan_se_guarda_como_lista`, `app::test_app_plan_se_pinta_como_lista` | ✅ |
| RF-7 | Automático | `ui::test_error_se_muestra_como_aviso`, `ui::test_excepcion_del_agente_se_convierte_en_aviso`, `ui::test_turno_con_excepcion_deja_chat_libre` | ✅ |
| RF-8 | Automático | `ui::test_ocultar_secretos_valores_de_entorno`, `ui::test_ocultar_secretos_patron_google`, `ui::test_ocultar_secretos_en_error_preview_y_respuesta` | ✅ |
| RF-9 | Automático | `app::test_app_selector_un_solo_archivo_png_jpg` (`multiple_files` falso; tipos `.png`, `.jpg`, `.jpeg`) | ✅ |
| RF-10 | Automático | `ui::test_validar_imagen_acepta_png_y_jpg`, `ui::test_validar_imagen_formato_no_admitido`, `ui::test_config_limites_imagen`, `app::test_app_selector_un_solo_archivo_png_jpg` | ✅ |
| RF-11 | Manual (checklist T11) | Miniatura visible con `valida.png` y `valida.jpg` | ✅ |
| RF-12 | Automático + manual | `ui::test_imagen_se_pasa_en_formato_contrato`; prueba real: plano adjunto en dos peticiones y `describir_imagen` con status `ok` y preview de texto, sin bytes, en "Depuración" | ✅ |
| RF-13 | Automático + manual | `ui::test_imagen_se_descarta_tras_envio`; prueba real: selector vacío tras enviar | ✅ |
| RF-14 | Automático + manual | `ui::test_validar_imagen_formato_no_admitido`, `ui::test_validar_imagen_mime_falseado`, `ui::test_imagen_invalida_no_envia_mensaje[formato]`; checklist T11: aviso sin miniatura con `falsa.png` | ✅ |
| RF-15 | Automático + manual | `ui::test_validar_imagen_supera_limite`, `ui::test_validar_imagen_en_limite_exacto`, `ui::test_imagen_invalida_no_envia_mensaje[tamano]`; checklist T11: aviso sin miniatura con `grande.png` | ✅ |
| RF-16 | Automático | `ui::test_imagen_se_pasa_en_formato_contrato`, `app::test_capas_sin_logica_de_grafo` | ✅ |
| RF-17 | Automático | `ui::test_chat_bloqueado_con_plan_pendiente`, `ui::test_decision_con_excepcion_mantiene_plan_pendiente`, `app::test_app_plan_pendiente_bloquea_chat_y_avisa` (el bloqueo de la caja de chat no se registró a mano) | ✅ |
| RF-18 | Automático + manual | `app::test_app_plan_pendiente_bloquea_chat_y_avisa`; prueba real: aviso de plan pendiente en las dos peticiones | ✅ |
| RF-19 | Automático | `app::test_app_botones_habilitados_solo_con_plan` | ✅ |
| RF-20 | Automático + manual | `app::test_app_botones_habilitados_solo_con_plan`, `app::test_app_aprobar_desde_sidebar`, `app::test_app_rechazar_desde_sidebar`; prueba real: comentario y botones deshabilitados durante la espera, sin plan pendiente | ✅ |
| RF-21 | Automático + manual | `ui::test_aprobar_llama_con_true_y_comentario`, `app::test_app_aprobar_desde_sidebar`; prueba real: aprobar con comentario | ✅ |
| RF-22 | Automático + manual | `ui::test_rechazar_llama_con_false_y_comentario`, `app::test_app_rechazar_desde_sidebar`; prueba real: rechazar con comentario | ✅ |
| RF-23 | Automático + manual | `ui::test_aprobacion_con_done_muestra_plan_aprobado`, `app::test_app_aprobar_desde_sidebar`; prueba real: "Plan aprobado" | ✅ |
| RF-24 | Automático + manual | `ui::test_rechazo_muestra_mensaje`, `app::test_app_rechazar_desde_sidebar`; prueba real: "Plan rechazado, puedes hacer otra petición" | ✅ |
| RF-25 | Automático | `ui::test_decision_conserva_mensajes` | ✅ |
| RF-26 | Automático + manual | `ui::test_decision_desbloquea_chat`, `app::test_app_aprobar_desde_sidebar`, `app::test_app_rechazar_desde_sidebar`; prueba real: tras aprobar se pudo enviar una nueva solicitud | ✅ |
| RF-27 | Automático | `ui::test_aprobacion_con_error_no_muestra_aprobado`, `ui::test_aprobacion_sin_done_no_muestra_aprobado` | ✅ |
| RF-28 | Automático | `ui::test_turno_pendiente_no_llama_a_aprobar`, `app::test_app_sin_aprobacion_automatica` | ✅ |
| RF-29 | Automático | `ui::test_mensajes_de_decision_textos_exactos` | ✅ |
| RF-30 | Automático | `ui::test_error_plan_pendiente_como_aviso`, `ui::test_error_plan_pendiente_no_duplica_respuesta` | ✅ |
| RF-31 | Automático + manual | `app::test_app_expander_depuracion` (existe); prueba real: cerrado tras recargar | ✅ |
| RF-32 | Automático | `ui::test_estado_depuracion`, `app::test_app_arranca_con_thread_id` | ✅ |
| RF-33 | Automático | `ui::test_estado_depuracion`, `app::test_app_expander_depuracion` | ✅ |
| RF-34 | Automático | `ui::test_filas_traza_campos_y_orden`, `app::test_app_traza_en_panel` | ✅ |
| RF-35 | Automático | `ui::test_filas_traza_campos_y_orden`, `app::test_app_traza_en_panel` | ✅ |
| RF-36 | Automático | `ui::test_traza_se_reemplaza` | ✅ |
| RF-37 | Automático | `ui::test_comentario_hitl_ultimo_evento`, `ui::test_comentario_hitl_vacio_no_se_muestra`, `app::test_app_comentario_en_panel` | ✅ |
| RF-38 | Automático | `ui::test_nueva_sesion_genera_thread_id_uuid4`, `app::test_app_arranca_con_thread_id` | ✅ |
| RF-39 | Automático + manual | `ui::test_enviar_turno_llama_con_thread_id_activo`, `ui::test_decision_usa_mismo_thread_id`, `app::test_app_chat_y_respuesta`, `app::test_app_peticion_tras_rechazo_mismo_hilo`; prueba real: segunda solicitud en la misma conversación | ✅ |
| RF-40 | Automático | `app::test_app_nueva_conversacion_siempre_visible` | ✅ |
| RF-41 | Automático + manual | `ui::test_nueva_conversacion_genera_id_distinto`, `app::test_app_nueva_conversacion_siempre_visible`; checklist T14: el `thread_id` cambia | ✅ |
| RF-42 | Automático + manual | `ui::test_nueva_conversacion_vacia_estado`, `app::test_app_nueva_conversacion_siempre_visible`, `app::test_app_nueva_conversacion_vacia_comentario`; checklist T14: selector vacío | ✅ |
| RF-43 | Automático | `ui::test_nueva_conversacion_con_plan_pendiente_no_decide`, `app::test_app_nueva_conversacion_siempre_visible` | ✅ |
| RF-44 | Automático | `app::test_capas_sin_logica_de_grafo`, `ui::test_ui_agente_no_importa_streamlit_ni_nucleo` | ✅ |
| RF-45 | Automático | `ui::test_estado_solo_desde_banderas`, `ui::test_decision_con_excepcion_mantiene_plan_pendiente`, `ui::test_decision_con_error_del_nucleo_usa_su_bandera` | ✅ |

## Criterios de finalización
- [x] Todos los RF con test en verde (`pytest`), con un doble del agente y sin API: 43 de 45 RF tienen test automático en verde. RF-4 (indicador de espera) y RF-11 (miniatura) no se pueden comprobar con AppTest; se verificaron a mano, como preveía el plan.
- [x] Demo manual con `streamlit run app_agent.py`:
  - petición → plan pendiente → aprobar: observado en la prueba real (aviso de plan pendiente y "Plan aprobado", que solo aparece con `done` verdadero). El bloqueo de la caja de chat lo cubre `app::test_app_plan_pendiente_bloquea_chat_y_avisa`.
  - petición → rechazar: observado en la prueba real. La petición nueva en el mismo hilo tras rechazar la cubre `app::test_app_peticion_tras_rechazo_mismo_hilo`; en la prueba real se observó una segunda petición en el mismo hilo tras aprobar.
  - "Nueva conversación" con cambio de `thread_id`: checklist T14.
- [x] La app no contiene lógica de grafo (constitución, principio 6): `app::test_capas_sin_logica_de_grafo`.

## Fuera de spec
Comportamiento implementado que la spec no pide expresamente. Todo está recogido en el plan o se acordó durante la implementación:
- `decidir` no llama al agente si no hay plan pendiente.
- Si el agente lanza una excepción, la UI conserva el último `pendiente_aprobacion` conocido (lectura de RF-17 y RF-45).
- Con el error "plan pendiente", no se vuelve a pintar el pedido anterior: solo el aviso.
- Aprobar sin error pero con `done` falso muestra el aviso "El plan no se ha completado."
- Ante una excepción, el aviso es un texto fijo, sin el mensaje de la excepción.
- El campo de comentario está deshabilitado sin plan pendiente y se vacía tras cada decisión.
- La imagen se valida y avisa en cuanto se adjunta, antes de enviar.
- El texto se envía sin espacios al principio y al final; un mensaje con imagen pero sin texto no se envía y no muestra aviso.

## Limitaciones conocidas
1. Si la imagen no es válida, el texto escrito en el chat no se conserva y hay que volver a escribirlo: `st.chat_input` se vacía al enviar, aunque el mensaje no llegue a enviarse.
2. El itinerario puede aparecer repetido en el chat: el núcleo lo incluye en el texto de la respuesta y la interfaz lo pinta también como lista a partir del campo `plan`.

## Veredicto
**Sí.** Los 45 RF están verificados, por test de la suite (454 passed) o por observación en la prueba real y en los checklists de T11 y T14 del 25/10. La app no contiene lógica de grafo. Las dos limitaciones conocidas no incumplen ningún RF: RF-14 solo pide el aviso y no enviar, y RF-6 pide pintar el plan como lista. El indicador de espera al decidir ("Enviando la decisión al agente...") no se ha observado; RF-4 queda verificado con el indicador del envío de mensajes.
