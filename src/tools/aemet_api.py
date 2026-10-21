import json 
from config import URL_AEMET,TIEMPO_MAXIMO,EP_AVISOS,EP_OBSERVACIONES,EP_PREVISIONES
from dotenv import load_dotenv
from getpass import getpass
import os,requests

def _configure_api()->str:
    load_dotenv()
    if not os.getenv('AEMET_API_KEY'):
        os.environ['AEMET_API_KEY']=getpass('AEMET_API_KEY: ')
    api_key=os.getenv('AEMET_API_KEY')
    return api_key

def _error_response(error:str,*,response=None)->dict:
    return {'response':response,'error':error}

def _search_endpoint(endpoint:str)->list|dict:
    """Obtener datos según el endpoint (observaciones, previsiones y avisos)"""
    api_key=_configure_api()
    try:
        resp=requests.get(
            f"{URL_AEMET}{endpoint.lstrip('/')}",
            params={"api_key":api_key},
            timeout=TIEMPO_MAXIMO,
        )
    except Exception as e:
        return _error_response(e)
    try:
        meta=resp.json()
    except Exception as e:
        return _error_response(e,response=resp)
    #en meta['datos'] tenemos la url temporal para buscar los datos
    if isinstance(meta,dict) and meta.get('datos'):
        try:
            resp=requests.get(
                meta['datos'],
                timeout=TIEMPO_MAXIMO
            )
            return resp.json
        except Exception as e:
            return _error_response(e)
    if isinstance(meta,(dict|list)):
        return meta
    else:
        return {'response':resp,'error':'Invalid metadata type'}

def _get_observaciones()->list|dict:
    """Obtener observaciones"""
    endpoint=EP_OBSERVACIONES
    return _search_endpoint(endpoint=endpoint)

def _get_previsiones()->list|dict:
    """Obtener previsiones"""
    endpoint=EP_PREVISIONES
    return _search_endpoint(endpoint=endpoint)

def _get_avisos()->list|dict:
    """Obtener avisos"""
    endpoint=EP_AVISOS
    return _search_endpoint(endpoint=endpoint)
    