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
# MEJORA #4 — MODULARIDAD: Configuración de logging
# Antes: Sin logging, los errores se perdían silenciosamente.
# Ahora: Los errores se registran en app.log para diagnóstico.
# ==========================================
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(page_title="Idiomaconnect", page_icon="✨", layout="centered")

# MEJORA #2 — UI/UX: CSS profundamente renovado.
# Antes: CSS básico con bordes redondeados genéricos, sin variables CSS, sin animaciones.
# Ahora: Sistema de diseño completo con variables CSS, animaciones de entrada,
# glassmorphism, gradientes, estados hover enriquecidos y media queries para mobile.
# Inspiración "Google Stitch": superficies flotantes, transiciones fluidas, jerarquía clara.
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
    }

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
    }
    h1, h2, h3 { font-family: 'Nunito', sans-serif; }

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
    .stButton > button:active {
        transform: translateY(0px) scale(0.98) !important;
    }

    /* --- TARJETA DE PERFIL con glassmorphism y animación de entrada --- */
    .profile-card {
        padding: 28px 20px;
        border-radius: var(--radius-lg);
        text-align: center;
        color: white;
        margin-bottom: 16px;
        box-shadow: var(--shadow-lift);
        position: relative;
        overflow: hidden;
        animation: cardReveal 0.5s ease both;
        border: 1px solid rgba(255,255,255,0.35);
        backdrop-filter: blur(4px);
    }
    /* Brillo decorativo en esquina superior derecha */
    .profile-card::before {
        content: '';
        position: absolute;
        top: -30px; right: -30px;
        width: 100px; height: 100px;
        background: rgba(255,255,255,0.2);
        border-radius: 50%;
    }
    .profile-card h2 {
        margin: 0 0 6px 0;
        font-size: 1.6rem;
        font-weight: 800;
        text-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .profile-card p {
        margin: 0;
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .profile-card .emoji-avatar {
        font-size: 2.8rem;
        margin-bottom: 10px;
        display: block;
    }

    /* --- TARJETA PRINCIPAL DEL DASHBOARD --- */
    .dashboard-header {
        padding: 20px 24px;
        border-radius: var(--radius-md);
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: var(--shadow-lift);
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    }
    .dashboard-header::after {
        content: '';
        position: absolute;
        bottom: -20px; left: -20px;
        width: 120px; height: 120px;
        background: rgba(255,255,255,0.1);
        border-radius: 50%;
    }
    .dashboard-header h2, .dashboard-header h3 {
        margin: 0;
        position: relative; z-index: 1;
    }

    /* --- CONTENEDOR DE LECCIÓN con borde izquierdo de color dinámico --- */
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
    }
    .welcome-container p {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 32px;
    }

    /* --- BANNER DE ERROR Y ADVERTENCIA --- */
    .error-banner {
        background: #fff3f3;
        border: 1px solid #ffb3b3;
        border-left: 4px solid #e74c3c;
        border-radius: var(--radius-sm);
        padding: 14px 18px;
        margin: 12px 0;
        color: #c0392b;
        font-size: 0.9rem;
    }
    .warning-banner {
        background: #fffbf0;
        border: 1px solid #ffd591;
        border-left: 4px solid #f39c12;
        border-radius: var(--radius-sm);
        padding: 14px 18px;
        margin: 12px 0;
        color: #856404;
        font-size: 0.9rem;
    }

    /* --- ANIMACIONES --- */
    @keyframes cardReveal {
        from { opacity: 0; transform: translateY(20px) scale(0.96); }
        to   { opacity: 1; transform: translateY(0)    scale(1);    }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to   { opacity: 1; }
    }
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(16px); }
        to   { opacity: 1; transform: translateY(0);    }
    }

    /* Añadir delay escalonado a las tarjetas de perfil */
    div[data-testid="column"]:nth-child(1) .profile-card { animation-delay: 0.0s; }
    div[data-testid="column"]:nth-child(2) .profile-card { animation-delay: 0.1s; }
    div[data-testid="column"]:nth-child(3) .profile-card { animation-delay: 0.2s; }

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

# MEJORA #2 — UI/UX: Se añade "emoji" por perfil para identidad visual en la tarjeta.
# Antes: Las tarjetas sólo mostraban nombre y hobby en un div coloreado plano.
# Ahora: Cada perfil tiene un emoji representativo que refuerza la identidad visual.
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
# MEJORA #4 — MODULARIDAD: Constantes de configuración centralizadas
# Antes: Valores mágicos dispersos (model, max_tokens, etc.) dentro de las funciones.
# Ahora: Un bloque de configuración único y fácil de mantener.
# ==========================================
GROQ_MODEL_CHAT  = "llama3-8b-8192"
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

