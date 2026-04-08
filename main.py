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
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    }
    .dashboard-header h2, .dashboard-header h3 {
        margin: 0; position: relative; z-index: 1; color: white !important;
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
       NUEVOS ESTILOS: SISTEMA DE QUIZ
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
        border: 1.5px solid #d0d8f0 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        color: var(--text-dark) !important;
    }
    .stTextInput input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102,126,234,0.15) !important;
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
    }

    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. CONTEXTO FAMILIAR Y PERFILES
# ==========================================
FAMILY_CONTEXT = """
Contexto de la familia de la alumna (Usa esta informacion para crear ejemplos, historias y ejercicios):
- Padres: Juan Carlos y Daniela (Divorciados. Usar "Dad's house" y "Mom's house").
- Pareja del papa: Camila.
- Hermano menor: Amaro (10.5 meses de edad).
- Abuelos maternos: Regina y Jorge Hernan. Abuelos paternos: Silvia y Mario.
- Tios: Carlos, Natalia, Pamela. Primos: Agustin, Maximo, Luciana, Julian.
- Mascotas (7 en total): Gatos (Rosita, Toribio, Blanca, Leon). Perros (Pink - poodle, Alma - doberman, Odin - doberman).
"""

PROFILES = {
    "Antonia": {
        "color": "#8e44ad",
        "gradient": "linear-gradient(135deg, #9b59b6, #6c3483)",
        "emoji": "🎨",
        "hobbies": "Tenis y pintura",
        "tone": "Creativo e inspirador, usa metaforas visuales y de deporte."
    },
    "Belen": {
        "color": "#2980b9",
        "gradient": "linear-gradient(135deg, #3498db, #1a6fa0)",
        "emoji": "🎹",
        "hobbies": "Piano y musica",
        "tone": "Armonioso y ritmico, usa analogias musicales y melodiosas."
    },
    "Sofia": {
        "color": "#d35400",
        "gradient": "linear-gradient(135deg, #e67e22, #a04000)",
        "emoji": "🤸",
        "hobbies": "Gimnasia",
        "tone": "Dinamico, energetico y enfocado en la superacion fisica y el movimiento."
    }
}

# ==========================================
# CONSTANTES DE CONFIGURACION
# ==========================================
GROQ_MODEL_CHAT  = "llama-3.1-8b-instant"
GROQ_MODEL_AUDIO = "whisper-large-v3"
# max_tokens ampliado a 2500: el JSON de leccion+quiz es mayor que texto libre.
# Con 1000 el modelo truncaba el JSON y rompía el parse.
# Ampliado a 4000: la lección extensa (3 secciones con markdown) + 13 preguntas
# superan los 2500 tokens anteriores. 4000 da margen sin acercarse al límite
# del modelo (8192 tokens de contexto de salida en llama-3.1-8b-instant).
GROQ_MAX_TOKENS  = 4000
GROQ_TEMPERATURE = 0.7
XP_PER_LESSON    = 50
PASSING_SCORE    = 0.60        # 60% minimo para aprobar
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

# ------------------------------------------
# 4a. GENERACION DE LECCION + QUIZ (JSON)
# ------------------------------------------
# DISENO: El system_prompt exige JSON puro con 3 campos:
#   "lesson" — texto de la leccion en Spanglish (puede tener markdown)
#   "mc"     — lista de preguntas de multiple choice
#   "fitb"   — lista de preguntas de completar la oracion
#
# Por que JSON y no texto libre:
#   Streamlit necesita iterar sobre objetos Python para crear st.radio
#   y st.text_input dinamicamente. Texto libre requiere parsers fragiles.
#   Con JSON + response_format={"type":"json_object"} el modelo emite
#   JSON valido sin preambulo ni bloques de codigo.
#
# Por que response_format={"type":"json_object"}:
#   Groq soporta "JSON mode" que elimina el 99% de los errores de parse
#   al forzar al modelo a producir exclusivamente JSON bien formado.

