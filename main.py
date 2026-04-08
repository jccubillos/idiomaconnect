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
import time
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

# MEJORA VISIBILIDAD (Bug #1): CSS profundamente renovado para legibilidad total.
# Ahora aseguramos que el texto general sea oscuro y legible sobre el degradado claro,
# manteniendo el texto blanco SOLO dentro de las tarjetas personalizadas.
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
        
        /* COLORES GLOBALES DE TEXTO LEGIBLE (Sobre fondo claro) */
        --text-dark: #2c3e50;
        --text-subtle: #6b7280;
    }

    /* Aplicar tipografía y color oscuro por defecto a TODA la app */
    html, body, [class*="css"], .stMarkdown, p, li, label, h3 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: var(--text-dark) !important;
    }
    
    /* Asegurar que los títulos principales tengan peso */
    h1, h2 { 
        font-family: 'Nunito', sans-serif !important;
        font-weight: 800 !important;
        color: var(--text-dark) !important;
    }

    /* --- FONDO GENERAL CON TEXTURA SUTIL --- */
    .stApp {
        background: linear-gradient(135deg, #f0f4ff 0%, #faf0ff 50%, #f0fff8 100%);
        background-attachment: fixed;
    }

    /* --- BOTONES: Pilula moderna con efecto de elevación --- */
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
    /* Estilo secundario (Cerrar Sesión) */
    .stButton > button[kind="secondary"] {
        color: var(--text-dark) !important;
        background-color: white !important;
    }

    /* --- TARJETA DE PERFIL (Mantenemos texto blanco aquí) --- */
    .profile-card {
        padding: 28px 20px;
        border-radius: var(--radius-lg);
        text-align: center;
        /* Forzamos texto blanco dentro de la tarjeta */
        color: white !important;
        margin-bottom: 16px;
        box-shadow: var(--shadow-lift);
        position: relative;
        overflow: hidden;
        animation: cardReveal 0.5s ease both;
        border: 1px solid rgba(255,255,255,0.35);
        backdrop-filter: blur(4px);
    }
    .profile-card h2 {
        margin: 0 0 6px 0;
        font-size: 1.6rem;
        font-weight: 800;
        text-shadow: 0 2px 8px rgba(0,0,0,0.15);
        /* Forzamos texto blanco aquí también */
        color: white !important; 
    }
    .profile-card p {
        margin: 0;
        font-size: 0.9rem;
        opacity: 0.9;
        /* Forzamos texto blanco aquí también */
        color: white !important; 
    }
    .profile-card .emoji-avatar {
        font-size: 2.8rem;
        margin-bottom: 10px;
        display: block;
    }

    /* --- TARJETA PRINCIPAL DEL DASHBOARD (Mantenemos texto blanco aquí) --- */
    .dashboard-header {
        padding: 20px 24px;
        border-radius: var(--radius-md);
        /* Forzamos texto blanco dentro del header */
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
        margin: 0;
        position: relative; z-index: 1;
        /* Forzamos texto blanco aquí también */
        color: white !important; 
    }

    /* --- CONTENEDOR DE LECCIÓN --- */
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
    /* Asegurar legibilidad del texto de la lección */
    .lesson-container, .lesson-container p, .lesson-container li {
        color: var(--text-dark) !important;
    }

    /* --- CONTENEDOR DE BIENVENIDA --- */
    .welcome-container {
        text-align: center;
        padding: 40px 20px 20px;
        animation: fadeIn 0.6s ease both;
    }
    .welcome-container h1 {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 8px;
        /* Forzamos color degradado en webkit */
        color: transparent !important; 
    }
    .welcome-container p {
        font-size: 1.1rem;
        color: var(--text-subtle) !important;
        margin-bottom: 32px;
    }
    
    /* --- ETIQUETAS Y TEXTOS DE AYUDA (Bug #1) --- */
    .help-text, .section-title {
        color: var(--text-dark) !important;
        font-weight: 600;
    }
    .dashboard-section p {
        color: var(--text-dark) !important;
    }

    /* --- BANNER DE ERROR Y ADVERTENCIA --- */
    .error-banner {
        background: #fff3f3;
        border: 1px solid #ffb3b3;
        border-left: 4px solid #e74c3c;
        border-radius: var(--radius-sm);
        padding: 14px 18px;
        margin: 12px 0;
        color: #c0392b !important;
        font-size: 0.9rem;
    }
    .warning-banner {
        background: #fffbf0;
        border: 1px solid #ffd591;
        border-left: 4px solid #f39c12;
        border-radius: var(--radius-sm);
        padding: 14px 18px;
        margin: 12px 0;
        color: #856404 !important;
        font-size: 0.9rem;
    }

    /* --- RESPONSIVE: Mobile --- */
    @media (max-width: 640px) {
        .welcome-container h1 { font-size: 2rem; }
        .dashboard-header { flex-direction: column; gap: 8px; text-align: center; }
    }

    /* --- OCULTAR ELEMENTOS INTERNOS DE STREAMLIT --- */
    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. CONTEXTO FAMILIAR Y PERFILES
# ==========================================
FAMILY_CONTEXT = """
Contexto de la familia de la alumna (Usa esta información para crear ejemplos, historias y ejercicios):
- Padres: Juan Carlos y Daniela (Divorciados. Usar "Dad's house" y "Mom's house").
- Pareja del papá: Camila.
- Hermano menor: Amaro (10.5 meses de edad).
- Abuelos maternos: Regina y Jorge Hernán. Abuelos paternos: Silvia y Mario.
- Tíos: Carlos, Natalia, Pamela. Primos: Agustín, Máximo, Luciana, Julián.
- Mascotas (7 en total): Gatos (Rosita, Toribio, Blanca, León). Perros (Pink - poodle, Alma - doberman, Odin - doberman).
"""

PROFILES = {
    "Antonia": {
        "color": "#8e44ad",
        "gradient": "linear-gradient(135deg, #9b59b6, #6c3483)",
        "emoji": "🎨",
        "hobbies": "Tenis y pintura",
        "tone": "Creativo e inspirador, usa metáforas visuales y de deporte."
    },
    "Belén": {
        "color": "#2980b9",
        "gradient": "linear-gradient(135deg, #3498db, #1a6fa0)",
        "emoji": "🎹",
        "hobbies": "Piano y música",
        "tone": "Armonioso y rítmico, usa analogías musicales y melodiosas."
    },
    "Sofía": {
        "color": "#d35400",
        "gradient": "linear-gradient(135deg, #e67e22, #a04000)",
        "emoji": "🤸",
        "hobbies": "Gimnasia",
        "tone": "Dinámico, energético y enfocado en la superación física y el movimiento."
    }
}

# ==========================================
# CONSTANTES DE CONFIGURACIÓN
# ==========================================
# SOLUCIÓN BUG #2: Actualización de modelo Llama 3 decommissioned a Llama 3.1
GROQ_MODEL_CHAT  = "llama-3.1-8b-instant" 
GROQ_MODEL_AUDIO = "whisper-large-v3"
GROQ_MAX_TOKENS  = 1000
GROQ_TEMPERATURE = 0.7
XP_PER_LESSON    = 50
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
    """Inicializa el cliente Groq con manejo robusto de secretos."""
    try:
        key = st.secrets["GROQ_API_KEY"]
        if not key or key.strip() == "":
            return None, "GROQ_API_KEY está vacía en secrets.toml."
        client = Groq(api_key=key)
        return client, None
    except KeyError:
        return None, "Falta `GROQ_API_KEY` en `.streamlit/secrets.toml`."
    except Exception as e:
        logger.error(f"Error al inicializar Groq: {e}")
        return None, f"Error inesperado al conectar con Groq: {e}"


@st.cache_resource(show_spinner=False)
def get_db_connection():
    """Retorna conexión a Google Sheets con manejo granular de errores."""
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
def _build_system_prompt(profile_name: str) -> str:
    """Construye el system prompt para el LLM."""
    profile = PROFILES[profile_name]
    return f"""
    Eres un tutor de inglés experto, cariñoso y motivador, diseñado exclusivamente para {profile_name}, una niña de 13 años (nacida el 24/Sept/2012).
    A ella le apasiona: {profile['hobbies']}.
    Tu tono debe ser: {profile['tone']}.

    {FAMILY_CONTEXT}

    INSTRUCCIONES:
    - Crea una lección corta, interactiva y gamificada.
    - Integra al menos 1 o 2 miembros de su familia o mascotas en los ejemplos en inglés.
    - Incluye un pequeño desafío o pregunta al final para que gane XP.
    - Mantén el formato limpio, usando viñetas y emojis. Escribe en Spanglish (explicaciones en español, vocabulario en inglés).
    """


def generate_lesson(profile_name: str, topic: str, custom_text: str | None = None):
    """Genera una lección personalizada usando Groq Llama 3.1."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    system_prompt = _build_system_prompt(profile_name)
    user_prompt = f"El tema de hoy es: {topic}."
    if custom_text:
        user_prompt += f" La alumna ha proporcionado este texto de contexto (por voz o escrito): '{custom_text}'. Adapta la lección estrictamente a esto."

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            model=GROQ_MODEL_CHAT, # Usamos Llama 3.1 corregido
            temperature=GROQ_TEMPERATURE,
            max_tokens=GROQ_MAX_TOKENS,
        )
        return response.choices[0].message.content, None

    except Exception as e:
        err_str = str(e).lower()
        if "rate_limit" in err_str or "429" in err_str:
            logger.warning(f"Groq rate limit: {e}")
            return None, "Se alcanzó el límite de la API de Groq. Espera un momento.⏳"
        elif "timeout" in err_str or "connection" in err_str:
            logger.error(f"Groq connection error: {e}")
            return None, "Error de conexión con Groq. Verifica tu internet. 🌐"
        else:
            logger.error(f"Groq error inesperado: {e}")
            # Devolvemos el error detallado para diagnosticar si persiste
            return None, f"Error detallado de la API: {e}"


def transcribe_audio(audio_bytes: bytes):
    """Transcribe audio usando Groq Whisper."""
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
        logger.error(f"Error transcripción Whisper: {e}")
        return None, f"No se pudo transcribir el audio: {e}"
    finally:
        if os.path.exists(TEMP_AUDIO_FILE):
            os.remove(TEMP_AUDIO_FILE)


def save_xp_to_sheet(profile_name: str, xp_gained: int):
    """Añade una fila de registro de XP a Google Sheets."""
    sheet, db_error = get_db_connection()
    if db_error or not sheet:
        logger.warning(f"No se pudo guardar XP: {db_error}")
        return False, db_error

    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, profile_name, xp_gained])
        return True, None
    except Exception as e:
        logger.error(f"Error guardando XP: {e}")
        return False, f"Error de Google Sheets: {e}"


def send_weekly_report():
    """Envía el reporte semanal por email los viernes."""
    if datetime.datetime.now().weekday() != 4:  # 4 = Viernes
        return

    try:
        sender   = st.secrets["email_sender"]
        password = st.secrets["email_password"]

        sheet, _ = get_db_connection()
        report_lines = []
        if sheet:
            rows = sheet.get_all_records()
            xp_totals = {}
            for row in rows:
                name = row.get("profile", "")
                xp   = int(row.get("xp", 0))
                xp_totals[name] = xp_totals.get(name, 0) + xp
            for name, total in xp_totals.items():
                report_lines.append(f"- {name}: {total} XP ganados esta semana.")

        if not report_lines:
            report_lines = ["(No hubo registro de XP esta semana)"]

        body = (
            "¡Hola Juan Carlos!\n\n"
            "Este es el progreso de las trillizas esta semana:\n"
            + "\n".join(report_lines)
            + "\n\n¡Van excelente! 🚀"
        )

        msg = MIMEMultipart()
        msg['From']    = sender
        msg['To']      = REPORT_EMAIL_TO
        msg['Subject'] = "Reporte Semanal Idiomaconnect 🚀"
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, REPORT_EMAIL_TO, msg.as_string())
        logger.info("Reporte semanal enviado correctamente.")
    except Exception as e:
        logger.error(f"Error en reporte semanal: {e}")


# ==========================================
# FUNCIONES AUXILIARES DE UI
# ==========================================
def show_error(message: str):
    st.markdown(f"<div class='error-banner'>⚠️ {message}</div>", unsafe_allow_html=True)

def show_warning(message: str):
    st.markdown(f"<div class='warning-banner'>ℹ️ {message}</div>", unsafe_allow_html=True)


# ==========================================
# 5. MANEJO DE ESTADO (Session State)
# ==========================================
_STATE_DEFAULTS = {
    "current_user":   None,
    "xp":             0,
    "lesson_content": None,
    "lesson_error":   None,
    "lesson_pending": False,
    # Estado anti-bucle de chat_input
    "last_text_input": "", 
}
for key, default in _STATE_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ==========================================
# 6. INTERFAZ DE USUARIO (FLUJO)
# ==========================================

# --- PANTALLA DE LOGIN / SELECCIÓN DE PERFIL ---
if st.session_state.current_user is None:
    st.markdown("""
        <div class='welcome-container'>
            <h1>✨ IdiomaConnect</h1>
            <p>¿Quién está lista para aprender inglés hoy?</p>
        </div>
    """, unsafe_allow_html=True)

    cols = st.columns(3)
    for i, (name, data) in enumerate(PROFILES.items()):
        with cols[i]:
            st.markdown(f"""
                <div class='profile-card' style='background: {data["gradient"]};'>
                    <span class='emoji-avatar'>{data["emoji"]}</span>
                    <h2>{name}</h2>
                    <p>{data["hobbies"]}</p>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"¡Soy {name}!", key=f"btn_{name}", use_container_width=True):
                st.session_state.current_user = name
                # Resetear datos de sesión anterior
                st.session_state.xp             = 0
                st.session_state.lesson_content = None
                st.session_state.lesson_error   = None
                st.session_state.lesson_pending = False
                st.rerun()