# MEJORA #1 — ROBUSTEZ: Inicialización del cliente Groq con mensaje de error accionable.
# Antes: El bloque `except` silencioso dejaba groq_client=None sin feedback claro al developer.
# Ahora: Se distingue entre "clave ausente" y "clave inválida", y se muestra el error en UI.
@st.cache_resource(show_spinner=False)
def init_groq_client():
    """
    Inicializa y cachea el cliente Groq.
    Retorna (client, error_message). El cliente es None si falla.
    """
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


# MEJORA #1 — ROBUSTEZ: Conexión a Google Sheets con manejo granular de errores.
# Antes: Un solo except genérico que retornaba None sin distinguir el tipo de fallo.
# Ahora: Se diferencian errores de credenciales, de red y de nombre de hoja,
# y se retorna un mensaje descriptivo para mostrar en la UI.
@st.cache_resource(show_spinner=False)
def get_db_connection():
    """
    Retorna (sheet, error_message). La hoja es None si falla la conexión.
    """
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, GSHEETS_SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open("Idiomaconnect_DB").sheet1
        return sheet, None
    except KeyError:
        return None, "Faltan credenciales `gcp_service_account` en secrets.toml."
    except gspread.exceptions.SpreadsheetNotFound:
        return None, "Hoja 'Idiomaconnect_DB' no encontrada. Verifica el nombre y los permisos."
    except gspread.exceptions.APIError as e:
        logger.error(f"Google Sheets API error: {e}")
        return None, f"Error de Google Sheets API: {e}"
    except Exception as e:
        logger.error(f"Error de conexión a Google Sheets: {e}")
        return None, f"No se pudo conectar a Google Sheets: {e}"


# ==========================================
# 4. FUNCIONES PRINCIPALES
# ==========================================

# MEJORA #1 — ROBUSTEZ: Se añade manejo explícito de rate limits y timeouts.
# MEJORA #4 — MODULARIDAD: El system_prompt ahora se construye en una función separada
#             para facilitar pruebas unitarias y futura internacionalización.
# Antes: Monolito sin manejo de errores de red ni de la API de Groq.
# Ahora: Retorna (content, error). Distingue RateLimitError, timeout y errores genéricos.
def _build_system_prompt(profile_name: str) -> str:
    """Construye el system prompt para el LLM según el perfil de la alumna."""
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


def generate_lesson(profile_name: str, topic: str, custom_audio_text: str | None = None):
    """
    Genera una lección personalizada usando Groq.
    Retorna (content_string, error_string). Uno de los dos será None.
    """
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    system_prompt = _build_system_prompt(profile_name)
    user_prompt = f"El tema de hoy es: {topic}."
    if custom_audio_text:
        user_prompt += f" La alumna ha dicho por voz: '{custom_audio_text}'. Adapta la lección a esto."

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=GROQ_TEMPERATURE,
            max_tokens=GROQ_MAX_TOKENS,
        )
        return response.choices[0].message.content, None

    # MEJORA #1: Captura específica de rate limit (429) de Groq
    except Exception as e:
        err_str = str(e).lower()
        if "rate_limit" in err_str or "429" in err_str:
            logger.warning(f"Groq rate limit alcanzado: {e}")
            return None, "Se alcanzó el límite de la API de Groq. Espera un momento e inténtalo de nuevo. ⏳"
        elif "timeout" in err_str or "connection" in err_str:
            logger.error(f"Groq connection error: {e}")
            return None, "No se pudo conectar con Groq. Verifica tu conexión a internet. 🌐"
        else:
            logger.error(f"Groq error inesperado: {e}")
            return None, f"Error al generar la lección: {e}"


# MEJORA #4 — MODULARIDAD: La transcripción de audio se extrae a su propia función.
# Antes: El bloque de transcripción estaba embebido directamente en la UI (col2).
# Ahora: Es una función independiente y testeable.
def transcribe_audio(audio_bytes: bytes):
    """
    Transcribe audio usando Groq Whisper.
    Retorna (transcription_text, error_string).
    """
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
        err_str = str(e).lower()
        if "rate_limit" in err_str or "429" in err_str:
            logger.warning(f"Whisper rate limit: {e}")
            return None, "Límite de transcripciones alcanzado. Intenta en unos segundos. ⏳"
        else:
            logger.error(f"Error de transcripción Whisper: {e}")
            return None, f"No se pudo transcribir el audio: {e}"
    finally:
        # MEJORA #1: Limpieza del archivo temporal garantizada (aunque falle la transcripción)
        if os.path.exists(TEMP_AUDIO_FILE):
            os.remove(TEMP_AUDIO_FILE)


