"""Genera los PDF del bloque itinerarios / información práctica / seguridad del corpus Retiro RAG.

Diseño pensado para el pipeline load -> chunk:
- Un documento por modalidad (una sola category por documento, según el contrato).
- Sin pies de página numerados ni marcadores de lista (evita ruido en los chunks).
- Sin imágenes: los mapas no se extraen como texto y solo añaden peso.
- Cada sección empieza con su título, su fuente y una ficha de datos clave,
  para que el nombre de la ruta y sus cifras caigan en el mismo chunk.

Uso (desde la raíz del repo):
    pip install reportlab
    python scripts/corpus/generar_itinerarios.py
    python scripts/corpus/generar_itinerarios.py --salida otra/carpeta
"""

import argparse
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

# Referencia breve dentro del PDF (URL completa y fecha de consulta en docs/corpus/alcance_y_fuentes.md).
# Mantenerlas cortas: todo lo que se escribe aquí ocupa espacio en los chunks.
FUENTES = {
    "esmadrid_retiro": "esMadrid (Turismo de Madrid), «Parque de El Retiro», actualizado el 19/08/2026.",
    "puertas": "Una Ventana desde Madrid, «El Retiro, sus puertas y entradas»; Rutas Tranquilas "
               "Madrileñas, «Las puertas del Retiro» (2021); Wikipedia; esMadrid.",
    "vgrunning": "VG Running, «Correr en el Parque del Retiro» (2017, actualizado en 2018).",
    "ordenanza": "Ayuntamiento de Madrid (nota de prensa de 23/10/2018) y Madrid 360 (2022), "
                 "Ordenanza de Movilidad Sostenible.",
    "zonaretiro": "Zona Retiro, «Montar en bicicleta por el Retiro» (23/05/2017), CC BY-NC 3.0 ES.",
    "reinasofia": "Museo Nacional Centro de Arte Reina Sofía, «Horarios y tarifas», consultado el 11/09/2026.",
    "perros": "Ayuntamiento de Madrid, «Los perros en los parques de Madrid» (madrid.es).",
    "aseos": "Noticias Retiro, informe de la Asociación de Amigos del Buen Retiro (30/09/2025).",
    "protocolo_nota": "Ayuntamiento de Madrid, nota de prensa del 18/06/2026 sobre los protocolos de parques.",
    "estado_cierre": "Ayuntamiento de Madrid, «Estado de cierre y apertura de algunos parques en Madrid».",
    "lista_restricciones": "Ayuntamiento de Madrid, lista de parques con restricciones por tipo de alerta (24/06/2026).",
}


def origen_recorrido_propio() -> str:
    return (
        "Origen: recorrido propuesto por el equipo del proyecto a partir de los lugares que destaca "
        f"{FUENTES['esmadrid_retiro']} El orden de las paradas, la distancia y la duración son "
        "orientativos y no proceden de esa fuente."
    )


