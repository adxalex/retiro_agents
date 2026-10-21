import json 
from config import URL_AEMET,TIEMPO_MAXIMO,EP_AVISOS,EP_OBSERVACIONES,EP_PREVISIONES
from dotenv import load_dotenv
from getpass import getpass
import os,requests
from langchain_core.tools import tool

def _configure_api()->str:
    load_dotenv()
    if not os.getenv('AEMET_API_KEY'):
        os.environ['AEMET_API_KEY']=getpass('AEMET_API_KEY: ')
    api_key=os.getenv('AEMET_API_KEY')
    return api_key

def _error_response(error:str,*,response=None)->dict:
    return {'response':response,'error':error}

def _search_endpoint(endpoint:str)->list:
    """Obtener datos según el endpoint (observaciones, previsiones y avisos)"""
    api_key=_configure_api()
    resp=requests.get(
        f"{URL_AEMET}{endpoint.lstrip('/')}",
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
        if isinstance(resp_json,(list)):
            return resp_json
        raise ValueError (
            f"Formato de datos inesperado en el endpoint {endpoint}"
        )
    raise ValueError ("Respuesta inseperada AEMET")

def _get_observaciones()->list:
    """Obtener observaciones"""
    endpoint=EP_OBSERVACIONES
    return _search_endpoint(endpoint=endpoint)

def _get_previsiones()->list:
    """Obtener previsiones"""
    endpoint=EP_PREVISIONES
    return _search_endpoint(endpoint=endpoint)

def _get_avisos()->list:
    """Obtener avisos"""
    endpoint=EP_AVISOS
    return _search_endpoint(endpoint=endpoint)

@tool
def  api_dominio()->tuple[dict,str|None]:
    """ Consulta la meteorología de El Retiro, Madrid. 
    
    Siempre obtiene las observaciones meteorológicas. 
    
    Si falla la api, recupera las observaciones desde el JSON de fallback configurado en config.py. 
        
    Si no falla la api, también obtiene las previsiones y los avisos meteorológicos.
    
    En ese caso, las previsiones y los avisos quedan como no disponibles. 
    
    Returns: 
        Diccionario con observaciones, previsiones, avisos y metadatos sobre el origen de los datos. 
    """
    data={
        'observaciones':None,
        'previsiones': None,
        'avisos': None,
        'origen':None
    }
    try:
        data['observaciones']=_get_observaciones()[0]
        data['previsiones']=_get_previsiones()[0]
        data['avisos']=_get_avisos()[0]
        data['origen']='aemet'
        return data,None
    except Exception as e:
        data['observaciones']=None
        data['previsiones']=None
        data['avisos']=None
        data['origen']='respaldo'
        return data,str(e)
    