# Alcance y fuentes del corpus · Retiro RAG

## 1. Tema

Asistente RAG sobre el parque de El Retiro. Combina información histórica, cultural, natural y práctica para responder con apoyo en documentos públicos y trazables.

## 2. Debe responder sobre

- Historia, monumentos y jardines.
- Flora, fauna, arte y cultura.
- Actividades y deporte.
- Itinerarios e información práctica.
- Normas, seguridad y emergencias.

## 3. Fuera de alcance

- Asuntos ajenos a El Retiro.
- Información no sustentada por el corpus.
- Datos actuales presentados como vigentes sin una fuente vigente.
- Sustitución de instrucciones oficiales de seguridad.
- Datos personales o fuentes obtenidas mediante scraping agresivo.

Sin evidencia suficiente, el asistente indicará que la información no está en los documentos disponibles.

## 4. Formatos y volumen

- PDF.
- Markdown.
- Un tercer formato acordado, preferiblemente CSV si aporta información estructurada.

El corpus debe contener al menos dos formatos. Como orientación, se seleccionarán entre 5 y 20 documentos relevantes, evitando redundancias.

## 5. Reparto

- Alex: historia, monumentos y jardines.
- Alejandra: flora/fauna, arte/cultura y actividades.
- David: itinerarios, información práctica y seguridad.

## 6. Ficha de cada fuente

```markdown
### Título

- Institución o autor:
- URL:
- Fecha de consulta o descarga:
- Formato:
- Nombre del archivo local:
- Categoría:
- `corpus_group`:
- Motivo de inclusión:
- Fecha de vigencia:
- Observaciones de calidad:
```

## 7. Inventario

### Rutas a pie por el Parque del Retiro

- Institución o autor: rutas «Lo esencial del Retiro» y «Recorrido completo por el interior»: recorrido propuesto por el equipo del proyecto; datos de los lugares según esMadrid (Turismo de Madrid). Ruta de las 18 puertas: fuentes de la ficha siguiente.
- URL: https://www.esmadrid.com/informacion-turistica/parque-del-retiro
- Fecha de consulta o descarga: 10/09/2026 (página actualizada el 19/08/2026).
- Formato: PDF (generado con `scripts/corpus/generar_itinerarios.py`).
- Nombre del archivo local: `itinerarios__rutas_a_pie__retiro__v01.pdf`
- Categoría: `itinerarios`
- `corpus_group`: `itinerarios_informacion_practica_seguridad`
- Motivo de inclusión: preguntas de visitantes sobre recorridos a pie, accesos y puertas.
- Fecha de vigencia: datos de lugares vigentes a 19/08/2026; distancias y duraciones sin fecha.
- Observaciones de calidad: esMadrid no publica estas dos rutas; describe los lugares, no el recorrido. El orden de las paradas, la distancia (2,5 km y 5–6 km) y la duración son orientativos del equipo y el documento lo declara. Corregido «Puerta de Alcalá» por «Puerta de la Independencia» y el orden del lado oeste (Ángel Caído, Murillo, Felipe IV, España). El orden intermedio del lado este (América Española, Herrero Palacios, Granada) no está verificado. Eliminada la mención a pavos reales, que no figura en la fuente.

### Las 18 puertas del Retiro (fuentes de la ruta perimetral)

- Institución o autor: Una Ventana desde Madrid; Rutas Tranquilas Madrileñas; Wikipedia; esMadrid (Ayuntamiento de Madrid).
- URL:
  - https://www.unaventanadesdemadrid.com/retiro-puertas-y-entradas.html
  - https://www.unaventanadesdemadrid.com/madrid/retiro-zona-recreo.html (Puerta de Hernani)
  - https://rutastranquilasmadrileñas.es/jardines-y-parques/las-puertas-del-retiro/ (clasificación de las 18 puertas, Puerta de Dante)
  - https://es.wikipedia.org/wiki/Puerta_de_Madrid_(Retiro)
  - https://www.esmadrid.com/informacion-turistica/puerta-felipe-iv
- Fecha de consulta o descarga: 10/09/2026.
- Formato: web, integrada en el PDF de rutas a pie.
- Nombre del archivo local: `itinerarios__rutas_a_pie__retiro__v01.pdf`
- Categoría: `itinerarios`
- `corpus_group`: `itinerarios_informacion_practica_seguridad`
- Motivo de inclusión: ubicación y orden de las puertas para la ruta perimetral.
- Fecha de vigencia: datos históricos y de ubicación, estables.
- Observaciones de calidad: Una Ventana desde Madrid bloqueó la descarga automática; los datos se contrastaron con los fragmentos indexados por el buscador y con las demás fuentes. Tripadvisor sitúa el traslado de la Puerta de Felipe IV en 1922; se adopta 1880, según esMadrid.

### Circuitos para correr en el Parque del Retiro

