"""Tests de la lógica de la interfaz Streamlit del agente (sin API)."""
import ast
import uuid
from pathlib import Path

import pytest

import config
from src import ui_agente

RUTA_UI_AGENTE = Path(__file__).resolve().parents[1] / "src" / "ui_agente.py"


def resultado(**campos) -> dict:
    """Resultado con las claves del contrato público del agente."""
    base = {
        "thread_id": "",
        "respuesta": "",
        "plan": [],
        "pendiente_aprobacion": False,
        "done": False,
        "traza": [],
        "error": None,
    }
    base.update(campos)
    return base


class AgenteFalso:
    """Doble de procesar_turno que registra llamadas y devuelve datos fijos."""

    def __init__(self):
        self.llamadas = []
        self.respuestas = []

    def __call__(self, texto, thread_id, imagen=None):
        self.llamadas.append(
            {"texto": texto, "thread_id": thread_id, "imagen": imagen})
        datos = self.respuestas.pop(0) if self.respuestas else {}
        return resultado(thread_id=thread_id, **datos)


class AprobadorFalso:
    """Doble de aprobar_plan que registra llamadas y devuelve datos fijos."""

    def __init__(self):
        self.llamadas = []
        self.respuesta = {}

    def __call__(self, thread_id, aprobado, comentario=""):
        self.llamadas.append(
            {"thread_id": thread_id, "aprobado": aprobado, "comentario": comentario})
        return resultado(thread_id=thread_id, **self.respuesta)


@pytest.fixture
def procesar_falso():
    return AgenteFalso()


@pytest.fixture
def aprobar_falso():
    return AprobadorFalso()


@pytest.fixture
def sesion_con_plan(sesion, procesar_falso):
    """Sesión cuyo último turno ha dejado un plan pendiente."""
    procesar_falso.respuestas = [
        {"respuesta": "Propuesta", "plan": ["Paso 1"], "pendiente_aprobacion": True}]
    ui_agente.enviar_turno(sesion, "Plan de visita", None, None, procesar_falso)
    return sesion


@pytest.fixture
def sesion():
    return ui_agente.nueva_sesion()


def test_config_limites_imagen():
    assert config.IMAGEN_MAX_BYTES == 5 * 1024 * 1024
    assert config.IMAGEN_MIME_PERMITIDOS == ("image/png", "image/jpeg")


def test_nueva_sesion_genera_thread_id_uuid4():
    sesion = ui_agente.nueva_sesion()

    assert uuid.UUID(sesion["thread_id"]).version == 4
    assert sesion["mensajes"] == []
    assert sesion["ultimo"] is None
    assert sesion["uploader_key"] == 0


def test_ui_agente_no_importa_streamlit_ni_nucleo():
    arbol = ast.parse(RUTA_UI_AGENTE.read_text(encoding="utf-8"))
    modulos = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            modulos.add(nodo.module or "")
            modulos.update(f"{nodo.module}.{alias.name}" for alias in nodo.names)

    prohibidos = ("streamlit", "src.agent", "src.graph", "langgraph")
    assert not any(m.startswith(prohibidos) for m in modulos)


def test_mensajes_en_orden_cronologico(sesion, procesar_falso):
    procesar_falso.respuestas = [{"respuesta": "R1"}, {"respuesta": "R2"}]

    ui_agente.enviar_turno(sesion, "P1", None, None, procesar_falso)
    ui_agente.enviar_turno(sesion, "P2", None, None, procesar_falso)

    assert [(m["rol"], m["texto"]) for m in sesion["mensajes"]] == [
        (ui_agente.ROL_USUARIO, "P1"),
        (ui_agente.ROL_AGENTE, "R1"),
        (ui_agente.ROL_USUARIO, "P2"),
        (ui_agente.ROL_AGENTE, "R2"),
    ]


def test_enviar_turno_llama_con_thread_id_activo(sesion, procesar_falso):
    ui_agente.enviar_turno(sesion, "Hola", None, None, procesar_falso)
    ui_agente.enviar_turno(sesion, "Otra", None, None, procesar_falso)

    assert [ll["thread_id"] for ll in procesar_falso.llamadas] == [
        sesion["thread_id"], sesion["thread_id"]]
    assert procesar_falso.llamadas[0]["texto"] == "Hola"
    assert procesar_falso.llamadas[0]["imagen"] is None


