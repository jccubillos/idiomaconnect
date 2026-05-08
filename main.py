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
                               cefr_name: str = "Explorer") -> str:
    """System prompt que instruye al LLM a generar un JSON robusto.
    Adapta complejidad al nivel CEFR estimado del/la alumno/a."""
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

    return f"""
Eres un tutor de inglés experto, cariñoso y motivador, diseñado exclusivamente para {profile_name}, un/a {gender} de {age_desc}, cursando {grade}.
A {pronoun} le apasiona: {profile['hobbies']}.
Tu tono debe ser: {profile['tone']}.

NIVEL ESTIMADO DEL/LA ALUMNO/A: {cefr_code} ({cefr_name})
GUÍA DE COMPLEJIDAD ({cefr_code}): {complexity_guide}

Adapta vocabulario, gramática y longitud de oraciones a este nivel. Si subes la complejidad, hazlo gradualmente; nunca brinques 2 niveles de un solo tirón.

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
  La respuesta ("answer") debe ser UNA sola palabra en minúsculas sin puntuación ni tildes.
"""


def generate_lesson_and_quiz(profile_name: str, topic: str,
                              custom_text: str | None = None,
                              cefr_code: str = "A1",
                              cefr_name: str = "Explorer"):
    """Llama a Groq con JSON mode, adaptado al nivel CEFR del alumno."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    system_prompt = _build_system_prompt_json(profile_name, cefr_code, cefr_name)
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


def start_conversation(world_key: str):
    """Inicia el modo conversación con la IA."""
    st.session_state.current_world  = world_key
    st.session_state.current_lesson_type = "conversation"
    st.session_state.conv_active     = True
    st.session_state.conv_history    = []
    st.session_state.conv_turn_count = 0
    st.session_state.conv_pending_user_input = ""
    st.session_state.selected_world  = None
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

def _build_conversation_system_prompt(profile_name: str, world_meta: dict,
                                       cefr_code: str = "A1") -> str:
    """System prompt para modo conversación. La IA actúa como personaje
    temático del mundo y conversa en inglés al nivel CEFR de la alumna/o."""
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
4. If the student makes a grammar mistake, gently correct it BEFORE your main reply, like: "(Quick fix: 'I am' not 'I be') Now, ..."
5. Stay in character with the world's theme: {world_meta.get('tagline','')}
6. Be encouraging, never harsh. This is a teen learning English.
7. NEVER give a paragraph longer than 4 lines.
8. Respond in plain text, no markdown headers.

START: Greet {profile_name} in English warmly and ask an opening question related to your world's theme.
"""


