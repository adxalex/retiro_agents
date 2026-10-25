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

Este documento deriva del inventario municipal del arbolado de Madrid.
Se han conservado exclusivamente los registros cuyo campo `NUM_PARQUE`
tiene el valor `1`, correspondiente al parque de El Retiro.

Los resultados describen la versión del dataset utilizada. No constituyen
un recuento en tiempo real.

## Magnitudes generales

- Árboles registrados: 16510.
- Especies diferentes: 163.
- Registros con altura válida: 16509.
- Registros sin altura disponible: 1.
- Identificadores `ASSETNUM` duplicados: 0.

## Estadísticas de altura

- Altura media: 9.45 metros.
- Desviación estándar: 5.31 metros.
- Altura mínima: 0.60 metros.
- Primer cuartil: 5.00 metros.
- Mediana: 9.00 metros.
- Tercer cuartil: 13.00 metros.
- Altura máxima: 32.00 metros.

La altura por sí sola no permite determinar la edad, salud,
el estado estructural o el riesgo de un árbol.

## Quince especies más frecuentes

1. `AESCULUS HIPPOCASTANUM`: 5652 ejemplares; 34.23 % del total; altura media de 10.75 metros.
2. `PLATANUS X HISPANICA`: 988 ejemplares; 5.98 % del total; altura media de 13.46 metros.
3. `CERCIS SILIQUASTRUM`: 687 ejemplares; 4.16 % del total; altura media de 5.60 metros.
4. `CELTIS AUSTRALIS`: 614 ejemplares; 3.72 % del total; altura media de 7.88 metros.
5. `CUPRESSUS SEMPERVIRENS`: 537 ejemplares; 3.25 % del total; altura media de 7.38 metros.
6. `GLEDITSIA TRIACANTHOS`: 495 ejemplares; 3.00 % del total; altura media de 12.13 metros.
7. `ULMUS MINOR`: 418 ejemplares; 2.53 % del total; altura media de 9.35 metros.
8. `STYPHNOLOBIUM JAPONICUM`: 402 ejemplares; 2.43 % del total; altura media de 10.27 metros.
9. `PRUNUS DULCIS`: 343 ejemplares; 2.08 % del total; altura media de 3.58 metros.
10. `PINUS PINEA`: 327 ejemplares; 1.98 % del total; altura media de 12.59 metros.
11. `ULMUS PUMILA`: 324 ejemplares; 1.96 % del total; altura media de 11.62 metros.
12. `ACER CAMPESTRE`: 320 ejemplares; 1.94 % del total; altura media de 7.47 metros.
13. `LIGUSTRUM JAPONICUM`: 307 ejemplares; 1.86 % del total; altura media de 7.15 metros.
14. `QUERCUS ILEX`: 301 ejemplares; 1.82 % del total; altura media de 7.71 metros.
15. `ROBINIA PSEUDOACACIA`: 288 ejemplares; 1.74 % del total; altura media de 11.36 metros.

Las quince especies más frecuentes reúnen 12003 ejemplares,
aproximadamente el 72.70 % del inventario.

## Distribución por rangos de altura

- Hasta 2 m: 767 ejemplares (4.65 %).
- Más de 2 hasta 5 m: 3675 ejemplares (22.26 %).
- Más de 5 hasta 10 m: 5482 ejemplares (33.20 %).
- Más de 10 hasta 15 m: 4353 ejemplares (26.37 %).
- Más de 15 hasta 20 m: 1722 ejemplares (10.43 %).
- Más de 20 hasta 30 m: 503 ejemplares (3.05 %).
- Más de 30 m: 7 ejemplares (0.04 %).
- No disponible: 1 ejemplares (0.01 %).

## Calidad de los datos

La agrupación por especie utiliza el texto del campo `ESPECIE` después
de eliminar espacios exteriores y convertirlo a mayúsculas.

No se ha realizado una reconciliación taxonómica de sinónimos,
variedades o posibles errores ortográficos.

El campo `PERIMETRO` se conserva en el CSV filtrado, pero no se utiliza
en este resumen porque la documentación consultada no especifica su
unidad de medida.

## Limitaciones

El inventario representa una fotografía administrativa del arbolado.
Las altas, bajas, sustituciones y correcciones posteriores pueden
modificar sus cifras.

El filtro utiliza `NUM_PARQUE = 1`. No incorpora registros del barrio
de Los Jerónimos que carezcan de número de parque o tengan un valor
diferente, porque no puede asegurarse que pertenezcan a El Retiro.

Las estadísticas no deben utilizarse para diagnósticos individuales,
evaluaciones de riesgo ni predicciones sobre ejemplares concretos.

## Transformación aplicada

1. Lectura del CSV municipal utilizando punto y coma como separador.
2. Filtrado de los registros con `NUM_PARQUE = 1`.
3. Normalización básica del campo `ESPECIE`.
4. Conversión de `ALTURA_TOTAL` a número decimal.
5. Comprobación de valores ausentes y duplicados.
6. Agrupación por especie.
7. Cálculo de estadísticas descriptivas y rangos de altura.