@pytest.mark.parametrize("texto", ["", "   ", "\n\t"])
def test_texto_vacio_no_llama_al_agente(sesion, procesar_falso, texto):
    ui_agente.enviar_turno(sesion, texto, None, None, procesar_falso)

    assert procesar_falso.llamadas == []
    assert sesion["mensajes"] == []


def test_respuesta_no_vacia_se_anade(sesion, procesar_falso):
    procesar_falso.respuestas = [{"respuesta": "El parque abre a las 6:00."}]

    ui_agente.enviar_turno(sesion, "¿Horario?", None, None, procesar_falso)

    ultimo = sesion["mensajes"][-1]
    assert ultimo["rol"] == ui_agente.ROL_AGENTE
    assert ultimo["texto"] == "El parque abre a las 6:00."


def test_respuesta_y_plan_vacios_no_anaden_mensaje(sesion, procesar_falso):
    ui_agente.enviar_turno(sesion, "Hola", None, None, procesar_falso)

    assert [m["rol"] for m in sesion["mensajes"]] == [ui_agente.ROL_USUARIO]


def test_plan_se_guarda_como_lista(sesion, procesar_falso):
    plan = ["Entrar por la Puerta de Alcalá", "Ver el Palacio de Cristal"]
    procesar_falso.respuestas = [{"respuesta": "Propuesta:", "plan": plan}]

    ui_agente.enviar_turno(sesion, "Plan de visita", None, None, procesar_falso)

    ultimo = sesion["mensajes"][-1]
    assert ultimo["rol"] == ui_agente.ROL_AGENTE
    assert ultimo["plan"] == plan


def test_error_se_muestra_como_aviso(sesion, procesar_falso):
    procesar_falso.respuestas = [{"error": "Fallo de la tool."}]

    ui_agente.enviar_turno(sesion, "Hola", None, None, procesar_falso)

    assert [(m["rol"], m["texto"]) for m in sesion["mensajes"]] == [
        (ui_agente.ROL_USUARIO, "Hola"),
        (ui_agente.ROL_AVISO, "Fallo de la tool."),
    ]
    assert sesion["ultimo"]["error"] == "Fallo de la tool."


def test_excepcion_del_agente_se_convierte_en_aviso(sesion):
    def procesar_que_falla(texto, thread_id, imagen=None):
        raise RuntimeError("caída inesperada")

    ui_agente.enviar_turno(sesion, "Hola", None, None, procesar_que_falla)

    assert [(m["rol"], m["texto"]) for m in sesion["mensajes"]] == [
        (ui_agente.ROL_USUARIO, "Hola"),
        (ui_agente.ROL_AVISO, ui_agente.AVISO_ERROR_AGENTE),
    ]
    assert sesion["ultimo"]["error"] == ui_agente.AVISO_ERROR_AGENTE
    assert sesion["ultimo"]["pendiente_aprobacion"] is False
    assert sesion["ultimo"]["done"] is False


def test_error_plan_pendiente_como_aviso(sesion, procesar_falso):
    error = "Hay un plan pendiente de aprobación."
    procesar_falso.respuestas = [
        {"respuesta": "Propuesta", "plan": ["Paso"], "pendiente_aprobacion": True,
         "error": error},
    ]

    ui_agente.enviar_turno(sesion, "Otra cosa", None, None, procesar_falso)

    assert sesion["mensajes"][-1] == {
        "rol": ui_agente.ROL_AVISO, "texto": error, "plan": []}
    assert ui_agente.pendiente(sesion) is True


def test_error_plan_pendiente_no_duplica_respuesta(sesion, procesar_falso):
    error = "Hay un plan pendiente de aprobación."
    procesar_falso.respuestas = [
        {"respuesta": "Propuesta", "plan": ["Paso"], "pendiente_aprobacion": True,
         "error": error},
    ]

    ui_agente.enviar_turno(sesion, "Otra cosa", None, None, procesar_falso)

    assert [(m["rol"], m["texto"]) for m in sesion["mensajes"]] == [
        (ui_agente.ROL_USUARIO, "Otra cosa"),
        (ui_agente.ROL_AVISO, error),
    ]


