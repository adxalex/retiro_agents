"""Autenticación compartida para la API de Gemini.

Carga GEMINI_API_KEY desde el entorno o desde un archivo .env. La selección
de modelos pertenece a config.py. Cambiar el modelo de embeddings puede
requerir regenerar la colección de ChromaDB.
"""

# Esta versión combina la carga de credenciales utilizada en el curso con un
# cliente compartido para todo el pipeline. La clave se obtiene de .env o del
# entorno y, únicamente cuando se solicita de forma explícita, puede pedirse
# mediante una entrada oculta en consola.
#
# El modo no interactivo es el predeterminado para evitar que pytest,
# Streamlit o una ejecución automatizada queden esperando una entrada. Este
# módulo no selecciona modelos ni modifica config.py: embed.py y generate.py
# reutilizan la autenticación, pero conservan responsabilidades separadas.
#
# Tampoco se cambia automáticamente a otro modelo cuando uno deja de estar
# disponible. Esa decisión debe validarse y aplicarse manualmente porque un
# cambio de modelo de embeddings puede requerir regenerar el índice ChromaDB.

from __future__ import annotations

import getpass
import os

from dotenv import load_dotenv
from google import genai


def configurar_gemini_api_key(
    *,
    permitir_entrada: bool = False,
) -> str:
    """Obtiene la clave de Gemini y opcionalmente la solicita por consola."""
    load_dotenv()

    api_key = (
    os.getenv("GEMINI_API_KEY", "").strip()
    or os.getenv("GOOGLE_API_KEY", "").strip()
)

    if not api_key and permitir_entrada:
        api_key = getpass.getpass(
            "Pega aquí tu GEMINI_API_KEY (entrada oculta): "
        ).strip()

        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key

    if not api_key:
        raise RuntimeError(
            "No se ha definido GEMINI_API_KEY ni GOOGLE_API_KEY."
            "Añádela al archivo .env o al entorno."
        )

    return api_key


def get_gemini_client(
    *,
    permitir_entrada: bool = False,
) -> genai.Client:
    """Crea el cliente compartido utilizado por embeddings y generación."""
    api_key = configurar_gemini_api_key(
        permitir_entrada=permitir_entrada,
    )
    return genai.Client(api_key=api_key)