def _build_system_prompt_json(profile_name: str) -> str:
    """System prompt que instruye al LLM a responder SOLO con JSON valido."""
    profile = PROFILES[profile_name]
    return f"""
Eres un tutor de ingles experto y motivador para {profile_name}, una nina de 13 anios.
A ella le apasiona: {profile['hobbies']}.
Tu tono debe ser: {profile['tone']}.

{FAMILY_CONTEXT}

INSTRUCCION CRITICA:
Debes responder UNICAMENTE con un objeto JSON valido. Sin texto antes ni despues. Sin bloques de codigo markdown.

El JSON debe tener EXACTAMENTE esta estructura:
{{
  "lesson": "<leccion en Spanglish con emojis y vinetas markdown, integrando familia/mascotas>",
  "mc": [
    {{
      "q": "<pregunta en ingles>",
      "options": ["<opcion A>", "<opcion B>", "<opcion C>", "<opcion D>"],
      "answer": "<texto exacto de la opcion correcta>"
    }}
  ],
  "fitb": [
    {{
      "sentence": "<oracion con un ___ donde va la palabra>",
      "answer": "<palabra correcta en minusculas sin tildes>"
    }}
  ]
}}

REGLAS:
- "lesson": leccion corta y gamificada, maximo 200 palabras. Usa guiones para las vinetas. Integra 1-2 familiares o mascotas.
- "mc": entre 5 y 8 preguntas de multiple choice basadas en el contenido de la leccion. Siempre 4 opciones por pregunta.
- "fitb": exactamente 5 preguntas de completar la oracion. El campo "answer" es UNA sola palabra en minusculas sin tildes.
- Todo el contenido de preguntas y opciones en ingles. Las explicaciones dentro de "lesson" en Spanglish.
"""


def generate_lesson_and_quiz(profile_name: str, topic: str, custom_text: str | None = None):
    """
    Llama a Groq con JSON mode. Retorna (parsed_dict, error_string).
    parsed_dict tiene las claves: 'lesson', 'mc', 'fitb'.
    """
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    system_prompt = _build_system_prompt_json(profile_name)
    user_prompt   = f"El tema de la leccion de hoy es: {topic}."
    if custom_text:
        user_prompt += f" Contexto adicional de la alumna: '{custom_text}'. Adapta leccion y quiz a este tema."

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=GROQ_TEMPERATURE,
            max_tokens=GROQ_MAX_TOKENS,
            response_format={"type": "json_object"},   # JSON mode de Groq
        )
        raw = response.choices[0].message.content

        # Parse defensivo: elimina posibles backticks residuales
        raw_clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw_clean)

        # Validacion minima de estructura
        if not all(k in data for k in ("lesson", "mc", "fitb")):
            raise ValueError(f"JSON incompleto. Claves recibidas: {list(data.keys())}")
        if not isinstance(data["mc"],   list) or len(data["mc"])   < 1:
            raise ValueError("El campo 'mc' esta vacio o no es una lista.")
        if not isinstance(data["fitb"], list) or len(data["fitb"]) < 1:
            raise ValueError("El campo 'fitb' esta vacio o no es una lista.")

        return data, None

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}. Raw (primeros 300 chars): {raw[:300]}")
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


# ------------------------------------------
# 4b. TRANSCRIPCION DE AUDIO
# ------------------------------------------
def transcribe_audio(audio_bytes: bytes):
    """Transcribe audio con Groq Whisper. Retorna (text, error)."""
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


# ------------------------------------------
# 4c. GUARDADO EN GOOGLE SHEETS (ACTUALIZADO)
# ------------------------------------------
# CAMBIO RESPECTO A VERSION ANTERIOR:
# Se agregan los parametros score_pct y attempts para registrar el
# desempeno en el quiz. Ver instrucciones de columnas al final del archivo.
def save_xp_to_sheet(profile_name: str, xp_gained: int, score_pct: float, attempts: int):
    """
    Registra una sesion completada en Google Sheets.
    Columnas: timestamp | profile | xp | score_pct | attempts
    """
    sheet, db_error = get_db_connection()
    if db_error or not sheet:
        logger.warning(f"No se pudo guardar XP: {db_error}")
        return False, db_error
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        score_str = f"{score_pct:.1%}"   # ej: "75.0%"
        sheet.append_row([timestamp, profile_name, xp_gained, score_str, attempts])
        return True, None
    except Exception as e:
        logger.error(f"Error guardando en Sheets: {e}")
        return False, f"Error de Google Sheets: {e}"


