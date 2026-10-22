"""Tool multimodal: describe la imagen de demo (imagen → texto)."""

from pathlib import Path
from langchain_core.tools import tool
import config
import os
from google import genai
from google.genai import types

def configure_api()->str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError ("Error: falta GEMINI_API_KEY")

@tool
def describir_imagen(bytes,mime) -> str:
    """Describe la imagen de demo en español (texto visible, lugar, contexto).

    Sin ruta (o cadena vacía) usa assets/imagen_demo.jpg del proyecto.
    Llama a esta tool cuando el usuario mencione imagen, foto, cartel, poster o captura.
    """
    try:
        api_key=configure_api()
    except ValueError as e:
        return {'data':None,'error':str(e)}
    
    try:
        mime = mime
        client = genai.Client(api_key=api_key)
        out = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=bytes, mime_type=mime),
                        types.Part.from_text(
                            text=(
                                "Describe la imagen en 2-3 frases en español. "
                                "Si hay texto, fecha, hora o lugar visibles, menciónalos."
                            )
                        ),
                    ],
                )
            ],
        )
        if not (out.text or "").strip():
            return {'data':None,'error':"Error: respuesta vacía del modelo."}
        return {'data':out.text.strip(),'error':None}
    except Exception as e:  # noqa: BLE001
        return {'data':None,'error':f"Error al leer la imagen: {e}"}