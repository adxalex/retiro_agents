import json 
from config import BASE_URL_AEMET,TIEMPO_MAXIMO,EP_AVISOS,EP_OBSERVACIONES,EP_PREVISIONES,FALLBACK_JSON
from dotenv import load_dotenv
import os,requests

def _configure_api()->str:
    load_dotenv()
    api_key=os.getenv('AEMET_API_KEY')
    if not api_key:
        raise ValueError(
            "No se ha configurado la variable de entorno AEMET_API_KEY."
        )
    return api_key

def _search_endpoint(endpoint:str)->list:
    """Obtener datos según el endpoint (observaciones, previsiones y avisos)"""
    api_key=_configure_api()
    resp=requests.get(
        f"{BASE_URL_AEMET}{endpoint.lstrip('/')}",
        params={"api_key":api_key},
        timeout=TIEMPO_MAXIMO,
    )
    resp.raise_for_status()
    try:
        meta=resp.json()
    except Exception as e:
        raise ValueError(
                f"Respuesta JSON invalida adquisicion URL temporal en el endoint {endpoint}"
            ) from e
    #en meta['datos'] tenemos la url temporal para buscar los datos
    if isinstance(meta,dict) and meta.get('datos'):
        resp=requests.get(
            meta['datos'],
            timeout=TIEMPO_MAXIMO
        )
        resp.raise_for_status()
        try:
            resp_json= resp.json()
        except Exception as e:
            raise ValueError(
                f"Rspuesta JSON invalida consulta datos en el endpoint {endpoint}"
            ) from e
        if isinstance(resp_json,list):
            return resp_json
        raise ValueError (
            f"Formato de datos inesperado en el endpoint {endpoint}"
        )
    raise ValueError ("Respuesta inseperada AEMET")

def _get_observaciones()->dict:
    """Obtener observaciones"""
    data=_search_endpoint(endpoint=EP_OBSERVACIONES)
    if not data:
        raise ValueError("No se han devuelto observaciones.")
    if not isinstance(data[0], dict):
        raise ValueError("El formato de las observaciones no es válido.")
    return data[0]

def _get_observaciones_fallback() -> dict:
    """Obtiene las observaciones del archivo JSON de fallback."""
    with open(FALLBACK_JSON, "r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("El JSON de fallback debe contener un diccionario.")
    return data

def _get_previsiones()->dict:
    """Obtener previsiones"""
    data=_search_endpoint(endpoint=EP_PREVISIONES)
    if not data:
        raise ValueError("No se han devuelto previsiones.")
    if not isinstance(data[0], dict):
        raise ValueError("El formato de las previsiones no es válido.")
    return data[0]

def _get_avisos()->dict:
    """Obtener avisos"""
    data=_search_endpoint(endpoint=EP_AVISOS)
    if not data:
        raise ValueError("No se han devuelto avisos.")
    if not isinstance(data[0], dict):
        raise ValueError("El formato de los avisos no es válido.")
    return data[0]

def  api_dominio(args=None)->dict:
    """Consulta la meteorología de El Retiro, Madrid.

Obtiene las observaciones mediante AEMET. Si falla la consulta,
intenta recuperarlas del archivo JSON de respaldo configurado
en config.py.

Si las observaciones se obtienen correctamente de AEMET, intenta
consultar también las previsiones y los avisos meteorológicos.

Los errores de previsiones y avisos se gestionan por separado,
sin perder los datos obtenidos correctamente.

Returns:
    Diccionario con los datos meteorológicos, el origen de las
    observaciones y los posibles errores.
"""
    data={
        'observaciones':None,
        'previsiones': None,
        'avisos': None,
        'origen':None
    }
    error=[]
    try:
        data['observaciones']=_get_observaciones()
        data['origen']='aemet'
    except Exception:
        try:
            data['observaciones'] = _get_observaciones_fallback()
            data['origen'] = 'respaldo'
        except Exception as fallback_error:
            error.append(f"Error en el fallback: {fallback_error}.")
        return {
            'data': data,
            'error': "\n".join(error) or None
        }               
    try:
        data['previsiones']=_get_previsiones()
    except Exception:
        data['previsiones']=None

    try:
        data['avisos']=_get_avisos()
    except Exception:
        data['avisos']=None
    
    return {
        'data':data,
        'error':"\n".join(error) or None
    }
    