# ------------------------------------------
# 4d. LOGICA DE EVALUACION DEL QUIZ
# ------------------------------------------
def evaluate_quiz(mc_questions: list, fitb_questions: list,
                  mc_answers: dict, fitb_answers: dict) -> dict:
    """
    Evalua respuestas del usuario contra las correctas.
    Retorna: {score_pct, passed, correct, total, feedback_mc, feedback_fitb}
    """
    correct       = 0
    total         = len(mc_questions) + len(fitb_questions)
    feedback_mc   = []
    feedback_fitb = []

    # Multiple choice: comparacion exacta de strings
    for i, q in enumerate(mc_questions):
        user_ans    = mc_answers.get(i, "")
        correct_ans = q.get("answer", "")
        is_correct  = (user_ans.strip() == correct_ans.strip())
        if is_correct:
            correct += 1
        feedback_mc.append({
            "question":      q.get("q", ""),
            "user_answer":   user_ans or "(sin respuesta)",
            "correct_answer": correct_ans,
            "is_correct":    is_correct,
        })

    # Fill in the blanks: case-insensitive, sin espacios extra
    for i, q in enumerate(fitb_questions):
        user_ans    = fitb_answers.get(i, "").strip().lower()
        correct_ans = q.get("answer", "").strip().lower()
        is_correct  = (user_ans == correct_ans)
        if is_correct:
            correct += 1
        feedback_fitb.append({
            "sentence":      q.get("sentence", ""),
            "user_answer":   fitb_answers.get(i, "") or "(sin respuesta)",
            "correct_answer": q.get("answer", ""),
            "is_correct":    is_correct,
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


# ------------------------------------------
# 4e. REPORTE SEMANAL
# ------------------------------------------
def send_weekly_report():
    """Envia el reporte semanal por email los viernes."""
    if datetime.datetime.now().weekday() != 4:
        return
    try:
        sender   = st.secrets["email_sender"]
        password = st.secrets["email_password"]

        sheet, _ = get_db_connection()
        report_lines = []
        if sheet:
            rows = sheet.get_all_records()
            summary = {}
            for row in rows:
                name  = row.get("profile", "")
                xp    = int(row.get("xp", 0))
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
                    f"- {name}: {s['xp']} XP | {s['sessions']} lecciones | Promedio quiz: {avg:.0%}"
                )

        if not report_lines:
            report_lines = ["(No hubo registro de actividad esta semana)"]

        body = (
            "Hola Juan Carlos!\n\n"
            "Este es el progreso de las trillizas esta semana:\n"
            + "\n".join(report_lines)
            + "\n\nVan excelente! - IdiomaConnect"
        )
        msg = MIMEMultipart()
        msg['From']    = sender
        msg['To']      = REPORT_EMAIL_TO
        msg['Subject'] = "Reporte Semanal Idiomaconnect"
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, REPORT_EMAIL_TO, msg.as_string())
        logger.info("Reporte semanal enviado.")
    except Exception as e:
        logger.error(f"Error en reporte semanal: {e}")


# ==========================================
# FUNCIONES AUXILIARES DE UI
# ==========================================
def show_error(message: str):
    st.markdown(f"<div class='error-banner'>⚠️ {message}</div>", unsafe_allow_html=True)

def show_warning(message: str):
    st.markdown(f"<div class='warning-banner'>ℹ️ {message}</div>", unsafe_allow_html=True)

def _quiz_section_title(text: str):
    st.markdown(f"<p class='quiz-section-title'>{text}</p>", unsafe_allow_html=True)

def _question_badge(label: str):
    st.markdown(f"<span class='q-badge'>{label}</span>", unsafe_allow_html=True)


# ==========================================
# 5. MANEJO DE ESTADO (Session State)
# ==========================================
# NUEVAS CLAVES vs version anterior:
#   quiz_data     — dict parseado de la IA {lesson, mc, fitb} (reemplaza lesson_content)
#   quiz_result   — dict resultado de evaluate_quiz() | None si no se ha evaluado
#   quiz_attempts — int: numero de intentos en el quiz actual (para Sheets y UX)
_STATE_DEFAULTS = {
    "current_user":    None,
    "xp":              0,
    "quiz_data":       None,
    "lesson_error":    None,
    "lesson_pending":  False,
    "quiz_result":     None,   # NUEVO
    "quiz_attempts":   0,      # NUEVO
    "last_text_input": "",
}
for key, default in _STATE_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ==========================================
# 6. INTERFAZ DE USUARIO
# ==========================================