# --- PANTALLA PRINCIPAL (DASHBOARD) ---
else:
    user  = st.session_state.current_user
    data  = PROFILES[user]
    color = data["color"]

    # Encabezado personalizado
    st.markdown(f"""
        <div class='dashboard-header' style='background: {data["gradient"]};'>
            <h2>¡Hola, {data["emoji"]} {user}!</h2>
            <h3>⭐ {st.session_state.xp} XP</h3>
        </div>
    """, unsafe_allow_html=True)

    if st.button("← Cambiar alumna", type="secondary"):
        for key, default in _STATE_DEFAULTS.items():
            st.session_state[key] = default
        st.rerun()

    st.write("---")
    
    # Bug #1 Fix: Asegurar que el título sea legible (oscuro)
    st.markdown(f"<h3 class='section-title'>¿Qué quieres aprender hoy, {user}?</h3>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # --- Columna 1: IA me guía ---
    with col1:
        if st.button("🗺️ Que la IA me guíe", use_container_width=True):
            st.session_state.lesson_pending = True
            st.session_state.lesson_topic   = "Aventura Diaria (Vocabulario general y gramática divertida)"
            st.session_state.lesson_text    = None # Limpiar texto personalizado
            st.session_state.lesson_content = None
            st.session_state.lesson_error   = None

    # --- Columna 2: Tema de voz / Texto (Accesibilidad #3) ---
    with col2:
        # Bug #1 Fix: Texto descriptivo legible
        st.markdown("<p class='help-text'>🙋‍♀️ <b>Tema Escolar / Personalizado</b></p>", unsafe_allow_html=True)
        st.markdown("<p class='dashboard-section' style='margin-bottom: 5px; font-size: 0.9rem;'>Grabemos tu voz (microphone) o escribe tu tema aquí abajo:</p>", unsafe_allow_html=True)
        
        # Opción A: Grabadora de Voz
        audio_bytes = audio_recorder(
            text="Clic para hablar", recording_color="#e74c3c", neutral_color=color, icon_size="2x"
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
                st.session_state.lesson_text    = text # Guardar transcripción
                st.session_state.lesson_content = None
                st.session_state.lesson_error   = None

        # Opción B: Entrada de Texto (NUEVO REQUERIMIENTO #3)
        # Usamos chat_input para una UI moderna que encaja en Google Stitch
        # pero la contenemos visualmente en esta columna.
        text_input = st.chat_input(f"¿Qué estás aprendiendo en clase, {user}?")
        
        # Lógica para chat_input (manejo anti-bucle)
        if text_input and text_input != st.session_state.last_text_input and not st.session_state.lesson_pending:
            st.session_state.last_text_input = text_input # Actualizar flag
            
            st.session_state.lesson_pending = True
            st.session_state.lesson_topic   = "Tema del Colegio"
            st.session_state.lesson_text    = text_input # Guardar texto escrito
            st.session_state.lesson_content = None
            st.session_state.lesson_error   = None


    # --- Bloque de generación: separado de los botones ---
    if st.session_state.lesson_pending:
        topic       = st.session_state.get("lesson_topic", "Aventura Diaria")
        custom_text = st.session_state.get("lesson_text", None) # Consumir texto

        with st.spinner("✨ Preparando tu lección personalizada con Llama 3.1..."):
            content, error = generate_lesson(user, topic, custom_text)

        st.session_state.lesson_content = content
        st.session_state.lesson_error   = error
        st.session_state.lesson_pending = False  # reset del flag
        st.session_state.lesson_text    = None  # reset del texto

    # --- Mostrar error de generación ---
    if st.session_state.lesson_error:
        show_error(f"Error al generar la lección: {st.session_state.lesson_error}")

    # --- Mostrar lección ---
    if st.session_state.lesson_content:
        st.write("---")
        st.markdown("### 📚 Tu Lección de Hoy")
        st.markdown(
            f"<div class='lesson-container' style='border-color: {color};'>"
            f"{st.session_state.lesson_content}"
            f"</div>",
            unsafe_allow_html=True
        )

        st.write("")
        if st.button(f"✅ ¡Completé esta lección! (+{XP_PER_LESSON} XP)", use_container_width=True):
            st.session_state.xp += XP_PER_LESSON
            saved, save_error = save_xp_to_sheet(user, XP_PER_LESSON)
            if not saved:
                show_warning(f"XP guardado localmente, pero no en la nube: {save_error}")
            st.balloons()
            st.success(f"¡Increíble trabajo, {user}! +{XP_PER_LESSON} XP. Sigue así! 🏆")
            st.session_state.lesson_content = None
            st.session_state.lesson_error   = None


# --- DISPARADOR SILENCIOSO DEL REPORTE SEMANAL ---
send_weekly_report()
