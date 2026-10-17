# Spec 004 — CLI e interacción humana

## 1. Objetivo

Implementar una interfaz de línea de comandos (CLI) para interactuar con el agente multiagente del Parque del Retiro, visualizar su actividad y gestionar manualmente la aprobación o el rechazo de los planes propuestos.

La CLI será un cliente del núcleo del agente. Deberá respetar las funciones públicas y el formato de respuesta definidos en `docs/contrato.md`, sin duplicar la lógica de LangGraph.

## 2. Contexto

El núcleo del agente se encuentra en `src/agent.py` y expone dos funciones públicas:

- `procesar_turno(texto, thread_id, imagen=None)`
- `aprobar_plan(thread_id, aprobado, comentario="")`

La primera procesa una petición y devuelve la respuesta, el plan, el estado de aprobación, la traza y cualquier error relevante. La segunda registra una decisión humana y reanuda el grafo cuando existe un plan pendiente.

El núcleo es responsable del estado, la persistencia, los límites de ejecución, la validación del plan y la interrupción HITL. La CLI recibe entradas, invoca la API pública, muestra los resultados y solicita decisiones al usuario.

La guía del proyecto exige tanto una demo como un modo interactivo en el que la aprobación y el rechazo se realicen manualmente.

## 3. Alcance

Este bloque incluye:

- Creación del punto de entrada `main_agent.py`.
- Modo demo para demostrar el funcionamiento del agente.
- Modo interactivo para mantener una conversación.
- Visualización de respuestas, planes, pasos y eventos de traza.
- Opciones manuales para aprobar o rechazar planes.
- Continuación de la conversación tras el rechazo.
- Reutilización de `thread_id` durante una conversación.
- Inicio de una conversación nueva con un identificador diferente.
- Gestión de entradas no válidas.
- Tratamiento de errores y salida controlada.

Quedan fuera la implementación del grafo, las herramientas y la interfaz visual de Streamlit.

La CLI no implementará nodos, rutas, checkpointers ni reglas de decisión propias. Todas las operaciones del agente se realizarán a través de la API pública.

## 4. Archivos afectados

- `main_agent.py`: punto de entrada y lógica de presentación de la CLI.
- `src/agent.py`: API pública que consume la CLI.
- `src/graph.py`: implementación interna de la interrupción y reanudación, sin que la CLI acceda directamente a ella.
- `docs/contrato.md`: contrato que determina las interfaces disponibles.
- `requirements.txt`: dependencias necesarias para ejecutar el proyecto.
- `tests/`: pruebas de los modos demo e interactivo y de sus flujos de decisión.

La demo se coordinará desde `main_agent.py`. No se requiere añadir una función pública `run_demo(...)` a `src/agent.py`, ya que el contrato vigente define únicamente `procesar_turno(...)` y `aprobar_plan(...)`.

## 5. Requisitos funcionales

### RF-01. Punto de entrada

El usuario debe poder iniciar el modo interactivo mediante:

`python main_agent.py`

La lógica de negocio y la construcción del grafo no se implementarán en este archivo.

La CLI podrá admitir argumentos para seleccionar el modo de ejecución, siempre que se conserve el inicio interactivo por defecto.

### RF-02. Modo demo

La CLI debe ofrecer un modo demo reproducible que permita mostrar el recorrido del agente de principio a fin.

La demo deberá mostrar, cuando corresponda:

- La petición inicial.
- Los especialistas que intervienen.
- Los resultados relevantes de los especialistas y herramientas.
- La respuesta sintetizada.
- El plan generado.
- La pausa antes de aplicar el plan.
- La decisión de aprobación o rechazo.
- El resultado posterior a esa decisión.

La demo podrá incluir una aprobación automática opcional si se identifica claramente como modo demostrativo y separado del modo interactivo. En ese caso, la aprobación deberá ejecutarse invocando `aprobar_plan(...)`; nunca se podrá saltar la interrupción HITL ni modificar directamente el estado interno del grafo.

El modo interactivo no podrá aprobar automáticamente.

Si la demo necesita mostrar un recorrido sin depender de servicios externos, podrá utilizar dependencias simuladas en las pruebas o en un escenario de demostración controlado. La demo normal del proyecto deberá dejar claras las limitaciones si las herramientas reales no están disponibles.

La demo no deberá declarar que una aplicación ha terminado correctamente si la respuesta pública indica un error o si `done` sigue siendo `False`.

### RF-03. Modo interactivo

El modo interactivo permitirá introducir peticiones sucesivas y recibir los resultados del agente.

La CLI mantendrá el mismo `thread_id` durante la conversación activa. Ese identificador se pasará a todas las llamadas de `procesar_turno(...)` y `aprobar_plan(...)` correspondientes a dicha conversación.

El usuario deberá poder salir de forma explícita y controlada.

