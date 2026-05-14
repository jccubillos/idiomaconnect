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
st.set_page_config(page_title="Idiomaconnect", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    /* ============================================================
       CYBER-LINGUIST HUD — Sistema de diseño dark + glassmorphism
       ============================================================ */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap');
    /* Ocultar el ícono roto "_arrov_rights" del expander de Streamlit.
       stExpanderToggleIcon es el testid exacto del contenedor del ícono. */
    [data-testid="stExpanderToggleIcon"] {
        display: none !important;
    }

    :root {
        /* Surfaces */
        --bg-base:         #101417;
        --bg-low:          #191c1f;
        --bg-mid:          #1d2023;
        --bg-high:         #272a2d;
        --bg-glass:        rgba(29, 32, 35, 0.65);
        --bg-glass-strong: rgba(29, 32, 35, 0.85);

        /* Neon accents */
        --neon-red:        #ff5351;
        --neon-red-soft:   #ffb3ae;
        --neon-cyan:       #00eefc;
        --neon-cyan-soft:  #d3fbff;
        --neon-purple:     #c464ff;
        --neon-purple-soft:#e5b4ff;
        --neon-green:      #39ff14;
        --neon-yellow:     #ffd400;
        --neon-pink:       #ff66c4;

        /* Text */
        --text-primary:   #e0e2e6;
        --text-secondary: #a8acb3;
        --text-dim:       #6b7280;
        --text-on-neon:   #0a0b1e;

        /* Borders & glow */
        --border-soft:    rgba(255,255,255,0.08);
        --border-cyan:    rgba(0,238,252,0.25);
        --border-red:     rgba(255,83,81,0.3);
        --glow-red:       0 0 20px rgba(255,83,81,0.4);
        --glow-cyan:      0 0 20px rgba(0,238,252,0.35);
        --glow-purple:    0 0 20px rgba(196,100,255,0.35);

        /* Shape */
        --radius-sm: 0.5rem;
        --radius-md: 0.75rem;
        --radius-lg: 1rem;
        --radius-xl: 1.5rem;

        /* Motion */
        --t-base: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* --- TIPOGRAFÍA GLOBAL --- */
    html, body, [class*="css"], .stMarkdown, p, li, label, span {
        font-family: 'Source Sans 3', sans-serif !important;
        color: var(--text-primary) !important;
    }
    h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.01em;
    }

    /* --- FONDO BASE --- */
    .stApp {
        background:
            radial-gradient(1200px 600px at 10% -10%, rgba(196,100,255,0.08), transparent 60%),
            radial-gradient(1000px 500px at 110% 10%, rgba(0,238,252,0.07), transparent 55%),
            radial-gradient(900px 700px at 50% 110%, rgba(255,83,81,0.06), transparent 60%),
            #101417;
        background-attachment: fixed;
    }
    .stApp::before {
        content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
        background-image:
            linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
        background-size: 48px 48px;
        mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
    }
    .main .block-container { position: relative; z-index: 1; }

    /* --- BOTONES NEON --- */
    .stButton > button {
        border-radius: var(--radius-sm) !important;
        transition: var(--t-base) !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 12px 24px !important;
        letter-spacing: 0.4px !important;
        background: linear-gradient(135deg, #ff5351, #bb1522) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,179,174,0.4) !important;
        box-shadow: 0 0 0 1px rgba(255,83,81,0.15), var(--glow-red) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 0 0 1px rgba(255,83,81,0.4), 0 0 28px rgba(255,83,81,0.55) !important;
        filter: brightness(1.08);
    }
    .stButton > button[kind="secondary"] {
        background: transparent !important;
        color: var(--neon-cyan) !important;
        border: 1px solid var(--border-cyan) !important;
        box-shadow: 0 0 12px rgba(0,238,252,0.18) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: rgba(0,238,252,0.06) !important;
        box-shadow: 0 0 18px rgba(0,238,252,0.35) !important;
    }

    /* --- BIENVENIDA --- */
    .welcome-container {
        text-align: center; padding: 36px 20px 16px;
        animation: fadeIn 0.6s ease both;
    }
    .welcome-container h1 {
        font-size: 2.8rem; font-weight: 800;
        background: linear-gradient(135deg, #ffb3ae 0%, #c464ff 50%, #00eefc 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; color: transparent !important;
        margin-bottom: 6px; letter-spacing: -0.02em;
        text-shadow: 0 0 30px rgba(255,83,81,0.3);
    }
    .welcome-container p {
        font-size: 1.05rem; color: var(--text-secondary) !important; margin-bottom: 24px;
    }

    /* --- ETIQUETA DE GRUPO --- */
    .group-label {
        text-align: center;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700;
        color: var(--neon-cyan) !important;
        font-size: 0.78rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin: 22px 0 14px 0;
        opacity: 0.85;
    }
    .group-label::before, .group-label::after {
        content: "—"; margin: 0 10px; color: var(--text-dim) !important;
    }

    /* --- TARJETA DE PERFIL (avatar real) --- */
    .profile-card {
        background: var(--bg-glass);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-xl);
        padding: 22px 16px 18px;
        text-align: center;
        margin-bottom: 12px;
        animation: cardReveal 0.5s ease both;
        position: relative;
        overflow: hidden;
        transition: var(--t-base);
    }
    .profile-card::before {
        content: ""; position: absolute; inset: 0; border-radius: var(--radius-xl);
        padding: 1px; pointer-events: none; z-index: 0;
        background: linear-gradient(135deg, var(--profile-accent, #ff5351) 0%, transparent 50%);
        -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
        -webkit-mask-composite: xor; mask-composite: exclude; opacity: 0.7;
    }
    .profile-card:hover { transform: translateY(-4px); }
    .profile-card .avatar-ring {
        width: 92px; height: 92px; margin: 0 auto 10px;
        border-radius: 50%;
        padding: 3px;
        background: conic-gradient(from 180deg, var(--profile-accent, #ff5351), transparent 60%, var(--profile-accent, #ff5351));
        box-shadow: 0 0 18px var(--profile-accent, #ff5351);
        animation: spin 12s linear infinite;
        position: relative; z-index: 1;
    }
    .profile-card .avatar-ring img {
        width: 100%; height: 100%; border-radius: 50%; object-fit: cover;
        background: var(--bg-mid); display: block;
        animation: spin 12s linear infinite reverse;
    }
    .profile-card .avatar-emoji {
        width: 86px; height: 86px; margin: 0 auto 10px;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-size: 2.4rem; background: var(--bg-mid);
        border: 2px solid var(--profile-accent, #ff5351);
        box-shadow: 0 0 18px var(--profile-accent, #ff5351);
        position: relative; z-index: 1;
    }
    .profile-card h2 {
        margin: 4px 0 2px;
        font-size: 1.25rem; font-weight: 800;
        color: var(--profile-accent, #ffb3ae) !important;
        text-shadow: 0 0 12px var(--profile-accent, #ff5351);
        position: relative; z-index: 1;
    }
    .profile-card p {
        margin: 0; font-size: 0.78rem;
        color: var(--text-secondary) !important;
        text-transform: uppercase; letter-spacing: 1px;
        font-weight: 600;
        position: relative; z-index: 1;
    }

    /* --- WORLD ENTRY HERO (página themed por mundo) --- */
    .world-hero {
        position: relative;
        overflow: hidden;
        border-radius: var(--radius-xl);
        padding: 36px 28px 40px;
        margin: 6px 0 14px;
        background:
            radial-gradient(ellipse at 30% 20%, var(--world-accent-soft, rgba(0,238,252,0.18)) 0%, transparent 55%),
            radial-gradient(ellipse at 70% 80%, var(--world-accent-soft, rgba(0,238,252,0.10)) 0%, transparent 55%),
            linear-gradient(135deg, rgba(29,32,35,0.92) 0%, rgba(16,20,23,0.96) 100%);
        border: 1px solid var(--world-accent, #00eefc);
        box-shadow: 0 0 32px var(--world-accent-glow, rgba(0,238,252,0.25));
        backdrop-filter: blur(15px);
        animation: cardReveal 0.55s ease both;
        text-align: center;
    }
    .world-hero::before {
        content: ""; position: absolute; inset: 0; pointer-events: none;
        background-image:
            linear-gradient(var(--world-accent, #00eefc) 1px, transparent 1px),
            linear-gradient(90deg, var(--world-accent, #00eefc) 1px, transparent 1px);
        background-size: 40px 40px;
        opacity: 0.05;
        mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);
    }
    .world-hero::after {
        content: ""; position: absolute; inset: -2px; border-radius: inherit;
        pointer-events: none;
        background: conic-gradient(from 0deg, transparent 0%, var(--world-accent, #00eefc) 25%, transparent 50%);
        filter: blur(40px);
        opacity: 0.18;
        animation: spin 22s linear infinite;
    }
    .world-hero-emoji {
        font-size: 5.5rem;
        line-height: 1;
        display: inline-block;
        filter: drop-shadow(0 0 24px var(--world-accent, #00eefc));
        animation: floatY 4s ease-in-out infinite;
        position: relative; z-index: 1;
    }
    .world-hero-breadcrumb {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: var(--text-dim) !important;
        font-size: 0.72rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin: 0 0 16px;
        position: relative; z-index: 1;
    }
    .world-hero-breadcrumb b {
        color: var(--world-accent, #00eefc) !important;
        text-shadow: 0 0 10px var(--world-accent, #00eefc);
    }
    .world-hero-title {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 2.4rem;
        line-height: 1.05;
        letter-spacing: -0.02em;
        color: var(--world-accent, #00eefc) !important;
        text-shadow: 0 0 24px var(--world-accent, #00eefc);
        margin: 8px 0 6px;
        position: relative; z-index: 1;
    }
    .world-hero-tagline {
        color: var(--text-secondary) !important;
        font-size: 1rem;
        line-height: 1.5;
        max-width: 480px;
        margin: 0 auto;
        position: relative; z-index: 1;
    }

    /* --- MODE BUTTONS (Lección / Batalla en world entry) --- */
    .mode-card {
        background: var(--bg-glass);
        backdrop-filter: blur(15px);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-lg);
        padding: 22px 18px 14px;
        text-align: center;
        margin-bottom: 10px;
        transition: var(--t-base);
        position: relative; overflow: hidden;
        animation: cardReveal 0.5s ease both;
    }
    .mode-card::before {
        content: ""; position: absolute; inset: 0; border-radius: inherit;
        padding: 1px; pointer-events: none;
        background: linear-gradient(135deg, var(--mode-accent, #00eefc), transparent 60%);
        -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
        -webkit-mask-composite: xor; mask-composite: exclude; opacity: 0.7;
    }
    .mode-card:hover { transform: translateY(-3px); }
    .mode-icon {
        font-size: 2.6rem; line-height: 1;
        filter: drop-shadow(0 0 16px var(--mode-accent, #00eefc));
        margin-bottom: 8px;
    }
    .mode-name {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 1.2rem;
        color: var(--mode-accent, #00eefc) !important;
        text-shadow: 0 0 12px var(--mode-accent, #00eefc);
        margin: 4px 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .mode-desc {
        color: var(--text-secondary) !important;
        font-size: 0.82rem;
        line-height: 1.4;
        margin: 0 0 12px;
        min-height: 40px;
    }

    /* --- FLASHCARDS VISUALES --- */
    .fc-card {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 2px solid var(--fc-accent, #00eefc);
        border-radius: var(--radius-xl);
        padding: 32px 20px 24px;
        text-align: center;
        margin: 6px 0 14px;
        box-shadow: 0 0 32px var(--fc-accent, #00eefc);
        animation: cardReveal 0.45s ease both;
    }
    .fc-emoji {
        font-size: 6rem;
        line-height: 1;
        margin-bottom: 12px;
        filter: drop-shadow(0 0 22px var(--fc-accent, #00eefc));
        animation: bounceIn 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    }
    .fc-hint {
        color: var(--text-secondary) !important;
        font-size: 0.95rem;
        margin: 0;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .fc-feedback {
        margin: 14px 0 10px;
        padding: 12px 14px;
        border-radius: var(--radius-md);
        text-align: center;
        font-size: 0.95rem;
        font-weight: 600;
        animation: cardReveal 0.35s ease both;
    }
    .fc-feedback.ok {
        background: rgba(57, 255, 20, 0.12);
        border: 1px solid #39ff14;
        color: #d4ffd0 !important;
        text-shadow: 0 0 8px rgba(57,255,20,0.6);
    }
    .fc-feedback.bad {
        background: rgba(255, 83, 81, 0.12);
        border: 1px solid #ff5351;
        color: #ffd0ce !important;
    }
    @keyframes bounceIn {
        0%   { transform: scale(0.3); opacity: 0; }
        60%  { transform: scale(1.1); opacity: 1; }
        100% { transform: scale(1); opacity: 1; }
    }

    /* --- SENTENCE BUILDER --- */
    .sb-card {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 2px solid var(--sb-accent, #c464ff);
        border-radius: var(--radius-lg);
        padding: 18px 18px 14px;
        text-align: center;
        margin: 4px 0 12px;
        box-shadow: 0 0 22px var(--sb-accent, #c464ff);
        animation: cardReveal 0.4s ease both;
    }
    .sb-hint {
        color: var(--text-secondary) !important;
        font-size: 0.82rem;
        margin: 0 0 6px;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    .sb-spanish {
        color: #e0e2e6 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 1.35rem;
        font-weight: 700;
        margin: 0;
    }
    .sb-slot {
        min-height: 60px;
        border: 2px dashed #3a3d40;
        border-radius: var(--radius-md);
        padding: 14px 12px;
        margin: 10px 0 14px;
        background: rgba(29, 32, 35, 0.5);
        display: flex; align-items: center; justify-content: center;
        transition: var(--t-base);
    }
    .sb-slot-text {
        color: #e0e2e6 !important;
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0;
        text-align: center;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    .sb-section-label {
        color: var(--text-secondary) !important;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
        margin: 6px 0 4px;
    }

    /* --- STORY FILL (Cuento Personalizado) --- */
    .sf-card {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 2px solid var(--sf-accent, #ff66c4);
        border-radius: var(--radius-lg);
        padding: 22px 18px;
        margin: 6px 0 14px;
        box-shadow: 0 0 22px var(--sf-accent, #ff66c4);
        animation: cardReveal 0.45s ease both;
    }
    .sf-sentence {
        color: #e0e2e6 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 1.15rem;
        line-height: 1.7;
        margin: 0;
        text-align: center;
        font-weight: 600;
    }
    .sf-blank-empty {
        display: inline-block;
        min-width: 80px;
        border-bottom: 2px solid var(--sf-accent, #ff66c4);
        color: var(--sf-accent, #ff66c4) !important;
        font-weight: 700;
        padding: 0 6px;
    }
    .sf-story {
        background: var(--bg-glass);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-lg);
        padding: 22px 20px;
        margin: 14px 0 12px;
        animation: cardReveal 0.5s ease both;
    }
    .sf-text {
        color: #e0e2e6 !important;
        font-size: 1.0rem;
        line-height: 1.85;
        margin: 0;
    }
    .sf-blank {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 700;
    }
    .sf-blank.ok {
        background: rgba(57, 255, 20, 0.18);
        color: #d4ffd0 !important;
        border: 1px solid #39ff14;
        text-shadow: 0 0 6px rgba(57,255,20,0.5);
    }
    .sf-blank.bad {
        background: rgba(255, 83, 81, 0.15);
        color: #ffd0ce !important;
        border: 1px solid #ff5351;
    }
    .sf-blank.bad s {
        opacity: 0.6;
        margin-right: 4px;
    }

    /* --- TALLER DE LETRAS (Writing world) --- */
    .writing-card {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 2px solid var(--w-accent, #ff66c4);
        border-radius: var(--radius-lg);
        padding: 22px 20px 18px;
        margin: 6px 0 14px;
        box-shadow: 0 0 22px var(--w-accent, #ff66c4);
        animation: cardReveal 0.45s ease both;
    }
    .writing-prompt-label {
        color: var(--text-secondary) !important;
        font-size: 0.78rem;
        letter-spacing: 1px;
        text-transform: uppercase;
        font-weight: 600;
        margin: 0 0 6px;
    }
    .writing-prompt-text {
        color: #e0e2e6 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700;
        font-size: 1.2rem;
        line-height: 1.45;
        margin: 0;
    }
    .ds-scene {
        font-size: 3.4rem;
        line-height: 1.1;
        text-align: center;
        margin: 8px 0 16px;
        filter: drop-shadow(0 0 16px var(--w-accent, #ff66c4));
        animation: bounceIn 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    }
    /* Tarjeta de review en la pantalla final */
    .writing-review {
        background: var(--bg-glass);
        border-left: 3px solid var(--rev-accent, #00eefc);
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        position: relative;
        animation: cardReveal 0.35s ease both;
    }
    .writing-rev-score {
        position: absolute;
        top: 10px; right: 14px;
        color: var(--rev-accent, #00eefc) !important;
        font-weight: 800;
        font-size: 1.1rem;
        text-shadow: 0 0 8px var(--rev-accent, #00eefc);
        margin: 0;
    }
    .writing-rev-row {
        margin: 4px 0;
        color: var(--text-primary) !important;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .writing-rev-row b { color: var(--text-secondary) !important; }
    .writing-rev-row i { color: #e0e2e6 !important; opacity: 0.85; }
    .writing-rev-comment {
        margin: 8px 0 0;
        padding: 8px 10px;
        background: rgba(0, 238, 252, 0.08);
        border-radius: 6px;
        color: var(--text-primary) !important;
        font-size: 0.88rem;
        font-style: italic;
    }

    /* --- ROLEPLAY PICKER (Café Conversación) --- */
    .rp-card {
        background: var(--bg-glass);
        backdrop-filter: blur(15px);
        border: 1px solid #c464ff;
        border-radius: var(--radius-lg);
        padding: 16px 14px 8px;
        text-align: center;
        margin-bottom: 10px;
        box-shadow: 0 0 16px rgba(196,100,255,0.25);
        animation: cardReveal 0.45s ease both;
    }
    .rp-emoji {
        font-size: 2.4rem; line-height: 1;
        filter: drop-shadow(0 0 12px #c464ff);
        margin-bottom: 4px;
    }
    .rp-name {
        color: #c464ff !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 1.05rem;
        margin: 4px 0 2px;
        text-shadow: 0 0 10px rgba(196,100,255,0.7);
    }
    .rp-meta {
        color: var(--text-dim) !important;
        font-size: 0.75rem;
        margin: 0 0 4px;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    .rp-role {
        color: var(--text-secondary) !important;
        font-size: 0.8rem;
        margin: 0 0 8px;
    }
    /* Contexto de role-play durante la conversación */
    .rp-context {
        background: var(--bg-glass);
        border: 1px solid var(--rp-accent, #c464ff);
        border-radius: var(--radius-md);
        padding: 10px 14px;
        margin: 0 0 10px;
        font-size: 0.86rem;
    }
    .rp-context-row { margin: 2px 0; color: var(--text-secondary) !important; }
    .rp-context-row b { color: var(--rp-accent, #c464ff) !important; }
    /* Panel de misiones */
    .rp-objectives {
        background: rgba(196,100,255,0.06);
        border-left: 3px solid #c464ff;
        border-radius: 8px;
        padding: 10px 14px;
        margin: 0 0 14px;
    }
    .rp-obj-title {
        color: #c464ff !important;
        font-size: 0.85rem;
        font-weight: 700;
        margin: 0 0 6px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .rp-obj-list {
        list-style: none;
        padding: 0; margin: 0;
        font-size: 0.85rem;
    }
    .rp-obj-list li {
        margin: 3px 0;
        line-height: 1.4;
    }
    .obj-pending {
        color: var(--text-secondary) !important;
    }
    .obj-done {
        color: #39ff14 !important;
        text-shadow: 0 0 6px rgba(57,255,20,0.4);
    }
    .obj-mark {
        display: inline-block;
        width: 18px;
        font-weight: 800;
        margin-right: 4px;
    }

    /* --- REINFORCE CARD (refuerzo de errores recurrentes) --- */
    .reinforce-card {
        background: linear-gradient(135deg, rgba(255,212,0,0.10) 0%, rgba(255,83,81,0.06) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid #ffd400;
        border-radius: var(--radius-lg);
        padding: 12px 18px 8px;
        margin: 6px 0 10px;
        box-shadow: 0 0 14px rgba(255,212,0,0.15);
        animation: cardReveal 0.45s ease both;
    }
    .reinforce-title {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 0.78rem;
        color: #ffd400 !important;
        margin: 0 0 4px;
        letter-spacing: 2px;
        text-shadow: 0 0 8px rgba(255,212,0,0.5);
    }
    .reinforce-pattern {
        color: var(--text-primary) !important;
        font-weight: 700;
        font-size: 1.05rem;
        margin: 4px 0;
    }
    .reinforce-hint {
        color: var(--text-secondary) !important;
        font-size: 0.88rem;
        line-height: 1.4;
        margin: 4px 0 6px;
    }
    .reinforce-examples {
        margin: 4px 0 6px;
        padding-left: 20px;
        font-size: 0.88rem;
        color: #e0e2e6 !important;
    }
    .reinforce-examples li {
        margin: 2px 0;
        font-style: italic;
    }

    /* --- BADGES GRID (Logros) --- */
    .badges-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 8px;
        margin: 8px 0 12px;
    }
    .badge-tile {
        background: var(--bg-glass);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-md);
        padding: 10px 8px;
        text-align: center;
        transition: var(--t-base);
        animation: cardReveal 0.35s ease both;
    }
    .badge-earned {
        border-color: var(--profile-accent, #00eefc);
        box-shadow: 0 0 12px var(--profile-accent, #00eefc);
    }
    .badge-locked {
        opacity: 0.35;
        filter: grayscale(0.7);
    }
    .badge-emoji {
        font-size: 2rem;
        line-height: 1;
        margin-bottom: 4px;
    }
    .badge-earned .badge-emoji {
        filter: drop-shadow(0 0 10px var(--profile-accent, #00eefc));
    }
    .badge-name {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 0.82rem;
        color: var(--text-primary) !important;
        margin: 2px 0;
    }
    .badge-earned .badge-name {
        color: var(--profile-accent, #00eefc) !important;
    }
    .badge-desc {
        font-size: 0.7rem;
        color: var(--text-dim) !important;
        line-height: 1.3;
    }

    /* --- DAILY MISSION CARD (Misión del día + Recomendación + Racha) --- */
    .daily-card {
        background: var(--bg-glass);
        backdrop-filter: blur(15px);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-lg);
        padding: 16px 18px;
        margin: 6px 0 10px;
        animation: cardReveal 0.45s ease both;
        position: relative;
        overflow: hidden;
    }
    .daily-card::before {
        content: ""; position: absolute; inset: 0; border-radius: inherit;
        padding: 1px; pointer-events: none;
        background: linear-gradient(135deg, var(--profile-accent, #00eefc), transparent 60%);
        -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
        -webkit-mask-composite: xor; mask-composite: exclude; opacity: 0.7;
    }
    .daily-pending { box-shadow: 0 0 14px rgba(255,212,0,0.2); }
    .daily-started { box-shadow: 0 0 14px rgba(0,238,252,0.2); }
    .daily-done    { box-shadow: 0 0 14px rgba(57,255,20,0.2); }
    .daily-top {
        display: flex; justify-content: space-around;
        margin-bottom: 8px;
    }
    .daily-streak, .daily-today {
        display: flex; flex-direction: column; align-items: center;
        padding: 6px 12px;
    }
    .daily-streak-num, .daily-today-num {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 1.4rem;
        color: var(--profile-accent, #00eefc) !important;
        text-shadow: 0 0 10px var(--profile-accent, #00eefc);
        line-height: 1;
    }
    .daily-streak-lbl, .daily-today-lbl {
        font-size: 0.7rem;
        color: var(--text-dim) !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 4px;
    }
    .daily-status {
        text-align: center;
        color: var(--text-primary) !important;
        font-size: 0.92rem;
        font-weight: 600;
        margin: 8px 0 6px;
    }
    .daily-rec {
        margin: 6px 0 0;
        font-size: 0.9rem;
        color: var(--text-primary) !important;
        text-align: center;
    }
    .daily-rec-world {
        color: var(--profile-accent, #00eefc) !important;
        font-weight: 700;
        text-shadow: 0 0 8px var(--profile-accent, #00eefc);
    }
    .daily-rec-why {
        color: var(--text-dim) !important;
        font-size: 0.82rem;
        font-style: italic;
    }

    /* --- CULTURAL CAPSULE --- */
    .culture-card {
        background: linear-gradient(135deg, rgba(196,100,255,0.06) 0%, rgba(0,238,252,0.04) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(196,100,255,0.25);
        border-radius: var(--radius-lg);
        padding: 14px 18px 8px;
        margin: 8px 0 12px;
        box-shadow: 0 0 14px rgba(196,100,255,0.1);
        animation: cardReveal 0.5s ease both;
    }
    .culture-title {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 0.82rem;
        color: #e5b4ff !important;
        text-shadow: 0 0 10px rgba(196,100,255,0.5);
        margin: 0 0 6px;
        letter-spacing: 2px;
        text-align: center;
    }
    .culture-row {
        margin: 8px 0;
        padding: 6px 4px;
        border-top: 1px dashed rgba(255,255,255,0.07);
    }
    .culture-row:first-of-type { border-top: none; }
    .culture-row-label {
        font-size: 0.7rem;
        color: var(--text-dim) !important;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin: 0 0 2px;
        font-weight: 600;
    }
    .culture-row-en {
        color: var(--text-primary) !important;
        font-size: 0.92rem;
        font-weight: 600;
        margin: 2px 0;
        font-style: italic;
    }
    .culture-row-es {
        color: var(--text-secondary) !important;
        font-size: 0.82rem;
        margin: 2px 0;
    }

    /* --- EXAM MODE --- */
    .exam-skill-breakdown {
        background: var(--bg-glass);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-md);
        padding: 14px 18px;
        margin: 10px 0;
    }
    .exam-skill-row {
        display: flex; align-items: center;
        margin: 6px 0;
        font-size: 0.85rem;
    }
    .exam-skill-name {
        flex: 0 0 110px;
        color: var(--text-secondary) !important;
        text-transform: capitalize;
        font-weight: 600;
    }
    .exam-skill-bar {
        flex: 1;
        height: 8px;
        background: rgba(255,255,255,0.08);
        border-radius: 4px;
        overflow: hidden;
        margin: 0 12px;
        position: relative;
    }
    .exam-skill-bar > span {
        position: absolute;
        left: 0; top: 0;
        height: 100%;
        border-radius: 4px;
        transition: width 0.4s ease;
    }
    .exam-skill-score {
        flex: 0 0 50px;
        text-align: right;
        font-weight: 800;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* --- PARENT DASHBOARD --- */
    .parent-card {
        background: var(--bg-glass);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-md);
        padding: 14px 16px;
        margin: 6px 0 14px;
        animation: cardReveal 0.4s ease both;
    }
    .parent-kid-header {
        margin: 18px 0 8px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 1.4rem;
        font-weight: 800;
    }
    .parent-overview {
        display: flex; justify-content: space-around;
        flex-wrap: wrap;
    }
    .parent-stat {
        display: flex; flex-direction: column; align-items: center;
        padding: 4px 8px;
        min-width: 80px;
    }
    .parent-stat-val {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 1.4rem;
        color: var(--text-primary) !important;
        line-height: 1;
    }
    .parent-stat-lbl {
        font-size: 0.7rem;
        color: var(--text-dim) !important;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .parent-skill-row {
        display: flex; align-items: center;
        margin: 6px 0;
        font-size: 0.85rem;
    }
    .parent-skill-name {
        flex: 0 0 110px;
        color: var(--text-secondary) !important;
        text-transform: capitalize;
        font-weight: 600;
    }
    .parent-skill-bar {
        flex: 1;
        height: 10px;
        background: rgba(255,255,255,0.08);
        border-radius: 5px;
        overflow: hidden;
        margin: 0 12px;
        position: relative;
        min-width: 60px;
    }
    .parent-skill-bar > span {
        position: absolute;
        left: 0; top: 0;
        height: 100%;
        border-radius: 5px;
        transition: width 0.4s ease;
    }
    .parent-skill-stats {
        flex: 0 0 auto;
        text-align: right;
        font-size: 0.78rem;
        color: var(--text-dim) !important;
    }
    .parent-row {
        display: flex; justify-content: space-between;
        font-size: 0.78rem;
        padding: 5px 0;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .parent-row:last-child { border-bottom: none; }
    .parent-row-ts { color: var(--text-dim) !important; flex: 0 0 130px; }
    .parent-row-mid { color: var(--text-primary) !important; flex: 1; padding: 0 8px; text-transform: capitalize; }
    .parent-row-end { color: var(--neon-cyan) !important; flex: 0 0 110px; text-align: right; font-weight: 700; }

    /* --- CONVERSATION TIP (feedback puntual por turno) --- */
    .conv-tip {
        margin-top: 8px;
        padding: 6px 10px;
        background: rgba(255, 212, 0, 0.10);
        border-left: 3px solid #ffd400;
        border-radius: 6px;
        font-size: 0.82rem;
        color: #ffe680 !important;
        line-height: 1.4;
    }
    .conv-tip i { color: #ffe680 !important; }

    /* --- CONVERSATION END SUMMARY --- */
    .conv-summary {
        background: var(--bg-glass);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-lg);
        padding: 18px 20px;
        margin: 8px 0 14px;
        animation: cardReveal 0.5s ease both;
    }
    .summary-section {
        color: var(--text-secondary) !important;
        font-size: 0.78rem;
        margin: 14px 0 6px;
        letter-spacing: 1px;
        text-transform: uppercase;
        font-weight: 700;
    }
    .summary-section:first-child { margin-top: 0; }
    .summary-quote {
        color: #e0e2e6 !important;
        font-size: 1.05rem;
        margin: 0;
        font-style: italic;
        padding: 8px 12px;
        background: rgba(196,100,255,0.08);
        border-left: 3px solid #c464ff;
        border-radius: 6px;
    }
    .summary-word {
        display: inline-block;
        margin: 2px 4px 2px 0;
        padding: 3px 10px;
        border-radius: 50px;
        background: rgba(0,238,252,0.12);
        color: #d3fbff !important;
        border: 1px solid var(--neon-cyan);
        font-size: 0.85rem;
        font-weight: 600;
    }
    .summary-suggest {
        color: #e0e2e6 !important;
        font-size: 0.92rem;
        line-height: 1.5;
        margin: 0;
        padding: 10px 12px;
        background: rgba(255,212,0,0.08);
        border-left: 3px solid #ffd400;
        border-radius: 6px;
    }

    /* --- MINIMAL PAIRS --- */
    .mp-card {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 2px solid var(--mp-accent, #39ff14);
        border-radius: var(--radius-lg);
        padding: 18px 18px 14px;
        text-align: center;
        margin: 4px 0 12px;
        box-shadow: 0 0 22px var(--mp-accent, #39ff14);
        animation: cardReveal 0.4s ease both;
    }
    .mp-hint {
        color: var(--text-primary) !important;
        font-size: 1.05rem;
        margin: 0;
        font-weight: 700;
    }

    /* --- MEMORY MATCH --- */
    .mm-card {
        border-radius: var(--radius-md);
        padding: 18px 6px;
        text-align: center;
        font-weight: 700;
        line-height: 1;
        min-height: 56px;
        display: flex; align-items: center; justify-content: center;
        margin-bottom: 8px;
        animation: bounceIn 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    }
    .mm-face {
        border: 1px solid rgba(255,255,255,0.12);
    }

    /* --- BATTLE MODE HUD --- */
    .battle-hud {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 1px solid var(--neon-red);
        border-radius: var(--radius-lg);
        padding: 14px 18px;
        margin: 6px 0 12px;
        box-shadow: 0 0 24px rgba(255,83,81,0.2);
        position: relative; overflow: hidden;
    }
    .battle-hud::before {
        content: ""; position: absolute; inset: 0; pointer-events: none;
        background: linear-gradient(90deg, transparent, rgba(255,83,81,0.05), transparent);
        animation: scan 4s linear infinite;
    }
    .battle-hud-row {
        display: flex; align-items: center; gap: 14px;
        flex-wrap: wrap;
    }
    .battle-stat {
        display: flex; flex-direction: column; align-items: center;
        min-width: 60px;
        position: relative; z-index: 1;
    }
    .battle-stat-label {
        font-size: 0.62rem;
        color: var(--text-dim) !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 700;
    }
    .battle-stat-value {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 1.3rem;
        line-height: 1;
        margin-top: 2px;
    }

    .battle-hp-wrap {
        flex: 1; min-width: 160px; position: relative; z-index: 1;
    }
    .battle-hp-bar {
        background: rgba(0,0,0,0.5);
        border: 1px solid var(--border-soft);
        border-radius: 4px;
        height: 18px;
        overflow: hidden;
        position: relative;
    }
    .battle-hp-fill {
        height: 100%;
        transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1), background 0.3s;
        box-shadow: 0 0 10px currentColor;
    }
    .battle-hp-fill.high   { background: var(--neon-green); color: var(--neon-green); }
    .battle-hp-fill.mid    { background: var(--neon-yellow); color: var(--neon-yellow); }
    .battle-hp-fill.low    { background: var(--neon-red); color: var(--neon-red); animation: pulse 0.6s ease infinite; }
    .battle-hp-text {
        position: absolute; top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800; font-size: 0.78rem;
        color: #fff !important;
        text-shadow: 0 0 4px #000, 1px 1px 0 rgba(0,0,0,0.5);
        letter-spacing: 1px;
    }

    /* --- BATTLE QUESTION CARD --- */
    .battle-question {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 1px solid var(--border-soft);
        border-left: 3px solid var(--neon-cyan);
        border-radius: var(--radius-md);
        padding: 22px 24px;
        margin: 8px 0;
        animation: slideUp 0.35s ease both;
        box-shadow: 0 0 18px rgba(0,238,252,0.1);
    }
    .battle-q-meta {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 12px;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    .battle-q-num {
        color: var(--neon-cyan) !important;
        text-shadow: 0 0 8px rgba(0,238,252,0.5);
        font-weight: 800;
    }
    .battle-q-type {
        color: var(--text-dim) !important;
        background: rgba(255,255,255,0.04);
        padding: 3px 10px;
        border-radius: 50px;
        border: 1px solid var(--border-soft);
        font-weight: 700;
    }
    .battle-q-text {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700;
        font-size: 1.25rem;
        line-height: 1.4;
        color: var(--text-primary) !important;
        margin: 8px 0 14px;
    }
    .battle-blank {
        display: inline-block;
        min-width: 90px;
        padding: 0 10px;
        margin: 0 2px;
        border-bottom: 3px solid #ffd400;
        color: #ffd400 !important;
        font-weight: 800;
        letter-spacing: 4px;
        text-shadow: 0 0 8px rgba(255,212,0,0.6);
    }
    .battle-q-hint {
        font-family: 'Source Sans 3', sans-serif !important;
        font-size: 0.95rem;
        color: var(--text-secondary) !important;
        margin: 6px 0 14px;
        padding: 10px 14px;
        background: rgba(0, 238, 252, 0.08);
        border-left: 3px solid var(--neon-cyan);
        border-radius: 6px;
    }
    .battle-q-hint i {
        color: var(--text-primary) !important;
    }

    /* --- BATTLE FEEDBACK FLASH --- */
    .battle-flash {
        border-radius: var(--radius-md);
        padding: 18px 20px;
        margin: 10px 0;
        text-align: center;
        animation: flashIn 0.4s ease both;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    .battle-flash-correct {
        background: rgba(57,255,20,0.08);
        border: 1px solid rgba(57,255,20,0.5);
        box-shadow: 0 0 20px rgba(57,255,20,0.3);
    }
    .battle-flash-correct .flash-title {
        color: var(--neon-green) !important;
        text-shadow: 0 0 16px rgba(57,255,20,0.7);
    }
    .battle-flash-wrong {
        background: rgba(255,83,81,0.08);
        border: 1px solid rgba(255,83,81,0.5);
        box-shadow: 0 0 20px rgba(255,83,81,0.3);
    }
    .battle-flash-wrong .flash-title {
        color: var(--neon-red) !important;
        text-shadow: 0 0 16px rgba(255,83,81,0.7);
    }
    .flash-title {
        font-weight: 800;
        font-size: 1.4rem;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .flash-detail {
        color: var(--text-secondary) !important;
        font-size: 0.9rem;
        margin: 6px 0 0;
    }

    /* --- VICTORY / DEFEAT screens --- */
    .battle-end {
        text-align: center;
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border-radius: var(--radius-xl);
        padding: 40px 28px;
        margin: 10px 0;
        animation: cardReveal 0.5s ease both;
        position: relative;
        overflow: hidden;
    }
    .battle-end-victory {
        border: 2px solid var(--neon-green);
        box-shadow: 0 0 40px rgba(57,255,20,0.35);
    }
    .battle-end-defeat {
        border: 2px solid var(--neon-red);
        box-shadow: 0 0 40px rgba(255,83,81,0.35);
    }
    .battle-end-title {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 3rem;
        line-height: 1;
        letter-spacing: -0.02em;
        margin: 0 0 8px;
    }
    .battle-end-victory .battle-end-title {
        color: var(--neon-green) !important;
        text-shadow: 0 0 24px rgba(57,255,20,0.8);
    }
    .battle-end-defeat .battle-end-title {
        color: var(--neon-red) !important;
        text-shadow: 0 0 24px rgba(255,83,81,0.8);
    }
    .battle-end-emoji {
        font-size: 4rem;
        line-height: 1;
        margin-bottom: 4px;
        filter: drop-shadow(0 0 18px currentColor);
    }
    .battle-end-stats {
        display: flex; justify-content: center; gap: 28px;
        flex-wrap: wrap;
        margin: 18px 0 8px;
    }
    .battle-end-stat-num {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 2rem;
        line-height: 1;
    }
    .battle-end-stat-label {
        font-size: 0.7rem;
        color: var(--text-dim) !important;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        font-weight: 700;
        margin-top: 4px;
    }

    /* Reactividad de XP badge: respiración suave */
    .dashboard-header .xp-display {
        animation: breathe 3s ease-in-out infinite;
    }

    /* --- DAILY REVIEW (SRS) hero card sobre el grid --- */
    .srs-hero {
        background: linear-gradient(135deg,
            rgba(196,100,255,0.10) 0%,
            rgba(0,238,252,0.08) 100%);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(196,100,255,0.4);
        border-radius: var(--radius-lg);
        padding: 16px 20px;
        margin: 8px 0 14px;
        display: flex; align-items: center; gap: 14px;
        box-shadow: 0 0 22px rgba(196,100,255,0.18);
        position: relative; overflow: hidden;
        animation: cardReveal 0.5s ease both;
    }
    .srs-hero-icon {
        font-size: 2.4rem;
        filter: drop-shadow(0 0 14px #c464ff);
        animation: floatY 4s ease-in-out infinite;
    }
    .srs-hero-info { flex: 1; min-width: 0; }
    .srs-hero-title {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800; font-size: 1.05rem;
        color: #c464ff !important;
        text-shadow: 0 0 10px rgba(196,100,255,0.6);
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .srs-hero-sub {
        color: var(--text-secondary) !important;
        font-size: 0.84rem;
        margin: 3px 0 0;
    }
    .srs-hero-badge {
        background: rgba(255,212,0,0.1);
        border: 1px solid rgba(255,212,0,0.5);
        border-radius: 50px;
        padding: 4px 12px;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 0.85rem;
        color: var(--neon-yellow) !important;
        text-shadow: 0 0 8px rgba(255,212,0,0.5);
        flex-shrink: 0;
    }

    /* --- SRS FLASHCARD --- */
    .srs-card {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(196,100,255,0.5);
        border-radius: var(--radius-xl);
        padding: 36px 28px;
        margin: 10px 0;
        text-align: center;
        box-shadow: 0 0 28px rgba(196,100,255,0.2);
        animation: slideUp 0.4s ease both;
        position: relative; overflow: hidden;
    }
    .srs-progress {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: var(--text-dim) !important;
        margin: 0 0 18px;
    }
    .srs-progress b { color: #c464ff !important; text-shadow: 0 0 8px rgba(196,100,255,0.6); }
    .srs-word {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 2.6rem; font-weight: 800;
        color: var(--text-primary) !important;
        line-height: 1.1;
        margin: 8px 0 4px;
        letter-spacing: -0.01em;
    }
    .srs-emoji {
        font-size: 3rem;
        line-height: 1;
        margin-bottom: 6px;
        filter: drop-shadow(0 0 14px #c464ff);
    }
    .srs-ipa {
        color: #00eefc !important;
        font-family: 'Source Sans 3', sans-serif !important;
        font-size: 1rem;
        margin: 4px 0 16px;
        text-shadow: 0 0 8px rgba(0,238,252,0.4);
    }
    .srs-translation {
        background: rgba(57,255,20,0.08);
        border: 1px solid rgba(57,255,20,0.4);
        border-radius: var(--radius-md);
        padding: 14px 18px;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700;
        font-size: 1.3rem;
        color: var(--neon-green) !important;
        text-shadow: 0 0 10px rgba(57,255,20,0.5);
        margin: 12px 0;
    }

    /* --- PRONUNCIATION CHALLENGE --- */
    .pron-card {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 1px solid var(--border-cyan);
        border-radius: var(--radius-lg);
        padding: 28px 22px 22px;
        margin: 10px 0;
        text-align: center;
        box-shadow: 0 0 22px rgba(0,238,252,0.2);
        animation: slideUp 0.4s ease both;
    }
    .pron-meta {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: var(--text-dim) !important;
        margin: 0 0 8px;
    }
    .pron-meta b { color: var(--neon-cyan) !important; }
    .pron-target {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 3rem;
        font-weight: 800;
        line-height: 1;
        color: var(--neon-cyan) !important;
        text-shadow: 0 0 18px rgba(0,238,252,0.6);
        margin: 6px 0 4px;
        letter-spacing: -0.02em;
    }
    .pron-ipa {
        color: var(--text-secondary) !important;
        font-family: 'Source Sans 3', sans-serif !important;
        font-size: 1.05rem;
        margin: 0 0 6px;
        font-style: italic;
    }
    .pron-meaning {
        color: var(--text-secondary) !important;
        font-size: 0.95rem;
        margin: 0 0 16px;
    }

    .pron-result {
        margin-top: 14px;
        padding: 14px 16px;
        border-radius: var(--radius-md);
        animation: flashIn 0.4s ease both;
    }
    .pron-result-good {
        background: rgba(57,255,20,0.06);
        border: 1px solid rgba(57,255,20,0.5);
        box-shadow: 0 0 14px rgba(57,255,20,0.18);
    }
    .pron-result-mid {
        background: rgba(255,212,0,0.06);
        border: 1px solid rgba(255,212,0,0.5);
        box-shadow: 0 0 14px rgba(255,212,0,0.18);
    }
    .pron-result-bad {
        background: rgba(255,83,81,0.06);
        border: 1px solid rgba(255,83,81,0.5);
        box-shadow: 0 0 14px rgba(255,83,81,0.18);
    }
    .pron-score {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        font-size: 2.2rem;
        line-height: 1;
        margin-bottom: 4px;
    }
    .pron-result-good .pron-score { color: var(--neon-green) !important; text-shadow: 0 0 14px rgba(57,255,20,0.6); }
    .pron-result-mid  .pron-score { color: var(--neon-yellow) !important; text-shadow: 0 0 14px rgba(255,212,0,0.6); }
    .pron-result-bad  .pron-score { color: var(--neon-red) !important; text-shadow: 0 0 14px rgba(255,83,81,0.6); }
    .pron-heard {
        color: var(--text-secondary) !important;
        font-size: 0.88rem;
        margin: 6px 0 0;
    }
    .pron-heard em { color: var(--text-primary) !important; font-style: normal; font-weight: 700; }

    /* --- CONVERSATION MODE --- */
    .conv-bubble {
        max-width: 85%;
        padding: 12px 16px;
        border-radius: var(--radius-md);
        margin: 6px 0;
        animation: slideUp 0.3s ease both;
        line-height: 1.45;
        font-size: 0.95rem;
    }
    .conv-bubble.assistant {
        background: var(--bg-glass);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border-cyan);
        margin-right: auto;
        color: var(--text-primary) !important;
        box-shadow: 0 0 12px rgba(0,238,252,0.1);
    }
    .conv-bubble.user {
        background: linear-gradient(135deg, rgba(196,100,255,0.18), rgba(0,238,252,0.10));
        border: 1px solid var(--profile-accent, #c464ff);
        margin-left: auto;
        color: var(--text-primary) !important;
        text-align: right;
        box-shadow: 0 0 12px var(--profile-accent, rgba(196,100,255,0.3));
    }
    .conv-bubble .speaker {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 800;
        margin-bottom: 4px;
        opacity: 0.8;
    }
    .conv-bubble.assistant .speaker { color: var(--neon-cyan) !important; }
    .conv-bubble.user .speaker { color: var(--profile-accent, #c464ff) !important; }
    .conv-bubble .gloss {
        font-style: italic;
        color: var(--text-dim) !important;
        font-size: 0.82rem;
        display: block;
        margin-top: 4px;
    }

    /* --- ARENA / LEADERBOARD --- */
    .arena-hero {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 1px solid var(--border-cyan);
        border-radius: var(--radius-lg);
        padding: 22px 24px;
        text-align: center;
        margin-bottom: 14px;
        box-shadow: 0 0 24px rgba(0,238,252,0.12);
        position: relative; overflow: hidden;
    }
    .arena-hero h2 {
        background: linear-gradient(135deg, #ff5351, #c464ff, #00eefc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; color: transparent !important;
        font-size: 1.7rem; margin: 0 0 4px 0;
        letter-spacing: -0.02em;
    }
    .arena-hero p { color: var(--text-secondary) !important; margin: 0; font-size: 0.85rem; }

    .leaderboard-row {
        display: flex; align-items: center; gap: 14px;
        background: var(--bg-glass);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-md);
        padding: 12px 16px;
        margin-bottom: 8px;
        transition: var(--t-base);
        animation: cardReveal 0.4s ease both;
    }
    .leaderboard-row:hover { transform: translateX(4px); border-color: var(--border-cyan); }
    .leaderboard-row.is-self {
        border-color: var(--profile-accent, #ff5351);
        box-shadow: 0 0 16px var(--profile-accent, #ff5351);
        background: rgba(255,255,255,0.03);
    }
    .leaderboard-row.rank-1 { border-color: rgba(255,212,0,0.5); box-shadow: 0 0 18px rgba(255,212,0,0.25); }
    .leaderboard-row.rank-2 { border-color: rgba(192,200,210,0.4); }
    .leaderboard-row.rank-3 { border-color: rgba(205,127,50,0.5); }

    .lb-rank {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800; font-size: 1.4rem;
        width: 36px; text-align: center;
        color: var(--text-secondary) !important;
    }
    .leaderboard-row.rank-1 .lb-rank { color: #ffd400 !important; text-shadow: 0 0 10px #ffd400; }
    .leaderboard-row.rank-2 .lb-rank { color: #c0c8d2 !important; text-shadow: 0 0 8px #c0c8d2; }
    .leaderboard-row.rank-3 .lb-rank { color: #cd7f32 !important; text-shadow: 0 0 8px #cd7f32; }

    .lb-avatar img {
        width: 44px; height: 44px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid var(--lb-accent, #00eefc);
        box-shadow: 0 0 12px var(--lb-accent, #00eefc);
        background: var(--bg-mid);
    }
    .lb-avatar-fallback {
        width: 44px; height: 44px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.4rem;
        background: var(--bg-mid);
        border: 2px solid var(--lb-accent, #00eefc);
        box-shadow: 0 0 12px var(--lb-accent, #00eefc);
    }
    .lb-info { flex: 1; min-width: 0; }
    .lb-name {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800; font-size: 1rem;
        color: var(--lb-accent, #ffffff) !important;
        text-shadow: 0 0 8px var(--lb-accent, transparent);
        margin: 0;
    }
    .lb-meta {
        font-size: 0.75rem;
        color: var(--text-dim) !important;
        margin: 2px 0 0 0;
        text-transform: uppercase; letter-spacing: 0.8px;
    }
    .lb-xp {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        text-align: right;
    }
    .lb-xp-num {
        font-size: 1.2rem;
        color: var(--neon-yellow) !important;
        text-shadow: 0 0 10px rgba(255,212,0,0.5);
        line-height: 1;
    }
    .lb-xp-label {
        font-size: 0.65rem;
        color: var(--text-dim) !important;
        text-transform: uppercase; letter-spacing: 1px;
        margin-top: 2px;
    }

    /* --- PROFILE VIEW --- */
    .cefr-card {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 1px solid var(--profile-accent, #ff5351);
        border-radius: var(--radius-lg);
        padding: 24px;
        text-align: center;
        margin-bottom: 14px;
        box-shadow: 0 0 24px var(--profile-accent, #ff5351);
        position: relative; overflow: hidden;
    }
    .cefr-level {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 4rem; font-weight: 800; line-height: 0.95;
        color: var(--profile-accent, #ff5351) !important;
        text-shadow: 0 0 20px var(--profile-accent, #ff5351);
        letter-spacing: -0.03em;
        margin: 0;
    }
    .cefr-rank-name {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700;
        color: var(--text-primary) !important;
        font-size: 1.1rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin: 4px 0 0;
    }
    .cefr-rank-tagline {
        color: var(--text-secondary) !important;
        font-size: 0.85rem;
        margin: 6px 0 14px;
    }
    .cefr-progress-wrap {
        background: rgba(255,255,255,0.06);
        border: 1px solid var(--border-soft);
        border-radius: 50px;
        height: 10px;
        overflow: hidden;
        margin: 8px 0;
    }
    .cefr-progress-fill {
        height: 100%; border-radius: 50px;
        background: linear-gradient(90deg, var(--profile-accent, #ff5351), #00eefc);
        box-shadow: 0 0 12px var(--profile-accent, #ff5351);
        transition: width 1s ease;
    }
    .cefr-next {
        font-size: 0.75rem;
        color: var(--text-dim) !important;
        text-transform: uppercase; letter-spacing: 1px;
    }

    .trophy-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
        gap: 10px;
        margin-top: 10px;
    }
    .trophy-card {
        background: var(--bg-glass);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-md);
        padding: 14px 8px;
        text-align: center;
        transition: var(--t-base);
        opacity: 0.35;
        filter: grayscale(0.8);
    }
    .trophy-card.earned {
        opacity: 1;
        filter: none;
        border-color: var(--trophy-accent, #ffd400);
        box-shadow: 0 0 14px var(--trophy-accent, #ffd400);
    }
    .trophy-card .trophy-icon {
        font-size: 2rem;
        display: block;
        margin-bottom: 4px;
    }
    .trophy-card .trophy-name {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700;
        font-size: 0.72rem;
        color: var(--text-primary) !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        line-height: 1.2;
    }
    .trophy-card .trophy-desc {
        font-size: 0.66rem;
        color: var(--text-dim) !important;
        margin-top: 2px;
        line-height: 1.2;
    }

    .skill-row {
        display: flex; align-items: center; gap: 12px;
        margin-bottom: 8px;
    }
    .skill-label {
        flex: 0 0 90px;
        font-size: 0.78rem;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    .skill-bar {
        flex: 1;
        background: rgba(255,255,255,0.05);
        border: 1px solid var(--border-soft);
        border-radius: 50px;
        height: 8px;
        overflow: hidden;
    }
    .skill-bar-fill {
        height: 100%; border-radius: 50px;
        box-shadow: 0 0 10px currentColor;
    }
    .skill-pct {
        flex: 0 0 38px;
        text-align: right;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700;
        font-size: 0.78rem;
        color: var(--text-primary) !important;
    }

    /* --- WORLDS GRID (mapa de mundos) --- */
    .worlds-section-title {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: var(--neon-cyan) !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-size: 0.85rem;
        margin: 18px 0 10px;
        text-align: center;
        text-shadow: 0 0 10px rgba(0,238,252,0.4);
    }
    .worlds-section-title::before, .worlds-section-title::after {
        content: "◆"; margin: 0 10px;
        color: var(--neon-cyan); opacity: 0.6;
    }

    .world-card {
        background: var(--bg-glass);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-lg);
        padding: 18px 18px 14px;
        margin-bottom: 10px;
        position: relative;
        overflow: hidden;
        animation: cardReveal 0.5s ease both;
        transition: var(--t-base);
        cursor: default;
    }
    .world-card::before {
        content: ""; position: absolute; inset: 0; border-radius: var(--radius-lg);
        padding: 1px; pointer-events: none;
        background: linear-gradient(135deg, var(--world-accent, #00eefc) 0%, transparent 60%);
        -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
        -webkit-mask-composite: xor; mask-composite: exclude; opacity: 0.6;
    }
    .world-card-header {
        display: flex; align-items: center; gap: 12px; margin-bottom: 8px;
    }
    .world-icon {
        width: 44px; height: 44px;
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.5rem;
        background: rgba(255,255,255,0.04);
        border: 1px solid var(--world-accent, #00eefc);
        box-shadow: 0 0 14px var(--world-accent, #00eefc);
        flex-shrink: 0;
    }
    .world-name {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800; font-size: 1.05rem; line-height: 1.2;
        color: var(--world-accent, #00eefc) !important;
        text-shadow: 0 0 8px var(--world-accent, #00eefc);
        margin: 0;
    }
    .world-tagline {
        font-size: 0.78rem; color: var(--text-secondary) !important;
        margin: 2px 0 0 0; line-height: 1.3;
    }
    .world-card .stButton { margin-top: 10px; }
    .world-card .stButton > button {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid var(--world-accent, #00eefc) !important;
        color: var(--world-accent, #00eefc) !important;
        box-shadow: 0 0 10px rgba(0,0,0,0.2) !important;
        font-size: 0.85rem !important;
        padding: 8px 16px !important;
    }
    .world-card .stButton > button:hover {
        background: rgba(255,255,255,0.06) !important;
        box-shadow: 0 0 18px var(--world-accent, #00eefc) !important;
        text-shadow: 0 0 6px var(--world-accent, #00eefc);
    }

    /* --- VOICE COMM PANEL --- */
    .voice-comm {
        background: var(--bg-glass);
        backdrop-filter: blur(15px);
        border: 1px solid var(--border-cyan);
        border-radius: var(--radius-lg);
        padding: 18px 20px;
        margin-top: 10px;
        box-shadow: 0 0 14px rgba(0,238,252,0.08);
    }
    .voice-comm-title {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800;
        color: var(--neon-cyan) !important;
        text-shadow: 0 0 10px rgba(0,238,252,0.4);
        font-size: 0.95rem;
        margin: 0 0 4px 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .voice-comm-sub {
        color: var(--text-secondary) !important;
        font-size: 0.82rem;
        margin: 0 0 10px 0;
    }

    /* --- DASHBOARD HEADER --- */
    .dashboard-header {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid var(--border-soft);
        border-left: 3px solid var(--profile-accent, #ff5351);
        border-radius: var(--radius-lg);
        padding: 18px 22px;
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 14px;
        box-shadow: 0 0 24px rgba(0,0,0,0.3), 0 0 18px var(--profile-accent-glow, rgba(255,83,81,0.2));
        position: relative; overflow: hidden;
    }
    .dashboard-header h2 {
        margin: 0; font-size: 1.5rem;
        color: var(--profile-accent, #ffb3ae) !important;
        text-shadow: 0 0 14px var(--profile-accent, #ff5351);
    }
    .dashboard-header .xp-display {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800; font-size: 1.1rem;
        color: var(--neon-yellow) !important;
        text-shadow: 0 0 10px rgba(255,212,0,0.55);
        padding: 6px 14px;
        background: rgba(255,212,0,0.08);
        border: 1px solid rgba(255,212,0,0.3);
        border-radius: 50px;
    }

    /* --- PANEL DE PROGRESO --- */
    .progress-panel {
        background: var(--bg-glass);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-lg);
        padding: 16px 18px;
        margin-bottom: 18px;
        display: flex; justify-content: space-around; align-items: center;
        flex-wrap: wrap; gap: 8px;
    }
    .stat-item { text-align: center; padding: 4px 10px; }
    .stat-value {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 1.5rem; font-weight: 800; line-height: 1.1;
        color: var(--text-primary) !important;
    }
    .stat-label {
        font-size: 0.66rem; color: var(--text-dim) !important;
        text-transform: uppercase; letter-spacing: 1.2px;
        font-weight: 700; margin-top: 4px;
    }
    .stat-divider {
        width: 1px; height: 32px;
        background: linear-gradient(180deg, transparent, rgba(255,255,255,0.12), transparent);
    }

    /* --- SECCIÓN DE AUDIO --- */
    .audio-section {
        background: var(--bg-glass);
        backdrop-filter: blur(15px);
        border: 1px solid var(--border-cyan);
        border-radius: var(--radius-md);
        padding: 16px 20px; margin: 14px 0;
        box-shadow: 0 0 14px rgba(0,238,252,0.1);
    }
    .audio-section p {
        margin: 0 0 10px 0;
        font-size: 0.88rem;
        color: var(--neon-cyan-soft) !important;
    }

    /* --- BADGE DE INTENTOS --- */
    .attempts-badge {
        display: inline-block;
        background: rgba(255,212,0,0.1);
        border: 1px solid rgba(255,212,0,0.4);
        border-radius: 50px;
        padding: 3px 12px;
        font-size: 0.78rem; font-weight: 700;
        color: var(--neon-yellow) !important;
        margin-left: 8px; vertical-align: middle;
        box-shadow: 0 0 8px rgba(255,212,0,0.2);
    }
    .attempts-badge-danger {
        background: rgba(255,83,81,0.1);
        border-color: rgba(255,83,81,0.5);
        color: var(--neon-red-soft) !important;
        box-shadow: 0 0 10px rgba(255,83,81,0.25);
    }

    /* --- CONTENEDOR DE LECCIÓN --- */
    .lesson-container {
        background: var(--bg-glass);
        backdrop-filter: blur(15px);
        border: 1px solid var(--border-soft);
        border-left: 3px solid var(--profile-accent, #ff5351);
        padding: 26px 28px;
        border-radius: var(--radius-md);
        line-height: 1.7;
        animation: slideUp 0.4s ease both;
        box-shadow: 0 0 24px rgba(0,0,0,0.25);
    }
    .lesson-container, .lesson-container p, .lesson-container li {
        color: var(--text-primary) !important;
    }
    .lesson-container h3 {
        color: var(--profile-accent, #ffb3ae) !important;
        text-shadow: 0 0 10px var(--profile-accent, #ff5351);
        margin-top: 18px;
    }
    .lesson-container strong { color: var(--neon-cyan) !important; }
    .lesson-container em     { color: var(--neon-purple-soft) !important; }
    .lesson-container code   {
        background: var(--bg-high); color: var(--neon-cyan) !important;
        padding: 1px 6px; border-radius: 4px; font-size: 0.92em;
    }

    /* --- QUIZ --- */
    .quiz-container {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 1px solid var(--border-soft);
        border-left: 3px solid var(--profile-accent, #ff5351);
        padding: 24px 28px;
        border-radius: var(--radius-md);
        animation: slideUp 0.45s ease both;
        margin-top: 8px;
        box-shadow: 0 0 24px rgba(0,0,0,0.25);
    }
    .quiz-container h3 {
        color: var(--profile-accent, #ffb3ae) !important;
        margin-bottom: 4px;
        text-shadow: 0 0 10px var(--profile-accent, #ff5351);
    }

    .question-card {
        background: var(--bg-low);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-sm);
        padding: 16px 18px;
        margin-bottom: 14px;
        transition: var(--t-base);
    }
    .question-card:hover {
        border-color: var(--border-cyan);
        box-shadow: 0 0 14px rgba(0,238,252,0.12);
    }
    .question-card p {
        margin: 0 0 10px 0; font-weight: 600;
        color: var(--text-primary) !important;
    }

    .q-badge {
        display: inline-block;
        background: linear-gradient(135deg, var(--neon-purple), var(--neon-cyan));
        color: var(--text-on-neon) !important;
        font-size: 0.68rem; font-weight: 800;
        padding: 3px 10px;
        border-radius: 50px;
        margin-bottom: 8px;
        letter-spacing: 1px;
        text-transform: uppercase;
        box-shadow: 0 0 10px rgba(196,100,255,0.35);
    }

    .quiz-section-title {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 1rem; font-weight: 800;
        color: var(--neon-cyan) !important;
        margin: 22px 0 12px 0;
        padding-bottom: 6px;
        border-bottom: 1px solid var(--border-cyan);
        text-transform: uppercase;
        letter-spacing: 1.5px;
        text-shadow: 0 0 10px rgba(0,238,252,0.4);
    }

    /* --- RESULT PANEL --- */
    .result-panel {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(15px);
        border: 1px solid;
        border-radius: var(--radius-md);
        padding: 26px 28px;
        text-align: center;
        animation: slideUp 0.4s ease both;
        margin-top: 8px;
    }
    .result-panel h2 {
        font-size: 1.7rem !important; margin-bottom: 4px;
    }
    .result-panel .score-number {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 3.4rem; font-weight: 800; line-height: 1;
        margin: 8px 0;
    }
    .result-pass {
        border-color: rgba(57,255,20,0.4);
        box-shadow: 0 0 30px rgba(57,255,20,0.18);
    }
    .result-pass h2, .result-pass .score-number {
        color: var(--neon-green) !important;
        text-shadow: 0 0 18px rgba(57,255,20,0.55);
    }
    .result-fail {
        border-color: rgba(255,212,0,0.4);
        box-shadow: 0 0 28px rgba(255,212,0,0.16);
    }
    .result-fail h2, .result-fail .score-number {
        color: var(--neon-yellow) !important;
        text-shadow: 0 0 18px rgba(255,212,0,0.5);
    }
    .result-blocked {
        border-color: rgba(255,83,81,0.5);
        box-shadow: 0 0 28px rgba(255,83,81,0.2);
    }
    .result-blocked h2, .result-blocked .score-number {
        color: var(--neon-red) !important;
        text-shadow: 0 0 18px rgba(255,83,81,0.55);
    }

    .feedback-row {
        background: var(--bg-low);
        border-radius: var(--radius-sm);
        padding: 12px 14px;
        margin-bottom: 8px;
        border-left: 3px solid;
        text-align: left;
        font-size: 0.88rem;
        color: var(--text-primary) !important;
    }
    .feedback-correct {
        border-color: var(--neon-green);
        box-shadow: 0 0 8px rgba(57,255,20,0.15);
    }
    .feedback-wrong {
        border-color: var(--neon-red);
        box-shadow: 0 0 8px rgba(255,83,81,0.15);
    }
    .feedback-row strong { color: var(--neon-cyan) !important; }

    .score-bar-wrap {
        background: rgba(255,255,255,0.06);
        border-radius: 50px;
        height: 12px;
        margin: 14px 0;
        overflow: hidden;
        border: 1px solid var(--border-soft);
    }
    .score-bar-fill {
        height: 100%; border-radius: 50px;
        transition: width 1s ease;
        box-shadow: 0 0 12px currentColor;
    }

    /* --- SAVE ERROR BANNER (cuando falla guardar en Sheets) --- */
    .save-error-banner {
        background: rgba(255,83,81,0.10);
        backdrop-filter: blur(15px);
        border: 2px solid var(--neon-red);
        border-radius: var(--radius-lg);
        padding: 22px 24px;
        margin: 14px 0;
        box-shadow: 0 0 32px rgba(255,83,81,0.35);
        animation: cardReveal 0.5s ease both;
    }
    .save-error-banner h3 {
        color: var(--neon-red) !important;
        text-shadow: 0 0 12px rgba(255,83,81,0.6);
        margin: 0 0 10px;
        font-size: 1.2rem;
    }
    .save-error-banner p, .save-error-banner li {
        color: var(--text-primary) !important;
        line-height: 1.5;
    }
    .save-error-banner code {
        background: var(--bg-high);
        color: var(--neon-cyan) !important;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.9rem;
        word-break: break-all;
    }
    .save-error-banner .sa-email {
        display: inline-block;
        background: rgba(0,238,252,0.10);
        border: 1px solid var(--border-cyan);
        color: var(--neon-cyan) !important;
        padding: 6px 12px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 0.92rem;
        margin: 4px 0;
        text-shadow: 0 0 8px rgba(0,238,252,0.4);
        word-break: break-all;
    }

    /* --- CONNECTION STATUS PILL --- */
    .conn-pill {
        display: inline-flex; align-items: center; gap: 6px;
        background: var(--bg-glass);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border-soft);
        border-radius: 50px;
        padding: 4px 12px;
        font-size: 0.74rem;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
        margin: 4px 4px 4px 0;
    }
    .conn-pill.ok    { color: var(--neon-green) !important; border-color: rgba(57,255,20,0.4); box-shadow: 0 0 8px rgba(57,255,20,0.18); }
    .conn-pill.fail  { color: var(--neon-red)   !important; border-color: rgba(255,83,81,0.5);  box-shadow: 0 0 8px rgba(255,83,81,0.22); }
    .conn-pill.warn  { color: var(--neon-yellow)!important; border-color: rgba(255,212,0,0.5);  box-shadow: 0 0 8px rgba(255,212,0,0.22); }

    /* --- BANNERS --- */
    .error-banner {
        background: rgba(255,83,81,0.08);
        border: 1px solid rgba(255,83,81,0.4);
        border-left: 3px solid var(--neon-red);
        border-radius: var(--radius-sm);
        padding: 14px 18px; margin: 12px 0;
        color: var(--neon-red-soft) !important;
        font-size: 0.9rem;
        box-shadow: 0 0 14px rgba(255,83,81,0.12);
    }
    .warning-banner {
        background: rgba(255,212,0,0.08);
        border: 1px solid rgba(255,212,0,0.4);
        border-left: 3px solid var(--neon-yellow);
        border-radius: var(--radius-sm);
        padding: 14px 18px; margin: 12px 0;
        color: var(--neon-yellow) !important;
        font-size: 0.9rem;
        box-shadow: 0 0 12px rgba(255,212,0,0.12);
    }

    /* --- INPUTS --- */
    .stRadio > div { gap: 6px !important; }
    .stRadio label, .stRadio div[role="radiogroup"] label {
        color: var(--text-primary) !important;
    }
    .stRadio div[role="radiogroup"] > label {
        background: var(--bg-low);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-sm);
        padding: 8px 12px !important;
        transition: var(--t-base);
    }
    .stRadio div[role="radiogroup"] > label:hover {
        border-color: var(--border-cyan);
        background: rgba(0,238,252,0.04);
    }

    .stTextInput input, .stChatInput textarea, [data-testid="stChatInput"] textarea {
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--border-soft) !important;
        background-color: var(--bg-low) !important;
        color: var(--text-primary) !important;
        font-family: 'Source Sans 3', sans-serif !important;
        caret-color: var(--neon-cyan) !important;
    }
    .stTextInput input::placeholder, .stChatInput textarea::placeholder {
        color: var(--text-dim) !important;
        opacity: 1 !important;
    }
    .stTextInput input:focus, .stChatInput textarea:focus {
        border-color: var(--neon-cyan) !important;
        box-shadow: 0 0 0 1px rgba(0,238,252,0.3), 0 0 14px rgba(0,238,252,0.2) !important;
        background-color: var(--bg-mid) !important;
    }

    /* --- FORM, EXPANDER, CAPTION, ALERTS --- */
    [data-testid="stForm"] { border: none !important; padding: 0 !important; }

    [data-testid="stExpander"] {
        background: var(--bg-glass);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border-soft) !important;
        border-radius: var(--radius-sm) !important;
    }
    [data-testid="stExpander"] summary { color: var(--neon-cyan) !important; }

    /* Panel de diagnóstico manual (reemplaza st.expander) */
    .diag-panel {
        background: var(--bg-glass);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-sm);
        padding: 14px 16px;
        margin: 6px 0 12px;
    }

    .stCaption, [data-testid="stCaptionContainer"], small {
        color: var(--text-dim) !important;
    }

    [data-testid="stAlert"] {
        background: var(--bg-glass) !important;
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--border-soft) !important;
    }

    .stSpinner > div { border-top-color: var(--neon-cyan) !important; }

    hr { border-color: var(--border-soft) !important; opacity: 0.5; }

    /* --- HELPERS --- */
    .help-text, .section-title {
        color: var(--text-primary) !important;
        font-weight: 700;
    }
    .section-title {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: var(--neon-cyan) !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 1.05rem;
    }

    /* --- ANIMACIONES --- */
    @keyframes cardReveal {
        from { opacity: 0; transform: translateY(20px) scale(0.96); }
        to   { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes fadeIn  { from { opacity: 0; } to { opacity: 1; } }
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(16px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes floatY { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
    @keyframes pulse  { 0%,100% { opacity: 1; } 50% { opacity: 0.55; } }
    @keyframes scan   { 0% { background-position: -120% 0; } 100% { background-position: 220% 0; } }
    @keyframes breathe { 0%,100% { box-shadow: 0 0 8px rgba(255,212,0,0.3); } 50% { box-shadow: 0 0 16px rgba(255,212,0,0.55); } }
    @keyframes flashIn { from { opacity: 0; transform: scale(0.96); } to { opacity: 1; transform: scale(1); } }

    div[data-testid="column"]:nth-child(1) .profile-card { animation-delay: 0.0s; }
    div[data-testid="column"]:nth-child(2) .profile-card { animation-delay: 0.1s; }
    div[data-testid="column"]:nth-child(3) .profile-card { animation-delay: 0.2s; }

    /* --- RESPONSIVE --- */
    @media (max-width: 640px) {
        .welcome-container h1 { font-size: 2rem; }
        .dashboard-header { flex-direction: column; gap: 8px; text-align: center; }
        .quiz-container, .lesson-container { padding: 18px; }
        .result-panel { padding: 20px; }
        .progress-panel { flex-direction: column; gap: 4px; }
    }

    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. CONTEXTO FAMILIAR Y PERFILES
# ==========================================

AVATAR_BASE_URL = "https://raw.githubusercontent.com/jccubillos/idiomaconnect/main"

PROFILES = {
    # ── Hijas de Juan Carlos ─────────────────────────────────────────────
    "Antonia": {
        "color": "#c464ff",
        "gradient": "linear-gradient(135deg, #c464ff, #7000a7)",
        "emoji": "🎨",
        "avatar": f"{AVATAR_BASE_URL}/antonia.png",
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
        "color": "#00eefc",
        "gradient": "linear-gradient(135deg, #00eefc, #00686f)",
        "emoji": "🎹",
        "avatar": f"{AVATAR_BASE_URL}/belen.png",
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
        "color": "#39ff14",
        "gradient": "linear-gradient(135deg, #39ff14, #1d8c00)",
        "emoji": "🤸",
        "avatar": f"{AVATAR_BASE_URL}/sofia.png",
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
        "color": "#ff5351",
        "gradient": "linear-gradient(135deg, #ff5351, #93000a)",
        "emoji": "✈️",
        "avatar": f"{AVATAR_BASE_URL}/agustin.png",
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
        "color": "#ffd400",
        "gradient": "linear-gradient(135deg, #ffd400, #b38f00)",
        "emoji": "🎮",
        "avatar": f"{AVATAR_BASE_URL}/maximo.png",
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
        "color": "#ff66c4",
        "gradient": "linear-gradient(135deg, #ff66c4, #880e4f)",
        "emoji": "🎻",
        "avatar": f"{AVATAR_BASE_URL}/antonela.png",
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
# MUNDOS PERSONALES (uno por perfil, basado en hobbies)
# ==========================================
PERSONAL_WORLDS = {
    "Antonia": {
        "emoji": "🎨",
        "name": "Galería de Arte",
        "tagline": "Pintura, museos y emociones en colores",
        "topic": (
            "Vocabulario del mundo del arte y la pintura: colores, técnicas, materiales "
            "(brush, canvas, easel, palette), tipos de obras, museos famosos, expresar "
            "emociones a través del arte. Incluye también algo de vocabulario de tenis "
            "(racket, court, serve) en al menos un ejemplo."
        ),
    },
    "Belen": {
        "emoji": "🎼",
        "name": "Sala de Conciertos",
        "tagline": "Notas, escenarios y vibras musicales",
        "topic": (
            "Vocabulario musical en inglés: instrumentos (piano, keys, chords), notas, "
            "composición, partituras, conciertos, sentimientos al tocar. Verbos clave: "
            "play, practice, perform, compose. Usa ejemplos en escenarios y conciertos."
        ),
    },
    "Sofia": {
        "emoji": "🤸",
        "name": "Arena Olímpica",
        "tagline": "Movimiento, disciplina y récords",
        "topic": (
            "Vocabulario deportivo: gimnasia, partes del cuerpo en movimiento, posiciones "
            "(handstand, cartwheel, balance beam), competencia, entrenamiento, esfuerzo y "
            "disciplina. Verbos: stretch, jump, flip, train. Ejemplos en torneos y rutinas."
        ),
    },
    "Agustin": {
        "emoji": "✈️",
        "name": "Cabina de Vuelo",
        "tagline": "Aeronaves, salud y misiones aéreas",
        "topic": (
            "Vocabulario de aviación militar (aircraft, cockpit, runway, mission, squadron) "
            "y medicina básica (doctor, patient, hospital, heart, lungs). Mezcla con "
            "vocabulario de fútbol (goal, pass, midfielder) en al menos un ejemplo. "
            "Tono motivador, metas grandes."
        ),
    },
    "Maximo": {
        "emoji": "🎮",
        "name": "Sala de Boss Battle",
        "tagline": "Niveles, ítems y misiones épicas",
        "topic": (
            "Vocabulario de videojuegos: levels, items, quests, achievements, characters, "
            "boss, power-up, respawn, leaderboard. Combina con vocabulario de medicina "
            "(doctor, medicine, healthy) en al menos un ejemplo, y un guiño al fútbol."
        ),
    },
    "Antonela": {
        "emoji": "🏕️",
        "name": "Campamento Sinfónico",
        "tagline": "Naturaleza, violín y trabajo en equipo",
        "topic": (
            "Vocabulario de naturaleza (forest, lake, mountain, river, campfire), scouts y "
            "trabajo en equipo (teamwork, mission, helping). Incluye términos del violín "
            "(bow, strings, melody) y del basquetbol (court, team, dribble) en ejemplos."
        ),
    },
}


# ==========================================
# CATÁLOGO DE MUNDOS UNIVERSALES
# ==========================================
# ==========================================
# CÁPSULA CULTURAL — Idioms, frases de canciones, datos
# ==========================================
CULTURAL_IDIOMS = [
    {"en": "It's raining cats and dogs", "es": "Está lloviendo a cántaros"},
    {"en": "Break a leg!", "es": "¡Mucha suerte! (especialmente para artistas)"},
    {"en": "Piece of cake", "es": "Pan comido / Muy fácil"},
    {"en": "Hit the books", "es": "Ponerse a estudiar duro"},
    {"en": "Under the weather", "es": "Sentirse mal/enfermo"},
    {"en": "Once in a blue moon", "es": "Muy de vez en cuando"},
    {"en": "Cost an arm and a leg", "es": "Costar un ojo de la cara"},
    {"en": "Bite the bullet", "es": "Apechugar / Aguantarse"},
    {"en": "Spill the beans", "es": "Soltar el secreto"},
    {"en": "Hit the nail on the head", "es": "Dar en el clavo"},
    {"en": "When pigs fly", "es": "Cuando las ranas críen pelo (= nunca)"},
    {"en": "A blessing in disguise", "es": "No hay mal que por bien no venga"},
    {"en": "Call it a day", "es": "Dejarlo por hoy"},
    {"en": "Hang in there", "es": "Aguanta / No te rindas"},
    {"en": "Out of the blue", "es": "De la nada / Inesperadamente"},
    {"en": "Get your act together", "es": "Ponte las pilas"},
    {"en": "Better late than never", "es": "Más vale tarde que nunca"},
    {"en": "Don't judge a book by its cover", "es": "Las apariencias engañan"},
    {"en": "Speak of the devil!", "es": "¡Hablando del rey de Roma!"},
    {"en": "The early bird catches the worm", "es": "Al que madruga, Dios lo ayuda"},
]

CULTURAL_SONGS = [
    {"line": "Yesterday, all my troubles seemed so far away", "song": "Yesterday — The Beatles"},
    {"line": "We don't need no education", "song": "Another Brick in the Wall — Pink Floyd"},
    {"line": "I want to break free", "song": "I Want to Break Free — Queen"},
    {"line": "Don't stop believin'", "song": "Don't Stop Believin' — Journey"},
    {"line": "Let it be, let it be", "song": "Let It Be — The Beatles"},
    {"line": "I will always love you", "song": "I Will Always Love You — Whitney Houston"},
    {"line": "Hello, is it me you're looking for?", "song": "Hello — Lionel Richie"},
    {"line": "Shake it off, shake it off", "song": "Shake It Off — Taylor Swift"},
    {"line": "I'm walking on sunshine", "song": "Walking on Sunshine — Katrina & The Waves"},
    {"line": "Don't worry, be happy", "song": "Don't Worry Be Happy — Bobby McFerrin"},
    {"line": "Someone like you", "song": "Someone Like You — Adele"},
    {"line": "Imagine all the people living life in peace", "song": "Imagine — John Lennon"},
    {"line": "I gotta feeling that tonight's gonna be a good night", "song": "I Gotta Feeling — Black Eyed Peas"},
    {"line": "Photograph, I won't ever let you go", "song": "Photograph — Ed Sheeran"},
    {"line": "We are the champions, my friends", "song": "We Are the Champions — Queen"},
]

CULTURAL_FACTS = [
    {"en": "English has over 170,000 words in current use.", "es": "El inglés tiene más de 170,000 palabras en uso actual."},
    {"en": "Shakespeare invented over 1,700 English words still used today.", "es": "Shakespeare inventó más de 1,700 palabras del inglés que todavía usamos."},
    {"en": "The most common letter in English is 'E'.", "es": "La letra más común en inglés es la 'E'."},
    {"en": "'Set' has the most definitions of any English word — over 430.", "es": "'Set' es la palabra inglesa con más significados: más de 430."},
    {"en": "English is the official language of the sky — all pilots speak it.", "es": "El inglés es el idioma oficial del cielo: todos los pilotos lo hablan."},
    {"en": "The dot over the letter 'i' is called a 'tittle'.", "es": "El puntito sobre la 'i' se llama 'tittle' en inglés."},
    {"en": "'Pneumonoultramicroscopicsilicovolcanoconiosis' is the longest English word.", "es": "La palabra más larga del inglés tiene 45 letras (es un tipo de enfermedad pulmonar)."},
    {"en": "About 1.5 BILLION people speak English worldwide.", "es": "Cerca de 1,500 millones de personas hablan inglés en el mundo."},
    {"en": "Only 400 million speak English as a first language.", "es": "Solo 400 millones tienen el inglés como lengua materna."},
    {"en": "'Goodbye' originally meant 'God be with you'.", "es": "'Goodbye' originalmente significaba 'God be with you' (Dios esté contigo)."},
    {"en": "The longest word without a vowel is 'rhythms'.", "es": "La palabra más larga sin vocales en inglés es 'rhythms'."},
    {"en": "'I am' is the shortest complete sentence in English.", "es": "'I am' es la oración completa más corta del inglés."},
    {"en": "Many Spanish speakers use 'actually' wrong — it means 'really', not 'currently'.", "es": "Muchos hispanohablantes confunden 'actually': significa 'realmente', NO 'actualmente'."},
    {"en": "'Library' (biblioteca) ≠ 'librería' (bookstore). They are 'false friends'.", "es": "'Library' es BIBLIOTECA, no librería. La librería se dice 'bookstore'."},
    {"en": "'Embarrassed' (avergonzado) ≠ 'embarazada' (pregnant). Be careful!", "es": "'Embarrassed' es AVERGONZADO, no embarazada. ¡Cuidado al traducir!"},
]


def get_cultural_capsule_for_today() -> dict:
    """Devuelve la cápsula del día (idiom + song + dato) basada en day-of-year."""
    today = datetime.date.today()
    doy = today.timetuple().tm_yday
    return {
        "idiom": CULTURAL_IDIOMS[doy % len(CULTURAL_IDIOMS)],
        "song":  CULTURAL_SONGS[doy % len(CULTURAL_SONGS)],
        "fact":  CULTURAL_FACTS[doy % len(CULTURAL_FACTS)],
    }


UNIVERSAL_WORLDS = {
    "grammar": {
        "emoji":   "🌌",
        "name":    "Galaxia Gramatical",
        "tagline": "Reglas, estructuras y patrones del inglés",
        "intro":   ("Bienvenida al sector galáctico de la gramática. Aquí decodificarás "
                    "las reglas que rigen el universo del idioma inglés."),
        "accent":  "#c464ff",
        "topic":   "Aventura Diaria (Reglas gramaticales divertidas y estructuradas)",
    },
    "vocab": {
        "emoji":   "📚",
        "name":    "Bóveda de Vocabulario",
        "tagline": "Palabras nuevas, adjetivos, objetos cotidianos",
        "intro":   ("Has accedido a la cámara acorazada de palabras. Cada misión "
                    "expande tu inventario lingüístico con vocabulario práctico."),
        "accent":  "#00eefc",
        "topic":   ("Vocabulario Práctico (Aprender palabras nuevas, adjetivos, "
                    "objetos de la casa, direcciones como arriba/abajo o verbos de "
                    "acción simple. PROHIBIDO usar gramática compleja o densa, "
                    "enfócate 100% en ampliar su vocabulario y mostrar el "
                    "significado de las palabras)"),
    },
    "challenge": {
        "emoji":   "⚔️",
        "name":    "Desafío Sorpresa",
        "tagline": "La IA elige el reto perfecto para hoy",
        "intro":   ("Modo aleatorio activado. La IA seleccionará un desafío "
                    "sorpresivo conectado con tu edad e intereses. ¿Listo/a?"),
        "accent":  "#ff5351",
        "topic":   ("Reto Sorpresa: la IA elige libremente entre gramática avanzada, "
                    "vocabulario temático, expresiones idiomáticas o phrasal verbs. "
                    "Debe ser un tema que sorprenda, sea desafiante pero alcanzable, "
                    "y conectado con la edad e intereses del/la alumno/a."),
    },
    "sound": {
        "emoji":   "🎙",
        "name":    "Estudio de Sonido",
        "tagline": "Escucha, distingue y pronuncia sonidos del inglés",
        "intro":   ("Bienvenida al estudio acústico. Aquí entrenarás tu oído y "
                    "tu voz: los sonidos que los hispanohablantes confunden, "
                    "las palabras gemelas, y las pronunciaciones difíciles."),
        "accent":  "#39ff14",
        "topic":   ("Pronunciación y comprensión auditiva: sonidos difíciles del inglés "
                    "(th, r final, vocales i/ee), pares mínimos, palabras de uso cotidiano "
                    "para entrenar el oído y la voz."),
    },
    "chat": {
        "emoji":   "💬",
        "name":    "Café Conversación",
        "tagline": "Practica situaciones reales con misiones de role-play",
        "intro":   ("Bienvenida al café donde se habla inglés. Elige un escenario "
                    "real (pedir comida, viajar, conocer gente) y completa misiones "
                    "conversando con la IA."),
        "accent":  "#c464ff",
        "topic":   ("Conversación práctica en situaciones cotidianas: restaurantes, "
                    "viajes, escuela, presentaciones, opiniones simples."),
    },
    "writing": {
        "emoji":   "🖋",
        "name":    "Taller de Letras",
        "tagline": "Traduce, describe y escribe en inglés",
        "intro":   ("Bienvenida al taller donde tus ideas se vuelven palabras en "
                    "inglés. Aquí entrenas la habilidad más exigente: producir "
                    "tu propio texto y recibir feedback línea por línea."),
        "accent":  "#ff66c4",
        "topic":   ("Escritura productiva en inglés: traducir oraciones del español "
                    "al inglés y describir escenas con propias palabras."),
    },
    "journal": {
        "emoji":   "📔",
        "name":    "Diario Hablado",
        "tagline": "Habla 30 segundos sobre el prompt del día",
        "intro":   ("El reto más cercano a hablar inglés real. Cada día un tema "
                    "diferente — habla libre, sin guión, y recibe feedback "
                    "personalizado sobre tu fluidez, vocabulario y gramática."),
        "accent":  "#00eefc",
        "topic":   ("Producción oral espontánea: hablar 30 segundos sobre un tema "
                    "cotidiano sin guión preestablecido."),
    },
}


def get_world_meta(world_key: str, profile_name: str) -> dict:
    """Devuelve el meta del mundo. Para 'personal' arma uno desde PERSONAL_WORLDS."""
    if world_key == "personal":
        pw = PERSONAL_WORLDS.get(profile_name)
        accent = PROFILES.get(profile_name, {}).get("color", "#ff66c4")
        if pw:
            return {
                "emoji":   pw["emoji"],
                "name":    pw["name"],
                "tagline": pw["tagline"],
                "intro":   ("Tu mundo personal te espera. Aquí cada misión está "
                            "tejida con las cosas que te apasionan."),
                "accent":  accent,
                "topic":   pw["topic"],
            }
    return UNIVERSAL_WORLDS.get(world_key, {
        "emoji": "⭐", "name": "Mundo", "tagline": "",
        "intro": "", "accent": "#00eefc", "topic": "Aventura Diaria",
    })


# ==========================================
# CONSTANTES DE CONFIGURACION
# ==========================================
GROQ_MODEL_CHAT  = "llama-3.3-70b-versatile"
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

def _build_system_prompt_json(profile_name: str, cefr_code: str = "A1",
                               cefr_name: str = "Explorer",
                               world_key: str = "",
                               world_name: str = "",
                               world_tagline: str = "") -> str:
    """System prompt que instruye al LLM a generar un JSON robusto.
    Adapta complejidad al nivel CEFR estimado del/la alumno/a.
    Personaliza la lección según el MUNDO en el que está el alumno."""
    profile  = PROFILES[profile_name]
    gender   = profile.get("gender", "niño/niña")
    pronoun  = "ella" if gender == "niña" else "él"
    age_desc = profile.get("age_desc", "13 años")
    grade    = profile.get("grade", "")

    # Guía de complejidad por nivel
    cefr_guides = {
        "A1": "Vocabulario muy básico (saludos, familia, números, colores, objetos comunes). Oraciones cortas en presente simple. Evita pasado y futuro.",
        "A2": "Vocabulario cotidiano (rutinas, hobbies, comida, ropa). Presente simple, presente continuo y pasado simple regular. Oraciones de 5-10 palabras.",
        "B1": "Vocabulario amplio (opiniones, sentimientos, planes). Todos los tiempos básicos, condicionales tipo 1, modales (can/should/must). Oraciones complejas con conectores.",
        "B2": "Vocabulario académico y de actualidad. Voz pasiva, condicionales 2 y 3, perfecto continuo, reported speech. Discusión de temas abstractos.",
        "C1": "Vocabulario sofisticado, expresiones idiomáticas, phrasal verbs avanzados. Estructuras complejas, matices, ironía, registro formal/informal.",
        "C2": "Nivel casi nativo. Sutilezas, juegos de palabras, registros culturales, lenguaje literario.",
    }
    complexity_guide = cefr_guides.get(cefr_code, cefr_guides["A1"])

    # ─── Personalización por mundo: persona narrativa y enfoque temático ───
    world_personas = {
        "grammar":  {
            "persona": "Capitán/a Grammar, navegante del cosmos lingüístico",
            "setting": "una galaxia donde cada regla gramatical es una constelación",
            "voice_hint": "Usa metáforas espaciales ocasionales (galaxia, órbita, nave, estrella) sin abusar. La lección DEBE ser de gramática.",
        },
        "vocab":    {
            "persona": "Wordsmith Quinn, guardián/a de la Bóveda de Vocabulario",
            "setting": "una bóveda mágica donde cada palabra es un tesoro brillante",
            "voice_hint": "Usa imágenes de tesoros, joyas, cofres ocasionalmente. La lección DEBE estar enfocada 100% en vocabulario nuevo (NO gramática densa).",
        },
        "personal": {
            "persona": "Mentor/a personal del mundo de los hobbies del/la alumno/a",
            "setting": f"un mundo construido alrededor de los intereses de {profile_name}",
            "voice_hint": "Conecta TODA la lección con los hobbies del alumno. Usa nombres de familia/mascotas en ejemplos.",
        },
        "sound":    {
            "persona": "Ingeniero/a de sonido del Estudio Acústico",
            "setting": "un estudio de grabación con cabinas y micrófonos brillantes",
            "voice_hint": "Enfócate en sonidos del inglés. Marca cómo se pronuncia cada palabra clave con corchetes [pro-nun-cia-ción].",
        },
        "chat":     {
            "persona": "Barista del Café Conversación",
            "setting": "un café acogedor donde se habla inglés del mundo real",
            "voice_hint": "Usa ejemplos en forma de diálogos cortos entre dos personas.",
        },
        "writing":  {
            "persona": "Escritor/a del Taller de Letras",
            "setting": "un taller con plumas, tinta y máquinas de escribir vintage",
            "voice_hint": "Enfócate en cómo se construyen oraciones. Modela CÓMO escribir, no solo qué.",
        },
        "challenge":{
            "persona": "Maestro/a del Desafío Sorpresa",
            "setting": "una arena de combate lingüístico",
            "voice_hint": "Plantea la lección como un desafío épico que el alumno debe superar.",
        },
    }
    wp = world_personas.get(world_key, {
        "persona": "Tutor amigable",
        "setting": "una clase virtual",
        "voice_hint": "",
    })

    world_block = ""
    if world_key:
        world_block = f"""

════════════════════════════════════════
PERSONALIZACIÓN DEL MUNDO ({world_name or 'genérico'}):
════════════════════════════════════════
- Tu IDENTIDAD para esta lección: {wp['persona']}.
- AMBIENTACIÓN: {wp['setting']}.
- TAGLINE DEL MUNDO: {world_tagline}
- INSTRUCCIONES DE ESTILO: {wp['voice_hint']}

En la Parte A (introducción narrativa), DEBES abrir con una referencia natural al mundo
("Bienvenida a la {world_name}..." o similar). El resto de la lección mantiene la temática
del mundo pero SIN forzar metáforas en cada oración — solo cuando enriquezca.
"""

    # ─── Memoria de contenido: lo que el alumno ya cubrió ───
    recent = get_recent_lesson_topics(profile_name, n=15)
    memory_block = ""
    if recent:
        recent_str = ", ".join(recent[-10:])
        memory_block = f"""

════════════════════════════════════════
MEMORIA DE CONTENIDO RECIENTE:
════════════════════════════════════════
{profile_name} ya practicó recientemente: {recent_str}.

INSTRUCCIÓN: Si el tema/mundo coincide con algo ya cubierto, AMPLÍA con vocabulario
o estructura NUEVA — no repitas los mismos ejemplos. Si es un mundo nuevo para el
alumno, comienza con fundamentos.
"""

    return f"""
Eres un tutor de inglés experto, cariñoso y motivador, diseñado exclusivamente para {profile_name}, un/a {gender} de {age_desc}, cursando {grade}.
A {pronoun} le apasiona: {profile['hobbies']}.
Tu tono debe ser: {profile['tone']}.

NIVEL ESTIMADO DEL/LA ALUMNO/A: {cefr_code} ({cefr_name})
GUÍA DE COMPLEJIDAD ({cefr_code}): {complexity_guide}

Adapta vocabulario, gramática y longitud de oraciones a este nivel. Si subes la complejidad, hazlo gradualmente; nunca brinques 2 niveles de un solo tirón.

{profile['family_context']}{world_block}{memory_block}

════════════════════════════════════════
INSTRUCCIÓN CRÍTICA DE FORMATO JSON:
════════════════════════════════════════
Debes responder ÚNICAMENTE con un objeto JSON válido. Sin texto antes ni después.

REGLAS CRÍTICAS PARA NO ROMPER EL JSON — LÉELAS ANTES DE ESCRIBIR:
1. PROHIBIDO usar comillas dobles (") dentro de los valores. Usa siempre comillas simples (').
2. PROHIBIDO usar tablas Markdown con pipes (|). Para vocabulario usa SOLO listas con guiones (-).
3. PROHIBIDO usar saltos de línea reales dentro de un string JSON. Usa siempre \\n.
4. Los caracteres especiales dentro de strings JSON deben escaparse correctamente.

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
      "sentence": "<oración EN INGLÉS con UN SOLO ___ (tres guiones bajos) donde va la palabra a completar>",
      "answer": "<única palabra correcta en minúsculas sin tildes>",
      "hint": "<TRADUCCIÓN COMPLETA al ESPAÑOL de la oración como se vería ya completada, para que el alumno entienda qué palabra falta>"
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
- Si el tema es vocabulario: incluye una lista con guiones (-) donde CADA palabra empiece con un emoji visual representativo, seguida de la palabra en inglés, su pronunciación aproximada entre corchetes [pro-nun-cia-ción] y su significado en español. Ejemplo: `- 🦋 **butterfly** [bá-ter-flai] — mariposa`. NUNCA uses tablas con pipes (|). Los emojis ayudan a memorizar visualmente.
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
  La oración ("sentence") DEBE estar 100% EN INGLÉS — NUNCA en español.
  La oración debe contener EXACTAMENTE un marcador "___" (tres guiones bajos) donde va la palabra que falta. JAMÁS uses asteriscos, negritas ni varios huecos. Solo "___" una sola vez.
  La respuesta ("answer") debe ser UNA sola palabra en minúsculas sin puntuación ni tildes.
  El campo "hint" es OBLIGATORIO: contiene la traducción completa al ESPAÑOL de la oración (como se vería ya completa) para dar contexto al alumno.
"""


def generate_lesson_and_quiz(profile_name: str, topic: str,
                              custom_text: str | None = None,
                              cefr_code: str = "A1",
                              cefr_name: str = "Explorer",
                              world_key: str = "",
                              world_name: str = "",
                              world_tagline: str = ""):
    """Llama a Groq con JSON mode, adaptado al nivel CEFR del alumno y al MUNDO."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    system_prompt = _build_system_prompt_json(
        profile_name, cefr_code, cefr_name,
        world_key=world_key, world_name=world_name, world_tagline=world_tagline
    )
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


@st.cache_data(ttl=300, show_spinner=False)
def get_custom_avatars() -> dict:
    """
    Lee la pestaña 'avatars' del Google Sheet y devuelve un dict
    {profile_name_lower: custom_url} para sobrescribir el avatar por defecto.
    Si la pestaña no existe o falla, devuelve {} y la app usa los avatares
    base (assets en GitHub).
    """
    sheet, _ = get_db_connection()
    if not sheet:
        return {}
    try:
        spreadsheet = sheet.spreadsheet
        try:
            avatars_ws = spreadsheet.worksheet("avatars")
        except gspread.exceptions.WorksheetNotFound:
            return {}

        rows = avatars_ws.get_all_records()
        result = {}
        for r in rows:
            name = str(r.get("profile", "")).strip().lower()
            url  = str(r.get("custom_avatar_url", "")).strip()
            if name and url:
                result[name] = url
        return result
    except Exception as e:
        logger.warning(f"No se pudo leer pestaña avatars: {e}")
        return {}


def get_avatar_for(profile_name: str) -> str:
    """Devuelve la URL del avatar (custom de Sheets si existe, sino el base de PROFILES)."""
    custom = get_custom_avatars()
    key = profile_name.strip().lower()
    if key in custom and custom[key]:
        return custom[key]
    return PROFILES[profile_name].get("avatar", "")


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


@st.cache_data(ttl=120, show_spinner=False)
def get_skill_breakdown(profile_name: str) -> dict:
    """Devuelve breakdown por skill: {skill: {xp, sessions, avg_score}}.
    Las skills consideradas: vocabulary, grammar, listening, speaking, writing, reading."""
    skills = ["vocabulary", "grammar", "listening", "speaking", "writing", "reading", "conversation"]
    empty = {s: {"xp": 0, "sessions": 0, "avg_score": 0.0} for s in skills}
    sheet, _ = get_db_connection()
    if not sheet:
        return empty
    try:
        rows = sheet.get_all_records()
        user_rows = [r for r in rows if r.get("profile", "") == profile_name]
        out = {s: {"xp": 0, "sessions": 0, "scores": []} for s in skills}
        for r in user_rows:
            sk = (r.get("skill") or "").strip().lower()
            if sk not in out:
                continue
            out[sk]["xp"] += int(r.get("xp", 0) or 0)
            out[sk]["sessions"] += 1
            score_str = str(r.get("score_pct", "0%")).replace("%", "")
            try:
                out[sk]["scores"].append(float(score_str) / 100.0)
            except ValueError:
                pass
        for s in skills:
            scores = out[s]["scores"]
            out[s]["avg_score"] = sum(scores) / len(scores) if scores else 0.0
            out[s].pop("scores", None)
        return out
    except Exception as e:
        logger.error(f"Error get_skill_breakdown: {e}")
        return empty


@st.cache_data(ttl=120, show_spinner=False)
def get_streak_days(profile_name: str) -> int:
    """Cuenta días consecutivos con al menos 1 sesión, terminando HOY o AYER."""
    sheet, _ = get_db_connection()
    if not sheet:
        return 0
    try:
        rows = sheet.get_all_records()
        user_rows = [r for r in rows if r.get("profile", "") == profile_name]
        # Set de fechas (no datetimes) con actividad
        active_days = set()
        for r in user_rows:
            ts_str = r.get("timestamp", "")
            try:
                ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                active_days.add(ts.date())
            except Exception:
                pass
        if not active_days:
            return 0
        # Contar racha desde hoy hacia atrás (también permite ayer si aún no jugó hoy)
        today = datetime.date.today()
        cursor = today if today in active_days else today - datetime.timedelta(days=1)
        if cursor not in active_days:
            return 0
        streak = 0
        while cursor in active_days:
            streak += 1
            cursor -= datetime.timedelta(days=1)
        return streak
    except Exception as e:
        logger.error(f"Error get_streak_days: {e}")
        return 0


@st.cache_data(ttl=60, show_spinner=False)
def get_today_session_count(profile_name: str) -> int:
    """Sesiones del día de hoy."""
    sheet, _ = get_db_connection()
    if not sheet:
        return 0
    try:
        rows = sheet.get_all_records()
        today = datetime.date.today()
        n = 0
        for r in rows:
            if r.get("profile", "") != profile_name:
                continue
            ts_str = r.get("timestamp", "")
            try:
                ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                if ts.date() == today:
                    n += 1
            except Exception:
                pass
        return n
    except Exception:
        return 0


# Mapa skill → mundo recomendado
SKILL_TO_WORLD = {
    "vocabulary":   {"key": "vocab",    "emoji": "📚", "name": "Bóveda de Vocabulario"},
    "grammar":      {"key": "grammar",  "emoji": "🌌", "name": "Galaxia Gramatical"},
    "listening":    {"key": "sound",    "emoji": "🎙", "name": "Estudio de Sonido"},
    "speaking":     {"key": "chat",     "emoji": "💬", "name": "Café Conversación"},
    "writing":      {"key": "writing",  "emoji": "🖋", "name": "Taller de Letras"},
    "reading":      {"key": "personal", "emoji": "🎨", "name": "Mundo Personal"},
    "conversation": {"key": "chat",     "emoji": "💬", "name": "Café Conversación"},
}


BADGE_DEFINITIONS = [
    {"key": "first_step",   "emoji": "🌱", "name": "Primer paso",          "desc": "Completaste tu primera lección"},
    {"key": "ten_sessions", "emoji": "🎯", "name": "Decena",               "desc": "Llegaste a 10 sesiones"},
    {"key": "fifty_xp",     "emoji": "⚡", "name": "Eléctric@",            "desc": "Acumulaste 50 XP"},
    {"key": "hundred_xp",   "emoji": "💎", "name": "Centurión",            "desc": "100 XP en tu cuenta"},
    {"key": "five_hundred", "emoji": "🏆", "name": "Campeón",              "desc": "500 XP — ¡increíble!"},
    {"key": "thousand_xp",  "emoji": "👑", "name": "Leyenda",              "desc": "1000 XP — élite total"},
    {"key": "streak_3",     "emoji": "🔥", "name": "Encendid@",            "desc": "3 días seguidos jugando"},
    {"key": "streak_7",     "emoji": "🌋", "name": "Imparable",            "desc": "Una semana entera de racha"},
    {"key": "streak_30",    "emoji": "🌟", "name": "Mes Perfecto",         "desc": "30 días consecutivos"},
    {"key": "perfect_quiz", "emoji": "💯", "name": "Perfeccionista",       "desc": "Obtuviste 100% en un quiz"},
    {"key": "all_worlds",   "emoji": "🌍", "name": "Explorador/a Global",  "desc": "Visitaste los 8 mundos"},
    {"key": "exam_passed",  "emoji": "📜", "name": "Aprobado",             "desc": "Pasaste un examen semanal con ≥70%"},
    {"key": "speak_journal","emoji": "📔", "name": "Diarista",             "desc": "Grabaste tu primer Diario Hablado"},
    {"key": "writer",       "emoji": "🖋", "name": "Escritor/a",           "desc": "Completaste 5 ejercicios de escritura"},
    {"key": "speaker",      "emoji": "🎤", "name": "Orador/a",             "desc": "5 sesiones de pronunciación o speaking"},
]


@st.cache_data(ttl=120, show_spinner=False)
def compute_earned_badges(profile_name: str) -> list:
    """Devuelve la lista de keys de badges desbloqueados por el alumno."""
    earned = set()
    stats = get_user_stats(profile_name)
    streak = get_streak_days(profile_name)
    breakdown = get_skill_breakdown(profile_name)

    if stats["total_sessions"] >= 1: earned.add("first_step")
    if stats["total_sessions"] >= 10: earned.add("ten_sessions")
    if stats["total_xp"] >= 50:   earned.add("fifty_xp")
    if stats["total_xp"] >= 100:  earned.add("hundred_xp")
    if stats["total_xp"] >= 500:  earned.add("five_hundred")
    if stats["total_xp"] >= 1000: earned.add("thousand_xp")
    if streak >= 3:  earned.add("streak_3")
    if streak >= 7:  earned.add("streak_7")
    if streak >= 30: earned.add("streak_30")
    if stats["best_score"] >= 1.0: earned.add("perfect_quiz")

    # All worlds: leer sheets
    sheet, _ = get_db_connection()
    if sheet:
        try:
            rows = sheet.get_all_records()
            visited = set()
            exam_passed = False
            journal_count = 0
            writer_count = 0
            speaker_count = 0
            for r in rows:
                if r.get("profile") != profile_name:
                    continue
                visited.add(r.get("world", ""))
                lt = (r.get("lesson_type") or "").lower()
                sc_str = str(r.get("score_pct", "0%")).replace("%", "")
                try:
                    sc = float(sc_str) / 100.0
                except ValueError:
                    sc = 0.0
                if lt == "exam" and sc >= 0.7:
                    exam_passed = True
                if lt == "speaking_journal":
                    journal_count += 1
                if lt in ("translate_inv", "describe_scene"):
                    writer_count += 1
                if lt in ("pronunciation", "shadow_speak"):
                    speaker_count += 1
            if len(visited & {"grammar", "vocab", "personal", "challenge",
                              "sound", "chat", "writing", "journal"}) >= 8:
                earned.add("all_worlds")
            if exam_passed:    earned.add("exam_passed")
            if journal_count >= 1: earned.add("speak_journal")
            if writer_count >= 5:  earned.add("writer")
            if speaker_count >= 5: earned.add("speaker")
        except Exception as e:
            logger.error(f"Error compute_badges: {e}")

    return list(earned)


def get_weakest_skill(profile_name: str) -> tuple:
    """Identifica la skill más débil: la que tiene MENOS sesiones, en caso
    de empate, la que tiene peor avg_score. Devuelve (skill_key, world_meta)."""
    breakdown = get_skill_breakdown(profile_name)
    # Solo consideramos skills "core" (no conversation que es duplicado de speaking)
    core_skills = ["vocabulary", "grammar", "listening", "speaking", "writing", "reading"]
    # Ordenar: primero menos sesiones, luego peor score
    ranked = sorted(
        core_skills,
        key=lambda s: (breakdown[s]["sessions"], breakdown[s]["avg_score"])
    )
    weakest = ranked[0]
    return weakest, SKILL_TO_WORLD[weakest]


def save_xp_to_sheet(profile_name: str, xp_gained: int, score_pct: float, attempts: int,
                      world: str = "", skill: str = "", lesson_type: str = ""):
    """
    Registra una sesion completada en Google Sheets, con reintento automático.
    Columnas: Timestamp | profile | xp | score_pct | attempts
              | world | skill | lesson_type | streak_date | trophies

    Si el primer intento falla, limpia el caché de conexión y reintenta UNA vez.
    Devuelve (saved: bool, error: str|None).
    """
    last_error = None
    for attempt_idx in range(2):
        if attempt_idx == 1:
            # En reintento: limpiar caché de conexión y forzar reauth
            try:
                get_db_connection.clear()
            except Exception:
                pass

        sheet, db_error = get_db_connection()
        if db_error or not sheet:
            last_error = db_error or "Conexión no disponible"
            logger.warning(f"⚠️ save_xp intento {attempt_idx+1}: sin conexión ({last_error})")
            continue

        try:
            now       = datetime.datetime.now()
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            streak_dt = now.strftime("%Y-%m-%d")
            score_str = f"{score_pct:.1%}"
            sheet.append_row([
                timestamp, profile_name, xp_gained, score_str, attempts,
                world, skill, lesson_type, streak_dt, ""
            ])
            # Invalidar cachés que dependen del sheet
            get_user_stats.clear()
            get_leaderboard.clear()
            logger.info(f"✅ XP guardado: {profile_name} +{xp_gained} XP "
                        f"(world={world}, type={lesson_type}, intento #{attempt_idx+1})")
            return True, None
        except Exception as e:
            last_error = str(e)
            logger.error(f"❌ Error guardando en Sheets (intento #{attempt_idx+1}): {e}")

    return False, last_error or "Error desconocido al guardar"


def get_service_account_email() -> str:
    """Devuelve el email del service account desde secrets, o un placeholder."""
    try:
        return st.secrets["gcp_service_account"]["client_email"]
    except (KeyError, FileNotFoundError, AttributeError):
        return "(no se pudo leer del secrets.toml)"
    except Exception:
        return "(error al leer credenciales)"


def render_save_failure(error: str, xp_award: int):
    """Muestra un banner prominente cuando falla guardar en Sheets,
    con el email del service account que el usuario debe agregar como Editor."""
    sa_email = get_service_account_email()
    safe_error = (str(error) or "Desconocido")[:300]
    st.markdown(f"""
        <div class='save-error-banner'>
            <h3>⚠️ Tus +{xp_award} XP NO se guardaron en la nube</h3>
            <p style='margin:0 0 10px;'>
                Los puntos NO se sumarán a tu cuenta hasta que arreglemos la conexión.
                Si cierras la app ahora, este progreso se perderá.
            </p>
            <p style='margin:0 0 6px;'><b>Error técnico:</b></p>
            <p style='margin:0 0 14px;'><code>{safe_error}</code></p>
            <hr style='border-color: rgba(255,255,255,0.1); margin: 14px 0;'>
            <p style='margin:0 0 8px;'><b>🔧 CÓMO ARREGLARLO (1 minuto):</b></p>
            <ol style='margin:0 0 8px; padding-left:22px;'>
                <li>Abre tu Google Sheets <b>Idiomaconnect_DB</b></li>
                <li>Click el botón <b>Compartir</b> (arriba a la derecha)</li>
                <li>Agrega este correo con permiso <b>Editor</b>:</li>
            </ol>
            <div style='text-align:center; margin: 8px 0;'>
                <span class='sa-email'>{sa_email}</span>
            </div>
            <ol start='4' style='margin:0 0 8px; padding-left:22px;'>
                <li>Vuelve a esta app y aprieta <b>"🔁 Reintentar guardar"</b> abajo</li>
            </ol>
        </div>
    """, unsafe_allow_html=True)


def attempt_xp_save():
    """Centraliza el intento de guardar XP. Lee pending_xp_save_args,
    si tiene éxito incrementa session_state.xp y resetea; si falla,
    setea last_save_error para que el overlay lo muestre."""
    args = st.session_state.get("pending_xp_save_args")
    if not args:
        return
    saved, err = save_xp_to_sheet(
        args["user"], args["xp_award"], args["score_pct"], args["attempts"],
        world=args.get("world", ""),
        skill=args.get("skill", ""),
        lesson_type=args.get("lesson_type", "")
    )
    if saved:
        # XP YA está en Sheets. Reseteamos session_state.xp a 0 y limpiamos
        # la caché de stats para que el encabezado refleje el nuevo total
        # desde la fuente única de verdad (Google Sheets) sin doble conteo.
        st.session_state.xp = 0
        for fn in (get_user_stats, get_skill_breakdown,
                   get_streak_days, get_today_session_count,
                   compute_earned_badges, get_recent_lesson_topics):
            try:
                fn.clear()
            except Exception:
                pass
        st.session_state.flash_success = args.get("success_msg",
            f"¡+{args['xp_award']} XP guardados!")
        st.session_state.pending_xp_save_args = None
        st.session_state.last_save_error = None
        reset_to_worlds()
    else:
        st.session_state.last_save_error = err


def queue_xp_save(user: str, xp_award: int, score_pct: float, attempts: int,
                   world: str = "", skill: str = "",
                   lesson_type: str = "lesson_quiz",
                   success_msg: str = ""):
    """Encola los datos del save y ejecuta el primer intento de inmediato."""
    st.session_state.pending_xp_save_args = {
        "user": user,
        "xp_award": xp_award,
        "score_pct": score_pct,
        "attempts": attempts,
        "world": world,
        "skill": skill,
        "lesson_type": lesson_type,
        "success_msg": success_msg or f"¡{user}! +{xp_award} XP en tu cuenta.",
    }
    attempt_xp_save()


def check_db_status() -> tuple:
    """Diagnóstico rápido de la conexión.
    Devuelve (status: 'ok'|'fail'|'warn', message, sa_email)."""
    sa_email = get_service_account_email()
    sheet, err = get_db_connection()
    if err or sheet is None:
        return ("fail", err or "Sin conexión", sa_email)
    # Intentar lectura mínima
    try:
        _ = sheet.row_values(1)
        return ("ok", "Conectado a Google Sheets", sa_email)
    except Exception as e:
        return ("warn", f"Conectado pero error leyendo: {e}", sa_email)


# ==========================================
# LEADERBOARD, CEFR Y TROFEOS
# ==========================================

@st.cache_data(ttl=120, show_spinner=False)
def get_leaderboard() -> list[dict]:
    """
    Devuelve una lista ordenada por XP semanal (desc) con las stats
    agregadas de TODOS los perfiles. Lee el sheet una sola vez.
    Cada elemento: {profile, total_xp, week_xp, total_sessions, avg_score,
                    best_score, perfect_count, last_activity, world_counts}
    """
    base = []
    sheet, _ = get_db_connection()
    if not sheet:
        # Fallback: lista vacía con cada perfil para que la UI no falle
        for name in PROFILES:
            base.append({
                "profile": name, "total_xp": 0, "week_xp": 0,
                "total_sessions": 0, "avg_score": 0.0, "best_score": 0.0,
                "perfect_count": 0, "last_activity": None, "world_counts": {},
                "active_days": 0,
            })
        return base

    try:
        rows = sheet.get_all_records()
    except Exception as e:
        logger.warning(f"Error leyendo sheet para leaderboard: {e}")
        rows = []

    now = datetime.datetime.now()
    week_start = (now - datetime.timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    agg = {name: {
        "profile": name, "total_xp": 0, "week_xp": 0,
        "total_sessions": 0, "score_sum": 0.0, "best_score": 0.0,
        "perfect_count": 0, "last_activity": None, "world_counts": {},
        "active_days": set(),
        "battle_wins": 0, "lesson_count": 0,
        "pronunciation_count": 0, "conversation_count": 0,
        "srs_review_count": 0,
        "active_dates_set": set(),  # para max_consec_streak
    } for name in PROFILES}

    for r in rows:
        name = r.get("profile", "")
        if name not in agg:
            continue
        try:
            xp = int(r.get("xp", 0) or 0)
        except (ValueError, TypeError):
            xp = 0
        try:
            score_f = float(str(r.get("score_pct", "0%")).replace("%", "")) / 100.0
        except ValueError:
            score_f = 0.0

        ts = None
        ts_str = r.get("timestamp", "") or r.get("Timestamp", "")
        try:
            ts = datetime.datetime.strptime(str(ts_str), "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            ts = None

        a = agg[name]
        a["total_xp"]       += xp
        a["total_sessions"] += 1
        a["score_sum"]      += score_f
        if score_f > a["best_score"]:
            a["best_score"] = score_f
        if score_f >= 0.999:
            a["perfect_count"] += 1
        if ts is not None:
            if a["last_activity"] is None or ts > a["last_activity"]:
                a["last_activity"] = ts
            if ts >= week_start:
                a["week_xp"] += xp
            a["active_days"].add(ts.date())

        world = str(r.get("world", "") or "").strip()
        if world:
            a["world_counts"][world] = a["world_counts"].get(world, 0) + 1

        # Tracking de tipo de lección y batallas ganadas
        ltype = str(r.get("lesson_type", "") or "").strip()
        if ltype == "battle":
            # Considerar victoria si score >= 60% (mismo umbral que classic)
            if score_f >= PASSING_SCORE:
                a["battle_wins"] += 1
        elif ltype == "pronunciation":
            a["pronunciation_count"] += 1
        elif ltype == "conversation":
            a["conversation_count"] += 1
        elif ltype == "srs_review":
            a["srs_review_count"] += 1
        elif ltype in ("lesson_quiz", ""):
            a["lesson_count"] += 1

        if ts is not None:
            a["active_dates_set"].add(ts.date())

    # Finalizar
    for a in agg.values():
        sessions = a["total_sessions"]
        a["avg_score"] = (a["score_sum"] / sessions) if sessions else 0.0
        a.pop("score_sum", None)
        a["active_days"] = len(a["active_days"])

        # Calcular streak máximo de días consecutivos
        dates = sorted(a["active_dates_set"])
        max_streak = 0
        cur_streak = 0
        prev_date = None
        for d in dates:
            if prev_date is None or (d - prev_date).days == 1:
                cur_streak += 1
            elif (d - prev_date).days > 1:
                cur_streak = 1
            # day 0 no incrementa
            max_streak = max(max_streak, cur_streak)
            prev_date = d
        a["max_consec_days"] = max_streak

        # Mundos universales únicos visitados (los 4: grammar/vocab/personal/challenge)
        UNIVERSAL_KEYS = {"grammar", "vocab", "personal", "challenge"}
        a["unique_worlds_visited"] = len(
            UNIVERSAL_KEYS.intersection(a["world_counts"].keys())
        )

        a.pop("active_dates_set", None)

    # Ordenar por XP semanal (desc), desempate por XP total
    base = sorted(agg.values(),
                  key=lambda x: (x["week_xp"], x["total_xp"]),
                  reverse=True)
    return base


# Niveles CEFR derivados del XP total acumulado.
# Cada tupla: (codigo, nombre, tagline, xp_minimo)
CEFR_LEVELS = [
    ("A1", "Explorer",  "Primeros pasos en inglés",                0),
    ("A2", "Cadet",     "Frases cotidianas y rutinas",            150),
    ("B1", "Pilot",     "Conversaciones independientes",          400),
    ("B2", "Captain",   "Fluidez en temas complejos",             900),
    ("C1", "Commander", "Dominio en contextos académicos",       1700),
    ("C2", "Legend",    "Maestría casi nativa",                  3000),
]


def get_cefr_info(total_xp: int) -> dict:
    """
    Calcula el nivel CEFR estimado, próximo nivel y progreso al siguiente.
    """
    current_idx = 0
    for i, (_, _, _, threshold) in enumerate(CEFR_LEVELS):
        if total_xp >= threshold:
            current_idx = i
        else:
            break

    code, name, tagline, threshold = CEFR_LEVELS[current_idx]

    if current_idx + 1 < len(CEFR_LEVELS):
        next_code, next_name, _, next_threshold = CEFR_LEVELS[current_idx + 1]
        span = max(1, next_threshold - threshold)
        progress = max(0.0, min(1.0, (total_xp - threshold) / span))
        xp_to_next = max(0, next_threshold - total_xp)
        next_label = f"{xp_to_next} XP para {next_code} {next_name}"
    else:
        progress = 1.0
        next_label = "Nivel máximo alcanzado"

    return {
        "code": code, "name": name, "tagline": tagline,
        "progress": progress, "next_label": next_label,
    }


# Catálogo de trofeos. (id, icono, nombre corto, descripción, color, predicate(stats)->bool)
TROPHY_CATALOG = [
    # Progresión básica
    ("first_step",  "🚀", "Primer Vuelo",   "Completa tu primera misión",
     "#00eefc", lambda s: s["total_sessions"] >= 1),
    ("five_lessons","🔥", "Combo x5",       "Completa 5 misiones",
     "#ff5351", lambda s: s["total_sessions"] >= 5),
    ("ten_lessons", "⚡", "Combo x10",      "Completa 10 misiones",
     "#ffd400", lambda s: s["total_sessions"] >= 10),
    # Calidad
    ("perfect",     "🎯", "Notón Perfecto", "Saca 100% en un quiz",
     "#39ff14", lambda s: s.get("perfect_count", 0) >= 1),
    # XP milestones
    ("xp_500",      "💎", "Club 500 XP",    "Acumula 500 XP",
     "#c464ff", lambda s: s["total_xp"] >= 500),
    ("xp_1000",     "🏆", "Club 1000 XP",   "Acumula 1000 XP",
     "#ffd400", lambda s: s["total_xp"] >= 1000),
    ("xp_2000",     "🌟", "Leyenda",        "Acumula 2000 XP",
     "#ff66c4", lambda s: s["total_xp"] >= 2000),
    # Constancia
    ("active_5d",   "📅", "Disciplina",     "Activo en 5 días distintos",
     "#00eefc", lambda s: s.get("active_days", 0) >= 5),
    ("streak_3d",   "⛅", "Racha 3 días",   "3 días consecutivos activos",
     "#39ff14", lambda s: s.get("max_consec_days", 0) >= 3),
    ("streak_7d",   "🌅", "Racha 7 días",   "7 días consecutivos activos",
     "#ff5351", lambda s: s.get("max_consec_days", 0) >= 7),
    # Battle mode
    ("battle_first","🥷", "Bautismo de Fuego", "Gana tu primera batalla",
     "#ff5351", lambda s: s.get("battle_wins", 0) >= 1),
    ("battle_5",    "🌪️", "Guerrero",       "Gana 5 batallas",
     "#ffd400", lambda s: s.get("battle_wins", 0) >= 5),
    # Exploración
    ("explorer",    "🌍", "Explorador",     "Visita los 4 mundos universales",
     "#c464ff", lambda s: s.get("unique_worlds_visited", 0) >= 4),
    # Modos avanzados
    ("speaker",     "🎤", "Voz Clara",      "Practica pronunciación 1 vez",
     "#39ff14", lambda s: s.get("pronunciation_count", 0) >= 1),
    ("conversator", "💬", "Conversador",    "Completa 3 conversaciones",
     "#c464ff", lambda s: s.get("conversation_count", 0) >= 3),
    ("memory",      "🧠", "Memoria de Elefante", "Repasa 50 palabras",
     "#ffd400", lambda s: s.get("srs_review_count", 0) >= 50),
]


def get_trophies(stats: dict) -> list[dict]:
    """Devuelve la lista del catálogo con flag earned segun stats del perfil."""
    out = []
    for tid, icon, name, desc, color, predicate in TROPHY_CATALOG:
        try:
            earned = bool(predicate(stats))
        except Exception:
            earned = False
        out.append({
            "id": tid, "icon": icon, "name": name, "desc": desc,
            "color": color, "earned": earned,
        })
    return out


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


def start_lesson(topic: str, custom_text: str | None = None,
                 world: str = "custom", lesson_type: str = "lesson_quiz"):
    """Resetea el estado de quiz/battle y dispara la generación de una nueva lección."""
    st.session_state.lesson_pending = True
    st.session_state.lesson_topic   = topic
    st.session_state.lesson_text    = custom_text
    st.session_state.current_world  = world
    st.session_state.current_lesson_type = lesson_type
    st.session_state.quiz_data      = None
    st.session_state.quiz_result    = None
    st.session_state.quiz_attempts  = 0
    st.session_state.lesson_error   = None
    st.session_state.lesson_audio   = None
    # Battle state reset
    st.session_state.battle_questions  = None
    st.session_state.battle_finished   = False
    st.session_state.battle_feedback   = None
    st.session_state.battle_history    = []
    st.session_state.battle_index      = 0
    st.session_state.battle_hp         = st.session_state.battle_max_hp
    st.session_state.battle_streak     = 0
    st.session_state.battle_max_streak = 0
    st.session_state.battle_correct    = 0
    st.session_state.battle_total      = 0
    st.session_state.battle_mc_answer  = None
    st.session_state.battle_fitb_answer = ""
    # Cerrar el world entry y volver a Home
    st.session_state.selected_world = None
    st.session_state.view = "home"


def reset_to_worlds():
    """Limpia toda lección/battle/conv/pron/srs y vuelve al mapa de mundos."""
    keys_to_reset = [
        "quiz_data", "quiz_result", "quiz_attempts", "lesson_error",
        "lesson_audio", "lesson_pending", "selected_world",
        "battle_questions", "battle_finished", "battle_feedback",
        "battle_history", "battle_index", "battle_streak",
        "battle_max_streak", "battle_correct", "battle_total",
        "battle_mc_answer", "battle_fitb_answer",
        # Pronunciation
        "pron_words", "pron_index", "pron_results", "pron_last_audio",
        "pron_last_score", "pron_finished",
        # Conversation
        "conv_active", "conv_history", "conv_turn_count",
        "conv_pending_user_input",
        # SRS
        "srs_active", "srs_cards", "srs_index", "srs_revealed",
        "srs_correct", "srs_attempted", "srs_finished",
        # Flashcards
        "fc_cards", "fc_index", "fc_correct", "fc_attempted",
        "fc_finished", "fc_chosen", "fc_audio",
        # Sentence Builder
        "sb_sentences", "sb_index", "sb_placed", "sb_correct",
        "sb_attempted", "sb_finished", "sb_revealed", "sb_last_ok",
        # Memory Match
        "mm_pairs", "mm_flipped", "mm_matched", "mm_attempts",
        "mm_first", "mm_finished",
        # Story Fill
        "sf_story", "sf_index", "sf_picked", "sf_revealed",
        "sf_correct", "sf_finished",
        # Role-Play + Resumen final
        "rp_scenario", "rp_done_objs", "rp_picker",
        "conv_summary", "conv_show_end",
        # Minimal Pairs
        "mp_pairs", "mp_index", "mp_correct", "mp_chosen",
        "mp_finished", "mp_audio",
        # Listen ID
        "li_cards", "li_index", "li_correct", "li_chosen",
        "li_finished", "li_audio",
        # Traducción Inversa
        "ti_items", "ti_index", "ti_answers", "ti_feedback",
        "ti_evaluating", "ti_finished",
        # Describe la Escena
        "ds_scenes", "ds_index", "ds_answers", "ds_feedback",
        "ds_evaluating", "ds_finished",
        # Shadow Speaking
        "ss_phrases", "ss_index", "ss_results", "ss_last_audio",
        "ss_last_score", "ss_finished",
        # Examen
        "ex_questions", "ex_index", "ex_correct", "ex_answers",
        "ex_finished", "ex_chosen",
        # Diario Hablado
        "dh_prompt", "dh_audio", "dh_transcript", "dh_feedback",
        "dh_finished",
    ]
    for k in keys_to_reset:
        if k in _STATE_DEFAULTS:
            st.session_state[k] = _STATE_DEFAULTS[k]
    st.session_state.battle_hp = st.session_state.battle_max_hp


def start_pronunciation(world_key: str, world_topic: str):
    """Inicia el modo pronunciación: pide palabras al LLM y arma el estado."""
    profile_name = st.session_state.current_user
    cefr = get_cefr_info(
        next(
            (e["total_xp"] for e in get_leaderboard()
             if e["profile"] == profile_name),
            0
        )
    )["code"]

    with st.spinner("🎤 Preparando palabras para practicar..."):
        words, err = generate_pronunciation_words(profile_name, world_topic, cefr)

    if err or not words:
        st.error(f"⚠️ No pude generar palabras: {err or 'sin datos'}")
        return

    st.session_state.lesson_pending = False
    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "pronunciation"
    st.session_state.pron_words      = words
    st.session_state.pron_index      = 0
    st.session_state.pron_results    = []
    st.session_state.pron_last_audio = None
    st.session_state.pron_last_score = None
    st.session_state.pron_finished   = False
    st.session_state.selected_world  = None  # cierra entry page
    st.session_state.view = "home"


def start_conversation(world_key: str, scenario_key: str = None):
    """Inicia el modo conversación con la IA. Si scenario_key se da,
    arranca un role-play con ese escenario."""
    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "conversation"
    st.session_state.conv_active     = True
    st.session_state.conv_history    = []
    st.session_state.conv_turn_count = 0
    st.session_state.conv_pending_user_input = ""
    if scenario_key:
        st.session_state.rp_scenario = get_scenario_by_key(scenario_key)
        st.session_state.rp_done_objs = []
    else:
        st.session_state.rp_scenario = None
        st.session_state.rp_done_objs = None
    st.session_state.rp_picker = False
    st.session_state.selected_world  = None
    st.session_state.view = "home"


def open_roleplay_picker(world_key: str):
    """Abre la pantalla de selección de escenario role-play."""
    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "roleplay_picker"
    st.session_state.rp_picker = True
    st.session_state.rp_scenario = None
    st.session_state.rp_done_objs = None
    st.session_state.conv_active = False
    st.session_state.selected_world = None
    st.session_state.view = "home"


def start_flashcards(world_key: str, world_topic: str):
    """Inicia el modo Flashcards Visuales (exclusivo del mundo vocabulario):
    pide al LLM 6 tarjetas con palabra, significado, emoji y 3 distractores.
    Cada tarjeta muestra el emoji grande + audio TTS y 4 opciones de palabra."""
    profile_name = st.session_state.current_user
    cefr = get_cefr_info(
        next(
            (e["total_xp"] for e in get_leaderboard()
             if e["profile"] == profile_name),
            0
        )
    )["code"]

    with st.spinner("🃏 Preparando tus tarjetas..."):
        cards, err = generate_flashcards(profile_name, world_topic, cefr)

    if err or not cards:
        st.error(f"⚠️ No pude generar tarjetas: {err or 'sin datos'}")
        return

    # Mezclar opciones de cada tarjeta: 1 correcta + 3 distractores aleatorios
    import random as _rand
    prepared = []
    for c in cards:
        opts = [c["word"]] + (c.get("distractors") or [])[:3]
        # rellenar si vinieron menos de 3 distractores
        while len(opts) < 4:
            opts.append("???")
        opts = opts[:4]
        _rand.shuffle(opts)
        correct_idx = opts.index(c["word"]) if c["word"] in opts else 0
        prepared.append({
            "word":        c["word"],
            "meaning":     c.get("meaning", ""),
            "emoji":       c.get("emoji", "🃏"),
            "ipa":         c.get("ipa", ""),
            "options":     opts,
            "correct_idx": correct_idx,
        })

    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "flashcards"
    st.session_state.fc_cards       = prepared
    st.session_state.fc_index       = 0
    st.session_state.fc_correct     = 0
    st.session_state.fc_attempted   = 0
    st.session_state.fc_finished    = False
    st.session_state.fc_chosen      = None
    st.session_state.fc_audio       = None
    st.session_state.selected_world = None
    st.session_state.view = "home"


def start_sentence_builder(world_key: str, world_topic: str):
    """Inicia el modo Constructor de Oraciones (exclusivo de Galaxia Gramatical):
    el niño tiene palabras desordenadas y debe ordenarlas tocándolas en secuencia."""
    profile_name = st.session_state.current_user
    cefr = get_cefr_info(
        next(
            (e["total_xp"] for e in get_leaderboard()
             if e["profile"] == profile_name),
            0
        )
    )["code"]

    with st.spinner("🧩 Preparando oraciones para armar..."):
        sents, err = generate_sentences(profile_name, world_topic, cefr)

    if err or not sents:
        st.error(f"⚠️ No pude generar oraciones: {err or 'sin datos'}")
        return

    import random as _rand
    prepared = []
    for s in sents:
        words = s["english"].split()
        target = list(words)
        scrambled = list(words)
        # Asegurar que el orden mezclado sea distinto del orden correcto
        for _ in range(8):
            _rand.shuffle(scrambled)
            if scrambled != target:
                break
        prepared.append({
            "spanish":   s["spanish"],
            "english":   s["english"],
            "scrambled": scrambled,
            "target":    target,
        })

    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "sentence_builder"
    st.session_state.sb_sentences   = prepared
    st.session_state.sb_index       = 0
    st.session_state.sb_placed      = []
    st.session_state.sb_correct     = 0
    st.session_state.sb_attempted   = 0
    st.session_state.sb_finished    = False
    st.session_state.sb_revealed    = False
    st.session_state.sb_last_ok     = None
    st.session_state.selected_world = None
    st.session_state.view = "home"


def start_story_fill(world_key: str, world_topic: str):
    """Inicia el modo Cuento Personalizado con Huecos (mundo personal)."""
    profile_name = st.session_state.current_user
    cefr = get_cefr_info(
        next(
            (e["total_xp"] for e in get_leaderboard()
             if e["profile"] == profile_name),
            0
        )
    )["code"]

    with st.spinner("📖 Escribiendo tu cuento personalizado..."):
        story, err = generate_story_fill(profile_name, world_topic, cefr)

    if err or not story:
        st.error(f"⚠️ No pude generar el cuento: {err or 'sin datos'}")
        return

    # Mezclar opciones de cada hueco para que la correcta no siempre sea la primera
    import random as _rand
    for s in story["sentences"]:
        _rand.shuffle(s["blank_options"])
        s["correct_idx"] = s["blank_options"].index(s["blank_correct"])

    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "story_fill"
    st.session_state.sf_story       = story
    st.session_state.sf_index       = 0
    st.session_state.sf_picked      = [None] * len(story["sentences"])
    st.session_state.sf_revealed    = False
    st.session_state.sf_correct     = 0
    st.session_state.sf_finished    = False
    st.session_state.selected_world = None
    st.session_state.view = "home"


def start_speaking_journal(world_key: str, world_topic: str):
    """Inicia el Diario Hablado (Speaking Journal)."""
    profile_name = st.session_state.current_user
    cefr = get_cefr_info(
        next(
            (e["total_xp"] for e in get_leaderboard()
             if e["profile"] == profile_name),
            0
        )
    )["code"]

    with st.spinner("📔 Buscando el prompt de hoy..."):
        prompt, err = generate_journal_prompt(profile_name, cefr)

    if err or not prompt:
        st.error(f"⚠️ No pude generar el prompt: {err or 'sin datos'}")
        return

    st.session_state.current_world = world_key
    st.session_state.current_lesson_type = "speaking_journal"
    st.session_state.dh_prompt     = prompt
    st.session_state.dh_audio      = None
    st.session_state.dh_transcript = None
    st.session_state.dh_feedback   = None
    st.session_state.dh_finished   = False
    st.session_state.selected_world = None
    st.session_state.view = "home"


def start_exam(profile_name: str):
    """Inicia el modo Examen: 10 preguntas mezcladas de todas las skills.
    Solo disponible los viernes y sábados (con bonus el viernes)."""
    # Validar día de la semana: 4=viernes, 5=sábado
    today_weekday = datetime.date.today().weekday()
    if today_weekday not in (4, 5):
        days_to_fri = (4 - today_weekday) % 7
        st.warning(
            f"🔒 El Examen Semanal solo está disponible los **viernes y sábados**. "
            f"Faltan **{days_to_fri} día(s)** para el próximo viernes. "
            f"Mientras tanto, sigue practicando en los mundos para llegar mejor preparado/a."
        )
        return

    # Validar pre-requisito: al menos 3 sesiones en la semana actual
    stats = get_user_stats(profile_name)
    if stats.get("total_sessions", 0) >= 3 and stats.get("week_xp", 0) < 30:
        st.info(
            "💡 **Sugerencia:** Esta semana llevas menos de 30 XP. El examen requiere "
            "estar preparado/a — practica un poco más antes de rendir."
        )
        # No bloqueamos, solo sugerimos

    cefr = get_cefr_info(
        next(
            (e["total_xp"] for e in get_leaderboard()
             if e["profile"] == profile_name),
            0
        )
    )["code"]

    with st.spinner("📝 Generando tu examen semanal..."):
        questions, err = generate_exam_questions(profile_name, cefr)

    if err or not questions:
        st.error(f"⚠️ No pude generar el examen: {err or 'sin datos'}")
        return

    import random as _rand
    _rand.shuffle(questions)

    st.session_state.current_world = "exam"
    st.session_state.current_lesson_type = "exam"
    st.session_state.ex_questions = questions
    st.session_state.ex_index     = 0
    st.session_state.ex_correct   = 0
    st.session_state.ex_answers   = [None] * len(questions)
    st.session_state.ex_finished  = False
    st.session_state.ex_chosen    = None
    st.session_state.selected_world = None
    st.session_state.view = "home"


def start_shadow_speaking(world_key: str, world_topic: str):
    """Inicia Shadow Speaking (Estudio de Sonido): el alumno escucha una frase
    y la repite, la IA evalúa la similitud fonética."""
    profile_name = st.session_state.current_user
    cefr = get_cefr_info(
        next(
            (e["total_xp"] for e in get_leaderboard()
             if e["profile"] == profile_name),
            0
        )
    )["code"]

    with st.spinner("🎵 Preparando frases para imitar..."):
        phrases, err = generate_shadow_phrases(profile_name, cefr)

    if err or not phrases:
        st.error(f"⚠️ No pude generar frases: {err or 'sin datos'}")
        return

    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "shadow_speak"
    st.session_state.ss_phrases     = phrases
    st.session_state.ss_index       = 0
    st.session_state.ss_results     = []
    st.session_state.ss_last_audio  = None
    st.session_state.ss_last_score  = None
    st.session_state.ss_finished    = False
    st.session_state.selected_world = None
    st.session_state.view = "home"


def start_translate_inverse(world_key: str, world_topic: str):
    """Inicia Traducción Inversa (Taller de Letras)."""
    profile_name = st.session_state.current_user
    cefr = get_cefr_info(
        next(
            (e["total_xp"] for e in get_leaderboard()
             if e["profile"] == profile_name),
            0
        )
    )["code"]

    with st.spinner("✍️ Preparando oraciones para traducir..."):
        items, err = generate_translate_items(profile_name, cefr)

    if err or not items:
        st.error(f"⚠️ No pude generar oraciones: {err or 'sin datos'}")
        return

    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "translate_inv"
    st.session_state.ti_items       = items
    st.session_state.ti_index       = 0
    st.session_state.ti_answers     = [""] * len(items)
    st.session_state.ti_feedback    = [None] * len(items)
    st.session_state.ti_evaluating  = False
    st.session_state.ti_finished    = False
    st.session_state.selected_world = None
    st.session_state.view = "home"


def start_describe_scene(world_key: str, world_topic: str):
    """Inicia Describe la Escena (Taller de Letras)."""
    profile_name = st.session_state.current_user
    cefr = get_cefr_info(
        next(
            (e["total_xp"] for e in get_leaderboard()
             if e["profile"] == profile_name),
            0
        )
    )["code"]

    with st.spinner("🎨 Preparando escenas..."):
        scenes, err = generate_scene_descriptions(profile_name, cefr)

    if err or not scenes:
        st.error(f"⚠️ No pude generar escenas: {err or 'sin datos'}")
        return

    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "describe_scene"
    st.session_state.ds_scenes      = scenes
    st.session_state.ds_index       = 0
    st.session_state.ds_answers     = [""] * len(scenes)
    st.session_state.ds_feedback    = [None] * len(scenes)
    st.session_state.ds_evaluating  = False
    st.session_state.ds_finished    = False
    st.session_state.selected_world = None
    st.session_state.view = "home"


def start_minimal_pairs(world_key: str, world_topic: str):
    """Inicia el modo Pares Mínimos (Estudio de Sonido)."""
    profile_name = st.session_state.current_user
    cefr = get_cefr_info(
        next(
            (e["total_xp"] for e in get_leaderboard()
             if e["profile"] == profile_name),
            0
        )
    )["code"]

    with st.spinner("👂 Preparando pares mínimos..."):
        pairs, err = generate_minimal_pairs(profile_name, cefr)

    if err or not pairs:
        st.error(f"⚠️ No pude generar pares: {err or 'sin datos'}")
        return

    # Para cada par, elegir aleatoriamente cuál palabra "se dice" (correct_idx 0 o 1)
    import random as _rand
    prepared = []
    for p in pairs:
        correct_idx = _rand.choice([0, 1])
        prepared.append({
            "word_a": p["word_a"], "meaning_a": p.get("meaning_a", ""),
            "word_b": p["word_b"], "meaning_b": p.get("meaning_b", ""),
            "correct_idx": correct_idx,
        })

    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "min_pairs"
    st.session_state.mp_pairs       = prepared
    st.session_state.mp_index       = 0
    st.session_state.mp_correct     = 0
    st.session_state.mp_chosen      = None
    st.session_state.mp_finished    = False
    st.session_state.mp_audio       = None
    st.session_state.selected_world = None
    st.session_state.view = "home"


def start_listen_id(world_key: str, world_topic: str):
    """Inicia el modo ¿Qué escuché? — escucha la palabra correcta y elige
    entre 4 tarjetas escritas. Reutiliza flashcards pero AL REVÉS (audio→texto)."""
    profile_name = st.session_state.current_user
    cefr = get_cefr_info(
        next(
            (e["total_xp"] for e in get_leaderboard()
             if e["profile"] == profile_name),
            0
        )
    )["code"]

    with st.spinner("👂 Preparando ejercicio de escucha..."):
        cards, err = generate_listen_id_cards(profile_name, world_topic, cefr)

    if err or not cards:
        st.error(f"⚠️ No pude generar tarjetas: {err or 'sin datos'}")
        return

    import random as _rand
    prepared = []
    for c in cards:
        opts = [c["word"]] + (c.get("distractors") or [])[:3]
        while len(opts) < 4:
            opts.append("???")
        opts = opts[:4]
        _rand.shuffle(opts)
        correct_idx = opts.index(c["word"]) if c["word"] in opts else 0
        prepared.append({
            "word":        c["word"],
            "meaning":     c.get("meaning", ""),
            "emoji":       c.get("emoji", "🔊"),
            "options":     opts,
            "correct_idx": correct_idx,
        })

    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "listen_id"
    st.session_state.li_cards       = prepared
    st.session_state.li_index       = 0
    st.session_state.li_correct     = 0
    st.session_state.li_chosen      = None
    st.session_state.li_finished    = False
    st.session_state.li_audio       = None
    st.session_state.selected_world = None
    st.session_state.view = "home"


def start_memory_match(world_key: str, world_topic: str):
    """Inicia Memory Match (exclusivo de Bóveda de Vocabulario): genera 6
    parejas palabra-emoji, las mezcla en 12 cartas boca abajo."""
    profile_name = st.session_state.current_user
    cefr = get_cefr_info(
        next(
            (e["total_xp"] for e in get_leaderboard()
             if e["profile"] == profile_name),
            0
        )
    )["code"]

    with st.spinner("🧠 Preparando el tablero de memoria..."):
        pairs, err = generate_memory_pairs(profile_name, world_topic, cefr)

    if err or not pairs:
        st.error(f"⚠️ No pude generar parejas: {err or 'sin datos'}")
        return

    import random as _rand
    cards = []
    for pid, p in enumerate(pairs):
        cards.append({"id": pid * 2,     "kind": "emoji", "value": p["emoji"], "word": p["word"], "meaning": p.get("meaning", ""), "pair_id": pid})
        cards.append({"id": pid * 2 + 1, "kind": "word",  "value": p["word"],  "word": p["word"], "meaning": p.get("meaning", ""), "pair_id": pid})
    _rand.shuffle(cards)

    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "memory_match"
    st.session_state.mm_pairs       = cards
    st.session_state.mm_flipped     = []
    st.session_state.mm_matched     = []
    st.session_state.mm_attempts    = 0
    st.session_state.mm_first       = None
    st.session_state.mm_finished    = False
    st.session_state.selected_world = None
    st.session_state.view = "home"


def start_srs_review(profile_name: str):
    """Inicia el modo SRS: trae cards vencidas y arma el estado."""
    cards = get_due_srs_cards(profile_name, limit=12)
    st.session_state.srs_active     = True
    st.session_state.srs_cards      = cards
    st.session_state.srs_index      = 0
    st.session_state.srs_revealed   = False
    st.session_state.srs_correct    = 0
    st.session_state.srs_attempted  = 0
    st.session_state.srs_finished   = False
    st.session_state.current_world  = "srs"
    st.session_state.current_lesson_type = "srs_review"
    st.session_state.selected_world = None
    st.session_state.view = "home"


# ==========================================
# CONVERSATION MODE HELPERS
# ==========================================

# ==========================================
# ROLE-PLAY SCENARIOS (Café Conversación)
# ==========================================
ROLEPLAY_SCENARIOS = [
    {
        "key": "cafe_order", "emoji": "🍔", "cefr": "A1",
        "name": "Pedir en un café",
        "context": "You are a waiter at a friendly café. The student is a hungry customer.",
        "role_user": "Cliente hambriento en un café",
        "role_ai":   "Mesera/o amable del café",
        "objectives": [
            "Saludar (Hi / Hello)",
            "Pedir algo de comer",
            "Pedir algo de beber",
            "Pedir la cuenta",
            "Despedirse amablemente",
        ],
    },
    {
        "key": "new_friend", "emoji": "🎒", "cefr": "A1",
        "name": "Conocer a alguien en la escuela",
        "context": "You are a friendly classmate meeting the student for the first time at school.",
        "role_user": "Estudiante nuevo en la escuela",
        "role_ai":   "Compañero/a curioso/a y amable",
        "objectives": [
            "Saludar y presentarte (decir tu nombre)",
            "Decir tu edad o de dónde vienes",
            "Mencionar UN hobby tuyo",
            "Preguntar UN hobby al otro",
            "Quedar en verse otra vez",
        ],
    },
    {
        "key": "doctor", "emoji": "🏥", "cefr": "A2",
        "name": "Visita al doctor",
        "context": "You are a kind doctor. The student is a patient who is not feeling well.",
        "role_user": "Paciente con molestias",
        "role_ai":   "Doctor/a paciente y profesional",
        "objectives": [
            "Saludar al doctor",
            "Decir qué te duele (dolor de cabeza, garganta, etc.)",
            "Decir hace cuánto tiempo lo sientes",
            "Hacer UNA pregunta al doctor",
            "Despedirte y agradecer",
        ],
    },
    {
        "key": "shopping", "emoji": "🛒", "cefr": "A2",
        "name": "Comprar ropa",
        "context": "You are a shop assistant in a clothing store. The student is a customer looking for something.",
        "role_user": "Cliente buscando ropa",
        "role_ai":   "Vendedor/a servicial de la tienda",
        "objectives": [
            "Saludar a la vendedora",
            "Decir qué tipo de prenda buscas",
            "Decir el color o talla que quieres",
            "Preguntar el precio",
            "Decidir si lo compras o no",
        ],
    },
    {
        "key": "airport", "emoji": "✈️", "cefr": "B1",
        "name": "Pasar por el aeropuerto",
        "context": "You are an airport security officer. The student is a traveler going through security.",
        "role_user": "Viajero/a en seguridad del aeropuerto",
        "role_ai":   "Oficial educado/a de seguridad",
        "objectives": [
            "Saludar al oficial",
            "Mostrar/mencionar tu pasaporte y boleto",
            "Responder qué llevas en la mochila",
            "Decir el motivo del viaje",
            "Despedirte y desear buen día",
        ],
    },
    {
        "key": "movie_chat", "emoji": "🎬", "cefr": "B1",
        "name": "Recomendar una película",
        "context": "You are a friend who loves movies. The student wants a recommendation.",
        "role_user": "Amigo/a aburrido/a buscando peli",
        "role_ai":   "Amigo/a cinéfilo/a entusiasta",
        "objectives": [
            "Saludar y decir qué te apetece ver",
            "Decir UN género que te gusta (acción, comedia, etc.)",
            "Decir UN género que NO te gusta",
            "Preguntar de qué trata la peli recomendada",
            "Aceptar o rechazar la recomendación",
        ],
    },
    {
        "key": "library", "emoji": "📚", "cefr": "A1",
        "name": "Pedir un libro en la biblioteca",
        "context": "You are a kind librarian. The student wants to borrow a book.",
        "role_user": "Estudiante buscando un libro",
        "role_ai":   "Bibliotecaria/o amable",
        "objectives": [
            "Saludar a la bibliotecaria",
            "Decir qué tipo de libro buscas (cuento, ciencia, etc.)",
            "Mencionar UN tema que te guste",
            "Preguntar cuántos días puedes tener el libro",
            "Despedirte agradeciendo",
        ],
    },
    {
        "key": "birthday", "emoji": "🎂", "cefr": "A1",
        "name": "Invitar a alguien a tu cumpleaños",
        "context": "You are a classmate. The student wants to invite you to their birthday party.",
        "role_user": "Cumpleañera/o invitando",
        "role_ai":   "Compañero/a curioso/a",
        "objectives": [
            "Saludar al compañero",
            "Decir cuándo es tu cumpleaños",
            "Decir dónde será la fiesta",
            "Decir UNA cosa que harán (torta, juegos, piscina)",
            "Pedirle que confirme si va o no",
        ],
    },
    {
        "key": "hotel", "emoji": "🏨", "cefr": "A2",
        "name": "Hacer check-in en un hotel",
        "context": "You are a receptionist at a hotel. The student is a guest checking in.",
        "role_user": "Huésped con reserva",
        "role_ai":   "Recepcionista profesional",
        "objectives": [
            "Saludar al recepcionista",
            "Decir tu nombre y que tienes una reserva",
            "Mencionar cuántas noches te quedas",
            "Preguntar a qué hora es el desayuno",
            "Pedir la llave/key y despedirte",
        ],
    },
    {
        "key": "haircut", "emoji": "💇", "cefr": "A2",
        "name": "Cortarte el pelo",
        "context": "You are a hair stylist at a salon. The student is a client.",
        "role_user": "Cliente en la peluquería",
        "role_ai":   "Peluquera/o amable",
        "objectives": [
            "Saludar y decir que quieres cortarte el pelo",
            "Decir cuánto quieres que te corte (mucho, poco, las puntas)",
            "Mencionar si quieres algo extra (lavado, secado)",
            "Preguntar cuánto cuesta",
            "Pagar y despedirte",
        ],
    },
    {
        "key": "friend_problem", "emoji": "😟", "cefr": "B1",
        "name": "Resolver un problema con un amigo",
        "context": "You are a close friend the student had a fight with. The student wants to apologize and fix things.",
        "role_user": "Amigo/a que quiere pedir disculpas",
        "role_ai":   "Amigo/a herido/a pero abierto/a a escuchar",
        "objectives": [
            "Saludar y pedir hablar",
            "Reconocer qué hiciste mal",
            "Pedir disculpas con sinceridad",
            "Proponer cómo arreglar la situación",
            "Acordar volver a ser amigos",
        ],
    },
    {
        "key": "job_interview", "emoji": "💼", "cefr": "B2",
        "name": "Mini entrevista de trabajo",
        "context": "You are an interviewer for a summer part-time job. The student is a teenage candidate.",
        "role_user": "Adolescente buscando trabajo de verano",
        "role_ai":   "Entrevistador/a profesional pero amable",
        "objectives": [
            "Saludarte y presentarte",
            "Decir qué edad tienes y qué estudias",
            "Mencionar UNA fortaleza tuya",
            "Decir por qué quieres el trabajo",
            "Preguntar UNA cosa sobre el puesto y despedirte",
        ],
    },
]


def get_scenario_by_key(key: str):
    for s in ROLEPLAY_SCENARIOS:
        if s["key"] == key:
            return s
    return None


def _build_conversation_system_prompt(profile_name: str, world_meta: dict,
                                       cefr_code: str = "A1",
                                       scenario: dict = None) -> str:
    """System prompt para modo conversación. La IA actúa como personaje
    temático del mundo y conversa en inglés al nivel CEFR de la alumna/o.
    Si hay scenario activo, la IA actúa según ese rol de role-play."""
    profile  = PROFILES[profile_name]
    gender   = profile.get("gender", "niña")
    age_desc = profile.get("age_desc", "13 años")

    # Si hay role-play scenario activo, usar ese contexto
    if scenario:
        objs_list = "\n".join(
            f"  {i+1}. {o}" for i, o in enumerate(scenario["objectives"])
        )
        return f"""
You are role-playing: {scenario['role_ai']}.
Scene: {scenario['context']}

You are talking with {profile_name}, a {gender} of {age_desc}, who is playing the role of: {scenario['role_user']}.

CEFR LEVEL: {cefr_code} — adjust your English accordingly (simple grammar/vocab for A1, more complex for B1+).

OBJECTIVES the student should complete during the conversation:
{objs_list}

CONVERSATION RULES:
1. ALWAYS answer in English first, in 1-3 short sentences appropriate to the level.
2. Then add a single line in Spanish prefixed with "🇪🇸:" giving a brief gloss/help.
3. End every response with ONE follow-up question or prompt that PUSHES the student
   toward completing the next objective.
4. If the student's PREVIOUS message had a clear grammar/vocab issue, add a SHORT tip line in Spanish prefixed with "💡:" — example: "💡: Recuerda usar 'I am' en vez de 'I be'."
5. The tip is OPTIONAL — only include it if there's something CONCRETE and ÚTIL to teach. If the student wrote well, OMIT the tip entirely (don't include the 💡: line). NEVER force a tip just to fill space.
6. STAY IN CHARACTER — you are {scenario['role_ai']}, not a teacher.
7. Be encouraging and patient. The student is a teen learning English.
8. NEVER give a paragraph longer than 4 lines.
9. NO markdown headers, just plain text + optional 🇪🇸: gloss + optional 💡: tip.

OUTPUT FORMAT (in this order):
English reply (1-3 sentences ending with a question/prompt)
🇪🇸: brief Spanish gloss
💡: optional tip (only if there's a real, specific lesson)

START: Greet the student in English warmly, in character, and ask the FIRST opening
question that fits the scenario (e.g., a waiter would say "Welcome! What can I get you?").
On the FIRST turn, do NOT include a 💡: tip (the student hasn't said anything yet).
"""

    # Conversación libre (modo legacy sin scenario)
    profile  = PROFILES[profile_name]
    gender   = profile.get("gender", "niña")
    age_desc = profile.get("age_desc", "13 años")

    # Personaje según el mundo
    persona = {
        "Galaxia Gramatical":  "Captain Grammar, an experienced space explorer who teaches grammar through stories of the cosmos",
        "Bóveda de Vocabulario": "Wordsmith Quinn, a friendly librarian who loves teaching new words",
        "Galería de Arte":     "Art curator Maya, passionate about painting and creative expression",
        "Sala de Conciertos":  "Maestro Leo, a music teacher who connects English with musical concepts",
        "Arena Olímpica":      "Coach Riley, an enthusiastic gymnastics coach who motivates through sports",
        "Cabina de Vuelo":     "Pilot Captain Jordan, who teaches English through aviation and medical adventures",
        "Sala de Boss Battle": "Game master Pixel, who turns conversations into RPG-style quests",
        "Campamento Sinfónico": "Scout leader Sam, sharing nature and music adventures around a campfire",
        "Desafío Sorpresa":    "Mystery Mentor, a curious and clever tutor who always has surprises",
    }.get(world_meta.get("name", ""), "a friendly English tutor")

    return f"""
You are {persona}.
You are having a casual English conversation with {profile_name}, a {gender} of {age_desc}.

CEFR LEVEL OF STUDENT: {cefr_code} — adjust your English accordingly:
- A1: very simple sentences, basic vocab, present simple
- A2: short sentences, daily topics, present + past simple
- B1: more complex sentences, opinions, future + conditionals
- B2+: rich vocabulary, abstract topics, idioms

CONVERSATION RULES:
1. ALWAYS answer in English first, in 1-3 short sentences appropriate to the level.
2. Then add a single line in Spanish prefixed with "🇪🇸:" giving a brief gloss/help. Example: "🇪🇸: ¿Cuál es tu deporte favorito?"
3. End every response with ONE engaging follow-up question to keep the conversation flowing.
4. OPTIONAL tip: If the student's PREVIOUS message had a concrete grammar/vocab issue worth teaching, add a SHORT tip line in Spanish prefixed with "💡:" — example: "💡: Recuerda usar 'I am' en vez de 'I be'."
5. The 💡: tip is OPTIONAL — only include it if there's something CONCRETE to teach. If the student wrote well, OMIT the tip entirely. NEVER force a tip just to fill space. NEVER include a tip on the first turn.
6. Stay in character with the world's theme: {world_meta.get('tagline','')}
7. Be encouraging, never harsh. This is a teen learning English.
8. NEVER give a paragraph longer than 4 lines.
9. Respond in plain text, no markdown headers.

OUTPUT FORMAT (in this order):
English reply (1-3 sentences ending with a question)
🇪🇸: brief Spanish gloss
💡: optional tip (only if there's a real, specific lesson)

START: Greet {profile_name} in English warmly and ask an opening question related to your world's theme.
"""


def conversation_send(profile_name: str, world_meta: dict,
                       cefr_code: str, history: list,
                       scenario: dict = None) -> tuple:
    """Envía la conversación a Groq y devuelve (response_text, error).
    Si scenario está dado, la IA actúa según el rol del escenario."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    system_prompt = _build_conversation_system_prompt(
        profile_name, world_meta, cefr_code, scenario=scenario
    )
    messages = [{"role": "system", "content": system_prompt}] + history

    try:
        response = groq_client.chat.completions.create(
            messages=messages,
            model=GROQ_MODEL_CHAT,
            temperature=0.8,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip(), None
    except Exception as e:
        logger.error(f"Conversación Groq error: {e}")
        return None, f"Error de la API: {e}"


def summarize_conversation(scenario: dict, history: list,
                            profile_name: str = "") -> dict:
    """Genera un resumen pedagógico de la conversación: highlight phrase,
    new words used, 1 sugerencia. Devuelve dict o None."""
    if not history:
        return None
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None

    user_turns = [m["content"] for m in history if m["role"] == "user"]
    if not user_turns:
        return None

    scenario_desc = ""
    if scenario:
        scenario_desc = f"Scenario: {scenario['name']} ({scenario['role_user']} vs {scenario['role_ai']}).\n"

    transcript = "\n".join(f"- {t}" for t in user_turns[-12:])

    sys_prompt = f"""You are a kind English teacher reviewing a teen's English conversation.
{scenario_desc}

STUDENT'S MESSAGES (in order):
{transcript}

Return ONLY a JSON with this structure:
{{
  "highlight":  "<the best sentence the student wrote, in English, with quotes>",
  "new_words":  ["<word1>", "<word2>", "<word3>"],
  "suggestion": "<ONE concrete tip in Spanish to improve their English next time, 1 sentence>"
}}

RULES:
- "highlight" must be a real, well-built sentence the student actually wrote. If none stands out, pick the longest grammatically correct one.
- "new_words" must be 0-5 nice/relevant English words they used (no boilerplate like "I", "the", "is"). If none, return [].
- "suggestion" must be SPECIFIC and helpful (mention a real pattern they could improve), in friendly Spanish.
- Keep everything brief."""

    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": sys_prompt}],
            model=GROQ_MODEL_CHAT,
            temperature=0.3,
            max_tokens=350,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        return {
            "highlight":  (data.get("highlight") or "").strip(),
            "new_words":  [w.strip() for w in (data.get("new_words") or []) if w][:5],
            "suggestion": (data.get("suggestion") or "").strip(),
        }
    except Exception as e:
        logger.error(f"Error resumen conv: {e}")
        return None


def check_scenario_objectives(scenario: dict, history: list) -> list:
    """Pide al LLM evaluar qué objetivos del escenario ya se cumplieron
    según la historia del usuario. Devuelve lista de índices completados."""
    if not scenario or not history:
        return []
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return []

    # Construir transcripción del usuario (solo sus turnos)
    user_turns = [m["content"] for m in history if m["role"] == "user"]
    if not user_turns:
        return []

    objs_list = "\n".join(
        f"{i}. {o}" for i, o in enumerate(scenario["objectives"])
    )
    transcript = "\n".join(f"- {t}" for t in user_turns[-12:])

    sys_prompt = f"""You are a strict pedagogical evaluator. Determine which of the
student's objectives were already attempted/completed based on their messages.

OBJECTIVES (numbered):
{objs_list}

STUDENT MESSAGES:
{transcript}

Return ONLY a JSON object like {{"completed": [0, 2, 4]}} with the indices of objectives
that have been attempted by the student. Be GENEROUS: if they tried in English (even with errors), count it.
Do NOT count objectives that have not appeared at all in the messages."""

    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": sys_prompt}],
            model=GROQ_MODEL_CHAT,
            temperature=0.2,
            max_tokens=120,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        return [int(i) for i in data.get("completed", []) if isinstance(i, (int, str))]
    except Exception as e:
        logger.error(f"Error eval objectives: {e}")
        return []


# ==========================================
# PRONUNCIATION HELPERS
# ==========================================

def generate_pronunciation_words(profile_name: str, world_topic: str,
                                  cefr_code: str = "A1") -> tuple:
    """Pide al LLM 6 palabras o frases cortas para practicar pronunciación,
    relacionadas con el mundo. Devuelve (lista de dicts, error).
    Cada item: {word, ipa, meaning, emoji}"""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    profile = PROFILES.get(profile_name, {})
    sys_prompt = f"""
Eres un experto en pronunciación inglesa para hispanohablantes.
Generas listas de palabras o frases cortas para practicar pronunciación.

Nivel del/la alumno/a: {cefr_code}
Edad: {profile.get('age_desc', '13 años')}
Tema del mundo: {world_topic}

Devuelve SOLO un objeto JSON con esta estructura, sin texto antes ni después:
{{
  "words": [
    {{
      "word": "<palabra o frase corta en inglés (1-3 palabras)>",
      "ipa": "<transcripción IPA real del inglés americano>",
      "meaning": "<significado en español>",
      "emoji": "<un solo emoji visual representativo>"
    }}
  ]
}}

REGLAS:
- Genera EXACTAMENTE 6 palabras/frases.
- Mezcla dificultad: 2 fáciles, 3 medias, 1 difícil para hispanohablantes (sonidos como 'th', 'r' final, vocales 'i' vs 'ee').
- Las palabras deben ser temáticas al mundo del estudiante.
- Acordes al nivel CEFR ({cefr_code}).
- IPA debe ser real, no inventado.
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": f"Genera la lista para el tema: {world_topic[:200]}"}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.7,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        words = data.get("words", [])
        if not words:
            return None, "El modelo no devolvió palabras. Intenta de nuevo."
        return words[:6], None
    except Exception as e:
        logger.error(f"Error generando palabras de pronunciación: {e}")
        return None, f"Error al generar palabras: {e}"


def generate_sentences(profile_name: str, world_topic: str,
                        cefr_code: str = "A1") -> tuple:
    """Pide al LLM 5 oraciones cortas con traducción al español para el modo
    Constructor de Oraciones (mundo Gramatical). Devuelve (lista, error).
    Cada item: {spanish, english}."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    profile = PROFILES.get(profile_name, {})
    sys_prompt = f"""
Eres un profesor de inglés que diseña ejercicios de construcción de oraciones para niños hispanohablantes.

Nivel del/la alumno/a: {cefr_code}
Edad: {profile.get('age_desc', '13 años')}
Tema gramatical: {world_topic}

Devuelve SOLO un objeto JSON con esta estructura, sin texto antes ni después:
{{
  "sentences": [
    {{
      "spanish": "<oración en español, clara y simple>",
      "english": "<traducción al inglés, EXACTA, sin signos de puntuación final excepto punto>"
    }}
  ]
}}

REGLAS ESTRICTAS:
- Genera EXACTAMENTE 5 oraciones.
- Cada oración en inglés debe tener entre 4 y 7 palabras (ni más ni menos).
- Las palabras deben estar separadas por UN espacio simple.
- NO uses comas, comillas, puntos suspensivos. Solo letras y un punto final opcional.
- Las oraciones deben ser cortas y claras, ideales para reordenar palabras.
- Acordes al nivel CEFR ({cefr_code}) y al tema gramatical indicado.
- Variedad: no todas con el mismo verbo o estructura.
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": f"Genera 5 oraciones para: {world_topic[:200]}"}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.7,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        sents = data.get("sentences", [])
        # Validación: filtrar oraciones con longitud apropiada
        valid = []
        for s in sents:
            eng = (s.get("english") or "").strip().rstrip(".").strip()
            esp = (s.get("spanish") or "").strip()
            if not eng or not esp:
                continue
            words = eng.split()
            if 3 <= len(words) <= 8:
                valid.append({"spanish": esp, "english": eng})
        if not valid:
            return None, "El modelo no devolvió oraciones válidas. Intenta de nuevo."
        return valid[:5], None
    except Exception as e:
        logger.error(f"Error generando oraciones: {e}")
        return None, f"Error al generar oraciones: {e}"


def generate_translate_items(profile_name: str, cefr_code: str = "A1") -> tuple:
    """Pide al LLM 5 oraciones en español para traducir al inglés.
    Devuelve (lista de {spanish, english_correct, alt_translations}, error)."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    profile = PROFILES.get(profile_name, {})
    sys_prompt = f"""
Eres un profesor de inglés que prepara ejercicios de TRADUCCIÓN INVERSA (español → inglés)
para niños hispanohablantes.

Nivel CEFR: {cefr_code}
Edad: {profile.get('age_desc', '13 años')}

Devuelve SOLO un objeto JSON con esta estructura, sin texto antes ni después:
{{
  "items": [
    {{
      "spanish": "<oración natural en español, 5-12 palabras>",
      "english_correct": "<traducción correcta y natural al inglés>",
      "alt_translations": ["<otra forma válida 1>", "<otra forma válida 2>"]
    }}
  ]
}}

REGLAS:
- EXACTAMENTE 5 oraciones.
- Acordes al nivel CEFR {cefr_code} (frases simples para A1-A2, más complejas para B1+).
- Variedad: diferentes tiempos verbales, sujetos, temas.
- Las oraciones deben ser CONCRETAS y útiles en la vida real.
- "alt_translations" debe contener al menos 1 alternativa válida (sinónimos, orden, etc.).
- NUNCA uses signos de puntuación final salvo punto.
- NO escribas tildes en las palabras en inglés ni comillas dentro de los textos.
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": "Genera 5 oraciones para traducir."}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.7,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        items = data.get("items", [])
        valid = [
            {
                "spanish":          (it.get("spanish") or "").strip(),
                "english_correct":  (it.get("english_correct") or "").strip(),
                "alt_translations": [a.strip() for a in (it.get("alt_translations") or []) if a],
            }
            for it in items
            if it.get("spanish") and it.get("english_correct")
        ]
        if len(valid) < 3:
            return None, "El modelo no devolvió suficientes oraciones."
        return valid[:5], None
    except Exception as e:
        logger.error(f"Error generando traducciones: {e}")
        return None, f"Error al generar: {e}"


def generate_scene_descriptions(profile_name: str, cefr_code: str = "A1") -> tuple:
    """Pide al LLM 4 escenas (emoji-art) con prompts para describir en inglés.
    Devuelve (lista de {emoji_scene, prompt_es, sample_en}, error)."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    profile = PROFILES.get(profile_name, {})
    sys_prompt = f"""
Eres un creador de ejercicios visuales de inglés para niños hispanohablantes.

Nivel CEFR: {cefr_code}
Edad: {profile.get('age_desc', '13 años')}
Hobbies: {profile.get('hobbies', '')}

Devuelve SOLO un objeto JSON con esta estructura, sin texto antes ni después:
{{
  "scenes": [
    {{
      "emoji_scene": "<combinación de 4-8 emojis que representen una escena cotidiana>",
      "prompt_es":   "<pregunta breve EN ESPAÑOL que oriente la descripción>",
      "sample_en":   "<ejemplo modelo de respuesta correcta en inglés, 1-2 oraciones>"
    }}
  ]
}}

REGLAS:
- EXACTAMENTE 4 escenas.
- Cada "emoji_scene" debe ser una secuencia rica de emojis que sugiera una situación
  clara (ej: "🌧️🌂🚶‍♀️🌳" para "lluvia en el parque").
- "prompt_es" debe ser una pregunta o instrucción corta (ej: "Describe el clima y lo
  que está haciendo la persona.").
- "sample_en" debe ser una respuesta natural acorde al nivel CEFR {cefr_code}, 1-2 oraciones.
- Variedad: diferentes lugares, momentos del día, actividades.
- NO uses comillas dentro de los textos.
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": "Genera 4 escenas."}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.8,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        scenes = data.get("scenes", [])
        valid = [
            {
                "emoji_scene": (s.get("emoji_scene") or "").strip(),
                "prompt_es":   (s.get("prompt_es") or "").strip(),
                "sample_en":   (s.get("sample_en") or "").strip(),
            }
            for s in scenes
            if s.get("emoji_scene") and s.get("prompt_es")
        ]
        if len(valid) < 2:
            return None, "El modelo no devolvió suficientes escenas."
        return valid[:4], None
    except Exception as e:
        logger.error(f"Error generando escenas: {e}")
        return None, f"Error al generar: {e}"


def evaluate_writing(task_type: str, original: str,
                      user_text: str, reference: str = "",
                      cefr_code: str = "A1") -> dict:
    """Evalúa un texto escrito por el alumno. task_type: 'translation' o 'description'.
    Devuelve {score, correct, comment}."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return {"score": 0, "correct": reference or "(sin referencia)",
                "comment": "No pude evaluar: sin conexión al modelo."}

    if not user_text or not user_text.strip():
        return {"score": 0, "correct": reference,
                "comment": "No escribiste nada. Inténtalo de nuevo."}

    if task_type == "translation":
        task_desc = (
            f"El alumno tradujo del español al inglés.\n"
            f"Oración original en español: {original}\n"
            f"Traducción correcta esperada: {reference}\n"
            f"Lo que escribió el alumno: {user_text}\n"
        )
    else:  # description
        task_desc = (
            f"El alumno escribió una descripción en inglés de una escena.\n"
            f"Escena/instrucción: {original}\n"
            f"Ejemplo de buena respuesta: {reference}\n"
            f"Lo que escribió el alumno: {user_text}\n"
        )

    sys_prompt = f"""
Eres un profesor de inglés EVALUADOR amable pero preciso. Evalúas a un alumno hispanohablante
de nivel CEFR {cefr_code}.

{task_desc}

Devuelve SOLO un JSON con esta estructura:
{{
  "score":   <entero 0-100, qué tan correcta es la respuesta del alumno>,
  "correct": "<la versión correcta/mejorada en inglés>",
  "comment": "<1-2 oraciones de feedback en español, alentador pero específico sobre qué
              mejoró/falló: gramática, vocabulario, naturalidad, etc.>"
}}

REGLAS DE PUNTUACIÓN:
- 90-100: prácticamente perfecto, captura el sentido y la gramática.
- 70-89: bien con errores menores (artículo, preposición, tiempo verbal puntual).
- 50-69: comprensible pero con errores que afectan claridad.
- 25-49: parcialmente correcto, errores serios pero hay intento.
- 0-24: muy alejado o sin sentido.

REGLAS DE COMENTARIO:
- Empieza con UN punto positivo si lo hay.
- Mencionar el error específico si lo hay (ej: "Usa 'is' en lugar de 'are' aquí").
- Sé breve: máximo 2 oraciones.
- Habla siempre en español (es para un niño hispanohablante).
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": "Evalúa la respuesta del alumno."}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.3,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        return {
            "score":   max(0, min(100, int(data.get("score", 0)))),
            "correct": (data.get("correct") or reference).strip(),
            "comment": (data.get("comment") or "Buen intento.").strip(),
        }
    except Exception as e:
        logger.error(f"Error evaluando writing: {e}")
        return {"score": 50, "correct": reference,
                "comment": f"No pude evaluar bien. Aquí tienes la versión correcta."}


def generate_exam_questions(profile_name: str, cefr_code: str = "A1") -> tuple:
    """Genera un examen cumulativo de 10 preguntas mezclando skills:
    3 vocabulary MC, 2 grammar MC, 2 fill-in-the-blank, 2 translation, 1 reading comp.
    Devuelve (lista de preguntas con campo 'skill', error)."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    profile = PROFILES.get(profile_name, {})
    sys_prompt = f"""
You are an English teacher creating a CUMULATIVE WEEKLY EXAM for a Spanish-speaking teen.

Student: {profile_name} ({profile.get('age_desc', '13 años')})
CEFR Level: {cefr_code}

Return ONLY a JSON with this exact structure (no extra text):
{{
  "questions": [
    {{
      "skill":    "<one of: vocabulary | grammar | listening | reading | writing>",
      "type":     "<one of: mc | fitb | translation>",
      "q":        "<the question text>",
      "hint":     "<Spanish hint or translation context for fitb/translation; empty string for mc>",
      "options":  ["<A>", "<B>", "<C>", "<D>"],
      "answer":   "<exact correct answer text>"
    }}
  ]
}}

RULES — EXACTLY this distribution of 10 questions:
- 3 vocabulary MC (multiple choice asking word meaning or synonym)
- 2 grammar MC (multiple choice asking correct form/tense)
- 2 fitb (fill in the blank — sentence with ONE "___" gap, answer is ONE word)
- 2 translation (a Spanish sentence to translate to English; "answer" is the English version, "options" is empty list [])
- 1 reading comprehension MC (short text included in "q" + question — keep total under 40 words)

OTHER RULES:
- All "q" content MUST be in ENGLISH (except translation source which goes in "hint" as Spanish).
- For "translation": "q" contains the Spanish sentence to translate; "options" must be [].
- For "fitb": "q" must contain EXACTLY one "___" marker (3 underscores); "options" can be [] OR 4 word options.
- For all MC types: "options" must have EXACTLY 4 entries; "answer" must match one of them exactly.
- Acorde al nivel CEFR {cefr_code}.
- Variedad: cubrir diferentes temas (familia, escuela, comida, hobbies, etc.).
- NO use markdown, NO use asterisks, only plain text.
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": "Generate the 10-question cumulative exam."}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.6,
            max_tokens=1800,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        questions = data.get("questions", [])
        valid = []
        for q in questions:
            qtype = (q.get("type") or "").lower()
            if qtype not in ("mc", "fitb", "translation"):
                continue
            ans = (q.get("answer") or "").strip()
            text = (q.get("q") or "").strip()
            if not text or not ans:
                continue
            # Normalizar fitb (limpiar asteriscos del modelo si se cuelan)
            if qtype == "fitb":
                text = re.sub(r"\*+_+\*+", "___", text)
                text = re.sub(r"_+", "___", text)
            valid.append({
                "skill":   (q.get("skill") or "general").lower(),
                "type":    qtype,
                "q":       text,
                "hint":    (q.get("hint") or "").strip(),
                "options": q.get("options") or [],
                "answer":  ans,
            })
        if len(valid) < 6:
            return None, "El modelo no devolvió un examen completo."
        return valid[:10], None
    except Exception as e:
        logger.error(f"Error generando examen: {e}")
        return None, f"Error al generar examen: {e}"


def extract_error_pattern(wrong_items: list, cefr_code: str = "A1") -> dict:
    """Analiza una lista de errores [{q, correct, user_answer}] y devuelve
    el PATRÓN dominante para una micro-lección de refuerzo. Devuelve dict
    {pattern, hint, examples} o None si no hay patrón claro."""
    if not wrong_items:
        return None
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None

    errs_text = "\n".join(
        f"- Pregunta: {it.get('q', '')[:120]}\n"
        f"  Respuesta correcta: {it.get('correct', '')}\n"
        f"  Lo que el alumno respondió: {it.get('user_answer', '')}"
        for it in wrong_items[:6]
    )

    sys_prompt = f"""You are a pedagogical error analyzer for a Spanish-speaking English learner (CEFR {cefr_code}).

ANÁLISIS — el alumno respondió mal estas preguntas:
{errs_text}

Identifica EL PATRÓN dominante de error (UNA sola cosa).
Ejemplos de patrones: "confusion is/are", "missing -s en 3ra persona", "wrong preposition in/on/at", "pasado regular vs irregular", "uso de a/an".

Devuelve SOLO JSON:
{{
  "pattern":  "<nombre corto del patrón en español, 3-7 palabras>",
  "hint":     "<explicación breve en español, 1-2 oraciones>",
  "examples": ["<ejemplo en inglés 1>", "<ejemplo en inglés 2>", "<ejemplo en inglés 3>"]
}}

Si NO hay un patrón claro (los errores son aleatorios), devuelve {{"pattern": "", "hint": "", "examples": []}}.

RULES:
- "pattern" debe ser específico y enseñable, no vago.
- "examples" debe contener 3 oraciones cortas correctas en inglés que demuestren el patrón."""

    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": sys_prompt}],
            model=GROQ_MODEL_CHAT,
            temperature=0.3,
            max_tokens=350,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        if not data.get("pattern"):
            return None
        return {
            "pattern":  data["pattern"].strip(),
            "hint":     (data.get("hint") or "").strip(),
            "examples": [e.strip() for e in (data.get("examples") or []) if e][:3],
        }
    except Exception as e:
        logger.error(f"Error extract_error_pattern: {e}")
        return None


@st.cache_data(ttl=180, show_spinner=False)
def get_recent_lesson_topics(profile_name: str, n: int = 15) -> list:
    """Devuelve los últimos N topics que el alumno ya cubrió, para evitar
    repetición al generar contenido nuevo."""
    sheet, _ = get_db_connection()
    if not sheet:
        return []
    try:
        rows = sheet.get_all_records()
        user_rows = [r for r in rows if r.get("profile", "") == profile_name][-n:]
        topics = []
        for r in user_rows:
            w = (r.get("world") or "").strip()
            lt = (r.get("lesson_type") or "").strip()
            if w or lt:
                topics.append(f"{w}/{lt}")
        # Quitar duplicados manteniendo orden
        seen = set()
        unique = []
        for t in topics:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique[-n:]
    except Exception:
        return []


def generate_journal_prompt(profile_name: str, cefr_code: str = "A1") -> tuple:
    """Genera el prompt del día para Diario Hablado. Se basa en day-of-year
    + profile_name para que sea consistente dentro del día pero varíe entre días.
    Devuelve ({en, es, emoji}, error)."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    profile = PROFILES.get(profile_name, {})
    today = datetime.date.today()
    day_seed = today.toordinal() + hash(profile_name) % 100

    sys_prompt = f"""
You are creating a speaking prompt for a Spanish-speaking teen learning English.
The student will record themselves speaking for 30 seconds about this prompt.

Student: {profile_name} ({profile.get('age_desc', '13 años')})
Hobbies: {profile.get('hobbies', '')}
CEFR Level: {cefr_code}
Seed for variety: {day_seed}

Return ONLY a JSON with this structure:
{{
  "en":    "<the speaking prompt in English, a clear question 6-12 words long>",
  "es":    "<Spanish translation/context of the prompt>",
  "emoji": "<one fitting emoji>"
}}

RULES:
- The prompt should be a CONCRETE question the student can answer in 30 seconds.
- Examples: "What did you do yesterday?", "Tell me about your best friend.", "Describe your favorite food."
- Acorde al nivel CEFR {cefr_code} (simpler for A1, more abstract for B1+).
- Vary the topic: daily life, hobbies, opinions, memories, future plans.
- Avoid yes/no questions — prefer open-ended.
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": "Generate today's speaking prompt."}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.9,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        prompt = {
            "en":    (data.get("en") or "").strip(),
            "es":    (data.get("es") or "").strip(),
            "emoji": (data.get("emoji") or "🎤").strip(),
        }
        if not prompt["en"]:
            return None, "El modelo no devolvió un prompt válido."
        return prompt, None
    except Exception as e:
        logger.error(f"Error generando journal prompt: {e}")
        return None, f"Error al generar: {e}"


def evaluate_speaking_journal(prompt_en: str, transcript: str,
                                cefr_code: str = "A1") -> dict:
    """Evalúa una respuesta hablada (vía transcripción de Whisper).
    Devuelve {score, fluency, vocab, grammar, comment, model_answer}."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return {"score": 0, "comment": "Sin conexión.",
                "model_answer": "", "fluency": 0, "vocab": 0, "grammar": 0}

    if not transcript or not transcript.strip():
        return {"score": 0, "comment": "No te escuché. Inténtalo de nuevo.",
                "model_answer": "", "fluency": 0, "vocab": 0, "grammar": 0}

    sys_prompt = f"""
Evaluador de habla en inglés para un alumno hispano de nivel {cefr_code}.

PROMPT que se le hizo: {prompt_en}
LO QUE DIJO (transcrito): {transcript}

Devuelve SOLO JSON:
{{
  "score":        <0-100 entero, puntuación global>,
  "fluency":      <0-100, fluidez y duración>,
  "vocab":        <0-100, riqueza de vocabulario>,
  "grammar":      <0-100, corrección gramatical>,
  "comment":      "<2 oraciones en español: 1 positiva + 1 sugerencia concreta>",
  "model_answer": "<respuesta modelo en INGLÉS, 2-3 oraciones acorde al nivel {cefr_code}>"
}}

RULES:
- Si la transcripción es muy corta (<10 palabras), penaliza fluency.
- Si hay errores graves de gramática, baja grammar pero NO seas duro: alentar.
- model_answer debe ser una respuesta natural que el alumno podría aspirar.
- Habla siempre en español en "comment".
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": "Evalúa la respuesta."}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        return {
            "score":        max(0, min(100, int(data.get("score", 0)))),
            "fluency":      max(0, min(100, int(data.get("fluency", 0)))),
            "vocab":        max(0, min(100, int(data.get("vocab", 0)))),
            "grammar":      max(0, min(100, int(data.get("grammar", 0)))),
            "comment":      (data.get("comment") or "Buen intento.").strip(),
            "model_answer": (data.get("model_answer") or "").strip(),
        }
    except Exception as e:
        logger.error(f"Error evaluando diario: {e}")
        return {"score": 50, "fluency": 50, "vocab": 50, "grammar": 50,
                "comment": "No pude evaluar bien.", "model_answer": ""}


def generate_shadow_phrases(profile_name: str, cefr_code: str = "A1") -> tuple:
    """Pide al LLM 5 frases cortas, rítmicas y divertidas para Shadow Speaking.
    Mezcla trabalenguas suaves, frases con rima, y oraciones con ritmo claro.
    Devuelve (lista de {text, meaning, emoji}, error)."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    profile = PROFILES.get(profile_name, {})
    sys_prompt = f"""
You are an ESL pronunciation coach. Generate 5 short English phrases for SHADOW SPEAKING practice
(student listens to a model audio and tries to imitate the rhythm and intonation).

CEFR LEVEL: {cefr_code}
Age: {profile.get('age_desc', '13 años')}

Return ONLY a JSON with this structure:
{{
  "phrases": [
    {{
      "text":    "<short English phrase, 4-8 words, with clear rhythm>",
      "meaning": "<brief Spanish meaning>",
      "emoji":   "<one fun emoji that matches the phrase>"
    }}
  ]
}}

RULES:
- EXACTLY 5 phrases.
- Length: 4-8 words each (NOT longer).
- Variety: include 1 gentle tongue-twister, 1 rhyme, 1 question, 1 exclamation, 1 simple statement.
- Real, natural English that a teen could actually say.
- CEFR-appropriate vocab: simple for A1, more variety for A2+.
- NO complex punctuation: just letters, spaces, and optional final period.
- NO emojis inside the "text" field — emoji goes only in "emoji" field.
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": "Generate 5 shadow speaking phrases."}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.8,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        phrases = data.get("phrases", [])
        valid = [
            {
                "text":    (p.get("text") or "").strip().rstrip("."),
                "meaning": (p.get("meaning") or "").strip(),
                "emoji":   (p.get("emoji") or "🎵").strip(),
            }
            for p in phrases
            if p.get("text")
        ]
        if not valid:
            return None, "El modelo no devolvió frases válidas."
        return valid[:5], None
    except Exception as e:
        logger.error(f"Error generando shadow phrases: {e}")
        return None, f"Error al generar: {e}"


def generate_minimal_pairs(profile_name: str, cefr_code: str = "A1") -> tuple:
    """Pide al LLM 5 pares mínimos clásicos para hispanohablantes.
    Devuelve (lista de {pair:[w1,w2], meanings:[m1,m2]}, error).
    Ejemplos: ship/sheep, beach/peach, live/leave, bit/beat."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    sys_prompt = f"""
You are an expert ESL phonetics teacher specialized in Spanish-speaking learners.
Generate 5 MINIMAL PAIRS in English that Spanish speakers commonly confuse:
- Long vs short vowels: ship/sheep, bit/beat, live/leave, full/fool
- /b/ vs /v/: berry/very, bat/vat
- /s/ vs /th/: sin/thin, sink/think
- Final consonants: cap/cab, back/bag
- Other tricky pairs

CEFR LEVEL: {cefr_code} (keep words simple, A1-A2 vocab preferred).

Return ONLY a JSON with this exact structure:
{{
  "pairs": [
    {{
      "word_a":    "<first word>",
      "meaning_a": "<short Spanish meaning>",
      "word_b":    "<second word>",
      "meaning_b": "<short Spanish meaning>"
    }}
  ]
}}

RULES:
- EXACTLY 5 pairs.
- Each pair must differ by ONE sound only.
- Both words must be REAL English words with clear Spanish meanings.
- Variety: cover different sound contrasts across the 5 pairs.
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": "Generate 5 minimal pairs."}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.6,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        pairs = data.get("pairs", [])
        valid = [p for p in pairs
                 if p.get("word_a") and p.get("word_b")
                 and p["word_a"].lower() != p["word_b"].lower()]
        if not valid:
            return None, "El modelo no devolvió pares válidos."
        return valid[:5], None
    except Exception as e:
        logger.error(f"Error generando minimal pairs: {e}")
        return None, f"Error al generar pares: {e}"


def generate_listen_id_cards(profile_name: str, world_topic: str,
                              cefr_code: str = "A1") -> tuple:
    """Pide al LLM 6 palabras para el modo ¿Qué Escuché? (audio + 4 opciones).
    Reutiliza generate_flashcards (que ya devuelve word + 3 distractores)."""
    return generate_flashcards(profile_name, world_topic, cefr_code)


def generate_story_fill(profile_name: str, world_topic: str,
                         cefr_code: str = "A1") -> tuple:
    """Pide al LLM un cuento corto personalizado con 4-5 huecos.
    Cada hueco tiene 3 opciones de palabra (1 correcta + 2 distractores).
    Devuelve (dict story, error)."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    profile = PROFILES.get(profile_name, {})
    sys_prompt = f"""
Eres un escritor de cuentos cortos en inglés para niños hispanohablantes.

Nombre del/la niño/a: {profile_name}
Edad: {profile.get('age_desc', '13 años')}
Hobbies/intereses: {profile.get('hobbies', '')}
Nivel CEFR: {cefr_code}
Tema del mundo: {world_topic}

Devuelve SOLO un objeto JSON con esta estructura, sin texto antes ni después:
{{
  "title": "<título corto del cuento (3-6 palabras en inglés)>",
  "title_es": "<el mismo título traducido al español>",
  "sentences": [
    {{
      "text_before":   "<texto en inglés antes del hueco>",
      "blank_correct": "<la palabra correcta que va en el hueco (1-2 palabras)>",
      "text_after":    "<texto en inglés después del hueco>",
      "blank_options": ["<opción correcta>", "<distractor 1>", "<distractor 2>"],
      "spanish_hint":  "<TRADUCCIÓN al español de la oración COMPLETA y ya rellenada, para dar contexto>"
    }}
  ]
}}

REGLAS ESTRICTAS:
- EXACTAMENTE 4 oraciones, cada una con UN hueco.
- Cada oración debe ser CORTA (8-15 palabras totales).
- El cuento debe ser personalizado: usa los hobbies/intereses del/la niño/a
  para inventar una historia que le interese (su personaje principal puede
  llamarse como ella/él).
- Los 2 distractores deben ser palabras del mismo TIPO gramatical y nivel CEFR
  que la correcta (si la correcta es un verbo, los distractores son verbos).
- Los distractores deben ser PLAUSIBLES pero claramente incorrectos en contexto.
- "blank_options" debe contener 3 opciones: la correcta + 2 distractores
  (la correcta debe coincidir EXACTAMENTE con "blank_correct").
- "spanish_hint" es OBLIGATORIO: traducción al español de la oración COMPLETA ya rellenada,
  para que el/la niño/a entienda el contexto pero aún tenga que elegir entre opciones.
- Vocabulario y gramática acordes al nivel CEFR {cefr_code}.
- NO uses comillas dentro del texto. Solo letras, espacios y puntos finales.
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": f"Cuento personalizado para {profile_name} sobre: {world_topic[:200]}"}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.8,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        title = data.get("title", "Story")
        sents = data.get("sentences", [])
        # Validación
        valid = []
        for s in sents:
            correct = (s.get("blank_correct") or "").strip()
            opts = [o.strip() for o in (s.get("blank_options") or []) if o]
            if not correct or correct not in opts or len(opts) < 2:
                continue
            valid.append({
                "text_before":   (s.get("text_before") or "").strip(),
                "blank_correct": correct,
                "text_after":    (s.get("text_after") or "").strip(),
                "blank_options": opts[:3],
                "spanish_hint":  (s.get("spanish_hint") or "").strip(),
            })
        if len(valid) < 2:
            return None, "El modelo no devolvió un cuento válido. Intenta de nuevo."
        title_es = (data.get("title_es") or "").strip()
        return {"title": title, "title_es": title_es,
                "sentences": valid[:4]}, None
    except Exception as e:
        logger.error(f"Error generando story fill: {e}")
        return None, f"Error al generar cuento: {e}"


def generate_memory_pairs(profile_name: str, world_topic: str,
                           cefr_code: str = "A1") -> tuple:
    """Pide al LLM 6 parejas palabra-emoji para el modo Memory Match.
    Devuelve (lista de {word, emoji, meaning}, error)."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    profile = PROFILES.get(profile_name, {})
    sys_prompt = f"""
Eres un experto en enseñanza de vocabulario inglés para niños hispanohablantes.

Nivel del/la alumno/a: {cefr_code}
Edad: {profile.get('age_desc', '13 años')}
Tema del mundo: {world_topic}

Devuelve SOLO un objeto JSON con esta estructura, sin texto antes ni después:
{{
  "pairs": [
    {{
      "word": "<palabra simple en inglés (1 palabra, máximo 2)>",
      "emoji": "<un solo emoji muy visual y CLARO>",
      "meaning": "<significado breve en español>"
    }}
  ]
}}

REGLAS ESTRICTAS:
- Genera EXACTAMENTE 6 parejas (12 cartas para el juego).
- Las palabras deben ser CONCRETAS y VISUALES (objetos, animales, comida, etc).
- Cada emoji debe representar SIN AMBIGÜEDAD su palabra.
- 6 emojis DIFERENTES entre sí — no se pueden repetir.
- 6 palabras DIFERENTES entre sí — no se pueden repetir.
- Acordes al nivel CEFR ({cefr_code}) y a la temática del mundo.
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": f"Genera 6 parejas para: {world_topic[:200]}"}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.7,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        pairs = data.get("pairs", [])
        pairs = [p for p in pairs if p.get("word") and p.get("emoji")]
        if len(pairs) < 4:
            return None, "El modelo no devolvió suficientes parejas. Intenta de nuevo."
        return pairs[:6], None
    except Exception as e:
        logger.error(f"Error generando parejas: {e}")
        return None, f"Error al generar parejas: {e}"


def generate_flashcards(profile_name: str, world_topic: str,
                         cefr_code: str = "A1") -> tuple:
    """Pide al LLM 6 tarjetas de vocabulario para el modo Flashcards Visuales.
    Cada tarjeta tiene: palabra, significado en español, emoji y 3 distractores
    (palabras incorrectas plausibles del mismo nivel y temática).
    Devuelve (lista de dicts, error)."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    profile = PROFILES.get(profile_name, {})
    sys_prompt = f"""
Eres un experto en enseñanza de vocabulario inglés para niños hispanohablantes.

Nivel del/la alumno/a: {cefr_code}
Edad: {profile.get('age_desc', '13 años')}
Tema del mundo: {world_topic}

Devuelve SOLO un objeto JSON con esta estructura, sin texto antes ni después:
{{
  "cards": [
    {{
      "word": "<palabra simple en inglés (1-2 palabras max)>",
      "meaning": "<significado breve en español>",
      "emoji": "<un solo emoji muy visual representando la palabra>",
      "ipa": "<transcripción IPA opcional, puede ir vacía>",
      "distractors": ["<palabra incorrecta 1>", "<palabra incorrecta 2>", "<palabra incorrecta 3>"]
    }}
  ]
}}

REGLAS ESTRICTAS:
- Genera EXACTAMENTE 6 tarjetas.
- Las palabras deben ser CONCRETAS y VISUALES (objetos, animales, comida, acciones).
  Evita palabras abstractas que no tengan emoji claro.
- Los 3 distractores deben ser palabras del mismo nivel CEFR y MISMA categoría
  semántica que la correcta (ej: si "cat" es la correcta, distractores podrían ser
  "dog", "bird", "fish" — NO "table", "blue", "run").
- Distractores plausibles pero claramente diferentes; no sinónimos ni palabras
  que también podrían ser correctas.
- El emoji debe representar SIN AMBIGÜEDAD la palabra correcta.
- Acorde al nivel CEFR ({cefr_code}) y a la temática del mundo.
"""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": f"Genera 6 tarjetas para: {world_topic[:200]}"}
            ],
            model=GROQ_MODEL_CHAT,
            temperature=0.7,
            max_tokens=900,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw.lstrip("```json").lstrip("```").rstrip("```").strip())
        cards = data.get("cards", [])
        # Validación mínima
        cards = [c for c in cards if c.get("word") and c.get("meaning")]
        if not cards:
            return None, "El modelo no devolvió tarjetas. Intenta de nuevo."
        return cards[:6], None
    except Exception as e:
        logger.error(f"Error generando flashcards: {e}")
        return None, f"Error al generar tarjetas: {e}"


def _normalize_text(s: str) -> str:
    """Limpia para comparación: minúsculas, sin puntuación, espacios colapsados."""
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9'\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _phonemize_word(word: str) -> str:
    """Convierte una palabra inglesa a una secuencia de fonemas IPA usando phonemizer.
    Devuelve string vacío si phonemizer no está disponible."""
    try:
        from phonemizer import phonemize  # type: ignore
        result = phonemize(
            word, language="en-us", backend="espeak",
            strip=True, preserve_punctuation=False
        )
        return str(result).strip()
    except Exception:
        return ""


def _levenshtein(a: str, b: str) -> int:
    """Distancia de edición simple entre dos strings."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(cur[j-1] + 1, prev[j] + 1, prev[j-1] + cost))
        prev = cur
    return prev[-1]


def score_pronunciation(target: str, transcribed: str) -> dict:
    """
    Devuelve dict con: score (0-100), tier ('good'|'mid'|'bad'),
    method ('exact'|'phoneme'|'char'), heard (lo que entendió Whisper).
    """
    t_norm = _normalize_text(target)
    s_norm = _normalize_text(transcribed)

    # Match exacto → 100
    if t_norm == s_norm and t_norm:
        return {"score": 100, "tier": "good", "method": "exact",
                "heard": transcribed}

    # Intentar match por fonemas (phonemizer + espeak)
    target_ph = _phonemize_word(t_norm)
    spoken_ph = _phonemize_word(s_norm)

    if target_ph and spoken_ph:
        max_len = max(len(target_ph), len(spoken_ph), 1)
        dist    = _levenshtein(target_ph, spoken_ph)
        score   = max(0, int(round((1 - dist / max_len) * 100)))
        method  = "phoneme"
    else:
        # Fallback: comparación por caracteres
        max_len = max(len(t_norm), len(s_norm), 1)
        dist    = _levenshtein(t_norm, s_norm)
        score   = max(0, int(round((1 - dist / max_len) * 100)))
        method  = "char"

    if score >= 80:
        tier = "good"
    elif score >= 55:
        tier = "mid"
    else:
        tier = "bad"

    return {"score": score, "tier": tier, "method": method,
            "heard": transcribed}


# ==========================================
# SRS (Spaced Repetition System) HELPERS
# ==========================================

def _ensure_srs_sheet():
    """Garantiza que existe la pestaña 'srs' con headers correctos.
    Devuelve el worksheet o None."""
    sheet, _ = get_db_connection()
    if not sheet:
        return None
    try:
        spreadsheet = sheet.spreadsheet
        try:
            srs_ws = spreadsheet.worksheet("srs")
        except gspread.exceptions.WorksheetNotFound:
            srs_ws = spreadsheet.add_worksheet(title="srs", rows=2000, cols=10)
            srs_ws.append_row([
                "profile", "word", "translation", "emoji",
                "ease", "interval_days", "repetitions",
                "next_review", "last_review", "lapses"
            ])
        return srs_ws
    except Exception as e:
        logger.warning(f"No se pudo asegurar pestaña srs: {e}")
        return None


@st.cache_data(ttl=120, show_spinner=False)
def get_srs_cards(profile_name: str) -> list[dict]:
    """Devuelve todas las cards del perfil en SRS."""
    srs_ws = _ensure_srs_sheet()
    if not srs_ws:
        return []
    try:
        rows = srs_ws.get_all_records()
        return [r for r in rows
                if str(r.get("profile", "")).strip() == profile_name]
    except Exception as e:
        logger.warning(f"Error leyendo SRS: {e}")
        return []


def get_due_srs_count(profile_name: str) -> int:
    """Cuenta cuántas cards están vencidas (next_review <= hoy)."""
    cards = get_srs_cards(profile_name)
    today = datetime.date.today()
    n = 0
    for c in cards:
        try:
            nr = datetime.datetime.strptime(
                str(c.get("next_review", "")), "%Y-%m-%d"
            ).date()
            if nr <= today:
                n += 1
        except (ValueError, TypeError):
            n += 1  # cards sin fecha cuentan como pendientes
    return n


def get_due_srs_cards(profile_name: str, limit: int = 12) -> list[dict]:
    """Devuelve las cards vencidas, ordenadas por más antiguas primero."""
    cards = get_srs_cards(profile_name)
    today = datetime.date.today()
    due = []
    for c in cards:
        try:
            nr = datetime.datetime.strptime(
                str(c.get("next_review", "")), "%Y-%m-%d"
            ).date()
            if nr <= today:
                c["_due_date"] = nr
                due.append(c)
        except (ValueError, TypeError):
            c["_due_date"] = datetime.date(2000, 1, 1)
            due.append(c)
    due.sort(key=lambda x: x.get("_due_date") or datetime.date.today())
    return due[:limit]


def add_srs_card(profile_name: str, word: str,
                  translation: str, emoji: str = "📝") -> bool:
    """Agrega una nueva card al SRS si no existe ya esa palabra."""
    srs_ws = _ensure_srs_sheet()
    if not srs_ws:
        return False
    try:
        # Evitar duplicados (mismo profile + word)
        existing = get_srs_cards(profile_name)
        word_l = word.strip().lower()
        for c in existing:
            if str(c.get("word", "")).strip().lower() == word_l:
                return False  # ya existe

        today = datetime.date.today().strftime("%Y-%m-%d")
        srs_ws.append_row([
            profile_name, word.strip(), translation.strip(), emoji,
            2.5, 1, 0, today, "", 0
        ])
        get_srs_cards.clear()
        return True
    except Exception as e:
        logger.warning(f"Error agregando SRS: {e}")
        return False


def update_srs_card(profile_name: str, word: str, quality: int) -> bool:
    """
    Actualiza una card SRS según el algoritmo SM-2 simplificado.
    quality: 0 (no la sabía) | 1 (difícil, casi) | 2 (bien) | 3 (perfecto)
    """
    srs_ws = _ensure_srs_sheet()
    if not srs_ws:
        return False
    try:
        rows = srs_ws.get_all_records()
        word_l = word.strip().lower()
        for idx, r in enumerate(rows, start=2):  # +2 = header offset
            if (str(r.get("profile", "")).strip() == profile_name
                    and str(r.get("word", "")).strip().lower() == word_l):

                ease = float(r.get("ease", 2.5) or 2.5)
                interval = int(r.get("interval_days", 1) or 1)
                reps = int(r.get("repetitions", 0) or 0)
                lapses = int(r.get("lapses", 0) or 0)

                if quality <= 0:
                    # Falló: reset
                    reps = 0
                    interval = 1
                    lapses += 1
                    ease = max(1.3, ease - 0.2)
                else:
                    reps += 1
                    if reps == 1:
                        interval = 1
                    elif reps == 2:
                        interval = 3
                    else:
                        interval = max(1, int(round(interval * ease)))
                    # Ajuste de ease por calidad
                    delta = {1: -0.15, 2: 0.0, 3: 0.15}.get(quality, 0)
                    ease = max(1.3, min(3.0, ease + delta))

                today = datetime.date.today()
                next_review = today + datetime.timedelta(days=interval)
                today_s = today.strftime("%Y-%m-%d")
                next_s  = next_review.strftime("%Y-%m-%d")

                # Update fila completa (cols 5-10: ease, interval, reps, next, last, lapses)
                srs_ws.update(
                    f"E{idx}:J{idx}",
                    [[round(ease, 2), interval, reps, next_s, today_s, lapses]]
                )
                get_srs_cards.clear()
                return True
        return False
    except Exception as e:
        logger.warning(f"Error actualizando SRS: {e}")
        return False


def extract_vocab_from_lesson(lesson_text: str) -> list[dict]:
    """Extrae palabras de vocabulario del texto Markdown de la lección.
    Busca el patrón: '- 🦋 **butterfly** [ipa] — mariposa'.
    Devuelve lista de dicts {word, translation, emoji} (máx 10)."""
    if not lesson_text:
        return []
    out = []
    # Pattern flexible: - [opcional prefijo no-letras] **word** [opt ipa] — translation
    # Captura todo lo que esté antes de **word** (suele ser emoji + espacio).
    pattern = re.compile(
        r"^\s*-\s+(.*?)"
        r"\*\*([A-Za-z][A-Za-z\s'-]{0,30})\*\*"
        r"\s*(?:\[[^\]]+\])?"
        r"\s*[—–\-:]\s*([^\n]+)",
        re.MULTILINE
    )
    for m in pattern.finditer(lesson_text):
        prefix = (m.group(1) or "").strip()
        word   = (m.group(2) or "").strip()
        trans  = (m.group(3) or "").strip()
        # Extraer el primer caracter "raro" (emoji) del prefijo
        emoji = "📝"
        if prefix:
            non_ascii = [c for c in prefix if ord(c) > 127]
            if non_ascii:
                emoji = non_ascii[0]
        # Limpiar traducción de cursivas, etc.
        trans = re.sub(r"[*_`]", "", trans).strip()
        if word and trans and len(out) < 10:
            out.append({"word": word, "translation": trans, "emoji": emoji})
    return out


def build_battle_questions(quiz_data: dict) -> list[dict]:
    """Convierte el JSON de la lección en una lista de preguntas mezcladas
    para el modo batalla. Mezcla MC y FITB, ~8 preguntas máximo."""
    import random as _random
    questions = []
    for q in quiz_data.get("mc", []):
        questions.append({
            "type":    "mc",
            "q":       q.get("q", ""),
            "options": q.get("options", []),
            "answer":  q.get("answer", ""),
        })
    for q in quiz_data.get("fitb", []):
        sentence = q.get("sentence", "")
        # Normalizar: si el modelo puso "**___**" o variantes, dejar solo "___"
        sentence = re.sub(r"\*+_+\*+", "___", sentence)
        sentence = re.sub(r"_+", "___", sentence)
        questions.append({
            "type":    "fitb",
            "q":       sentence,
            "options": [],
            "answer":  q.get("answer", ""),
            "hint":    q.get("hint", ""),
        })
    _random.shuffle(questions)
    return questions[:8]   # capped a 8 para que la batalla sea ágil


# ==========================================
# 5. MANEJO DE ESTADO (Session State)
# ==========================================
_STATE_DEFAULTS = {
    "current_user":    None,
    "view":            "home",       # home | arena | profile
    "selected_world":  None,         # cuando set, muestra world entry page
    "xp":              0,
    "quiz_data":       None,
    "lesson_error":    None,
    "lesson_pending":  False,
    "quiz_result":     None,
    "quiz_attempts":   0,
    "last_text_input": "",
    "lesson_audio":    None,   # bytes MP3 cacheados del audio de la lección
    "current_world":   "",     # mundo elegido para la lección actual
    "current_lesson_type": "", # tipo de lección (lesson_quiz | battle)
    # Battle mode state
    "battle_index":      0,
    "battle_hp":         100,
    "battle_max_hp":     100,
    "battle_streak":     0,
    "battle_max_streak": 0,
    "battle_correct":    0,
    "battle_total":      0,
    "battle_questions":  None,    # lista normalizada [{type, q, options?, answer}]
    "battle_finished":   False,
    "battle_feedback":   None,    # último feedback {is_correct, ...}
    "battle_history":    None,    # lista completa de feedbacks por pregunta
    "battle_mc_answer":  None,    # selección MC pendiente
    "battle_fitb_answer": "",     # input FITB pendiente
    # Pronunciation mode state
    "pron_words":      None,      # lista de {word, ipa, meaning, emoji}
    "pron_index":      0,
    "pron_results":    None,      # lista de scores por palabra
    "pron_last_audio": None,
    "pron_last_score": None,      # último resultado de score_pronunciation
    "pron_finished":   False,
    # Conversation mode state
    "conv_active":   False,
    "conv_history":  None,        # [{role, content}, ...]
    "conv_turn_count": 0,
    "conv_pending_user_input": "",
    # SRS state
    "srs_active":    False,
    "srs_cards":     None,
    "srs_index":     0,
    "srs_revealed":  False,
    "srs_correct":   0,
    "srs_attempted": 0,
    "srs_finished":  False,
    # Flashcards Visuales (Bóveda de Vocabulario)
    "fc_cards":      None,    # lista de {word, meaning, emoji, options:[4 strings shuffled], correct_idx}
    "fc_index":      0,
    "fc_correct":    0,
    "fc_attempted":  0,
    "fc_finished":   False,
    "fc_chosen":     None,    # índice seleccionado en la tarjeta actual (None = aún no contesta)
    "fc_audio":      None,    # bytes MP3 del audio actual
    # Sentence Builder (Galaxia Gramatical) — palabras desordenadas a ordenar
    "sb_sentences":  None,    # lista de {spanish, english, scrambled:[words], target:[words]}
    "sb_index":      0,
    "sb_placed":     None,    # lista de índices de palabras ya colocadas en orden
    "sb_correct":    0,
    "sb_attempted":  0,
    "sb_finished":   False,
    "sb_revealed":   False,   # si ya validó la oración actual
    "sb_last_ok":    None,    # True/False de la última validación
    # Memory Match (Bóveda de Vocabulario) — parejas imagen-palabra
    "mm_pairs":      None,    # lista de {id, kind:'emoji'|'word', value, pair_id} (12 items: 6 parejas)
    "mm_flipped":    None,    # set de ids actualmente boca arriba (no matched)
    "mm_matched":    None,    # set de pair_ids ya emparejados
    "mm_attempts":   0,
    "mm_first":      None,    # id de la primera carta del par en curso
    "mm_finished":   False,
    # Story Fill (Mundo Personal) — cuento personalizado con huecos a completar
    "sf_story":      None,    # dict {title, sentences:[{text, blank_correct, blank_options, picked_idx}]}
    "sf_index":      0,
    "sf_picked":     None,    # lista paralela a sentences: índice elegido o None
    "sf_revealed":   False,   # si ya validó todas las elecciones (pantalla final)
    "sf_correct":    0,
    "sf_finished":   False,
    # Role-Play en Café Conversación
    "rp_scenario":   None,    # dict del escenario activo (key, name, role_user, role_ai, objectives, emoji)
    "rp_done_objs":  None,    # set de índices de objetivos completados
    "rp_picker":     False,   # True cuando se muestra el selector de escenarios
    "conv_summary":  None,    # dict {highlight, new_words, suggestion} para mostrar al cerrar
    "conv_show_end": False,   # True cuando se muestra la pantalla de resumen final
    # Pares Mínimos (Estudio de Sonido)
    "mp_pairs":      None,    # lista de {pair: [w1, w2], correct_idx (0 o 1), meaning_a, meaning_b}
    "mp_index":      0,
    "mp_correct":    0,
    "mp_chosen":     None,    # 0|1 o None
    "mp_finished":   False,
    "mp_audio":      None,
    # Listen ID (¿Qué escuché?) en Estudio de Sonido
    "li_cards":      None,    # lista de {word, meaning, emoji, options:[4 strings], correct_idx, audio}
    "li_index":      0,
    "li_correct":    0,
    "li_chosen":     None,
    "li_finished":   False,
    "li_audio":      None,
    # Traducción Inversa (Taller de Letras) — ES→EN
    "ti_items":      None,    # lista de {spanish, english_correct}
    "ti_index":      0,
    "ti_answers":    None,    # lista de strings (lo que el usuario escribió)
    "ti_feedback":   None,    # lista de dicts {score, correct, comment} tras evaluar
    "ti_evaluating": False,
    "ti_finished":   False,
    # Describe la Escena (Taller de Letras)
    "ds_scenes":     None,    # lista de {emoji_scene, prompt, sample}
    "ds_index":      0,
    "ds_answers":    None,
    "ds_feedback":   None,
    "ds_evaluating": False,
    "ds_finished":   False,
    # Shadow Speaking (Estudio de Sonido) — imitar frases rítmicas
    "ss_phrases":    None,    # lista de {text, ipa, meaning, emoji}
    "ss_index":      0,
    "ss_results":    None,    # lista de scores por frase
    "ss_last_audio": None,
    "ss_last_score": None,
    "ss_finished":   False,
    # Modo Examen (test cumulativo de fin de semana)
    "ex_questions":  None,    # lista de preguntas heterogéneas {type, q, options, answer, hint, skill}
    "ex_index":      0,
    "ex_correct":    0,
    "ex_answers":    None,    # respuestas del alumno, por pregunta
    "ex_finished":   False,
    "ex_chosen":     None,    # respuesta pendiente (para form)
    # Acceso a Dashboard de Padres
    "parent_mode":   False,   # True cuando se ingresó contraseña correctamente
    "parent_password_error": None,
    # Diario Hablado (Speaking Journal) — habla libre con feedback
    "dh_prompt":     None,    # {en, es, emoji} prompt del día
    "dh_audio":      None,    # bytes del audio grabado
    "dh_transcript": None,    # transcripción de Whisper
    "dh_feedback":   None,    # {score, correct, comment} del LLM
    "dh_finished":   False,
    # Error tracking
    "last_error_topic":  None,   # {pattern, hint, examples} para mostrar refuerzo
    "error_dismissed":   False,  # True si el usuario cerró el card del error
    # Save-to-Sheets pipeline (anti-XP-fantasma)
    "pending_xp_save_args": None,  # dict con args para reintento
    "last_save_error":      None,  # último error string si la última save falló
    "flash_success":        None,  # mensaje de éxito a mostrar tras el rerun
}
for key, default in _STATE_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ==========================================
# 6. INTERFAZ DE USUARIO
# ==========================================

# ── DASHBOARD DE PADRES (protegido por contraseña) ──
def _get_parent_password() -> str:
    """Obtiene la contraseña de padres desde secrets, o fallback."""
    try:
        return str(st.secrets.get("parent_password", "padres1234"))
    except Exception:
        return "padres1234"


if st.session_state.get("parent_mode"):
    # === DASHBOARD DE PADRES ===
    st.markdown("""
        <div class='welcome-container'>
            <h1>👨‍👩‍👧 Dashboard de Padres</h1>
            <p>Resumen de progreso de cada niño</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("← Volver a perfiles", key="parent_back", type="secondary"):
        st.session_state.parent_mode = False
        st.rerun()

    st.write("")

    # Iterar sobre cada perfil y mostrar estadísticas
    for prof_name, prof in PROFILES.items():
        st.markdown(
            f"<h3 class='parent-kid-header' style='color:{prof['color']}; text-shadow:0 0 12px {prof['color']};'>"
            f"{prof['emoji']} {prof_name}</h3>",
            unsafe_allow_html=True
        )

        stats = get_user_stats(prof_name)
        streak = get_streak_days(prof_name)
        skill_data = get_skill_breakdown(prof_name)
        weakest_sk, weakest_meta = get_weakest_skill(prof_name)

        # Tarjeta de overview
        st.markdown(
            f"<div class='parent-card'>"
            f"<div class='parent-overview'>"
            f"<div class='parent-stat'><div class='parent-stat-val' style='color:{prof['color']};'>{stats['total_xp']}</div><div class='parent-stat-lbl'>XP Total</div></div>"
            f"<div class='parent-stat'><div class='parent-stat-val'>{stats['total_sessions']}</div><div class='parent-stat-lbl'>Lecciones</div></div>"
            f"<div class='parent-stat'><div class='parent-stat-val'>{stats['avg_score']*100:.0f}%</div><div class='parent-stat-lbl'>Promedio</div></div>"
            f"<div class='parent-stat'><div class='parent-stat-val'>{stats['week_xp']}</div><div class='parent-stat-lbl'>XP semana</div></div>"
            f"<div class='parent-stat'><div class='parent-stat-val'>🔥 {streak}</div><div class='parent-stat-lbl'>Racha</div></div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True
        )

        # Skills breakdown - barras
        skills_html = "<div class='parent-card'>"
        skills_html += "<p class='summary-section'>📊 Desempeño por habilidad</p>"
        max_xp_skill = max((skill_data[s]["xp"] for s in skill_data), default=1) or 1
        for sk in ["vocabulary", "grammar", "listening", "speaking", "writing", "reading"]:
            d = skill_data[sk]
            pct_bar = (d["xp"] / max_xp_skill * 100) if max_xp_skill else 0
            avg_pct = d["avg_score"] * 100
            sk_color = "#39ff14" if avg_pct >= 80 else "#ffd400" if avg_pct >= 55 else "#ff5351"
            if d["sessions"] == 0:
                sk_color = "#3a3d40"
            skills_html += (
                f"<div class='parent-skill-row'>"
                f"<span class='parent-skill-name'>{sk}</span>"
                f"<span class='parent-skill-bar'><span style='width:{pct_bar}%; background:{sk_color};'></span></span>"
                f"<span class='parent-skill-stats'>{d['xp']} XP · {d['sessions']} sesiones · {avg_pct:.0f}%</span>"
                f"</div>"
            )
        skills_html += (
            f"<p style='margin: 10px 0 0; color: var(--text-secondary); font-size:0.85rem;'>"
            f"💡 <b>Sugerencia:</b> Practicar <b style='color:{prof['color']};'>{weakest_meta['emoji']} {weakest_meta['name']}</b> "
            f"(habilidad con menos práctica).</p>"
            f"</div>"
        )
        st.markdown(skills_html, unsafe_allow_html=True)

        # Últimas 10 sesiones (timeline)
        sheet, _ = get_db_connection()
        recent_html = "<div class='parent-card'><p class='summary-section'>🕒 Últimas 10 sesiones</p>"
        if sheet:
            try:
                rows = sheet.get_all_records()
                user_rows = [r for r in rows if r.get("profile", "") == prof_name][-10:][::-1]
                if user_rows:
                    for r in user_rows:
                        ts = r.get("timestamp", "—")
                        wld = r.get("world", "—") or "—"
                        lt = r.get("lesson_type", "—") or "—"
                        xp = r.get("xp", 0)
                        sc = r.get("score_pct", "—")
                        recent_html += (
                            f"<div class='parent-row'>"
                            f"<span class='parent-row-ts'>{ts}</span>"
                            f"<span class='parent-row-mid'>{wld} · {lt}</span>"
                            f"<span class='parent-row-end'>+{xp} XP · {sc}</span>"
                            f"</div>"
                        )
                else:
                    recent_html += "<p style='color: var(--text-dim); margin:0;'>Aún no hay sesiones registradas.</p>"
            except Exception as e:
                recent_html += f"<p style='color: var(--text-dim);'>No se pudo leer: {e}</p>"
        recent_html += "</div>"
        st.markdown(recent_html, unsafe_allow_html=True)

        st.write("")

    # Refrescar caché
    if st.button("🔄 Refrescar datos", key="parent_refresh", type="secondary"):
        for fn in (get_user_stats, get_skill_breakdown,
                   get_streak_days, get_today_session_count):
            try: fn.clear()
            except Exception: pass
        st.rerun()

    st.stop()


if st.session_state.current_user is None:
    st.markdown("""
        <div class='welcome-container'>
            <h1>⚡ IdiomaConnect</h1>
            <p>Elige tu perfil de combate · Sistema de aprendizaje activado</p>
        </div>
    """, unsafe_allow_html=True)

    # ── Acceso a Dashboard de Padres (con contraseña) ──
    if "show_parent_login" not in st.session_state:
        st.session_state.show_parent_login = False

    if not st.session_state.show_parent_login:
        if st.button("🔒 Dashboard de padres", key="parent_login_btn",
                     use_container_width=True, type="secondary"):
            st.session_state.show_parent_login = True
            st.rerun()
    else:
        st.markdown(
            "<div class='diag-panel'>"
            "<p style='font-size:0.92rem; color:var(--text-primary); margin:0 0 10px; font-weight:600;'>"
            "🔒 Acceso solo para padres</p>"
            "<p style='font-size:0.82rem; color:#a8acb3; margin:0 0 8px;'>"
            "Ingresa la contraseña para ver el progreso de los niños.</p>"
            "</div>",
            unsafe_allow_html=True
        )
        with st.form("parent_login_form", clear_on_submit=True):
            pw_input = st.text_input(
                "Contraseña", type="password",
                placeholder="•••••••",
                label_visibility="collapsed",
                key="parent_pw_field"
            )
            col_pw1, col_pw2 = st.columns(2)
            with col_pw1:
                submit_pw = st.form_submit_button(
                    "✓ Entrar", use_container_width=True, type="primary"
                )
            with col_pw2:
                cancel_pw = st.form_submit_button(
                    "✕ Cancelar", use_container_width=True, type="secondary"
                )
        if cancel_pw:
            st.session_state.show_parent_login = False
            st.session_state.parent_password_error = None
            st.rerun()
        if submit_pw:
            if pw_input == _get_parent_password():
                st.session_state.parent_mode = True
                st.session_state.show_parent_login = False
                st.session_state.parent_password_error = None
                st.rerun()
            else:
                st.session_state.parent_password_error = "Contraseña incorrecta. Intenta de nuevo."
        if st.session_state.get("parent_password_error"):
            st.markdown(
                f"<p style='color:#ff5351; font-size:0.85rem; margin: 6px 0;'>"
                f"⚠ {st.session_state.parent_password_error}</p>",
                unsafe_allow_html=True
            )

    # ── Diagnóstico de conexión (toggle manual sin st.expander) ──
    if "show_diag" not in st.session_state:
        st.session_state.show_diag = False

    diag_label = "🛠️ Ocultar diagnóstico" if st.session_state.show_diag else "🛠️ Diagnóstico de conexión"
    if st.button(diag_label, key="diag_toggle", use_container_width=True, type="secondary"):
        st.session_state.show_diag = not st.session_state.show_diag
        st.rerun()

    if st.session_state.show_diag:
        st.markdown("<div class='diag-panel'>", unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:0.85rem; color:#a8acb3; margin:0 0 8px;'>"
            "Si el XP no se guarda entre sesiones, revisa aquí.</p>",
            unsafe_allow_html=True
        )
        status, msg, sa_email = check_db_status()

        if status == "ok":
            st.markdown(
                f"<span class='conn-pill ok'>✅ {msg}</span>",
                unsafe_allow_html=True
            )
        elif status == "warn":
            st.markdown(
                f"<span class='conn-pill warn'>⚠ {msg}</span>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<span class='conn-pill fail'>✗ {msg}</span>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"<p style='margin: 10px 0 6px; font-size:0.85rem;'>"
                f"<b>Acción:</b> agrega este email como Editor en tu Google Sheets "
                f"<i>Idiomaconnect_DB</i>:</p>"
                f"<div style='text-align:center; margin: 6px 0;'>"
                f"<span class='sa-email'>{sa_email}</span></div>",
                unsafe_allow_html=True
            )

        col_d1, col_d2 = st.columns([1, 2])
        with col_d1:
            if st.button("🔁 Reintentar conexión", key="diag_retry",
                         use_container_width=True, type="secondary"):
                try:
                    get_db_connection.clear()
                except Exception:
                    pass
                st.rerun()
        with col_d2:
            st.caption(f"Service account: `{sa_email}`")
        st.markdown("</div>", unsafe_allow_html=True)

    profile_list = list(PROFILES.items())
    groups = [profile_list[:3], profile_list[3:]]

    for g_idx, group in enumerate(groups):
        if not group:
            continue
        if g_idx > 0:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        cols = st.columns(3)
        for j, (name, pdata) in enumerate(group):
            with cols[j]:
                accent = pdata["color"]
                avatar_url = get_avatar_for(name)
                hobby_short = pdata["hobbies"].split(',')[0].strip()

                if avatar_url:
                    avatar_html = (
                        f"<div class='avatar-ring'>"
                        f"<img src='{avatar_url}' alt='{name}' "
                        f"onerror=\"this.style.display='none'; "
                        f"this.parentElement.innerHTML='{pdata['emoji']}';"
                        f"this.parentElement.classList.add('avatar-emoji');"
                        f"this.parentElement.classList.remove('avatar-ring');\" />"
                        f"</div>"
                    )
                else:
                    avatar_html = f"<div class='avatar-emoji'>{pdata['emoji']}</div>"

                st.markdown(
                    f"<div class='profile-card' style='--profile-accent: {accent};'>"
                    f"{avatar_html}"
                    f"<h2>{name}</h2>"
                    f"<p>{hobby_short}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                if st.button(f"Activar {name}", key=f"btn_{name}", use_container_width=True):
                    for k, v in _STATE_DEFAULTS.items():
                        st.session_state[k] = v
                    st.session_state.current_user = name
                    st.rerun()

else:
    user  = st.session_state.current_user
    pdata = PROFILES[user]
    color = pdata["color"]

    # Inyectar el accent del perfil como CSS variable global
    # (el dashboard, lesson y quiz containers la usan)
    st.markdown(
        f"<style>:root, .stApp {{ --profile-accent: {color}; }}</style>",
        unsafe_allow_html=True
    )

    # --- STATS (se carga primero para mostrar XP total en el encabezado) ---
    stats = get_user_stats(user)
    # XP a mostrar: total guardado en Sheets + lo ganado en esta sesión (aún no guardado)
    displayed_xp = stats["total_xp"] + st.session_state.xp

    # --- ENCABEZADO ---
    avatar_url = get_avatar_for(user)
    avatar_inline = (
        f"<img src='{avatar_url}' alt='{user}' "
        f"style='width:42px; height:42px; border-radius:50%; object-fit:cover; "
        f"border:2px solid {color}; box-shadow:0 0 12px {color}; margin-right:12px;' "
        f"onerror=\"this.style.display='none';\" />"
        if avatar_url else ""
    )
    st.markdown(f"""
        <div class='dashboard-header'>
            <h2 style='display:flex; align-items:center;'>
                {avatar_inline}
                <span>Hola, {user}</span>
            </h2>
            <span class='xp-display'>⚡ {displayed_xp} XP</span>
        </div>
    """, unsafe_allow_html=True)

    # --- PANEL DE PROGRESO ACUMULADO (desde Google Sheets) ---
    if stats["total_sessions"] > 0:
        st.markdown(f"""
            <div class='progress-panel'>
                <div class='stat-item'>
                    <div class='stat-value' style='color:{color} !important; text-shadow:0 0 10px {color};'>{stats["total_xp"]}</div>
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
                    <div class='stat-label'>Promedio</div>
                </div>
                <div class='stat-divider'></div>
                <div class='stat-item'>
                    <div class='stat-value' style='color:#ffd400 !important; text-shadow:0 0 10px #ffd400;'>{stats["week_xp"]}</div>
                    <div class='stat-label'>Semana</div>
                </div>
                <div class='stat-divider'></div>
                <div class='stat-item'>
                    <div class='stat-value' style='color:#39ff14 !important; text-shadow:0 0 10px #39ff14;'>{stats["best_score"]:.0%}</div>
                    <div class='stat-label'>Récord</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ── Barra de navegación (Home / Arena / Profile) ─────────────────
    current_view = st.session_state.get("view", "home")
    nav_items = [
        ("home",    "🗺️  Mundos"),
        ("arena",   "⚔️  Arena"),
        ("profile", "👤  Perfil"),
    ]
    # Claves de estado que pertenecen a una lección/quiz activo
    _LESSON_KEYS = [
        "selected_world", "quiz_data", "lesson_error", "lesson_pending",
        "quiz_result", "quiz_attempts", "last_text_input", "lesson_audio",
        "current_world", "current_lesson_type",
        "battle_index", "battle_hp", "battle_max_hp", "battle_streak",
        "battle_max_streak", "battle_correct", "battle_total",
        "battle_questions", "battle_finished", "battle_feedback",
        "battle_history", "battle_mc_answer", "battle_fitb_answer",
        "pron_words", "pron_index", "pron_results", "pron_last_audio",
        "pron_last_score", "pron_finished",
        "conv_active", "conv_history", "conv_turn_count", "conv_pending_user_input",
        "srs_active", "srs_cards", "srs_index", "srs_revealed",
        "srs_correct", "srs_attempted", "srs_finished",
        "fc_cards", "fc_index", "fc_correct", "fc_attempted",
        "fc_finished", "fc_chosen", "fc_audio",
        "sb_sentences", "sb_index", "sb_placed", "sb_correct",
        "sb_attempted", "sb_finished", "sb_revealed", "sb_last_ok",
        "mm_pairs", "mm_flipped", "mm_matched", "mm_attempts",
        "mm_first", "mm_finished",
        "sf_story", "sf_index", "sf_picked", "sf_revealed",
        "sf_correct", "sf_finished",
        "rp_scenario", "rp_done_objs", "rp_picker",
        "conv_summary", "conv_show_end",
        "mp_pairs", "mp_index", "mp_correct", "mp_chosen",
        "mp_finished", "mp_audio",
        "li_cards", "li_index", "li_correct", "li_chosen",
        "li_finished", "li_audio",
        "ti_items", "ti_index", "ti_answers", "ti_feedback",
        "ti_evaluating", "ti_finished",
        "ds_scenes", "ds_index", "ds_answers", "ds_feedback",
        "ds_evaluating", "ds_finished",
        "ss_phrases", "ss_index", "ss_results", "ss_last_audio",
        "ss_last_score", "ss_finished",
        "ex_questions", "ex_index", "ex_correct", "ex_answers",
        "ex_finished", "ex_chosen",
        "dh_prompt", "dh_audio", "dh_transcript", "dh_feedback",
        "dh_finished",
    ]

    nav_cols = st.columns(len(nav_items))
    for i, (v_key, label) in enumerate(nav_items):
        is_active = (current_view == v_key)
        with nav_cols[i]:
            # Activo = primary (rojo neón), inactivo = secondary (cyan ghost)
            if st.button(
                label,
                key=f"nav_{v_key}",
                use_container_width=True,
                type=("primary" if is_active else "secondary"),
            ):
                st.session_state.view = v_key
                # Al volver al mapa de mundos, cancela cualquier lección activa
                if v_key == "home":
                    for k in _LESSON_KEYS:
                        if k in _STATE_DEFAULTS:
                            st.session_state[k] = _STATE_DEFAULTS[k]
                st.rerun()

    if st.button("← Cambiar perfil", type="secondary"):
        for k, v in _STATE_DEFAULTS.items():
            st.session_state[k] = v
        st.rerun()

    # ════════════════════════════════════════════════════════════════
    # VISTAS: ARENA / PROFILE — se renderizan y detienen el flujo aquí
    # (la vista HOME continúa más abajo con el mapa de mundos + lección)
    # ════════════════════════════════════════════════════════════════
    if current_view == "arena":
        st.markdown("""
            <div class='arena-hero'>
                <h2>⚔️ ARENA DE COMPETICIÓN</h2>
                <p>Ranking semanal · Reset cada lunes</p>
            </div>
        """, unsafe_allow_html=True)

        leaderboard = get_leaderboard()

        # Filtrar perfiles sin actividad reciente al final, pero mostrarlos siempre
        for idx, entry in enumerate(leaderboard, start=1):
            name      = entry["profile"]
            pdata_lb  = PROFILES.get(name, {})
            accent_lb = pdata_lb.get("color", "#00eefc")
            avatar    = get_avatar_for(name)
            is_self   = (name == user)

            row_classes = ["leaderboard-row"]
            if idx == 1: row_classes.append("rank-1")
            elif idx == 2: row_classes.append("rank-2")
            elif idx == 3: row_classes.append("rank-3")
            if is_self: row_classes.append("is-self")
            row_class = " ".join(row_classes)

            if avatar:
                avatar_html = (
                    f"<div class='lb-avatar'>"
                    f"<img src='{avatar}' alt='{name}' "
                    f"onerror=\"this.parentElement.innerHTML='"
                    f"<div class=&quot;lb-avatar-fallback&quot;>{pdata_lb.get('emoji','⭐')}</div>';\" />"
                    f"</div>"
                )
            else:
                avatar_html = (
                    f"<div class='lb-avatar-fallback'>{pdata_lb.get('emoji','⭐')}</div>"
                )

            sessions_str = (
                f"{entry['total_sessions']} lecciones · {entry['avg_score']:.0%} promedio"
                if entry['total_sessions'] > 0 else "Aún sin actividad"
            )

            st.markdown(
                f"<div class='{row_class}' style='--lb-accent: {accent_lb};"
                f" --profile-accent: {accent_lb};'>"
                f"<div class='lb-rank'>#{idx}</div>"
                f"{avatar_html}"
                f"<div class='lb-info'>"
                f"<p class='lb-name'>{name}{' · TÚ' if is_self else ''}</p>"
                f"<p class='lb-meta'>{sessions_str}</p>"
                f"</div>"
                f"<div class='lb-xp'>"
                f"<div class='lb-xp-num'>{entry['week_xp']}</div>"
                f"<div class='lb-xp-label'>XP semana</div>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown(
            "<p style='text-align:center; color:#6b7280; font-size:0.78rem;"
            " margin-top:14px; letter-spacing:1px; text-transform:uppercase;'>"
            "✦ El ranking se reinicia cada lunes ✦</p>",
            unsafe_allow_html=True
        )

    # ════════════════════════════════════════════════════════════════
    # VISTA: PROFILE (CEFR + trofeos + stats detalladas)
    # ════════════════════════════════════════════════════════════════
    elif current_view == "profile":
        # Buscar entry del usuario en el leaderboard (para perfect_count, active_days, world_counts)
        leaderboard = get_leaderboard()
        my_entry = next((e for e in leaderboard if e["profile"] == user), None) or {
            "total_xp": 0, "total_sessions": 0, "avg_score": 0.0,
            "best_score": 0.0, "perfect_count": 0, "last_activity": None,
            "world_counts": {}, "active_days": 0,
        }

        # ── Tarjeta CEFR ──
        cefr = get_cefr_info(my_entry["total_xp"])
        st.markdown(f"""
            <div class='cefr-card'>
                <p style='color:#6b7280; font-size:0.72rem; letter-spacing:2px;
                          text-transform:uppercase; margin:0;'>Nivel actual estimado</p>
                <p class='cefr-level'>{cefr['code']}</p>
                <p class='cefr-rank-name'>{cefr['name']}</p>
                <p class='cefr-rank-tagline'>{cefr['tagline']}</p>
                <div class='cefr-progress-wrap'>
                    <div class='cefr-progress-fill' style='width:{cefr['progress']*100:.1f}%;'></div>
                </div>
                <p class='cefr-next'>{cefr['next_label']}</p>
            </div>
        """, unsafe_allow_html=True)

        # ── Badges / Logros ──
        earned_keys = set(compute_earned_badges(user))
        total_badges = len(BADGE_DEFINITIONS)
        st.markdown(
            f"<p class='worlds-section-title'>🏅 LOGROS · {len(earned_keys)}/{total_badges}</p>",
            unsafe_allow_html=True
        )
        badges_html = "<div class='badges-grid'>"
        for b in BADGE_DEFINITIONS:
            is_earned = (b["key"] in earned_keys)
            cls = "badge-earned" if is_earned else "badge-locked"
            badges_html += (
                f"<div class='badge-tile {cls}' title='{b['desc']}'>"
                f"<div class='badge-emoji'>{b['emoji']}</div>"
                f"<div class='badge-name'>{b['name']}</div>"
                f"<div class='badge-desc'>{b['desc']}</div>"
                f"</div>"
            )
        badges_html += "</div>"
        st.markdown(badges_html, unsafe_allow_html=True)

        st.write("")

        # ── Stats detalladas ──
        st.markdown(
            "<p class='worlds-section-title'>ESTADÍSTICAS</p>",
            unsafe_allow_html=True
        )
        last_act = my_entry.get("last_activity")
        last_act_str = last_act.strftime("%d/%m/%Y %H:%M") if last_act else "—"

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown(f"""
                <div class='progress-panel' style='flex-direction:column; gap:14px;'>
                    <div class='stat-item'>
                        <div class='stat-value' style='color:{color} !important; text-shadow:0 0 10px {color};'>{my_entry["total_xp"]}</div>
                        <div class='stat-label'>XP Total</div>
                    </div>
                    <div class='stat-item'>
                        <div class='stat-value'>{my_entry["total_sessions"]}</div>
                        <div class='stat-label'>Lecciones completadas</div>
                    </div>
                    <div class='stat-item'>
                        <div class='stat-value' style='color:#39ff14 !important; text-shadow:0 0 10px #39ff14;'>{my_entry["best_score"]:.0%}</div>
                        <div class='stat-label'>Mejor nota</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col_s2:
            st.markdown(f"""
                <div class='progress-panel' style='flex-direction:column; gap:14px;'>
                    <div class='stat-item'>
                        <div class='stat-value' style='color:#00eefc !important; text-shadow:0 0 10px #00eefc;'>{my_entry["avg_score"]:.0%}</div>
                        <div class='stat-label'>Promedio quiz</div>
                    </div>
                    <div class='stat-item'>
                        <div class='stat-value' style='color:#ffd400 !important; text-shadow:0 0 10px #ffd400;'>{my_entry.get("active_days", 0)}</div>
                        <div class='stat-label'>Días activos</div>
                    </div>
                    <div class='stat-item'>
                        <div class='stat-value' style='font-size:0.95rem;'>{last_act_str}</div>
                        <div class='stat-label'>Última misión</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # ── Distribución por mundo ──
        world_counts = my_entry.get("world_counts", {})
        if world_counts:
            st.markdown(
                "<p class='worlds-section-title'>DISTRIBUCIÓN POR MUNDO</p>",
                unsafe_allow_html=True
            )
            world_meta = {
                "grammar":   ("🌌", "Galaxia Gramatical", "#c464ff"),
                "vocab":     ("📚", "Bóveda Vocabulario", "#00eefc"),
                "personal":  (PERSONAL_WORLDS.get(user, {}).get("emoji", "⭐"),
                              PERSONAL_WORLDS.get(user, {}).get("name", "Mi Mundo"),
                              color),
                "challenge": ("⚔️", "Desafío Sorpresa", "#ff5351"),
                "voice":     ("🎤", "Misión Voz", "#39ff14"),
                "custom":    ("📡", "Tema personalizado", "#ffd400"),
            }
            total_world = sum(world_counts.values()) or 1
            for w_key, count in sorted(world_counts.items(),
                                        key=lambda x: x[1], reverse=True):
                emoji_w, name_w, color_w = world_meta.get(
                    w_key, ("•", w_key.title(), "#a8acb3")
                )
                pct_w = count / total_world
                st.markdown(
                    f"<div class='skill-row'>"
                    f"<div class='skill-label'>{emoji_w} {name_w}</div>"
                    f"<div class='skill-bar'>"
                    f"<div class='skill-bar-fill' style='width:{pct_w*100:.1f}%;"
                    f" background:{color_w}; color:{color_w};'></div>"
                    f"</div>"
                    f"<div class='skill-pct'>{count}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        # ── Trofeos ──
        st.markdown(
            "<p class='worlds-section-title'>TROFEOS</p>",
            unsafe_allow_html=True
        )
        trophies = get_trophies(my_entry)
        earned_n = sum(1 for t in trophies if t["earned"])
        st.markdown(
            f"<p style='text-align:center; color:#a8acb3; font-size:0.85rem;"
            f" margin:0 0 10px;'>"
            f"<b style='color:{color}; text-shadow:0 0 10px {color};'>{earned_n}</b>"
            f" / {len(trophies)} desbloqueados</p>",
            unsafe_allow_html=True
        )

        trophies_html = "<div class='trophy-grid'>"
        for t in trophies:
            klass = "trophy-card earned" if t["earned"] else "trophy-card"
            t_color = t["color"]
            t_icon  = t["icon"]
            t_name  = t["name"]
            t_desc  = t["desc"]
            trophies_html += (
                f"<div class='{klass}' style='--trophy-accent: {t_color};'>"
                f"<span class='trophy-icon'>{t_icon}</span>"
                f"<div class='trophy-name'>{t_name}</div>"
                f"<div class='trophy-desc'>{t_desc}</div>"
                f"</div>"
            )
        trophies_html += "</div>"
        st.markdown(trophies_html, unsafe_allow_html=True)

    # Si estamos en arena o profile, detener acá — no renderizar el resto.
    if current_view in ("arena", "profile"):
        send_weekly_report()
        st.stop()

    # ════════════════════════════════════════════════════════════════
    # VISTA: HOME (puede mostrar: world entry, battle, lesson+quiz, o worlds grid)
    # ════════════════════════════════════════════════════════════════

    # ── 0a) FLASH SUCCESS (mensaje tras un save exitoso) ─────────────
    flash_msg = st.session_state.get("flash_success")
    if flash_msg:
        st.success(flash_msg)
        st.balloons()
        st.session_state.flash_success = None

    # ── 0b) SAVE-ERROR OVERLAY (cuando falló guardar XP) ─────────────
    if st.session_state.get("last_save_error"):
        pending = st.session_state.get("pending_xp_save_args") or {}
        render_save_failure(
            st.session_state.last_save_error,
            pending.get("xp_award", 0)
        )
        st.write("")
        col_re1, col_re2 = st.columns(2)
        with col_re1:
            if st.button("🔁 Reintentar guardar", key="retry_xp_save",
                         use_container_width=True, type="primary"):
                # Forzar refresh de la conexión y reintentar
                try:
                    get_db_connection.clear()
                except Exception:
                    pass
                attempt_xp_save()
                st.rerun()
        with col_re2:
            if st.button("🏠 Continuar sin guardar (perder XP)",
                         key="abandon_xp_save",
                         use_container_width=True, type="secondary"):
                st.session_state.pending_xp_save_args = None
                st.session_state.last_save_error = None
                reset_to_worlds()
                st.rerun()

        send_weekly_report()
        st.stop()

    # ── 1) BATTLE MODE: pregunta activa ──────────────────────────────
    if (st.session_state.battle_questions
            and not st.session_state.battle_finished):
        # Inyectar accent del mundo actual sobre el HUD de batalla
        battle_world_meta = get_world_meta(
            st.session_state.get("current_world", ""), user
        )
        b_accent = battle_world_meta.get("accent", color)
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {b_accent}; }}</style>",
            unsafe_allow_html=True
        )

        b_questions = st.session_state.battle_questions
        b_idx       = st.session_state.battle_index
        b_total     = len(b_questions)
        b_hp        = max(0, st.session_state.battle_hp)
        b_max_hp    = st.session_state.battle_max_hp
        b_streak    = st.session_state.battle_streak
        b_correct   = st.session_state.battle_correct

        # ── HUD ──
        hp_pct = (b_hp / b_max_hp) if b_max_hp else 0
        hp_class = "high" if hp_pct > 0.6 else "mid" if hp_pct > 0.3 else "low"
        st.markdown(
            f"<div class='battle-hud'>"
            f"<div class='battle-hud-row'>"
            f"<div class='battle-stat'>"
            f"  <div class='battle-stat-label'>Pregunta</div>"
            f"  <div class='battle-stat-value' style='color:{b_accent}; text-shadow:0 0 10px {b_accent};'>"
            f"  {min(b_idx + 1, b_total)}/{b_total}</div>"
            f"</div>"
            f"<div class='battle-hp-wrap'>"
            f"  <div class='battle-stat-label' style='text-align:left;'>HP</div>"
            f"  <div class='battle-hp-bar'>"
            f"    <div class='battle-hp-fill {hp_class}' style='width:{hp_pct*100:.0f}%;'></div>"
            f"    <span class='battle-hp-text'>{b_hp} / {b_max_hp}</span>"
            f"  </div>"
            f"</div>"
            f"<div class='battle-stat'>"
            f"  <div class='battle-stat-label'>Streak</div>"
            f"  <div class='battle-stat-value' style='color:#ffd400; text-shadow:0 0 10px #ffd400;'>"
            f"  🔥{b_streak}</div>"
            f"</div>"
            f"<div class='battle-stat'>"
            f"  <div class='battle-stat-label'>Aciertos</div>"
            f"  <div class='battle-stat-value' style='color:#39ff14; text-shadow:0 0 10px #39ff14;'>"
            f"  {b_correct}</div>"
            f"</div>"
            f"</div></div>",
            unsafe_allow_html=True
        )

        # Mostrar feedback flash si lo hay (después de la última respuesta)
        feedback = st.session_state.battle_feedback
        if feedback is not None:
            if feedback["is_correct"]:
                st.markdown(
                    f"<div class='battle-flash battle-flash-correct'>"
                    f"<p class='flash-title'>✓ ¡Acierto!</p>"
                    f"<p class='flash-detail'>+{feedback.get('xp_gained', 10)} XP · "
                    f"Streak: {feedback.get('streak', 0)}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='battle-flash battle-flash-wrong'>"
                    f"<p class='flash-title'>✗ Fallaste</p>"
                    f"<p class='flash-detail'>"
                    f"Tu respuesta: <em>{feedback.get('your_answer', '—')}</em> · "
                    f"Correcta: <strong>{feedback.get('correct_answer', '')}</strong> · "
                    f"−{feedback.get('hp_lost', 20)} HP</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            if st.button("➜ Siguiente", key="battle_next",
                         use_container_width=True, type="primary"):
                st.session_state.battle_feedback = None
                # Si fue la última, marcar batalla como terminada
                if st.session_state.battle_index >= b_total or st.session_state.battle_hp <= 0:
                    st.session_state.battle_finished = True
                    # Extraer patrón de error de los items fallados (si hay)
                    wrong = [
                        {"q": h.get("q", ""),
                         "correct": h.get("correct_answer", ""),
                         "user_answer": h.get("your_answer", "")}
                        for h in (st.session_state.battle_history or [])
                        if not h.get("is_correct", True)
                    ]
                    if len(wrong) >= 2:
                        cefr_now = get_cefr_info(
                            next((e["total_xp"] for e in get_leaderboard()
                                  if e["profile"] == user), 0)
                        )["code"]
                        try:
                            pattern = extract_error_pattern(wrong, cefr_now)
                            if pattern:
                                st.session_state.last_error_topic = pattern
                                st.session_state.error_dismissed = False
                        except Exception:
                            pass
                st.rerun()

        # Si no hay feedback pendiente y aún quedan preguntas, mostrar la actual
        elif b_idx < b_total and b_hp > 0:
            q = b_questions[b_idx]
            q_type_label = "Multiple Choice" if q["type"] == "mc" else "Fill the Blank"
            q_text = q["q"]
            if q["type"] == "fitb":
                # Reemplazar ___ por un span estilizado (HTML directo, no Markdown)
                q_text = q_text.replace(
                    "___",
                    "<span class='battle-blank'>______</span>"
                )

            # Hint en español (solo FITB): traducción de la oración completa
            hint_html = ""
            if q["type"] == "fitb" and q.get("hint"):
                hint_html = (
                    f"<p class='battle-q-hint'>"
                    f"💡 <i>{q['hint']}</i>"
                    f"</p>"
                )

            st.markdown(
                f"<div class='battle-question'>"
                f"<div class='battle-q-meta'>"
                f"  <span class='battle-q-num'>► Pregunta {b_idx + 1}</span>"
                f"  <span class='battle-q-type'>{q_type_label}</span>"
                f"</div>"
                f"<div class='battle-q-text'>{q_text}</div>"
                f"{hint_html}"
                f"</div>",
                unsafe_allow_html=True
            )

            with st.form(key=f"battle_form_{b_idx}", clear_on_submit=True):
                user_answer = ""
                if q["type"] == "mc":
                    options = ["— Selecciona —"] + q.get("options", [])
                    pick = st.radio("Respuesta",
                                    options=options, index=0,
                                    label_visibility="collapsed",
                                    key=f"battle_mc_{b_idx}")
                    user_answer = "" if pick == "— Selecciona —" else pick
                else:  # fitb
                    user_answer = st.text_input(
                        "Respuesta",
                        placeholder="Escribe la palabra...",
                        label_visibility="collapsed",
                        key=f"battle_fitb_{b_idx}"
                    )

                submitted = st.form_submit_button(
                    "⚡ ¡Atacar!",
                    use_container_width=True,
                    type="primary"
                )

            if submitted:
                correct_ans = q.get("answer", "")
                if q["type"] == "mc":
                    is_correct = (user_answer.strip() == correct_ans.strip())
                else:
                    is_correct = (user_answer.strip().lower() ==
                                  correct_ans.strip().lower())

                if is_correct:
                    st.session_state.battle_correct += 1
                    st.session_state.battle_streak  += 1
                    st.session_state.battle_max_streak = max(
                        st.session_state.battle_max_streak,
                        st.session_state.battle_streak
                    )
                    xp_gain = 10 + min(st.session_state.battle_streak - 1, 5) * 2
                    st.session_state.battle_feedback = {
                        "is_correct": True, "xp_gained": xp_gain,
                        "streak": st.session_state.battle_streak,
                    }
                else:
                    hp_lost = 20
                    st.session_state.battle_hp -= hp_lost
                    st.session_state.battle_streak = 0
                    st.session_state.battle_feedback = {
                        "is_correct": False,
                        "your_answer": user_answer or "(sin respuesta)",
                        "correct_answer": correct_ans,
                        "hp_lost": hp_lost,
                    }

                st.session_state.battle_history = (st.session_state.battle_history or []) + [{
                    "q": q.get("q", ""),
                    "your_answer": user_answer,
                    "correct_answer": correct_ans,
                    "is_correct": is_correct,
                    "type": q["type"],
                }]
                st.session_state.battle_total += 1
                st.session_state.battle_index += 1
                st.rerun()
        else:
            # Sin feedback y sin más preguntas → terminar batalla
            st.session_state.battle_finished = True
            st.rerun()

        if st.button("✕ Abandonar batalla", key="battle_abandon",
                     type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2) BATTLE MODE: pantalla final (victoria / derrota) ──────────
    if st.session_state.battle_finished:
        b_total   = st.session_state.battle_total
        b_correct = st.session_state.battle_correct
        b_max_streak = st.session_state.battle_max_streak
        b_hp_left = max(0, st.session_state.battle_hp)
        victory   = (b_hp_left > 0 and b_correct >= max(1, b_total // 2))

        score_pct = (b_correct / b_total) if b_total else 0.0

        if victory:
            xp_award = XP_PER_LESSON
            if b_max_streak >= 5:
                xp_award += 10
            st.markdown(f"""
                <div class='battle-end battle-end-victory'>
                    <div class='battle-end-emoji' style='color:#39ff14;'>🏆</div>
                    <h1 class='battle-end-title'>¡VICTORIA!</h1>
                    <p style='color:#a8acb3; margin:6px 0 0; font-size:1rem;'>
                        Has dominado este combate. La gloria es tuya.
                    </p>
                    <div class='battle-end-stats'>
                        <div>
                            <div class='battle-end-stat-num' style='color:#39ff14; text-shadow:0 0 14px #39ff14;'>
                                {b_correct}/{b_total}
                            </div>
                            <div class='battle-end-stat-label'>Aciertos</div>
                        </div>
                        <div>
                            <div class='battle-end-stat-num' style='color:#ffd400; text-shadow:0 0 14px #ffd400;'>
                                🔥{b_max_streak}
                            </div>
                            <div class='battle-end-stat-label'>Mejor streak</div>
                        </div>
                        <div>
                            <div class='battle-end-stat-num' style='color:#00eefc; text-shadow:0 0 14px #00eefc;'>
                                {b_hp_left}
                            </div>
                            <div class='battle-end-stat-label'>HP restante</div>
                        </div>
                        <div>
                            <div class='battle-end-stat-num' style='color:#ff66c4; text-shadow:0 0 14px #ff66c4;'>
                                +{xp_award}
                            </div>
                            <div class='battle-end-stat-label'>XP ganado</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            xp_award = max(10, b_correct * 5)
            st.markdown(f"""
                <div class='battle-end battle-end-defeat'>
                    <div class='battle-end-emoji' style='color:#ff5351;'>💔</div>
                    <h1 class='battle-end-title'>DERROTA</h1>
                    <p style='color:#a8acb3; margin:6px 0 0; font-size:1rem;'>
                        Esta vez no fue. ¡Pero el conocimiento se construye con cada intento!
                    </p>
                    <div class='battle-end-stats'>
                        <div>
                            <div class='battle-end-stat-num' style='color:#ffd400; text-shadow:0 0 14px #ffd400;'>
                                {b_correct}/{b_total}
                            </div>
                            <div class='battle-end-stat-label'>Aciertos</div>
                        </div>
                        <div>
                            <div class='battle-end-stat-num' style='color:#ff66c4; text-shadow:0 0 14px #ff66c4;'>
                                +{xp_award}
                            </div>
                            <div class='battle-end-stat-label'>XP consuelo</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # Botón para confirmar y guardar
        st.write("")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("✅ Reclamar XP",
                         use_container_width=True, type="primary",
                         key="battle_claim"):
                world_key = st.session_state.get("current_world", "")
                if victory:
                    success_msg = f"¡Increíble batalla, {user}! +{xp_award} XP en tu cuenta."
                else:
                    success_msg = f"Buen intento. Recibes {xp_award} XP de consolación."
                queue_xp_save(
                    user, xp_award, score_pct, attempts=1,
                    world=world_key, skill="battle",
                    lesson_type="battle",
                    success_msg=success_msg
                )
                st.rerun()
        with col_b2:
            if st.button("🏠 Volver al mapa",
                         use_container_width=True, type="secondary",
                         key="battle_back"):
                reset_to_worlds()
                st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.02) STORY FILL MODE (Mundo Personal) ───────────────────────
    if st.session_state.sf_story is not None:
        sf_world_meta = get_world_meta(
            st.session_state.get("current_world", "personal"), user
        )
        sf_accent = sf_world_meta.get("accent", "#ff66c4")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {sf_accent}; }}</style>",
            unsafe_allow_html=True
        )

        story    = st.session_state.sf_story
        sents    = story["sentences"]
        total    = len(sents)
        picked   = list(st.session_state.sf_picked or [None] * total)
        revealed = st.session_state.sf_revealed

        # ── Pantalla final ──
        if st.session_state.sf_finished:
            correct   = st.session_state.sf_correct
            score_pct = (correct / total) * 100.0 if total else 0
            xp_award  = max(15, int(score_pct / 2))

            color_avg = "#39ff14" if score_pct >= 80 else "#ffd400" if score_pct >= 55 else "#ff5351"
            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: {color_avg}; box-shadow: 0 0 30px {color_avg};'>
                    <div class='battle-end-emoji' style='color:{color_avg};'>📖</div>
                    <h1 class='battle-end-title' style='color:{color_avg}; text-shadow:0 0 20px {color_avg};'>
                        {int(score_pct)}%
                    </h1>
                    <p class='battle-end-subtitle'>{correct} de {total} huecos correctos</p>
                </div>
            """, unsafe_allow_html=True)

            # Mostrar el cuento completo con las elecciones (verde/rojo)
            full_html = f"<div class='sf-story'><h3 style='color:{sf_accent}; text-shadow:0 0 12px {sf_accent}; text-align:center; margin: 0 0 14px;'>{story['title']}</h3><p class='sf-text'>"
            for i, s in enumerate(sents):
                user_idx = picked[i]
                correct_idx = s["correct_idx"]
                if user_idx == correct_idx:
                    word_html = f"<span class='sf-blank ok'>{s['blank_correct']}</span>"
                else:
                    chosen_word = s["blank_options"][user_idx] if user_idx is not None else "___"
                    word_html = (f"<span class='sf-blank bad'>"
                                 f"<s>{chosen_word}</s> → {s['blank_correct']}</span>")
                full_html += f"{s['text_before']} {word_html} {s['text_after']} "
            full_html += "</p></div>"
            st.markdown(full_html, unsafe_allow_html=True)

            if st.session_state.get("last_save_error"):
                render_save_failure(st.session_state.last_save_error, xp_award)

            col_x1, col_x2 = st.columns(2)
            with col_x1:
                if st.button(f"⚡ Reclamar +{xp_award} XP", key="sf_claim_xp",
                             use_container_width=True, type="primary"):
                    queue_xp_save(
                        user=user, xp_award=xp_award,
                        score_pct=score_pct / 100.0, attempts=1,
                        world=st.session_state.get("current_world", "personal"),
                        skill="reading", lesson_type="story_fill",
                        success_msg=f"¡+{xp_award} XP en Cuento!"
                    )
                    st.rerun()
            with col_x2:
                if st.button("🏠 Volver al mapa", key="sf_back",
                             use_container_width=True, type="secondary"):
                    reset_to_worlds()
                    st.rerun()

            send_weekly_report()
            st.stop()

        # ── Hueco actual ──
        idx = st.session_state.sf_index
        if idx >= total:
            # Calcular correctas y marcar como finished
            n_correct = sum(
                1 for i, s in enumerate(sents)
                if picked[i] == s["correct_idx"]
            )
            st.session_state.sf_correct = n_correct
            st.session_state.sf_finished = True
            st.rerun()

        sent = sents[idx]

        st.markdown(
            f"<p class='worlds-section-title' style='color:{sf_accent};'>"
            f"📖 {story['title']} · HUECO {idx + 1} / {total}</p>",
            unsafe_allow_html=True
        )

        # Hint en español (traducción completa de la oración para dar contexto)
        spanish_hint = (sent.get("spanish_hint") or "").strip()
        hint_block = (
            f"<p class='battle-q-hint' style='margin: 12px 0 0;'>"
            f"💡 <i>{spanish_hint}</i></p>"
            if spanish_hint else ""
        )

        # Mostrar la oración con un hueco visible + traducción debajo
        st.markdown(
            f"<div class='sf-card' style='--sf-accent: {sf_accent};'>"
            f"<p class='sf-sentence'>"
            f"{sent['text_before']} "
            f"<span class='sf-blank-empty'>______</span> "
            f"{sent['text_after']}"
            f"</p>"
            f"{hint_block}"
            f"</div>",
            unsafe_allow_html=True
        )

        # Botones de opciones
        st.markdown("<p class='sb-section-label'>Elige la palabra que completa:</p>", unsafe_allow_html=True)
        opt_cols = st.columns(len(sent["blank_options"]))
        for i, opt in enumerate(sent["blank_options"]):
            with opt_cols[i]:
                if st.button(opt, key=f"sf_opt_{idx}_{i}",
                             use_container_width=True, type="secondary"):
                    picked[idx] = i
                    st.session_state.sf_picked = picked
                    st.session_state.sf_index = idx + 1
                    st.rerun()

        st.write("")
        if st.button("✕ Salir", key="sf_abandon", type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.03) SENTENCE BUILDER MODE (Galaxia Gramatical) ─────────────
    if st.session_state.sb_sentences is not None:
        sb_world_meta = get_world_meta(
            st.session_state.get("current_world", "grammar"), user
        )
        sb_accent = sb_world_meta.get("accent", "#c464ff")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {sb_accent}; }}</style>",
            unsafe_allow_html=True
        )

        sents = st.session_state.sb_sentences
        idx   = st.session_state.sb_index
        total = len(sents)

        # ── Pantalla final ──
        if st.session_state.sb_finished or idx >= total:
            attempted = max(1, st.session_state.sb_attempted)
            correct   = st.session_state.sb_correct
            score_pct = (correct / attempted) * 100.0
            xp_award  = max(15, int(score_pct / 2))

            color_avg = "#39ff14" if score_pct >= 80 else "#ffd400" if score_pct >= 55 else "#ff5351"
            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: {color_avg}; box-shadow: 0 0 30px {color_avg};'>
                    <div class='battle-end-emoji' style='color:{color_avg};'>🧩</div>
                    <h1 class='battle-end-title' style='color:{color_avg}; text-shadow:0 0 20px {color_avg};'>
                        {int(score_pct)}%
                    </h1>
                    <p class='battle-end-subtitle'>{correct} de {total} oraciones correctas</p>
                </div>
            """, unsafe_allow_html=True)

            if st.session_state.get("last_save_error"):
                render_save_failure(st.session_state.last_save_error, xp_award)

            col_x1, col_x2 = st.columns(2)
            with col_x1:
                if st.button(f"⚡ Reclamar +{xp_award} XP", key="sb_claim_xp",
                             use_container_width=True, type="primary"):
                    queue_xp_save(
                        user=user, xp_award=xp_award,
                        score_pct=score_pct / 100.0, attempts=1,
                        world=st.session_state.get("current_world", "grammar"),
                        skill="grammar", lesson_type="sentence_builder",
                        success_msg=f"¡+{xp_award} XP en Constructor!"
                    )
                    st.rerun()
            with col_x2:
                if st.button("🏠 Volver al mapa", key="sb_back",
                             use_container_width=True, type="secondary"):
                    reset_to_worlds()
                    st.rerun()

            send_weekly_report()
            st.stop()

        # ── Oración actual ──
        sent   = sents[idx]
        placed = st.session_state.sb_placed or []
        scrambled = sent["scrambled"]
        target    = sent["target"]
        revealed  = st.session_state.sb_revealed

        st.markdown(
            f"<p class='worlds-section-title' style='color:{sb_accent};'>"
            f"🧩 ORACIÓN {idx + 1} / {total}</p>",
            unsafe_allow_html=True
        )

        # Tarjeta con la oración en español
        st.markdown(
            f"<div class='sb-card' style='--sb-accent: {sb_accent};'>"
            f"<p class='sb-hint'>Traduce y ordena las palabras:</p>"
            f"<p class='sb-spanish'>{sent['spanish']}</p>"
            f"</div>",
            unsafe_allow_html=True
        )

        # Área de oración construida
        built_words = [scrambled[i] for i in placed]
        built_display = " ".join(built_words) if built_words else "( toca las palabras en orden )"
        slot_color = sb_accent if built_words else "#3a3d40"
        st.markdown(
            f"<div class='sb-slot' style='border-color:{slot_color};'>"
            f"<p class='sb-slot-text'>{built_display}</p>"
            f"</div>",
            unsafe_allow_html=True
        )

        # Botones de palabras desordenadas (las ya colocadas se ven inactivas)
        st.markdown("<p class='sb-section-label'>Palabras disponibles:</p>", unsafe_allow_html=True)
        n_cols = min(4, len(scrambled))
        word_cols = st.columns(n_cols)
        for i, w in enumerate(scrambled):
            with word_cols[i % n_cols]:
                already_placed = (i in placed)
                if revealed or already_placed:
                    st.button(w, key=f"sb_w_{idx}_{i}",
                              disabled=True, use_container_width=True)
                else:
                    if st.button(w, key=f"sb_w_{idx}_{i}",
                                 use_container_width=True, type="secondary"):
                        st.session_state.sb_placed = placed + [i]
                        st.rerun()

        st.write("")
        col_a, col_b, col_c = st.columns([1, 1, 1])
        # Deshacer
        with col_a:
            if not revealed and placed:
                if st.button("↶ Quitar última", key=f"sb_undo_{idx}",
                             use_container_width=True, type="secondary"):
                    st.session_state.sb_placed = placed[:-1]
                    st.rerun()
        # Verificar (cuando coloca todas las palabras)
        with col_b:
            if not revealed and len(placed) == len(scrambled):
                if st.button("✓ Verificar", key=f"sb_check_{idx}",
                             use_container_width=True, type="primary"):
                    built = [scrambled[i] for i in placed]
                    ok = (built == target)
                    st.session_state.sb_attempted += 1
                    if ok:
                        st.session_state.sb_correct += 1
                    st.session_state.sb_revealed = True
                    st.session_state.sb_last_ok = ok
                    st.rerun()
        # Siguiente (después de validar)
        with col_c:
            if revealed:
                next_label = "Siguiente →" if (idx + 1) < total else "Resultados 🏁"
                if st.button(next_label, key=f"sb_next_{idx}",
                             use_container_width=True, type="primary"):
                    st.session_state.sb_index += 1
                    st.session_state.sb_placed = []
                    st.session_state.sb_revealed = False
                    st.session_state.sb_last_ok = None
                    if st.session_state.sb_index >= total:
                        st.session_state.sb_finished = True
                    st.rerun()

        # Feedback de validación
        if revealed:
            if st.session_state.sb_last_ok:
                st.markdown(
                    f"<div class='fc-feedback ok'>"
                    f"✓ ¡Correcto! <b>{sent['english']}</b>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='fc-feedback bad'>"
                    f"✗ Casi. Era: <b>{sent['english']}</b>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.write("")
        if st.button("✕ Salir", key="sb_abandon", type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.04) MEMORY MATCH MODE (Bóveda de Vocabulario) ───────────────
    if st.session_state.mm_pairs is not None:
        mm_world_meta = get_world_meta(
            st.session_state.get("current_world", "vocab"), user
        )
        mm_accent = mm_world_meta.get("accent", "#00eefc")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {mm_accent}; }}</style>",
            unsafe_allow_html=True
        )

        cards = st.session_state.mm_pairs
        # IMPORTANTE: lookup por id (las cards están barajadas, los índices
        # de lista NO corresponden a card_id). Este era el bug crítico anterior.
        card_by_id = {c["id"]: c for c in cards}

        flipped = list(st.session_state.mm_flipped or [])
        matched = list(st.session_state.mm_matched or [])
        total_pairs = len(cards) // 2

        # ── Verificar si terminó ──
        if len(matched) >= total_pairs:
            st.session_state.mm_finished = True

        # ── Pantalla final ──
        if st.session_state.mm_finished:
            attempts = max(1, st.session_state.mm_attempts)
            efficiency = min(100.0, (total_pairs / attempts) * 100.0)
            xp_award = max(15, int(efficiency / 2))

            color_avg = "#39ff14" if efficiency >= 80 else "#ffd400" if efficiency >= 55 else "#ff5351"
            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: {color_avg}; box-shadow: 0 0 30px {color_avg};'>
                    <div class='battle-end-emoji' style='color:{color_avg};'>🧠</div>
                    <h1 class='battle-end-title' style='color:{color_avg}; text-shadow:0 0 20px {color_avg};'>
                        ¡Completado!
                    </h1>
                    <p class='battle-end-subtitle'>{total_pairs} parejas en {attempts} intentos · eficiencia {int(efficiency)}%</p>
                </div>
            """, unsafe_allow_html=True)

            if st.session_state.get("last_save_error"):
                render_save_failure(st.session_state.last_save_error, xp_award)

            col_x1, col_x2 = st.columns(2)
            with col_x1:
                if st.button(f"⚡ Reclamar +{xp_award} XP", key="mm_claim_xp",
                             use_container_width=True, type="primary"):
                    queue_xp_save(
                        user=user, xp_award=xp_award,
                        score_pct=efficiency / 100.0, attempts=attempts,
                        world=st.session_state.get("current_world", "vocab"),
                        skill="vocabulary", lesson_type="memory_match",
                        success_msg=f"¡+{xp_award} XP en Memory Match!"
                    )
                    st.rerun()
            with col_x2:
                if st.button("🏠 Volver al mapa", key="mm_back",
                             use_container_width=True, type="secondary"):
                    reset_to_worlds()
                    st.rerun()

            send_weekly_report()
            st.stop()

        # ── Detectar estado del par actual (si hay 2 flipped) ──
        is_match = False
        is_mismatch = False
        if len(flipped) == 2:
            a_card = card_by_id.get(flipped[0])
            b_card = card_by_id.get(flipped[1])
            if a_card and b_card:
                if a_card["pair_id"] == b_card["pair_id"]:
                    is_match = True
                else:
                    is_mismatch = True

        # ── Tablero ──
        st.markdown(
            f"<p class='worlds-section-title' style='color:{mm_accent};'>"
            f"🧠 MEMORY MATCH · {len(matched)} / {total_pairs} parejas · intentos: {st.session_state.mm_attempts}</p>",
            unsafe_allow_html=True
        )

        n_cols = 4
        rows = [cards[i:i + n_cols] for i in range(0, len(cards), n_cols)]

        for row in rows:
            row_cols = st.columns(n_cols)
            for c_idx, card in enumerate(row):
                with row_cols[c_idx]:
                    card_id = card["id"]
                    is_card_matched = (card["pair_id"] in matched)
                    is_card_flipped = (card_id in flipped)
                    show_face = is_card_matched or is_card_flipped

                    if show_face:
                        emoji_or_word = card["value"]
                        if is_card_matched:
                            bg = mm_accent; fg = "#0a0b1e"
                        elif is_match:  # par actual correcto, aún no confirmado
                            bg = "#39ff14"; fg = "#0a0b1e"
                        elif is_mismatch:
                            bg = "#ff5351"; fg = "#fff"
                        else:
                            bg = "#272a2d"; fg = "#e0e2e6"
                        font_size = "2.2rem" if card["kind"] == "emoji" else "1rem"
                        st.markdown(
                            f"<div class='mm-card mm-face' style='background:{bg}; color:{fg}; font-size:{font_size};'>"
                            f"{emoji_or_word}</div>",
                            unsafe_allow_html=True
                        )
                    else:
                        # Botón boca abajo: deshabilitado si ya hay 2 flipped
                        disabled = (len(flipped) >= 2)
                        if st.button("❓", key=f"mm_{card_id}",
                                     use_container_width=True,
                                     disabled=disabled, type="secondary"):
                            new_flipped = flipped + [card_id]
                            st.session_state.mm_flipped = new_flipped
                            if len(new_flipped) == 2:
                                st.session_state.mm_attempts += 1
                            st.rerun()

        st.write("")
        # Botón Continuar después de cualquier par evaluado (match o no)
        if is_match:
            st.markdown(
                f"<div class='fc-feedback ok'>"
                f"✓ ¡Match! <b>{card_by_id[flipped[0]]['word']}</b> = {card_by_id[flipped[0]]['meaning']}"
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button("✓ Continuar →", key="mm_continue_ok",
                         use_container_width=True, type="primary"):
                pid = card_by_id[flipped[0]]["pair_id"]
                st.session_state.mm_matched = matched + [pid]
                st.session_state.mm_flipped = []
                st.rerun()
        elif is_mismatch:
            st.markdown(
                f"<div class='fc-feedback bad'>"
                f"✗ No coinciden. Inténtalo de nuevo."
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button("Continuar →", key="mm_continue_bad",
                         use_container_width=True, type="primary"):
                st.session_state.mm_flipped = []
                st.rerun()

        if st.button("✕ Salir", key="mm_abandon", type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.05) FLASHCARDS VISUALES MODE (Bóveda de Vocabulario) ───────
    if st.session_state.fc_cards is not None:
        fc_world_meta = get_world_meta(
            st.session_state.get("current_world", "vocab"), user
        )
        fc_accent = fc_world_meta.get("accent", "#00eefc")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {fc_accent}; }}</style>",
            unsafe_allow_html=True
        )

        cards = st.session_state.fc_cards
        idx   = st.session_state.fc_index
        total = len(cards)

        # ── Pantalla final ──
        if st.session_state.fc_finished or idx >= total:
            attempted = max(1, st.session_state.fc_attempted)
            correct   = st.session_state.fc_correct
            score_pct = (correct / attempted) * 100.0
            xp_award  = max(15, int(score_pct / 2))  # 15-50 XP

            color_avg = "#39ff14" if score_pct >= 80 else "#ffd400" if score_pct >= 55 else "#ff5351"
            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: {color_avg}; box-shadow: 0 0 30px {color_avg};'>
                    <div class='battle-end-emoji' style='color:{color_avg};'>🃏</div>
                    <h1 class='battle-end-title' style='color:{color_avg}; text-shadow:0 0 20px {color_avg};'>
                        {int(score_pct)}%
                    </h1>
                    <p class='battle-end-subtitle'>{correct} de {total} tarjetas correctas</p>
                </div>
            """, unsafe_allow_html=True)

            # Overlay de error de guardado (si lo hay)
            if st.session_state.get("last_save_error"):
                render_save_failure(st.session_state.last_save_error, xp_award)

            col_x1, col_x2 = st.columns(2)
            with col_x1:
                if st.button(f"⚡ Reclamar +{xp_award} XP", key="fc_claim_xp",
                             use_container_width=True, type="primary"):
                    queue_xp_save(
                        user=user,
                        xp_award=xp_award,
                        score_pct=score_pct / 100.0,
                        attempts=1,
                        world=st.session_state.get("current_world", "vocab"),
                        skill="vocabulary",
                        lesson_type="flashcards",
                        success_msg=f"¡+{xp_award} XP en Flashcards!"
                    )
                    st.rerun()
            with col_x2:
                if st.button("🏠 Volver al mapa", key="fc_back",
                             use_container_width=True, type="secondary"):
                    reset_to_worlds()
                    st.rerun()

            send_weekly_report()
            st.stop()

        # ── Tarjeta actual ──
        card = cards[idx]
        chosen = st.session_state.fc_chosen

        st.markdown(
            f"<p class='worlds-section-title' style='color:{fc_accent};'>"
            f"🃏 TARJETA {idx + 1} / {total}</p>",
            unsafe_allow_html=True
        )

        # Tarjeta grande con emoji
        st.markdown(
            f"<div class='fc-card' style='--fc-accent: {fc_accent};'>"
            f"<div class='fc-emoji'>{card['emoji']}</div>"
            f"<p class='fc-hint'>¿Qué palabra es ésta en inglés?</p>"
            f"</div>",
            unsafe_allow_html=True
        )

        # Botón de audio (genera y reproduce TTS de la palabra correcta)
        col_audio_l, col_audio_c, col_audio_r = st.columns([1, 2, 1])
        with col_audio_c:
            if st.button("🔊 Escuchar palabra", key=f"fc_audio_btn_{idx}",
                         use_container_width=True, type="secondary"):
                with st.spinner("Generando audio..."):
                    audio_bytes = generate_lesson_audio(card["word"])
                if audio_bytes:
                    st.session_state.fc_audio = audio_bytes
                else:
                    st.warning("No pude generar el audio. Intenta de nuevo.")

        if st.session_state.fc_audio:
            st.audio(st.session_state.fc_audio, format="audio/mp3")

        st.write("")

        # 4 opciones (botones)
        if chosen is None:
            # Aún no contestó: mostrar opciones para tocar
            opt_cols = st.columns(2)
            for i, opt in enumerate(card["options"]):
                with opt_cols[i % 2]:
                    if st.button(opt, key=f"fc_opt_{idx}_{i}",
                                 use_container_width=True, type="secondary"):
                        st.session_state.fc_chosen = i
                        st.session_state.fc_attempted += 1
                        if i == card["correct_idx"]:
                            st.session_state.fc_correct += 1
                        st.rerun()
        else:
            # Ya contestó: mostrar feedback con todos los botones marcados
            is_correct = (chosen == card["correct_idx"])
            opt_cols = st.columns(2)
            for i, opt in enumerate(card["options"]):
                with opt_cols[i % 2]:
                    if i == card["correct_idx"]:
                        # opción correcta siempre marcada en verde
                        bg = "#39ff14"; fg = "#0a0b1e"; mark = "✓"
                    elif i == chosen:
                        # la que eligió y es incorrecta marcada en rojo
                        bg = "#ff5351"; fg = "#fff"; mark = "✗"
                    else:
                        bg = "transparent"; fg = "#a8acb3"; mark = ""
                    st.markdown(
                        f"<div style='padding:14px 12px; border-radius:8px; "
                        f"background:{bg}; color:{fg}; text-align:center; "
                        f"border:1px solid {'transparent' if bg=='transparent' else bg}; "
                        f"font-weight:700; margin-bottom:8px;'>"
                        f"{mark} {opt}</div>",
                        unsafe_allow_html=True
                    )

            # Mensaje de feedback
            if is_correct:
                st.markdown(
                    f"<div class='fc-feedback ok'>"
                    f"✓ ¡Correcto! <b>{card['word']}</b> significa <i>{card['meaning']}</i>."
                    f"</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='fc-feedback bad'>"
                    f"✗ Era <b>{card['word']}</b> ({card['meaning']}). ¡Lo recordarás la próxima!"
                    f"</div>",
                    unsafe_allow_html=True
                )

            # Avanzar
            next_label = "Siguiente tarjeta →" if (idx + 1) < total else "Ver resultados 🏁"
            if st.button(next_label, key=f"fc_next_{idx}",
                         use_container_width=True, type="primary"):
                st.session_state.fc_index += 1
                st.session_state.fc_chosen = None
                st.session_state.fc_audio = None
                if st.session_state.fc_index >= total:
                    st.session_state.fc_finished = True
                st.rerun()

        st.write("")
        if st.button("✕ Salir de Flashcards", key="fc_abandon",
                     type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.1) PRONUNCIATION MODE ──────────────────────────────────────
    if st.session_state.pron_words is not None:
        pron_world_meta = get_world_meta(
            st.session_state.get("current_world", ""), user
        )
        pron_accent = pron_world_meta.get("accent", "#00eefc")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {pron_accent}; }}</style>",
            unsafe_allow_html=True
        )

        words = st.session_state.pron_words
        idx   = st.session_state.pron_index
        total = len(words)

        # ── Pantalla final ──
        if st.session_state.pron_finished or idx >= total:
            results = st.session_state.pron_results or []
            if results:
                avg_score = sum(r["score"] for r in results) / len(results)
            else:
                avg_score = 0
            n_good = sum(1 for r in results if r["tier"] == "good")
            n_mid  = sum(1 for r in results if r["tier"] == "mid")
            n_bad  = sum(1 for r in results if r["tier"] == "bad")

            xp_award = max(15, int(avg_score / 2))  # 0-50 XP

            color_avg = "#39ff14" if avg_score >= 80 else "#ffd400" if avg_score >= 55 else "#ff5351"
            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: {color_avg}; box-shadow: 0 0 30px {color_avg};'>
                    <div class='battle-end-emoji' style='color:{color_avg};'>🎤</div>
                    <h1 class='battle-end-title' style='color:{color_avg}; text-shadow:0 0 20px {color_avg};'>
                        ¡Práctica completa!
                    </h1>
                    <p style='color:#a8acb3; margin:6px 0 0; font-size:1rem;'>
                        Promedio de pronunciación
                    </p>
                    <div style='font-family: Plus Jakarta Sans; font-weight:800; font-size:3.5rem;
                                color:{color_avg}; text-shadow:0 0 22px {color_avg}; margin: 6px 0;'>
                        {int(avg_score)}%
                    </div>
                    <div class='battle-end-stats'>
                        <div>
                            <div class='battle-end-stat-num' style='color:#39ff14; text-shadow:0 0 14px #39ff14;'>{n_good}</div>
                            <div class='battle-end-stat-label'>Excelentes</div>
                        </div>
                        <div>
                            <div class='battle-end-stat-num' style='color:#ffd400; text-shadow:0 0 14px #ffd400;'>{n_mid}</div>
                            <div class='battle-end-stat-label'>Casi</div>
                        </div>
                        <div>
                            <div class='battle-end-stat-num' style='color:#ff5351; text-shadow:0 0 14px #ff5351;'>{n_bad}</div>
                            <div class='battle-end-stat-label'>Por mejorar</div>
                        </div>
                        <div>
                            <div class='battle-end-stat-num' style='color:#ff66c4; text-shadow:0 0 14px #ff66c4;'>+{xp_award}</div>
                            <div class='battle-end-stat-label'>XP ganado</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            st.write("")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if st.button("✅ Reclamar XP", key="pron_claim",
                             use_container_width=True, type="primary"):
                    queue_xp_save(
                        user, xp_award, avg_score / 100.0, attempts=1,
                        world=st.session_state.get("current_world", ""),
                        skill="pronunciation",
                        lesson_type="pronunciation",
                        success_msg=f"¡Buena pronunciación, {user}! +{xp_award} XP."
                    )
                    st.rerun()
            with col_p2:
                if st.button("🏠 Volver al mapa", key="pron_back_end",
                             use_container_width=True, type="secondary"):
                    reset_to_worlds()
                    st.rerun()

            send_weekly_report()
            st.stop()

        # ── Card actual ──
        w = words[idx]
        word_text = w.get("word", "")
        ipa       = w.get("ipa", "")
        meaning   = w.get("meaning", "")
        emoji     = w.get("emoji", "🔊")

        st.markdown(f"""
            <div class='pron-card'>
                <p class='pron-meta'>🎤 Pronunciación · <b>{idx + 1}/{total}</b></p>
                <div style='font-size:2.6rem; line-height:1;
                            filter: drop-shadow(0 0 16px {pron_accent});'>{emoji}</div>
                <p class='pron-target'>{word_text}</p>
                <p class='pron-ipa'>{ipa}</p>
                <p class='pron-meaning'>{meaning}</p>
            </div>
        """, unsafe_allow_html=True)

        # Botón listen — genera audio y reproduce
        col_p1, col_p2 = st.columns([1, 1])
        with col_p1:
            if st.button("🔊 Escuchar", key=f"pron_listen_{idx}",
                         use_container_width=True, type="secondary"):
                with st.spinner("Generando audio..."):
                    audio_bytes_listen = generate_lesson_audio(word_text)
                if audio_bytes_listen:
                    st.audio(audio_bytes_listen, format="audio/mp3", autoplay=True)

        # Audio recorder + comparación con score
        with col_p2:
            st.markdown(
                "<p style='font-size:0.78rem; color:#a8acb3; margin: 0 0 4px; text-align:center;'>"
                "Repite la palabra:</p>",
                unsafe_allow_html=True
            )
            user_audio = audio_recorder(
                text="Grabar", recording_color="#ff5351",
                neutral_color=pron_accent, icon_size="2x",
                key=f"pron_rec_{idx}"
            )

        # Si grabó audio nuevo (no procesado aún)
        if user_audio and st.session_state.pron_last_audio != user_audio:
            st.session_state.pron_last_audio = user_audio
            with st.spinner("Analizando tu pronunciación..."):
                transcribed, t_err = transcribe_audio(user_audio)
            if t_err:
                show_error(t_err)
            else:
                result = score_pronunciation(word_text, transcribed or "")
                st.session_state.pron_last_score = result

        # Mostrar resultado de la última grabación si existe
        last = st.session_state.pron_last_score
        if last is not None:
            cls = f"pron-result pron-result-{last['tier']}"
            tier_label = {
                "good": "¡Excelente!",
                "mid":  "Casi, sigue practicando",
                "bad":  "Intenta de nuevo",
            }.get(last["tier"], "")
            st.markdown(
                f"<div class='{cls}'>"
                f"<div class='pron-score'>{last['score']}%</div>"
                f"<p style='margin:0; font-weight:700; font-family: Plus Jakarta Sans;'>"
                f"{tier_label}</p>"
                f"<p class='pron-heard'>Te escuché: <em>{last['heard'] or '(silencio)'}</em></p>"
                f"</div>",
                unsafe_allow_html=True
            )

            col_pn1, col_pn2 = st.columns([1, 1])
            with col_pn1:
                if st.button("🔁 Reintentar", key=f"pron_retry_{idx}",
                             use_container_width=True, type="secondary"):
                    st.session_state.pron_last_audio = None
                    st.session_state.pron_last_score = None
                    st.rerun()
            with col_pn2:
                if st.button("➜ Aceptar y siguiente", key=f"pron_next_{idx}",
                             use_container_width=True, type="primary"):
                    if st.session_state.pron_results is None:
                        st.session_state.pron_results = []
                    st.session_state.pron_results.append({
                        "word":  word_text,
                        "score": last["score"],
                        "tier":  last["tier"],
                    })
                    st.session_state.pron_index += 1
                    st.session_state.pron_last_audio = None
                    st.session_state.pron_last_score = None
                    if st.session_state.pron_index >= total:
                        st.session_state.pron_finished = True
                    st.rerun()

        st.write("")
        if st.button("✕ Abandonar práctica", key="pron_abandon",
                     type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.125) SPEAKING JOURNAL MODE (Diario Hablado) ─────────────────
    if st.session_state.dh_prompt is not None:
        dh_accent = "#00eefc"
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {dh_accent}; }}</style>",
            unsafe_allow_html=True
        )

        prompt = st.session_state.dh_prompt
        feedback = st.session_state.dh_feedback

        # ── Pantalla final ──
        if st.session_state.dh_finished and feedback:
            sc = feedback["score"]
            xp_award = max(20, int(sc / 2))
            color_avg = "#39ff14" if sc >= 80 else "#ffd400" if sc >= 55 else "#ff5351"

            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: {color_avg}; box-shadow: 0 0 30px {color_avg};'>
                    <div class='battle-end-emoji' style='color:{color_avg};'>📔</div>
                    <h1 class='battle-end-title' style='color:{color_avg}; text-shadow:0 0 20px {color_avg};'>
                        {sc}/100
                    </h1>
                    <p class='battle-end-subtitle'>Tu Diario Hablado de hoy</p>
                </div>
            """, unsafe_allow_html=True)

            # Breakdown por dimensión
            breakdown_html = "<div class='exam-skill-breakdown'>"
            breakdown_html += "<p class='summary-section'>📊 Tu desempeño</p>"
            for label, key, ico in [
                ("Fluidez", "fluency", "🌊"),
                ("Vocabulario", "vocab", "📚"),
                ("Gramática", "grammar", "🧩"),
            ]:
                val = feedback.get(key, 0)
                bar_color = "#39ff14" if val >= 80 else "#ffd400" if val >= 50 else "#ff5351"
                breakdown_html += (
                    f"<div class='exam-skill-row'>"
                    f"<span class='exam-skill-name'>{ico} {label}</span>"
                    f"<span class='exam-skill-bar'><span style='width:{val}%; background:{bar_color};'></span></span>"
                    f"<span class='exam-skill-score' style='color:{bar_color};'>{val}</span>"
                    f"</div>"
                )
            breakdown_html += "</div>"
            st.markdown(breakdown_html, unsafe_allow_html=True)

            # Tarjeta de "lo que dijiste"
            st.markdown(
                f"<div class='conv-summary'>"
                f"<p class='summary-section'>🎤 Lo que dijiste</p>"
                f"<p class='summary-quote'>“{st.session_state.dh_transcript or ''}”</p>"
                f"<p class='summary-section'>💡 Comentario</p>"
                f"<p class='summary-suggest'>{feedback['comment']}</p>"
                f"<p class='summary-section'>🌟 Respuesta modelo (cómo lo diría un nativo)</p>"
                f"<p class='summary-quote' style='border-left-color:#39ff14; background: rgba(57,255,20,0.06);'>"
                f"“{feedback.get('model_answer', '')}”</p>"
                f"</div>",
                unsafe_allow_html=True
            )

            if st.session_state.get("last_save_error"):
                render_save_failure(st.session_state.last_save_error, xp_award)

            col_x1, col_x2 = st.columns(2)
            with col_x1:
                if st.button(f"⚡ Reclamar +{xp_award} XP", key="dh_claim_xp",
                             use_container_width=True, type="primary"):
                    queue_xp_save(
                        user=user, xp_award=xp_award,
                        score_pct=sc / 100.0, attempts=1,
                        world="journal", skill="speaking",
                        lesson_type="speaking_journal",
                        success_msg=f"¡+{xp_award} XP en tu Diario!"
                    )
                    st.rerun()
            with col_x2:
                if st.button("🏠 Volver al mapa", key="dh_back",
                             use_container_width=True, type="secondary"):
                    reset_to_worlds()
                    st.rerun()

            send_weekly_report()
            st.stop()

        # ── Pantalla del prompt + grabación ──
        st.markdown(
            f"<p class='worlds-section-title' style='color:{dh_accent};'>"
            f"📔 DIARIO HABLADO · HOY</p>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<div class='fc-card' style='--fc-accent: {dh_accent};'>"
            f"<div class='fc-emoji'>{prompt['emoji']}</div>"
            f"<p class='writing-prompt-text' style='color:#e0e2e6; margin: 6px 0 8px;'>"
            f"{prompt['en']}</p>"
            f"<p class='battle-q-hint' style='margin: 0; border: none; "
            f"background: transparent; padding: 0;'>💡 <i>{prompt['es']}</i></p>"
            f"</div>",
            unsafe_allow_html=True
        )

        st.markdown(
            "<p class='sb-section-label' style='text-align:center;'>"
            "Habla 30 segundos en INGLÉS. Sin guión. Solo lo que pienses.</p>",
            unsafe_allow_html=True
        )

        # Grabador de audio
        col_dl, col_dc, col_dr = st.columns([1, 3, 1])
        with col_dc:
            dh_rec = audio_recorder(
                text="Grabar mi diario", recording_color="#ff5351",
                neutral_color=dh_accent, icon_size="2x",
                key="dh_recorder"
            )

        if dh_rec and not st.session_state.dh_transcript:
            with st.spinner("Transcribiendo tu voz..."):
                transcript, terr = transcribe_audio(dh_rec)
            if terr:
                show_error(terr)
            elif transcript:
                st.session_state.dh_audio = dh_rec
                st.session_state.dh_transcript = transcript
                st.rerun()

        # Si hay transcripción, mostrarla y permitir confirmar
        if st.session_state.dh_transcript:
            st.markdown(
                f"<div class='conv-summary' style='margin: 12px 0;'>"
                f"<p class='summary-section'>📝 Esto entendí que dijiste</p>"
                f"<p class='summary-quote'>“{st.session_state.dh_transcript}”</p>"
                f"</div>",
                unsafe_allow_html=True
            )
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                if st.button("🔁 Grabar de nuevo", key="dh_retry",
                             use_container_width=True, type="secondary"):
                    st.session_state.dh_audio = None
                    st.session_state.dh_transcript = None
                    st.rerun()
            with col_e2:
                if st.button("✓ Evaluar mi diario", key="dh_eval",
                             use_container_width=True, type="primary"):
                    cefr_now = get_cefr_info(
                        next((e["total_xp"] for e in get_leaderboard()
                              if e["profile"] == user), 0)
                    )["code"]
                    with st.spinner("Analizando tu inglés..."):
                        fb = evaluate_speaking_journal(
                            prompt["en"],
                            st.session_state.dh_transcript,
                            cefr_now
                        )
                    st.session_state.dh_feedback = fb
                    st.session_state.dh_finished = True
                    st.rerun()

        st.write("")
        if st.button("✕ Salir", key="dh_abandon", type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.13) TRANSLATE INVERSE MODE (Taller de Letras) ───────────────
    if st.session_state.ti_items is not None:
        ti_world_meta = get_world_meta(
            st.session_state.get("current_world", "writing"), user
        )
        ti_accent = ti_world_meta.get("accent", "#ff66c4")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {ti_accent}; }}</style>",
            unsafe_allow_html=True
        )

        items = st.session_state.ti_items
        idx   = st.session_state.ti_index
        total = len(items)
        answers  = st.session_state.ti_answers or [""] * total
        feedback = st.session_state.ti_feedback or [None] * total

        # ── Pantalla final ──
        if st.session_state.ti_finished or idx >= total:
            scores = [fb["score"] for fb in feedback if fb]
            avg_score = sum(scores) / len(scores) if scores else 0
            xp_award = max(15, int(avg_score / 2))
            color_avg = "#39ff14" if avg_score >= 80 else "#ffd400" if avg_score >= 55 else "#ff5351"

            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: {color_avg}; box-shadow: 0 0 30px {color_avg};'>
                    <div class='battle-end-emoji' style='color:{color_avg};'>✍️</div>
                    <h1 class='battle-end-title' style='color:{color_avg}; text-shadow:0 0 20px {color_avg};'>
                        {int(avg_score)}/100
                    </h1>
                    <p class='battle-end-subtitle'>Puntuación promedio en {total} traducciones</p>
                </div>
            """, unsafe_allow_html=True)

            # Repasar todas las respuestas con feedback
            for i, it in enumerate(items):
                fb = feedback[i] if i < len(feedback) else None
                if not fb:
                    continue
                sc = fb["score"]
                sc_color = "#39ff14" if sc >= 80 else "#ffd400" if sc >= 55 else "#ff5351"
                st.markdown(
                    f"<div class='writing-review' style='--rev-accent: {sc_color};'>"
                    f"<p class='writing-rev-score'>{sc}/100</p>"
                    f"<p class='writing-rev-row'><b>🇪🇸 Español:</b> {it['spanish']}</p>"
                    f"<p class='writing-rev-row'><b>📝 Tu inglés:</b> <i>{answers[i] or '(vacío)'}</i></p>"
                    f"<p class='writing-rev-row'><b>✅ Correcto:</b> {fb['correct']}</p>"
                    f"<p class='writing-rev-comment'>💡 {fb['comment']}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            if st.session_state.get("last_save_error"):
                render_save_failure(st.session_state.last_save_error, xp_award)

            col_x1, col_x2 = st.columns(2)
            with col_x1:
                if st.button(f"⚡ Reclamar +{xp_award} XP", key="ti_claim_xp",
                             use_container_width=True, type="primary"):
                    queue_xp_save(
                        user=user, xp_award=xp_award,
                        score_pct=avg_score / 100.0, attempts=1,
                        world="writing", skill="writing", lesson_type="translate_inv",
                        success_msg=f"¡+{xp_award} XP en Traducción!"
                    )
                    st.rerun()
            with col_x2:
                if st.button("🏠 Volver al mapa", key="ti_back",
                             use_container_width=True, type="secondary"):
                    reset_to_worlds()
                    st.rerun()

            send_weekly_report()
            st.stop()

        # ── Oración actual ──
        item = items[idx]

        st.markdown(
            f"<p class='worlds-section-title' style='color:{ti_accent};'>"
            f"✍️ TRADUCCIÓN {idx + 1} / {total}</p>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<div class='writing-card' style='--w-accent: {ti_accent};'>"
            f"<p class='writing-prompt-label'>Traduce al inglés:</p>"
            f"<p class='writing-prompt-text'>🇪🇸 {item['spanish']}</p>"
            f"</div>",
            unsafe_allow_html=True
        )

        with st.form(key=f"ti_form_{idx}", clear_on_submit=False):
            user_translation = st.text_area(
                "Escribe tu traducción al inglés:",
                key=f"ti_input_{idx}",
                value=answers[idx] if idx < len(answers) else "",
                height=80,
                max_chars=300,
                placeholder="Type your English translation here...",
            )
            submitted = st.form_submit_button(
                "✓ Enviar y evaluar", use_container_width=True, type="primary"
            )

        if submitted:
            answers[idx] = user_translation.strip()
            st.session_state.ti_answers = answers
            with st.spinner("Evaluando tu traducción..."):
                fb = evaluate_writing(
                    task_type="translation",
                    original=item["spanish"],
                    user_text=user_translation,
                    reference=item["english_correct"],
                    cefr_code=get_cefr_info(
                        next((e["total_xp"] for e in get_leaderboard()
                              if e["profile"] == user), 0)
                    )["code"]
                )
            feedback[idx] = fb
            st.session_state.ti_feedback = feedback
            st.session_state.ti_index += 1
            if st.session_state.ti_index >= total:
                st.session_state.ti_finished = True
            st.rerun()

        st.write("")
        if st.button("✕ Salir", key="ti_abandon", type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.14) DESCRIBE SCENE MODE (Taller de Letras) ──────────────────
    if st.session_state.ds_scenes is not None:
        ds_world_meta = get_world_meta(
            st.session_state.get("current_world", "writing"), user
        )
        ds_accent = ds_world_meta.get("accent", "#ff66c4")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {ds_accent}; }}</style>",
            unsafe_allow_html=True
        )

        scenes = st.session_state.ds_scenes
        idx    = st.session_state.ds_index
        total  = len(scenes)
        answers  = st.session_state.ds_answers or [""] * total
        feedback = st.session_state.ds_feedback or [None] * total

        # ── Pantalla final ──
        if st.session_state.ds_finished or idx >= total:
            scores = [fb["score"] for fb in feedback if fb]
            avg_score = sum(scores) / len(scores) if scores else 0
            xp_award = max(15, int(avg_score / 2))
            color_avg = "#39ff14" if avg_score >= 80 else "#ffd400" if avg_score >= 55 else "#ff5351"

            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: {color_avg}; box-shadow: 0 0 30px {color_avg};'>
                    <div class='battle-end-emoji' style='color:{color_avg};'>🎨</div>
                    <h1 class='battle-end-title' style='color:{color_avg}; text-shadow:0 0 20px {color_avg};'>
                        {int(avg_score)}/100
                    </h1>
                    <p class='battle-end-subtitle'>Puntuación promedio en {total} descripciones</p>
                </div>
            """, unsafe_allow_html=True)

            for i, sc in enumerate(scenes):
                fb = feedback[i] if i < len(feedback) else None
                if not fb:
                    continue
                sscore = fb["score"]
                sc_color = "#39ff14" if sscore >= 80 else "#ffd400" if sscore >= 55 else "#ff5351"
                st.markdown(
                    f"<div class='writing-review' style='--rev-accent: {sc_color};'>"
                    f"<p class='writing-rev-score'>{sscore}/100</p>"
                    f"<p class='writing-rev-row'><b>Escena:</b> <span style='font-size:1.5rem;'>{sc['emoji_scene']}</span></p>"
                    f"<p class='writing-rev-row'><b>📝 Tu texto:</b> <i>{answers[i] or '(vacío)'}</i></p>"
                    f"<p class='writing-rev-row'><b>✅ Ejemplo:</b> {fb['correct']}</p>"
                    f"<p class='writing-rev-comment'>💡 {fb['comment']}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            if st.session_state.get("last_save_error"):
                render_save_failure(st.session_state.last_save_error, xp_award)

            col_x1, col_x2 = st.columns(2)
            with col_x1:
                if st.button(f"⚡ Reclamar +{xp_award} XP", key="ds_claim_xp",
                             use_container_width=True, type="primary"):
                    queue_xp_save(
                        user=user, xp_award=xp_award,
                        score_pct=avg_score / 100.0, attempts=1,
                        world="writing", skill="writing", lesson_type="describe_scene",
                        success_msg=f"¡+{xp_award} XP describiendo!"
                    )
                    st.rerun()
            with col_x2:
                if st.button("🏠 Volver al mapa", key="ds_back",
                             use_container_width=True, type="secondary"):
                    reset_to_worlds()
                    st.rerun()

            send_weekly_report()
            st.stop()

        # ── Escena actual ──
        scene = scenes[idx]

        st.markdown(
            f"<p class='worlds-section-title' style='color:{ds_accent};'>"
            f"🎨 ESCENA {idx + 1} / {total}</p>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<div class='writing-card' style='--w-accent: {ds_accent};'>"
            f"<div class='ds-scene'>{scene['emoji_scene']}</div>"
            f"<p class='writing-prompt-label'>📝 Tarea:</p>"
            f"<p class='writing-prompt-text' style='font-size:1.0rem;'>{scene['prompt_es']}</p>"
            f"</div>",
            unsafe_allow_html=True
        )

        with st.form(key=f"ds_form_{idx}", clear_on_submit=False):
            user_desc = st.text_area(
                "Escribe en inglés (1-2 oraciones):",
                key=f"ds_input_{idx}",
                value=answers[idx] if idx < len(answers) else "",
                height=100,
                max_chars=400,
                placeholder="Describe the scene in English...",
            )
            submitted_ds = st.form_submit_button(
                "✓ Enviar y evaluar", use_container_width=True, type="primary"
            )

        if submitted_ds:
            answers[idx] = user_desc.strip()
            st.session_state.ds_answers = answers
            with st.spinner("Evaluando tu descripción..."):
                fb = evaluate_writing(
                    task_type="description",
                    original=f"{scene['emoji_scene']} — {scene['prompt_es']}",
                    user_text=user_desc,
                    reference=scene["sample_en"],
                    cefr_code=get_cefr_info(
                        next((e["total_xp"] for e in get_leaderboard()
                              if e["profile"] == user), 0)
                    )["code"]
                )
            feedback[idx] = fb
            st.session_state.ds_feedback = feedback
            st.session_state.ds_index += 1
            if st.session_state.ds_index >= total:
                st.session_state.ds_finished = True
            st.rerun()

        st.write("")
        if st.button("✕ Salir", key="ds_abandon", type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.15) ROLEPLAY PICKER (selector de escenarios) ────────────────
    if st.session_state.rp_picker:
        rp_world_meta = get_world_meta("chat", user)
        rp_accent = rp_world_meta.get("accent", "#c464ff")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {rp_accent}; }}</style>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<p class='worlds-section-title' style='color:{rp_accent};'>"
            f"🎭 ELIGE TU ESCENARIO DE ROLE-PLAY</p>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<p style='text-align:center; color:#a8acb3; font-size:0.92rem; margin: 4px 0 14px;'>"
            "Cada escenario tiene misiones que debes completar conversando en inglés.</p>",
            unsafe_allow_html=True
        )

        # Filtrar escenarios por nivel CEFR del usuario (mostrar todos pero marcar)
        for row_start in range(0, len(ROLEPLAY_SCENARIOS), 2):
            cols_rp = st.columns(2)
            for j, sc in enumerate(ROLEPLAY_SCENARIOS[row_start:row_start + 2]):
                with cols_rp[j]:
                    st.markdown(
                        f"<div class='rp-card'>"
                        f"<div class='rp-emoji'>{sc['emoji']}</div>"
                        f"<p class='rp-name'>{sc['name']}</p>"
                        f"<p class='rp-meta'>{sc['cefr']} · {len(sc['objectives'])} misiones</p>"
                        f"<p class='rp-role'>Tu rol: <i>{sc['role_user']}</i></p>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    if st.button(f"Empezar →", key=f"rp_pick_{sc['key']}",
                                 use_container_width=True, type="primary"):
                        start_conversation("chat", scenario_key=sc["key"])
                        st.rerun()

        st.write("")
        if st.button("← Volver", key="rp_back", type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.16) MINIMAL PAIRS MODE (Estudio de Sonido) ──────────────────
    if st.session_state.mp_pairs is not None:
        mp_world_meta = get_world_meta(
            st.session_state.get("current_world", "sound"), user
        )
        mp_accent = mp_world_meta.get("accent", "#39ff14")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {mp_accent}; }}</style>",
            unsafe_allow_html=True
        )

        pairs = st.session_state.mp_pairs
        idx   = st.session_state.mp_index
        total = len(pairs)

        # Pantalla final
        if st.session_state.mp_finished or idx >= total:
            correct = st.session_state.mp_correct
            score_pct = (correct / total) * 100.0 if total else 0
            xp_award = max(15, int(score_pct / 2))
            color_avg = "#39ff14" if score_pct >= 80 else "#ffd400" if score_pct >= 55 else "#ff5351"
            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: {color_avg}; box-shadow: 0 0 30px {color_avg};'>
                    <div class='battle-end-emoji' style='color:{color_avg};'>👯</div>
                    <h1 class='battle-end-title' style='color:{color_avg}; text-shadow:0 0 20px {color_avg};'>
                        {int(score_pct)}%
                    </h1>
                    <p class='battle-end-subtitle'>{correct} de {total} pares correctos</p>
                </div>
            """, unsafe_allow_html=True)

            if st.session_state.get("last_save_error"):
                render_save_failure(st.session_state.last_save_error, xp_award)

            col_x1, col_x2 = st.columns(2)
            with col_x1:
                if st.button(f"⚡ Reclamar +{xp_award} XP", key="mp_claim_xp",
                             use_container_width=True, type="primary"):
                    queue_xp_save(
                        user=user, xp_award=xp_award,
                        score_pct=score_pct / 100.0, attempts=1,
                        world="sound", skill="listening", lesson_type="min_pairs",
                        success_msg=f"¡+{xp_award} XP en Pares Mínimos!"
                    )
                    st.rerun()
            with col_x2:
                if st.button("🏠 Volver al mapa", key="mp_back",
                             use_container_width=True, type="secondary"):
                    reset_to_worlds()
                    st.rerun()

            send_weekly_report()
            st.stop()

        # Par actual
        pair = pairs[idx]
        chosen = st.session_state.mp_chosen
        correct_idx = pair["correct_idx"]
        correct_word = pair["word_a"] if correct_idx == 0 else pair["word_b"]

        st.markdown(
            f"<p class='worlds-section-title' style='color:{mp_accent};'>"
            f"👯 PAR {idx + 1} / {total}</p>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<div class='mp-card' style='--mp-accent: {mp_accent};'>"
            f"<p class='mp-hint'>Escucha atentamente: ¿cuál palabra se dijo?</p>"
            f"</div>",
            unsafe_allow_html=True
        )

        # Botón de audio
        col_al, col_ac, col_ar = st.columns([1, 2, 1])
        with col_ac:
            if st.button("🔊 Escuchar palabra", key=f"mp_audio_{idx}",
                         use_container_width=True, type="secondary"):
                with st.spinner("Generando audio..."):
                    audio_bytes = generate_lesson_audio(correct_word)
                if audio_bytes:
                    st.session_state.mp_audio = audio_bytes
                else:
                    st.warning("No pude generar el audio.")
        if st.session_state.mp_audio:
            st.audio(st.session_state.mp_audio, format="audio/mp3")

        st.write("")

        # 2 opciones grandes
        if chosen is None:
            col_o1, col_o2 = st.columns(2)
            with col_o1:
                if st.button(f"🅰️  {pair['word_a']}", key=f"mp_a_{idx}",
                             use_container_width=True, type="secondary"):
                    st.session_state.mp_chosen = 0
                    if correct_idx == 0:
                        st.session_state.mp_correct += 1
                    st.rerun()
            with col_o2:
                if st.button(f"🅱️  {pair['word_b']}", key=f"mp_b_{idx}",
                             use_container_width=True, type="secondary"):
                    st.session_state.mp_chosen = 1
                    if correct_idx == 1:
                        st.session_state.mp_correct += 1
                    st.rerun()
        else:
            is_correct = (chosen == correct_idx)
            # Pintar ambas
            col_o1, col_o2 = st.columns(2)
            for opt_idx, (col, w, m) in enumerate([
                (col_o1, pair["word_a"], pair.get("meaning_a", "")),
                (col_o2, pair["word_b"], pair.get("meaning_b", "")),
            ]):
                if opt_idx == correct_idx:
                    bg = "#39ff14"; fg = "#0a0b1e"; mark = "✓"
                elif opt_idx == chosen:
                    bg = "#ff5351"; fg = "#fff"; mark = "✗"
                else:
                    bg = "transparent"; fg = "#a8acb3"; mark = ""
                with col:
                    st.markdown(
                        f"<div style='padding:16px 12px; border-radius:8px; "
                        f"background:{bg}; color:{fg}; text-align:center; "
                        f"font-weight:700;'>{mark} {w}<br>"
                        f"<span style='font-size:0.78rem; font-weight:400; opacity:0.85;'>{m}</span></div>",
                        unsafe_allow_html=True
                    )

            if is_correct:
                st.markdown(
                    f"<div class='fc-feedback ok'>✓ ¡Correcto! Se dijo <b>{correct_word}</b>.</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='fc-feedback bad'>✗ La palabra era <b>{correct_word}</b>. Escúchala de nuevo.</div>",
                    unsafe_allow_html=True
                )

            next_label = "Siguiente par →" if (idx + 1) < total else "Resultados 🏁"
            if st.button(next_label, key=f"mp_next_{idx}",
                         use_container_width=True, type="primary"):
                st.session_state.mp_index += 1
                st.session_state.mp_chosen = None
                st.session_state.mp_audio = None
                if st.session_state.mp_index >= total:
                    st.session_state.mp_finished = True
                st.rerun()

        st.write("")
        if st.button("✕ Salir", key="mp_abandon", type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.165) SHADOW SPEAKING MODE (Estudio de Sonido) ───────────────
    if st.session_state.ss_phrases is not None:
        ss_world_meta = get_world_meta(
            st.session_state.get("current_world", "sound"), user
        )
        ss_accent = ss_world_meta.get("accent", "#39ff14")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {ss_accent}; }}</style>",
            unsafe_allow_html=True
        )

        phrases = st.session_state.ss_phrases
        idx     = st.session_state.ss_index
        total   = len(phrases)
        results = st.session_state.ss_results or []

        # ── Pantalla final ──
        if st.session_state.ss_finished or idx >= total:
            if results:
                avg_score = sum(r["score"] for r in results) / len(results)
            else:
                avg_score = 0
            xp_award = max(15, int(avg_score / 2))
            color_avg = "#39ff14" if avg_score >= 80 else "#ffd400" if avg_score >= 55 else "#ff5351"

            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: {color_avg}; box-shadow: 0 0 30px {color_avg};'>
                    <div class='battle-end-emoji' style='color:{color_avg};'>🎵</div>
                    <h1 class='battle-end-title' style='color:{color_avg}; text-shadow:0 0 20px {color_avg};'>
                        {int(avg_score)}/100
                    </h1>
                    <p class='battle-end-subtitle'>Promedio de similitud fonética en {total} frases</p>
                </div>
            """, unsafe_allow_html=True)

            if st.session_state.get("last_save_error"):
                render_save_failure(st.session_state.last_save_error, xp_award)

            col_x1, col_x2 = st.columns(2)
            with col_x1:
                if st.button(f"⚡ Reclamar +{xp_award} XP", key="ss_claim_xp",
                             use_container_width=True, type="primary"):
                    queue_xp_save(
                        user=user, xp_award=xp_award,
                        score_pct=avg_score / 100.0, attempts=1,
                        world="sound", skill="speaking", lesson_type="shadow_speak",
                        success_msg=f"¡+{xp_award} XP en Shadow Speaking!"
                    )
                    st.rerun()
            with col_x2:
                if st.button("🏠 Volver al mapa", key="ss_back",
                             use_container_width=True, type="secondary"):
                    reset_to_worlds()
                    st.rerun()

            send_weekly_report()
            st.stop()

        phrase = phrases[idx]

        st.markdown(
            f"<p class='worlds-section-title' style='color:{ss_accent};'>"
            f"🎵 FRASE {idx + 1} / {total}</p>",
            unsafe_allow_html=True
        )

        # Tarjeta con la frase + emoji
        st.markdown(
            f"<div class='fc-card' style='--fc-accent: {ss_accent};'>"
            f"<div class='fc-emoji' style='font-size:3.6rem;'>{phrase['emoji']}</div>"
            f"<p class='writing-prompt-text' style='color:#e0e2e6; margin: 6px 0 8px;'>"
            f"{phrase['text']}</p>"
            f"<p class='writing-prompt-label' style='font-style:italic;'>"
            f"🇪🇸 {phrase['meaning']}</p>"
            f"</div>",
            unsafe_allow_html=True
        )

        # Paso 1: Escuchar modelo
        col_al, col_ac, col_ar = st.columns([1, 2, 1])
        with col_ac:
            if st.button("🔊 Escuchar modelo", key=f"ss_audio_{idx}",
                         use_container_width=True, type="secondary"):
                with st.spinner("Generando audio..."):
                    audio_bytes = generate_lesson_audio(phrase["text"])
                if audio_bytes:
                    st.session_state.ss_last_audio = audio_bytes
        if st.session_state.ss_last_audio:
            st.audio(st.session_state.ss_last_audio, format="audio/mp3")

        st.write("")
        st.markdown(
            "<p class='sb-section-label'>Ahora repítela tú — graba imitando el ritmo:</p>",
            unsafe_allow_html=True
        )

        # Paso 2: Grabar al usuario
        rec_audio = audio_recorder(
            text="Grabar", recording_color="#ff5351",
            neutral_color=ss_accent, icon_size="2x",
            key=f"ss_rec_{idx}"
        )

        last_score = st.session_state.ss_last_score
        if rec_audio and last_score is None:
            with st.spinner("Transcribiendo y evaluando..."):
                transcribed, terr = transcribe_audio(rec_audio)
                if terr:
                    show_error(terr)
                else:
                    score = score_pronunciation(phrase["text"], transcribed)
                    st.session_state.ss_last_score = score
                    st.rerun()

        # Mostrar resultado de la última grabación
        if last_score:
            sc = last_score["score"]
            tier = last_score["tier"]
            heard = last_score.get("heard", "")
            tier_color = "#39ff14" if tier == "good" else "#ffd400" if tier == "mid" else "#ff5351"
            tier_label = "¡Excelente!" if tier == "good" else "Cerca, prueba otra vez" if tier == "mid" else "Inténtalo de nuevo"
            st.markdown(
                f"<div class='fc-feedback' style='background: rgba(0,0,0,0.2); border:1px solid {tier_color}; color:{tier_color};'>"
                f"<b>{tier_label} — {sc}/100</b><br>"
                f"<span style='color:#a8acb3; font-size:0.85rem;'>Escuché: <i>“{heard}”</i></span>"
                f"</div>",
                unsafe_allow_html=True
            )

            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button("🔁 Intentar de nuevo", key=f"ss_retry_{idx}",
                             use_container_width=True, type="secondary"):
                    st.session_state.ss_last_score = None
                    st.rerun()
            with col_r2:
                next_label = "✓ Aceptar y siguiente →" if (idx + 1) < total else "Resultados 🏁"
                if st.button(next_label, key=f"ss_next_{idx}",
                             use_container_width=True, type="primary"):
                    results.append({"score": sc, "tier": tier,
                                    "text": phrase["text"], "heard": heard})
                    st.session_state.ss_results = results
                    st.session_state.ss_index += 1
                    st.session_state.ss_last_audio = None
                    st.session_state.ss_last_score = None
                    if st.session_state.ss_index >= total:
                        st.session_state.ss_finished = True
                    st.rerun()

        st.write("")
        if st.button("✕ Salir", key="ss_abandon", type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.17) LISTEN ID MODE (¿Qué Escuché?) en Estudio de Sonido ────
    if st.session_state.li_cards is not None:
        li_world_meta = get_world_meta(
            st.session_state.get("current_world", "sound"), user
        )
        li_accent = li_world_meta.get("accent", "#00eefc")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {li_accent}; }}</style>",
            unsafe_allow_html=True
        )

        li_cards = st.session_state.li_cards
        idx   = st.session_state.li_index
        total = len(li_cards)

        if st.session_state.li_finished or idx >= total:
            correct = st.session_state.li_correct
            score_pct = (correct / total) * 100.0 if total else 0
            xp_award = max(15, int(score_pct / 2))
            color_avg = "#39ff14" if score_pct >= 80 else "#ffd400" if score_pct >= 55 else "#ff5351"
            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: {color_avg}; box-shadow: 0 0 30px {color_avg};'>
                    <div class='battle-end-emoji' style='color:{color_avg};'>👂</div>
                    <h1 class='battle-end-title' style='color:{color_avg}; text-shadow:0 0 20px {color_avg};'>
                        {int(score_pct)}%
                    </h1>
                    <p class='battle-end-subtitle'>{correct} de {total} palabras identificadas</p>
                </div>
            """, unsafe_allow_html=True)

            if st.session_state.get("last_save_error"):
                render_save_failure(st.session_state.last_save_error, xp_award)

            col_x1, col_x2 = st.columns(2)
            with col_x1:
                if st.button(f"⚡ Reclamar +{xp_award} XP", key="li_claim_xp",
                             use_container_width=True, type="primary"):
                    queue_xp_save(
                        user=user, xp_award=xp_award,
                        score_pct=score_pct / 100.0, attempts=1,
                        world="sound", skill="listening", lesson_type="listen_id",
                        success_msg=f"¡+{xp_award} XP en Listen ID!"
                    )
                    st.rerun()
            with col_x2:
                if st.button("🏠 Volver al mapa", key="li_back",
                             use_container_width=True, type="secondary"):
                    reset_to_worlds()
                    st.rerun()

            send_weekly_report()
            st.stop()

        card = li_cards[idx]
        chosen = st.session_state.li_chosen

        st.markdown(
            f"<p class='worlds-section-title' style='color:{li_accent};'>"
            f"👂 PALABRA {idx + 1} / {total}</p>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<div class='fc-card' style='--fc-accent: {li_accent};'>"
            f"<div class='fc-emoji' style='font-size:5rem;'>🔊</div>"
            f"<p class='fc-hint'>Escucha la palabra y elige cuál es</p>"
            f"</div>",
            unsafe_allow_html=True
        )

        col_al, col_ac, col_ar = st.columns([1, 2, 1])
        with col_ac:
            if st.button("🔊 Escuchar", key=f"li_audio_{idx}",
                         use_container_width=True, type="secondary"):
                with st.spinner("Generando audio..."):
                    audio_bytes = generate_lesson_audio(card["word"])
                if audio_bytes:
                    st.session_state.li_audio = audio_bytes
        if st.session_state.li_audio:
            st.audio(st.session_state.li_audio, format="audio/mp3")

        st.write("")

        if chosen is None:
            opt_cols = st.columns(2)
            for i, opt in enumerate(card["options"]):
                with opt_cols[i % 2]:
                    if st.button(opt, key=f"li_opt_{idx}_{i}",
                                 use_container_width=True, type="secondary"):
                        st.session_state.li_chosen = i
                        if i == card["correct_idx"]:
                            st.session_state.li_correct += 1
                        st.rerun()
        else:
            is_correct = (chosen == card["correct_idx"])
            opt_cols = st.columns(2)
            for i, opt in enumerate(card["options"]):
                with opt_cols[i % 2]:
                    if i == card["correct_idx"]:
                        bg = "#39ff14"; fg = "#0a0b1e"; mark = "✓"
                    elif i == chosen:
                        bg = "#ff5351"; fg = "#fff"; mark = "✗"
                    else:
                        bg = "transparent"; fg = "#a8acb3"; mark = ""
                    st.markdown(
                        f"<div style='padding:14px 12px; border-radius:8px; "
                        f"background:{bg}; color:{fg}; text-align:center; "
                        f"font-weight:700; margin-bottom:8px;'>{mark} {opt}</div>",
                        unsafe_allow_html=True
                    )

            if is_correct:
                st.markdown(
                    f"<div class='fc-feedback ok'>"
                    f"✓ ¡Correcto! Era <b>{card['word']}</b> ({card['meaning']})</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='fc-feedback bad'>"
                    f"✗ Era <b>{card['word']}</b> ({card['meaning']}).</div>",
                    unsafe_allow_html=True
                )

            next_label = "Siguiente →" if (idx + 1) < total else "Resultados 🏁"
            if st.button(next_label, key=f"li_next_{idx}",
                         use_container_width=True, type="primary"):
                st.session_state.li_index += 1
                st.session_state.li_chosen = None
                st.session_state.li_audio = None
                if st.session_state.li_index >= total:
                    st.session_state.li_finished = True
                st.rerun()

        st.write("")
        if st.button("✕ Salir", key="li_abandon", type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.18) EXAM MODE (test cumulativo semanal) ─────────────────────
    if st.session_state.ex_questions is not None:
        ex_accent = "#ffd400"
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {ex_accent}; }}</style>",
            unsafe_allow_html=True
        )

        questions = st.session_state.ex_questions
        idx       = st.session_state.ex_index
        total     = len(questions)
        answers   = st.session_state.ex_answers or [None] * total

        # ── Pantalla final ──
        if st.session_state.ex_finished or idx >= total:
            correct = st.session_state.ex_correct
            score_pct = (correct / total) * 100.0 if total else 0
            # XP del examen: bonus mayor que un quiz normal (50-150)
            xp_award = max(50, int(score_pct * 1.5))
            # Bonus extra si es viernes (día oficial del examen)
            friday_bonus = 0
            if datetime.date.today().weekday() == 4:
                friday_bonus = int(xp_award * 0.5)
                xp_award += friday_bonus
            color_avg = "#39ff14" if score_pct >= 80 else "#ffd400" if score_pct >= 55 else "#ff5351"

            friday_html = (
                f"<p style='color:#ffd400; margin-top:6px; font-weight:700;'>"
                f"🎉 ¡Bonus de viernes +{friday_bonus} XP!</p>"
                if friday_bonus > 0 else ""
            )
            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: {color_avg}; box-shadow: 0 0 30px {color_avg};'>
                    <div class='battle-end-emoji' style='color:{color_avg};'>📝</div>
                    <h1 class='battle-end-title' style='color:{color_avg}; text-shadow:0 0 20px {color_avg};'>
                        {int(score_pct)}%
                    </h1>
                    <p class='battle-end-subtitle'>Examen completado · {correct}/{total} correctas</p>
                    {friday_html}
                </div>
            """, unsafe_allow_html=True)

            # Mini-review de aciertos/errores por skill
            by_skill = {}
            for i, q in enumerate(questions):
                sk = q.get("skill", "general")
                by_skill.setdefault(sk, {"total": 0, "correct": 0})
                by_skill[sk]["total"] += 1
                ua = (answers[i] or "").strip().lower()
                ca = q["answer"].strip().lower()
                if ua == ca:
                    by_skill[sk]["correct"] += 1
            review_html = "<div class='exam-skill-breakdown'>"
            review_html += "<p class='summary-section'>📊 Desempeño por habilidad</p>"
            for sk, d in by_skill.items():
                pct = (d["correct"] / d["total"] * 100) if d["total"] else 0
                bar_color = "#39ff14" if pct >= 80 else "#ffd400" if pct >= 50 else "#ff5351"
                review_html += (
                    f"<div class='exam-skill-row'>"
                    f"<span class='exam-skill-name'>{sk}</span>"
                    f"<span class='exam-skill-bar'><span style='width:{pct}%; background:{bar_color};'></span></span>"
                    f"<span class='exam-skill-score' style='color:{bar_color};'>{d['correct']}/{d['total']}</span>"
                    f"</div>"
                )
            review_html += "</div>"
            st.markdown(review_html, unsafe_allow_html=True)

            if st.session_state.get("last_save_error"):
                render_save_failure(st.session_state.last_save_error, xp_award)

            col_x1, col_x2 = st.columns(2)
            with col_x1:
                if st.button(f"⚡ Reclamar +{xp_award} XP", key="ex_claim_xp",
                             use_container_width=True, type="primary"):
                    queue_xp_save(
                        user=user, xp_award=xp_award,
                        score_pct=score_pct / 100.0, attempts=1,
                        world="exam", skill="exam", lesson_type="exam",
                        success_msg=f"¡Examen aprobado, +{xp_award} XP!"
                    )
                    st.rerun()
            with col_x2:
                if st.button("🏠 Volver al mapa", key="ex_back",
                             use_container_width=True, type="secondary"):
                    reset_to_worlds()
                    st.rerun()

            send_weekly_report()
            st.stop()

        # ── Pregunta actual ──
        q = questions[idx]
        qtype = q["type"]
        st.markdown(
            f"<p class='worlds-section-title' style='color:{ex_accent};'>"
            f"📝 EXAMEN · PREGUNTA {idx + 1} / {total} · <span style='opacity:0.7;'>{q['skill']}</span></p>",
            unsafe_allow_html=True
        )

        # Texto de la pregunta (con blank visual si es fitb)
        q_html = q["q"]
        if qtype == "fitb":
            q_html = q_html.replace("___", "<span class='battle-blank'>______</span>")
        elif qtype == "translation":
            q_html = f"🇪🇸 {q_html}"

        hint_html = ""
        if q.get("hint"):
            hint_html = f"<p class='battle-q-hint'>💡 <i>{q['hint']}</i></p>"

        st.markdown(
            f"<div class='battle-question'>"
            f"<div class='battle-q-meta'>"
            f"<span class='battle-q-num'>{q['skill'].upper()}</span>"
            f"<span class='battle-q-type'>{qtype.upper()}</span>"
            f"</div>"
            f"<div class='battle-q-text'>{q_html}</div>"
            f"{hint_html}"
            f"</div>",
            unsafe_allow_html=True
        )

        with st.form(key=f"ex_form_{idx}", clear_on_submit=False):
            user_answer = ""
            if qtype == "mc" and q.get("options"):
                opts = ["— Selecciona —"] + list(q["options"])
                pick = st.radio("Respuesta",
                                options=opts, index=0,
                                label_visibility="collapsed",
                                key=f"ex_mc_{idx}")
                user_answer = "" if pick == "— Selecciona —" else pick
            else:  # fitb o translation
                user_answer = st.text_input(
                    "Respuesta", placeholder="Escribe tu respuesta en inglés...",
                    label_visibility="collapsed", key=f"ex_in_{idx}"
                )
            submitted = st.form_submit_button(
                "✓ Responder", use_container_width=True, type="primary"
            )

        if submitted:
            answers[idx] = user_answer.strip()
            ua = user_answer.strip().lower()
            ca = q["answer"].strip().lower()
            if qtype == "translation":
                # Translation: aceptar si comparte >70% de palabras con la answer
                ua_words = set(ua.split())
                ca_words = set(ca.split())
                if ua_words and ca_words:
                    overlap = len(ua_words & ca_words) / max(len(ca_words), 1)
                    is_correct = overlap >= 0.7
                else:
                    is_correct = (ua == ca)
            else:
                is_correct = (ua == ca)
            if is_correct:
                st.session_state.ex_correct += 1
            st.session_state.ex_answers = answers
            st.session_state.ex_index += 1
            if st.session_state.ex_index >= total:
                st.session_state.ex_finished = True
            st.rerun()

        st.write("")
        if st.button("✕ Abandonar examen", key="ex_abandon", type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.19) CONVERSATION END SUMMARY ────────────────────────────────
    if st.session_state.conv_show_end:
        conv_world_meta = get_world_meta(
            st.session_state.get("current_world", ""), user
        )
        conv_accent = conv_world_meta.get("accent", "#c464ff")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {conv_accent}; }}</style>",
            unsafe_allow_html=True
        )

        scenario = st.session_state.get("rp_scenario")
        summary = st.session_state.get("conv_summary") or {}
        turn_count = st.session_state.conv_turn_count
        done = set(st.session_state.get("rp_done_objs") or [])

        # Calcular XP final
        bonus_xp = 0
        objs_total = 0
        if scenario:
            objs_total = len(scenario["objectives"])
            bonus_xp = len(done) * 5
            if objs_total > 0 and len(done) == objs_total:
                bonus_xp += 15
        xp_award = min(80, 20 + turn_count * 5 + bonus_xp)

        st.markdown(f"""
            <div class='battle-end battle-end-victory' style='border-color: {conv_accent}; box-shadow: 0 0 30px {conv_accent};'>
                <div class='battle-end-emoji' style='color:{conv_accent};'>💬</div>
                <h1 class='battle-end-title' style='color:{conv_accent}; text-shadow:0 0 20px {conv_accent};'>
                    ¡Buena charla!
                </h1>
                <p class='battle-end-subtitle'>
                    {turn_count} turnos · {f"{len(done)}/{objs_total} misiones" if scenario else "conversación libre"}
                </p>
            </div>
        """, unsafe_allow_html=True)

        # Tarjeta de resumen
        st.markdown("<div class='conv-summary'>", unsafe_allow_html=True)
        if scenario and objs_total > 0:
            obj_html = ""
            for i, o in enumerate(scenario["objectives"]):
                cls = "obj-done" if i in done else "obj-pending"
                mark = "✓" if i in done else "○"
                obj_html += f"<li class='{cls}'><span class='obj-mark'>{mark}</span> {o}</li>"
            st.markdown(
                f"<p class='summary-section'>🎯 Misiones</p>"
                f"<ul class='rp-obj-list'>{obj_html}</ul>",
                unsafe_allow_html=True
            )

        if summary.get("highlight"):
            st.markdown(
                f"<p class='summary-section'>🌟 Frase destacada</p>"
                f"<p class='summary-quote'>“{summary['highlight']}”</p>",
                unsafe_allow_html=True
            )

        if summary.get("new_words"):
            words_html = " ".join(
                f"<span class='summary-word'>{w}</span>"
                for w in summary["new_words"]
            )
            st.markdown(
                f"<p class='summary-section'>🌱 Palabras que usaste</p>"
                f"<p>{words_html}</p>",
                unsafe_allow_html=True
            )

        if summary.get("suggestion"):
            st.markdown(
                f"<p class='summary-section'>💡 Tip para la próxima</p>"
                f"<p class='summary-suggest'>{summary['suggestion']}</p>",
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.get("last_save_error"):
            render_save_failure(st.session_state.last_save_error, xp_award)

        col_x1, col_x2 = st.columns(2)
        with col_x1:
            if st.button(f"⚡ Reclamar +{xp_award} XP", key="conv_claim_xp",
                         use_container_width=True, type="primary"):
                lesson_type = "roleplay" if scenario else "conversation"
                queue_xp_save(
                    user, xp_award, 1.0, attempts=1,
                    world=st.session_state.get("current_world", ""),
                    skill="conversation", lesson_type=lesson_type,
                    success_msg=f"¡Gran conversación, {user}! +{xp_award} XP."
                )
                st.rerun()
        with col_x2:
            if st.button("🏠 Volver al mapa", key="conv_end_back",
                         use_container_width=True, type="secondary"):
                reset_to_worlds()
                st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.2) CONVERSATION MODE ───────────────────────────────────────
    if st.session_state.conv_active:
        conv_world_meta = get_world_meta(
            st.session_state.get("current_world", ""), user
        )
        conv_accent = conv_world_meta.get("accent", "#00eefc")
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {conv_accent}; }}</style>",
            unsafe_allow_html=True
        )

        # Escenario activo (si lo hay)
        scenario = st.session_state.get("rp_scenario")

        # Header
        if scenario:
            st.markdown(
                f"<p class='worlds-section-title' style='color:{conv_accent};"
                f" text-shadow:0 0 10px {conv_accent};'>"
                f"{scenario['emoji']} {scenario['name']}</p>",
                unsafe_allow_html=True
            )
            # Tarjeta de contexto: tu rol y el rol de la IA
            st.markdown(
                f"<div class='rp-context' style='--rp-accent: {conv_accent};'>"
                f"<p class='rp-context-row'><b>Tú:</b> {scenario['role_user']}</p>"
                f"<p class='rp-context-row'><b>IA:</b> {scenario['role_ai']}</p>"
                f"</div>",
                unsafe_allow_html=True
            )
            # Panel de misiones (objectives)
            done = set(st.session_state.get("rp_done_objs") or [])
            obj_items_html = ""
            for i, o in enumerate(scenario["objectives"]):
                cls = "obj-done" if i in done else "obj-pending"
                mark = "✓" if i in done else "☐"
                obj_items_html += f"<li class='{cls}'><span class='obj-mark'>{mark}</span> {o}</li>"
            st.markdown(
                f"<div class='rp-objectives'>"
                f"<p class='rp-obj-title'>🎯 Misiones — {len(done)}/{len(scenario['objectives'])}</p>"
                f"<ul class='rp-obj-list'>{obj_items_html}</ul>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<p class='worlds-section-title' style='color:{conv_accent};"
                f" text-shadow:0 0 10px {conv_accent};'>"
                f"💬 Conversación · {conv_world_meta.get('name','Mundo')}</p>",
                unsafe_allow_html=True
            )

        # Historial de mensajes
        history = st.session_state.conv_history or []

        # Si está vacío, generar el primer turno (saludo de la IA)
        if not history:
            cefr_now = get_cefr_info(
                next((e["total_xp"] for e in get_leaderboard() if e["profile"] == user), 0)
            )["code"]
            with st.spinner("Iniciando conversación..."):
                first_msg, err = conversation_send(
                    user, conv_world_meta, cefr_now,
                    [{"role": "user", "content": "(Start the conversation)"}],
                    scenario=scenario
                )
            if err:
                show_error(err)
            elif first_msg:
                history = [{"role": "assistant", "content": first_msg}]
                st.session_state.conv_history = history

        # Render bubbles
        for m in history:
            if m["role"] == "system":
                continue
            content = m["content"]

            # Parser robusto: separa main / gloss / tip puntual del feedback
            tip_part = ""
            gloss_part = ""
            main_part = content

            # Buscar el tip 💡 primero (puede ir al final)
            if "💡:" in main_part:
                main_part, _, tip_raw = main_part.partition("💡:")
                tip_part = tip_raw.strip()
            # Luego separar la gloss en español
            if "🇪🇸:" in main_part:
                main_part, _, gloss_raw = main_part.partition("🇪🇸:")
                gloss_part = gloss_raw.strip()

            gloss_html = (
                f"<span class='gloss'>🇪🇸: {gloss_part}</span>" if gloss_part else ""
            )
            tip_html = (
                f"<div class='conv-tip'>💡 <i>{tip_part}</i></div>"
                if tip_part and m["role"] == "assistant" else ""
            )

            speaker = "TUTOR" if m["role"] == "assistant" else user.upper()
            klass = "assistant" if m["role"] == "assistant" else "user"
            st.markdown(
                f"<div class='conv-bubble {klass}'>"
                f"<div class='speaker'>{speaker}</div>"
                f"{main_part.strip()}{gloss_html}"
                f"{tip_html}"
                f"</div>",
                unsafe_allow_html=True
            )

        # Botones para enviar respuesta (audio o texto)
        st.write("")
        st.markdown(
            "<p style='font-size:0.82rem; color:#a8acb3; margin: 4px 0;'>"
            "Tu turno · habla en inglés (o escribe abajo):</p>",
            unsafe_allow_html=True
        )

        col_c1, col_c2 = st.columns([1, 4])
        with col_c1:
            user_audio_conv = audio_recorder(
                text="Hablar", recording_color="#ff5351",
                neutral_color=conv_accent, icon_size="2x",
                key=f"conv_rec_{st.session_state.conv_turn_count}"
            )
        with col_c2:
            if user_audio_conv:
                with st.spinner("Transcribiendo..."):
                    transcribed_conv, terr = transcribe_audio(user_audio_conv)
                if terr:
                    show_error(terr)
                elif transcribed_conv:
                    st.session_state.conv_pending_user_input = transcribed_conv
                    st.success(f"Te escuché: *'{transcribed_conv}'*")

        text_conv = st.chat_input(
            "Escribe en inglés...",
            key=f"conv_text_{st.session_state.conv_turn_count}"
        )
        if text_conv:
            st.session_state.conv_pending_user_input = text_conv

        # Si hay input pendiente, enviar a la IA
        if st.session_state.conv_pending_user_input:
            user_input = st.session_state.conv_pending_user_input
            st.session_state.conv_pending_user_input = ""
            history = (st.session_state.conv_history or []) + [
                {"role": "user", "content": user_input}
            ]
            cefr_now = get_cefr_info(
                next((e["total_xp"] for e in get_leaderboard() if e["profile"] == user), 0)
            )["code"]
            with st.spinner("La IA está respondiendo..."):
                ai_msg, err2 = conversation_send(
                    user, conv_world_meta, cefr_now, history,
                    scenario=scenario
                )
            if err2:
                show_error(err2)
            elif ai_msg:
                history.append({"role": "assistant", "content": ai_msg})
                st.session_state.conv_history = history
                st.session_state.conv_turn_count += 1
                # Re-evaluar objectives si hay scenario activo (cada 2 turnos para ahorrar tokens)
                if scenario and st.session_state.conv_turn_count % 2 == 0:
                    done = check_scenario_objectives(scenario, history)
                    st.session_state.rp_done_objs = done
                st.rerun()

        # Botones finalizar
        st.write("")
        col_e1, col_e2 = st.columns(2)
        turn_count = st.session_state.conv_turn_count
        # Mínimo 3 turnos del usuario para reclamar XP
        can_claim = turn_count >= 3

        # Bonus XP si tiene scenario y completó misiones
        bonus_xp = 0
        if scenario:
            done = set(st.session_state.get("rp_done_objs") or [])
            total_objs = len(scenario["objectives"])
            bonus_xp = len(done) * 5
            if len(done) == total_objs:
                bonus_xp += 15  # bonus extra por completarlas todas

        with col_e1:
            if st.button(
                f"🏁 Terminar conversación ({turn_count}/3+)" if not can_claim else "🏁 Terminar conversación",
                key="conv_finish",
                use_container_width=True,
                type="primary",
                disabled=not can_claim
            ):
                # Antes de cerrar: re-evaluar objetivos y generar resumen
                if scenario:
                    final_done = check_scenario_objectives(scenario, history)
                    st.session_state.rp_done_objs = final_done
                with st.spinner("Preparando tu resumen..."):
                    summary = summarize_conversation(scenario, history, user)
                st.session_state.conv_summary = summary
                st.session_state.conv_show_end = True
                st.rerun()
        with col_e2:
            if st.button("✕ Salir", key="conv_abandon",
                         use_container_width=True, type="secondary"):
                reset_to_worlds()
                st.rerun()

        send_weekly_report()
        st.stop()

    # ── 2.3) SRS REVIEW MODE ─────────────────────────────────────────
    if st.session_state.srs_active:
        st.markdown(
            "<style>:root, .stApp { --profile-accent: #c464ff; }</style>",
            unsafe_allow_html=True
        )

        cards = st.session_state.srs_cards or []
        idx   = st.session_state.srs_index
        total = len(cards)

        # ── Sin cards o terminó ──
        if total == 0:
            st.markdown("""
                <div class='battle-end battle-end-victory' style='border-color: #c464ff; box-shadow: 0 0 28px rgba(196,100,255,0.3);'>
                    <div class='battle-end-emoji' style='color:#c464ff;'>🌱</div>
                    <h1 class='battle-end-title' style='color:#c464ff; text-shadow:0 0 18px #c464ff;'>
                        Sin repasos por ahora
                    </h1>
                    <p style='color:#a8acb3; margin:10px 0; font-size:1rem;'>
                        Aún no tienes palabras pendientes de repaso.<br>
                        ¡Completa lecciones para ir armando tu mazo!
                    </p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("🏠 Volver al mapa", key="srs_back_empty",
                         use_container_width=True, type="primary"):
                reset_to_worlds()
                st.rerun()
            send_weekly_report()
            st.stop()

        if st.session_state.srs_finished or idx >= total:
            attempted = st.session_state.srs_attempted
            correct   = st.session_state.srs_correct
            pct = (correct / attempted) if attempted else 0
            xp_award = 10 + correct * 5

            st.markdown(f"""
                <div class='battle-end battle-end-victory' style='border-color: #c464ff; box-shadow: 0 0 30px rgba(196,100,255,0.35);'>
                    <div class='battle-end-emoji' style='color:#c464ff;'>🧠</div>
                    <h1 class='battle-end-title' style='color:#c464ff; text-shadow:0 0 20px #c464ff;'>
                        Repaso Completo
                    </h1>
                    <div class='battle-end-stats'>
                        <div>
                            <div class='battle-end-stat-num' style='color:#39ff14; text-shadow:0 0 14px #39ff14;'>{correct}/{attempted}</div>
                            <div class='battle-end-stat-label'>Recordadas</div>
                        </div>
                        <div>
                            <div class='battle-end-stat-num' style='color:#00eefc; text-shadow:0 0 14px #00eefc;'>{int(pct*100)}%</div>
                            <div class='battle-end-stat-label'>Acierto</div>
                        </div>
                        <div>
                            <div class='battle-end-stat-num' style='color:#ff66c4; text-shadow:0 0 14px #ff66c4;'>+{xp_award}</div>
                            <div class='battle-end-stat-label'>XP ganado</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            st.write("")
            if st.button("✅ Terminar y guardar", key="srs_finish_claim",
                         use_container_width=True, type="primary"):
                queue_xp_save(
                    user, xp_award, pct, attempts=1,
                    world="srs", skill="vocabulary",
                    lesson_type="srs_review",
                    success_msg=f"¡Excelente memoria, {user}! +{xp_award} XP."
                )
                st.rerun()

            send_weekly_report()
            st.stop()

        # ── Card actual ──
        card = cards[idx]
        word        = str(card.get("word", "")).strip()
        translation = str(card.get("translation", "")).strip()
        emoji_card  = str(card.get("emoji", "📝")).strip() or "📝"

        st.markdown(
            f"<p style='text-align:center; color:#6b7280; font-size:0.78rem;"
            f" letter-spacing:2px; text-transform:uppercase; margin: 8px 0 0;'>"
            f"🧠 Repaso Inteligente · <b style='color:#c464ff;"
            f" text-shadow: 0 0 8px #c464ff;'>{idx+1}/{total}</b></p>",
            unsafe_allow_html=True
        )

        if not st.session_state.srs_revealed:
            st.markdown(f"""
                <div class='srs-card'>
                    <p class='srs-progress'>¿Recuerdas qué significa esta palabra?</p>
                    <div class='srs-emoji'>{emoji_card}</div>
                    <p class='srs-word'>{word}</p>
                </div>
            """, unsafe_allow_html=True)

            col_s1, col_s2 = st.columns([1, 1])
            with col_s1:
                if st.button("🔊 Escuchar", key=f"srs_listen_{idx}",
                             use_container_width=True, type="secondary"):
                    with st.spinner("Generando audio..."):
                        ab = generate_lesson_audio(word)
                    if ab:
                        st.audio(ab, format="audio/mp3", autoplay=True)
            with col_s2:
                if st.button("👁️ Mostrar respuesta", key=f"srs_reveal_{idx}",
                             use_container_width=True, type="primary"):
                    st.session_state.srs_revealed = True
                    st.rerun()
        else:
            st.markdown(f"""
                <div class='srs-card'>
                    <div class='srs-emoji'>{emoji_card}</div>
                    <p class='srs-word'>{word}</p>
                    <div class='srs-translation'>{translation}</div>
                    <p class='srs-progress'>¿Qué tan bien la recordabas?</p>
                </div>
            """, unsafe_allow_html=True)

            col_q1, col_q2, col_q3, col_q4 = st.columns(4)

            def _grade_card(quality: int):
                update_srs_card(user, word, quality)
                st.session_state.srs_attempted += 1
                if quality >= 2:
                    st.session_state.srs_correct += 1
                st.session_state.srs_index += 1
                st.session_state.srs_revealed = False
                if st.session_state.srs_index >= total:
                    st.session_state.srs_finished = True

            with col_q1:
                if st.button("😖 No la sabía", key=f"srs_q0_{idx}",
                             use_container_width=True, type="secondary"):
                    _grade_card(0); st.rerun()
            with col_q2:
                if st.button("😅 Difícil", key=f"srs_q1_{idx}",
                             use_container_width=True, type="secondary"):
                    _grade_card(1); st.rerun()
            with col_q3:
                if st.button("🙂 Bien", key=f"srs_q2_{idx}",
                             use_container_width=True, type="secondary"):
                    _grade_card(2); st.rerun()
            with col_q4:
                if st.button("🤩 Perfecto", key=f"srs_q3_{idx}",
                             use_container_width=True, type="primary"):
                    _grade_card(3); st.rerun()

        st.write("")
        if st.button("✕ Salir del repaso", key="srs_abandon",
                     type="secondary"):
            reset_to_worlds()
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 3) WORLD ENTRY PAGE ──────────────────────────────────────────
    if (st.session_state.selected_world is not None
            and not st.session_state.lesson_pending
            and st.session_state.quiz_data is None):

        wkey = st.session_state.selected_world
        wmeta = get_world_meta(wkey, user)
        wcolor = wmeta["accent"]

        # Inyectar accent del mundo en CSS variable global
        st.markdown(
            f"<style>:root, .stApp {{ --profile-accent: {wcolor}; }}</style>",
            unsafe_allow_html=True
        )

        # Hex → rgba helper inline
        def _hex_to_rgba(hex_str: str, alpha: float) -> str:
            h = hex_str.lstrip("#")
            if len(h) == 3:
                h = "".join(c*2 for c in h)
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r}, {g}, {b}, {alpha})"
        wglow = _hex_to_rgba(wcolor, 0.35)
        wsoft = _hex_to_rgba(wcolor, 0.18)

        st.markdown(
            f"<div class='world-hero' style='--world-accent: {wcolor};"
            f" --world-accent-soft: {wsoft}; --world-accent-glow: {wglow};'>"
            f"<p class='world-hero-breadcrumb'>"
            f"  Mapa de Mundos <b>›</b> <b>{wmeta['name']}</b>"
            f"</p>"
            f"<div class='world-hero-emoji'>{wmeta['emoji']}</div>"
            f"<h1 class='world-hero-title'>{wmeta['name']}</h1>"
            f"<p class='world-hero-tagline'>{wmeta['intro']}</p>"
            f"</div>",
            unsafe_allow_html=True
        )

        st.markdown(
            "<p class='worlds-section-title'>ELIGE TU MODO</p>",
            unsafe_allow_html=True
        )

        # ─── Catálogo completo de modos ───
        _ALL_MODES = {
            "flashcards": {
                "key": "flashcards", "icon": "🃏",
                "name": "Flashcards Visuales",
                "desc": "Mira el dibujo, escucha y elige la palabra correcta.",
                "btn": "Jugar Flashcards", "accent": "#ffd400",
            },
            "memory_match": {
                "key": "memory_match", "icon": "🧠",
                "name": "Memory Match",
                "desc": "Encuentra las parejas de palabra y dibujo escondidas.",
                "btn": "Jugar Memory", "accent": "#ff66c4",
            },
            "sentence_builder": {
                "key": "sentence_builder", "icon": "🧩",
                "name": "Constructor de Oraciones",
                "desc": "Toca las palabras en orden para formar la oración.",
                "btn": "Construir Oraciones", "accent": "#ffd400",
            },
            "story_fill": {
                "key": "story_fill", "icon": "📖",
                "name": "Cuento Personalizado",
                "desc": "Un cuento sobre ti con huecos. Elige la palabra correcta.",
                "btn": "Leer mi Cuento", "accent": "#ffd400",
            },
            "lesson_quiz": {
                "key": "lesson_quiz", "icon": "🎓",
                "name": "Lección + Quiz",
                "desc": "Explicación guiada + quiz a tu ritmo.",
                "btn": "Iniciar Lección", "accent": "#00eefc",
            },
            "battle": {
                "key": "battle", "icon": "⚔️",
                "name": "Modo Batalla",
                "desc": "Combate: 8 preguntas, HP limitado, aciertos en cadena.",
                "btn": "¡Combatir!", "accent": "#ff5351",
            },
            "pronunciation": {
                "key": "pronunciation", "icon": "🎤",
                "name": "Pronunciación",
                "desc": "Escucha 6 palabras y repítelas — la IA evalúa.",
                "btn": "Practicar", "accent": "#39ff14",
            },
            "conversation": {
                "key": "conversation", "icon": "💬",
                "name": "Conversación",
                "desc": "Charla libre en inglés con un personaje del mundo.",
                "btn": "Conversar", "accent": "#c464ff",
            },
        }

        # Modos exclusivos del Estudio de Sonido y Café Conversación
        _ALL_MODES["min_pairs"] = {
            "key": "min_pairs", "icon": "👯",
            "name": "Pares Mínimos",
            "desc": "ship/sheep, beach/peach — entrena el oído fino.",
            "btn": "Practicar Pares", "accent": "#ffd400",
        }
        _ALL_MODES["listen_id"] = {
            "key": "listen_id", "icon": "👂",
            "name": "¿Qué Escuché?",
            "desc": "Escucha una palabra y elige la correcta entre 4.",
            "btn": "Jugar", "accent": "#00eefc",
        }
        _ALL_MODES["roleplay"] = {
            "key": "roleplay", "icon": "🎭",
            "name": "Role-Play",
            "desc": "Elige un escenario real y completa misiones.",
            "btn": "Elegir Escenario", "accent": "#c464ff",
        }
        _ALL_MODES["translate_inv"] = {
            "key": "translate_inv", "icon": "✍️",
            "name": "Traducción Inversa",
            "desc": "Lee la oración en español y escríbela en inglés.",
            "btn": "Empezar a Traducir", "accent": "#ffd400",
        }
        _ALL_MODES["describe_scene"] = {
            "key": "describe_scene", "icon": "🎨",
            "name": "Describe la Escena",
            "desc": "Mira la escena y escribe lo que ves en inglés.",
            "btn": "Describir Escenas", "accent": "#ff66c4",
        }
        _ALL_MODES["shadow_speak"] = {
            "key": "shadow_speak", "icon": "🎵",
            "name": "Shadow Speaking",
            "desc": "Escucha una frase rítmica y repítela imitando el ritmo.",
            "btn": "Repetir Frases", "accent": "#39ff14",
        }
        _ALL_MODES["speaking_journal"] = {
            "key": "speaking_journal", "icon": "📔",
            "name": "Diario del Día",
            "desc": "Habla 30s sobre el tema del día. La IA te da feedback.",
            "btn": "Grabar Diario", "accent": "#00eefc",
        }

        # ─── Modos disponibles por mundo (cada mundo con su identidad propia) ───
        _MODES_BY_WORLD = {
            # Vocabulario: foco en palabras y reconocimiento visual
            "vocab":     ["flashcards", "memory_match", "lesson_quiz"],
            # Gramática: foco en construir estructuras y drill de reglas
            "grammar":   ["sentence_builder", "battle", "lesson_quiz"],
            # Mundo personal: foco en expresión personal y narrativa
            "personal":  ["story_fill", "lesson_quiz"],
            # Estudio de Sonido: escuchar + pronunciar (todas las mecánicas auditivas)
            "sound":     ["min_pairs", "listen_id", "shadow_speak", "pronunciation"],
            # Café Conversación: hablar / role-play
            "chat":      ["roleplay", "conversation"],
            # Taller de Letras: escritura productiva
            "writing":   ["translate_inv", "describe_scene"],
            # Diario Hablado: producción oral espontánea
            "journal":   ["speaking_journal"],
            # Desafío Sorpresa: foco en variedad y combate
            "challenge": ["battle", "lesson_quiz"],
        }
        # Mundo destacado (modo "primary") por defecto
        _FEATURED_BY_WORLD = {
            "vocab":     "flashcards",
            "grammar":   "sentence_builder",
            "personal":  "story_fill",
            "sound":     "min_pairs",
            "chat":      "roleplay",
            "writing":   "translate_inv",
            "journal":   "speaking_journal",
            "challenge": "battle",
        }

        # Construir la lista de modos para el mundo actual (fallback: todos)
        active_keys = _MODES_BY_WORLD.get(wkey, list(_ALL_MODES.keys()))
        modes = [_ALL_MODES[k] for k in active_keys if k in _ALL_MODES]
        featured_key = _FEATURED_BY_WORLD.get(wkey, "battle")

        # Grid 2 columnas, filas según cantidad de modos
        for row_start in range(0, len(modes), 2):
            mode_cols = st.columns(2)
            for j, m in enumerate(modes[row_start:row_start+2]):
                m_accent = m["accent"]
                m_icon   = m["icon"]
                m_name   = m["name"]
                m_desc   = m["desc"]
                with mode_cols[j]:
                    st.markdown(
                        f"<div class='mode-card' style='--mode-accent: {m_accent};'>"
                        f"<div class='mode-icon'>{m_icon}</div>"
                        f"<p class='mode-name'>{m_name}</p>"
                        f"<p class='mode-desc'>{m_desc}</p>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    # El modo destacado del mundo es "primary"
                    is_featured = (m["key"] == featured_key)
                    if st.button(m["btn"], key=f"mode_{m['key']}",
                                 use_container_width=True,
                                 type="primary" if is_featured else "secondary"):
                        if m["key"] == "flashcards":
                            start_flashcards(wkey, wmeta["topic"])
                        elif m["key"] == "memory_match":
                            start_memory_match(wkey, wmeta["topic"])
                        elif m["key"] == "sentence_builder":
                            start_sentence_builder(wkey, wmeta["topic"])
                        elif m["key"] == "story_fill":
                            start_story_fill(wkey, wmeta["topic"])
                        elif m["key"] == "min_pairs":
                            start_minimal_pairs(wkey, wmeta["topic"])
                        elif m["key"] == "listen_id":
                            start_listen_id(wkey, wmeta["topic"])
                        elif m["key"] == "roleplay":
                            open_roleplay_picker(wkey)
                        elif m["key"] == "translate_inv":
                            start_translate_inverse(wkey, wmeta["topic"])
                        elif m["key"] == "describe_scene":
                            start_describe_scene(wkey, wmeta["topic"])
                        elif m["key"] == "shadow_speak":
                            start_shadow_speaking(wkey, wmeta["topic"])
                        elif m["key"] == "speaking_journal":
                            start_speaking_journal(wkey, wmeta["topic"])
                        elif m["key"] == "pronunciation":
                            start_pronunciation(wkey, wmeta["topic"])
                        elif m["key"] == "conversation":
                            start_conversation(wkey)
                        else:
                            start_lesson(wmeta["topic"], world=wkey,
                                          lesson_type=m["key"])
                        st.rerun()

        st.write("")
        if st.button("← Volver al mapa de mundos", key="world_back",
                     type="secondary"):
            st.session_state.selected_world = None
            st.rerun()

        send_weekly_report()
        st.stop()

    # ── 4) Mapa de mundos por defecto ──────────────────────────────
    # Solo se renderiza cuando no hay lección/quiz/result en curso.
    # Si hay lección activa, saltamos el grid y vamos directo a su render.
    in_lesson_flow = (
        st.session_state.quiz_data is not None
        or st.session_state.quiz_result is not None
        or st.session_state.lesson_pending
        or st.session_state.fc_cards is not None
        or st.session_state.sb_sentences is not None
        or st.session_state.mm_pairs is not None
        or st.session_state.sf_story is not None
        or st.session_state.mp_pairs is not None
        or st.session_state.li_cards is not None
        or st.session_state.rp_picker
        or st.session_state.ti_items is not None
        or st.session_state.ds_scenes is not None
        or st.session_state.conv_show_end
        or st.session_state.ss_phrases is not None
        or st.session_state.ex_questions is not None
        or st.session_state.dh_prompt is not None
    )

    if not in_lesson_flow:
        # ───── REFUERZO POR ERRORES RECURRENTES ─────
        err_topic = st.session_state.get("last_error_topic")
        err_dismissed = st.session_state.get("error_dismissed", False)
        if err_topic and not err_dismissed and err_topic.get("pattern"):
            examples_html = "".join(
                f"<li>{e}</li>" for e in (err_topic.get("examples") or [])
            )
            st.markdown(
                f"<div class='reinforce-card'>"
                f"<p class='reinforce-title'>📚 REPASO RÁPIDO — TU PUNTO DÉBIL</p>"
                f"<p class='reinforce-pattern'>🎯 {err_topic['pattern']}</p>"
                f"<p class='reinforce-hint'>{err_topic.get('hint', '')}</p>"
                f"<ul class='reinforce-examples'>{examples_html}</ul>"
                f"</div>",
                unsafe_allow_html=True
            )
            col_rf1, col_rf2 = st.columns([3, 1])
            with col_rf1:
                st.caption("Estas oraciones modelan el patrón correcto — léelas en voz alta.")
            with col_rf2:
                if st.button("✓ Entendido", key="dismiss_error",
                             use_container_width=True, type="secondary"):
                    st.session_state.error_dismissed = True
                    st.rerun()

        # ───── MISIÓN DEL DÍA + RECOMENDACIÓN + RACHA ─────
        streak     = get_streak_days(user)
        today_n    = get_today_session_count(user)
        weakest, w_meta = get_weakest_skill(user)
        streak_emoji = "🔥" if streak >= 3 else "✨" if streak >= 1 else "💤"
        if today_n == 0:
            mission_status = "¡Empieza tu primera misión del día!"
            mission_state = "pending"
        elif today_n == 1:
            mission_status = "Genial. Una más para asegurar la racha."
            mission_state = "started"
        else:
            mission_status = "¡Misión cumplida hoy! Sigue acumulando."
            mission_state = "done"

        st.markdown(
            f"<div class='daily-card daily-{mission_state}'>"
            f"<div class='daily-top'>"
            f"<div class='daily-streak'>"
            f"<span class='daily-streak-num'>{streak_emoji} {streak}</span>"
            f"<span class='daily-streak-lbl'>días seguidos</span>"
            f"</div>"
            f"<div class='daily-today'>"
            f"<span class='daily-today-num'>{today_n}</span>"
            f"<span class='daily-today-lbl'>actividades hoy</span>"
            f"</div>"
            f"</div>"
            f"<p class='daily-status'>{mission_status}</p>"
            f"<p class='daily-rec'>🎯 <b>Hoy te recomiendo:</b> "
            f"<span class='daily-rec-world'>{w_meta['emoji']} {w_meta['name']}</span> "
            f"<span class='daily-rec-why'>(es tu habilidad con menos práctica)</span></p>"
            f"</div>",
            unsafe_allow_html=True
        )

        col_dm1, col_dm2 = st.columns(2)
        with col_dm1:
            if st.button(f"⚡ Ir al mundo recomendado",
                         key="goto_recommended",
                         use_container_width=True, type="primary"):
                st.session_state.selected_world = w_meta["key"]
                st.rerun()
        with col_dm2:
            if st.button("📝 Examen semanal (+50-150 XP)",
                         key="start_exam_btn",
                         use_container_width=True, type="secondary"):
                start_exam(user)
                st.rerun()

        # ───── CÁPSULA CULTURAL DEL DÍA ─────
        capsule = get_cultural_capsule_for_today()
        st.markdown(
            f"<div class='culture-card'>"
            f"<p class='culture-title'>💎 CÁPSULA CULTURAL DEL DÍA</p>"
            f"<div class='culture-row'>"
            f"<p class='culture-row-label'>🗯 IDIOM</p>"
            f"<p class='culture-row-en'>“{capsule['idiom']['en']}”</p>"
            f"<p class='culture-row-es'>🇪🇸 {capsule['idiom']['es']}</p>"
            f"</div>"
            f"<div class='culture-row'>"
            f"<p class='culture-row-label'>🎵 SONG LINE</p>"
            f"<p class='culture-row-en'>“{capsule['song']['line']}”</p>"
            f"<p class='culture-row-es'>🎤 {capsule['song']['song']}</p>"
            f"</div>"
            f"<div class='culture-row'>"
            f"<p class='culture-row-label'>📌 ¿SABÍAS QUÉ?</p>"
            f"<p class='culture-row-en'>{capsule['fact']['en']}</p>"
            f"<p class='culture-row-es'>🇪🇸 {capsule['fact']['es']}</p>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True
        )

        # SRS hero card: muestra si hay cards pendientes de repaso
        due_count = get_due_srs_count(user)
        if due_count > 0:
            st.markdown(
                f"<div class='srs-hero'>"
                f"<div class='srs-hero-icon'>🧠</div>"
                f"<div class='srs-hero-info'>"
                f"<p class='srs-hero-title'>Repaso Inteligente</p>"
                f"<p class='srs-hero-sub'>Tienes palabras esperando a que las recuerdes</p>"
                f"</div>"
                f"<div class='srs-hero-badge'>{due_count} 🌱</div>"
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button(f"🧠 Repasar {due_count} palabra{'s' if due_count != 1 else ''}",
                         key="srs_start_btn",
                         use_container_width=True, type="primary"):
                start_srs_review(user)
                st.rerun()

        st.markdown(
            "<p class='worlds-section-title'>MAPA DE MUNDOS</p>",
            unsafe_allow_html=True
        )

        # ── Mundos disponibles para esta sesión ──
        personal_world = PERSONAL_WORLDS.get(user, {
            "emoji": "⭐", "name": "Mi Mundo", "tagline": "Personalizado para ti",
            "topic": "Vocabulario práctico de la vida diaria"
        })

        worlds = [
            {
                "key":     "grammar",
                "emoji":   "🌌",
                "name":    "Galaxia Gramatical",
                "tagline": "Reglas, estructuras y patrones del inglés",
                "accent":  "#c464ff",
                "topic":   "Aventura Diaria (Reglas gramaticales divertidas y estructuradas)",
                "btn":     "Iniciar Misión",
            },
            {
                "key":     "vocab",
                "emoji":   "📚",
                "name":    "Bóveda de Vocabulario",
                "tagline": "Palabras nuevas, adjetivos, objetos cotidianos",
                "accent":  "#00eefc",
                "topic":   ("Vocabulario Práctico (Aprender palabras nuevas, adjetivos, "
                            "objetos de la casa, direcciones como arriba/abajo o verbos de "
                            "acción simple. PROHIBIDO usar gramática compleja o densa, "
                            "enfócate 100% en ampliar su vocabulario y mostrar el "
                            "significado de las palabras)"),
                "btn":     "Iniciar Misión",
            },
            {
                "key":     "personal",
                "emoji":   personal_world["emoji"],
                "name":    personal_world["name"],
                "tagline": personal_world["tagline"],
                "accent":  color,
                "topic":   personal_world["topic"],
                "btn":     "Entrar a mi mundo",
            },
            {
                "key":     "sound",
                "emoji":   "🎙",
                "name":    "Estudio de Sonido",
                "tagline": "Escucha, distingue y pronuncia",
                "accent":  "#39ff14",
                "topic":   ("Pronunciación y comprensión auditiva del inglés."),
                "btn":     "Entrar al Estudio",
            },
            {
                "key":     "chat",
                "emoji":   "💬",
                "name":    "Café Conversación",
                "tagline": "Misiones de role-play en inglés",
                "accent":  "#c464ff",
                "topic":   ("Conversación práctica en situaciones cotidianas."),
                "btn":     "Entrar al Café",
            },
            {
                "key":     "writing",
                "emoji":   "🖋",
                "name":    "Taller de Letras",
                "tagline": "Traduce y describe en inglés",
                "accent":  "#ff66c4",
                "topic":   ("Escritura productiva: traducir y describir escenas."),
                "btn":     "Entrar al Taller",
            },
            {
                "key":     "journal",
                "emoji":   "📔",
                "name":    "Diario Hablado",
                "tagline": "Habla 30s sobre el prompt del día",
                "accent":  "#00eefc",
                "topic":   "Producción oral espontánea diaria.",
                "btn":     "Grabar mi diario",
            },
            {
                "key":     "challenge",
                "emoji":   "⚔️",
                "name":    "Desafío Sorpresa",
                "tagline": "La IA elige el reto perfecto para hoy",
                "accent":  "#ff5351",
                "topic":   ("Reto Sorpresa: la IA elige libremente entre gramática avanzada, "
                            "vocabulario temático, expresiones idiomáticas o phrasal verbs. "
                            "Debe ser un tema que sorprenda, sea desafiante pero alcanzable, "
                            "y conectado con la edad e intereses del/la alumno/a."),
                "btn":     "Aceptar Desafío",
            },
        ]

        # Grid 2x2 de mundos (filas dinámicas según cantidad de mundos)
        for row_start in range(0, len(worlds), 2):
            cols = st.columns(2)
            for j, w in enumerate(worlds[row_start:row_start+2]):
                with cols[j]:
                    st.markdown(
                        f"<div class='world-card' style='--world-accent: {w['accent']};'>"
                        f"  <div class='world-card-header'>"
                        f"    <div class='world-icon'>{w['emoji']}</div>"
                        f"    <div>"
                        f"      <p class='world-name'>{w['name']}</p>"
                        f"      <p class='world-tagline'>{w['tagline']}</p>"
                        f"    </div>"
                        f"  </div>",
                        unsafe_allow_html=True
                    )
                    if st.button(w["btn"], key=f"world_{w['key']}",
                                 use_container_width=True, type="secondary"):
                        st.session_state.selected_world = w["key"]
                        st.session_state.view = "home"
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        # ── Voice Comm Panel (audio + texto libre) ──
        st.markdown(
            "<div class='voice-comm'>"
            "<p class='voice-comm-title'>📡 Misión Personalizada</p>"
            "<p class='voice-comm-sub'>Habla o escribe el tema que estás viendo en el colegio:</p>"
            "</div>",
            unsafe_allow_html=True
        )

        col_v1, col_v2 = st.columns([1, 3])
        with col_v1:
            audio_bytes = audio_recorder(
                text="Hablar", recording_color="#ff5351",
                neutral_color=color, icon_size="2x"
            )
        with col_v2:
            if audio_bytes and not st.session_state.lesson_pending:
                with st.spinner("Escuchando tu voz... 🎙️"):
                    text, t_error = transcribe_audio(audio_bytes)
                if t_error:
                    show_error(t_error)
                elif text:
                    st.success(f"Te escuché decir: *'{text}'*")
                    start_lesson("Tema del Colegio", text, world="voice")

        text_input = st.chat_input(f"Escribe tu tema personalizado aquí, {user}...")
        if (text_input
                and text_input != st.session_state.last_text_input
                and not st.session_state.lesson_pending):
            st.session_state.last_text_input = text_input
            start_lesson("Tema del Colegio", text_input, world="custom")

    # --- GENERAR LECCIÓN ---
    if st.session_state.lesson_pending:
        topic       = st.session_state.get("lesson_topic", "Aventura Diaria")
        custom_text = st.session_state.get("lesson_text", None)
        is_battle   = st.session_state.get("current_lesson_type", "") == "battle"

        # Calcular nivel CEFR estimado para adaptar la complejidad
        my_lb_entry = next(
            (e for e in get_leaderboard() if e["profile"] == user),
            {"total_xp": 0}
        )
        cefr_info_now = get_cefr_info(my_lb_entry["total_xp"])

        spinner_text = ("⚔️ Cargando arena de combate..."
                        if is_battle
                        else "✨ Preparando tu lección y quiz... (~10 segundos)")
        # Pasar info del mundo para personalizar la lección (persona, ambientación)
        _current_world_key = st.session_state.get("current_world", "")
        _current_world_meta = get_world_meta(_current_world_key, user) if _current_world_key else {}
        with st.spinner(spinner_text):
            data_parsed, error = generate_lesson_and_quiz(
                user, topic, custom_text,
                cefr_code=cefr_info_now["code"],
                cefr_name=cefr_info_now["name"],
                world_key=_current_world_key,
                world_name=_current_world_meta.get("name", ""),
                world_tagline=_current_world_meta.get("tagline", "")
            )

        st.session_state.lesson_error   = error
        st.session_state.lesson_pending = False
        st.session_state.lesson_text    = None

        if data_parsed and is_battle:
            # En modo batalla: convertir el JSON a battle_questions y NO mostrar lesson
            st.session_state.battle_questions  = build_battle_questions(data_parsed)
            st.session_state.battle_finished   = False
            st.session_state.battle_index      = 0
            st.session_state.battle_hp         = st.session_state.battle_max_hp
            st.session_state.battle_streak     = 0
            st.session_state.battle_max_streak = 0
            st.session_state.battle_correct    = 0
            st.session_state.battle_total      = 0
            st.session_state.battle_history    = []
            st.session_state.battle_feedback   = None
            st.session_state.quiz_data         = None
            st.rerun()
        else:
            # Flujo clásico (lesson + quiz)
            st.session_state.quiz_data = data_parsed

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

        # Re-inyectar accent del mundo activo para que lesson + quiz lo usen
        cur_world_key = st.session_state.get("current_world", "")
        if cur_world_key:
            cur_world_meta = get_world_meta(cur_world_key, user)
            cur_world_accent = cur_world_meta.get("accent", color)
            st.markdown(
                f"<style>:root, .stApp {{ --profile-accent: {cur_world_accent}; }}</style>",
                unsafe_allow_html=True
            )
            # Breadcrumb del mundo activo
            st.markdown(
                f"<p style='text-align:center; margin: 14px 0 6px; font-size: 0.78rem;"
                f" letter-spacing:2px; text-transform:uppercase; color:#6b7280;'>"
                f"<span style='color:{cur_world_accent}; text-shadow:0 0 10px {cur_world_accent};'>"
                f"{cur_world_meta.get('emoji','⭐')} {cur_world_meta.get('name','Mundo')}</span>"
                f" &nbsp;›&nbsp; Lección activa</p>",
                unsafe_allow_html=True
            )

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
            f"<div class='lesson-container'>"
            f"{lesson_text}"
            f"</div>",
            unsafe_allow_html=True
        )

        st.write("")

        # --- QUIZ ---
        attempts_left = MAX_QUIZ_ATTEMPTS - st.session_state.quiz_attempts
        badge_class   = "attempts-badge-danger" if attempts_left <= 1 else "attempts-badge"

        st.markdown(
            f"<div class='quiz-container'>",
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
                # Normalizar la oración: reemplazar ___ por un span visual estilizado
                raw_sentence = q.get("sentence", "___")
                raw_sentence = re.sub(r"\*+_+\*+", "___", raw_sentence)
                raw_sentence = re.sub(r"_+", "___", raw_sentence)
                sentence_display = raw_sentence.replace(
                    "___", "<span class='battle-blank'>______</span>"
                )
                # Hint en español (traducción de la oración completa)
                hint_text = (q.get("hint") or "").strip()
                hint_html = (
                    f"<p class='battle-q-hint' style='margin: 6px 0 10px;'>"
                    f"💡 <i>{hint_text}</i></p>"
                    if hint_text else ""
                )
                st.markdown(
                    f"<div class='question-card'>"
                    f"<span class='q-badge'>Completar {i+1} de {len(fitb_qs)}</span>"
                    f"<p style='font-size:1.1rem; font-weight:600; margin: 6px 0 4px;'>{sentence_display}</p>"
                    f"{hint_html}",
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
            title_text   = "¡Misión Completada!"
            bar_color    = "#39ff14"
        elif attempts_exhausted:
            panel_class  = "result-blocked"
            emoji_result = "📖"
            title_text   = f"Límite de {MAX_QUIZ_ATTEMPTS} intentos alcanzado"
            bar_color    = "#ff5351"
        else:
            panel_class  = "result-fail"
            emoji_result = "💪"
            title_text   = "¡Casi! Inténtalo de nuevo"
            bar_color    = "#ffd400"

        st.write("---")
        st.markdown(f"""
            <div class='result-panel {panel_class}'>
                <h2>{emoji_result} {title_text}</h2>
                <div class='score-number'>{pct:.0%}</div>
                <p style='color:#a8acb3 !important; margin:0;'>
                    {correct} de {total} correctas &middot; Intento #{attempts} de {MAX_QUIZ_ATTEMPTS}
                </p>
                <div class='score-bar-wrap'>
                    <div class='score-bar-fill'
                         style='width:{pct*100:.1f}%; background:{bar_color}; color:{bar_color};'></div>
                </div>
                <p style='color:#6b7280 !important; font-size:0.82rem; letter-spacing:1px; text-transform:uppercase;'>
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
                # Auto-añadir vocabulario al mazo SRS antes de intentar el save
                added = 0
                if st.session_state.quiz_data:
                    lesson_md = st.session_state.quiz_data.get("lesson", "")
                    vocab_items = extract_vocab_from_lesson(lesson_md)
                    for v in vocab_items:
                        if add_srs_card(user, v["word"], v["translation"],
                                         v.get("emoji", "📝")):
                            added += 1

                vocab_msg = (
                    f" 📚 +{added} palabra{'s' if added != 1 else ''} al mazo de repaso."
                    if added > 0 else ""
                )
                queue_xp_save(
                    user, XP_PER_LESSON, pct, attempts,
                    world=st.session_state.get("current_world", ""),
                    skill="",
                    lesson_type=st.session_state.get("current_lesson_type", "lesson_quiz"),
                    success_msg=(
                        f"¡Increíble, {user}! Obtuviste {pct:.0%} y ganaste "
                        f"+{XP_PER_LESSON} XP. ¡Sigue así!" + vocab_msg
                    )
                )
                st.rerun()

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
