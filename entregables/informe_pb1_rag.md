# Informe de decisiones · Retiro RAG

**Estado:** plantilla. Completar con resultados reales antes de la presentación.

## 1. Resumen

Describir el dominio, corpus, formatos y flujo RAG implementado.

## 2. Corpus

- Número final de documentos:
- Formatos:
- Categorías:
- Criterios de selección:
- Limitaciones:

## 3. Experimento de chunking

Comparar al menos dos configuraciones sobre los mismos documentos y preguntas.

### Configuración A

- `CHUNK_SIZE`:
- `CHUNK_OVERLAP`:
- Número de chunks:
- Preguntas:
- Resultados:

### Configuración B

- `CHUNK_SIZE`:
- `CHUNK_OVERLAP`:
- Número de chunks:
- Preguntas:
- Resultados:

### Decisión

Indicar la configuración adoptada y justificarla considerando contexto, ruido y coste.

## 4. Experimento de retrieval

### Cómo funciona el retrieval

`retrieve()` convierte la consulta en un vector con `embed_query()`, la busca en
la colección `retiro_madrid` de ChromaDB y devuelve los `top_k` chunks más
próximos, ordenados de mayor a menor relevancia.

Cada resultado conserva el chunk indexado completo (`chunk_id`, `document_id`,
`text`, `source`, `chunk_index`, `category`, `corpus_group` y `page` cuando
existe) y añade un campo `score`, según el contrato 3.

### De distancia a score

ChromaDB devuelve una distancia: cuanto menor, más parecido. El contrato exige
un `score` donde un valor mayor signifique más relevancia, así que se aplica:

    score = max(0.0, min(1.0, 1.0 - distancia))

El recorte entre 0 y 1 evita valores fuera de rango por errores de precisión. La
fórmula solo es válida con métrica coseno, que es la que usa la colección
(`HNSW_SPACE = "cosine"`). `retrieve.py` comprueba esa constante y lanza un error
explícito si alguien la cambia, para que la conversión no quede silenciosamente
mal.

### Filtro por metadata

`retrieve()` acepta un parámetro `where` que se traslada a ChromaDB, lo que
permite restringir la búsqueda a una categoría:

    python main.py --query "¿qué pasa con alerta roja?" --category seguridad

Es útil para depurar la cobertura por bloque temático y queda disponible para
futuras mejoras, como enrutar preguntas por tipo.

### Numeración de las citas

El prompt numera los fragmentos del 1 al `top_k`, de modo que el modelo puede
citar `[3]` aunque los tres fragmentos procedan del mismo documento. La lista
`fuentes` agrupa por documento y, por tanto, no sirve para resolver esas citas.
Para evitar que una cita quede sin referencia, `responder()` devuelve también
`citas`, con la correspondencia número → documento, página, `chunk_id` y `score`.

El fallo se detectó durante las pruebas con el índice real: una respuesta citaba
`[1]` y `[3]` mientras la lista de fuentes mostraba un único documento.

### Resultados por pregunta

Medición sobre el banco de 25 preguntas de `queries/banco_preguntas_bloque_c.md`
con el índice real: 1.177 chunks, `gemini-embedding-001`, dimensión 3.072.

| Pregunta | K | Score top-1 | Mejor fuente | ¿Tiene sentido? | Ruido |
|---|---:|---:|---|---|---|
| ¿Qué horario tiene el parque en verano? | 3 | 0,721 | `informacion_practica_guia_visitante_retiro.pdf` | Sí, es la fuente correcta | Aparece `flora_fauna__senda_botanica` sin relación |
| ¿Qué rey impulsó la creación del Retiro? | 3 | 0,754 | `retiro_historia.md` | Sí | Aparece `plan_director_arbolado` |
| Hay alerta naranja y estoy en el lago, ¿qué hago? | 3 | 0,710 | `seguridad_protocolo_alertas_retiro.pdf` | Sí, única fuente devuelta | Ninguno |
| ¿Qué edificio es neomudéjar? (fuera de corpus) | 3 | 0,709 | `flora_fauna__plan_director_arbolado__madrid__v01.pdf` | No debe responder, y no responde | Todo el contexto es ruido |

### Comparación de `TOP_K`

Métrica: en cuántas preguntas aparece una fuente válida entre los `top_k` chunks
recuperados.

| `TOP_K` | Fuente única declarada | Cualquier fuente válida |
|---:|---|---|
| 3 | 73 % (11/15) | 94 % (15/16) |
| 5 | 80 % (12/15) | 94 % (15/16) |

