from src.generate import responder
from langchain_core.tools import tool

@tool
def rag_ask(args:dict):
    """Devuelve la información recogida en el corpus a traves de chunks relevantes embeddeados y almacenados en chroma db"""
    pregunta=args.get('pregunta')
    try:
        return{'data':responder(pregunta),'error':None}
    except Exception as e:
        return {'data':None,'error':str(e)}