def test_traza_se_reemplaza(sesion, procesar_falso):
    evento_1 = {"origen": "supervisor", "nombre": "normas"}
    evento_2 = {"origen": "supervisor", "nombre": "entorno"}
    procesar_falso.respuestas = [{"traza": [evento_1]}, {"traza": [evento_2]}]

    ui_agente.enviar_turno(sesion, "P1", None, None, procesar_falso)
    ui_agente.enviar_turno(sesion, "P2", None, None, procesar_falso)

    assert sesion["ultimo"]["traza"] == [evento_2]


def test_chat_bloqueado_con_plan_pendiente(sesion, procesar_falso):
    assert ui_agente.pendiente(sesion) is False

    procesar_falso.respuestas = [
        {"respuesta": "Propuesta", "plan": ["Paso"], "pendiente_aprobacion": True}]
    ui_agente.enviar_turno(sesion, "Plan", None, None, procesar_falso)

    assert ui_agente.pendiente(sesion) is True


def test_estado_solo_desde_banderas(sesion, procesar_falso):
    procesar_falso.respuestas = [
        {"respuesta": "Plan pendiente de aprobación. Plan aprobado.",
         "pendiente_aprobacion": False},
        {"respuesta": "", "plan": ["Paso"], "pendiente_aprobacion": True},
    ]

    ui_agente.enviar_turno(sesion, "P1", None, None, procesar_falso)
    assert ui_agente.pendiente(sesion) is False

    ui_agente.enviar_turno(sesion, "P2", None, None, procesar_falso)
    assert ui_agente.pendiente(sesion) is True


def test_aprobar_llama_con_true_y_comentario(sesion_con_plan, aprobar_falso):
    ui_agente.decidir(sesion_con_plan, True, "  Empezar por el estanque ", aprobar_falso)

    assert aprobar_falso.llamadas == [{
        "thread_id": sesion_con_plan["thread_id"],
        "aprobado": True,
        "comentario": "Empezar por el estanque",
    }]


def test_rechazar_llama_con_false_y_comentario(sesion_con_plan, aprobar_falso):
    ui_agente.decidir(sesion_con_plan, False, "", aprobar_falso)

    assert aprobar_falso.llamadas == [{
        "thread_id": sesion_con_plan["thread_id"],
        "aprobado": False,
        "comentario": "",
    }]


def test_aprobacion_con_done_muestra_plan_aprobado(sesion_con_plan, aprobar_falso):
    aprobar_falso.respuesta = {"done": True}

    ui_agente.decidir(sesion_con_plan, True, "", aprobar_falso)

    assert sesion_con_plan["mensajes"][-1] == {
        "rol": ui_agente.ROL_SISTEMA,
        "texto": ui_agente.MENSAJE_PLAN_APROBADO,
        "plan": [],
    }


def test_rechazo_muestra_mensaje(sesion_con_plan, aprobar_falso):
    ui_agente.decidir(sesion_con_plan, False, "", aprobar_falso)

    assert sesion_con_plan["mensajes"][-1] == {
        "rol": ui_agente.ROL_SISTEMA,
        "texto": ui_agente.MENSAJE_PLAN_RECHAZADO,
        "plan": [],
    }


def test_decision_conserva_mensajes(sesion_con_plan, aprobar_falso):
    previos = [dict(m) for m in sesion_con_plan["mensajes"]]
    aprobar_falso.respuesta = {"done": True}

    ui_agente.decidir(sesion_con_plan, True, "", aprobar_falso)

    assert sesion_con_plan["mensajes"][:len(previos)] == previos
    assert len(sesion_con_plan["mensajes"]) == len(previos) + 1


@pytest.mark.parametrize("aprobado", [True, False])
def test_decision_desbloquea_chat(sesion_con_plan, aprobar_falso, aprobado):
    aprobar_falso.respuesta = {"done": aprobado, "pendiente_aprobacion": False}

    ui_agente.decidir(sesion_con_plan, aprobado, "", aprobar_falso)

    assert ui_agente.pendiente(sesion_con_plan) is False


