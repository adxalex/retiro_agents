
# Spec 003 — Núcleo del agente multiagente

## 1. Objetivo

Implementar el núcleo de un agente multiagente para el Parque del Retiro mediante LangGraph. El sistema debe recibir peticiones del usuario, decidir qué especialista debe intervenir, reunir los resultados y preparar un plan que requiera aprobación humana antes de aplicarse.

## 2. Contexto

El proyecto reutiliza el RAG existente del Parque del Retiro. El agente no debe reconstruirlo, sino invocarlo a través de las herramientas que proporcionará el módulo de tools.

Se definen dos especialistas:

- **Especialista de conocimiento del Retiro:** responde sobre lugares, historia, instalaciones, servicios y normas a partir del RAG.
- **Especialista de planificación de visita:** ayuda a organizar una visita utilizando herramientas de contexto, tiempo, meteorología o fuentes externas que estén disponibles.

Ambos especialistas deben tener instrucciones diferenciadas y utilizar únicamente las herramientas autorizadas para su función.

## 3. Alcance

Este bloque incluye:

- Definición del estado compartido del grafo.
- Creación y conexión de los nodos de LangGraph.
- Orquestación mediante un supervisor.
- Integración de los dos especialistas.
- Síntesis de resultados y preparación de un plan.
- Persistencia de la conversación mediante `MemorySaver` y `thread_id`.
- Interrupción antes de aplicar el plan para solicitar aprobación humana.
- Control de límites de ejecución y condición de finalización desde Python.
- Exposición de una interfaz de programación reutilizable por la CLI y Streamlit.

Quedan fuera de este bloque la implementación interna de las herramientas y la interfaz visual de Streamlit.

## 4. Archivos afectados

- `src/state.py`: definición del estado compartido.
- `src/graph.py`: construcción y compilación del grafo.
- `src/agent.py`: funciones públicas para procesar turnos, gestionar decisiones humanas y ejecutar la demo.
- `requirements.txt`: incorporación de `langgraph`, si todavía no está declarado.

## 5. Requisitos funcionales

### RF-01. Estado compartido

El sistema debe disponer de un estado tipado y compartido entre los nodos que permita conservar, como mínimo:

- Mensaje o petición actual.
- Historial relevante de la conversación.
- Especialistas ejecutados y resultados obtenidos.
- Notas necesarias para sintetizar la respuesta.
- Respuesta final propuesta.
- Plan pendiente de aprobación.
- Decisión humana, cuando exista.
- Número de pasos o iteraciones ejecutados.
- Indicador de finalización `done`.
- Información de trazabilidad suficiente para mostrar el recorrido del agente.

Los campos concretos y sus tipos se definirán en la implementación, manteniendo un contrato estable para los consumidores del agente.

### RF-02. Supervisor

El supervisor debe seleccionar el siguiente paso según la petición y los resultados disponibles.

Puede dirigir el flujo hacia el especialista de conocimiento, el de planificación o la síntesis. Debe permitir que intervengan ambos especialistas cuando la petición lo requiera.

Si falla la decisión del LLM o su respuesta no es válida, debe existir una alternativa determinista implementada en Python.

El supervisor no podrá ignorar los límites de ejecución ni decidir por sí solo que una acción pendiente de aprobación ya está autorizada.

### RF-03. Especialistas

Cada especialista debe tener un propósito y unas instrucciones propias.

El especialista de conocimiento utilizará el RAG a través de la interfaz de herramientas acordada con el equipo.

El especialista de planificación utilizará las herramientas de contexto disponibles y no inventará resultados que dependan de ellas.

Si una herramienta falla o no devuelve evidencia suficiente, el sistema debe reflejar esa limitación en sus resultados.

### RF-04. Síntesis

El nodo de síntesis debe reunir los resultados relevantes de los especialistas y producir:

- Una respuesta comprensible para el usuario.
- Un plan propuesto, cuando corresponda.
- Las limitaciones o datos no disponibles que sean relevantes.
- Una indicación clara de que el plan está pendiente de aprobación humana.

La síntesis no equivale a ejecutar el plan ni a autorizarlo.

### RF-05. Aplicación y aprobación humana

El nodo `aplicar` debe quedar protegido mediante una interrupción de LangGraph antes de su ejecución, por ejemplo con `interrupt_before=["aplicar"]`.

El grafo debe detenerse después de preparar el plan y antes de aplicar los cambios o acciones correspondientes.

Cuando el usuario apruebe el plan, el flujo podrá continuar y Python deberá marcar `done=True` únicamente cuando la aplicación haya concluido correctamente.

