# Spec 003 — Núcleo del agente multiagente

## 1. Objetivo

Implementar el núcleo de un agente multiagente para el Parque del Retiro mediante LangGraph. El sistema debe recibir peticiones del usuario, seleccionar los especialistas adecuados, reunir sus resultados, preparar una respuesta y, cuando exista un plan válido, solicitar aprobación humana antes de aplicarlo.

El núcleo debe cumplir el contrato definido en `docs/contrato.md`. Si existe alguna discrepancia entre esta especificación y el contrato, prevalece el contrato.

## 2. Contexto

El proyecto reutiliza el RAG existente del Parque del Retiro. El agente no debe reconstruirlo ni duplicar su lógica, sino invocarlo mediante la interfaz de herramientas acordada con el equipo.

Se definen dos especialistas:

- **Especialista de conocimiento del Retiro (`normas`):** responde sobre lugares, historia, instalaciones, servicios y normas utilizando el RAG.
- **Especialista de planificación de visita (`entorno`):** utiliza herramientas de contexto, hora, información externa e imagen para ayudar a organizar una visita.

Cada especialista tendrá instrucciones propias y solo utilizará las herramientas autorizadas para su función.

La implementación interna de las herramientas pertenece al bloque de trabajo correspondiente. El núcleo debe consumirlas respetando el contrato de `docs/contrato.md`, sin duplicar su funcionalidad.

## 3. Alcance

Este bloque incluye:

- Definición del estado compartido del grafo.
- Construcción y conexión de los nodos de LangGraph.
- Orquestación mediante un supervisor.
- Implementación de los dos especialistas.
- Síntesis de resultados y generación de una respuesta.
- Generación de un plan únicamente cuando haya información suficiente para proponer acciones concretas.
- Persistencia de la conversación mediante `MemorySaver` y `thread_id`.
- Interrupción antes de aplicar un plan válido para solicitar aprobación humana.
- Gestión del rechazo y preparación del hilo para una nueva petición.
- Control de límites de ejecución desde Python.
- Determinación de `done` desde código, nunca exclusivamente desde el LLM.
- Trazabilidad de las decisiones del supervisor, las herramientas y los eventos HITL.
- Exposición de una interfaz pública reutilizable por la CLI y Streamlit.

Quedan fuera de este bloque la implementación interna de las herramientas y la interfaz visual de Streamlit.

La demostración de la CLI se coordinará desde `main_agent.py`; no constituye una tercera función pública obligatoria de `src/agent.py`.

## 4. Archivos afectados

- `src/state.py`: definición del estado compartido.
- `src/graph.py`: construcción, ejecución y compilación del grafo.
- `src/agent.py`: funciones públicas `procesar_turno(...)` y `aprobar_plan(...)`.
- `config.py`: configuración de los límites y demás parámetros del núcleo.
- `requirements.txt`: inclusión de `langgraph` si todavía no está declarado.
- `tests/test_graph.py` y `tests/test_agent.py`: pruebas del núcleo y de su contrato público.

La implementación de la CLI corresponde a `main_agent.py` y se especifica en la Spec 004.

## 5. Requisitos funcionales

### RF-01. Estado compartido

El sistema dispondrá de un estado tipado compartido entre los nodos. Como mínimo, deberá representar:

- Identificador de conversación.
- Historial de mensajes.
- Petición actual.
- Resultados y notas de los especialistas.
- Respuesta sintetizada.
- Plan propuesto.
- Decisión humana, si existe.
- Estado de finalización.
- Contadores de ejecución.
- Trazabilidad de las acciones.
- Imagen opcional.
- Comentario asociado a una decisión humana, si se proporciona.

La implementación actual utiliza `EstadoGrafo` en `src/state.py`, con los campos definidos en el código. Los campos internos podrán ampliarse cuando sea necesario, siempre que se mantenga la compatibilidad con el contrato público.

El historial deberá acumular los mensajes de una conversación mediante el mecanismo de LangGraph establecido en la implementación. El estado de conversación se distinguirá de los datos correspondientes al pedido actual, que pueden reiniciarse tras un rechazo.

Los eventos de traza deberán respetar la estructura definida en la sección 4 de `docs/contrato.md`.

### RF-02. Supervisor

El supervisor seleccionará el siguiente nodo de acuerdo con la petición, los resultados disponibles y los límites de ejecución.

Podrá dirigir el flujo al especialista de conocimiento, al especialista de planificación o a la síntesis. Una petición compleja podrá requerir la intervención de ambos especialistas.

La selección del LLM no será la única fuente de control. Si el LLM falla, devuelve una ruta no válida o no puede utilizarse, Python aplicará una alternativa determinista.