def test_aprobacion_con_error_no_muestra_aprobado(sesion_con_plan, aprobar_falso):
    aprobar_falso.respuesta = {"done": True, "error": "Fallo al aplicar."}

    ui_agente.decidir(sesion_con_plan, True, "", aprobar_falso)

    textos = [m["texto"] for m in sesion_con_plan["mensajes"]]
    assert ui_agente.MENSAJE_PLAN_APROBADO not in textos
    assert sesion_con_plan["mensajes"][-1]["rol"] == ui_agente.ROL_AVISO
    assert sesion_con_plan["mensajes"][-1]["texto"] == "Fallo al aplicar."


def test_aprobacion_sin_done_no_muestra_aprobado(sesion_con_plan, aprobar_falso):
    aprobar_falso.respuesta = {"done": False}

    ui_agente.decidir(sesion_con_plan, True, "", aprobar_falso)

    textos = [m["texto"] for m in sesion_con_plan["mensajes"]]
    assert ui_agente.MENSAJE_PLAN_APROBADO not in textos
    assert sesion_con_plan["mensajes"][-1] == {
        "rol": ui_agente.ROL_AVISO,
        "texto": ui_agente.AVISO_PLAN_NO_COMPLETADO,
        "plan": [],
    }


def test_turno_pendiente_no_llama_a_aprobar(
        sesion, procesar_falso, aprobar_falso):
    # Un turno que deja el plan pendiente no decide por su cuenta.
    procesar_falso.respuestas = [
        {"respuesta": "Propuesta", "plan": ["Paso"], "pendiente_aprobacion": True}]
    ui_agente.enviar_turno(sesion, "Plan", None, None, procesar_falso)
    assert aprobar_falso.llamadas == []

    # Sin plan pendiente, decidir no llama al agente ni cambia el chat.
    otra = ui_agente.nueva_sesion()
    ui_agente.decidir(otra, True, "", aprobar_falso)
    assert aprobar_falso.llamadas == []
    assert otra["mensajes"] == []
    assert otra["ultimo"] is None


def test_mensajes_de_decision_textos_exactos():
    assert ui_agente.MENSAJE_PLAN_APROBADO == "Plan aprobado"
    assert ui_agente.MENSAJE_PLAN_RECHAZADO == (
        "Plan rechazado, puedes hacer otra petición")


def test_decision_con_excepcion_mantiene_plan_pendiente(sesion_con_plan):
    def aprobar_que_falla(thread_id, aprobado, comentario=""):
        raise RuntimeError("caída inesperada")

    ui_agente.decidir(sesion_con_plan, True, "", aprobar_que_falla)

    assert ui_agente.pendiente(sesion_con_plan) is True
    assert sesion_con_plan["mensajes"][-1] == {
        "rol": ui_agente.ROL_AVISO,
        "texto": ui_agente.AVISO_ERROR_AGENTE,
        "plan": [],
    }
    textos = [m["texto"] for m in sesion_con_plan["mensajes"]]
    assert ui_agente.MENSAJE_PLAN_APROBADO not in textos


def test_decision_con_error_del_nucleo_usa_su_bandera(sesion_con_plan, aprobar_falso):
    aprobar_falso.respuesta = {"error": "Fallo al aplicar.", "pendiente_aprobacion": False}

    ui_agente.decidir(sesion_con_plan, True, "", aprobar_falso)

    assert ui_agente.pendiente(sesion_con_plan) is False


def test_turno_con_excepcion_deja_chat_libre(sesion):
    def procesar_que_falla(texto, thread_id, imagen=None):
        raise RuntimeError("caída inesperada")

    ui_agente.enviar_turno(sesion, "Hola", None, None, procesar_que_falla)

    assert ui_agente.pendiente(sesion) is False


def evento(origen, nombre, args=None, status="ok", preview=""):
    """Evento de traza con la forma del contrato."""
    return {"ts": "2026-10-22T10:00:00+02:00", "origen": origen, "nombre": nombre,
            "args": args if args is not None else {}, "status": status,
            "preview": preview}