Cuando el usuario rechace el plan, no debe marcarse como completado. El agente debe permitir continuar la conversación, modificar la propuesta o generar un nuevo plan.

No se permite la aprobación automática en el flujo interactivo.

### RF-06. Persistencia

El grafo debe compilarse con `MemorySaver` o el mecanismo de memoria exigido por el proyecto.

Cada conversación debe identificarse mediante un `thread_id` estable. Las llamadas posteriores de una misma conversación deberán reutilizarlo para recuperar el estado y continuar la ejecución.

Una conversación nueva debe poder utilizar un identificador distinto.

### RF-07. Límites y finalización

El número máximo de pasos o iteraciones debe estar controlado por Python mediante una constante o configuración explícita.

El agente no podrá ejecutar un bucle indefinido ni delegar exclusivamente en el LLM la decisión de continuar.

Al alcanzar el límite, debe detenerse de forma controlada, informar de que no ha podido completar el flujo y evitar marcar como completado un plan que no haya sido aplicado y confirmado.

### RF-08. Interfaz pública

`src/agent.py` debe exponer, como mínimo, las siguientes operaciones:

- `procesar_turno(...)`: iniciar o continuar un turno de conversación.
- `aprobar_plan(...)`: registrar la decisión humana y continuar el flujo.
- `run_demo(...)`: ejecutar un escenario de demostración reproducible.

Los parámetros y valores de retorno deben documentarse y mantenerse compatibles con los clientes CLI y Streamlit.

La lógica del grafo debe permanecer en `src/graph.py`, no duplicarse en las interfaces.

### RF-09. Trazabilidad y errores

El sistema debe permitir identificar los pasos ejecutados, el especialista utilizado, los errores relevantes y las pausas de aprobación.

Los errores del LLM o de las herramientas deben tratarse de forma controlada siempre que sea posible. No se deben mostrar secretos ni claves de API en los mensajes de error.

## 6. Requisitos no funcionales

- Modularidad: estado, grafo, herramientas e interfaces deben estar separados.
- Reutilización: el agente debe poder invocarse sin depender de Streamlit.
- Mantenibilidad: las constantes y los límites deben ser fáciles de localizar y modificar.
- Seguridad: solo se podrán ejecutar herramientas autorizadas y las acciones pendientes de aprobación no podrán aplicarse anticipadamente.
- Compatibilidad: el grafo debe conservar un contrato común para CLI y Streamlit.

## 7. Criterios de aceptación

- **CA-01:** una petición llega al supervisor y se dirige al especialista apropiado o a la síntesis cuando proceda.
- **CA-02:** una petición compleja puede utilizar ambos especialistas y combinar sus resultados.
- **CA-03:** si el supervisor falla, el fallback de Python permite continuar de forma controlada o detener el flujo con un error claro.
- **CA-04:** la síntesis genera una propuesta y el grafo se interrumpe antes de ejecutar `aplicar`.
- **CA-05:** una aprobación permite reanudar el mismo hilo y marcar `done=True` solo después de una aplicación correcta.
- **CA-06:** un rechazo no marca el flujo como completado y permite continuar con nuevas instrucciones.
- **CA-07:** dos turnos del mismo `thread_id` conservan el contexto esperado.
- **CA-08:** el límite de iteraciones se respeta incluso si el LLM solicita continuar indefinidamente.
- **CA-09:** el agente puede ser invocado desde un cliente distinto de Streamlit.
- **CA-10:** las pruebas verifican el comportamiento de aprobación, rechazo, fallback, límites y errores relevantes.

## 8. Pruebas previstas

- Pruebas unitarias del estado y de las decisiones de enrutamiento.
- Pruebas con respuestas simuladas del LLM para comprobar el fallback.
- Pruebas del flujo de interrupción, aprobación y rechazo.
- Pruebas de persistencia con un mismo `thread_id`.
- Pruebas de límites de ejecución.
- Pruebas de integración con las interfaces reales de las herramientas cuando estén disponibles.

Las pruebas deben poder ejecutarse sin depender innecesariamente de llamadas reales y costosas a modelos externos.

## 9. Dependencias y decisiones pendientes

- Confirmar los nombres y contratos definitivos de las herramientas con el responsable del módulo tools.
- Confirmar el modelo y mecanismo de invocación del LLM.
- Definir la estructura exacta de los resultados de cada especialista.
- Confirmar la política de reanudación tras un rechazo.
- Confirmar la versión de LangGraph compatible con el entorno del proyecto.

## 10. Definición de terminado

La especificación se considera implementada cuando existen los módulos definidos, el grafo compila, las pruebas de aceptación pasan y la interfaz pública puede utilizarse desde la CLI y desde Streamlit sin duplicar la lógica de orquestación.
