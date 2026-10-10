"""Saludo contextual del asistente: hora, tiempo en el Retiro y avisos.

Este modulo NO forma parte del flujo RAG. Sus datos vienen de una API externa
en tiempo real, no del corpus, asi que:

- Nunca se mezclan con el contexto que recibe el LLM.
- Nunca aparecen entre las fuentes citadas de una respuesta.
- Se muestran como un aviso aparte, siempre con su origen y su hora.

Fuente de datos: AEMET OpenData, estacion 3195 (Madrid-Retiro), que esta
dentro del propio parque. Requiere una API key gratuita (AEMET_API_KEY en
.env), que se solicita en https://opendata.aemet.es/centrodedescargas/altaUsuario

Los umbrales de viento y el horario replican el documento
seguridad_protocolo_alertas_retiro.pdf e informacion_practica_guia_visitante_retiro.pdf
del corpus. Si esos documentos cambian, hay que actualizar estas constantes.

La comparacion del viento con los umbrales es ORIENTATIVA: el estado oficial
del parque lo publica el Ayuntamiento en sus paneles y en @MADRID.
"""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

import requests

ESTACION_RETIRO = "3195"
URL_AEMET = (
    "https://opendata.aemet.es/opendata/api/observacion/convencional/datos/estacion/"
)
TIEMPO_MAXIMO = 8  # segundos

# Umbrales del protocolo del Retiro 2026 (ver corpus: seguridad_protocolo_alertas).
VIENTO_NARANJA_KMH = 45.0
VIENTO_ROJA_KMH = 60.0

# Horario del parque (ver corpus: informacion_practica_guia_visitante).
HORA_APERTURA = 6
HORA_CIERRE_INVIERNO = 22  # octubre a marzo
HORA_CIERRE_VERANO = 24  # abril a septiembre
MESES_VERANO = range(4, 10)

# El horario del parque es hora local de Madrid. Si el servidor corre en UTC,
# datetime.now() daria una hora equivocada y el aviso de apertura o cierre
# seria incorrecto, asi que la zona horaria se fija explicitamente.
ZONA_MADRID = ZoneInfo("Europe/Madrid")


def ahora_en_madrid() -> datetime:
    """Hora actual en el parque, independiente de la zona del servidor."""
    return datetime.now(ZONA_MADRID)

AVISO_NO_OFICIAL = (
    "Comparación orientativa con los umbrales del protocolo. El estado oficial "
    "del parque se publica en los paneles de los accesos y en @MADRID."
)


def _saludo_por_hora(hora: int) -> str:
    if 6 <= hora < 13:
        return "Buenos dias"
    if 13 <= hora < 21:
        return "Buenas tardes"
    return "Buenas noches"


def hora_de_cierre(momento: datetime) -> int:
    """Hora de cierre del parque segun la temporada."""
    return (
        HORA_CIERRE_VERANO
        if momento.month in MESES_VERANO
        else HORA_CIERRE_INVIERNO
    )


def estado_del_parque(momento: datetime | None = None) -> dict:
    """Dice si el parque esta abierto segun el horario del corpus."""
    momento = momento or ahora_en_madrid()
    cierre = hora_de_cierre(momento)
    abierto = HORA_APERTURA <= momento.hour < cierre
    temporada = "verano" if momento.month in MESES_VERANO else "invierno"
    return {
        "abierto": abierto,
        "hora_apertura": HORA_APERTURA,
        "hora_cierre": cierre,
        "temporada": temporada,
        "horario": f"{HORA_APERTURA}:00 a {cierre % 24:02d}:00",
    }


def _kmh(velocidad_ms: float | None) -> float | None:
    """AEMET da el viento en m/s; el protocolo usa km/h."""
    if velocidad_ms is None:
        return None
    return round(float(velocidad_ms) * 3.6, 1)


_SIN_INDICAR = object()


