# Plan técnico — Spec 001

> Basado en `spec.md` (estado: Aprobada). No añade comportamiento que no esté en la spec.

## Archivos afectados

| Archivo | Crear / Modificar | Qué cambia | RF |
|---|---|---|---|
| `config.py` | Modificar | Centralizar la configuración necesaria para las consultas AEMET de observación, previsión y avisos, la ruta del fallback, la zona/offset requerido y los timeouts. Mantener las constantes existentes y no modificar el saludo. | RF-1, RF-2, RF-3, NFR |
| `src/tools/__init__.py` | Crear | Exponer el paquete de tools para que la herramienta meteorológica pueda importarse desde el agente. | RF-1–RF-7 |
| `src/tools/aemet.py` | Crear | Implementar la lógica meteorológica y exponerla como tool de LangChain: validar la hora recibida, consultar AEMET, cargar y validar la observación local cuando corresponda, normalizar la respuesta, devolver estado homogéneo y dejar traza. Mantener la lógica de consulta separada del adaptador LangChain para probarla sin red ni invocaciones del modelo. | RF-1–RF-7 |
| `src/tools/fallback/aemet.json` | Mantener | Leer como fuente local de respaldo de observación. Validar los campos requeridos al cargar; no usarlo para completar previsión ni avisos. La procedencia comunicada debe identificar el respaldo local, aunque el JSON conserve el campo `fuente` existente. | RF-3–RF-5 |
| `tests/test_aemet_tool.py` | Crear | Cubrir la tool con sesión HTTP simulada, credenciales inyectadas y fixture JSON local; sin red ni llamadas reales a AEMET. | RF-1–RF-7 |

## Contrato

La tool de LangChain recibirá la hora producida por `hora_actual` como dato opcional (`hora_actual` ISO 8601 con offset UTC+01:00). La tool no implementará ni invocará esa herramienta: cuando no haya hora, devolverá solo la observación, conforme a RF-2. La lógica interna resolverá credenciales desde la configuración existente; las pruebas inyectarán credencial y sesión HTTP simuladas directamente en esa lógica, no como argumentos visibles para el agente.

La salida será un diccionario con estado `ok`, `error` o `blocked`, datos meteorológicos parciales o completos, mensajes en español y una traza identificable. `observacion` podrá proceder de AEMET o del JSON local; `prevision` y `avisos` solo contendrán datos AEMET válidos. Cuando esos datos no estén disponibles, se explicará su ausencia sin inventarlos. El estado `blocked` queda disponible para una solicitud que no pueda ejecutarse; los fallos de servicios o de lectura/validación de datos se representarán como `error`, sin propagar excepciones.

Ejemplo de salida parcial con fallback:

```json
{
  "status": "ok",
  "data": {
    "observacion": {
      "estacion": "MADRID RETIRO",
      "hora_utc": "2026-10-18T09:00:00+0000",
      "temperatura_c": 11.1,
      "fuente": "Respaldo local: src/tools/fallback/aemet.json"
    },
    "prevision": null,
    "avisos": null
  },
  "message": "Observación obtenida del respaldo local. No se pudo obtener la previsión ni los avisos de AEMET.",
  "trace": {
    "tool": "aemet",
    "status": "ok",
    "source": "local"
  }
}
```

Los datos del ejemplo ilustran la forma de salida, no constituyen valores por defecto. Los campos concretos de observación, previsión y avisos se limitarán a los datos válidos que proporcionen sus fuentes.

## Lógica clave

```text
validar solicitud y hora opcional
si hora inválida o con offset distinto de UTC+01:00:
    cargar y validar observación local
    devolver observación local, ausencia de previsión/avisos y motivo de hora
siempre intentar obtener observación AEMET
si hay hora válida:
    intentar obtener previsión y avisos AEMET desde esa hora hasta fin del día
si algún dato AEMET está ausente o inválido:
    conservar los datos AEMET válidos
    si falta la observación, intentar cargar la observación local
    indicar explícitamente los datos que no se pudieron obtener
validar que la observación local tenga estructura y valores válidos antes de usarla
si no hay ningún dato válido:
    devolver error sin inventar datos
registrar y devolver resultado con estado, mensaje, datos y traza
```

## Decisiones técnicas

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Mantener la tool meteorológica en un módulo nuevo y separado de `src/contexto_visita.py`. | Reutilizar o sustituir la ruta meteorológica del saludo contextual. | La spec limita la tool a los agentes y declara fuera de alcance cambiar el saludo; el módulo separado evita alterar ese comportamiento. |
| Exponer una tool de LangChain delgada sobre una función de consulta testeable sin modelo. | Hacer que la capa de consultas dependa directamente de la interfaz de invocación del agente. | Permite su uso futuro por el agente LangGraph y mantiene los tests deterministas y sin llamadas al modelo. |
| Inyectar la sesión HTTP, la credencial de prueba y el dato opcional `hora_actual` en la función de consulta. | Hacer llamadas de red y resolver toda dependencia dentro de una función no sustituible. | Permite probar los flujos AEMET sin red ni consumo de API y deja explícita la dependencia futura de `hora_actual`. |
| Leer el fallback del archivo existente, validar sus datos y marcar la procedencia como local en la salida. | Confiar en el JSON sin validación o presentar su valor `fuente` como si la observación acabara de consultarse a AEMET. | La spec prohíbe datos inventados y exige indicar que se usó el respaldo local. |
| Devolver datos parciales válidos y describir cada dato no disponible en `message`; reservar `error` para el caso sin datos válidos o un fallo que impida completar la consulta. | Descartar toda la respuesta si falla cualquiera de las consultas. | RF-3 requiere conservar los datos válidos cuando AEMET solo entrega parte de lo pedido. |
| Usar los endpoints/recursos AEMET y parseadores por tipo de dato, con configuración centralizada en `config.py`. | Codificar URLs, identificadores o timeouts dentro de la tool. | Sigue la constitución sobre configuración y mantiene separados observación, previsión y avisos; los endpoints concretos deberán verificarse con la documentación de AEMET antes de implementar. |
| Mantener el offset exigido por la spec como UTC+01:00 y rechazar como hora no válida cualquier valor con offset diferente. | Convertir automáticamente desde cualquier zona o aplicar `Europe/Madrid` con horario de verano. | La decisión aclarada para RF-2 especifica UTC+1. La implementación no debe sustituir ese requisito por una interpretación distinta. |
| Escribir trazas mediante el mecanismo estándar de logging y devolver su resumen en el resultado. | Usar `print` como única evidencia o depender de una interfaz todavía inexistente. | La salida estructurada permite al futuro agente y a su panel de depuración consumir la traza; no acopla la tool a Streamlit. |