La primera columna corresponde a la medición inicial, con una sola fuente
esperada por pregunta. Al crecer el corpus, varias preguntas pasaron a tener más
de un documento que las responde legítimamente: el edificio de las exposiciones
del Reina Sofía, por ejemplo, aparece tanto en la guía del visitante como en el
documento de arte y cultura. La segunda columna admite cualquiera de esas
fuentes e incorpora al denominador la pregunta 8, que dejó de ser de abstención.

El criterio se amplió **después** de observar los resultados, por lo que se
publican ambas cifras: la estricta subestima el rendimiento y la ampliada
refleja mejor lo que el sistema recupera.

Único fallo real de retrieval: la pregunta 9 (jardín de estilo francés), que
devuelve la senda botánica y el plan director de arbolado en lugar del documento
que describe el Parterre Francés.

### Decisión sobre `TOP_K`

`TOP_K = 3` como valor predeterminado.

Justificación: con el índice real, pasar de 3 a 5 no mejora el recall bajo el
criterio de fuentes válidas (94 % en ambos casos) y solo aporta una pregunta más
bajo el criterio estricto. A cambio, cada chunk adicional añade texto al contexto
del LLM, lo que aumenta el coste por consulta y el riesgo de mezclar fragmentos
poco relacionados. El valor es configurable por `.env` y por `--top-k`.

---

## 5. Generación y grounding

### Diseño del prompt

`build_prompt()` construye un prompt con tres partes: instrucciones, contexto
numerado y pregunta. Las instrucciones obligan al modelo a responder solo desde
el contexto, a citar con `[1]`, `[2]`, a declarar cuándo un dato tiene fecha o
procede de una fuente no oficial, y a no inventar horarios, precios ni
distancias.

Cada chunk se presenta con su número, fuente, página y categoría, lo que permite
que las citas sean verificables y que el usuario sepa de qué documento sale cada
afirmación.

### La abstención tiene dos compuertas

Durante el desarrollo se comprobó que **ChromaDB siempre devuelve vecinos**,
también cuando el corpus no contiene la respuesta: ante una pregunta sin
cobertura devuelve igualmente los chunks menos lejanos. Por tanto, la abstención
no puede basarse en que la lista venga vacía. Se implementaron dos compuertas:

1. **Compuerta de retrieval.** Si el mejor `score` no alcanza `RAG_SCORE_MINIMO`,
   el sistema se abstiene sin llamar al LLM. Es determinista, reproducible y
   ahorra el coste de la llamada.
2. **Compuerta de generación.** El prompt obliga al modelo a devolver el
   centinela `SIN_EVIDENCIA` cuando el contexto no sostiene la respuesta;
   `responder()` lo detecta y lo sustituye por un mensaje claro para el usuario.

La salida de `responder()` incluye siempre `abstuvo` y `motivo_abstencion`, de
forma que se puede distinguir cuál de las dos compuertas actuó.

### Calibración del umbral

El umbral no se fijó a ojo. `scripts/validation/calibrar_umbral.py` ejecuta el
banco de preguntas, compara la distribución del `score` del mejor chunk en las
preguntas respondibles y en las de abstención, y propone el valor con más
aciertos.

| Medida | `gemini-embedding-001` |
|---|---|
| Score mínimo, preguntas respondibles (n=16) | 0,698 |
| Mediana del score, preguntas respondibles | 0,747 |
| Score máximo, preguntas respondibles | 0,782 |
| Score mínimo, preguntas de abstención (n=9) | 0,648 |
| Mediana del score, preguntas de abstención | 0,709 |
| Score máximo, preguntas de abstención | 0,744 |
| Mejor umbral posible | 0,698 (20/25 aciertos) |
| Umbral adoptado | **0,65** (17/25 aciertos) |

**Las dos distribuciones se solapan casi por completo.** Todos los scores caen
entre 0,648 y 0,782, y cinco preguntas sin respuesta en el corpus puntúan por
encima de 0,70, entre ellas la del evento deportivo (0,744) y la de los
fotógrafos (0,736). El mejor umbral posible acierta 20 de 25 y deja un margen de
0,008 sobre la pregunta respondible peor puntuada.

Las cifras se recalcularon sobre la misma ejecución de `calibrar_umbral.py`
después de reclasificar la pregunta 8 como respondible: su score (0,768) pasa de
un grupo al otro. No se reejecutó la calibración porque el score de cada
pregunta no cambia al reclasificarla, solo cambia el grupo al que pertenece.

