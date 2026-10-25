# Banco de preguntas de evaluación — bloque B

## Propósito

Este documento reúne las preguntas candidatas de flora y fauna, arte y cultura
y actividades. Es un banco de trabajo: no implica que todas deban entrar en la
evaluación final del MVP.

Los identificadores de fuente indicados deben coincidir con los `document_id`
que finalmente produzca `load.py`. Si el equipo cambia alguno, debe actualizar
este documento y los fixtures JSON antes de ejecutar los tests.

## Criterios de uso

- Las respuestas no se comparan de manera literal: se comprueban hechos mínimos.
- Una pregunta directa supera la prueba cuando recupera la fuente esperada y
  contiene todos los hechos requeridos.
- En una pregunta multifuente se espera recuperar al menos una fuente pertinente;
  cuando la respuesta necesita realmente ambas, se indica expresamente.
- Las cifras históricas deben presentarse con su fecha y no como cifras actuales.
- Las actividades de entidades externas no deben presentarse como servicios
  oficiales del parque.
- Las preguntas que requieren información actual deben producir
  `abstuvo=true` si el sistema no dispone de una fuente fresca verificable.

## Identificadores documentales de referencia

- Senda Botánica: `flora_fauna__senda_botanica__madrid__v01`
- Plan Director: `flora_fauna__plan_director_arbolado__madrid__v01`
- Informe de expertos con OCR: `flora_fauna__informe_arbolado__madrid__v01_ocr`
- Inventario filtrado: `flora_fauna__inventario_arbolado_retiro__madrid__v01_filtrado`
- Resumen del inventario: `flora_fauna__resumen_inventario_arbolado_retiro__madrid__v01`
- Guía de aves: `flora_fauna__guia_aves_comunes__madrid__v01`
- Palacios: `arte_cultura__palacio_cristal_velazquez__museo_reina_sofia__v01`
- Paisaje de la Luz: `arte_cultura__retiro_paisaje_de_la_luz__fuentes_academicas_unesco__v01`
- Guía de actividades: `actividades__guia_retiro__fuentes_mixtas__v01`

> La guía de aves tiene alcance municipal. No debe describirse como un censo
> actual ni exclusivo de El Retiro.

## Flora, fauna y arbolado

### VEG-01 — Directa

**Pregunta:** ¿Cuántos tramos componen la Senda Botánica del Retiro?

**Fuente esperada:** Senda Botánica.

**Hechos requeridos:** siete tramos.

### VEG-02 — Directa

**Pregunta:** ¿Cuál es la longitud total aproximada de la Senda Botánica?

**Fuente esperada:** Senda Botánica.

**Hechos requeridos:** aproximadamente 8 km.

### VEG-03 — Enumeración

**Pregunta:** ¿Qué ámbitos recorre la Senda Botánica del Retiro?

**Fuente esperada:** Senda Botánica.

**Hechos requeridos:** jardines antiguos; Bosque del Recuerdo y Huerto del
Francés; Rosaleda; Campo Grande; jardines de Cecilio Rodríguez y Herrero
Palacios; antiguo Reservado; zona de Recreo.

**Regla:** admitir variaciones menores en los nombres, pero exigir los siete
ámbitos.

### VEG-04 — Descriptiva

**Pregunta:** Según la Senda Botánica, ¿qué elementos botánicos destacan en el
entorno de la Rosaleda?

**Fuente esperada:** Senda Botánica.

**Hechos requeridos:** pinos alrededor del jardín; un pino carrasco singular;
árboles exóticos o poco frecuentes en el sureste del parque.

### VEG-05 — Directa

**Pregunta:** ¿Qué árbol singular se encuentra junto al Palacio de Cristal?

**Fuente esperada:** Senda Botánica.

**Hechos requeridos:** ciprés de los pantanos o taxodio.

### VEG-06 — Comparativa

**Pregunta:** ¿Qué diferencia existe entre el diseño del Parterre y el del Campo
Grande?

**Fuente esperada:** Senda Botánica.

**Hechos requeridos:** Parterre geométrico o racionalista; Campo Grande
paisajista, natural o pintoresco.

### VEG-07 — Causal

**Pregunta:** ¿Por qué se elaboró el Plan Director del Arbolado del Retiro?

**Fuente esperada:** Plan Director.

**Hechos requeridos:** evaluación y gestión del arbolado; caídas de grandes
ejemplares; ausencia de signos externos evidentes en algunos casos.

### VEG-08 — Síntesis

