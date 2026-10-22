"""Tests de la lógica de la interfaz Streamlit del agente (sin API)."""
import config


def test_config_limites_imagen():
    assert config.IMAGEN_MAX_BYTES == 5 * 1024 * 1024
    assert config.IMAGEN_MIME_PERMITIDOS == ("image/png", "image/jpeg")
