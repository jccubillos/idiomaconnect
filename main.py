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
        padding: 1px; pointer-events: none;
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
    }
    .profile-card h2 {
        margin: 4px 0 2px;
        font-size: 1.25rem; font-weight: 800;
        color: var(--profile-accent, #ffb3ae) !important;
        text-shadow: 0 0 12px var(--profile-accent, #ff5351);
    }
    .profile-card p {
        margin: 0; font-size: 0.78rem;
        color: var(--text-secondary) !important;
        text-transform: uppercase; letter-spacing: 1px;
        font-weight: 600;
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
- Si el tema es vocabulario: incluye una lista con guiones (-) con la palabra en inglés, su pronunciación aproximada entre corchetes [pro-nun-cia-ción] y su significado en español. NUNCA uses tablas con pipes (|).
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


def save_xp_to_sheet(profile_name: str, xp_gained: int, score_pct: float, attempts: int,
                      world: str = "", skill: str = "", lesson_type: str = ""):
    """
    Registra una sesion completada en Google Sheets.
    Columnas: Timestamp | profile | xp | score_pct | attempts
              | world | skill | lesson_type | streak_date | trophies
    """
    sheet, db_error = get_db_connection()
    if db_error or not sheet:
        logger.warning(f"No se pudo guardar XP: {db_error}")
        return False, db_error
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
        return True, None
    except Exception as e:
        logger.error(f"Error guardando en Sheets: {e}")
        return False, f"Error de Google Sheets: {e}"


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

    # Finalizar
    for a in agg.values():
        sessions = a["total_sessions"]
        a["avg_score"] = (a["score_sum"] / sessions) if sessions else 0.0
        a.pop("score_sum", None)
        a["active_days"] = len(a["active_days"])

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
    ("first_step",  "🚀", "Primer Vuelo",   "Completa tu primera misión",
     "#00eefc", lambda s: s["total_sessions"] >= 1),
    ("five_lessons","🔥", "Combo x5",       "Completa 5 misiones",
     "#ff5351", lambda s: s["total_sessions"] >= 5),
    ("ten_lessons", "⚡", "Combo x10",      "Completa 10 misiones",
     "#ffd400", lambda s: s["total_sessions"] >= 10),
    ("perfect",     "🎯", "Notón Perfecto", "Saca 100% en un quiz",
     "#39ff14", lambda s: s.get("perfect_count", 0) >= 1),
    ("xp_500",      "💎", "Club 500 XP",    "Acumula 500 XP",
     "#c464ff", lambda s: s["total_xp"] >= 500),
    ("xp_1000",     "🏆", "Club 1000 XP",   "Acumula 1000 XP",
     "#ffd400", lambda s: s["total_xp"] >= 1000),
    ("xp_2000",     "🌟", "Leyenda",        "Acumula 2000 XP",
     "#ff66c4", lambda s: s["total_xp"] >= 2000),
    ("active_5d",   "📅", "Disciplina",     "Activo en 5 días distintos",
     "#00eefc", lambda s: s.get("active_days", 0) >= 5),
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
    """Resetea el estado de quiz y dispara la generación de una nueva lección."""
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
    # Volver siempre a la vista Home cuando se inicia una lección
    st.session_state.view = "home"


# ==========================================
# 5. MANEJO DE ESTADO (Session State)
# ==========================================
_STATE_DEFAULTS = {
    "current_user":    None,
    "view":            "home",       # home | arena | profile
    "xp":              0,
    "quiz_data":       None,
    "lesson_error":    None,
    "lesson_pending":  False,
    "quiz_result":     None,
    "quiz_attempts":   0,
    "last_text_input": "",
    "lesson_audio":    None,   # bytes MP3 cacheados del audio de la lección
    "current_world":   "",     # mundo elegido para la lección actual
    "current_lesson_type": "", # tipo de lección (lesson_quiz, etc.)
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
            <h1>⚡ IdiomaConnect</h1>
            <p>Elige tu perfil de combate · Sistema de aprendizaje activado</p>
        </div>
    """, unsafe_allow_html=True)

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
            <span class='xp-display'>⚡ {st.session_state.xp} XP</span>
        </div>
    """, unsafe_allow_html=True)

    # --- PANEL DE PROGRESO ACUMULADO (desde Google Sheets) ---
    stats = get_user_stats(user)
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
    # VISTA: HOME (mapa de mundos + lección + quiz)
    # ════════════════════════════════════════════════════════════════
    st.markdown(
        "<p class='worlds-section-title'>MAPA DE MUNDOS</p>",
        unsafe_allow_html=True
    )

    # ── Mundos disponibles para esta sesión ────────────────────────────
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

    # Grid 2x2 de mundos
    for row_start in (0, 2):
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
                    start_lesson(w["topic"], world=w["key"])
                st.markdown("</div>", unsafe_allow_html=True)

    # ── Voice Comm Panel (audio + texto libre) ──────────────────────────
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
                st.session_state.xp += XP_PER_LESSON

                saved, save_error = save_xp_to_sheet(
                    user, XP_PER_LESSON, pct, attempts,
                    world=st.session_state.get("current_world", ""),
                    lesson_type=st.session_state.get("current_lesson_type", ""),
                )
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
