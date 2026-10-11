# Banco de preguntas de evaluación · bloque C (retrieval y generación)

25 preguntas probadas contra el índice real del corpus completo
(255 registros documentales, 17 fuentes, 1.177 chunks).

`Esperado` indica el comportamiento correcto del sistema:

- **Responde**: el corpus contiene la respuesta y debe citar la fuente indicada.
- **Abstención**: el corpus no contiene la respuesta; el sistema debe decir que no
  dispone de esa información en lugar de inventarla.
- **Parcial**: el corpus responde solo una parte; el sistema debe responder lo que
  sabe y declarar lo que no.

| # | Pregunta | Esperado | Fuente esperada | Respuesta correcta / nota |
| --- | --- | --- | --- | --- |
| 1 | ¿En qué siglo se construyó originalmente el Real Sitio del Buen Retiro? | Responde | retiro_jardines.md, retiro_historia.md | Siglo XVII; las obras empezaron en 1630 |
| 2 | ¿Qué rey impulsó la creación del Retiro como espacio palaciego y de recreo? | Responde | retiro_historia.md | Felipe IV, con el impulso del Conde-Duque de Olivares |
| 3 | ¿Cuál es la entrada más utilizada para iniciar un recorrido turístico? | Abstención | — | El corpus no dice cuál es la más utilizada. La Puerta de la Independencia aparece como inicio de una ruta propuesta por el equipo, que no es lo mismo |
| 4 | ¿Qué monumento preside el Estanque Grande? | Responde | retiro_monumentos_jardines.csv | Monumento a Alfonso XII, o Monumento a la Patria Española |
| 5 | ¿Qué edificio se utiliza para exposiciones del Museo Reina Sofía? | Responde | informacion_practica_guia_visitante_retiro.pdf | Palacio de Velázquez y Palacio de Cristal; el de Cristal está cerrado por obras en 2026 |
| 6 | ¿Qué característica arquitectónica distingue al Palacio de Cristal? | Responde | retiro_monumentos_jardines.csv | Estructura de hierro y cristal; ejemplo destacado de la arquitectura del hierro en España |
| 7 | ¿Qué función tenía originalmente la Casa de Vacas? | Abstención | — | El corpus solo la nombra como centro cultural actual; no recoge su uso original |
| 8 | ¿Qué fauna es más habitual en el Estanque Grande? | Responde | flora_fauna__fauna_estanque_grande_retiro__fuentes_contrastadas__v01.md | Carpas, según el documento de fauna contrastada. Antes era de abstención: el hueco se cubrió con una fuente nueva |
| 9 | ¿Qué jardín es famoso por sus parterres geométricos y estilo francés? | Responde | informacion_practica_guia_visitante_retiro.pdf, itinerarios_pie_retiro_.pdf | El Parterre Francés |
| 10 | ¿Qué árbol centenario está catalogado como uno de los más antiguos de Madrid? | Responde | informacion_practica_guia_visitante_retiro.pdf | El ahuehuete del Parterre Francés (unos 400 años); el más antiguo del Retiro es hoy un olivo de 627 años |
| 11 | ¿Qué evento deportivo multitudinario atraviesa el Retiro cada año? | Abstención | — | El corpus solo recoge la Feria del Libro y los fuegos de San Isidro |
| 12 | ¿Qué norma de seguridad se recomienda cerca del Estanque? | Abstención | — | El corpus no recoge normas específicas del estanque. Solo hay normas generales de alertas |
| 13 | ¿Qué edificio fue utilizado como cuartel durante la Guerra de la Independencia? | Parcial | retiro_historia.md | El recinto del Retiro fue usado como fortaleza y acuartelamiento por los franceses; no se nombra un edificio concreto |
| 14 | ¿Qué espacio es conocido por lectura y cuentacuentos? | Abstención | — | El corpus nombra la Biblioteca Eugenio Trías y el Teatro de Títeres, pero no menciona cuentacuentos |
| 15 | ¿Qué ruta incluye el Palacio de Cristal, el Estanque y el Parterre? | Responde | itinerarios_pie_retiro_.pdf | El recorrido completo por el interior (5–6 km, 1 h–1 h 30) |
| 16 | ¿Qué institución oficial respalda la información turística del Retiro? | Responde | informacion_practica_guia_visitante_retiro.pdf | esMadrid, web oficial de Turismo del Ayuntamiento de Madrid |
| 17 | ¿Qué horario tiene el parque en verano? | Responde | informacion_practica_guia_visitante_retiro.pdf | De abril a septiembre, de 6:00 a 0:00 |
| 18 | ¿Qué zona es de especial interés para fotógrafos por su luz natural? | Abstención | — | El corpus no clasifica zonas por luz; solo recoge lugares destacados |
| 19 | ¿Qué elemento está dedicado a Alfonso XII? | Responde | retiro_monumentos_jardines.csv | El conjunto escultórico junto al Estanque Grande, con mirador |
| 20 | ¿Qué edificio se caracteriza por su estilo neomudéjar? | Abstención | — | El término no aparece en el corpus. El Palacio de Velázquez suele describirse así, pero el corpus no lo dice |
| 21 | ¿Qué punto es ideal para iniciar la ruta «Lo esencial»? | Responde | itinerarios_pie_retiro_.pdf | La Puerta de la Independencia, frente a la Puerta de Alcalá |
| 22 | ¿Qué protocolo seguir si un visitante se pierde? | Abstención | — | El corpus no recoge protocolo para personas perdidas. Solo el de alertas meteorológicas |
| 23 | Estoy en el Ángel Caído y necesito un baño, ¿cuál es el más cercano? | Parcial | informacion_practica_guia_visitante_retiro.pdf | Hay un aseo subterráneo junto al Ángel Caído, según una fuente no oficial de 2025. No hay horarios ni confirmación de que esté abierto |
| 24 | Alguien dice haber visto una estatua moverse, ¿qué harías? | Abstención | — | Fuera del alcance del sistema. No debe inventar leyendas ni confirmar el hecho |
| 25 | Hay alerta naranja y estoy en el lago, ¿qué hago? | Responde | seguridad_protocolo_alertas_retiro.pdf | Con alerta naranja se restringen áreas infantiles, deportivas, de mayores, área canina, Cecilio Rodríguez y Herrero Palacios, y se suspenden los eventos al aire libre. El estanque no está entre las zonas restringidas |