def obtener_observacion(
    api_key: str | None | object = _SIN_INDICAR,
    sesion: Any | None = None,
) -> dict | None:
    """Ultima observacion de la estacion del Retiro, o None si no se puede.

    AEMET responde en dos pasos: la primera llamada devuelve una URL en el
    campo 'datos', y esa URL contiene el JSON real.

    Nunca lanza excepcion: si algo falla, devuelve None y la aplicacion sigue
    funcionando sin el aviso. Un fallo de la API externa no puede tumbar el
    asistente.
    """
    # Solo se recurre a .env cuando no se indica nada. Pasar "" o None
    # significa "sin clave" y debe respetarse: de lo contrario los tests
    # acabarian llamando a la API real.
    if api_key is _SIN_INDICAR:
        api_key = os.getenv("AEMET_API_KEY", "")
    if not isinstance(api_key, str) or not api_key.strip():
        return None

    sesion = sesion or requests
    try:
        primera = sesion.get(
            f"{URL_AEMET}{ESTACION_RETIRO}",
            params={"api_key": api_key},
            timeout=TIEMPO_MAXIMO,
        )
        primera.raise_for_status()
        url_datos = primera.json().get("datos")
        if not url_datos:
            return None

        segunda = sesion.get(url_datos, timeout=TIEMPO_MAXIMO)
        segunda.raise_for_status()
        observaciones = segunda.json()

        # AEMET devuelve una lista de observaciones, pero ante un error de
        # cuota o de servicio responde con un objeto de descripcion. Sin esta
        # comprobacion, observaciones[-1] lanzaba KeyError y tumbaba la app.
        if not isinstance(observaciones, list) or not observaciones:
            return None

        ultima = observaciones[-1]
        if not isinstance(ultima, dict):
            return None

        return {
            "estacion": ultima.get("ubi", "Madrid-Retiro"),
            "hora_utc": ultima.get("fint"),
            "temperatura_c": ultima.get("ta"),
            "humedad_pct": ultima.get("hr"),
            "precipitacion_mm": ultima.get("prec"),
            "viento_kmh": _kmh(ultima.get("vv")),
            "racha_kmh": _kmh(ultima.get("vmax")),
            "fuente": "AEMET, estación meteorológica del Retiro",
        }
    except Exception:  # noqa: BLE001 - la API externa nunca rompe la app
        return None


def nivel_de_viento(racha_kmh: float | None) -> dict:
    """Compara la racha con los umbrales del protocolo del Retiro 2026."""
    if racha_kmh is None:
        return {"nivel": "desconocido", "mensaje": None}

    if racha_kmh >= VIENTO_ROJA_KMH:
        return {
            "nivel": "rojo",
            "mensaje": (
                f"Rachas de {racha_kmh:.0f} km/h: por encima de este viento "
                "el parque puede cerrarse."
            ),
        }
    if racha_kmh >= VIENTO_NARANJA_KMH:
        return {
            "nivel": "naranja",
            "mensaje": (
                f"Rachas de {racha_kmh:.0f} km/h: con este viento suelen "
                "cerrarse las zonas infantiles, deportivas y algunos jardines."
            ),
        }
    return {"nivel": "verde", "mensaje": None}


def saludo_contextual(
    api_key: str | None | object = _SIN_INDICAR,
    sesion: Any | None = None,
    momento: datetime | None = None,
) -> dict:
    """Construye el saludo de bienvenida del asistente.

    Devuelve siempre las mismas claves, haya datos meteorologicos o no:
    saludo, estado (del parque), observacion, viento, peculiaridades y fuente.
    """
    momento = momento or ahora_en_madrid()
    estado = estado_del_parque(momento)
    observacion = obtener_observacion(api_key=api_key, sesion=sesion)
    viento = nivel_de_viento(observacion.get("racha_kmh") if observacion else None)

    saludo = f"{_saludo_por_hora(momento.hour)}. Soy el asistente del Parque de El Retiro."

    peculiaridades: list[str] = []
    if not estado["abierto"]:
        peculiaridades.append(
            f"El parque está cerrado ahora mismo. Abre a las "
            f"{HORA_APERTURA:02d}:00."
        )
    else:
        faltan = estado["hora_cierre"] - momento.hour
        cierre = f"{estado['hora_cierre'] % 24:02d}:00"
        if faltan <= 1:
            peculiaridades.append(f"El parque cierra dentro de poco, a las {cierre}.")
        else:
            peculiaridades.append(f"El parque cierra hoy a las {cierre}.")

    if viento["mensaje"]:
        peculiaridades.append(viento["mensaje"])
        peculiaridades.append(AVISO_NO_OFICIAL)

    if observacion and observacion.get("precipitacion_mm"):
        try:
            if float(observacion["precipitacion_mm"]) > 0:
                peculiaridades.append("Está lloviendo en el parque.")
        except (TypeError, ValueError):
            pass

    return {
        "saludo": saludo,
        "estado": estado,
        "observacion": observacion,
        "viento": viento,
        "peculiaridades": peculiaridades,
        "fuente": observacion["fuente"] if observacion else None,
    }


def texto_de_bienvenida(contexto: dict) -> str:
    """Version en texto plano del saludo, para la CLI."""
    lineas = [contexto["saludo"]]

    observacion = contexto["observacion"]
    if observacion and observacion.get("temperatura_c") is not None:
        tiempo = f"Ahora en el Retiro: {observacion['temperatura_c']} grados"
        if observacion.get("viento_kmh") is not None:
            tiempo += f", viento {observacion['viento_kmh']:.0f} km/h"
        lineas.append(tiempo + ".")
    else:
        lineas.append("(Sin datos meteorológicos ahora mismo.)")

    lineas.extend(contexto["peculiaridades"])

    if contexto["fuente"]:
        hora = observacion.get("hora_utc") or "sin hora"
        lineas.append(f"Datos de {contexto['fuente']}, medidos a las {hora}.")

    return "\n".join(lineas)
