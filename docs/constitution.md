# Constitución — Retiro Agents

Principios innegociables para toda spec, plan, tarea y línea de código. Si una petición choca con alguno, el agente se detiene y lo dice.

1. **Manda el enunciado del PB2.** Ninguna spec puede contradecir el enunciado oficial del Project Break 2; si alguna choca con él, se avisa antes de seguir.
2. **La spec manda sobre el código.** Solo se implementa lo que está en una spec aprobada de `specs/`; si cambia el comportamiento, primero se cambia la spec.
3. **Anclado al corpus.** El RAG responde solo con lo recuperado y se abstiene sin evidencia; el agente no inventa datos que deba aportar una tool.
4. **El modelo propone, Python decide.** La allowlist de tools, la validación de argumentos, los límites (`max_steps`) y el cierre del plan se deciden en código, nunca solo por el LLM.
5. **HITL obligatorio.** El plan no se cierra sin una pausa y una decisión humana (aprobar o rechazar), tanto en la CLI como en Streamlit.
6. **Lógica separada de las interfaces.** Tools, grafo, orquestación y UI van en capas distintas; la CLI y Streamlit son clientes finos del mismo contrato y Streamlit no contiene lógica de grafo.
7. **Tools predecibles.** Toda tool devuelve una salida homogénea (`ok`, `error` o `blocked`), nunca lanza excepciones y deja una traza visible; una API externa siempre tiene fallback local.
8. **Trazabilidad.** El supervisor, las tools y el HITL dejan traza visible (log y panel de depuración de Streamlit).
9. **Tests como puerta, sin API.** El LLM, los embeddings y la red se sustituyen por dobles; Chroma real solo en un directorio temporal y con embeddings falsos; los tests del grafo usan un LLM falso y `MemorySaver`. Prohibido avanzar con tests en rojo.
10. **Configuración y secretos.** Los valores configurables o que usen los agentes viven en `config.py`; las constantes internas de un módulo pueden quedarse en él. Las claves, solo en `.env`, nunca en el repositorio.
11. **Stack cerrado.** Python 3.10+, LangChain/LangGraph, Gemini, ChromaDB, Streamlit y pytest. No se añaden dependencias sin actualizar antes la spec y el plan.
12. **Git.** Una rama por bloque hacia `develop` y una PR revisada por otro miembro, con commits pequeños; nada de trabajo directo en `main`.
13. **Idioma** *(pendiente de acordar con el equipo)*. Identificadores nuevos en inglés técnico neutro; mensajes y documentación en español; el código heredado no se renombra.
