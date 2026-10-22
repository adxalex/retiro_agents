from src.tools.aemet_api import api_dominio
from datetime import datetime
import copy

TOOL_REGISTRY={
    'api_dominio':api_dominio
}

def args_validation(nombre,args=None):
    args=args or {}
    if nombre == 'api_dominio':
        return {}

def ejecutar_tool(nombre,args=None):
    resultado={
        'tool':nombre,
        'status':None,
        'data':None,
        'error':None,
        'traza':None
    }
    traza={
        'ts':datetime.now().astimezone().isoformat(),
        'origen':'tool',
        'nombre':nombre,
        'args':args or {},
        'status':None,
        'preview':None
    }
    clean=args_validation(nombre,args)
    try:
        new_result=copy.deepcopy(resultado)
        new_traza=copy.deepcopy(traza)
        resp= TOOL_REGISTRY[nombre](**clean)
        if resp['error'] is None:
            new_result['status']='ok'
            new_traza['status']='ok'
        else:
            new_result['status']='error'
            new_traza['status']='error'
        new_result['data']=resp['data']
        new_result['error']=resp['error']
        new_result['traza']=traza
        return new_result
    except Exception as e:
        resultado['error']="Error al ejecutar la tool"
        traza['status']="error"
        resultado['status']="error"
        resultado['traza']=traza
        return resultado