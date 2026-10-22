# Spec 005 — Interfaz Streamlit del agente

> Estado: Aprobada · Fecha: 2026-10-22

## Contexto y objetivo
El núcleo del agente (Spec 003) ya expone las dos funciones públicas del contrato (`docs/contrato.md`, sección 1) y la CLI (Spec 004) las consume desde la terminal. El enunciado del PB2 y la constitución (principios 5, 6 y 8) exigen además una interfaz Streamlit en la que la persona usuaria converse con el agente, apruebe o rechace los planes de forma manual y pueda ver la traza del supervisor, las tools y el HITL. Hoy la app Streamlit existente solo cubre el RAG; queremos una app nueva del agente, que se lanza con `streamlit run app_agent.py`, y que sea un cliente fino del contrato: solo llama a las dos funciones públicas y no contiene lógica de grafo.

## Usuarios / actores
- Visitante o persona que planifica una visita al Retiro: conversa con el agente, adjunta imágenes y decide sobre los planes.
- Equipo del proyecto y evaluadores del PB2: usan el panel de depuración para comprobar el recorrido multiagente y el HITL durante la demo.

## Historias de usuario
- H1: Como visitante quiero chatear con el agente en el navegador para resolver dudas y preparar mi visita.
- H2: Como visitante quiero adjuntar una foto a mi mensaje para que el agente tenga en cuenta lo que veo.
- H3: Como visitante quiero aprobar o rechazar el plan propuesto, con un comentario opcional, para que nada se aplique sin mi decisión.
- H4: Como evaluador quiero ver la traza, el `thread_id` y los indicadores `pendiente_aprobacion` y `done` para comprobar qué hizo el agente.
- H5: Como visitante quiero empezar una conversación nueva para no mezclar peticiones distintas.

## Requisitos funcionales (criterios de aceptación en EARS)

### Chat
- RF-1: EL SISTEMA muestra en el área de chat, en orden cronológico, los mensajes de la persona usuaria, las respuestas del agente y los mensajes del sistema de la conversación activa.
- RF-2: CUANDO la persona usuaria envía un mensaje con texto no vacío, EL SISTEMA lo envía al agente mediante la función pública de procesar turno con el identificador de la conversación activa.
- RF-3: SI el mensaje enviado está vacío o solo contiene espacios, ENTONCES EL SISTEMA no llama al agente.
- RF-4: MIENTRAS el agente procesa un mensaje o una decisión, EL SISTEMA muestra un indicador de espera.
- RF-5: CUANDO el agente devuelve una respuesta no vacía, EL SISTEMA la añade al chat como mensaje del agente.
- RF-6: CUANDO el agente devuelve un plan no vacío, EL SISTEMA lo muestra en el chat como lista, un elemento por acción, junto a la respuesta.
- RF-7: SI el agente devuelve un error, ENTONCES EL SISTEMA lo muestra como aviso en el chat y la app sigue operativa.
- RF-8: EL SISTEMA no muestra claves de API, variables de entorno ni secretos en el chat, la sidebar ni el panel de depuración.

### Imagen adjunta
- RF-9: EL SISTEMA permite adjuntar como máximo una imagen opcional por mensaje.
- RF-10: EL SISTEMA solo acepta imágenes en formato PNG o JPG.
- RF-11: CUANDO la persona usuaria adjunta una imagen válida, EL SISTEMA muestra una miniatura antes del envío.
- RF-12: CUANDO se envía un mensaje con una imagen válida adjunta, EL SISTEMA pasa la imagen al agente junto al texto en el formato del contrato (contenido y tipo MIME).
- RF-13: CUANDO se ha enviado un mensaje con imagen, EL SISTEMA descarta la imagen y no la reenvía en mensajes posteriores.
- RF-14: SI la imagen adjunta no es PNG o JPG, ENTONCES EL SISTEMA muestra un aviso y no envía el mensaje.
- RF-15: SI la imagen adjunta supera 5 MB, ENTONCES EL SISTEMA muestra un aviso y no envía el mensaje.
- RF-16: EL SISTEMA no genera descripciones de la imagen por su cuenta; la interpretación corresponde al agente.

