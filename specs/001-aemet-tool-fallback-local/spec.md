# Spec 001 — Tool meteorológica de AEMET con fallback local

> Estado: Aprobada · Fecha: 2026-10-17

## Contexto y objetivo
La información meteorológica actual del Retiro depende de AEMET y, si el servicio no está disponible, el sistema no ofrece datos alternativos. Esta funcionalidad permitirá que un agente solicite observación, previsión y avisos meteorológicos de AEMET, con respaldo local cuando el servicio externo falle, para que la información útil no dependa exclusivamente de la conexión con AEMET.

## Usuarios / actores
- Visitante del Parque de El Retiro que consulta información meteorológica mediante el agente.
- Agente que solicita y presenta información meteorológica.

## Historias de usuario
- H1: Como visitante quiero consultar observación, previsión y avisos meteorológicos del Retiro para conocer las condiciones actuales y las esperadas durante el resto del día.
- H2: Como visitante quiero recibir una observación de respaldo y saber si no hay previsión o avisos cuando AEMET no esté disponible.

## Requisitos funcionales (criterios de aceptación en EARS)
- RF-1: CUANDO el agente solicite información meteorológica del Retiro, EL SISTEMA obtendrá de AEMET la observación actual de la estación meteorológica del Retiro.
- RF-2: CUANDO la herramienta `hora_actual` proporcione una hora válida en formato ISO 8601 con precisión de segundos y offset UTC+01:00, EL SISTEMA obtendrá la previsión y los avisos aplicables desde esa hora hasta el final del día correspondiente. SI `hora_actual` no está disponible, ENTONCES EL SISTEMA devolverá solo la observación. SI la hora o su zona/offset no son válidos, ENTONCES EL SISTEMA usará la observación local de respaldo e indicará que el error se debe a la hora; no presentará previsión ni avisos.
- RF-3: SI AEMET no responde, devuelve un error, JSON no válido o ninguna observación válida, ENTONCES EL SISTEMA obtendrá la observación de respaldo del archivo `src/tools/fallback/aemet.json`. Esta fuente solo contiene observación: EL SISTEMA indicará que no puede proporcionar previsión ni avisos por el fallo de AEMET. Si la respuesta de AEMET contiene datos válidos y otros datos solicitados ausentes o inválidos, EL SISTEMA mostrará los datos válidos e indicará el error de AEMET para los datos ausentes, sin completarlos con la fuente local.
- RF-4: SI no hay información válida disponible ni en AEMET ni en la fuente local de respaldo, ENTONCES EL SISTEMA informará que no pudo obtener los datos solicitados y no presentará datos meteorológicos inventados.
- RF-5: CUANDO EL SISTEMA use la fuente local de respaldo, indicará que los datos proceden de esa fuente y comunicará su fecha y hora de referencia cuando estén disponibles.
- RF-6: CUANDO la herramienta concluya una solicitud, EL SISTEMA devolverá un resultado con estado `ok`, `error` o `blocked`. La herramienta no propagará excepciones; los errores inesperados se devolverán con estado `error`, conforme a la constitución.
- RF-7: CUANDO la herramienta procese una solicitud, EL SISTEMA dejará una traza visible del resultado.

## Requisitos no funcionales
- Cada petición HTTP a AEMET tendrá un timeout de 8 segundos, conforme al límite ya establecido para las consultas meteorológicas.
- Los mensajes y errores visibles para la persona usuaria estarán en español.

## Casos límite
- AEMET no tiene credenciales configuradas, no responde, devuelve un error HTTP o datos JSON no válidos, o no proporciona una observación válida: se usará la observación local. No se inventarán previsión ni avisos (RF-3, RF-4).
- AEMET devuelve solo parte de los datos solicitados: se mostrarán los datos válidos y se dejará constancia del error de AEMET para los datos ausentes, sin completarlos con la fuente local (RF-3).
- La fuente local no contiene información válida para todos o algunos de los datos pedidos: no se completarán los datos ausentes mediante invención (RF-4).
- `hora_actual` aún no está disponible: se devolverá solo la observación, sin previsión ni avisos (RF-2).
- La hora recibida no es válida o no usa el offset UTC+01:00: se usará la observación local y se indicará que el error se debe a la hora; no se presentarán previsión ni avisos (RF-2).
- Los datos locales no incluyen fecha y hora de referencia: se indicará la fuente local y se omitirán los metadatos temporales no disponibles (RF-5).

## Fuera de alcance
- Cambiar el horario o el estado de apertura del parque.
- Cambiar la consulta meteorológica del saludo contextual. Esta herramienta será usada solo por agentes.
- Cambiar el comportamiento de recuperación RAG o las respuestas basadas en el corpus.

## Criterios de finalización
- Todos los requisitos funcionales tienen criterios verificables y pruebas sin depender de llamadas reales a AEMET.
- La consulta meteorológica externa y el uso de la fuente local de respaldo quedan cubiertos por pruebas con servicios simulados.
- La spec queda aprobada por la persona solicitante antes de pasar a plan.