La ruta elegida deberá validarse antes de ejecutar el siguiente nodo. El supervisor no podrá:

- Superar el límite global de iteraciones.
- Enviar una ejecución a un especialista que haya alcanzado su límite.
- Saltarse la síntesis cuando se deba finalizar el procesamiento.
- Aplicar un plan sin una decisión humana explícita.

Cada ejecución del supervisor deberá quedar reflejada en la traza.

### RF-03. Especialistas

Cada especialista tendrá un propósito y unas instrucciones propias.

**Especialista de conocimiento (`normas`):**

- Utilizará la herramienta `rag_ask` mediante la interfaz de herramientas definida en el contrato.
- Enviará el argumento `{"pregunta": str}`.
- Conservará la respuesta y la información disponible sobre fuentes, citas y abstención.
- No presentará como hechos confirmados datos que el RAG no haya podido respaldar.
- Si la herramienta falla o se abstiene, reflejará esa limitación en las notas del especialista.

**Especialista de planificación (`entorno`):**

- Podrá utilizar `api_dominio` y `hora_actual`.
- Podrá utilizar `describir_imagen` cuando el usuario haya proporcionado una imagen válida.
- No inventará información meteorológica, temporal ni visual.
- Distinguirá los resultados obtenidos de las limitaciones y errores de las herramientas.

Las herramientas se ejecutarán mediante la interfaz autorizada del bloque tools. El núcleo registrará los eventos devueltos por ellas y no duplicará su lógica interna.

Cada especialista dispondrá de un prompt específico. Si falla el LLM encargado de elaborar o interpretar una nota, el sistema conservará la información original aprovechable cuando sea posible y reflejará las limitaciones. Un fallo no deberá convertirse en evidencia positiva.

### RF-04. Síntesis y validez del plan

El nodo `sintetizar` integrará las notas de los especialistas y generará una respuesta coherente, diferenciando los datos respaldados, la información contextual y las limitaciones detectadas.

La síntesis podrá utilizar una implementación determinista en Python. No se exige un LLM adicional para este nodo, siempre que el resultado cumpla los criterios de calidad y validez establecidos en esta especificación.

El campo `respuesta` contendrá la respuesta informativa y, cuando proceda, la explicación de la propuesta. El campo `plan` contendrá una lista de cadenas, con una acción concreta por elemento.

Solo podrá generarse un plan aprobable cuando la información disponible permita formular acciones concretas y justificadas por los resultados obtenidos. No se considerarán planes válidos las listas genéricas que se limiten a recomendar revisar información sin proponer acciones concretas.

La síntesis deberá distinguir entre:

- Información aprovechable.
- Información parcial o no verificada.
- Errores de herramientas.
- Abstención del RAG.
- Ausencia de información suficiente para preparar un plan.

Si no existe información suficiente para preparar un plan válido:

- `respuesta` podrá contener una explicación informativa y las limitaciones pertinentes.
- `plan` deberá ser `[]`.
- `done` deberá ser `False`.
- El turno no deberá quedar pendiente de aprobación.
- El grafo deberá terminar sin entrar en la pausa HITL.

La ausencia de un plan aprobable no debe impedir que el agente proporcione una respuesta informativa útil cuando disponga de información respaldada.

La síntesis no podrá marcar `done=True` ni decidir que un plan ha sido aplicado.

### RF-05. Aplicación y aprobación humana (HITL)

El nodo `aplicar` solo podrá ejecutarse cuando exista un plan válido y el usuario haya tomado una decisión humana explícita.

El grafo deberá compilarse con `MemorySaver` y `interrupt_before=["aplicar"]`, o con el mecanismo equivalente acordado en el contrato.

Cuando la síntesis genere un plan válido, el grafo se detendrá antes de `aplicar` y devolverá un resultado con `pendiente_aprobacion=True`.

La pausa se registrará en la traza con origen `hitl` y nombre `pausa`.

La función pública `aprobar_plan(thread_id, aprobado, comentario="")` registrará la decisión y reanudará el grafo correspondiente.

**Aprobación:**

- Se continuará el mismo hilo desde el punto de interrupción.
- El nodo `aplicar` verificará la decisión humana.
- `done` solo podrá pasar a `True` después de que la aplicación concluya correctamente.
- El resultado público deberá indicar `pendiente_aprobacion=False`.
- La traza registrará el evento HITL `aprobar`.

**Rechazo:**