La CLI deberá permitir iniciar una conversación nueva. Al hacerlo, generará un identificador diferente, preferiblemente mediante UUID4 convertido a cadena, sin mezclar el estado de la conversación anterior con el nuevo hilo.

Si hay un plan pendiente, la CLI deberá solicitar que se apruebe o rechace antes de permitir el envío de otra petición al mismo hilo. Si el usuario no quiere tomar una decisión en ese momento, podrá salir de forma controlada sin afirmar que el plan se ha aplicado.

### RF-04. Visualización del proceso

La CLI mostrará de forma legible:

- La respuesta devuelta por el agente.
- El plan propuesto, si existe.
- Los especialistas utilizados, cuando la traza lo permita.
- Las herramientas ejecutadas y sus estados.
- Los errores y limitaciones importantes.
- Si el turno está pendiente de aprobación.
- Si el agente ha completado correctamente la aplicación.
- La información de trazabilidad útil para comprender el recorrido.

La traza se leerá del campo `traza` devuelto por la API pública. La CLI no reconstruirá la traza consultando el estado interno de LangGraph.

Cada evento contiene `ts`, `origen`, `nombre`, `args`, `status` y `preview`. La CLI deberá mostrar un resumen legible y evitar imprimir datos sensibles o información innecesaria.

No será obligatorio imprimir todo el estado interno del grafo ni todos los argumentos de las herramientas. La visualización deberá ser suficiente para demostrar el funcionamiento multiagente y las decisiones HITL.

### RF-05. Aprobación manual

Cuando el resultado indique `pendiente_aprobacion=True`, la CLI informará de que existe un plan pendiente y solicitará una decisión explícita.

La CLI ofrecerá la opción de aprobar el plan y, si el usuario la selecciona, invocará:

`aprobar_plan(thread_id, True, comentario)`

El núcleo será responsable de registrar la decisión, reanudar el grafo y determinar si la aplicación ha concluido correctamente.

La CLI mostrará el resultado devuelto por el núcleo. No establecerá por su cuenta `done=True`, no eliminará la interrupción ni ejecutará directamente el nodo `aplicar`.

La aprobación automática solo podrá existir en el modo demo expresamente identificado; nunca en el modo interactivo.

### RF-06. Rechazo manual

La CLI ofrecerá una opción para rechazar el plan pendiente. La decisión se comunicará al núcleo mediante:

`aprobar_plan(thread_id, False, comentario)`

Al rechazarlo:

- El plan rechazado no deberá aplicarse.
- `done` deberá permanecer en `False`.
- El resultado público indicará que ya no existe una pausa pendiente si el rechazo se ha procesado correctamente.
- La CLI mostrará que el plan ha sido rechazado.
- El usuario podrá introducir nuevas instrucciones en el mismo hilo o iniciar una conversación nueva.

La limpieza del pedido, las notas, la respuesta y el plan corresponde al núcleo y deberá respetar `docs/contrato.md`.

La CLI no modificará directamente el estado del grafo para implementar el rechazo.

### RF-07. Persistencia de conversación

La CLI utilizará un `thread_id` estable durante la conversación activa.

Las peticiones sucesivas y las decisiones HITL de esa conversación reutilizarán el mismo identificador.

Cuando se inicie una conversación nueva, la CLI generará un identificador diferente.

La persistencia garantizada por este requisito es la proporcionada por el checkpointer durante la ejecución del proceso. No se presupone que `MemorySaver` conserve el estado después de cerrar y volver a iniciar el programa.

La CLI no almacenará ni combinará manualmente los estados internos del grafo.

### RF-08. Entradas no válidas

La CLI gestionará entradas incorrectas, incluidas:

- Opciones de menú no reconocidas.
- Decisiones de aprobación distintas de las opciones admitidas.
- Peticiones vacías.
- Intentos de enviar una petición cuando todavía hay un plan pendiente.
- Errores recuperables de entrada o interrupciones del usuario.

Una decisión no válida no deberá invocar `aprobar_plan(...)`, reanudar el grafo ni provocar una aplicación accidental.

Cuando la API pública devuelva un error, la CLI mostrará un mensaje comprensible y permitirá corregir la entrada o salir de forma controlada.

### RF-09. Errores de ejecución

Si falla el LLM, una herramienta o el grafo, la CLI deberá mostrar un mensaje comprensible utilizando la información pública disponible.

La CLI no mostrará claves de API, variables de entorno sensibles ni secretos.

Un error no deberá presentarse como una aplicación completada. La CLI deberá respetar los valores `error`, `pendiente_aprobacion` y `done` devueltos por el núcleo.

Cuando sea posible continuar de forma segura, el programa permitirá que el usuario vuelva a intentarlo o inicie otra conversación. Si no es posible continuar, deberá permitir salir sin dejar una decisión HITL ficticia.

### RF-10. Separación de responsabilidades

