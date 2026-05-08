import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from groq import Groq
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
from audio_recorder_streamlit import audio_recorder
import os
import json
import logging
import io
import re

import asyncio
import tempfile
import threading

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# ==========================================
# CONFIGURACIÓN DE LOGGING
# ==========================================
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(page_title="Idiomaconnect", page_icon="✨", layout="centered")

st.markdown("""
    <style>
    /* --- FUENTES Y VARIABLES GLOBALES --- */
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&family=Space+Grotesk:wght@400;500;600&display=swap');

    :root {
        --radius-sm: 12px;
        --radius-md: 20px;
        --radius-lg: 28px;
        --shadow-soft: 0 4px 20px rgba(0,0,0,0.08);
        --shadow-lift: 0 12px 32px rgba(0,0,0,0.14);
        --transition-base: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        --text-dark: #2c3e50;
        --text-subtle: #6b7280;
    }

    html, body, [class*="css"], .stMarkdown, p, li, label, h3 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: var(--text-dark) !important;
    }
    h1, h2 {
        font-family: 'Nunito', sans-serif !important;
        font-weight: 800 !important;
        color: var(--text-dark) !important;
    }

    /* --- FONDO GENERAL --- */
    .stApp {
        background: linear-gradient(135deg, #f0f4ff 0%, #faf0ff 50%, #f0fff8 100%);
        background-attachment: fixed;
    }

    /* --- BOTONES --- */
    .stButton > button {
        border-radius: 50px !important;
        transition: var(--transition-base) !important;
        border: none !important;
        box-shadow: var(--shadow-soft) !important;
        font-family: 'Nunito', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 12px 28px !important;
        letter-spacing: 0.3px !important;
    }
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02) !important;
        box-shadow: var(--shadow-lift) !important;
        filter: brightness(1.05);
    }
    .stButton > button[kind="secondary"] {
        color: var(--text-dark) !important;
        background-color: white !important;
    }

    /* --- TARJETA DE PERFIL --- */
    .profile-card {
        padding: 28px 20px;
        border-radius: var(--radius-lg);
        text-align: center;
        color: white !important;
        margin-bottom: 16px;
        box-shadow: var(--shadow-lift);
        position: relative;
        overflow: hidden;
        animation: cardReveal 0.5s ease both;
        border: 1px solid rgba(255,255,255,0.35);
        backdrop-filter: blur(4px);
    }
    .profile-card h2 { margin: 0 0 6px 0; font-size: 1.6rem; font-weight: 800; color: white !important; }
    .profile-card p  { margin: 0; font-size: 0.9rem; opacity: 0.9; color: white !important; }
    .profile-card .emoji-avatar { font-size: 2.8rem; margin-bottom: 10px; display: block; }

    /* --- DASHBOARD HEADER --- */
    .dashboard-header {
        padding: 20px 24px;
        border-radius: var(--radius-md);
        color: white !important;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: var(--shadow-lift);
        margin-bottom: 12px;
        position: relative;
        overflow: hidden;
    }
    .dashboard-header h2, .dashboard-header h3 {
        margin: 0; position: relative; z-index: 1; color: white !important;
    }

    /* --- PANEL DE PROGRESO ACUMULADO --- */
    .progress-panel {
        background: rgba(255,255,255,0.75);
        border-radius: var(--radius-md);
        padding: 14px 20px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-around;
        align-items: center;
        box-shadow: var(--shadow-soft);
        backdrop-filter: blur(6px);
        border: 1px solid rgba(255,255,255,0.6);
        flex-wrap: wrap;
        gap: 8px;
    }
    .stat-item { text-align: center; padding: 4px 12px; }
    .stat-value {
        font-family: 'Nunito', sans-serif !important;
        font-size: 1.5rem;
        font-weight: 800;
        line-height: 1.2;
        color: var(--text-dark) !important;
    }
    .stat-label {
        font-size: 0.7rem;
        color: var(--text-subtle) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    .stat-divider {
        width: 1px;
        height: 36px;
        background: rgba(0,0,0,0.1);
    }

    /* --- SECCIÓN DE AUDIO --- */
    .audio-section {
        background: rgba(255,255,255,0.8);
        border-radius: var(--radius-md);
        padding: 18px 22px;
        margin: 16px 0;
        border: 1px solid #e0e7ff;
        box-shadow: var(--shadow-soft);
        backdrop-filter: blur(4px);
    }
    .audio-section p {
        margin: 0 0 10px 0;
        font-size: 0.88rem;
        color: var(--text-subtle) !important;
    }

    /* --- BADGE DE INTENTOS --- */
    .attempts-badge {
        display: inline-block;
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 20px;
        padding: 3px 12px;
        font-size: 0.8rem;
        font-weight: 700;
        color: #856404 !important;
        margin-left: 8px;
        vertical-align: middle;
    }
    .attempts-badge-danger {
        background: #f8d7da;
        border-color: #dc3545;
        color: #721c24 !important;
    }

    /* --- CONTENEDOR DE LECCION --- */
    .lesson-container {
        background: rgba(255,255,255,0.85);
        padding: 28px;
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-soft);
        border-left: 5px solid;
        line-height: 1.7;
        backdrop-filter: blur(8px);
        animation: slideUp 0.4s ease both;
    }
    .lesson-container, .lesson-container p, .lesson-container li {
        color: var(--text-dark) !important;
    }

    /* ================================================
       ESTILOS: SISTEMA DE QUIZ
       ================================================ */

    .quiz-container {
        background: rgba(255,255,255,0.92);
        padding: 28px 32px;
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-soft);
        border-left: 5px solid;
        backdrop-filter: blur(8px);
        animation: slideUp 0.45s ease both;
        margin-top: 8px;
    }
    .quiz-container h3 { color: var(--text-dark) !important; margin-bottom: 4px; }

    .question-card {
        background: #f8faff;
        border: 1px solid #e8edf8;
        border-radius: var(--radius-sm);
        padding: 18px 20px;
        margin-bottom: 16px;
        transition: var(--transition-base);
    }
    .question-card:hover { box-shadow: var(--shadow-soft); border-color: #d0d8f0; }
    .question-card p { margin: 0 0 10px 0; font-weight: 600; color: var(--text-dark) !important; }

    .q-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white !important;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 10px;
        border-radius: 20px;
        margin-bottom: 8px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    .quiz-section-title {
        font-family: 'Nunito', sans-serif !important;
        font-size: 1.1rem;
        font-weight: 800;
        color: var(--text-dark) !important;
        margin: 24px 0 12px 0;
        padding-bottom: 6px;
        border-bottom: 2px solid #eef0f8;
    }

    .result-panel {
        border-radius: var(--radius-md);
        padding: 28px 32px;
        text-align: center;
        animation: slideUp 0.4s ease both;
        box-shadow: var(--shadow-lift);
        margin-top: 8px;
    }
    .result-panel h2 { font-size: 2rem !important; margin-bottom: 6px; }
    .result-panel .score-number {
        font-family: 'Nunito', sans-serif;
        font-size: 3.5rem;
        font-weight: 800;
        line-height: 1;
        margin: 10px 0;
    }
    .result-pass { background: linear-gradient(135deg, #d4edda, #c3e6cb); border: 2px solid #28a745; }
    .result-fail { background: linear-gradient(135deg, #fff3cd, #ffeeba); border: 2px solid #ffc107; }
    .result-blocked { background: linear-gradient(135deg, #f8d7da, #f5c6cb); border: 2px solid #dc3545; }

    .feedback-row {
        background: white;
        border-radius: var(--radius-sm);
        padding: 12px 16px;
        margin-bottom: 10px;
        border-left: 4px solid;
        text-align: left;
        font-size: 0.88rem;
    }
    .feedback-correct { border-color: #28a745; }
    .feedback-wrong   { border-color: #dc3545; }
    .feedback-row strong { color: var(--text-dark) !important; }

    .score-bar-wrap {
        background: rgba(0,0,0,0.08);
        border-radius: 20px;
        height: 14px;
        margin: 14px 0;
        overflow: hidden;
    }
    .score-bar-fill { height: 100%; border-radius: 20px; transition: width 1s ease; }

    /* --- BIENVENIDA --- */
    .welcome-container {
        text-align: center; padding: 40px 20px 20px;
        animation: fadeIn 0.6s ease both;
    }
    .welcome-container h1 {
        font-size: 2.8rem; font-weight: 800;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; margin-bottom: 8px; color: transparent !important;
    }
    .welcome-container p { font-size: 1.1rem; color: var(--text-subtle) !important; margin-bottom: 32px; }

    /* --- BANNERS --- */
    .error-banner {
        background: #fff3f3; border: 1px solid #ffb3b3; border-left: 4px solid #e74c3c;
        border-radius: var(--radius-sm); padding: 14px 18px; margin: 12px 0;
        color: #c0392b !important; font-size: 0.9rem;
    }
    .warning-banner {
        background: #fffbf0; border: 1px solid #ffd591; border-left: 4px solid #f39c12;
        border-radius: var(--radius-sm); padding: 14px 18px; margin: 12px 0;
        color: #856404 !important; font-size: 0.9rem;
    }

    /* --- RADIO Y TEXT INPUT --- */
    .stRadio > div { gap: 6px !important; }
    .stRadio label { color: var(--text-dark) !important; }
    .stTextInput input {
        border-radius: var(--radius-sm) !important;
        border: 1.5px solid #667eea !important;
        font-family: 'Space Grotesk', sans-serif !important;
        background-color: #3b2f6e !important;
        color: #ffffff !important;
        caret-color: #ffffff !important;
    }
    .stTextInput input::placeholder {
        color: rgba(255,255,255,0.55) !important;
        opacity: 1 !important;
    }
    .stTextInput input:focus {
        border-color: #a78bfa !important;
        background-color: #4a3a85 !important;
        box-shadow: 0 0 0 3px rgba(167,139,250,0.25) !important;
        color: #ffffff !important;
    }

    /* Quitar borde rojo por defecto de st.form */
    [data-testid="stForm"] { border: none !important; padding: 0 !important; }

    /* --- ANIMACIONES --- */
    @keyframes cardReveal { from { opacity:0; transform:translateY(20px) scale(0.96); } to { opacity:1; transform:translateY(0) scale(1); } }
    @keyframes fadeIn     { from { opacity:0; } to { opacity:1; } }
    @keyframes slideUp    { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }

    div[data-testid="column"]:nth-child(1) .profile-card { animation-delay: 0.0s; }
    div[data-testid="column"]:nth-child(2) .profile-card { animation-delay: 0.1s; }
    div[data-testid="column"]:nth-child(3) .profile-card { animation-delay: 0.2s; }

    .help-text, .section-title { color: var(--text-dark) !important; font-weight: 600; }

    @media (max-width: 640px) {
        .welcome-container h1 { font-size: 2rem; }
        .dashboard-header { flex-direction: column; gap: 8px; text-align: center; }
        .quiz-container { padding: 18px; }
        .result-panel { padding: 20px; }
        .progress-panel { flex-direction: column; gap: 4px; }
    }

    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. CONTEXTO FAMILIAR Y PERFILES
# ==========================================

PROFILES = {
    # ── Hijas de Juan Carlos ─────────────────────────────────────────────
    "Antonia": {
        "color": "#8e44ad",
        "gradient": "linear-gradient(135deg, #9b59b6, #6c3483)",
        "emoji": "🎨",
        "gender": "niña",
        "age_desc": "13 años (nacida el 24/Sept/2012)",
        "grade": "8vo básico",
        "hobbies": "Tenis y pintura",
        "tone": "Creativo e inspirador, usa metaforas visuales y de deporte.",
        "family_context": """
Contexto familiar de Antonia (usa esto para crear ejemplos, historias y ejercicios):
- Padres: Juan Carlos y Daniela (divorciados; usar 'Dad's house' y 'Mom's house').
- Pareja del papa: Camila. Hermano menor: Amaro (bebe de 10 meses).
- Hermanas: Belen y Sofia (trillizas).
- Abuelos maternos: Regina y Jorge Hernan. Abuelos paternos: Silvia y Mario.
- Tios: Carlos, Natalia, Pamela. Primos: Agustin (14), Maximo (12), Luciana, Julian, Antonela (12).
- Mascotas: Gatos (Rosita, Toribio, Blanca, Leon) y Perros (Pink-poodle, Alma-doberman, Odin-doberman).
"""
    },
    "Belen": {
        "color": "#2980b9",
        "gradient": "linear-gradient(135deg, #3498db, #1a6fa0)",
        "emoji": "🎹",
        "gender": "niña",
        "age_desc": "13 años (nacida el 24/Sept/2012)",
        "grade": "8vo básico",
        "hobbies": "Piano y musica",
        "tone": "Armonioso y ritmico, usa analogias musicales y melodiosas.",
        "family_context": """
Contexto familiar de Belen (usa esto para crear ejemplos, historias y ejercicios):
- Padres: Juan Carlos y Daniela (divorciados; usar 'Dad's house' y 'Mom's house').
- Pareja del papa: Camila. Hermano menor: Amaro (bebe de 10 meses).
- Hermanas: Antonia y Sofia (trillizas).
- Abuelos maternos: Regina y Jorge Hernan. Abuelos paternos: Silvia y Mario.
- Tios: Carlos, Natalia, Pamela. Primos: Agustin (14), Maximo (12), Luciana, Julian, Antonela (12).
- Mascotas: Gatos (Rosita, Toribio, Blanca, Leon) y Perros (Pink-poodle, Alma-doberman, Odin-doberman).
"""
    },
    "Sofia": {
        "color": "#d35400",
        "gradient": "linear-gradient(135deg, #e67e22, #a04000)",
        "emoji": "🤸",
        "gender": "niña",
        "age_desc": "13 años (nacida el 24/Sept/2012)",
        "grade": "8vo básico",
        "hobbies": "Gimnasia",
        "tone": "Dinamico, energetico y enfocado en la superacion fisica y el movimiento.",
        "family_context": """
Contexto familiar de Sofia (usa esto para crear ejemplos, historias y ejercicios):
- Padres: Juan Carlos y Daniela (divorciados; usar 'Dad's house' y 'Mom's house').
- Pareja del papa: Camila. Hermano menor: Amaro (bebe de 10 meses).
- Hermanas: Antonia y Belen (trillizas).
- Abuelos maternos: Regina y Jorge Hernan. Abuelos paternos: Silvia y Mario.
- Tios: Carlos, Natalia, Pamela. Primos: Agustin (14), Maximo (12), Luciana, Julian, Antonela (12).
- Mascotas: Gatos (Rosita, Toribio, Blanca, Leon) y Perros (Pink-poodle, Alma-doberman, Odin-doberman).
"""
    },
    # ── Sobrinos (hijos de Carlos y Natalia) ─────────────────────────────
    "Agustin": {
        "color": "#16a085",
        "gradient": "linear-gradient(135deg, #1abc9c, #0e6655)",
        "emoji": "✈️",
        "gender": "niño",
        "age_desc": "14 años",
        "grade": "8vo básico",
        "hobbies": "Futbol, videojuegos, le apasiona la medicina y la aviacion militar (sueña con ser medico o piloto de la Fuerza Aerea)",
        "tone": "Aventurero y ambicioso, usa analogias de aviacion, medicina, jugadas de futbol y misiones de videojuegos. Habla de metas y logros grandes.",
        "family_context": """
Contexto familiar de Agustin (usa esto para crear ejemplos, historias y ejercicios):
- Papa: Carlos. Mama: Natalia.
- Hermano menor: Maximo (12 años, 7mo basico).
- Tio: Juan Carlos. Tia: Camila.
- Primas: Antonia, Belen y Sofia (trillizas de 13 años, hijas de su tio Juan Carlos).
- Primo/a adicional: Antonela (12 años, vive en Villarrica).
- Mascota: Guquito (perro). Viven en Santiago.
- Nota: Agustin sueña con ser medico o piloto de la Fuerza Aerea de Chile.
"""
    },
    "Maximo": {
        "color": "#c0392b",
        "gradient": "linear-gradient(135deg, #e74c3c, #922b21)",
        "emoji": "🎮",
        "gender": "niño",
        "age_desc": "12 años",
        "grade": "7mo básico",
        "hobbies": "Futbol, videojuegos, le apasiona la medicina (sueña con ser medico)",
        "tone": "Curioso y analitico, usa analogias de videojuegos, niveles y misiones, medicina y futbol. Celebra cada avance como subir de nivel.",
        "family_context": """
Contexto familiar de Maximo (usa esto para crear ejemplos, historias y ejercicios):
- Papa: Carlos. Mama: Natalia.
- Hermano mayor: Agustin (14 años, 8vo basico).
- Tio: Juan Carlos. Tia: Camila.
- Primas: Antonia, Belen y Sofia (trillizas de 13 años, hijas de su tio Juan Carlos).
- Primo/a adicional: Antonela (12 años, vive en Villarrica).
- Mascota: Guquito (perro). Viven en Santiago.
- Nota: Maximo sueña con ser medico.
"""
    },
    # ── Sobrina (por otra rama familiar) ─────────────────────────────────
    "Antonela": {
        "color": "#e91e8c",
        "gradient": "linear-gradient(135deg, #f06292, #880e4f)",
        "emoji": "🎻",
        "gender": "niña",
        "age_desc": "12 años",
        "grade": "7mo básico",
        "hobbies": "Violin, basquetbol y scouts (va cada domingo)",
        "tone": "Alegre, aventurero y comunitario, mezcla analogias musicales del violin con la energia del basquetbol y los valores de exploradora scout. Usa imagenes de naturaleza y trabajo en equipo.",
        "family_context": """
Contexto familiar de Antonela (usa esto para crear ejemplos, historias y ejercicios):
- Papa: Rodrigo. Mama: Marisela.
- Hermana: Florencia.
- Abuelo: Moises. Abuela: Ninfia.
- Tio: Juan Carlos. Tia: Camila.
- Mascotas: Odin y Polka (perros), Colela (oveja), una chiva.
- Vive en el campo en la ciudad de Villarrica (sur de Chile, zona de lagos y bosques).
- Los domingos va a scout: le encanta la naturaleza, el trabajo en equipo y las aventuras al aire libre.
"""
    },
}

# ==========================================
# CONSTANTES DE CONFIGURACION
# ==========================================
GROQ_MODEL_CHAT  = "llama-3.1-8b-instant"
GROQ_MODEL_AUDIO = "whisper-large-v3"
GROQ_MAX_TOKENS  = 4000
GROQ_TEMPERATURE = 0.7
XP_PER_LESSON    = 50
PASSING_SCORE    = 0.60
MAX_QUIZ_ATTEMPTS = 3          # Máximo de intentos por lección
GSHEETS_SCOPE    = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
REPORT_EMAIL_TO  = "jccubillos@gmail.com"
TEMP_AUDIO_FILE  = "temp_audio.wav"


# ==========================================
# 3. CONEXIONES A APIS
# ==========================================
@st.cache_resource(show_spinner=False)
def init_groq_client():
    """Inicializa y cachea el cliente Groq."""
    try:
        key = st.secrets["GROQ_API_KEY"]
        if not key or key.strip() == "":
            return None, "GROQ_API_KEY esta vacia en secrets.toml."
        return Groq(api_key=key), None
    except KeyError:
        return None, "Falta `GROQ_API_KEY` en `.streamlit/secrets.toml`."
    except Exception as e:
        logger.error(f"Error al inicializar Groq: {e}")
        return None, f"Error inesperado al conectar con Groq: {e}"


@st.cache_resource(show_spinner=False)
def get_db_connection():
    """Retorna (sheet, error). Conexion cacheada a Google Sheets."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, GSHEETS_SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open("Idiomaconnect_DB").sheet1
        return sheet, None
    except KeyError:
        return None, "Faltan credenciales `gcp_service_account` en secrets.toml."
    except gspread.exceptions.SpreadsheetNotFound:
        return None, "Hoja 'Idiomaconnect_DB' no encontrada."
    except Exception as e:
        logger.error(f"Error Google Sheets: {e}")
        return None, f"No se pudo conectar a Google Sheets: {e}"


# ==========================================
# 4. FUNCIONES PRINCIPALES
# ==========================================

def _build_system_prompt_json(profile_name: str) -> str:
    """System prompt que instruye al LLM a generar un JSON robusto."""
    profile  = PROFILES[profile_name]
    gender   = profile.get("gender", "niño/niña")
    pronoun  = "ella" if gender == "niña" else "él"
    age_desc = profile.get("age_desc", "13 años")
    grade    = profile.get("grade", "")
    return f"""
Eres un tutor de inglés experto, cariñoso y motivador, diseñado exclusivamente para {profile_name}, un/a {gender} de {age_desc}, cursando {grade}.
A {pronoun} le apasiona: {profile['hobbies']}.
Tu tono debe ser: {profile['tone']}.

{profile['family_context']}

════════════════════════════════════════
INSTRUCCIÓN CRÍTICA DE FORMATO JSON:
════════════════════════════════════════
Debes responder ÚNICAMENTE con un objeto JSON válido. Sin texto antes ni después.
REGLA DE ORO PARA EVITAR ERRORES: ESTÁ TOTALMENTE PROHIBIDO USAR COMILLAS DOBLES (") DENTRO DE TUS TEXTOS Y EXPLICACIONES. Si necesitas citar algo, usa comillas simples (').
Todos los saltos de línea dentro de los strings del JSON deben ser \\n.

El JSON debe tener EXACTAMENTE esta estructura:
{{
  "title": "<Un título corto y atractivo para la clase en español. Ej: ¡Misión de Rescate!>",
  "academic_topic": "<El tema gramatical o vocabulario exacto de la clase. Ej: Verbo To be, Vocabulario de la casa, Adjetivos>",
  "lesson": "<string con la lección completa en formato Markdown — ver instrucciones abajo>",
  "mc": [
    {{
      "q": "<pregunta en inglés>",
      "options": ["<opción A>", "<opción B>", "<opción C>", "<opción D>"],
      "answer": "<texto exacto de la opción correcta>"
    }}
  ],
  "fitb": [
    {{
      "sentence": "<oración en inglés con ___ donde va la palabra>",
      "answer": "<única palabra correcta en minúsculas sin tildes>"
    }}
  ]
}}

════════════════════════════════════════
INSTRUCCIONES PARA EL CAMPO "lesson":
════════════════════════════════════════
La lección debe ser EXTENSA, CLARA y PEDAGÓGICA, estructurada en 4 partes usando Markdown.
Idioma: explicaciones siempre en español, los términos en inglés van en **negrita**.

TU PRIORIDAD COMO TUTOR ES LA CLARIDAD Y LA COMPRENSIÓN PROFUNDA:
- Explica el PORQUÉ de cada regla, no solo el QUÉ. Si hay una excepción, nómbrala.
- Usa analogías simples cuando el concepto sea difícil ("funciona igual que en español cuando...").
- Antes de dar un ejemplo, asegúrate de que la alumna ya entendió la regla base.
- No asumas que la alumna conoce términos gramaticales técnicos; si los usas, defínelos.
- Escribe como si le estuvieras explicando en persona: cálido, paciente, preciso.

ESTRUCTURA OBLIGATORIA DE LA LECCIÓN (mínimo 300 palabras en total):

### 🌟 Parte A — [Subtítulo creativo relacionado al tema]
- Introducción narrativa de 3 a 5 oraciones que conecte el tema con {profile_name}, sus hobbies o su familia.
- El objetivo es crear contexto emocional: ¿por qué este tema le va a servir en su vida real?

### 📖 Parte B — ¿Qué vamos a aprender hoy?
- Explicación teórica CLARA y DETALLADA del concepto gramatical o vocabulario.
- Mínimo 180 palabras. Usa párrafos cortos, no bloques de texto denso.
- Incluye: (1) la regla principal, (2) cómo se forma o usa, (3) al menos UN error común que cometen los hispanohablantes y cómo evitarlo.
- Si el tema es vocabulario: incluye tabla o lista con la palabra en inglés, su pronunciación aproximada entre corchetes [pro-nun-cia-ción] y su significado en español.
- Usa negritas para resaltar las palabras o reglas clave.

### ✏️ Parte C — Ejemplos en acción
- Entre 6 y 10 oraciones de ejemplo en inglés.
- Cada ejemplo debe tener: la oración en inglés (con la palabra/concepto clave en **negrita**) + su traducción al español entre paréntesis en *cursiva*.
- Al menos 3 ejemplos deben usar nombres de familiares o mascotas de {profile_name} (ver contexto familiar arriba).
- Después de los ejemplos, incluye un párrafo corto de 2-3 oraciones que resuma el patrón que se repite en todos los ejemplos.

### 🎯 Parte D — Tip de Oro + Reto
- Un consejo práctico memorable de 2-3 oraciones (algo que la alumna pueda recordar fácilmente).
- Una pregunta o mini-reto corto (1 pregunta) para reflexionar antes del quiz. No requiere respuesta escrita aquí.

════════════════════════════════════════
INSTRUCCIONES PARA "mc" Y "fitb":
════════════════════════════════════════
- "mc": entre 5 y 8 preguntas de múltiple choice BASADAS DIRECTAMENTE en la lección.
  Las opciones incorrectas deben representar errores comunes y reales, no respuestas absurdas.
- "fitb": 5 preguntas de completar la oración, usando oraciones que aparezcan o sean similares a los ejemplos de la Parte C.
  La respuesta ("answer") debe ser UNA sola palabra en minúsculas sin puntuación ni tildes.
"""


def generate_lesson_and_quiz(profile_name: str, topic: str, custom_text: str | None = None):
    """Llama a Groq con JSON mode."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    system_prompt = _build_system_prompt_json(profile_name)
    # Sanitize user input before sending to the LLM
    safe_topic = topic.strip()[:300] if topic else "Aventura Diaria"
    safe_custom = custom_text.strip()[:500] if custom_text else None

    user_prompt = f"El tema de la leccion de hoy es: {safe_topic}."
    if safe_custom:
        user_prompt += f" Contexto adicional de la alumna: '{safe_custom}'. Adapta leccion y quiz a este tema."

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=GROQ_TEMPERATURE,
            max_tokens=GROQ_MAX_TOKENS,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content

        raw_clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw_clean)

        if not all(k in data for k in ("title", "academic_topic", "lesson", "mc", "fitb")):
            raise ValueError("JSON incompleto. Asegúrate de generar 'title', 'academic_topic', 'lesson', 'mc' y 'fitb'.")

        return data, None

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}. Raw (primeros 500 chars): {raw[:500]}")
        return None, f"El modelo no devolvio JSON valido. Intenta de nuevo. (Detalle: {e})"
    except ValueError as e:
        logger.error(f"Validacion JSON fallida: {e}")
        return None, str(e)
    except Exception as e:
        err_str = str(e).lower()
        if "rate_limit" in err_str or "429" in err_str:
            return None, "Limite de la API de Groq alcanzado. Espera un momento. ⏳"
        elif "timeout" in err_str or "connection" in err_str:
            return None, "Error de conexion con Groq. Verifica tu internet. 🌐"
        else:
            logger.error(f"Groq error inesperado: {e}")
            return None, f"Error inesperado de la API: {e}"


def transcribe_audio(audio_bytes: bytes):
    """Transcribe audio con Groq Whisper."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"
    try:
        with open(TEMP_AUDIO_FILE, "wb") as f:
            f.write(audio_bytes)
        with open(TEMP_AUDIO_FILE, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(TEMP_AUDIO_FILE, file.read()),
                model=GROQ_MODEL_AUDIO,
            )
        return transcription.text, None
    except Exception as e:
        logger.error(f"Error transcripcion Whisper: {e}")
        return None, f"No se pudo transcribir el audio: {e}"
    finally:
        if os.path.exists(TEMP_AUDIO_FILE):
            os.remove(TEMP_AUDIO_FILE)


def _strip_markdown(text: str) -> str:
    """Elimina formato Markdown para generar audio TTS limpio."""
    # Encabezados
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Negrita e itálica
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'_{1,3}(.*?)_{1,3}', r'\1', text, flags=re.DOTALL)
    # Links [texto](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Código
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Líneas horizontales
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Emojis comunes en las lecciones — se reemplazan para que el TTS no los lea
    text = re.sub(r'[🌟📖✏️🎯🏆⭐🎨🎹🤸💪🔥📚🧠✅❌🎉👋🗺️📝🔊🇬🇧]+', '', text)
    # Espacios múltiples y líneas en blanco excesivas
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def generate_lesson_audio(lesson_text: str) -> bytes | None:
    """
    Genera audio TTS usando edge-tts con voz bilingüe es-US-PalomaNeural.
    Corre en un hilo separado con su propio event loop para no interferir
    con el event loop de Streamlit/uvicorn.
    """
    if not EDGE_TTS_AVAILABLE:
        return None

    clean_text = _strip_markdown(lesson_text)[:5000]
    if not clean_text:
        return None

    VOICE = "es-US-PalomaNeural"
    result_holder = [None]
    error_holder  = [None]

    def run_in_thread():
        tmp_path = None
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp.close()
            tmp_path = tmp.name

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def _generate():
                    communicate = edge_tts.Communicate(clean_text, VOICE)
                    await communicate.save(tmp_path)
                loop.run_until_complete(_generate())
            finally:
                loop.close()

            with open(tmp_path, "rb") as f:
                result_holder[0] = f.read()
        except Exception as e:
            error_holder[0] = e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    t = threading.Thread(target=run_in_thread, daemon=True)
    t.start()
    t.join(timeout=30)

    if error_holder[0]:
        logger.error(f"Error generando audio edge-tts: {error_holder[0]}")
        return None
    return result_holder[0]


