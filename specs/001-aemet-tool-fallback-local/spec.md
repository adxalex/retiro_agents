# Spec 001 — Tool meteorológica de AEMET con fallback local

> Estado: Aprobada · Fecha: 2026-10-17

## Contexto y objetivo
La información meteorológica actual del Retiro depende de AEMET y, si el servicio no está disponible, el sistema no ofrece datos alternativos. Esta funcionalidad permitirá que un agente solicite observación, previsión y avisos meteorológicos de AEMET, con respaldo local cuando el servicio externo falle, para que la información útil no dependa exclusivamente de la conexión con AEMET.

## Usuarios / actores
- Visitante del Parque de El Retiro que consulta información meteorológica mediante el agente.
- Agente que solicita y presenta información meteorológica.

## Historias de usuario
- H1: Como visitante quiero consultar observación, previsión y avisos meteorológicos del Retiro para conocer las condiciones actuales y las esperadas durante el resto del día.
- H2: Como visitante quiero recibir información de respaldo cuando AEMET no esté disponible para que la consulta no dependa únicamente del servicio externo.

## Requisitos funcionales (criterios de aceptación en EARS)
- RF-1: CUANDO el agente solicite información meteorológica del Retiro, EL SISTEMA obtendrá de AEMET la observación actual de la estación meteorológica del Retiro.
- RF-2: CUANDO la herramienta `hora_actual` proporcione la hora actual en formato ISO 8601 con precisión de segundos, EL SISTEMA obtendrá la previsión y los avisos aplicables desde esa hora hasta el final del día correspondiente.
- RF-3: SI AEMET no está disponible o no proporciona datos válidos, ENTONCES EL SISTEMA obtendrá la información meteorológica solicitada de una fuente local de respaldo [NECESITA ACLARACIÓN: ¿qué fuente local concreta debe proporcionar la observación, la previsión y los avisos?].
- RF-4: SI no hay información válida disponible ni en AEMET ni en la fuente local de respaldo, ENTONCES EL SISTEMA informará que no pudo obtener los datos solicitados y no presentará datos meteorológicos inventados.
- RF-5: CUANDO EL SISTEMA use la fuente local de respaldo, indicará que los datos proceden de esa fuente y comunicará su fecha y hora de referencia cuando estén disponibles.
- RF-6: CUANDO la herramienta concluya una solicitud, EL SISTEMA devolverá un resultado con estado `ok`, `error` o `blocked`.
- RF-7: CUANDO la herramienta procese una solicitud, EL SISTEMA dejará una traza visible del resultado.

## Requisitos no funcionales
- Cada petición HTTP a AEMET tendrá un timeout de 8 segundos, conforme al límite ya establecido para las consultas meteorológicas.
- Los mensajes y errores visibles para la persona usuaria estarán en español.

## Casos límite
- AEMET no tiene credenciales configuradas, no responde, devuelve un error HTTP, datos JSON no válidos o una respuesta sin los datos pedidos: se aplicará el fallback local (RF-3).
- La fuente local no contiene información válida para todos o algunos de los datos pedidos: no se completarán los datos ausentes mediante invención (RF-4).
- La hora recibida no permite determinar la previsión o los avisos correspondientes: [NECESITA ACLARACIÓN: ¿qué zona horaria debe usarse para interpretar la hora recibida por `hora_actual`?] (RF-2).
- Los datos locales no incluyen fecha y hora de referencia: se indicará la fuente local y se omitirán los metadatos temporales no disponibles (RF-5).

## Fuera de alcance
- Cambiar el horario o el estado de apertura del parque.
- Cambiar el saludo contextual actual, salvo lo necesario para consumir el resultado de esta herramienta [NECESITA ACLARACIÓN: ¿debe sustituirse con esta herramienta la consulta meteorológica que usa actualmente el saludo?].
- Cambiar el comportamiento de recuperación RAG o las respuestas basadas en el corpus.

## Criterios de finalización
- Todos los requisitos funcionales tienen criterios verificables y pruebas sin depender de llamadas reales a AEMET.
- La consulta meteorológica externa y el uso de la fuente local de respaldo quedan cubiertos por pruebas con servicios simulados.
- La spec queda aprobada por la persona solicitante antes de pasar a plan.

## Dudas abiertas
- [NECESITA ACLARACIÓN: ¿qué fuente local concreta debe proporcionar la observación, la previsión y los avisos?]
- [NECESITA ACLARACIÓN: ¿qué zona horaria debe usarse para interpretar la hora recibida por `hora_actual` y determinar el final del día?]
- [NECESITA ACLARACIÓN: ¿debe sustituirse con esta herramienta la consulta meteorológica que usa actualmente el saludo contextual?]