- El plan rechazado no se aplicará.
- `done` permanecerá en `False`.
- Se limpiarán los datos del pedido actual definidos en el contrato: `pedido`, `notas`, `respuesta` y `plan`.
- `aprobado` volverá a `None` para la siguiente petición.
- La conversación y su historial se conservarán.
- El agente permitirá recibir una nueva petición en el mismo `thread_id`.
- La traza registrará el evento HITL `rechazar`.

No se permite la aprobación automática en el flujo interactivo. La CLI podrá disponer de un escenario de demostración con aprobación automática opcional, pero esa decisión deberá realizarse a través de la función pública de aprobación, sin saltarse el mecanismo HITL del núcleo.

### RF-06. Persistencia de la conversación

El grafo utilizará `MemorySaver` o el mecanismo de persistencia establecido en el contrato.

Cada conversación tendrá un `thread_id` estable. Las llamadas posteriores con ese identificador deberán recuperar el estado guardado y continuar el mismo hilo.

Una conversación nueva utilizará un identificador distinto, generado por el cliente, preferiblemente mediante UUID4 convertido a cadena.

La persistencia de `MemorySaver` se limita al proceso en ejecución. No se garantiza que el estado sobreviva al cierre y posterior reinicio de la aplicación.

Las conversaciones con distintos `thread_id` no deberán compartir el historial ni el estado de aprobación.

### RF-07. Límites y finalización

Los límites de ejecución se aplicarán en Python, no mediante instrucciones al LLM.

Se utilizarán los parámetros definidos en `config.py`:

- `MAX_ITER = 6`: número máximo de ejecuciones del nodo supervisor por turno.
- `MAX_STEPS_ESPECIALISTA = 3`: número máximo de ejecuciones permitidas por especialista, salvo que el contrato vigente establezca otros valores.

El supervisor deberá contar sus ejecuciones reales y no podrá superar el límite configurado. Cuando solo quede una ejecución disponible, deberá dirigir el flujo a la síntesis en lugar de iniciar otro ciclo de especialista.

Si se alcanza un límite, el flujo finalizará de manera controlada y la respuesta explicará las limitaciones relevantes.

Al alcanzar un límite no se podrá marcar `done=True` si el plan no ha sido aplicado correctamente. Tampoco se podrá solicitar aprobación de un plan que la síntesis no considere válido.

### RF-08. Interfaz pública

`src/agent.py` expondrá las siguientes funciones públicas, con las firmas definidas en `docs/contrato.md`:

- `procesar_turno(texto: str, thread_id: str, imagen: dict | None = None) -> dict`
- `aprobar_plan(thread_id: str, aprobado: bool, comentario: str = "") -> dict`

Ambas funciones devolverán el mismo conjunto de claves:

- `thread_id`: identificador de la conversación.
- `respuesta`: cadena con la respuesta o `""` si no hay ninguna.
- `plan`: lista de cadenas o `[]` si no hay plan.
- `pendiente_aprobacion`: booleano que indica si el grafo está pausado antes de `aplicar`.
- `done`: booleano que solo será `True` tras una aplicación aprobada y completada correctamente.
- `traza`: lista de eventos de trazabilidad.
- `error`: cadena con el error o `None`.

La imagen opcional deberá respetar el formato `{"bytes": bytes, "mime": str}`. El núcleo la pasará a la herramienta `describir_imagen` según el contrato.

Las funciones públicas no propagarán excepciones al cliente: comunicarán los errores mediante la clave `error` y mantendrán la estructura del resultado.

Si se llama a `procesar_turno` mientras exista un plan pendiente, se devolverá un error sin iniciar otro turno. Si se llama a `aprobar_plan` sin un plan pendiente, se devolverá un error sin reanudar el grafo.

No se añadirá `run_demo(...)` como función pública obligatoria de `src/agent.py`. La demo será responsabilidad de `main_agent.py`, que consumirá las funciones públicas existentes.

La lógica de orquestación no deberá duplicarse en los clientes.

### RF-09. Trazabilidad y errores

Cada evento de traza respetará la estructura del contrato:

`{"ts": str, "origen": "supervisor" | "tool" | "hitl", "nombre": str, "args": dict, "status": str, "preview": str}`

`preview` tendrá un máximo de 200 caracteres.

Para eventos de supervisor, `nombre` identificará la ruta o especialista elegido. Para eventos de herramientas, `nombre` será el nombre de la herramienta ejecutada. Para HITL, `nombre` será uno de estos valores: `pausa`, `aprobar` o `rechazar`.

Los errores de LLM y herramientas se tratarán de forma controlada siempre que sea posible. No se mostrarán claves de API, variables de entorno sensibles ni secretos en la respuesta pública o la traza.

La traza deberá permitir reconstruir el recorrido general del turno y mostrar qué especialistas, herramientas y decisiones intervinieron.

