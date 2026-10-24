# Contrato del agente

Estado: vigente. Define las interfaces entre bloques (agente, tools e interfaces de usuario). Cualquier cambio se hace primero aquí, con /sdd-cambio, y se avisa al equipo.

## 1. Funciones públicas (src/agent.py)

La CLI y Streamlit solo llaman a estas dos funciones. No hay lógica de grafo fuera de agent.py.

- procesar_turno(texto: str, thread_id: str, imagen: dict | None = None) -> dict
- aprobar_plan(thread_id: str, aprobado: bool, comentario: str = "") -> dict

imagen = {"bytes": bytes, "mime": str} o None. El turno recibe la imagen y la pasa a la tool describir_imagen.

Ambas devuelven el mismo dict:
- thread_id: str
- respuesta: str ("" si aún no hay)
- plan: list[str] (viñetas; [] si aún no hay)
- pendiente_aprobacion: bool (True = grafo pausado antes de "aplicar")
- done: bool (True solo tras aprobar; lo decide Python, no el LLM)
- traza: list[dict] (eventos del turno, ver sección 4)
- error: str | None

Reglas:
- El mismo thread_id continúa la conversación. "Nueva conversación" = el cliente genera un thread_id nuevo (uuid4 como str).
- aprobar_plan(aprobado=True): done=True y pendiente_aprobacion=False.
- aprobar_plan(aprobado=False): se borran plan, notas y respuesta del pedido; la conversación sigue y done=False.
- Ninguna de las dos lanza excepciones: los problemas se informan en "error".
- procesar_turno con un plan pendiente de decisión devuelve error ("plan pendiente"). aprobar_plan sin plan pendiente también.

## 2. Estado (src/state.py), dos niveles

- Conversación (persiste): thread_id, historial, done.
- Pedido (se reinicia al rechazar): pedido, notas (dict especialista -> texto), respuesta, plan, aprobado (bool | None), pasos (int), traza (list).

## 3. Tools (src/tools/__init__.py)

ejecutar_tool(nombre: str, args: dict) -> dict. Nunca lanza excepciones.

Devuelve: {"tool": nombre, "status": "ok" | "error" | "blocked", "data": ..., "error": str | None, "traza": evento}

- "traza" es el evento de la sección 4 ya construido. El grafo solo lo añade a la lista del turno.
- ALLOWLIST = rag_ask, api_dominio, hora_actual, describir_imagen. Un nombre fuera de la lista devuelve "blocked" sin ejecutarse.

Tools:
- rag_ask: args {"pregunta": str}. Llama a responder(), no a la función rag_ask() del RAG, para conservar fuentes y citas. data = {respuesta, fuentes, citas, abstuvo, motivo_abstencion}.
- api_dominio: args {}. data incluye "origen": "aemet" | "respaldo" y los campos de la observación.
- hora_actual: args {}. data = {"hora_madrid": "HH:MM", "estado_parque": str}.
- describir_imagen: args {"imagen": {"imagen_bytes", "mime"}}. data = str (descripción).

## 4. Traza

Cada evento: {"ts": ISO 8601, "origen": "supervisor" | "tool" | "hitl", "nombre": str, "args": dict, "status": str, "preview": str (máx. 200 caracteres)}.

- supervisor: nombre = especialista elegido.
- tool: nombre = nombre de la tool.
- hitl: nombre = "pausa" | "aprobar" | "rechazar".

## 5. Límites (config.py)

- MAX_ITER = 6: pasadas máximas del supervisor.
- MAX_STEPS_ESPECIALISTA = 3: pasos máximos por especialista.

Los aplica Python; el LLM no decide cuándo termina.

## 6. Grafo

supervisor -> especialista(s) -> sintetizar -> aplicar (interrupt_before=["aplicar"], MemorySaver).

- Especialista "normas": rag_ask.
- Especialista "entorno": api_dominio, hora_actual, describir_imagen.
- El supervisor tiene un fallback determinista en Python si el LLM falla.
- Cada especialista solo puede llamar a las tools de su lista.

## 7. Primeros entregables

- agent.py: procesar_turno y aprobar_plan con respuesta y plan fijos, pero con la pausa y el done reales. Sirve para avanzar con la CLI y Streamlit.
- tools: ejecutar_tool con datos fijos por tool. Sirve para avanzar con el grafo sin esperar a las tools reales.
- Ambos se reemplazan por las implementaciones reales sin cambiar las firmas.