### Aprobación humana (HITL)
- RF-17: MIENTRAS el agente indica `pendiente_aprobacion` verdadero, EL SISTEMA desactiva la caja de chat.
- RF-18: MIENTRAS el agente indica `pendiente_aprobacion` verdadero, EL SISTEMA muestra el aviso "Hay un plan pendiente: apruébalo o recházalo para continuar".
- RF-19: MIENTRAS el agente indica `pendiente_aprobacion` verdadero, EL SISTEMA muestra en la sidebar los botones "Aprobar" y "Rechazar" habilitados y un campo de comentario opcional.
- RF-20: MIENTRAS no haya un plan pendiente, EL SISTEMA mantiene los botones "Aprobar" y "Rechazar" deshabilitados u ocultos.
- RF-21: CUANDO la persona usuaria pulsa "Aprobar", EL SISTEMA llama a la función pública de aprobación con decisión afirmativa, el identificador de la conversación activa y el comentario escrito (vacío si no hay).
- RF-22: CUANDO la persona usuaria pulsa "Rechazar", EL SISTEMA llama a la función pública de aprobación con decisión negativa, el identificador de la conversación activa y el comentario escrito (vacío si no hay).
- RF-23: CUANDO la aprobación devuelve `done` verdadero y sin error, EL SISTEMA añade al chat el mensaje del sistema "Plan aprobado".
- RF-24: CUANDO el rechazo se procesa sin error, EL SISTEMA añade al chat el mensaje del sistema "Plan rechazado, puedes hacer otra petición".
- RF-25: CUANDO se procesa una decisión, EL SISTEMA conserva en el chat los mensajes anteriores de la conversación.
- RF-26: CUANDO el agente devuelve `pendiente_aprobacion` falso tras una decisión, EL SISTEMA reactiva la caja de chat.
- RF-27: SI la llamada de aprobación devuelve un error o `done` falso tras aprobar, ENTONCES EL SISTEMA no muestra el mensaje "Plan aprobado" y muestra el error como aviso.
- RF-28: EL SISTEMA no aprueba ni rechaza ningún plan sin que la persona usuaria pulse el botón correspondiente.
- RF-29: EL SISTEMA no afirma que el comentario modifique el siguiente plan.
- RF-30: SI el agente devuelve el error de plan pendiente, ENTONCES EL SISTEMA lo muestra como aviso y la app sigue operativa.

### Panel de depuración
- RF-31: EL SISTEMA ofrece un panel de depuración plegable, cerrado por defecto.
- RF-32: EL SISTEMA muestra en el panel de depuración el `thread_id` de la conversación activa.
- RF-33: EL SISTEMA muestra en el panel de depuración los valores de `pendiente_aprobacion` y `done` devueltos por la última llamada al agente.
- RF-34: EL SISTEMA muestra en el panel de depuración los eventos de traza devueltos por la última llamada al agente, en el orden recibido.
- RF-35: EL SISTEMA muestra de cada evento de traza su `ts`, `origen`, `nombre`, `status` y `preview`.
- RF-36: CUANDO se recibe el resultado de una nueva llamada al agente, EL SISTEMA reemplaza la traza mostrada por la de esa llamada, sin acumularla con la anterior.
- RF-37: CUANDO el último evento de origen `hitl` de la traza incluye en sus `args` un comentario no vacío, EL SISTEMA muestra ese comentario en el panel de depuración junto a ese evento.

### Conversación
- RF-38: CUANDO se abre la app por primera vez en una sesión, EL SISTEMA crea una conversación con un identificador nuevo.
- RF-39: EL SISTEMA usa el mismo identificador de conversación en todas las llamadas al agente de la conversación activa.
- RF-40: EL SISTEMA muestra siempre disponible el botón "Nueva conversación".
- RF-41: CUANDO la persona usuaria pulsa "Nueva conversación", EL SISTEMA genera un identificador de conversación distinto de los anteriores de la sesión.
- RF-42: CUANDO la persona usuaria pulsa "Nueva conversación", EL SISTEMA vacía el chat, la imagen adjunta, el comentario y el panel de depuración.
- RF-43: CUANDO se pulsa "Nueva conversación" con un plan pendiente, EL SISTEMA deja ese plan sin decidir y no muestra que se haya aplicado ni rechazado.