## Estrategia de tests

Todos los tests sustituirán red y credenciales: sesión falsa compatible con `get`, respuestas HTTP/JSON controladas, credencial de prueba inyectada y archivo JSON temporal o fixture. Ningún test llamará a AEMET.

- **RF-1:** comprobar solicitud de observación de la estación 3195 y extracción de los campos meteorológicos; doble HTTP de los dos pasos de AEMET.
- **RF-2:** comprobar consulta de previsión y avisos desde una hora ISO válida con offset UTC+01:00 hasta el final del día; comprobar que hora ausente limita la respuesta a observación y que hora inválida selecciona fallback, indica el motivo y omite previsión/avisos.
- **RF-3:** simular falta de credenciales, error HTTP, JSON inválido, observación ausente y respuesta parcial; verificar uso del JSON solo para observación y conservación de los datos AEMET válidos.
- **RF-4:** probar fallback ausente, JSON ilegible, estructura inválida y datos sin valores utilizables; comprobar resultado de error, mensajes explícitos y ausencia de datos meteorológicos fabricados.
- **RF-5:** verificar origen local en la respuesta cuando se usa fallback, presencia de fecha/hora de referencia si el JSON la contiene y omisión de esos metadatos si no están disponibles.
- **RF-6:** verificar forma homogénea de salida y estados `ok` y `error`; comprobar que errores inesperados no escapan de la tool. Probar `blocked` solo si el contrato de entrada aprobado define una solicitud bloqueable; el adaptador LangChain debe exponer el resultado de consulta sin convertir errores en respuestas meteorológicas exitosas.
- **RF-7:** capturar el logger para confirmar una traza por solicitud con estado y procedencia, y comprobar que el resultado contiene el resumen de traza.
- **Requisito no funcional de timeout:** comprobar que cada llamada HTTP simulada recibe el timeout configurado, sin esperar realmente.

No se requieren comprobaciones manuales ni llamadas reales a la API.

## Riesgos

- La spec no concreta los endpoints ni la estructura de respuesta AEMET para previsión y avisos. Antes de implementar habrá que contrastar esos detalles con la documentación del servicio; no se deben usar llamadas reales durante tests.
- `src/tools/fallback/aemet.json` contiene un campo `fuente` que identifica AEMET, pero el dato leído desde ese archivo debe presentarse como respaldo local para satisfacer RF-5.
- La spec no fija vigencia máxima para la observación local. El plan no añade un umbral de caducidad: solo comunicará fecha y hora de referencia cuando existan y no describirá el dato como actual si su contenido no lo acredita.
- `hora_actual` pertenece a una spec futura. Hasta que se integre, el contrato admite su ausencia y la tool devuelve solo observación.
- La constitución pide traza en el log y panel de depuración de Streamlit, pero la spec limita esta tool a agentes y el código actual no tiene dicho panel. Esta entrega deja una traza estructurada y registrable; su visualización en el panel se integrará cuando exista la interfaz del agente, sin modificar ahora el saludo ni la UI actual.
- Los valores y cobertura de avisos aplicables al Retiro deben derivarse de los recursos AEMET configurados y confirmarse durante implementación para evitar presentar avisos de una zona incorrecta.

## Trazabilidad

| RF | Parte del plan | Test |
|---|---|---|
| RF-1 | `src/tools/aemet.py`: consulta y parseo de observación | `tests/test_aemet_tool.py::test_obtiene_observacion_de_estacion_retiro` |
| RF-2 | Contrato y lógica opcional de `hora_actual`; consultas de previsión/avisos | `tests/test_aemet_tool.py::test_consulta_prevision_y_avisos_con_hora_valida`, `test_hora_ausente_devuelve_solo_observacion`, `test_hora_invalida_usa_fallback` |
| RF-3 | Fallback de observación y conservación de datos parciales | `tests/test_aemet_tool.py::test_fallo_aemet_usa_observacion_local`, `test_respuesta_parcial_conserva_datos_validos` |
| RF-4 | Validación de respuesta AEMET y JSON local; salida de error sin invención | `tests/test_aemet_tool.py::test_sin_datos_validos_devuelve_error`, `test_fallback_invalido_no_inventa_datos` |
| RF-5 | Procedencia y metadatos temporales del fallback | `tests/test_aemet_tool.py::test_fallback_indica_fuente_local_y_referencia`, `test_fallback_sin_referencia_omite_metadatos` |
| RF-6 | Contrato homogéneo y conversión de errores a resultado | `tests/test_aemet_tool.py::test_resultado_tiene_estado_y_campos_homogeneos`, `test_error_inesperado_no_se_propaga` |
| RF-7 | Registro de ejecución y traza estructurada | `tests/test_aemet_tool.py::test_cada_solicitud_deja_traza_visible` |
