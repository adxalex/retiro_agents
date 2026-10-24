# Spec 001 — Herramientas del agente

> Estado: Aprobada · Fecha: 2026-10-24

## Contexto y objetivo
El agente necesita consultar la hora, información meteorológica de El Retiro, descripciones de imágenes e información respaldada por el corpus del proyecto. Esta especificación define el comportamiento observable común de esas herramientas y el comportamiento propio de cada una, incluidos sus resultados y errores, para que el agente pueda utilizarlas sin inventar datos ni confundir una respuesta parcial con una respuesta completa.

## Usuarios / actores
- Agente del proyecto: invoca las herramientas y utiliza sus resultados para resolver tareas.
- Visitante del parque: se beneficia indirectamente de la información que el agente obtiene.

## Historias de usuario
- H1: Como agente quiero consultar la fecha y hora actuales para responder con información temporal correcta.
- H2: Como agente quiero consultar observaciones, previsiones y avisos meteorológicos para informar sobre las condiciones del Retiro.
- H3: Como agente quiero obtener una descripción textual de una imagen para interpretar su contenido.
- H4: Como agente quiero consultar el corpus del proyecto para responder con información respaldada por sus fuentes.

## Requisitos funcionales (criterios de aceptación en EARS)

### A. Comportamiento común
- RF-1: CUANDO se ejecute una herramienta, EL SISTEMA devolverá un diccionario con las claves `tool`, `status`, `data`, `error` y `traza`, donde `status` será `ok`, `error` o `blocked`, `error` será `str | None` y `traza` será un evento con `ts`, `origen`, `nombre`, `args`, `status` y `preview` de hasta 200 caracteres, según el contrato vigente del agente.
- RF-2: SI una herramienta falla después de que sus argumentos hayan superado la validación, ENTONCES EL SISTEMA devolverá `status=error`, `data=None` y un campo `error` que explique el fallo, sin propagar una excepción al agente.
- RF-3: CUANDO se invoque una herramienta, EL SISTEMA dejará una traza visible de la invocación en el registro y en el panel de depuración de Streamlit.
- RF-22: SI el agente solicita una herramienta que no figura en el registro de herramientas disponibles, ENTONCES EL SISTEMA devolverá un resultado con estado `blocked`.

### B. Consulta de hora actual
- RF-4: CUANDO el agente solicite la hora actual, EL SISTEMA devolverá en `data` los campos `hora_madrid` en formato `HH:MM` y `estado_parque` como texto, según el contrato vigente del agente.
- RF-5: SI EL SISTEMA no puede obtener la hora actual, ENTONCES devolverá un resultado con estado `error`, sin una fecha y hora como dato válido.

### C. Consultas meteorológicas
- RF-6: CUANDO el agente solicite información meteorológica, EL SISTEMA devolverá en `data` un diccionario con los campos `observaciones`, `previsiones`, `avisos` y `origen`.
- RF-7: CUANDO la respuesta de AEMET permita devolver observaciones meteorológicas, EL SISTEMA devolverá esas observaciones en `data.observaciones` e indicará `aemet` en `data.origen`.
- RF-8: SI la respuesta de AEMET no permite devolver observaciones meteorológicas y la alternativa local sí permite devolverlas, ENTONCES EL SISTEMA devolverá las observaciones locales en `data.observaciones` e indicará `respaldo` en `data.origen`.
- RF-9: SI ni la respuesta de AEMET ni la alternativa local permiten devolver observaciones meteorológicas, ENTONCES EL SISTEMA devolverá un resultado con estado `error`, `None` en `data.observaciones`, `data.previsiones` y `data.avisos`, e indicará `respaldo` en `data.origen`, sin intentar obtener previsiones ni avisos.
- RF-10: SI hay observaciones disponibles pero la respuesta de previsiones no contiene una lista no vacía cuyo primer elemento sea un diccionario, ENTONCES EL SISTEMA devolverá `None` en `data.previsiones`.
- RF-11: SI hay observaciones disponibles pero la respuesta de avisos no contiene una lista no vacía cuyo primer elemento sea un diccionario, ENTONCES EL SISTEMA devolverá `None` en `data.avisos`.
- RF-12: CUANDO haya observaciones disponibles procedentes de AEMET o de la alternativa local, EL SISTEMA devolverá el resultado meteorológico con estado `ok`, aunque las previsiones o los avisos sean `None`.
- RF-13: SI no se pueden recuperar observaciones ni de AEMET ni de la alternativa local, ENTONCES EL SISTEMA no intentará obtener previsiones ni avisos y devolverá `None` en `data.observaciones`, `data.previsiones` y `data.avisos`, e indicará `respaldo` en `data.origen`.

### D. Descripción de imágenes
- RF-14: CUANDO el agente aporte una imagen válida, EL SISTEMA devolverá una descripción textual en español de su contenido.
- RF-15: SI el agente no aporta un diccionario de imagen con `imagen_bytes` de tipo `bytes` y no vacío, y `mime` igual a `image/png` o `image/jpeg`, ENTONCES EL SISTEMA utilizará una imagen de respaldo almacenada en el proyecto, que se considera válida, para generar la descripción.
- RF-16: SI el servicio de descripción falla al procesar la imagen seleccionada (la aportada válida o la de respaldo) o no puede leerla, ENTONCES EL SISTEMA devolverá un resultado con estado `error` y `data` igual a `None`, conforme a RF-2, sin intentar otro fallback.
- RF-17: SI el servicio de descripción devuelve una respuesta vacía, ENTONCES EL SISTEMA devolverá un resultado con estado `error` y `data` igual a `None`, conforme a RF-2.
- RF-23: SI no se puede obtener la imagen de respaldo durante el fallback por argumentos inválidos, ENTONCES EL SISTEMA devolverá un resultado con estado `error` y `data` igual a `None` sin propagar una excepción al agente.