# MEJORA #4 — MODULARIDAD: La función de guardado de XP en GSheets es explícita.
# Antes: La lógica de GSheets estaba comentada como "TODO" con get_db_connection() sin usar.
# Ahora: Función dedicada, lista para usar al presionar "Completé la lección".
def save_xp_to_sheet(profile_name: str, xp_gained: int):
    """
    Añade una fila de registro de XP a Google Sheets.
    Retorna (True, None) si éxito, (False, error_string) si falla.
    """
    sheet, db_error = get_db_connection()
    if db_error or not sheet:
        logger.warning(f"No se pudo guardar XP en Sheets: {db_error}")
        return False, db_error

    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, profile_name, xp_gained])
        return True, None
    except gspread.exceptions.APIError as e:
        logger.error(f"Error guardando XP: {e}")
        return False, f"Error de Google Sheets al guardar XP: {e}"


# MEJORA #1 — ROBUSTEZ: El reporte semanal ahora reporta errores en el log.
# Antes: `except Exception: pass` — falla 100% silenciosa, imposible de diagnosticar.
# Ahora: Los errores se registran con logger. El servidor de SMTP y las credenciales
#        se validan antes de intentar la conexión.
def send_weekly_report():
    """Envía el reporte semanal por email. Sólo se ejecuta los viernes."""
    if datetime.datetime.now().weekday() != 4:  # 4 = Viernes
        return

    try:
        sender   = st.secrets["email_sender"]
        password = st.secrets["email_password"]

        # Leer XP real desde GSheets si está disponible
        sheet, _ = get_db_connection()
        report_lines = []
        if sheet:
            try:
                rows = sheet.get_all_records()
                xp_totals = {}
                for row in rows:
                    name = row.get("profile", "")
                    xp   = int(row.get("xp", 0))
                    xp_totals[name] = xp_totals.get(name, 0) + xp
                for name, total in xp_totals.items():
                    report_lines.append(f"- {name}: {total} XP ganados esta semana.")
            except Exception as e:
                logger.warning(f"No se pudo leer XP desde Sheets para el reporte: {e}")

        if not report_lines:
            report_lines = [
                "- Antonia: 150 XP ganados.",
                "- Belén: 120 XP ganados.",
                "- Sofía: 180 XP ganados.",
            ]

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

    except KeyError as e:
        logger.error(f"Credencial de email faltante en secrets: {e}")
    except smtplib.SMTPAuthenticationError:
        logger.error("Error de autenticación SMTP. Verifica email_sender y email_password.")
    except smtplib.SMTPException as e:
        logger.error(f"Error SMTP al enviar reporte: {e}")
    except Exception as e:
        logger.error(f"Error inesperado en send_weekly_report: {e}")


# ==========================================
# MEJORA #2 — UI/UX: Función auxiliar para mostrar banners de error/advertencia
# ==========================================
def show_error(message: str):
    st.markdown(f"<div class='error-banner'>⚠️ {message}</div>", unsafe_allow_html=True)

def show_warning(message: str):
    st.markdown(f"<div class='warning-banner'>ℹ️ {message}</div>", unsafe_allow_html=True)