`main_agent.py` se limitará a:

- Interpretar el modo de ejecución.
- Recibir las entradas del usuario.
- Crear y conservar el `thread_id` de la conversación activa.
- Invocar `procesar_turno(...)` y `aprobar_plan(...)`.
- Mostrar respuestas, planes, errores y trazas.
- Recoger la decisión humana.
- Coordinar el escenario de demo.

La lógica de orquestación, el estado, los límites, la síntesis, la persistencia y la gestión de HITL permanecerán en el núcleo del agente.

La CLI no importará ni ejecutará directamente nodos internos del grafo para gestionar una conversación normal.

## 6. Requisitos no funcionales

- **Usabilidad:** mensajes claros en español y opciones comprensibles.
- **Modularidad:** no duplicar la lógica de LangGraph.
- **Robustez:** gestionar entradas incorrectas y errores recuperables.
- **Seguridad:** no aprobar automáticamente en modo interactivo ni exponer secretos.
- **Demostrabilidad:** el flujo deberá poder mostrarse en una presentación con resultados y decisiones visibles.
- **Compatibilidad:** utilizar exclusivamente las funciones públicas y la estructura de resultado definidas en `docs/contrato.md`.

## 7. Criterios de aceptación

- **CA-01:** ejecutar `python main_agent.py` inicia el modo interactivo.
- **CA-02:** existe un modo demo que muestra la petición, los resultados relevantes, el plan y la decisión HITL.
- **CA-03:** el modo interactivo permite introducir varias peticiones en una conversación.
- **CA-04:** la CLI muestra el plan y espera una decisión humana cuando `pendiente_aprobacion=True`.
- **CA-05:** al aprobar, la CLI invoca la API pública y muestra el resultado real de la aplicación.
- **CA-06:** al rechazar, el plan no se aplica y el usuario puede continuar con nuevas instrucciones.
- **CA-07:** la conversación activa reutiliza el mismo `thread_id`.
- **CA-08:** iniciar una conversación nueva genera un `thread_id` diferente.
- **CA-09:** una opción no válida no provoca la aplicación del plan ni termina inesperadamente el programa.
- **CA-10:** los errores se muestran de forma comprensible y no exponen secretos.
- **CA-11:** la CLI consume las funciones públicas del agente y no implementa su propia lógica de grafo.
- **CA-12:** el modo interactivo no tiene ningún camino de aprobación automática.
- **CA-13:** la CLI muestra los eventos relevantes de la traza que devuelve el agente.
- **CA-14:** si el núcleo devuelve `plan=[]` y `pendiente_aprobacion=False`, la CLI no solicita una aprobación innecesaria.

## 8. Pruebas previstas

- Prueba de inicio de la CLI.
- Prueba del modo demo.
- Prueba del modo interactivo con varias peticiones.
- Prueba de aprobación y reanudación del grafo.
- Prueba de rechazo y continuación con otro mensaje.
- Prueba de reutilización y renovación de `thread_id`.
- Prueba de entradas no válidas.
- Prueba de errores del agente y salida controlada.
- Prueba que confirme que no se aprueba automáticamente en el modo interactivo.
- Prueba de visualización de la traza del agente.
- Prueba de que no se solicita aprobación cuando no existe un plan pendiente.

Cuando sea posible, las pruebas simularán las respuestas del agente para evitar depender de llamadas reales al LLM o a servicios externos.

## 9. Dependencias y decisiones de integración

- Las firmas de `procesar_turno(...)` y `aprobar_plan(...)` son las definidas en `docs/contrato.md`.
- No se exige `run_demo(...)` como función pública de `src/agent.py`; la demo se coordina desde `main_agent.py`.
- El estado de aprobación se determina mediante `pendiente_aprobacion`, no deduciendo la pausa únicamente a partir del texto de la respuesta.
- El resultado de una aprobación se determina mediante los campos devueltos por el núcleo, especialmente `done`, `pendiente_aprobacion` y `error`.
- La traza se consume desde el campo `traza` de la respuesta pública.
- La CLI no accede directamente al estado interno ni al checkpointer del grafo para gestionar el flujo normal.
- Los cambios en las firmas públicas o en la estructura de respuesta requerirán actualizar primero `docs/contrato.md` y coordinar el cambio con el equipo.

## 10. Definición de terminado

La CLI se considerará implementada cuando:

- El modo interactivo y el modo demo se puedan ejecutar.
- La CLI muestre la respuesta, el plan y la traza de forma comprensible.
- La aprobación y el rechazo manuales funcionen mediante la API pública.
- El hilo se conserve durante una conversación y se pueda iniciar una conversación nueva.
- Las entradas no válidas y los errores se gestionen de forma controlada.
- No exista aprobación automática en el modo interactivo.
- Las pruebas de aceptación pasen y la CLI no duplique la lógica de orquestación del núcleo.