def conversation_send(profile_name: str, world_meta: dict,
                       cefr_code: str, history: list) -> tuple:
    """Envía la conversación a Groq y devuelve (response_text, error)."""
    groq_client, init_error = init_groq_client()
    if init_error or not groq_client:
        return None, f"⚠️ {init_error}"

    system_prompt = _build_conversation_system_prompt(
        profile_name, world_meta, cefr_code
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
        questions.append({
            "type":    "fitb",
            "q":       q.get("sentence", ""),
            "options": [],
            "answer":  q.get("answer", ""),
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
    # VISTA: HOME (puede mostrar: world entry, battle, lesson+quiz, o worlds grid)
    # ════════════════════════════════════════════════════════════════

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
                st.rerun()

        # Si no hay feedback pendiente y aún quedan preguntas, mostrar la actual
        elif b_idx < b_total and b_hp > 0:
            q = b_questions[b_idx]
            q_type_label = "Multiple Choice" if q["type"] == "mc" else "Fill the Blank"
            q_text = q["q"]
            if q["type"] == "fitb":
                q_text = q_text.replace("___", "**___**")

            st.markdown(
                f"<div class='battle-question'>"
                f"<div class='battle-q-meta'>"
                f"  <span class='battle-q-num'>► Pregunta {b_idx + 1}</span>"
                f"  <span class='battle-q-type'>{q_type_label}</span>"
                f"</div>"
                f"<div class='battle-q-text'>{q_text}</div>"
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
                st.session_state.xp += xp_award
                world_key = st.session_state.get("current_world", "")
                saved, save_error = save_xp_to_sheet(
                    user, xp_award, score_pct, attempts=1,
                    world=world_key, lesson_type="battle"
                )
                if not saved:
                    show_warning(f"XP guardado localmente, pero no en la nube: {save_error}")
                if victory:
                    st.balloons()
                    st.success(f"¡Increíble batalla, {user}! +{xp_award} XP en tu cuenta.")
                else:
                    st.info(f"Buen intento. Recibes {xp_award} XP de consolación.")
                reset_to_worlds()
                st.rerun()
        with col_b2:
            if st.button("🏠 Volver al mapa",
                         use_container_width=True, type="secondary",
                         key="battle_back"):
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
                    st.session_state.xp += xp_award
                    saved, _ = save_xp_to_sheet(
                        user, xp_award, avg_score / 100.0, attempts=1,
                        world=st.session_state.get("current_world", ""),
                        skill="pronunciation",
                        lesson_type="pronunciation"
                    )
                    if saved:
                        st.success(f"¡Buena pronunciación, {user}! +{xp_award} XP.")
                    reset_to_worlds()
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

        # Header
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
                    [{"role": "user", "content": "(Start the conversation)"}]
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
            # Separar gloss en español
            if "🇪🇸:" in content:
                main_part, _, gloss_part = content.partition("🇪🇸:")
                gloss_html = f"<span class='gloss'>🇪🇸: {gloss_part.strip()}</span>"
            else:
                main_part = content
                gloss_html = ""

            speaker = "TUTOR" if m["role"] == "assistant" else user.upper()
            klass = "assistant" if m["role"] == "assistant" else "user"
            st.markdown(
                f"<div class='conv-bubble {klass}'>"
                f"<div class='speaker'>{speaker}</div>"
                f"{main_part.strip()}{gloss_html}"
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
                    user, conv_world_meta, cefr_now, history
                )
            if err2:
                show_error(err2)
            elif ai_msg:
                history.append({"role": "assistant", "content": ai_msg})
                st.session_state.conv_history = history
                st.session_state.conv_turn_count += 1
                st.rerun()

        # Botones finalizar
        st.write("")
        col_e1, col_e2 = st.columns(2)
        turn_count = st.session_state.conv_turn_count
        # Mínimo 3 turnos del usuario para reclamar XP
        can_claim = turn_count >= 3

        with col_e1:
            if st.button(
                f"🏁 Terminar y reclamar XP ({turn_count}/3+)" if not can_claim else "🏁 Terminar y reclamar XP",
                key="conv_finish",
                use_container_width=True,
                type="primary",
                disabled=not can_claim
            ):
                xp_award = min(60, 20 + turn_count * 5)
                st.session_state.xp += xp_award
                saved, _ = save_xp_to_sheet(
                    user, xp_award, 1.0, attempts=1,
                    world=st.session_state.get("current_world", ""),
                    skill="conversation",
                    lesson_type="conversation"
                )
                if saved:
                    st.success(f"¡Gran conversación, {user}! +{xp_award} XP.")
                reset_to_worlds()
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
                st.session_state.xp += xp_award
                saved, _ = save_xp_to_sheet(
                    user, xp_award, pct, attempts=1,
                    world="srs", skill="vocabulary",
                    lesson_type="srs_review"
                )
                if saved:
                    st.success(f"¡Excelente memoria, {user}! +{xp_award} XP.")
                reset_to_worlds()
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

        # 4 modos en grid 2x2: Lección, Batalla, Pronunciación, Conversación
        modes = [
            {
                "key":    "lesson_quiz",
                "icon":   "🧠",
                "name":   "Lección + Quiz",
                "desc":   "Explicación guiada + quiz a tu ritmo.",
                "btn":    "Iniciar Lección",
                "accent": "#00eefc",
            },
            {
                "key":    "battle",
                "icon":   "⚔️",
                "name":   "Modo Batalla",
                "desc":   "Combate: 8 preguntas, HP limitado, aciertos en cadena.",
                "btn":    "¡Combatir!",
                "accent": "#ff5351",
            },
            {
                "key":    "pronunciation",
                "icon":   "🎤",
                "name":   "Pronunciación",
                "desc":   "Escucha 6 palabras del mundo y repítelas — la IA evalúa.",
                "btn":    "Practicar",
                "accent": "#39ff14",
            },
            {
                "key":    "conversation",
                "icon":   "💬",
                "name":   "Conversación",
                "desc":   "Charla libre en inglés con un personaje del mundo.",
                "btn":    "Conversar",
                "accent": "#c464ff",
            },
        ]

        # Grid 2x2
        for row_start in (0, 2):
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
                    if st.button(m["btn"], key=f"mode_{m['key']}",
                                 use_container_width=True,
                                 type="primary" if m["key"] == "battle" else "secondary"):
                        if m["key"] == "pronunciation":
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
    )

    if not in_lesson_flow:
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
        with st.spinner(spinner_text):
            data_parsed, error = generate_lesson_and_quiz(
                user, topic, custom_text,
                cefr_code=cefr_info_now["code"],
                cefr_name=cefr_info_now["name"]
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

                # Auto-añadir vocabulario de la lección al mazo SRS
                if st.session_state.quiz_data:
                    lesson_md = st.session_state.quiz_data.get("lesson", "")
                    vocab_items = extract_vocab_from_lesson(lesson_md)
                    added = 0
                    for v in vocab_items:
                        if add_srs_card(user, v["word"], v["translation"], v.get("emoji", "📝")):
                            added += 1
                    if added > 0:
                        st.info(f"📚 +{added} palabra{'s' if added != 1 else ''} agregada{'s' if added != 1 else ''} a tu mazo de repaso.")

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