## Resumen

- Responde: 14 preguntas
- Parcial: 2 preguntas (13, 23)
- Abstención: 9 preguntas (3, 7, 11, 12, 14, 18, 20, 22, 24)
- Total: 25

La pregunta 8 (fauna del Estanque Grande) pasó de abstención a respondible al
integrarse la fuente contrastada de fauna. Se documenta el cambio en lugar de
eliminarla: es un hueco de cobertura detectado y cubierto con una fuente
trazable.

## Medición con el índice real

Índice: 1.177 chunks, `gemini-embedding-001`, dimensión 3.072, métrica coseno.
Generación: `gemini-3.6-flash`. `TOP_K` por defecto: 3.

### Recall de la fuente esperada

| `top_k` | Fuente única declarada | Cualquier fuente válida |
| --- | --- | --- |
| 3 | 73 % (11/15) | 94 % (15/16) |
| 5 | 80 % (12/15) | 94 % (15/16) |

La primera columna es la medición inicial, con una sola fuente esperada por
pregunta. Al crecer el corpus, varias preguntas pasaron a tener más de un
documento que las responde legítimamente: por ejemplo, el edificio de las
exposiciones del Reina Sofía aparece tanto en la guía del visitante como en el
documento de arte y cultura. La segunda columna admite cualquiera de esas
fuentes y añade la pregunta 8 al denominador.

El cambio de criterio se hizo **después** de ver los resultados, así que se
publican las dos cifras. La estricta subestima el rendimiento; la ampliada
refleja mejor lo que el sistema recupera.

Único fallo real de retrieval: la pregunta 9 (jardín de estilo francés), que
devuelve la senda botánica y el plan director de arbolado en lugar del documento
que describe el Parterre Francés.

### Distribución del score del mejor chunk

Cifras recalculadas sobre la misma ejecución de `calibrar_umbral.py`, después de
reclasificar la pregunta 8 como respondible: su score (0,768) pasa del grupo de
abstención al de respondibles. No se reejecutó la calibración, porque los scores
de cada pregunta no cambian al reclasificarla; solo cambia a qué grupo pertenece.

| | n | Mínimo | Mediana | Máximo |
| --- | ---: | ---: | ---: | ---: |
| Preguntas respondibles | 16 | 0,698 | 0,747 | 0,782 |
| Preguntas de abstención | 9 | 0,648 | 0,709 | 0,744 |

Las dos distribuciones siguen solapándose casi por completo. El mejor umbral
posible (0,698) acierta 20 de 25, pero deja un margen de 0,008 sobre la pregunta
respondible peor puntuada: cualquier pregunta correcta ligeramente peor quedaría
silenciada.

**Decisión: `RAG_SCORE_MINIMO = 0.65`**, que acierta 17 de 25. Se prefiere no
silenciar ninguna respuesta correcta y dejar que la abstención la resuelva el
centinela del prompt.

El valor por defecto en el código sigue siendo 0.0, es decir, con la compuerta de
score desactivada. El 0,65 se documenta en `.env.example` y debe fijarse en el
`.env` de cada entorno; no está activo por omisión.

Cinco preguntas sin respuesta en el corpus puntúan por encima de 0,70, entre
ellas la del evento deportivo (0,744) y la de los fotógrafos (0,736). Esto
confirma que un umbral de score por sí solo no basta.

### Verificación de la abstención

Pregunta: ¿Qué edificio del Retiro se caracteriza por su estilo neomudéjar?

- Score del mejor chunk: 0,709, por encima del umbral, así que la compuerta de
  score **no** la detuvo.
- Resultado: abstención, con motivo `el_modelo_no_vio_evidencia`.

Es la evidencia directa de que las dos compuertas son necesarias: el filtro
numérico dejó pasar la consulta y fue el centinela del prompt quien evitó que el
modelo respondiera desde su conocimiento propio, que sí incluye ese dato.

## Cómo ejecutarlo

    python scripts/validation/eval_preguntas.py            # top_k=3
    python scripts/validation/eval_preguntas.py --top-k 5  # comparación de top_k

El script usa el índice real de ChromaDB. Para probar sin clave de Gemini ni
índice, usa `--simulado`, que construye un índice temporal con embeddings
deterministas de juguete.