def test_filas_traza_campos_y_orden():
    traza = [
        evento("supervisor", "normas", {"pregunta": "x"}, "ok", "Ruta elegida"),
        evento("tool", "rag_ask", {"pregunta": "x"}, "ok", "Respuesta"),
        {"origen": "hitl", "nombre": "pausa"},
    ]

    filas = ui_agente.filas_traza(traza)

    assert [list(f) for f in filas] == [
        ["ts", "origen", "nombre", "status", "preview"]] * 3
    assert [f["nombre"] for f in filas] == ["normas", "rag_ask", "pausa"]
    assert filas[0]["preview"] == "Ruta elegida"
    assert filas[2] == {"ts": "", "origen": "hitl", "nombre": "pausa",
                        "status": "", "preview": ""}
    assert ui_agente.filas_traza([]) == []


def test_comentario_hitl_ultimo_evento():
    traza = [
        evento("hitl", "pausa", {"numero_pasos": 2}, "pending"),
        evento("supervisor", "entorno"),
        evento("hitl", "aprobar", {"comentario": "Prefiero el estanque"}),
    ]

    assert ui_agente.comentario_hitl(traza) == "Prefiero el estanque"


@pytest.mark.parametrize("traza", [
    [],
    [evento("supervisor", "normas", {"comentario": "no es hitl"})],
    [evento("hitl", "rechazar", {"comentario": ""})],
    [evento("hitl", "rechazar", {"comentario": "   "})],
    [evento("hitl", "rechazar", {})],
    [{"origen": "hitl", "nombre": "rechazar", "args": None}],
    # Solo cuenta el último evento hitl.
    [evento("hitl", "rechazar", {"comentario": "antiguo"}),
     evento("hitl", "pausa", {"numero_pasos": 1}, "pending")],
])
def test_comentario_hitl_vacio_no_se_muestra(traza):
    assert ui_agente.comentario_hitl(traza) is None


def test_estado_depuracion(sesion, procesar_falso):
    inicial = ui_agente.estado_depuracion(sesion)
    assert inicial == {
        "thread_id": sesion["thread_id"],
        "pendiente_aprobacion": False,
        "done": False,
        "filas": [],
        "comentario": None,
    }

    traza = [evento("hitl", "pausa", {"numero_pasos": 1}, "pending", "Plan pendiente")]
    procesar_falso.respuestas = [
        {"respuesta": "Propuesta", "plan": ["Paso"], "pendiente_aprobacion": True,
         "traza": traza}]
    ui_agente.enviar_turno(sesion, "Plan", None, None, procesar_falso)

    estado = ui_agente.estado_depuracion(sesion)
    assert estado["thread_id"] == sesion["thread_id"]
    assert estado["pendiente_aprobacion"] is True
    assert estado["done"] is False
    assert estado["filas"] == ui_agente.filas_traza(traza)
    assert estado["comentario"] is None


FIRMA_PNG = b"\x89PNG\r\n\x1a\n"
FIRMA_JPEG = b"\xff\xd8\xff"


def bytes_imagen(firma: bytes, total: int = 64) -> bytes:
    """Bytes mínimos con la firma indicada y el tamaño total pedido."""
    return firma + b"0" * (total - len(firma))


@pytest.mark.parametrize("mime, firma", [
    ("image/png", FIRMA_PNG),
    ("image/jpeg", FIRMA_JPEG),
])
def test_validar_imagen_acepta_png_y_jpg(mime, firma):
    datos = bytes_imagen(firma)

    imagen, aviso = ui_agente.validar_imagen(mime, datos)

    assert imagen == {"bytes": datos, "mime": mime}
    assert aviso is None


def test_validar_imagen_sin_adjunto():
    assert ui_agente.validar_imagen(None, None) == (None, None)


@pytest.mark.parametrize("mime, datos", [
    ("image/gif", b"GIF89a" + b"0" * 32),
    ("image/webp", b"RIFF0000WEBP" + b"0" * 32),
    (None, bytes_imagen(FIRMA_PNG)),
])
def test_validar_imagen_formato_no_admitido(mime, datos):
    imagen, aviso = ui_agente.validar_imagen(mime, datos)

    assert imagen is None
    assert aviso == ui_agente.AVISO_IMAGEN_FORMATO


@pytest.mark.parametrize("mime, datos", [
    ("image/png", bytes_imagen(FIRMA_JPEG)),
    ("image/png", b"GIF89a" + b"0" * 32),
    ("image/jpeg", b"esto no es una imagen"),
    ("image/png", b""),
])
def test_validar_imagen_mime_falseado(mime, datos):
    imagen, aviso = ui_agente.validar_imagen(mime, datos)

    assert imagen is None
    assert aviso == ui_agente.AVISO_IMAGEN_FORMATO


