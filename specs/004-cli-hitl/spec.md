
# Spec 004 — CLI e interacción humana

## 1. Objetivo

Implementar una interfaz de línea de comandos (CLI) que permita interactuar con el agente multiagente del Parque del Retiro, visualizar su actividad y gestionar manualmente la aprobación o el rechazo de los planes propuestos.

La CLI debe actuar como cliente del núcleo del agente. No debe contener la lógica interna del grafo.

## 2. Contexto

La aplicación utilizará las funciones públicas definidas en `src/agent.py`.

El núcleo del agente es responsable de la orquestación, el estado, la persistencia, los límites de ejecución y la interrupción HITL. La CLI se encargará de recibir las instrucciones del usuario, mostrar los resultados y recoger sus decisiones.

El flujo interactivo debe requerir una decisión humana explícita antes de aplicar un plan.

## 3. Alcance

Incluye:

- Creación del punto de entrada `main_agent.py`.
- Modo demo para demostrar el funcionamiento del agente.
- Modo interactivo para mantener una conversación.
- Visualización de respuestas, pasos ejecutados y planes pendientes.
- Opciones manuales para aprobar o rechazar.
- Continuación de la conversación tras el rechazo.
- Reutilización de `thread_id` durante la misma conversación.
- Inicio de una conversación nueva con un identificador diferente.
- Tratamiento básico de errores y salida controlada.

Quedan fuera la implementación del grafo, las herramientas y la interfaz de Streamlit.

## 4. Archivos afectados

- `main_agent.py`: punto de entrada de la CLI.
- `src/agent.py`: interfaz pública que consume la CLI.
- `src/graph.py`: mecanismo de interrupción y reanudación que utiliza la CLI.
- `requirements.txt`: dependencias necesarias para ejecutar el agente.

## 5. Requisitos funcionales

### RF-01. Punto de entrada

El usuario debe poder iniciar la CLI ejecutando:

`python main_agent.py`

La lógica de negocio y la construcción del grafo no deben implementarse en este archivo.

### RF-02. Modo demo

La CLI debe ofrecer un modo demo que ejecute un escenario reproducible y muestre:

- La petición inicial.
- Los especialistas que intervienen.
- Los resultados relevantes.
- El plan generado.
- La pausa antes de la aplicación.
- El resultado de la decisión humana.

La demo podrá incluir una aprobación automática únicamente si se trata de un modo expresamente identificado y separado del flujo interactivo. La ejecución normal no debe aprobar planes automáticamente.

### RF-03. Modo interactivo

El usuario debe poder introducir peticiones sucesivas y recibir las respuestas del agente.

La CLI debe conservar el mismo `thread_id` durante la conversación activa, para que el núcleo pueda recuperar el estado correspondiente.

Debe existir una forma clara de salir del modo interactivo sin cerrar inesperadamente el programa ni dejar al usuario atrapado en un bucle.

### RF-04. Visualización del proceso

La CLI debe mostrar, de forma legible:

- La respuesta propuesta.
- Los especialistas utilizados, cuando la información esté disponible.
- Los pasos o herramientas relevantes ejecutados.
- Los errores o limitaciones importantes.
- El estado del flujo: en ejecución, pendiente de aprobación o completado.

No es necesario imprimir todo el estado interno de LangGraph; debe mostrarse información útil para comprender y demostrar el funcionamiento.

### RF-05. Aprobación manual

Cuando el agente se detenga antes del nodo `aplicar`, la CLI debe indicar que existe un plan pendiente y solicitar una decisión explícita.

Debe ofrecer una opción para aprobarlo.

Si el usuario aprueba, la CLI invocará `aprobar_plan(...)` o la interfaz pública acordada. El núcleo del agente será responsable de reanudar el grafo y verificar que la aplicación ha concluido correctamente.

La CLI no debe marcar por sí misma `done=True` ni saltarse la interrupción.

### RF-06. Rechazo manual

La CLI debe ofrecer una opción para rechazar el plan.

Al rechazarlo:

- No debe ejecutarse el plan rechazado.
- El flujo no debe marcarse como completado.
- Debe mostrarse un mensaje que explique que el plan ha sido rechazado.
- El usuario debe poder introducir nuevas instrucciones o solicitar una propuesta revisada.