Se adoptó 0,65 en lugar del óptimo teórico porque un umbral ajustado a estos
datos silenciaría cualquier respuesta correcta ligeramente peor puntuada. Con
0,65 no se pierde ninguna respuesta válida y se descarta el caso más claramente
irrelevante.

**Conclusión:** con embeddings reales, la compuerta de score aporta poco por sí
sola. El peso de la abstención lo lleva el centinela del prompt. Esto valida a
posteriori la decisión de implementar dos compuertas en lugar de una.

### Acierto in-corpus

- Pregunta: ¿Qué fauna piscícola predomina en el Estanque Grande del Retiro?
- Respuesta: carpas como especie principal, y peces gato y percasoles según
  fuentes secundarias coincidentes, con el nivel de confianza que indica el
  propio documento.
- Fuentes: `flora_fauna__fauna_estanque_grande_retiro__fuentes_contrastadas__v01.md`
- Evidencia: el documento de fauna contrastada recoge esas especies con su nivel
  de confianza, que la respuesta traslada en lugar de presentarlas como
  certezas.
- Valoración: correcta y anclada. La respuesta reproduce la gradación de
  confianza de la fuente, que es justo lo que pedían las instrucciones del
  prompt.

### Abstención fuera de corpus

- Pregunta: ¿Qué edificio del Retiro se caracteriza por su estilo neomudéjar?
- Resultado esperado: abstención. El término no aparece en ningún documento del
  corpus, pese a que es un dato real que un LLM conoce por su entrenamiento.
- Score del mejor chunk: 0,709, por encima del umbral de 0,65, de modo que la
  compuerta de retrieval **no** detuvo la consulta.
- Resultado obtenido: abstención, con motivo `el_modelo_no_vio_evidencia`.
- ¿Se abstuvo correctamente?: sí.

Es la evidencia directa de que ambas compuertas son necesarias: el filtro
numérico dejó pasar la consulta y fue el centinela del prompt quien evitó que el
modelo respondiera desde su conocimiento propio.

---

## 6. Evaluación global

- Número de preguntas: 25
- Preguntas respondibles: 14
- Preguntas parciales: 2
- Preguntas de abstención: 9
- Categorías cubiertas: historia, monumentos, jardines, flora y fauna,
  itinerarios, información práctica y seguridad

La pregunta 8 (fauna del Estanque Grande) pasó de abstención a respondible al
integrarse la fuente contrastada de fauna. Se documenta el cambio en lugar de
eliminar la pregunta: es un hueco de cobertura detectado por la evaluación y
cubierto después con una fuente trazable.

El banco está en `queries/banco_preguntas_bloque_c.md` y se ejecuta con
`scripts/validation/eval_preguntas.py`. Incluye dos preguntas conversacionales
(un visitante que busca un aseo y otro que pregunta qué hacer con alerta
naranja) y una fuera de alcance, para comprobar que el sistema no responde a lo
que no le corresponde.

### Criterios

- **Evidencia:** una fuente válida debe aparecer entre los `top_k` chunks
  recuperados.
- **Grounding:** la respuesta debe apoyarse solo en el contexto recuperado y
  citar los fragmentos con `[n]`.
- **Abstención:** en las preguntas sin cobertura, la respuesta debe declarar que
  no dispone de esa información, sin ofrecer un dato alternativo.

### Resultados

| Métrica | `top_k` = 3 | `top_k` = 5 |
|---|---|---|
| Recall, fuente única declarada | 73 % (11/15) | 80 % (12/15) |
| Recall, cualquier fuente válida | 94 % (15/16) | 94 % (15/16) |
| Aciertos del mejor umbral posible | 20/25 | — |
| Aciertos con el umbral adoptado (0,65) | 17/25 | — |

Los 17/25 del umbral adoptado corresponden solo a la compuerta de score: las 16
preguntas respondibles pasan el filtro y una de abstención se detiene en él. Las
ocho restantes dependen del centinela del prompt, que en la prueba directa
funcionó correctamente.

**Estado de la configuración:** el valor por defecto de `RAG_SCORE_MINIMO` en el
código es 0.0, es decir, con la compuerta de score desactivada. El 0,65 se
documenta en `.env.example` como valor recomendado y debe fijarse en el `.env`
de cada entorno; no se aplica de forma automática.

---

## 7. Tres fallos conocidos

### Fallo 1 · Chroma siempre devuelve vecinos y los scores se solapan

- Caso: preguntas sin respuesta en el corpus, como el estilo neomudéjar (0,709)
  o el evento deportivo (0,744), que puntúan por encima de varias preguntas
  respondibles.