def test_validar_imagen_supera_limite():
    datos = bytes_imagen(FIRMA_PNG, config.IMAGEN_MAX_BYTES + 1)

    imagen, aviso = ui_agente.validar_imagen("image/png", datos)

    assert imagen is None
    assert aviso == ui_agente.AVISO_IMAGEN_TAMANO


def test_validar_imagen_en_limite_exacto():
    datos = bytes_imagen(FIRMA_JPEG, config.IMAGEN_MAX_BYTES)

    imagen, aviso = ui_agente.validar_imagen("image/jpeg", datos)

    assert imagen == {"bytes": datos, "mime": "image/jpeg"}
    assert aviso is None


@pytest.mark.parametrize("mime, datos, aviso", [
    ("image/gif", b"GIF89a" + b"0" * 32, "AVISO_IMAGEN_FORMATO"),
    ("image/png", bytes_imagen(FIRMA_PNG, config.IMAGEN_MAX_BYTES + 1),
     "AVISO_IMAGEN_TAMANO"),
], ids=["formato", "tamano"])
def test_imagen_invalida_no_envia_mensaje(sesion, procesar_falso, mime, datos, aviso):
    ui_agente.enviar_turno(sesion, "Mira esta foto", mime, datos, procesar_falso)

    assert procesar_falso.llamadas == []
    assert [(m["rol"], m["texto"]) for m in sesion["mensajes"]] == [
        (ui_agente.ROL_AVISO, getattr(ui_agente, aviso))]
    assert sesion["ultimo"] is None
    assert sesion["uploader_key"] == 0


def test_imagen_se_pasa_en_formato_contrato(sesion, procesar_falso):
    datos = bytes_imagen(FIRMA_PNG)
    procesar_falso.respuestas = [{"respuesta": "Veo el estanque."}]

    ui_agente.enviar_turno(sesion, "¿Qué es esto?", "image/png", datos, procesar_falso)

    imagen = procesar_falso.llamadas[0]["imagen"]
    assert imagen == {"bytes": datos, "mime": "image/png"}
    assert set(imagen) == {"bytes", "mime"}
    # La UI no describe la imagen: solo el usuario y la respuesta del agente.
    assert [(m["rol"], m["texto"]) for m in sesion["mensajes"]] == [
        (ui_agente.ROL_USUARIO, "¿Qué es esto?"),
        (ui_agente.ROL_AGENTE, "Veo el estanque."),
    ]


def test_imagen_se_descarta_tras_envio(sesion, procesar_falso):
    datos = bytes_imagen(FIRMA_JPEG)

    ui_agente.enviar_turno(sesion, "Con foto", "image/jpeg", datos, procesar_falso)
    assert sesion["uploader_key"] == 1

    ui_agente.enviar_turno(sesion, "Sin foto", None, None, procesar_falso)
    assert sesion["uploader_key"] == 1
    assert procesar_falso.llamadas[1]["imagen"] is None


CLAVE_GEMINI = "clave-gemini-de-prueba-123"
CLAVE_AEMET = "token-aemet-de-prueba-456"
CLAVE_GOOGLE = "AIza" + "B" * 35


@pytest.fixture
def entorno_secretos(monkeypatch):
    """Claves falsas en el entorno; nunca se usan las reales."""
    for variable in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "AEMET_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", CLAVE_GEMINI)
    monkeypatch.setenv("AEMET_API_KEY", CLAVE_AEMET)


def test_ocultar_secretos_valores_de_entorno(entorno_secretos):
    texto = f"Fallo con {CLAVE_GEMINI} y {CLAVE_AEMET}."

    oculto = ui_agente.ocultar_secretos(texto)

    assert CLAVE_GEMINI not in oculto and CLAVE_AEMET not in oculto
    assert oculto == f"Fallo con {ui_agente.MASCARA} y {ui_agente.MASCARA}."