**Pregunta:** ¿Qué factores condicionan la gestión del arbolado de El Retiro?

**Fuente esperada:** Plan Director.

**Hechos mínimos:** edad o estado; suelo o clima; uso público o entorno urbano;
valor histórico; renovación.

**Regla:** exigir al menos cuatro grupos de factores.

### VEG-09 — Directa histórica

**Pregunta:** ¿Qué categorías de edad o estado emplea el informe de expertos de
2014 para clasificar los árboles inventariados?

**Fuente esperada:** Informe de expertos con OCR.

**Hechos requeridos:** joven, maduro, viejo, decrépito y muerto.

### VEG-10 — Directa histórica

**Pregunta:** Según el informe de 2014, ¿qué ejemplares se consideran
prioritarios para tala o evaluación?

**Fuente esperada:** Informe de expertos con OCR.

**Hechos requeridos:** muertos prioritarios para tala; decrépitos analizados
después según su riesgo.

### VEG-11 — Técnica

**Pregunta:** ¿Qué métodos menciona el corpus para valorar el riesgo estructural
del arbolado?

**Fuente esperada:** Plan Director o informe de expertos con OCR.

**Hechos mínimos:** evaluación visual; VTA; mediciones o estudios instrumentales
cuando proceda.

### VEG-12 — Estructurada

**Pregunta:** ¿Qué información contiene el inventario municipal utilizado para
cada árbol?

**Fuente esperada:** inventario filtrado.

**Hechos requeridos:** identificador, parque, distrito, barrio, coordenadas,
especie, perímetro y altura total. Los nombres pueden expresarse con etiquetas
humanas o con los campos originales del CSV.

### VEG-13 — Recuperación temática

**Pregunta:** Según la guía incorporada al corpus, menciona tres especies de aves
documentadas en espacios verdes de Madrid.

**Fuente esperada:** guía de aves.

**Regla:** antes de automatizar este caso, registrar en el fixture una lista
cerrada de especies verificadas en la guía. La respuesta debe aclarar que no es
una observación en tiempo real ni un censo exclusivo de El Retiro.

### VEG-14 — Multifuente

**Pregunta:** ¿Cómo se relaciona la diversidad botánica de El Retiro con su
evolución histórica?

**Fuentes esperadas:** Senda Botánica y Plan Director.

**Hechos mínimos:** diseños históricos; reformas paisajistas; introducción de
especies ornamentales, frutales o exóticas; configuración de la diversidad
actual.

### VEG-15 — Multifuente

**Pregunta:** ¿Cómo combina la gestión de El Retiro la conservación histórica,
la seguridad y la renovación del arbolado?

**Fuentes esperadas:** Plan Director e informe de expertos con OCR.

**Hechos mínimos:** conservación del valor histórico o paisajístico; evaluación
de riesgos; renovación planificada de ejemplares envejecidos o deteriorados.

### VEG-16 — Directa histórica

**Pregunta:** ¿Cuántos árboles y especies registraba el arbolado de El Retiro en
noviembre de 2014 según el informe de expertos?

**Fuente esperada:** informe de expertos con OCR.

**Hechos requeridos:** 19.034 árboles; 167 especies; noviembre de 2014.

### VEG-17 — Estructurada histórica

**Pregunta:** ¿Cómo se distribuían por edad o estado los árboles de El Retiro
según el informe de 2014?

**Fuente esperada:** informe de expertos con OCR.

**Hechos requeridos:** 34,8 % jóvenes; 58,0 % maduros; 4,2 % viejos; 2,9 %
decrépitos; 0,1 % muertos.

### VEG-18 — Directa histórica

**Pregunta:** ¿Qué especies registraron más caídas completas de árboles en 2014
según el informe de expertos?

**Fuente esperada:** informe de expertos con OCR.

**Hechos requeridos:** `Pinus pinea`, 7 caídas y 24,14 %; `Pinus halepensis`, 3
caídas y 10,34 %. Las cifras de ejemplares pueden usarse como detalle adicional.

### VEG-19 — Enumeración histórica

**Pregunta:** ¿Qué especies registraron más roturas o caídas de ramas en 2014?

**Fuente esperada:** informe de expertos con OCR.

**Hechos requeridos:** `Gleditsia triacanthos`, 20; `Sophora japonica`, 19;
`Aesculus hippocastanum`, 15; `Platanus x hispanica`, 9.

### VEG-20 — Directa