## 6. Requisitos no funcionales

- **Modularidad:** estado, grafo, herramientas e interfaces estarán separados.
- **Reutilización:** el núcleo podrá invocarse sin depender de Streamlit ni de la CLI.
- **Mantenibilidad:** los límites y parámetros relevantes estarán centralizados en la configuración.
- **Seguridad:** solo se ejecutarán herramientas autorizadas y no se aplicarán planes antes de su aprobación.
- **Compatibilidad:** la interfaz pública permanecerá alineada con `docs/contrato.md`.
- **Robustez:** los fallos recuperables no provocarán bucles indefinidos ni resultados que aparenten una ejecución exitosa sin haberlo sido.

## 7. Criterios de aceptación

- **CA-01:** una petición llega al supervisor y se dirige a un especialista o a la síntesis según corresponda.
- **CA-02:** una petición compleja puede utilizar ambos especialistas y combinar sus resultados.
- **CA-03:** si el selector del supervisor falla o devuelve una ruta inválida, el fallback de Python permite continuar de forma controlada.
- **CA-04:** con un plan válido, la síntesis genera una respuesta y un plan concreto y el grafo se pausa antes de `aplicar`.
- **CA-05:** si no hay información suficiente para un plan válido, el grafo termina sin pausa HITL y devuelve `plan=[]`.
- **CA-06:** la aprobación reanuda el mismo hilo y solo marca `done=True` tras una aplicación correcta.
- **CA-07:** el rechazo no aplica el plan, deja `done=False`, limpia los datos del pedido actual y permite continuar en el mismo hilo.
- **CA-08:** dos turnos del mismo `thread_id` conservan el historial esperado y dos identificadores distintos mantienen estados separados.
- **CA-09:** el número real de ejecuciones del supervisor nunca supera `MAX_ITER`.
- **CA-10:** ningún especialista supera `MAX_STEPS_ESPECIALISTA`.
- **CA-11:** las dos funciones públicas devuelven el contrato completo y no propagan excepciones.
- **CA-12:** los eventos de traza respetan los nombres y campos definidos en el contrato.
- **CA-13:** los errores de herramientas, LLM e imagen se comunican de forma controlada y no exponen secretos.
- **CA-14:** el núcleo puede invocarse desde CLI y Streamlit sin duplicar la lógica del grafo.

## 8. Pruebas previstas

- Pruebas unitarias del estado y de las decisiones de enrutamiento.
- Pruebas del fallback determinista cuando el selector LLM falla o devuelve rutas inválidas.
- Pruebas con resultados simulados para los dos especialistas.
- Pruebas de síntesis con información completa, parcial, insuficiente y con errores de herramientas.
- Pruebas que verifiquen que un plan genérico o sin respaldo no genera una pausa HITL.
- Pruebas de interrupción, aprobación y rechazo.
- Pruebas de persistencia y aislamiento por `thread_id`.
- Pruebas que cuenten las ejecuciones reales del supervisor y de cada especialista.
- Pruebas de validación de entradas e imagen.
- Pruebas de la estructura y longitud de los eventos de traza.
- Pruebas que confirmen que las funciones públicas devuelven errores en el contrato en lugar de propagar excepciones.

Las pruebas deberán poder ejecutarse con herramientas y LLM simulados, evitando llamadas reales innecesarias.

## 9. Dependencias y decisiones de integración

- Las herramientas se consumirán exclusivamente mediante la interfaz definida en `docs/contrato.md`.
- El especialista de conocimiento usará `rag_ask` con `{"pregunta": str}`; la implementación interna del RAG y el uso de `responder()` corresponden al bloque tools.
- El especialista de planificación utilizará `api_dominio`, `hora_actual` y, cuando proceda, `describir_imagen`.
- Los nombres y parámetros de las herramientas no se cambiarán sin actualizar primero el contrato y coordinarlo con el responsable de tools.
- La CLI y Streamlit consumirán las dos funciones públicas de `src/agent.py`.
- `langgraph` deberá declararse en `requirements.txt`.

## 10. Definición de terminado

La especificación se considerará implementada cuando:

- El grafo compile y respete la estructura multiagente.
- Los dos especialistas, la síntesis y el nodo de aplicación estén integrados.
- La persistencia, la interrupción HITL y los límites estén controlados por Python.
- La síntesis solo produzca planes aprobables cuando existan acciones concretas respaldadas.
- La API pública cumpla el contrato.
- Las pruebas de aceptación pasen.
- El núcleo pueda utilizarse desde la CLI y Streamlit sin duplicar la orquestación.