def test_ocultar_secretos_patron_google(entorno_secretos):
    corta = "AIza" + "C" * 10

    oculto = ui_agente.ocultar_secretos(f"key={CLAVE_GOOGLE} y {corta}")

    assert oculto == f"key={ui_agente.MASCARA} y {corta}"


def test_ocultar_secretos_en_error_preview_y_respuesta(
        entorno_secretos, sesion, procesar_falso, aprobar_falso):
    procesar_falso.respuestas = [{
        "respuesta": f"Respuesta con {CLAVE_GEMINI}",
        "plan": [f"Paso con {CLAVE_AEMET}"],
        "pendiente_aprobacion": True,
        "error": f"Error con {CLAVE_GOOGLE}",
        "traza": [evento("tool", "api_dominio", {"comentario": CLAVE_GEMINI},
                         "error", f"preview {CLAVE_AEMET}")],
    }]

    ui_agente.enviar_turno(sesion, "Plan", None, None, procesar_falso)

    ultimo = sesion["ultimo"]
    assert ultimo["respuesta"] == f"Respuesta con {ui_agente.MASCARA}"
    assert ultimo["plan"] == [f"Paso con {ui_agente.MASCARA}"]
    assert ultimo["error"] == f"Error con {ui_agente.MASCARA}"
    assert ultimo["traza"][0]["preview"] == f"preview {ui_agente.MASCARA}"
    assert ultimo["traza"][0]["args"]["comentario"] == ui_agente.MASCARA
    # Lo que se pinta en el chat sale ya enmascarado.
    visible = str(sesion["mensajes"]) + str(ui_agente.estado_depuracion(sesion))
    for clave in (CLAVE_GEMINI, CLAVE_AEMET, CLAVE_GOOGLE):
        assert clave not in visible

    # El comentario de la decisión que se lee de la traza también.
    aprobar_falso.respuesta = {"traza": [evento(
        "hitl", "rechazar", {"comentario": f"ojo {CLAVE_GEMINI}"})]}
    ui_agente.decidir(sesion, False, "", aprobar_falso)

    assert ui_agente.estado_depuracion(sesion)["comentario"] == (
        f"ojo {ui_agente.MASCARA}")


def test_nueva_conversacion_genera_id_distinto(monkeypatch):
    repetido = uuid.UUID("11111111-1111-4111-8111-111111111111")
    nuevo = uuid.UUID("22222222-2222-4222-8222-222222222222")
    generados = iter([repetido, repetido, nuevo])
    monkeypatch.setattr(ui_agente.uuid, "uuid4", lambda: next(generados))

    sesion = ui_agente.nueva_sesion([str(repetido)])

    assert sesion["thread_id"] == str(nuevo)


def test_nueva_conversacion_vacia_estado(sesion_con_plan):
    sesion_con_plan["uploader_key"] = 3
    previos = [sesion_con_plan["thread_id"]]

    nueva = ui_agente.nueva_sesion(previos)

    assert nueva["thread_id"] not in previos
    assert nueva["mensajes"] == []
    assert nueva["ultimo"] is None
    assert nueva["uploader_key"] == 0
    assert ui_agente.pendiente(nueva) is False


def test_nueva_conversacion_con_plan_pendiente_no_decide(sesion_con_plan, aprobar_falso):
    mensajes_previos = [dict(m) for m in sesion_con_plan["mensajes"]]

    ui_agente.nueva_sesion([sesion_con_plan["thread_id"]])

    assert aprobar_falso.llamadas == []
    # El hilo anterior queda tal cual: pendiente y sin mensaje de decisión.
    assert ui_agente.pendiente(sesion_con_plan) is True
    assert sesion_con_plan["mensajes"] == mensajes_previos
    textos = [m["texto"] for m in sesion_con_plan["mensajes"]]
    assert ui_agente.MENSAJE_PLAN_APROBADO not in textos
    assert ui_agente.MENSAJE_PLAN_RECHAZADO not in textos


def test_decision_usa_mismo_thread_id(sesion_con_plan, procesar_falso, aprobar_falso):
    ui_agente.decidir(sesion_con_plan, False, "", aprobar_falso)

    assert procesar_falso.llamadas[0]["thread_id"] == sesion_con_plan["thread_id"]
    assert aprobar_falso.llamadas[0]["thread_id"] == sesion_con_plan["thread_id"]