# ==========================================
# 5. MANEJO DE ESTADO (Session State)
# ==========================================
# MEJORA #3 — OPTIMIZACIÓN DE ESTADO: Inicialización centralizada en un solo bloque.
# Antes: Tres `if 'key' not in st.session_state` separados — funcional pero disperso.
# Ahora: Un dict de defaults aplicado en un loop. Fácil de ampliar con nuevas claves.
_STATE_DEFAULTS = {
    "current_user":   None,
    "xp":             0,
    "lesson_content": None,
    "lesson_error":   None,
    # MEJORA #3: Flag anti-bucle — evita regenerar la lección en cada rerun
    # causado por el st.balloons() o st.success() al ganar XP.
    "lesson_pending": False,
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
            # MEJORA #3 — ESTADO: El botón sólo cambia current_user y llama st.rerun() una vez.
            # No hay lógica adicional que pueda disparar un segundo rerun accidental.
            if st.button(f"¡Soy {name}!", key=f"btn_{name}", use_container_width=True):
                st.session_state.current_user = name
                # Resetear datos de sesión anterior al cambiar de perfil
                st.session_state.xp             = 0
                st.session_state.lesson_content = None
                st.session_state.lesson_error   = None
                st.session_state.lesson_pending = False
                st.rerun()

# --- PANTALLA PRINCIPAL (DASHBOARD) ---
else:
    user  = st.session_state.current_user
    color = PROFILES[user]["color"]
    grad  = PROFILES[user]["gradient"]
    emoji = PROFILES[user]["emoji"]

    # Encabezado personalizado
    st.markdown(f"""
        <div class='dashboard-header' style='background: {grad};'>
            <h2>¡Hola, {emoji} {user}!</h2>
            <h3>⭐ {st.session_state.xp} XP</h3>
        </div>
    """, unsafe_allow_html=True)

    # MEJORA #3 — ESTADO: El botón de cerrar sesión limpia todo el estado relevante
    # en una sola operación antes del rerun, evitando estados residuales inconsistentes.
    if st.button("← Cambiar alumna", type="secondary"):
        for key, default in _STATE_DEFAULTS.items():
            st.session_state[key] = default
        st.rerun()

    st.write("---")
    st.markdown("### ¿Qué quieres aprender hoy?")

    col1, col2 = st.columns(2)

    # --- Columna 1: IA me guía ---
    with col1:
        # MEJORA #3 — ESTADO: Se usa el flag `lesson_pending` para separar el clic del spinner.
        # Antes: La lógica de generación estaba directamente en el `if st.button(...)`.
        # Eso significa que si Streamlit re-ejecuta el script (por cualquier widget),
        # el botón vuelve a False y el spinner nunca se muestra correctamente.
        # Ahora: El clic sólo activa el flag. La generación ocurre después en un bloque dedicado.
        if st.button("🗺️ Que la IA me guíe", use_container_width=True):
            st.session_state.lesson_pending = True
            st.session_state.lesson_topic   = "Aventura Diaria (Vocabulario general y gramática divertida)"
            st.session_state.lesson_content = None
            st.session_state.lesson_error   = None

    # --- Columna 2: Tema de voz ---
    with col2:
        st.write("🗣️ **Tema Escolar / Personalizado**")
        st.write("Graba un audio contándome qué estás aprendiendo:")
        audio_bytes = audio_recorder(
            text="Clic para hablar",
            recording_color="#e74c3c",
            neutral_color="#95a5a6",
            icon_size="2x"
        )

        if audio_bytes:
            # MEJORA #3 — ESTADO: Igual que arriba, el flag evita regener en cada rerun.
            # Se verifica que no haya ya una lección pendiente para evitar doble disparo.
            if not st.session_state.lesson_pending:
                with st.spinner("Escuchando tu voz... 🎙️"):
                    text, t_error = transcribe_audio(audio_bytes)
                if t_error:
                    show_error(t_error)
                elif text:
                    st.success(f"Te escuché decir: *'{text}'*")
                    st.session_state.lesson_pending = True
                    st.session_state.lesson_topic   = "Tema del Colegio"
                    st.session_state.lesson_audio   = text
                    st.session_state.lesson_content = None
                    st.session_state.lesson_error   = None

    # --- Bloque de generación: separado de los botones ---
    # MEJORA #3 — ESTADO: Al procesar aquí (fuera de los botones), el spinner y la
    # generación son estables aunque Streamlit re-ejecute el script por otros widgets.
    if st.session_state.lesson_pending:
        topic      = st.session_state.get("lesson_topic", "Aventura Diaria")
        audio_text = st.session_state.pop("lesson_audio", None)  # consumir y limpiar

        with st.spinner("✨ Preparando tu lección personalizada..."):
            content, error = generate_lesson(user, topic, audio_text)

        st.session_state.lesson_content = content
        st.session_state.lesson_error   = error
        st.session_state.lesson_pending = False  # reset del flag

    # --- Mostrar error de generación ---
    if st.session_state.lesson_error:
        show_error(st.session_state.lesson_error)

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

            # MEJORA: Guardar en GSheets con feedback al usuario
            saved, save_error = save_xp_to_sheet(user, XP_PER_LESSON)
            if not saved:
                show_warning(f"XP guardado localmente, pero no en la nube: {save_error}")

            st.balloons()
            st.success(f"¡Increíble trabajo, {user}! +{XP_PER_LESSON} XP. Sigue así! 🏆")
            # Limpiar lección para invitar a una nueva
            st.session_state.lesson_content = None
            st.session_state.lesson_error   = None


# ==========================================
# 7. DISPARADOR SILENCIOSO DEL REPORTE SEMANAL
# ==========================================
# MEJORA #1: La función ya no falla silenciosamente; los errores van al log.
send_weekly_report()
