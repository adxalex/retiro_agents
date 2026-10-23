from src.tools.aemet_api import api_dominio
from src.tools.image_decrip import describir_imagen
from src.tools.rag_tool import rag_ask
from src.tools.hora_actual import hora_actual
from datetime import datetime
import copy
from config import IMAGE_DEFAULT_PATH

TOOL_REGISTRY={
    'api_dominio':api_dominio,
    'describir_imagen':describir_imagen,
    'rag_ask':rag_ask,
    'hora_actual':hora_actual
}

def args_validation(nombre,args=None):
    if args is None: 
        args = {} 
    elif not isinstance(args, dict): 
        raise TypeError("args debe ser un diccionario")
    if nombre == 'api_dominio':
        return {}
    if nombre =='describir_imagen':
        ruta=IMAGE_DEFAULT_PATH
        imagen=args.get('imagen')
        if not isinstance(imagen, dict):
            ruta = IMAGE_DEFAULT_PATH
            mime = "image/png" if ruta.suffix.lower() == ".png" else "image/jpeg"
            imagen_bytes = ruta.read_bytes()

            return {
                'imagen': {
                    'bytes': imagen_bytes,
                    'mime': mime
                }
            }
        mime = imagen.get('mime')
        imagen_bytes = imagen.get('bytes')
        if (
            not isinstance(imagen_bytes, bytes)
            or not imagen_bytes
            or mime not in ('image/png', 'image/jpeg')
        ):
            mime = "image/png" if ruta.suffix.lower() == ".png" else "image/jpeg"
            imagen_bytes = ruta.read_bytes()
        return{
            'imagen':{
                'bytes':imagen_bytes,
                'mime':mime
                }
            }
    if nombre =='rag_ask':
        return {"pregunta": str(args.get("pregunta") or "").strip()}
    if nombre =='hora_actual':
        return {}
    raise ValueError(f"No hay validación definida para la herramienta: {nombre}")

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
    if nombre not in TOOL_REGISTRY:
        resultado['status']='blocked'
        traza['status']='blocked'
        resultado['traza']=traza
        return resultado
    new_result=copy.deepcopy(resultado)
    new_traza=copy.deepcopy(traza)
    try:
        clean = args_validation(nombre, args)
        new_traza['args']=clean
        resp = TOOL_REGISTRY[nombre](clean)

        if not isinstance(resp, dict):
            raise TypeError(
                "La herramienta debe devolver un diccionario"
            )

        if 'error' not in resp or 'data' not in resp:
            raise ValueError(
                "La respuesta debe contener 'error' y 'data'"
            )

        new_result['data'] = resp['data']
        new_result['error'] = resp['error']

        if resp['error'] is None:
            new_result['status'] = 'ok'
            new_traza['status'] = 'ok'
            new_traza['preview'] = str(resp['data'])[:200]
        else:
            new_result['status'] = 'error'
            new_traza['status'] = 'error'
            new_traza['preview'] = str(resp['error'])[:200]

        new_result['traza'] = new_traza
        return new_result

    except Exception as e:
        resultado['status'] = 'error'
        resultado['error'] = f"Error al ejecutar la tool: {str(e)}"

        traza['status'] = 'error'
        traza['preview'] = resultado['error'][:200]

        resultado['traza'] = traza
        return resultado