- Causa probable: una búsqueda por vecinos más próximos no tiene noción de
  "ninguno es relevante". Además, los embeddings comprimen todos los scores del
  corpus en una franja estrecha, entre 0,648 y 0,782.
- Impacto: un umbral de score no puede separar por sí solo lo respondible de lo
  que no lo es; sin el centinela, el LLM recibiría contexto irrelevante y podría
  construir una respuesta plausible pero infundada.
- Posible mejora: un reranking o un clasificador de relevancia previo al LLM,
  que use el contenido del chunk y no solo la distancia vectorial.

### Fallo 2 · Preguntas con superlativos o comparaciones

- Caso: «qué fauna es *más habitual*», «cuál es la entrada *más utilizada*». El
  corpus puede contener los elementos, pero no la comparación.
- Causa probable: el retrieval semántico recupera fragmentos sobre el tema, pero
  ningún documento afirma cuál predomina.
- Impacto: riesgo de que el modelo deduzca un superlativo que ninguna fuente
  sostiene.
- Posible mejora: instruir al modelo para tratar los superlativos como
  afirmaciones que requieren evidencia explícita, y clasificar estas preguntas
  como parciales en el banco.

### Fallo 3 · Corpus desequilibrado y ruido dominante

- Caso: `flora_fauna__plan_director_arbolado__madrid__v01.pdf` aparece entre los
  resultados de 13 de las 25 preguntas, incluidas las de horarios, monumentos y
  protocolos de seguridad.
- Causa probable: de los 1.177 chunks del índice, 1.082 pertenecen al grupo de
  flora, fauna, arte y actividades, frente a 61 del bloque de itinerarios e
  información práctica y 34 del de historia y monumentos. Un documento muy
  extenso ocupa una proporción desmesurada del espacio vectorial.
- Impacto: fragmentos irrelevantes ocupan plazas del `top_k` y desplazan al
  documento correcto, lo que explica el fallo de la pregunta 9.
- Posible mejora: equilibrar el corpus limitando el número de chunks por
  documento, o aplicar el filtro por categoría en función del tipo de pregunta.

---

## 8. Logging y métricas

## 8. Logging y métricas

`src/logging_utils.py` registra cada consulta en dos sitios: una línea legible
por consola y una línea JSON por consulta en `output/consultas.jsonl`.

Campos registrados: marca de tiempo, pregunta, `top_k`, número de chunks
recuperados, tiempo en segundos, modelo de generación, `abstuvo`,
`motivo_abstencion`, `score` del mejor chunk y fuentes citadas.

Se eligió el formato JSONL porque permite añadir líneas sin releer el fichero y
se carga en una instrucción:

    pandas.read_json("output/consultas.jsonl", lines=True)

El registro está conectado dentro de `responder()`, de modo que queda constancia
tanto de las consultas hechas desde la CLI como desde Streamlit. Un fallo de
escritura no interrumpe la consulta: se avisa y se continúa, porque un problema
de registro no debe dejar sin respuesta al usuario.

`resumen_de_consultas()` devuelve el total de consultas, el número de
abstenciones, la tasa de abstención y el tiempo medio.

### Métricas de la sesión de evaluación

Medición sobre una sesión limpia de 10 consultas reales contra el índice
completo, con `gemini-3.6-flash` y `top_k = 3`.

| Métrica | Valor |
|---|---|
| Consultas registradas | 10 |
| Abstenciones | 3 |
| Tasa de abstención | 30 % |
| Tiempo medio por consulta | 14,8 s |

La tasa de abstención del 30 % corresponde a la composición de la sesión: se
incluyeron a propósito preguntas sin cobertura en el corpus (el estilo
neomudéjar, el evento deportivo y el aparcamiento) para comprobar el
comportamiento en ambos casos.

**El tiempo medio de 14,8 segundos es el principal límite de rendimiento del
sistema.** El grueso corresponde a la generación: el retrieval sobre ChromaDB es
prácticamente instantáneo y la llamada al modelo consume casi todo el tiempo. Es
aceptable para una consulta puntual, pero se hace largo en una demostración en
vivo. Dos mejoras evidentes, fuera del alcance del MVP: devolver la respuesta en
streaming, para que el usuario empiece a leer antes de que termine de generarse,
y cachear las consultas repetidas.

### Un fallo detectado al recoger estas métricas

La primera medición dio 314 consultas con un tiempo medio de 0,465 segundos,
cifras imposibles para consultas reales. La causa era que la suite de tests
también escribía en el registro: cada ejecución de `pytest` añadía cientos de
entradas generadas con clientes simulados, porque las pruebas llaman a
`responder()` y este registra siempre.