# ── PANTALLA DE LOGIN ──
if st.session_state.current_user is None:
    st.markdown("""
        <div class='welcome-container'>
            <h1>✨ IdiomaConnect</h1>
            <p>¿Quien esta lista para aprender ingles hoy?</p>
        </div>
    """, unsafe_allow_html=True)

    cols = st.columns(3)
    for i, (name, pdata) in enumerate(PROFILES.items()):
        with cols[i]:
            st.markdown(f"""
                <div class='profile-card' style='background: {pdata["gradient"]};'>
                    <span class='emoji-avatar'>{pdata["emoji"]}</span>
                    <h2>{name}</h2>
                    <p>{pdata["hobbies"]}</p>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"Soy {name}!", key=f"btn_{name}", use_container_width=True):
                for k, v in _STATE_DEFAULTS.items():
                    st.session_state[k] = v
                st.session_state.current_user = name
                st.rerun()

# ── PANTALLA PRINCIPAL (DASHBOARD) ──
else:
    user  = st.session_state.current_user
    pdata = PROFILES[user]
    color = pdata["color"]

    # Encabezado personalizado
    st.markdown(f"""
        <div class='dashboard-header' style='background: {pdata["gradient"]};'>
            <h2>Hola, {pdata["emoji"]} {user}!</h2>
            <h3>⭐ {st.session_state.xp} XP</h3>
        </div>
    """, unsafe_allow_html=True)

    if st.button("← Cambiar alumna", type="secondary"):
        for k, v in _STATE_DEFAULTS.items():
            st.session_state[k] = v
        st.rerun()

    st.write("---")
    st.markdown(f"<h3 class='section-title'>¿Que quieres aprender hoy, {user}?</h3>",
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗺️ Que la IA me guie", use_container_width=True):
            st.session_state.lesson_pending = True
            st.session_state.lesson_topic   = "Aventura Diaria (Vocabulario general y gramatica divertida)"
            st.session_state.lesson_text    = None
            st.session_state.quiz_data      = None
            st.session_state.quiz_result    = None
            st.session_state.quiz_attempts  = 0
            st.session_state.lesson_error   = None

    with col2:
        st.markdown("<p class='help-text'>🙋 <b>Tema Escolar / Personalizado</b></p>",
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
                st.success(f"Te escuche decir: *'{text}'*")
                st.session_state.lesson_pending = True
                st.session_state.lesson_topic   = "Tema del Colegio"
                st.session_state.lesson_text    = text
                st.session_state.quiz_data      = None
                st.session_state.quiz_result    = None
                st.session_state.quiz_attempts  = 0
                st.session_state.lesson_error   = None

        text_input = st.chat_input(f"¿Que estas aprendiendo en clase, {user}?")
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

    # ── BLOQUE DE GENERACION (separado de botones para evitar bucles) ──
    # Flag pattern: el clic activa lesson_pending=True, la generacion ocurre aqui,
    # fuera del bloque del boton, garantizando estabilidad entre reruns.
    if st.session_state.lesson_pending:
        topic       = st.session_state.get("lesson_topic", "Aventura Diaria")
        custom_text = st.session_state.get("lesson_text", None)

        with st.spinner("✨ Preparando tu leccion y quiz con Llama 3.1... (~10 segundos)"):
            data_parsed, error = generate_lesson_and_quiz(user, topic, custom_text)

        st.session_state.quiz_data      = data_parsed
        st.session_state.lesson_error   = error
        st.session_state.lesson_pending = False
        st.session_state.lesson_text    = None

    # ── MOSTRAR ERROR ──
    if st.session_state.lesson_error:
        show_error(f"Error al generar la leccion: {st.session_state.lesson_error}")

    # ══════════════════════════════════════════════════════════════════
    # BLOQUE LECCION + QUIZ
    # Visible cuando: hay datos parseados Y el quiz NO ha sido evaluado
    # (quiz_result is None). Una vez evaluado, este bloque desaparece
    # y se muestra el panel de resultados.
    # ══════════════════════════════════════════════════════════════════
    if st.session_state.quiz_data is not None and st.session_state.quiz_result is None:

        quiz_data = st.session_state.quiz_data
        mc_qs     = quiz_data.get("mc",   [])
        fitb_qs   = quiz_data.get("fitb", [])

        # ── 6a. LECCION ──
        st.write("---")
        st.markdown("### 📚 Tu Leccion de Hoy")
        st.markdown(
            f"<div class='lesson-container' style='border-color: {color};'>"
            f"{quiz_data.get('lesson', '')}"
            f"</div>",
            unsafe_allow_html=True
        )

        st.write("")

        # ── 6b. QUIZ dentro de st.form ──
        # Por que st.form aqui:
        # Sin form, cada interaccion con st.radio o st.text_input dispara
        # un rerun completo. Con 13 preguntas, eso genera latencia visible
        # y puede resetear estados inesperadamente.
        # st.form agrupa todos los widgets y ejecuta UN SOLO rerun
        # al presionar submit, dandole a la alumna una experiencia fluida.
        st.markdown(
            f"<div class='quiz-container' style='border-color: {color};'>",
            unsafe_allow_html=True
        )
        st.markdown("### 🧠 Quiz de Evaluacion")
        attempt_label = (
            f" (intento #{st.session_state.quiz_attempts + 1})"
            if st.session_state.quiz_attempts > 0 else ""
        )
        st.caption(
            f"Responde correctamente al menos el {PASSING_SCORE:.0%} para ganar "
            f"{XP_PER_LESSON} XP.{attempt_label}"
        )

        with st.form(key="quiz_form"):

            mc_user_answers   = {}
            fitb_user_answers = {}

            # ── Parte A: Multiple Choice ──
            _quiz_section_title("🔤 Parte A — Multiple Choice")

            for i, q in enumerate(mc_qs):
                st.markdown(
                    f"<div class='question-card'>"
                    f"<span class='q-badge'>Pregunta {i+1} de {len(mc_qs)}</span>"
                    f"<p>{q.get('q', '')}</p>",
                    unsafe_allow_html=True
                )
                # Placeholder al inicio fuerza una seleccion consciente
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

            # ── Parte B: Fill in the Blanks ──
            _quiz_section_title("✏️ Parte B — Fill in the Blanks")
            st.caption("Escribe UNA sola palabra en ingles para completar la oracion.")

            for i, q in enumerate(fitb_qs):
                # Resaltar el hueco visualmente
                sentence_display = q.get("sentence", "___").replace("___", "**___**")
                st.markdown(
                    f"<div class='question-card'>"
                    f"<span class='q-badge'>Completar {i+1} de {len(fitb_qs)}</span>"
                    f"<p>{sentence_display}</p>",
                    unsafe_allow_html=True
                )
                fitb_user_answers[i] = st.text_input(
                    label=f"Completar {i+1}",
                    placeholder="Escribe la palabra aqui...",
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

        st.markdown("</div>", unsafe_allow_html=True)  # cierre quiz-container

        # ── 6c. PROCESAR ENVIO ──
        # Este bloque ejecuta en el mismo rerun del submit.
        # Al guardar quiz_result (dict), en el proximo rerun este bloque
        # ya no se muestra (condicion `quiz_result is None` falla).
        # No hay bucle posible.
        if submitted:
            result = evaluate_quiz(mc_qs, fitb_qs, mc_user_answers, fitb_user_answers)
            st.session_state.quiz_result   = result
            st.session_state.quiz_attempts += 1
            st.rerun()


    # ══════════════════════════════════════════════════════════════════
    # BLOQUE DE RESULTADOS
    # Visible cuando quiz_result no es None (ya fue evaluado)
    # ══════════════════════════════════════════════════════════════════
    if st.session_state.quiz_result is not None:

        result   = st.session_state.quiz_result
        passed   = result["passed"]
        pct      = result["score_pct"]
        correct  = result["correct"]
        total    = result["total"]
        attempts = st.session_state.quiz_attempts

        panel_class  = "result-pass" if passed else "result-fail"
        emoji_result = "🏆" if passed else "💪"
        title_text   = "Leccion Superada!" if passed else "Casi! Intentalo de nuevo"
        bar_color    = "#28a745" if passed else "#ffc107"

        st.write("---")
        st.markdown(f"""
            <div class='result-panel {panel_class}'>
                <h2>{emoji_result} {title_text}</h2>
                <div class='score-number'>{pct:.0%}</div>
                <p style='color:#2c3e50 !important; margin:0;'>
                    {correct} de {total} correctas &middot; Intento #{attempts}
                </p>
                <div class='score-bar-wrap'>
                    <div class='score-bar-fill'
                         style='width:{pct*100:.1f}%; background:{bar_color};'></div>
                </div>
                <p style='color:#2c3e50 !important; font-size:0.85rem;'>
                    Minimo para aprobar: {PASSING_SCORE:.0%}
                </p>
            </div>
        """, unsafe_allow_html=True)

        st.write("")

        # ── Feedback detallado (colapsable, expandido si fallo) ──
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

        # ── Botones de accion post-resultado ──
        if passed:
            # APROBO: boton para cerrar la leccion y acreditar XP
            if st.button(
                f"🎉 Completar Leccion y ganar {XP_PER_LESSON} XP!",
                use_container_width=True,
                type="primary"
            ):
                st.session_state.xp += XP_PER_LESSON

                saved, save_error = save_xp_to_sheet(
                    user, XP_PER_LESSON, pct, attempts
                )
                if not saved:
                    show_warning(f"XP guardado localmente, pero no en la nube: {save_error}")

                # Reset para invitar a una nueva leccion
                st.session_state.quiz_data     = None
                st.session_state.quiz_result   = None
                st.session_state.quiz_attempts = 0
                st.session_state.lesson_error  = None

                st.balloons()
                st.success(
                    f"Increible, {user}! Obtuviste {pct:.0%} y ganaste +{XP_PER_LESSON} XP. Sigue asi!"
                )

        else:
            # FALLO: dos opciones
            # "Reintentar" reutiliza el mismo quiz (no gasta requests a Groq)
            # "Nueva Leccion" genera contenido fresco
            col_retry, col_new = st.columns(2)

            with col_retry:
                if st.button(
                    "🔄 Volver a intentar el Quiz",
                    use_container_width=True,
                    type="primary"
                ):
                    # Solo resetea el resultado; quiz_data se mantiene intacto.
                    # En el proximo rerun se muestra el formulario de nuevo.
                    st.session_state.quiz_result = None
                    st.rerun()

            with col_new:
                if st.button(
                    "📖 Nueva Leccion",
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.quiz_data     = None
                    st.session_state.quiz_result   = None
                    st.session_state.quiz_attempts = 0
                    st.session_state.lesson_error  = None
                    st.rerun()


# ── DISPARADOR SILENCIOSO DEL REPORTE SEMANAL ──
send_weekly_report()


# ══════════════════════════════════════════════════════════════════════════
# INSTRUCCIONES PARA GOOGLE SHEETS — NUEVAS COLUMNAS
# ══════════════════════════════════════════════════════════════════════════
#
# Tu hoja "Idiomaconnect_DB" (sheet1) necesita exactamente estos 5 headers
# en la primera fila (A1:E1):
#
#   A            B          C     D            E
#   timestamp  | profile  | xp | score_pct | attempts
#
#   timestamp  — Fecha y hora. Ej: "2025-07-11 14:32:05"
#   profile    — Nombre. Valores: Antonia, Belen, Sofia
#   xp         — XP ganados. Siempre 50 si la leccion fue aprobada.
#   score_pct  — Porcentaje de aciertos. Ej: "75.0%"  (texto)
#   attempts   — Numero de intentos para aprobar. Minimo 1.
#
# Si ya tienes filas con el formato anterior (3 columnas):
#   1. Agrega "score_pct" en D1  y  "attempts" en E1.
#   2. Las filas antiguas quedaran con D y E en blanco. No rompe nada.
#      El reporte semanal trata valores vacios como 0 correctamente.
#
# Si la hoja esta vacia:
#   1. Escribe los 5 headers en A1:E1.
#   2. Asegurate de que la cuenta de servicio tiene permiso de Editor.
#
# ══════════════════════════════════════════════════════════════════════════