**Pregunta:** ¿Qué extensión y número aproximado de árboles atribuye el Plan
Director del Arbolado al parque?

**Fuente esperada:** Plan Director.

**Hechos requeridos:** aproximadamente 120 hectáreas; unos 19.000 árboles.

### VEG-21 — Directa

**Pregunta:** ¿Cuántas zonas de gestión diferencia el Plan Director dentro del
parque?

**Fuente esperada:** Plan Director.

**Hechos requeridos:** diecisiete zonas.

### VEG-22 — Multifuente histórica

**Pregunta:** ¿Cómo se relacionan las cifras de arbolado del Plan Director y del
informe de expertos de 2014?

**Fuentes esperadas:** Plan Director e informe de expertos con OCR.

**Hechos requeridos:** el Plan Director ofrece una cifra aproximada de 19.000;
el informe registra 19.034 en noviembre de 2014; no deben presentarse como una
cifra actual.

### VEG-23 — Procedencia

**Pregunta:** ¿Qué entidad elaboró la guía de aves utilizada y desde cuándo
indica la fuente que trabaja en Madrid?

**Fuente esperada:** guía de aves.

**Hechos requeridos:** SEO/BirdLife; desde 1954.

**Prioridad:** baja para la evaluación final, por su escasa relación directa con
la experiencia turística de El Retiro.

### VEG-24 — Directa

**Pregunta:** ¿Qué fauna piscícola predomina en el Estanque Grande del Retiro?

**Fuente esperada:** flora_fauna**fauna_estanque_grande_retiro**fuentes_contrastadas\_\_v01.md

**Hechos requeridos:** carpas.

**Información complementaria:** también se han documentado peces gato y percasoles.

## Arte y cultura

### ART-01 — Directa

**Pregunta:** ¿En qué año se construyó el Palacio de Velázquez y con motivo de
qué exposición?

**Fuente esperada:** palacios.

**Hechos requeridos:** 1883; Exposición Nacional de Minería, Artes Metalúrgicas,
Cerámica, Cristalería y Aguas Minerales.

### ART-02 — Directa

**Pregunta:** ¿Para qué exposición se construyó el Palacio de Cristal y en qué
edificio se inspiró?

**Fuente esperada:** palacios.

**Hechos requeridos:** Exposición General de las Islas Filipinas de 1887;
Crystal Palace de Londres.

### ART-03 — Directa

**Pregunta:** ¿Qué altura tiene la cúpula acristalada del Palacio de Cristal?

**Fuente esperada:** palacios.

**Hechos requeridos:** 24 metros.

### ART-04 — Directa histórica

**Pregunta:** ¿Qué acontecimiento político tuvo lugar en el Palacio de Cristal
el 10 de mayo de 1936?

**Fuente esperada:** palacios.

**Hechos requeridos:** proclamación de Manuel Azaña como presidente de la
Segunda República.

### ART-05 — Enumeración

**Pregunta:** ¿Quién fue el arquitecto de los palacios de Cristal y Velázquez y
quiénes colaboraron con él en el Palacio de Velázquez?

**Fuente esperada:** palacios.

**Hechos requeridos:** Ricardo Velázquez Bosco; Alberto de Palacio; Bernardo
Asins; Germán y Daniel Zuloaga.

### ART-06 — Directa

**Pregunta:** ¿En qué año se inscribió el «Paseo del Prado y el Buen Retiro» en
la Lista del Patrimonio Mundial y en qué categoría?

**Fuente esperada:** Paisaje de la Luz.

**Hechos requeridos:** 2021; paisaje cultural.

### ART-07 — Directa

**Pregunta:** ¿Qué extensión aproximada tiene el bien declarado Patrimonio
Mundial y qué proporción corresponde a jardines?

**Fuente esperada:** Paisaje de la Luz.

**Hechos requeridos:** aproximadamente 219 hectáreas; alrededor del 75 %;
Paseo del Prado, Jardines del Buen Retiro y Real Jardín Botánico.

### ART-08 — Enumeración

**Pregunta:** ¿Qué instituciones creadas o consolidadas durante el reinado de
Carlos III reforzaron la relación entre naturaleza, ciencia y educación en el
entorno de El Retiro?

**Fuente esperada:** Paisaje de la Luz.

**Hechos requeridos:** Gabinete de Ciencias Naturales, actual Museo del Prado;
Real Jardín Botánico; Real Observatorio de Madrid.

### ART-09 — Multifuente