### Separación de responsabilidades
- RF-44: EL SISTEMA se comunica con el agente exclusivamente a través de las dos funciones públicas del contrato.
- RF-45: EL SISTEMA determina el estado de aprobación y de finalización únicamente a partir de `pendiente_aprobacion`, `done` y `error` devueltos por el agente, sin deducirlos del texto de la respuesta.

## Requisitos no funcionales
- Idioma: todos los textos visibles de la app en español.
- Seguridad: ningún secreto visible en la interfaz (RF-8); sin aprobación automática (RF-28).
- Tamaño de imagen: límite de 5 MB, configurable en la configuración centralizada del proyecto.
- Persistencia: la conversación dura lo que el proceso y la sesión del navegador; no se garantiza tras reiniciar la app (coherente con Spec 003, RF-06).
- Tests sin API: las pruebas sustituyen al agente por un doble y no llaman al LLM ni a servicios externos (constitución, principio 9).

## Casos límite
- Mensaje vacío o solo espacios → no se llama al agente (RF-3).
- Imagen con formato no admitido o de más de 5 MB → aviso y no se envía (RF-14, RF-15).
- Imagen en el límite exacto de 5 MB → se acepta (RF-15).
- Varias imágenes en un mismo mensaje → no permitido (RF-9).
- Mensaje enviado tras otro con imagen → va sin imagen (RF-13).
- Respuesta vacía con plan vacío y sin error → no se añade mensaje del agente ni se pide decisión (RF-5, RF-6, RF-20).
- El agente devuelve error "plan pendiente" pese al bloqueo → aviso sin romper la app (RF-30).
- Aprobación que devuelve error o `done` falso → no se muestra "Plan aprobado" (RF-27).
- Doble pulsación de "Aprobar"/"Rechazar" → tras la primera decisión los botones quedan deshabilitados (RF-20); si aun así llega una segunda llamada, el agente devuelve error y se muestra como aviso (RF-7).
- "Nueva conversación" con plan pendiente → plan abandonado sin decidir (RF-43).
- Recarga del navegador o reinicio de la app → la conversación anterior no se recupera (requisitos no funcionales).

## Fuera de alcance
- Cambios en el núcleo del agente, el grafo, las tools o el contrato.
- Cambios en la app Streamlit actual del RAG (banner del tiempo, métricas, contexto recuperado).
- Persistencia de conversaciones entre reinicios o recargas, y listado o recuperación de conversaciones anteriores.
- Retomar desde la UI un plan abandonado en otra conversación.
- Varias imágenes por mensaje, formatos distintos de PNG y JPG, y otros adjuntos (audio, documentos).
- Respuestas en streaming token a token.
- Autenticación de usuarios, despliegue en la nube y modo demo con aprobación automática.
- Edición o borrado de mensajes ya enviados.
- Que el comentario de la decisión influya en el siguiente plan.

## Criterios de finalización
- Todos los RF con test en verde (`pytest`), usando un doble del agente y sin API.
- Demo manual con `streamlit run app_agent.py` del flujo principal: petición → plan pendiente → chat bloqueado → aprobar (`done` verdadero); y petición → rechazar → nueva petición en el mismo hilo; y "Nueva conversación" con cambio de `thread_id`.
- Comprobación de que la app no contiene lógica de grafo (constitución, principio 6).

## Dependencias
- Esta spec da por supuesto el comportamiento del núcleo definido en la Spec 003 (PR #6, que debe estar mergeada en `develop` antes de implementar), en concreto:
  - La traza que devuelve la función de aprobación incluye, en orden, los eventos del turno y el evento de la decisión.
  - El último evento `hitl` (`aprobar` o `rechazar`) lleva el comentario en `args.comentario`.

## Dudas abiertas
- Ninguna.