La forma exacta de registrar el rechazo y reanudar el grafo debe ser responsabilidad de `src/agent.py` y `src/graph.py`.

### RF-07. Persistencia de conversación

La CLI debe utilizar un `thread_id` estable durante la conversación actual.

Cuando se inicie una conversación nueva, deberá utilizar un identificador diferente para evitar mezclar estados.

La persistencia garantizada por este requisito es la que ofrece el checkpointer durante la ejecución del proceso. No se presupone que `MemorySaver` conserve los datos después de cerrar y volver a iniciar el programa.

### RF-08. Entradas no válidas

La CLI debe gestionar entradas incorrectas, como una opción de aprobación no reconocida, sin cerrar inesperadamente el programa.

Una decisión no válida no debe reanudar el grafo ni provocar la aplicación accidental del plan.

### RF-09. Errores de ejecución

Si falla el LLM, una herramienta o el grafo, la CLI debe mostrar un mensaje comprensible y permitir salir de forma controlada.

No debe imprimir claves de API, variables de entorno sensibles ni otros secretos.

### RF-10. Separación de responsabilidades

`main_agent.py` debe limitarse a:

- Interpretar el modo de ejecución.
- Recibir las entradas del usuario.
- Invocar las funciones públicas de `src/agent.py`.
- Mostrar los resultados.
- Recoger la decisión humana.

La lógica de orquestación, el estado, el control de límites y la gestión de HITL deben permanecer en el núcleo del agente.

## 6. Requisitos no funcionales

- Usabilidad: mensajes claros en español y opciones comprensibles.
- Modularidad: sin duplicar la lógica de LangGraph.
- Robustez: gestión de entradas incorrectas y errores recuperables.
- Seguridad: nunca aprobar automáticamente en modo interactivo.
- Demostrabilidad: el flujo debe poder mostrarse en una presentación sin depender de acciones ocultas.

## 7. Criterios de aceptación

- **CA-01:** `python main_agent.py` inicia la CLI correctamente.
- **CA-02:** el modo demo muestra un recorrido del agente hasta la pausa HITL.
- **CA-03:** el modo interactivo permite introducir varias peticiones.
- **CA-04:** el agente muestra el plan y espera una decisión humana antes de aplicarlo.
- **CA-05:** al aprobar, el grafo se reanuda y la CLI muestra el resultado de la aplicación.
- **CA-06:** al rechazar, el plan no se aplica y el usuario puede continuar con nuevas instrucciones.
- **CA-07:** la conversación activa reutiliza el mismo `thread_id`.
- **CA-08:** una conversación nueva utiliza un `thread_id` diferente.
- **CA-09:** una opción no válida no provoca la aplicación del plan ni termina inesperadamente el programa.
- **CA-10:** los errores se muestran de forma comprensible y no exponen secretos.
- **CA-11:** la CLI utiliza las funciones públicas del agente y no implementa su propia lógica de grafo.
- **CA-12:** el flujo interactivo no tiene ningún camino de aprobación automática.

## 8. Pruebas previstas

- Prueba de inicio de la CLI.
- Prueba del modo demo.
- Prueba del flujo interactivo con varias peticiones.
- Prueba de aprobación y reanudación del grafo.
- Prueba de rechazo y continuación con otro mensaje.
- Prueba de reutilización y renovación de `thread_id`.
- Prueba de entradas no válidas.
- Prueba de errores del agente y salida controlada.
- Prueba que confirme que no se aprueba automáticamente en modo interactivo.

Cuando sea posible, las pruebas deben simular las respuestas del agente para evitar depender de llamadas reales al LLM.

## 9. Dependencias y decisiones pendientes

- Confirmar las firmas definitivas de `procesar_turno()`, `aprobar_plan()` y `run_demo()`.
- Confirmar cómo se representa un plan pendiente de aprobación en el resultado de `procesar_turno()`.
- Confirmar el mecanismo para rechazar un plan y continuar con nuevas instrucciones.
- Confirmar si el modo demo tendrá un escenario de aprobación y otro de rechazo.
- Confirmar el formato de trazas que proporcionará el núcleo del agente.

## 10. Definición de terminado

La CLI se considera terminada cuando puede ejecutar una demo, mantener una conversación, mostrar un plan pendiente, gestionar la aprobación y el rechazo manuales y continuar la conversación sin duplicar la lógica del grafo.