**Pregunta:** ¿Cómo contribuyen los palacios de Cristal y Velázquez al valor
cultural de El Retiro dentro del Paisaje de la Luz?

**Fuentes esperadas:** palacios y Paisaje de la Luz.

**Hechos mínimos:** arquitectura o función expositiva; integración con el
patrimonio vegetal y los jardines; relación entre artes, cultura y naturaleza.

## Actividades

Las respuestas de esta sección deben conservar la procedencia y distinguir los
servicios municipales de las iniciativas organizadas por entidades externas.
Los horarios, precios y programaciones requieren verificación fresca.

### ACT-01 — Enumeración

**Pregunta:** ¿Dónde se encuentra el Centro Deportivo Municipal La Chopera y qué
instalaciones describe la fuente?

**Fuente esperada:** guía de actividades.

**Hechos mínimos:** paseo de Fernán Núñez, 3; sala multiusos; musculación; campo
de fútbol 11; circuito de vida; pádel; pistas polideportivas; tenis;
accesibilidad para personas con movilidad reducida.

### ACT-02 — Directa

**Pregunta:** ¿Cuántas barcas describe la fuente municipal para el Estanque de
El Retiro y cuántas son accesibles para personas usuarias de silla de ruedas?

**Fuente esperada:** guía de actividades.

**Hechos requeridos:** cien barcas; dos accesibles.

**Advertencia:** presentar como dato de la fuente, no como disponibilidad en
tiempo real.

### ACT-03 — Directa

**Pregunta:** Según la información recogida, ¿cuál es la ocupación máxima y la
duración ordinaria de una sesión de barca?

**Fuente esperada:** guía de actividades.

**Hechos requeridos:** cuatro personas; 45 minutos; menores de 14 años
acompañados por una persona adulta.

### ACT-04 — Enumeración

**Pregunta:** ¿Qué tipos de actividades ofrece el Centro de Educación Ambiental
El Retiro según la guía?

**Fuente esperada:** guía de actividades.

**Hechos mínimos:** senda botánica; itinerarios guiados; actividades educativas;
horticultura o jardinería ecológica; ornitología; bicicleta urbana; huerto;
visitas al Vivero de Estufas. Exigir al menos cinco tipos.

### ACT-05 — Directa con procedencia

**Pregunta:** ¿Qué es La Cabaña y qué entidad aparece como organizadora?

**Fuente esperada:** guía de actividades.

**Hechos requeridos:** espacio de ajedrez y juegos de mesa; paseo de Cuba;
Asociación de Amigos del Retiro; entidad externa al servicio municipal.

### ACT-06 — Enumeración

**Pregunta:** ¿Qué modalidades de ajedrez describe la fuente para La Cabaña?

**Fuente esperada:** guía de actividades.

**Hechos requeridos:** torneos abiertos; partidas simultáneas; clases grupales.

### ACT-07 — Directa con procedencia

**Pregunta:** ¿Cómo describe la fuente a Retiro Running?

**Fuente esperada:** guía de actividades.

**Hechos requeridos:** comunidad social de running y power walking; reuniones
semanales; recorridos de distintas distancias; entidad no oficial.

### ACT-08 — Criterio de procedencia

**Pregunta:** ¿Debe presentarse el yoga organizado por Búho Zen como un servicio
oficial de El Retiro?

**Fuente esperada:** guía de actividades.

**Hechos requeridos:** no; iniciativa de una entidad externa; la programación
actual debe verificarse con la entidad.

### ACT-09 — Multifuente

**Pregunta:** ¿Qué relación tienen los palacios de Velázquez y Cristal con la
oferta cultural de El Retiro?

**Fuentes esperadas:** guía de actividades y palacios.

**Hechos requeridos:** sedes expositivas vinculadas al Museo Reina Sofía; la
disponibilidad y programación concreta deben consultarse en la fuente vigente.

## Preguntas de abstención

En todos estos casos se espera `abstuvo=true`. La respuesta puede aportar
contexto histórico, pero debe dejar claro que no dispone del dato actual,
predictivo o verificable solicitado.

### VEG-A01 — Cifra actual

**Pregunta:** ¿Cuántos árboles hay hoy exactamente en El Retiro?

**Comportamiento esperado:** abstenerse de dar una cifra exacta actual. Puede
indicar que el dataset filtrado registra 16.510 árboles, pero debe identificarlo
como fotografía administrativa del dataset y no como recuento en tiempo real.

### VEG-A02 — Predicción

**Pregunta:** ¿Qué árbol de El Retiro se caerá próximamente?

