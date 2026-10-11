---
document_id: flora_fauna__resumen_inventario_arbolado_retiro__madrid__v01
title: Resumen descriptivo del inventario del arbolado de El Retiro
category: flora_fauna
topic: Inventario del arbolado
source_organization: Ayuntamiento de Madrid
language: es
version: 1
derived_from: flora_fauna__inventario_arbolado__madrid__v01
transformation: filtrado por NUM_PARQUE igual a 1 y agregación estadística
review_status: pendiente_revision
---

# Resumen descriptivo del inventario del arbolado de El Retiro

## Alcance

Este documento presenta un resumen estadístico del inventario municipal de árboles correspondiente al parque de El Retiro. El conjunto deriva del inventario general del arbolado de Madrid y conserva únicamente los registros cuyo campo `NUM_PARQUE` tiene el valor `1`.

Los resultados describen la versión del conjunto de datos utilizada para el análisis. No constituyen un recuento en tiempo real ni garantizan que todos los ejemplares continúen presentes en la fecha de consulta.

## Magnitudes generales

El inventario filtrado contiene 16.510 árboles y 163 especies diferentes. De los 16.510 registros, 16.509 disponen de una altura válida y uno carece de este dato.

No se encontraron valores duplicados en el campo `ASSETNUM`, utilizado como identificador de cada ejemplar. Por tanto, cada uno de los 16.510 registros analizados posee un identificador diferente dentro del conjunto filtrado.

## Distribución de las alturas

La altura media registrada es de 9,45 metros y la mediana es de 9 metros. La proximidad entre ambos valores indica que el centro de la distribución se encuentra aproximadamente entre los 9 y los 9,5 metros.

El primer cuartil es de 5 metros: aproximadamente una cuarta parte de los árboles con altura informada mide 5 metros o menos. El tercer cuartil es de 13 metros: aproximadamente tres cuartas partes miden 13 metros o menos y una cuarta parte supera esa altura.

La altura mínima registrada es de 0,60 metros y la máxima, de 32 metros. La desviación estándar es de 5,31 metros, lo que refleja una variación considerable de alturas alrededor de la media.

Resumen estadístico de las alturas:

- Registros con altura válida: 16.509.
- Altura media: 9,45 metros.
- Desviación estándar: 5,31 metros.
- Altura mínima: 0,60 metros.
- Primer cuartil: 5 metros.
- Mediana: 9 metros.
- Tercer cuartil: 13 metros.
- Altura máxima: 32 metros.

Estos valores son descriptivos. La altura por sí sola no permite determinar la edad, salud, singularidad o riesgo estructural de un árbol.

## Especies más frecuentes

La especie más numerosa del inventario es `AESCULUS HIPPOCASTANUM`, con 5.652 ejemplares. Representa el 34,23 % de todos los árboles registrados en El Retiro y tiene una altura media de 10,75 metros.

La segunda especie más frecuente es `PLATANUS X HISPANICA`, con 988 ejemplares, equivalentes al 5,98 % del inventario. Su altura media es de 13,46 metros, la mayor altura media entre las quince especies más frecuentes.

Las quince especies con mayor número de ejemplares son:

1. `AESCULUS HIPPOCASTANUM`: 5.652 ejemplares; 34,23 % del total; altura media de 10,75 metros.
2. `PLATANUS X HISPANICA`: 988 ejemplares; 5,98 %; altura media de 13,46 metros.
3. `CERCIS SILIQUASTRUM`: 687 ejemplares; 4,16 %; altura media de 5,60 metros.
4. `CELTIS AUSTRALIS`: 614 ejemplares; 3,72 %; altura media de 7,88 metros.
5. `CUPRESSUS SEMPERVIRENS`: 537 ejemplares; 3,25 %; altura media de 7,38 metros.
6. `GLEDITSIA TRIACANTHOS`: 495 ejemplares; 3,00 %; altura media de 12,13 metros.
7. `ULMUS MINOR`: 418 ejemplares; 2,53 %; altura media de 9,35 metros.
8. `STYPHNOLOBIUM JAPONICUM`: 402 ejemplares; 2,43 %; altura media de 10,27 metros.
9. `PRUNUS DULCIS`: 343 ejemplares; 2,08 %; altura media de 3,58 metros.
10. `PINUS PINEA`: 327 ejemplares; 1,98 %; altura media de 12,59 metros.
11. `ULMUS PUMILA`: 324 ejemplares; 1,96 %; altura media de 11,62 metros.
12. `ACER CAMPESTRE`: 320 ejemplares; 1,94 %; altura media de 7,47 metros.
13. `LIGUSTRUM JAPONICUM`: 307 ejemplares; 1,86 %; altura media de 7,15 metros.
14. `QUERCUS ILEX`: 301 ejemplares; 1,82 %; altura media de 7,71 metros.
15. `ROBINIA PSEUDOACACIA`: 288 ejemplares; 1,74 %; altura media de 11,36 metros.