@st.cache_data(ttl=120, show_spinner=False)
def get_user_stats(profile_name: str) -> dict:
    """Obtiene estadísticas acumuladas del usuario desde Google Sheets (caché 2 min)."""
    empty = {"total_xp": 0, "total_sessions": 0, "avg_score": 0.0,
             "week_xp": 0, "best_score": 0.0}
    sheet, _ = get_db_connection()
    if not sheet:
        return empty
    try:
        rows = sheet.get_all_records()
        user_rows = [r for r in rows if r.get("profile", "") == profile_name]
        if not user_rows:
            return empty

        total_xp = sum(int(r.get("xp", 0) or 0) for r in user_rows)
        total_sessions = len(user_rows)

        scores = []
        for r in user_rows:
            score_str = str(r.get("score_pct", "0%")).replace("%", "")
            try:
                scores.append(float(score_str) / 100.0)
            except ValueError:
                pass
        avg_score = sum(scores) / len(scores) if scores else 0.0
        best_score = max(scores) if scores else 0.0

        # XP de la semana actual (lunes a hoy)
        now = datetime.datetime.now()
        week_start = (now - datetime.timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        week_xp = 0
        for r in user_rows:
            ts_str = r.get("timestamp", "")
            try:
                ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                if ts >= week_start:
                    week_xp += int(r.get("xp", 0) or 0)
            except Exception:
                pass

        return {
            "total_xp":      total_xp,
            "total_sessions": total_sessions,
            "avg_score":     avg_score,
            "week_xp":       week_xp,
            "best_score":    best_score,
        }
    except Exception as e:
        logger.error(f"Error cargando estadisticas de usuario: {e}")
        return empty


def save_xp_to_sheet(profile_name: str, xp_gained: int, score_pct: float, attempts: int):
    """Registra una sesion completada en Google Sheets."""
    sheet, db_error = get_db_connection()
    if db_error or not sheet:
        logger.warning(f"No se pudo guardar XP: {db_error}")
        return False, db_error
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        score_str = f"{score_pct:.1%}"
        sheet.append_row([timestamp, profile_name, xp_gained, score_str, attempts])
        # Invalidar caché de estadísticas para reflejar el nuevo registro
        get_user_stats.clear()
        return True, None
    except Exception as e:
        logger.error(f"Error guardando en Sheets: {e}")
        return False, f"Error de Google Sheets: {e}"


def evaluate_quiz(mc_questions: list, fitb_questions: list,
                  mc_answers: dict, fitb_answers: dict) -> dict:
    """Evalua respuestas del usuario contra las correctas."""
    correct       = 0
    total         = len(mc_questions) + len(fitb_questions)
    feedback_mc   = []
    feedback_fitb = []

    for i, q in enumerate(mc_questions):
        user_ans    = mc_answers.get(i, "")
        correct_ans = q.get("answer", "")
        is_correct  = (user_ans.strip() == correct_ans.strip())
        if is_correct:
            correct += 1
        feedback_mc.append({
            "question":       q.get("q", ""),
            "user_answer":    user_ans or "(sin respuesta)",
            "correct_answer": correct_ans,
            "is_correct":     is_correct,
        })

    for i, q in enumerate(fitb_questions):
        user_ans    = fitb_answers.get(i, "").strip().lower()
        correct_ans = q.get("answer", "").strip().lower()
        is_correct  = (user_ans == correct_ans)
        if is_correct:
            correct += 1
        feedback_fitb.append({
            "sentence":       q.get("sentence", ""),
            "user_answer":    fitb_answers.get(i, "") or "(sin respuesta)",
            "correct_answer": q.get("answer", ""),
            "is_correct":     is_correct,
        })

    score_pct = correct / total if total > 0 else 0.0
    return {
        "score_pct":     score_pct,
        "passed":        score_pct >= PASSING_SCORE,
        "correct":       correct,
        "total":         total,
        "feedback_mc":   feedback_mc,
        "feedback_fitb": feedback_fitb,
    }


def send_weekly_report():
    """
    Envía el reporte semanal por email UNA SOLA VEZ cada viernes,
    a partir de las 12:00 hr (horario Chile, America/Santiago).

    Mecanismo anti-spam de triple capa:
      1. Verifica que sea viernes Y que sean >= 12:00 hr en Chile.
      2. Guarda la clave del viernes en st.session_state (guard por sesión).
      3. Guarda la clave en Google Sheets (guard persistente entre reinicios).
    El reporte incluye SOLO la actividad de la semana en curso.
    """
    import zoneinfo

    # --- 1. Timezone Chile con fallback correcto ---
    try:
        chile_tz = zoneinfo.ZoneInfo("America/Santiago")
    except Exception:
        # Fallback DST-aware: Chile es UTC-3 en verano (oct-mar), UTC-4 en invierno
        month = datetime.datetime.utcnow().month
        offset = -3 if month in (10, 11, 12, 1, 2, 3) else -4
        chile_tz = datetime.timezone(datetime.timedelta(hours=offset))

    now_chile = datetime.datetime.now(tz=chile_tz)

    # Solo los viernes (weekday 4) a partir de las 12:00
    if now_chile.weekday() != 4:
        return
    if now_chile.hour < 12:
        return

    report_key = now_chile.strftime("report_sent_%Y_W%W")

    # --- 2. Guard en session_state ---
    if st.session_state.get(report_key, False):
        return

    # --- 3. Guard persistente en Google Sheets ---
    sheet, _ = get_db_connection()
    meta_sheet = None
    if sheet:
        try:
            spreadsheet = sheet.spreadsheet
            try:
                meta_sheet = spreadsheet.worksheet("meta")
            except gspread.exceptions.WorksheetNotFound:
                meta_sheet = spreadsheet.add_worksheet(title="meta", rows=10, cols=2)

            saved_key = ""
            try:
                saved_key = meta_sheet.cell(1, 1).value or ""
            except Exception:
                pass

            if saved_key == report_key:
                st.session_state[report_key] = True
                return

        except Exception as e:
            logger.warning(f"No se pudo verificar meta sheet: {e}")

    # --- 4. Construir reporte SOLO con datos de esta semana ---
    try:
        sender   = st.secrets["email_sender"]
        password = st.secrets["email_password"]

        report_lines = []
        if sheet:
            try:
                rows = sheet.get_all_records()

                # Calcular inicio de semana en hora Chile (naive para comparación)
                week_start_naive = (
                    now_chile - datetime.timedelta(days=now_chile.weekday())
                ).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

                summary = {}
                for row in rows:
                    ts_str = row.get("timestamp", "")
                    try:
                        ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        ts = None

                    # Ignorar registros anteriores a esta semana
                    if ts is None or ts < week_start_naive:
                        continue

                    name  = row.get("profile", "")
                    xp    = int(row.get("xp", 0) or 0)
                    score = str(row.get("score_pct", "0%")).replace("%", "")
                    try:
                        score_f = float(score) / 100.0
                    except ValueError:
                        score_f = 0.0
                    if name not in summary:
                        summary[name] = {"xp": 0, "sessions": 0, "score_sum": 0.0}
                    summary[name]["xp"]        += xp
                    summary[name]["sessions"]  += 1
                    summary[name]["score_sum"] += score_f

                for name, s in summary.items():
                    avg = s["score_sum"] / s["sessions"] if s["sessions"] > 0 else 0
                    report_lines.append(
                        f"  - {name}: {s['xp']} XP | {s['sessions']} lecciones | "
                        f"Promedio quiz: {avg:.0%}"
                    )
            except Exception as e:
                logger.warning(f"Error leyendo Sheets para reporte: {e}")

        if not report_lines:
            report_lines = ["  (No hubo actividad registrada esta semana)"]

        fecha_str = now_chile.strftime("%d/%m/%Y")
        body = (
            f"Hola Juan Carlos!\n\n"
            f"Resumen de actividad de las trillizas esta semana ({fecha_str}):\n\n"
            + "\n".join(report_lines)
            + "\n\nSiguen avanzando muy bien. Hasta el proximo viernes!\n"
            + "- IdiomaConnect"
        )
        msg = MIMEMultipart()
        msg['From']    = sender
        msg['To']      = REPORT_EMAIL_TO
        msg['Subject'] = f"Reporte Semanal IdiomaConnect — {fecha_str}"
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, REPORT_EMAIL_TO, msg.as_string())

        logger.info(f"Reporte semanal enviado correctamente ({fecha_str}).")

        # --- 5. Marcar como enviado en ambas capas ---
        st.session_state[report_key] = True
        if sheet and meta_sheet:
            try:
                meta_sheet.update_cell(1, 1, report_key)
            except Exception as e:
                logger.warning(f"No se pudo guardar report_key en meta sheet: {e}")

    except KeyError as e:
        logger.error(f"Falta credencial de email en secrets.toml: {e}")
    except Exception as e:
        logger.error(f"Error al enviar reporte semanal: {e}")