- Institución o autor: VG Running (escuela de running de Víctor García).
- URL: https://www.vgrunning.com/correr-retiro-madrid/
- Fecha de consulta o descarga: 10/09/2026 (artículo publicado el 05/10/2017, actualizado el 12/12/2018).
- Formato: PDF (generado con `scripts/corpus/generar_itinerarios.py`).
- Nombre del archivo local: `itinerarios__circuitos_running__retiro__v01.pdf`
- Categoría: `itinerarios`
- `corpus_group`: `itinerarios_informacion_practica_seguridad`
- Motivo de inclusión: circuitos con distancia, terreno e iluminación para preguntas sobre correr.
- Fecha de vigencia: 2018; el estado de la iluminación o del firme puede haber cambiado.
- Observaciones de calidad: texto parafraseado; sin mapas. Añadidos los tramos de series de 500 m y 1.000 m que recoge la fuente. Eliminados los «consejos prácticos» y la «seguridad para corredores», que no aparecen en la fuente.

### Montar en bicicleta en el Parque del Retiro

- Institución o autor: Ayuntamiento de Madrid; Madrid 360; Zona Retiro (L. Torres).
- URL:
  - https://www.madrid.es/portales/munimadrid/es/Inicio/Actualidad/Noticias/Entra-en-vigor-la-Ordenanza-de-Movilidad-Sostenible-para-mejorar-la-convivencia-vial/?vgnextchannel=a12149fa40ec9410VgnVCM100000171f5a0aRCRD&vgnextfmt=default&vgnextoid=6e9ec3f4b80a6610VgnVCM2000001f4a900aRCRD
  - https://www.madrid360.es/movilidad-sostenible/ordenanza-de-movilidad-sostenible/
  - https://zonaretiro.com/deportes/montar-bicicleta-retiro/ (licencia CC BY-NC 3.0 ES)
- Fecha de consulta o descarga: 10/09/2026.
- Formato: PDF (generado con `scripts/corpus/generar_itinerarios.py`).
- Nombre del archivo local: `informacion_practica__bicicleta__retiro__v01.pdf`
- Categoría: `informacion_practica`
- `corpus_group`: `itinerarios_informacion_practica_seguridad`
- Motivo de inclusión: normativa de circulación en parques, carril bici y alquiler.
- Fecha de vigencia: normativa 2018 y modificación posterior (Madrid 360, 2022); carril bici y alquiler, 2017.
- Observaciones de calidad: el precio correcto de la fuente es ~24 €/día (el PDF anterior decía 34 €). Eliminadas las «zonas prohibidas», «normas» y «consejos», que no figuran en la fuente. Se omite la sugerencia de Zona Retiro de salir del carril bici por los senderos, porque contradice la ordenanza. Conviene comprobar el texto consolidado vigente de la ordenanza.

## Inventario de fuentes de itinerarios, información práctica y seguridad

| Archivo local | Categoría | Formato | Fuente | Descarga | Responsable | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| itinerarios_pie_retiro_.pdf | itinerarios | PDF | esMadrid (lugares; recorrido propio del equipo); Una Ventana desde Madrid, Rutas Tranquilas Madrileñas, Wikipedia | 10/09/2026 | David | Por revisar |
| itinerarios_running_retiro_.pdf | itinerarios | PDF | VG Running | 10/09/2026 | David | Por revisar |
| informacion_practica_bicicleta_retiro.pdf | informacion_practica | PDF | Ayuntamiento de Madrid, Madrid 360, Zona Retiro | 10/09/2026 | David | Por revisar |
| informacion_practica_guia_visitante_retiro.pdf | informacion_practica | PDF | esMadrid, Museo Reina Sofía, Ayuntamiento de Madrid, Noticias Retiro | 11/09/2026 | David | Por revisar |
| seguridad_protocolo_alertas_retiro.pdf | seguridad | PDF | Ayuntamiento de Madrid, esMadrid | 11/09/2026 | David | Por revisar |

Estados posibles: `candidato`, `por revisar`, `aceptado` y `excluido`.

## 8. Criterios de aceptación

Una fuente entra en el corpus cuando:

1. Su procedencia y URL están documentadas.
2. Tiene relación directa con el alcance.
3. Su contenido puede cargarse correctamente.
4. No duplica innecesariamente otra fuente.
5. Su vigencia se entiende.
6. No contiene secretos ni datos personales innecesarios.
7. Puede utilizarse con fines educativos.

Si se excluye, se registra el motivo.

## 9. Cinco preguntas iniciales

1. ¿Qué función tuvo históricamente el parque de El Retiro?
2. ¿Qué es el Palacio de Cristal?
3. ¿Qué interés tiene la Rosaleda?
4. ¿Qué actividades se pueden realizar en el parque?
5. ¿Qué accesos o normas debe conocer una persona visitante?

Las preguntas formales de evaluación vivirán en `queries/` e incluirán al menos una fuera del corpus.

## 10. Declaración de uso

El equipo utilizará información pública con finalidad educativa. Las claves se guardarán únicamente en `.env`, fuera del control de versiones.