def documentos() -> dict[str, list[tuple[str, str]]]:
    return {
        "itinerarios__rutas_a_pie__retiro__v01.pdf": [
            ("h1", "Rutas a pie por el Parque del Retiro (Madrid)"),
            ("p", "Tres recorridos a pie: dos por el interior del parque y uno por el exterior "
                  "que pasa por sus 18 puertas."),

            ("h2", "Ruta a pie: Lo esencial del Retiro"),
            ("src", origen_recorrido_propio()),
            ("ficha", "Ficha de la ruta Lo esencial del Retiro (datos orientativos del equipo). "
                      "Distancia aproximada: 2,5 km. Duración aproximada: 30–35 minutos. Dificultad: "
                      "muy suave. Terreno: llano. Apta para cualquier acompañante."),
            ("p", "Paso 1 de 6 — Entrada por la Puerta de la Independencia, en la Plaza de la "
                  "Independencia, frente a la Puerta de Alcalá."),
            ("p", "Paso 2 de 6 — Seguir el paseo hasta el Estanque Grande, que ofrece barcas de remo "
                  "y la Escuela Municipal de Piragüismo, dirigida a niños y jóvenes de 7 a 17 años "
                  "(según esMadrid)."),
            ("p", "Paso 3 de 6 — Bordear el Estanque hasta el Monumento a Alfonso XII, proyectado por "
                  "el arquitecto José Grases Riera, con un mirador sobre la ciudad (según esMadrid)."),
            ("p", "Paso 4 de 6 — Subir hacia el Paseo de las Estatuas (Paseo de la Argentina), un "
                  "paseo corto flanqueado por esculturas de reyes."),
            ("p", "Paso 5 de 6 — Cruzar hacia el Parterre Francés, donde está el ahuehuete, del que "
                  "se dice que podría tener unos 400 años. Según esMadrid, el árbol más antiguo del "
                  "Retiro es hoy un olivo de 627 años plantado cerca de la Puerta del Ángel Caído."),
            ("p", "Paso 6 de 6 — Salida por la Puerta de Felipe IV, en la calle de Alfonso XII, "
                  "frente al Casón del Buen Retiro."),
            ("p", "Qué se ve en la ruta Lo esencial del Retiro: Estanque Grande, Monumento a "
                  "Alfonso XII, Paseo de las Estatuas y Parterre Francés."),

            ("h2", "Ruta a pie: las 18 puertas del Retiro"),
            ("src", f"Fuentes: {FUENTES['puertas']}"),
            ("ficha", "Ficha de la ruta de las 18 puertas. Recorrido: perimetral, por el exterior "
                      "del parque, en el sentido de las agujas del reloj, con inicio y final en la "
                      "Puerta de la Independencia. Calles que se recorren: Alcalá y O'Donnell "
                      "(norte), avenida de Menéndez Pelayo (este) y calle de Alfonso XII (oeste). "
                      "El perímetro del parque ronda los 4,5 km, según VG Running."),
            ("p", "Clasificación de las 18 puertas. Monumentales (4): España, Felipe IV, Madrid e "
                  "Independencia. Con valor patrimonial (5): Ángel Caído, Dante, Hernani, Granada y "
                  "O'Donnell. Secundarias (9): América Española, Doce de Octubre, Herrero Palacios, "
                  "Lagasca, Mariano de Cavia, Murillo, Niño Jesús, Reina Mercedes y Sainz de Baranda."),
            ("h3", "Puertas del lado norte (calles de Alcalá y O'Donnell)"),
            ("p", "Puerta de la Independencia: en la Plaza de la Independencia, frente a la Puerta "
                  "de Alcalá. La instaló José Urioste en 1885 reutilizando la puerta del jardín del "
                  "Casino de la Reina."),
            ("p", "Puerta de Hernani: en la calle de Alcalá, a la altura de la calle Lagasca; da al "
                  "Paseo del Salón del Estanque. La puerta metálica original de 1888 fue sustituida "
                  "por otra más monumental de Cecilio Rodríguez."),
            ("p", "Puerta de Lagasca: unos 30 metros después de la de Hernani, frente a la calle "
                  "Lagasca. Es secundaria y suele estar cerrada."),
            ("p", "Puerta de Madrid: en el cruce de la calle de Alcalá con la calle de O'Donnell. "
                  "Monumental, obra de José Urioste fechada en 1900, abre al Paseo de Coches o del "
                  "Duque de Fernán Núñez."),
            ("p", "Puerta de O'Donnell: en la esquina de la calle de O'Donnell con la avenida de "
                  "Menéndez Pelayo."),
            ("h3", "Puertas del lado este (avenida de Menéndez Pelayo)"),
            ("p", "Puerta de la América Española: acceso secundario."),
            ("p", "Puerta de la Reina Mercedes: acceso secundario frente a la calle de Ibiza."),
            ("p", "Puerta de Sainz de Baranda: acceso secundario a la altura de la calle del "
                  "Alcalde Sainz de Baranda."),
            ("p", "Puerta del Doce de Octubre: acceso secundario a la altura de la calle del Doce "
                  "de Octubre."),
            ("p", "Puerta de Herrero Palacios: acceso secundario."),
            ("p", "Puerta de Granada: puerta con valor patrimonial."),
            ("p", "Puerta del Niño Jesús: acceso secundario frente al Hospital Infantil "
                  "Universitario Niño Jesús."),
            ("p", "Puerta de Dante: cerca de la plaza de Mariano de Cavia; fue ornamentada y "
                  "dedicada a Dante en 1969."),
            ("h3", "Puertas de los lados sur y oeste (plaza de Mariano de Cavia y calle de Alfonso XII)"),
            ("p", "Puerta de Mariano de Cavia: en la plaza del mismo nombre, con escaleras por el "
                  "desnivel entre la calle y el parque."),
            ("p", "Puerta del Ángel Caído: construida en 2001, es la más cercana a la estación de "
                  "Atocha. Da acceso al Paseo del Duque de Fernán Núñez, que lleva a la Fuente del "
                  "Ángel Caído."),
            ("p", "Puerta de Murillo: en la calle de Alfonso XII, unos 300 metros al norte de la "
                  "Puerta del Ángel Caído."),
            ("p", "Puerta de Felipe IV: en la calle de Alfonso XII, frente al Casón del Buen Retiro, "
                  "y da entrada al Jardín del Parterre. Se levantó en 1680 junto al Paseo del Prado "
                  "y se trasladó a su emplazamiento actual en 1880."),
            ("p", "Puerta de España: en la calle de Alfonso XII, obra de José Urioste. Tras ella, "
                  "unos 400 metros al norte, se cierra la vuelta en la Puerta de la Independencia."),

            ("h2", "Ruta a pie: recorrido completo por el interior"),
            ("src", origen_recorrido_propio()),
            ("ficha", "Ficha del recorrido completo por el interior (datos orientativos del equipo). "
                      "Distancia aproximada: 5–6 km. Duración aproximada: entre 1 hora y 1 hora y 30 "
                      "minutos. Apto para cualquier acompañante."),
            ("p", "Tramo 1 de 6 — Entrada por la Puerta de la Independencia y paseo hasta el Estanque "
                  "Grande."),
            ("p", "Tramo 2 de 6 — Vuelta completa al Estanque Grande, con las barcas de remo y el "
                  "Monumento a Alfonso XII en su orilla."),
            ("p", "Tramo 3 de 6 — Subida por los caminos interiores hasta el Palacio de Cristal, "
                  "pabellón creado para la Exposición de Filipinas de 1887 y uno de los principales "
                  "ejemplos de la arquitectura del hierro en España (según esMadrid)."),
            ("p", "Tramo 4 de 6 — Del Palacio de Cristal al Palacio de Velázquez, ambos salas de "
                  "exposiciones del Museo Reina Sofía, y después a los Jardines de Cecilio Rodríguez, "
                  "jardines clasicistas con aires andaluces (según esMadrid)."),
            ("p", "Tramo 5 de 6 — Paso por la Rosaleda, con su colección de rosas, y continuación por "
                  "el Paseo de Coches."),
            ("p", "Tramo 6 de 6 — Paso por el Parterre Francés y salida por la Puerta de Felipe IV, "
                  "frente al Casón del Buen Retiro."),
            ("p", "Qué se ve en el recorrido completo por el interior: Estanque Grande, Monumento a "
                  "Alfonso XII, Palacio de Cristal, Palacio de Velázquez, Jardines de Cecilio "
                  "Rodríguez, Rosaleda, Paseo de Coches y Parterre Francés."),
        ],

        "itinerarios__circuitos_running__retiro__v01.pdf": [
            ("h1", "Circuitos para correr en el Parque del Retiro (Madrid)"),
            ("src", f"Fuente de todo el documento: {FUENTES['vgrunning']}"),
            ("p", "Según VG Running, el perímetro del parque ronda los 4,5 km y ofrece terrenos "
                  "variados (tierra, césped, asfalto y escaleras), con zonas llanas y cuestas. La "
                  "escuela lo considera especialmente adecuado para series, fartlek y cambios de "
                  "ritmo."),
            ("p", "Nota: los momentos del día que recomienda la fuente se refieren a la iluminación "
                  "de cada circuito y deben entenderse siempre dentro del horario de apertura del "
                  "parque, que este documento no recoge."),

            ("h2", "Circuito de running: perímetro (4,0 km)"),
            ("ficha", "Ficha del circuito de perímetro. Distancia: 4,0 km. Mejor momento: cualquiera, "
                      "de día o de noche, porque está iluminado casi en su totalidad. Terreno: casi "
                      "todo tierra, con un tramo de asfalto en la cuesta del Ángel."),
            ("p", "Es el circuito más clásico para correr en el Retiro. Bordea prácticamente todo el "
                  "parque pegado a la valla, por lo que no tiene pérdida; esa franja junto a la "
                  "valla es también la de más tránsito. El tramo de asfalto coincide con la llamada "
                  "cuesta del Ángel, la más pronunciada del parque, de algo menos de 500 metros."),

            ("h2", "Circuito de running: Parterre (5,2 km)"),
            ("ficha", "Ficha del circuito del Parterre. Distancia: 5,2 km. Mejor momento: con luz "
                      "natural, porque algunos tramos no tienen iluminación artificial. Terreno: casi "
                      "todo tierra; se puede completar entero sin pisar asfalto."),
            ("p", "Es una variante más larga del circuito de perímetro que aprovecha rectas largas para "
                  "sumar kilómetros y pasa por el Parterre Francés. Poder hacerlo entero por tierra "
                  "lo hace recomendable, según la fuente, para corredores con problemas de lesiones."),

            ("h2", "Tramo de running para series cortas (500 m)"),
            ("ficha", "Ficha del tramo de series cortas. Distancia: 500 metros exactos. Ubicación: "
                      "Paseo de Coches, entre el Paseo de Venezuela y el Paseo de Uruguay. Terreno: "
                      "asfalto o franja de tierra paralela. Mejor momento: cualquiera; está iluminado "
                      "y señalizado."),
            ("p", "La recta permite hacer series rápidas de 500 metros o más cortas (200, 300 o "
                  "400 metros). Si la tierra no está en buenas condiciones, se puede correr por el "
                  "asfalto del Paseo de Coches."),

            ("h2", "Tramo de running para series medias y largas (1.000 m)"),
            ("ficha", "Ficha del tramo de series medias y largas. Distancia: 1.000 metros exactos. "
                      "Ubicación: Paseo de Coches, desde el Paseo de Venezuela hasta la glorieta del "
                      "Ángel Caído. Terreno: prácticamente llano, asfalto o tierra. Mejor momento: "
                      "cualquiera; la tierra es especialmente buena por las mañanas."),
            ("p", "Combinando idas y vueltas por este tramo se pueden hacer series de 2.000, 3.000 o "
                  "4.000 metros."),

            ("h2", "Tramo de running para cuestas (475 m)"),
            ("ficha", "Ficha del tramo de cuestas. Distancia: 475 metros, desde la puerta de entrada "
                      "del parque (justo pasadas las barreras de coches) hasta la glorieta del Ángel "
                      "Caído. Terreno: asfalto o laterales de tierra. Mejor momento: cualquiera, de "
                      "mañana, tarde o noche; está iluminado y señalizado."),
            ("p", "La fuente aconseja subir por el asfalto y hacer la recuperación bajando por la "
                  "tierra a ritmo suave, para no sobrecargar. Se puede ajustar la longitud y la "
                  "inclinación de cada cuesta y combinar el trabajo con carrera continua por el "
                  "parque."),
        ],

        "informacion_practica__bicicleta__retiro__v01.pdf": [
            ("h1", "Montar en bicicleta en el Parque del Retiro (Madrid)"),
            ("p", "Normativa municipal sobre bicicletas en parques, carril bici y alquiler en el "
                  "entorno del Retiro."),

            ("h2", "Bicicleta en el Retiro: normativa municipal"),
            ("src", f"Fuentes: {FUENTES['ordenanza']}"),
            ("p", "Según el Ayuntamiento de Madrid, la Ordenanza de Movilidad Sostenible, en vigor "
                  "desde octubre de 2018, solo permite a las bicicletas circular por los parques en "
                  "los itinerarios en los que estén autorizadas, y limita la velocidad a 5 km/h en "
                  "las sendas compartidas con peatones."),
            ("p", "Según Madrid 360, tras la modificación de la ordenanza las bicicletas pueden "
                  "circular por parques y jardines públicos urbanos en caminos de más de 3 metros de "
                  "ancho."),
            ("p", "Antes de circular conviene respetar la señalización del propio parque y comprobar "
                  "el texto vigente de la ordenanza."),

            ("h2", "Bicicleta en el Retiro: carril bici (dato de 2017)"),
            ("src", f"Fuente: {FUENTES['zonaretiro']}"),
            ("p", "En mayo de 2017, Zona Retiro describía un carril bici que recorre todo el lado "
                  "este del parque, desde la calle de O'Donnell hasta la zona del Ángel Caído, "
                  "pasando por el Paseo de Uruguay."),

            ("h2", "Bicicleta en el Retiro: alquiler (dato de 2017)"),
            ("src", f"Fuente: {FUENTES['zonaretiro']}"),
            ("p", "Según el mismo artículo de mayo de 2017, en el entorno del Retiro había empresas "
                  "de alquiler de bicicletas como Biciretiro, Bybike o 27Bikes, con un precio de "
                  "alrededor de 24 euros por día. Es un dato de 2017: la oferta y los precios "
                  "actuales pueden ser distintos."),
        ],

        "informacion_practica__guia_visitante__retiro__v01.pdf": [
            ("h1", "Información práctica para visitar el Parque del Retiro (Madrid)"),
            ("p", "Horarios, accesos, transporte, zonas, mascotas, servicios, actividades y lugares "
                  "destacados del Parque del Retiro, también llamado Jardines del Buen Retiro."),

            ("h2", "Horarios del Parque del Retiro"),
            ("src", f"Fuente: {FUENTES['esmadrid_retiro']}"),
            ("ficha", "Horario del parque. Abierto todos los días. De octubre a marzo (otoño e invierno): "
                      "de 6:00 a 22:00. De abril a septiembre (primavera y verano): de 6:00 a 0:00 "
                      "(medianoche). Entrada libre."),
            ("p", "Las áreas caninas del parque abren a las 7:30 y cierran con el cierre del parque."),
            ("p", "El horario puede verse alterado por el protocolo de alertas meteorológicas: con alerta "
                  "roja el parque se cierra (ver el documento de seguridad del Retiro)."),

            ("h2", "Horarios del Palacio de Velázquez y del Palacio de Cristal"),
            ("src", f"Fuente: {FUENTES['reinasofia']}"),
            ("ficha", "Horario de los palacios del Retiro, sedes expositivas del Museo Reina Sofía. De "
                      "abril a septiembre: de 10:00 a 21:00. De octubre a marzo: de 10:00 a 18:00. Entrada "
                      "gratuita. Las salas se desalojan 10 minutos antes del cierre."),
            ("p", "Abren todos los días excepto el 1 y el 6 de enero, el 1 de mayo, el 25 de diciembre y "
                  "los periodos de montaje de exposiciones. El 24 y el 31 de diciembre abren hasta las "
                  "17:00. El Palacio de Cristal puede cerrar los días de lluvia y de alerta de calor por "
                  "las características del edificio."),
            ("p", "Estado en septiembre de 2026: el Palacio de Velázquez reabrió el miércoles 24 de "
                  "junio. El Palacio de Cristal está cerrado temporalmente por mejoras arquitectónicas; "
                  "se puede ver la instalación artística que lo recubre por fuera."),

            ("h2", "Horarios y condiciones de actividades del Retiro"),
            ("src", f"Fuente: {FUENTES['esmadrid_retiro']}"),
            ("p", "Teatro de Títeres: programación estable todos los fines de semana."),
            ("p", "Escuela Municipal de Piragüismo, en el Estanque Grande: para niños y jóvenes de 7 a "
                  "17 años."),
            ("p", "Foso de los monos, en la antigua Casa de Fieras: visitas en grupo con cita previa "
                  "gestionadas por la dirección del parque."),
            ("p", "Visitas guiadas gratuitas del programa municipal Pasea Madrid."),
            ("p", "Audioguía oficial, disponible desde la primavera de 2026: recorrido de 38 puntos en "
                  "español, inglés y lengua de signos, accesible mediante códigos QR y la web municipal."),
            ("p", "Exposición temporal «Emociones en peligro. Fotografías de Tim Flach» en el parque, "
                  "hasta el 25 de septiembre de 2026, según la agenda de esMadrid."),

            ("h2", "Accesos y puertas del Retiro"),
            ("src", f"Fuente: {FUENTES['esmadrid_retiro']}"),
            ("ficha", "Accesos del parque. El Retiro tiene 18 entradas, de las cuales 14 son accesibles. "
                      "Dirección postal de referencia: Plaza de la Independencia, 7, 28001 Madrid."),
            ("p", "Mejoras de accesibilidad: bancos modelo Madrid que pueden usarse desde distintas "
                  "alturas, acceso mejorado a la fuente de beber de la plaza de Honduras y pavimento "
                  "renovado en los jardines de Herrero Palacios."),
            ("p", "El nombre y la ubicación de cada una de las 18 puertas se describen en el documento "
                  "de rutas a pie por el Retiro."),

            ("h2", "Transporte para llegar al Retiro"),
            ("src", f"Fuente: {FUENTES['esmadrid_retiro']}"),
            ("ficha", "Metro: Retiro (línea 2), Ibiza (línea 9), Atocha (línea 1) y Estación del Arte "
                      "(línea 1). Cercanías: Madrid-Atocha."),
            ("p", "Autobuses: 001, 1, 2, 5, 9, 10, 14, 15, 19, 20, 26, 27, 28, 32, 34, 37, 45, 51, "
                  "52, 53, 61, 63, 74, 146, 150, 152, 203, 215, C1, C2, C03 y E1. Búhos nocturnos: de "
                  "N1 a N27."),
            ("p", "Estaciones de BiciMAD cercanas: calle Valenzuela, 3; calle Antonio Maura, 13; calle "
                  "Espalter, 3; Museo del Prado (calle Felipe IV, 5); Puerta del Ángel Caído (avenida "
                  "de Alfonso XII, 54); Jardines de Cecilio Rodríguez (avenida de Menéndez Pelayo, 69); "
                  "Puerta de la Reina Mercedes (avenida de Menéndez Pelayo, frente al 33); Hospital "
                  "Niño Jesús (avenida de Menéndez Pelayo, 63); avenida de Menéndez Pelayo, 9; plaza de "
                  "Mariano de Cavia; Metro Príncipe de Vergara; Metro Retiro (calle Alcalá, 95); calle "
                  "Alcalá, 111; calle Ibiza, 16; y calle Pío Baroja, 8."),

            ("h2", "Zonas y espacios del Retiro"),
            ("src", f"Fuente: {FUENTES['esmadrid_retiro']}"),
            ("ficha", "Dimensiones del parque: 125 hectáreas y más de 15.000 árboles. Patrimonio Mundial "
                      "de la UNESCO, junto al Paseo del Prado, desde el 25 de julio de 2021 (Paisaje de "
                      "la Luz)."),
            ("p", "Jardines destacados: jardín de Vivaces; Jardines de Cecilio Rodríguez, clasicistas "
                  "con aires andaluces; jardines del Arquitecto Herrero Palacios; Montaña de los Gatos, "
                  "rehabilitada; la Rosaleda, con su colección de rosas; y el Parterre Francés, donde "
                  "está el ahuehuete."),
            ("p", "Reservado de Fernando VII, en la esquina de las calles O'Donnell y Menéndez Pelayo: "
                  "incluye la Casa del Pescador, la Montaña de los Gatos (reabierta tras dos décadas "
                  "cerrada) y la Casa del Contrabandista, que hoy acoge Florida Park, espacio de ocio y "
                  "hostelería."),
            ("p", "Entorno del Observatorio Meteorológico, rehabilitado: incluye un reservado, el jardín "
                  "isabelino del Castillo del Telégrafo y el Baño de la Elefanta. En la Huerta del "
                  "Francés está la noria de agua, restaurada y en funcionamiento."),
            ("p", "Equipamientos dentro del parque: Centro Deportivo Municipal La Chopera, Biblioteca "
                  "Pública Municipal Eugenio Trías y Centro Cultural Casa de Vacas."),

            ("h2", "Mascotas en el Retiro: normas para perros"),
            ("src", f"Fuentes: {FUENTES['perros']} {FUENTES['esmadrid_retiro']}"),
            ("ficha", "Perros en los parques de Madrid. Con carácter general deben ir con correa. Pueden "
                      "ir sueltos de 19:00 a 10:00 en el horario oficial de invierno y de 20:00 a 10:00 en "
                      "el horario oficial de verano, siempre dentro del horario de apertura del parque."),
            ("p", "En el Retiro, las áreas caninas abren de 7:30 hasta el cierre del parque."),
            ("p", "Los perros no pueden entrar en zonas infantiles, zonas de mayores ni en las áreas "
                  "donde se prohíba expresamente. Los perros calificados como potencialmente peligrosos "
                  "deben llevar siempre correa y bozal en lugares públicos."),
            ("p", "Cuando van sueltos, la persona responsable debe tenerlos a la vista y a una distancia "
                  "que le permita intervenir. Está prohibido que se bañen en fuentes ornamentales o "
                  "estanques y que beban directamente de grifos o caños de agua de uso público."),

            ("h2", "Servicios del Retiro"),
            ("src", f"Fuente: {FUENTES['esmadrid_retiro']}"),
            ("ficha", "Servicios que indica esMadrid para el Retiro: alquiler de barcas, alquiler de "
                      "bicicletas en los alrededores, biblioteca, cafetería, restauración y restaurante, "
                      "circuito de running, puntos de información, senda botánica, visitas guiadas, zona "
                      "de picnic y zona deportiva."),
            ("p", "Para descansar hay quioscos y terrazas repartidos por el parque. Para ir con niños hay "
                  "muchas áreas de juego infantil."),
            ("p", "Información en los accesos: 22 paneles informativos muestran de forma permanente la "
                  "información que afecta al funcionamiento del parque; cuando no hay alerta, enseñan un "
                  "plano del Retiro con la ubicación del usuario y la hora."),
            ("p", "Fuentes de beber: la fuente de la plaza de Honduras tiene el acceso adaptado."),
            ("h3", "Aseos públicos del Retiro"),
            ("src", f"Fuente: {FUENTES['aseos']}"),
            ("p", "No se ha localizado un listado oficial de aseos. Según un informe de la Asociación de "
                  "Amigos del Buen Retiro publicado en septiembre de 2025, el parque tenía 6 aseos "
                  "públicos: 3 subterráneos, sin acceso accesible, y 3 en superficie. Entre los "
                  "subterráneos cita los del Ángel Caído, la plaza de la Fuente de la Alcachofa y el "
                  "Templete de la Música. El mismo informe describía instalaciones con desperfectos."),

            ("h2", "Actividades que se pueden hacer en el Retiro"),
            ("src", f"Fuente: {FUENTES['esmadrid_retiro']}"),
            ("p", "Pasear y hacer deporte: el Retiro es uno de los lugares favoritos de Madrid para correr "
                  "y patinar. Los circuitos de running se describen en el documento de circuitos para "
                  "correr, y la normativa de bicicletas en el documento de bicicleta."),
            ("p", "En el Estanque Grande se pueden alquilar barcas de remo y funciona la Escuela Municipal "
                  "de Piragüismo."),
            ("p", "Cultura: exposiciones en el Palacio de Velázquez, el Palacio de Cristal y el Centro "
                  "Cultural Casa de Vacas; funciones en el Teatro de Títeres; visitas guiadas gratuitas y "
                  "audioguía oficial."),
            ("p", "Eventos anuales que se celebran en el parque: la Feria del Libro de Madrid (edición de "
                  "2027 prevista entre mayo y junio, fechas por confirmar) y los fuegos artificiales de "
                  "San Isidro."),
            ("p", "Con alerta meteorológica naranja se suspenden los eventos al aire libre y con alerta "
                  "roja el parque se cierra (ver el documento de seguridad del Retiro)."),

            ("h2", "Lugares destacados para visitar y fotografiar en el Retiro"),
            ("src", f"Fuente: {FUENTES['esmadrid_retiro']} esMadrid no los clasifica como «puntos "
                    "fotográficos»: se recogen los elementos que destaca como imprescindibles."),
            ("p", "Monumento a Alfonso XII, junto al Estanque Grande: obra del arquitecto José Grases "
                  "Riera, con un mirador con vistas sobre la ciudad."),
            ("p", "Palacio de Cristal: pabellón creado para la Exposición de Filipinas de 1887 y uno de los "
                  "principales ejemplos de la arquitectura del hierro en España. En 2026 su interior está "
                  "cerrado por obras y se puede ver la instalación artística exterior."),
            ("p", "El Ángel Caído: según esMadrid, la única escultura del mundo que representa al diablo."),
            ("p", "Fuente de los Galápagos, que conmemora el nacimiento de Isabel II; noria de agua de la "
                  "Huerta del Francés; Ermita de San Pelayo y San Isidoro; y Montaña de los Gatos."),
            ("p", "Árboles singulares: el ahuehuete del Parterre Francés, del que se dice que podría tener "
                  "unos 400 años, y el olivo de 627 años (hacia 1396) plantado en una pradera próxima a la "
                  "Puerta del Ángel Caído, que es hoy el árbol más antiguo del Retiro."),
            ("p", "Otros lugares: la Rosaleda, el foso de los monos de la antigua Casa de Fieras y el Bosque "
                  "del Recuerdo, en homenaje a las víctimas de los atentados del 11 de marzo de 2004."),
        ],

        "seguridad__protocolo_alertas__retiro__v01.pdf": [
            ("h1", "Seguridad en el Parque del Retiro (Madrid): protocolo de alertas meteorológicas"),
            ("p", "Qué es el protocolo de alertas del Retiro, qué pasa en cada nivel, cómo saber si hay una "
                  "alerta activa y por qué existe."),

            ("h2", "Qué es el protocolo de alertas meteorológicas del Retiro"),
            ("src", f"Fuentes: {FUENTES['protocolo_nota']} {FUENTES['estado_cierre']}"),
            ("ficha", "Protocolo de alertas del Retiro. Sirve para prevenir accidentes por caída de ramas o "
                      "árboles y otros riesgos por rachas fuertes de viento, lluvia o nieve. Tiene cuatro "
                      "niveles, según las previsiones de la Agencia Estatal de Meteorología (AEMET): "
                      "verde, amarillo, naranja y rojo."),
            ("p", "La versión vigente es el «protocolo del Retiro 2026». La Junta de Gobierno del "
                  "Ayuntamiento de Madrid aprobó su modificación el 18 de junio de 2026; el Ayuntamiento "
                  "publica el texto del protocolo con fecha 20 de junio de 2026."),

            ("h2", "Umbrales de viento del protocolo del Retiro 2026"),
            ("src", f"Fuente: {FUENTES['protocolo_nota']}"),
            ("ficha", "Umbrales de viento 2026. Alerta naranja: rachas máximas de entre 45 y 60 km/h "
                      "(antes, entre 40 y 55 km/h). Alerta roja: rachas a partir de 60 km/h (antes, más "
                      "de 55 km/h); con alerta roja se cierra el parque."),
            ("p", "El Ayuntamiento amplió estos umbrales para que el parque pueda permanecer abierto más "
                  "días en verano sin reducir la seguridad. La nota oficial no detalla en esta "
                  "modificación el umbral de la alerta amarilla."),

            ("h2", "Qué ocurre en el Retiro con cada nivel de alerta"),
            ("src", f"Fuentes: {FUENTES['estado_cierre']} {FUENTES['lista_restricciones']}"),
            ("p", "Alerta verde: situación de normalidad."),
            ("p", "Alerta amarilla (riesgo bajo): se restringe el acceso a las zonas infantiles, "
                  "deportivas y de mayores, que se balizan. Según la página municipal de estado de los "
                  "parques, también se restringe el acceso a los Jardines de Cecilio Rodríguez: solo se "
                  "puede entrar al Pabellón, por la puerta del Paseo de Uruguay. Se recomienda no "
                  "quedarse parado bajo los árboles."),
            ("p", "Alerta naranja (riesgo moderado): se restringe el acceso a las áreas infantiles, "
                  "deportivas y de mayores, al área canina, al Pinar de San Blas, al Cementerio, a los "
                  "Planteles y a los Jardines de Cecilio Rodríguez y de Herrero Palacios. Se suspenden "
                  "los eventos al aire libre."),
            ("p", "Alerta roja (riesgo alto): se cierra el parque."),

            ("h2", "Cómo saber si hay una alerta activa en el Retiro"),
            ("src", f"Fuente: {FUENTES['esmadrid_retiro']}"),
            ("p", "Los 22 paneles informativos de los accesos del parque anuncian las alertas en español y "
                  "en inglés dos horas antes de que se activen."),
            ("p", "El Ayuntamiento comunica las alertas en su cuenta oficial de X, @MADRID, y publica un "
                  "mapa del estado de cierre y apertura de los parques en el geoportal municipal."),

            ("h2", "Otros parques de Madrid afectados por el protocolo"),
            ("src", f"Fuentes: {FUENTES['protocolo_nota']} {FUENTES['esmadrid_retiro']}"),
            ("p", "El Capricho, la Fuente del Berro, la Quinta de Torre Arias, la Quinta de los Molinos y la "
                  "Rosaleda del Parque del Oeste aplican los mismos umbrales que el Retiro, porque su "
                  "arbolado es parecido."),
            ("p", "El parque Juan Carlos I, el Juan Pablo II y el Lineal del Manzanares tienen otro "
                  "protocolo: la alerta roja se activa con rachas por encima de 75 km/h y no se cierran, "
                  "sino que se balizan las zonas sensibles."),
            ("p", "La Dehesa de la Villa y el Parque del Oeste no están incluidos porque no se pueden "
                  "cerrar; con alerta se aconseja extremar las precauciones y, con alerta roja, no "
                  "visitarlos."),

            ("h2", "Por qué existe el protocolo del Retiro"),
            ("src", f"Fuente: {FUENTES['protocolo_nota']}"),
            ("p", "El primer protocolo empezó a aplicarse en mayo de 2016, después de que un hombre de 38 "
                  "años muriera por la caída de un árbol en el parque; un mes después una niña resultó "
                  "herida en un episodio similar. En 2018 murió un niño por la caída de otro árbol, lo "
                  "que llevó a actualizar la normativa."),
            ("p", "Entre 2020 y 2025, el parque estuvo cerrado por alerta roja solo el 1 % del tiempo, "
                  "pero en ese periodo se produjo el 38 % de todas las caídas: 60 árboles y 439 ramas."),
        ],
    }


