from src.generate import responder
from langchain_core.tools import tool

@tool
def rag_ask(args:dict):
    pregunta=args.get('pregunta')
    try:
        return{'data':responder(pregunta),'error':None}
    except Exception as e:
        return {'data':None,'error':str(e)}