from datetime import datetime
from zoneinfo import ZoneInfo

from config import (
    HORA_APERTURA,
    HORA_CIERRE_INVIERNO,
    HORA_CIERRE_VERANO,
    MESES_VERANO,
    ZONA_HORARIA
)


def estado_parque(hora) -> str:
    """
    Devuelve el estado del parque según la hora y el mes actuales.
    """

    mes = hora.month
    hora_dia = hora.hour

    if mes in MESES_VERANO:
        hora_cierre = HORA_CIERRE_VERANO
    else:
        hora_cierre = HORA_CIERRE_INVIERNO

    if HORA_APERTURA <= hora_dia < hora_cierre:
        return "Abierto"

    return "Cerrado"


def hora_actual(args=None) -> dict:
    """Devuelve la fecha y hora local y el estado del parque."""

    try:
        ahora = datetime.now(ZoneInfo(ZONA_HORARIA))

        hora = ahora.strftime("%H:%M")
        estado = estado_parque(ahora)

        return {
            "data": {
                "hora_madrid": hora,
                "estado_parque": estado
            },
            "error": None
        }

    except Exception as e:
        return {
            "data": None,
            "error": str(e)
        }