## Composición del inventario

Las quince especies más frecuentes reúnen 12.003 ejemplares, aproximadamente el 72,70 % del inventario. Las otras 148 especies representan conjuntamente el 27,30 % restante.

Aunque el inventario contiene 163 especies, su distribución no es uniforme. `AESCULUS HIPPOCASTANUM` concentra por sí sola algo más de un tercio de los ejemplares. Esta concentración describe la composición numérica del conjunto, pero no permite valorar por sí sola la diversidad ecológica, la distribución espacial ni el estado de conservación del parque.

Entre las quince especies más frecuentes, `PLATANUS X HISPANICA`, `PINUS PINEA` y `GLEDITSIA TRIACANTHOS` presentan alturas medias superiores a 12 metros. `PRUNUS DULCIS` presenta la menor altura media de este grupo, con 3,58 metros.

Las diferencias de altura media entre especies pueden estar relacionadas con su porte, edad, ubicación, manejo o composición de los ejemplares inventariados. El dataset resumido no permite atribuir las diferencias a una causa concreta.

## Calidad de los datos

La cobertura del campo de altura es muy alta: 16.509 de los 16.510 registros contienen un valor válido, aproximadamente el 99,99 % del conjunto. Solo se detectó una altura no disponible.

No se encontraron identificadores `ASSETNUM` duplicados. Esta comprobación reduce el riesgo de contar dos veces el mismo registro, aunque no demuestra por sí sola que no existan duplicados físicos asociados a identificadores distintos.

Los nombres de las especies se han agrupado según el texto del campo `ESPECIE` después de eliminar espacios exteriores y convertirlo a mayúsculas. No se ha efectuado una reconciliación taxonómica avanzada de sinónimos, variedades o posibles errores de escritura.

## Limitaciones

El inventario representa una fotografía administrativa del arbolado en la versión descargada. Las altas, bajas, sustituciones y correcciones posteriores pueden modificar el número de árboles, su altura y la frecuencia de las especies.

El filtrado se basa en que `NUM_PARQUE` sea igual a `1`. Los registros del barrio de Los Jerónimos que carecen de número de parque o tienen otro valor no se han incorporado, porque no puede asegurarse que pertenezcan al recinto de El Retiro.

El campo `PERIMETRO` se conserva en el CSV derivado, pero no se interpreta en este resumen porque la documentación consultada no especifica su unidad de medida.

Las alturas se describen en metros de acuerdo con el campo `ALTURA_TOTAL`. Las estadísticas no deben utilizarse para realizar diagnósticos individuales, evaluaciones de riesgo ni recomendaciones de intervención sobre ejemplares concretos.

## Transformación aplicada

El proceso de preparación siguió estas operaciones:

1. Lectura del CSV municipal utilizando el punto y coma como separador.
2. Conservación de los registros cuyo `NUM_PARQUE` es igual a `1`.
3. Normalización básica del nombre de la especie mediante espacios exteriores y mayúsculas.
4. Conversión de `ALTURA_TOTAL` a un valor numérico, sustituyendo la coma decimal por punto cuando era necesario.
5. Comprobación de valores ausentes y duplicados en `ASSETNUM`.
6. Agrupación por especie para calcular frecuencia, porcentaje y altura media.
7. Cálculo de estadísticas descriptivas para las alturas válidas.

## Uso recomendado en el RAG

Este resumen es adecuado para responder preguntas agregadas, por ejemplo:

- ¿Cuántos árboles aparecen en el inventario de El Retiro?
- ¿Cuántas especies diferentes registra el dataset?
- ¿Cuál es la especie más frecuente?
- ¿Qué porcentaje representa `AESCULUS HIPPOCASTANUM`?
- ¿Cuál es la altura media o mediana de los árboles inventariados?
- ¿Cuáles son las especies más numerosas?
- ¿Qué especies frecuentes presentan mayor altura media?

No debe utilizarse para responder cuál es el número exacto de árboles presentes hoy, identificar árboles individuales, diagnosticar su estado o predecir caídas.
