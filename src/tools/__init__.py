from src.tools.aemet_api import api_dominio
from src.tools.image_decrip import describir_imagen
from src.tools.rag_tool import rag_ask
from datetime import datetime
import copy
from config import IMAGEN_DEFAULT_PATH

TOOL_REGISTRY={
    'api_dominio':api_dominio,
    'describir_imagen':describir_imagen,
    'rag_ask':rag_ask
}

def args_validation(nombre,args=None):
    args=args or {}
    if nombre == 'api_dominio':
        return {}
    if nombre =='describir_imagen':
        try:
            imagen=args.get('imagen')
        except Exception:
            ruta=IMAGEN_DEFAULT_PATH
            mime = "image/png" if ruta.suffix.lower() == ".png" else "image/jpeg"
            bytes= ruta.read_bytes()
            return{'imagen':[bytes,mime]}
        try:
            mime=imagen.get('mime')
        except Exception:
             ruta=IMAGEN_DEFAULT_PATH
             mime = "image/png" if ruta.suffix.lower() == ".png" else "image/jpeg"
        try:
            bytes=imagen.get('bytes')
        except Exception:
            ruta=IMAGEN_DEFAULT_PATH
            bytes=ruta.read_bytes()
        return{'imagen':[bytes,mime]}
    if nombre =='rag_ask':
        return {"pregunta": str(args.get("pregunta") or "").strip()}

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
    new_result=copy.deepcopy(resultado)
    new_traza=copy.deepcopy(traza)
    if nombre not in TOOL_REGISTRY:
        new_result['status']='blocked'
        new_traza['status']='blocked'
        new_result['traza']=new_traza
        return new_result
    try:
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