### E. Consultas mediante RAG
- RF-18: CUANDO el agente aporte una pregunta no vacía, EL SISTEMA devolverá en `data` los campos `respuesta`, `fuentes`, `citas`, `abstuvo` y `motivo_abstencion`, sin incluir los fragmentos recuperados, según el contrato vigente del agente.
- RF-19: SI el agente no aporta una pregunta o esta queda vacía al retirar los espacios en blanco, ENTONCES EL SISTEMA devolverá un resultado con estado `error`.
- RF-20: CUANDO el componente externo de consulta RAG devuelva una abstención, EL SISTEMA devolverá en `data` el estado de abstención, el mensaje, las fuentes, las citas y el motivo recibidos, sin que la herramienta decida si debe abstenerse.
- RF-21: SI falla la recuperación o la generación de una respuesta, ENTONCES EL SISTEMA devolverá un resultado con estado `error` sin propagar una excepción al agente.

## Requisitos no funcionales
No se establecen requisitos no funcionales adicionales a los requisitos comunes de resultado, tratamiento de errores y trazabilidad de RF-1 a RF-3.

## Casos límite
- No se puede obtener la hora: resultado de error sin fecha y hora válida (RF-5).
- La herramienta solicitada no figura en el registro de herramientas disponibles: resultado con estado `blocked` (RF-22).
- La respuesta de AEMET se considera inválida cuando no permite devolver observaciones; se usan las observaciones locales si están disponibles y, si tampoco se pueden devolver observaciones locales, el estado global es `error` y `data.origen` es `respaldo` (RF-8, RF-9, RF-13).
- Hay observaciones disponibles, pero la respuesta de previsiones o avisos no contiene una lista no vacía cuyo primer elemento sea un diccionario: se devuelve `None` para esa categoría sin invalidar las observaciones (RF-10 a RF-12).
- No se pueden recuperar observaciones ni de AEMET ni de la alternativa local: no se intentan obtener previsiones ni avisos; las tres categorías son `None`, `data.origen` es `respaldo` y el estado global es `error` (RF-9, RF-13).
- No se recibe un diccionario de imagen, `imagen_bytes` no es de tipo `bytes`, está vacío o `mime` no es `image/png` ni `image/jpeg`: se intenta obtener una imagen de respaldo y, si se obtiene, continúa la generación de la descripción (RF-15).
- La imagen de respaldo se considera válida; si no se puede obtener durante el fallback por argumentos inválidos, se devuelve `status=error` y `data=None` sin propagar la excepción al agente (RF-15, RF-23).
- Cualquier llamada a una herramienta que falle después de superar la validación de argumentos devuelve `status=error`, `data=None` y un campo `error` que explica el fallo (RF-2).
- El servicio de descripción falla al procesar la imagen seleccionada (la aportada válida o la de respaldo), no puede leerla o devuelve una respuesta vacía: el resultado tiene estado `error` y `data` igual a `None`, sin intentar otro fallback (RF-16, RF-17).
- No se aporta una pregunta RAG o solo contiene espacios en blanco: se devuelve un error (RF-19).
- La herramienta devuelve la abstención que reciba del componente externo de consulta RAG y no decide si corresponde abstenerse (RF-18, RF-20).
- El resultado RAG devuelve en `data` respuesta, fuentes, citas y estado de abstención, sin exponer los fragmentos recuperados (RF-18, RF-20).

## Fuera de alcance
- Decidir cuándo debe invocar el agente cada herramienta o cómo coordina varias invocaciones.
- Cambiar el comportamiento general de las interfaces CLI y Streamlit, salvo la visibilidad de las trazas definida en RF-3.
- Cambiar el contrato general del sistema RAG documentado en la spec base.
- Definir cómo se incorporan o eliminan herramientas del registro de herramientas disponibles.
- Proporcionar alternativas locales para predicciones o avisos meteorológicos.
- Definir los servicios externos, credenciales o detalles técnicos con los que se ejecutan las herramientas.
- Definir un fallback local para RAG; esta especificación se aprueba bajo el supuesto de que RAG no falla. Si se requiere ese fallback, deberá definirse en la spec 000-base-rag.

## Criterios de finalización
- Cada requisito funcional tiene una prueba que verifica su resultado observable y los casos de error aplicables.
- La suite de pruebas del proyecto termina sin fallos.

## Dudas abiertas
- [NECESITA ACLARACIÓN] RF-2 y RF-19: ¿qué valores deben llevar `data` y `error` cuando los argumentos no superan la validación?
- [NECESITA ACLARACIÓN] RF-20: ¿qué estado (`ok` o `error`) corresponde al resultado cuando el componente RAG devuelve una abstención?
- [NECESITA ACLARACIÓN] RF-22: ¿qué valores deben llevar `data` y `error` cuando se solicita una herramienta que no está en el registro?