**Comportamiento esperado:** abstenerse; el corpus no permite predecir la caída
de un ejemplar concreto.

### VEG-A03 — Estado individual actual

**Pregunta:** ¿Cuál es el estado actual de cada árbol señalado en el mapa de la
Senda Botánica?

**Comportamiento esperado:** abstenerse; el mapa identifica ejemplares o
recorridos, pero no acredita su estado actual.

### VEG-A04 — Observación en tiempo real

**Pregunta:** ¿Qué aves se encuentran ahora mismo junto al Estanque Grande?

**Comportamiento esperado:** abstenerse; la guía no ofrece observaciones en
tiempo real.

### VEG-A05 — Garantía de permanencia

**Pregunta:** ¿Se puede garantizar que todos los árboles de la Senda Botánica
siguen existiendo actualmente?

**Comportamiento esperado:** abstenerse de garantizarlo; la fuente corresponde a
una fecha determinada.

### VEG-A06 — Actualidad

**Pregunta:** ¿Cuántos árboles se han caído en El Retiro este año?

**Comportamiento esperado:** abstenerse. Puede aclarar que el informe histórico
documenta 29 caídas hasta el 15 de noviembre de 2014, pero no responde al año
actual.

### VEG-A07 — Diagnóstico o predicción individual

**Pregunta:** ¿Qué árbol concreto del inventario se encuentra hoy en mal estado
o va a partirse?

**Comportamiento esperado:** abstenerse; los documentos no permiten diagnosticar
ni predecir el estado de un ejemplar concreto.

### ART-A01 — Apertura actual

**Pregunta:** ¿Está abierto hoy el Palacio de Cristal?

**Comportamiento esperado:** abstenerse y remitir a la información vigente del
Museo Reina Sofía. Cualquier cierre recogido en el corpus debe presentarse con
su fecha, no como estado actual.

### ART-A02 — Exposición actual

**Pregunta:** ¿Qué exposición se puede visitar hoy en el Palacio de Velázquez?

**Comportamiento esperado:** abstenerse y remitir a la programación vigente del
Museo Reina Sofía.

### ACT-A01 — Evento actual

**Pregunta:** ¿Hay hoy un torneo de ajedrez en La Cabaña?

**Comportamiento esperado:** abstenerse y remitir a la entidad organizadora; el
corpus no contiene programación en tiempo real.

### ACT-A02 — Horario variable

**Pregunta:** ¿A qué hora cierran hoy las barcas del Estanque Grande?

**Comportamiento esperado:** abstenerse y remitir a la fuente municipal vigente;
el horario puede variar durante el año.

### ACT-A03 — Agenda actual

**Pregunta:** ¿Qué actividades hay este fin de semana en El Retiro?

**Comportamiento esperado:** abstenerse y recomendar la agenda municipal o una
fuente actualizada.

### ACT-A04 — Normativa y autorización actual

**Pregunta:** ¿Puede circular libremente un vehículo de alquiler de bicicletas
por cualquier zona del parque?

**Comportamiento esperado:** abstenerse de garantizarlo y remitir a las normas
municipales vigentes. Una mención comercial no implica autorización.

## Selección mínima recomendada para el conjunto compartido

Si cada integrante aporta cuatro casos, la selección del bloque B podría ser:

1. `VEG-12`: recuperación estructurada del inventario.
2. `ART-06`: dato cultural directo y estable.
3. `ACT-02`: información práctica con advertencia de vigencia.
4. `VEG-A02` o `ACT-A03`: abstención por predicción o actualidad.

Esta selección deja espacio para las preguntas de los otros bloques y combina
recuperación, generación, procedencia y abstención.

## Traslado posterior a tests

El Markdown es la especificación humana. Para automatizarla deben crearse
fixtures JSON dentro de `queries/`:

```text
queries/
├── retrieval.json
├── generation.json
└── abstention.json
```

Cada caso automatizado debe contener como mínimo:

```json
{
  "id": "ART-06",
  "question": "¿En qué año se inscribió el Paseo del Prado y el Buen Retiro en la Lista del Patrimonio Mundial y en qué categoría?",
  "expected_document_ids": [
    "arte_cultura__retiro_paisaje_de_la_luz__fuentes_academicas_unesco__v01"
  ],
  "required_facts": [["2021"], ["paisaje cultural"]],
  "expected_abstention": false
}
```

No debe crearse el fixture definitivo hasta verificar los `document_id` contra
la salida real de `load.py`.