def show_error(message: str):
    st.markdown(f"<div class='error-banner'>⚠️ {message}</div>", unsafe_allow_html=True)

def show_warning(message: str):
    st.markdown(f"<div class='warning-banner'>ℹ️ {message}</div>", unsafe_allow_html=True)

def _quiz_section_title(text: str):
    st.markdown(f"<p class='quiz-section-title'>{text}</p>", unsafe_allow_html=True)


# ==========================================
# 5. MANEJO DE ESTADO (Session State)
# ==========================================
_STATE_DEFAULTS = {
    "current_user":    None,
    "xp":              0,
    "quiz_data":       None,
    "lesson_error":    None,
    "lesson_pending":  False,
    "quiz_result":     None,
    "quiz_attempts":   0,
    "last_text_input": "",
    "lesson_audio":    None,   # bytes MP3 cacheados del audio de la lección
}
for key, default in _STATE_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ==========================================
# 6. INTERFAZ DE USUARIO
# ==========================================
if st.session_state.current_user is None:
    st.markdown("""
        <div class='welcome-container'>
            <h1>✨ IdiomaConnect</h1>
            <p>¿Quién está lista para aprender inglés hoy?</p>
        </div>
    """, unsafe_allow_html=True)

    profile_list = list(PROFILES.items())
    # Separar en dos grupos: hijas y sobrinos
    group_labels = {
        0: "👧 Mis Hijas",
        1: "👦👧 Mis Sobrinos",
    }
    groups = [profile_list[:3], profile_list[3:]]
    for g_idx, group in enumerate(groups):
        if not group:
            continue
        st.markdown(
            f"<p style='text-align:center; font-weight:700; color:#6b7280; "
            f"font-size:0.85rem; letter-spacing:1px; text-transform:uppercase; "
            f"margin: 20px 0 8px 0;'>{group_labels[g_idx]}</p>",
            unsafe_allow_html=True
        )
        cols = st.columns(3)
        for j, (name, pdata) in enumerate(group):
            with cols[j]:
                st.markdown(f"""
                    <div class='profile-card' style='background: {pdata["gradient"]};'>
                        <span class='emoji-avatar'>{pdata["emoji"]}</span>
                        <h2>{name}</h2>
                        <p>{pdata["hobbies"].split(',')[0]}</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"¡Soy {name}!", key=f"btn_{name}", use_container_width=True):
                    for k, v in _STATE_DEFAULTS.items():
                        st.session_state[k] = v
                    st.session_state.current_user = name
                    st.rerun()

else:
    user  = st.session_state.current_user
    pdata = PROFILES[user]
    color = pdata["color"]

    # --- ENCABEZADO ---
    st.markdown(f"""
        <div class='dashboard-header' style='background: {pdata["gradient"]};'>
            <h2>{pdata["emoji"]} ¡Hola, {user}!</h2>
            <h3>⭐ {st.session_state.xp} XP</h3>
        </div>
    """, unsafe_allow_html=True)

    # --- PANEL DE PROGRESO ACUMULADO (desde Google Sheets) ---
    stats = get_user_stats(user)
    if stats["total_sessions"] > 0:
        st.markdown(f"""
            <div class='progress-panel'>
                <div class='stat-item'>
                    <div class='stat-value' style='color:{color} !important;'>{stats["total_xp"]}</div>
                    <div class='stat-label'>XP Total</div>
                </div>
                <div class='stat-divider'></div>
                <div class='stat-item'>
                    <div class='stat-value'>{stats["total_sessions"]}</div>
                    <div class='stat-label'>Lecciones</div>
                </div>
                <div class='stat-divider'></div>
                <div class='stat-item'>
                    <div class='stat-value'>{stats["avg_score"]:.0%}</div>
                    <div class='stat-label'>Promedio Quiz</div>
                </div>
                <div class='stat-divider'></div>
                <div class='stat-item'>
                    <div class='stat-value' style='color:#f39c12 !important;'>{stats["week_xp"]}</div>
                    <div class='stat-label'>XP esta semana</div>
                </div>
                <div class='stat-divider'></div>
                <div class='stat-item'>
                    <div class='stat-value' style='color:#27ae60 !important;'>{stats["best_score"]:.0%}</div>
                    <div class='stat-label'>Mejor nota</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    if st.button("← Cambiar alumna", type="secondary"):
        for k, v in _STATE_DEFAULTS.items():
            st.session_state[k] = v
        st.rerun()

    st.write("---")
    st.markdown(f"<h3 class='section-title'>¿Qué quieres aprender hoy, {user}?</h3>",
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<p class='help-text'>🤖 <b>Ruta Automática</b></p>", unsafe_allow_html=True)
        st.markdown("<p style='margin-bottom:5px; font-size:0.9rem;'>Deja que la IA elija por ti:</p>",
                    unsafe_allow_html=True)

        if st.button("🗺️ Que la IA me guíe (Gramática)", use_container_width=True):
            st.session_state.lesson_pending = True
            st.session_state.lesson_topic   = "Aventura Diaria (Reglas gramaticales divertidas y estructuradas)"
            st.session_state.lesson_text    = None
            st.session_state.quiz_data      = None
            st.session_state.quiz_result    = None
            st.session_state.quiz_attempts  = 0
            st.session_state.lesson_error   = None
            st.session_state.lesson_audio   = None

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("📝 Aprendamos Vocabulario", use_container_width=True):
            st.session_state.lesson_pending = True
            st.session_state.lesson_topic   = "Vocabulario Práctico (Aprender palabras nuevas, adjetivos, objetos de la casa, direcciones como arriba/abajo o verbos de acción simple. PROHIBIDO usar gramática compleja o densa, enfócate 100% en ampliar su vocabulario y mostrar el significado de las palabras)"
            st.session_state.lesson_text    = None
            st.session_state.quiz_data      = None
            st.session_state.quiz_result    = None
            st.session_state.quiz_attempts  = 0
            st.session_state.lesson_error   = None
            st.session_state.lesson_audio   = None

    with col2:
        st.markdown("<p class='help-text'>🙋‍♀️ <b>Tema Escolar / Personalizado</b></p>",
                    unsafe_allow_html=True)
        st.markdown("<p style='margin-bottom:5px; font-size:0.9rem;'>Graba tu voz o escribe el tema:</p>",
                    unsafe_allow_html=True)

        audio_bytes = audio_recorder(
            text="Clic para hablar", recording_color="#e74c3c",
            neutral_color=color, icon_size="2x"
        )
        if audio_bytes and not st.session_state.lesson_pending:
            with st.spinner("Escuchando tu voz... 🎙️"):
                text, t_error = transcribe_audio(audio_bytes)
            if t_error:
                show_error(t_error)
            elif text:
                st.success(f"Te escuché decir: *'{text}'*")
                st.session_state.lesson_pending = True
                st.session_state.lesson_topic   = "Tema del Colegio"
                st.session_state.lesson_text    = text
                st.session_state.quiz_data      = None
                st.session_state.quiz_result    = None
                st.session_state.quiz_attempts  = 0
                st.session_state.lesson_error   = None
                st.session_state.lesson_audio   = None

        text_input = st.chat_input(f"¿Qué estás aprendiendo en clase, {user}?")
        if (text_input
                and text_input != st.session_state.last_text_input
                and not st.session_state.lesson_pending):
            st.session_state.last_text_input = text_input
            st.session_state.lesson_pending  = True
            st.session_state.lesson_topic    = "Tema del Colegio"
            st.session_state.lesson_text     = text_input
            st.session_state.quiz_data       = None
            st.session_state.quiz_result     = None
            st.session_state.quiz_attempts   = 0
            st.session_state.lesson_error    = None
            st.session_state.lesson_audio    = None

    # --- GENERAR LECCIÓN ---
    if st.session_state.lesson_pending:
        topic       = st.session_state.get("lesson_topic", "Aventura Diaria")
        custom_text = st.session_state.get("lesson_text", None)

        with st.spinner("✨ Preparando tu lección y quiz con Llama 3.1... (~10 segundos)"):
            data_parsed, error = generate_lesson_and_quiz(user, topic, custom_text)

        st.session_state.quiz_data      = data_parsed
        st.session_state.lesson_error   = error
        st.session_state.lesson_pending = False
        st.session_state.lesson_text    = None

    if st.session_state.lesson_error:
        show_error(f"Error al generar la lección: {st.session_state.lesson_error}")

    # --- MOSTRAR LECCIÓN + QUIZ ---
    if st.session_state.quiz_data is not None and st.session_state.quiz_result is None:

        quiz_data = st.session_state.quiz_data
        mc_qs     = quiz_data.get("mc",   [])
        fitb_qs   = quiz_data.get("fitb", [])

        lesson_title   = quiz_data.get("title", "Tu Lección de Hoy")
        academic_topic = quiz_data.get("academic_topic", "General English")
        lesson_text    = quiz_data.get("lesson", "")

        st.write("---")
        st.markdown(f"### 📚 {lesson_title}")
        st.markdown(f"**🎯 Enfoque Académico:** {academic_topic}")

        # ── SECCIÓN DE AUDIO (antes de la lección escrita) ───────────────
        st.markdown("<div class='audio-section'>", unsafe_allow_html=True)
        st.markdown(
            "<p>🔊 <b>Escuchar la Lección</b> — Presiona el botón, luego lee el texto "
            "abajo mientras escuchas para practicar pronunciación en inglés.</p>",
            unsafe_allow_html=True
        )

        if not EDGE_TTS_AVAILABLE:
            show_warning("El módulo edge-tts no está instalado. Verifica que `edge-tts` y `nest_asyncio` estén en requirements.txt y reinicia la app.")
        else:
            col_audio, col_spacer = st.columns([1, 2])
            with col_audio:
                if st.button("🔊 Escuchar Lección", use_container_width=True,
                             key="btn_audio_lesson"):
                    with st.spinner("Generando audio..."):
                        audio_result = generate_lesson_audio(lesson_text)
                    if audio_result:
                        st.session_state.lesson_audio = audio_result
                    else:
                        show_warning("No se pudo generar el audio. Intenta de nuevo.")

            if st.session_state.lesson_audio:
                st.audio(st.session_state.lesson_audio, format="audio/mp3", autoplay=False)
                st.caption(
                    "Voz bilingüe: pronuncia el español y el inglés correctamente. "
                    "Sigue el texto escrito abajo mientras escuchas."
                )

        st.markdown("</div>", unsafe_allow_html=True)
        # ─────────────────────────────────────────────────────────────────

        st.markdown(
            f"<div class='lesson-container' style='border-color: {color};'>"
            f"{lesson_text}"
            f"</div>",
            unsafe_allow_html=True
        )

        st.write("")

        # --- QUIZ ---
        attempts_left = MAX_QUIZ_ATTEMPTS - st.session_state.quiz_attempts
        badge_class   = "attempts-badge-danger" if attempts_left <= 1 else "attempts-badge"

        st.markdown(
            f"<div class='quiz-container' style='border-color: {color};'>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"### 🧠 Quiz de Evaluación"
            f"<span class='{badge_class}'>"
            f"{'⚠️ ' if attempts_left <= 1 else ''}"
            f"{attempts_left} intento{'s' if attempts_left != 1 else ''} restante{'s' if attempts_left != 1 else ''}"
            f"</span>",
            unsafe_allow_html=True
        )
        attempt_label = (
            f" (intento #{st.session_state.quiz_attempts + 1} de {MAX_QUIZ_ATTEMPTS})"
            if st.session_state.quiz_attempts > 0 else
            f" (tienes {MAX_QUIZ_ATTEMPTS} intentos)"
        )
        st.caption(
            f"Responde correctamente al menos el {PASSING_SCORE:.0%} para ganar "
            f"{XP_PER_LESSON} XP.{attempt_label}"
        )

        with st.form(key="quiz_form"):

            mc_user_answers   = {}
            fitb_user_answers = {}

            _quiz_section_title("🔤 Parte A — Multiple Choice")

            for i, q in enumerate(mc_qs):
                st.markdown(
                    f"<div class='question-card'>"
                    f"<span class='q-badge'>Pregunta {i+1} de {len(mc_qs)}</span>"
                    f"<p>{q.get('q', '')}</p>",
                    unsafe_allow_html=True
                )
                options_display = ["— Selecciona una respuesta —"] + q.get("options", [])
                choice = st.radio(
                    label=f"Pregunta {i+1}",
                    options=options_display,
                    index=0,
                    label_visibility="collapsed",
                    key=f"mc_radio_{i}"
                )
                mc_user_answers[i] = "" if choice == "— Selecciona una respuesta —" else choice
                st.markdown("</div>", unsafe_allow_html=True)

            _quiz_section_title("✏️ Parte B — Fill in the Blanks")
            st.caption("Escribe UNA sola palabra en inglés para completar la oración.")

            for i, q in enumerate(fitb_qs):
                sentence_display = q.get("sentence", "___").replace("___", "**___**")
                st.markdown(
                    f"<div class='question-card'>"
                    f"<span class='q-badge'>Completar {i+1} de {len(fitb_qs)}</span>"
                    f"<p>{sentence_display}</p>",
                    unsafe_allow_html=True
                )
                fitb_user_answers[i] = st.text_input(
                    label=f"Completar {i+1}",
                    placeholder="Escribe la palabra aquí...",
                    label_visibility="collapsed",
                    key=f"fitb_input_{i}"
                )
                st.markdown("</div>", unsafe_allow_html=True)

            st.write("")
            submitted = st.form_submit_button(
                "📊 Evaluar mi Quiz",
                use_container_width=True,
                type="primary"
            )

        st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            result = evaluate_quiz(mc_qs, fitb_qs, mc_user_answers, fitb_user_answers)
            st.session_state.quiz_result   = result
            st.session_state.quiz_attempts += 1
            st.rerun()

    # --- PANEL DE RESULTADOS ---
    if st.session_state.quiz_result is not None:

        result   = st.session_state.quiz_result
        passed   = result["passed"]
        pct      = result["score_pct"]
        correct  = result["correct"]
        total    = result["total"]
        attempts = st.session_state.quiz_attempts
        attempts_exhausted = attempts >= MAX_QUIZ_ATTEMPTS

        if passed:
            panel_class  = "result-pass"
            emoji_result = "🏆"
            title_text   = "¡Lección Superada!"
            bar_color    = "#28a745"
        elif attempts_exhausted:
            panel_class  = "result-blocked"
            emoji_result = "📖"
            title_text   = f"Límite de {MAX_QUIZ_ATTEMPTS} intentos alcanzado"
            bar_color    = "#dc3545"
        else:
            panel_class  = "result-fail"
            emoji_result = "💪"
            title_text   = "¡Casi! Inténtalo de nuevo"
            bar_color    = "#ffc107"

        st.write("---")
        st.markdown(f"""
            <div class='result-panel {panel_class}'>
                <h2>{emoji_result} {title_text}</h2>
                <div class='score-number'>{pct:.0%}</div>
                <p style='color:#2c3e50 !important; margin:0;'>
                    {correct} de {total} correctas &middot; Intento #{attempts} de {MAX_QUIZ_ATTEMPTS}
                </p>
                <div class='score-bar-wrap'>
                    <div class='score-bar-fill'
                         style='width:{pct*100:.1f}%; background:{bar_color};'></div>
                </div>
                <p style='color:#2c3e50 !important; font-size:0.85rem;'>
                    Mínimo para aprobar: {PASSING_SCORE:.0%}
                </p>
            </div>
        """, unsafe_allow_html=True)

        st.write("")

        with st.expander("🔍 Ver correcciones detalladas", expanded=not passed):

            if result.get("feedback_mc"):
                st.markdown("**Parte A — Multiple Choice**")
                for fb in result["feedback_mc"]:
                    icon = "✅" if fb["is_correct"] else "❌"
                    cls  = "feedback-correct" if fb["is_correct"] else "feedback-wrong"
                    extra = (
                        f"<br>Tu respuesta: <em>{fb['user_answer']}</em> &nbsp;·&nbsp; "
                        f"Correcta: <strong>{fb['correct_answer']}</strong>"
                        if not fb["is_correct"] else ""
                    )
                    st.markdown(
                        f"<div class='feedback-row {cls}'>"
                        f"{icon} <strong>{fb['question']}</strong>{extra}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

            if result.get("feedback_fitb"):
                st.markdown("**Parte B — Fill in the Blanks**")
                for fb in result["feedback_fitb"]:
                    icon = "✅" if fb["is_correct"] else "❌"
                    cls  = "feedback-correct" if fb["is_correct"] else "feedback-wrong"
                    extra = (
                        f"<br>Tu respuesta: <em>{fb['user_answer']}</em> &nbsp;·&nbsp; "
                        f"Correcta: <strong>{fb['correct_answer']}</strong>"
                        if not fb["is_correct"] else ""
                    )
                    st.markdown(
                        f"<div class='feedback-row {cls}'>"
                        f"{icon} {fb['sentence']}{extra}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        st.write("")

        if passed:
            if st.button(
                f"🎉 Completar Lección y ganar {XP_PER_LESSON} XP!",
                use_container_width=True,
                type="primary"
            ):
                st.session_state.xp += XP_PER_LESSON

                saved, save_error = save_xp_to_sheet(user, XP_PER_LESSON, pct, attempts)
                if not saved:
                    show_warning(f"XP guardado localmente, pero no en la nube: {save_error}")

                st.session_state.quiz_data     = None
                st.session_state.quiz_result   = None
                st.session_state.quiz_attempts = 0
                st.session_state.lesson_error  = None
                st.session_state.lesson_audio  = None

                st.balloons()
                st.success(
                    f"¡Increíble, {user}! Obtuviste {pct:.0%} y ganaste +{XP_PER_LESSON} XP. ¡Sigue así!"
                )

        elif attempts_exhausted:
            # Se agotaron los intentos: solo opción de nueva lección
            show_warning(
                f"Usaste los {MAX_QUIZ_ATTEMPTS} intentos disponibles. "
                "¡No te rindas! Prueba con una nueva lección para seguir ganando XP."
            )
            if st.button(
                "📖 Nueva Lección",
                use_container_width=True,
                type="primary"
            ):
                st.session_state.quiz_data     = None
                st.session_state.quiz_result   = None
                st.session_state.quiz_attempts = 0
                st.session_state.lesson_error  = None
                st.session_state.lesson_audio  = None
                st.rerun()

        else:
            # Todavía le quedan intentos
            col_retry, col_new = st.columns(2)

            with col_retry:
                if st.button(
                    "🔄 Volver a intentar el Quiz",
                    use_container_width=True,
                    type="primary"
                ):
                    st.session_state.quiz_result = None
                    st.rerun()

            with col_new:
                if st.button(
                    "📖 Nueva Lección",
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.quiz_data     = None
                    st.session_state.quiz_result   = None
                    st.session_state.quiz_attempts = 0
                    st.session_state.lesson_error  = None
                    st.session_state.lesson_audio  = None
                    st.rerun()

send_weekly_report()