Se añadió `tests/conftest.py` con una fixture automática que redirige
`RUTA_LOG` a un fichero temporal en todas las pruebas, y las métricas se
tomaron después en una sesión limpia.

El caso ilustra un riesgo propio del logging automático: si el registro no se
aísla en las pruebas, las métricas derivadas de él dejan de ser fiables sin que
nada falle de forma visible. Ningún test estaba en rojo y el sistema funcionaba
con normalidad; lo único incorrecto eran los números.

## 9. Decisiones técnicas

- Modelo de embeddings: `gemini-embedding-001`, dimensión 3.072. Se migró desde
  `text-embedding-004`, retirado por Google en enero de 2026.
- Modelo de generación: `gemini-3.6-flash`. Se migró desde `gemini-2.5-flash`,
  que Google dejó de servir a cuentas nuevas durante el desarrollo. El cambio
  afecta solo a `LLM_MODEL` y no obliga a reconstruir el índice.
- ChromaDB y ruta persistente: colección `retiro_madrid` en `chroma/`, con
  métrica coseno. La carpeta no se versiona, de modo que cada entorno construye
  su propio índice.
- Estrategia de regeneración: `build_index(recreate=True)` reconstruye la
  colección desde cero; `--keep-index` hace upsert sobre la existente. La
  idempotencia se verifica en los tests del bloque B.
- API interna: `responder(pregunta, top_k, score_minimo, collection, client,
  where)` devuelve `respuesta`, `fuentes`, `citas`, `chunks`, `abstuvo` y
  `motivo_abstencion`. `rag_ask()` es una envoltura que devuelve solo el texto.
- Inyección de dependencias: `retrieve()` y `responder()` aceptan `collection` y
  `client` opcionales, lo que permite probar todo el bloque C sin ChromaDB ni la
  API de Gemini, con dobles deterministas.
- Parámetros configurables por `.env`: `TOP_K`, `RAG_SCORE_MINIMO` y
  `RAG_LOG_FILE`, además de los modelos. El umbral también se puede sobrescribir
  desde la CLI con `--score-minimo`.
- Interfaz de línea de comandos: `--index` construye el índice (con `--dry-run`
  valida sin consumir API), `--query` ejecuta solo retrieval y `--ask` el flujo
  completo, con `--top-k`, `--category`, `--contexto`, `--score-minimo` y
  `--json`.
- Limitación conocida del SDK: `google-genai` 2.22.0 emite un aviso sobre
  *automatic function calling* en `generate_content()` aunque no se pasen
  herramientas. Es un fallo abierto del SDK
  (`googleapis/python-genai#2902`) que no afecta a las respuestas. Se decidió no
  migrar a la Chat API por su impacto en el alcance de la entrega.

---

## 10. Siguientes pasos

Mejoras razonables, fuera del alcance del MVP entregado:

- **Reranking.** Un modelo de reordenación sobre los `top_k` chunks recuperados
  mejoraría la precisión sin ampliar el contexto enviado al LLM. Es la medida
  con más recorrido, dado que los scores de embeddings apenas discriminan.
- **Equilibrado del corpus.** Limitar la proporción de chunks por documento
  evitaría que una fuente muy extensa domine el espacio vectorial.
- **Enrutado por categoría.** Clasificar la pregunta y aplicar el filtro `where`
  automáticamente, en lugar de buscar en todo el corpus.
- **Descomposición de consultas.** Dividir las preguntas con varias entidades en
  varias búsquedas.
- **Recalibración automática del umbral.** Cada vez que el corpus crece, la
  distribución de scores cambia; convendría reejecutar la calibración como parte
  del proceso de indexación.
- **Métricas de grounding automáticas.** Hoy la verificación de que la respuesta
  se apoya en el contexto es manual. Podría automatizarse comprobando que cada
  cita `[n]` apunta a un chunk efectivamente recuperado, usando el campo
  `citas`.

---

# Los dos huecos que faltan

Están en el apartado 8. Para rellenarlos:

1. Haz unas cuantas consultas para tener datos, por ejemplo:

       python main.py --ask "¿Qué horario tiene el parque en verano?"
       python main.py --ask "¿Qué monumento preside el Estanque Grande?"
       python main.py --ask "¿Qué edificio es neomudéjar?"

2. Pide el resumen:

       python -c "import sys; sys.path.insert(0,'.'); from src.logging_utils import resumen_de_consultas; print(resumen_de_consultas())"

3. Copia los cuatro números en el apartado 8.