def estilos() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=10.5, leading=15,
                          alignment=TA_LEFT, spaceAfter=6)
    return {
        "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=17,
                             leading=22, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=13,
                             leading=17, spaceBefore=14, spaceAfter=4),
        "h3": ParagraphStyle("h3", parent=base, fontName="Helvetica-Bold", fontSize=11,
                             leading=15, spaceBefore=8, spaceAfter=3),
        "src": ParagraphStyle("src", parent=base, fontName="Helvetica-Oblique", fontSize=9,
                              leading=12),
        "ficha": ParagraphStyle("ficha", parent=base, fontName="Helvetica-Bold", fontSize=10,
                                leading=14),
        "p": base,
    }


def construir(nombre: str, bloques: list[tuple[str, str]], salida: Path) -> Path:
    est = estilos()
    ruta = salida / nombre
    doc = SimpleDocTemplate(str(ruta), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title=bloques[0][1],
                            author="Equipo Retiro RAG")
    story, grupo = [], []
    for tipo, texto in bloques:
        parrafo = Paragraph(escape(texto), est[tipo])
        if tipo in ("h2", "h3"):
            if grupo:
                story.append(KeepTogether(grupo))
            grupo = [parrafo]
        elif grupo and len(grupo) < 3:
            grupo.append(parrafo)
        else:
            if grupo:
                story.append(KeepTogether(grupo))
                grupo = []
            story.append(parrafo)
    if grupo:
        story.append(KeepTogether(grupo))
    story.append(Spacer(1, 1))
    doc.build(story)
    return ruta


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera los PDF de itinerarios del corpus.")
    parser.add_argument("--salida", default="data/processed/itinerarios_informacion_practica_seguridad")
    args = parser.parse_args()
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    for nombre, bloques in documentos().items():
        print(f"[OK] {construir(nombre, bloques, salida)}")


if __name__ == "__main__":
    main()
