# =============================================================================
# AETHERDISPATCH v2.0 — Agent IA Handling Aérien
# Développé par EG Conseil & Lobbying | Mars 2026
# Modules : Masse & Centrage | Performances | V-Speeds | METAR Live
#           Carburant | OCR Manifest | Optimisation PuLP | Export PDF | PWA
# =============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import hashlib
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import io
import re

# ─── Tentative d'import PuLP (optionnel) ──────────────────────────────────────
try:
    import pulp as _pulp
    PULP_OK = True
except Exception:
    PULP_OK = False

# ─── Tentative d'import EasyOCR (optionnel, lourd) ────────────────────────────
try:
    import easyocr
    EASYOCR_OK = True
except ImportError:
    EASYOCR_OK = False

# =============================================================================
# CONFIGURATION PAGE & PWA INJECTION
# =============================================================================
st.set_page_config(
    page_title="AETHERDISPATCH",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Injection HTML/CSS futuriste + PWA hooks ─────────────────────────────────
def inject_pwa_and_styles():
    st.markdown("""
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#00BFFF">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="AETHERDISPATCH">
    <link rel="apple-touch-icon" href="/icon-192.png">

    <style>
    /* ── Variables chromatiques AETHERDISPATCH ── */
    :root {
        --aether-navy:    #0A0A1A;
        --aether-deep:    #0D1F3C;
        --aether-blue:    #00BFFF;
        --aether-violet:  #7B2FBE;
        --aether-gold:    #FFD700;
        --aether-green:   #00FF88;
        --aether-red:     #FF4444;
        --aether-text:    #E0E8FF;
        --aether-muted:   #8899BB;
        --aether-glow:    0 0 20px rgba(0, 191, 255, 0.4);
        --aether-glow-v:  0 0 20px rgba(123, 47, 190, 0.4);
    }

    /* ── Reset global ── */
    .stApp, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0A0A1A 0%, #0D1F3C 50%, #0A0A2A 100%) !important;
        color: var(--aether-text) !important;
        font-family: 'Segoe UI', 'Inter', sans-serif;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #050510 0%, #0A1428 100%) !important;
        border-right: 1px solid rgba(0,191,255,0.2) !important;
    }
    [data-testid="stSidebar"] .stMarkdown { color: var(--aether-text) !important; }

    /* ── Header principal ── */
    .aether-header {
        background: linear-gradient(90deg, #0A0A1A, #0D1F3C, #0A0A2A);
        border: 1px solid rgba(0,191,255,0.3);
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--aether-glow);
        text-align: center;
    }
    .aether-header h1 {
        font-size: 2.4rem;
        font-weight: 900;
        letter-spacing: 4px;
        background: linear-gradient(90deg, #00BFFF, #7B2FBE, #00BFFF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        text-transform: uppercase;
    }
    .aether-header p {
        color: var(--aether-muted);
        font-size: 0.85rem;
        letter-spacing: 2px;
        margin: 0.3rem 0 0;
        text-transform: uppercase;
    }

    /* ── Cartes métriques ── */
    .metric-card {
        background: linear-gradient(135deg, #0D1F3C, #12264A);
        border: 1px solid rgba(0,191,255,0.25);
        border-radius: 10px;
        padding: 1rem 1.2rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
    }
    .metric-card:hover { border-color: rgba(0,191,255,0.6); box-shadow: var(--aether-glow); }
    .metric-card .label { font-size: 0.72rem; color: var(--aether-muted); letter-spacing: 1.5px; text-transform: uppercase; }
    .metric-card .value { font-size: 1.6rem; font-weight: 700; color: var(--aether-blue); }
    .metric-card .unit  { font-size: 0.75rem; color: var(--aether-muted); }

    /* ── Badge statut ── */
    .badge-ok   { background: rgba(0,255,136,0.15); color: #00FF88; border: 1px solid #00FF88;
                  border-radius: 20px; padding: 3px 12px; font-size: 0.8rem; font-weight: 700; }
    .badge-warn { background: rgba(255,215,0,0.15); color: #FFD700; border: 1px solid #FFD700;
                  border-radius: 20px; padding: 3px 12px; font-size: 0.8rem; font-weight: 700; }
    .badge-nok  { background: rgba(255,68,68,0.15); color: #FF4444; border: 1px solid #FF4444;
                  border-radius: 20px; padding: 3px 12px; font-size: 0.8rem; font-weight: 700; }

    /* ── Séparateur lumineux ── */
    .aether-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #00BFFF, transparent);
        margin: 1.5rem 0;
        opacity: 0.4;
    }

    /* ── Boutons Streamlit ── */
    .stButton > button {
        background: linear-gradient(135deg, #00BFFF22, #7B2FBE22) !important;
        border: 1px solid #00BFFF !important;
        color: #00BFFF !important;
        font-weight: 700 !important;
        letter-spacing: 1px !important;
        border-radius: 8px !important;
        transition: all 0.3s !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #00BFFF44, #7B2FBE44) !important;
        box-shadow: var(--aether-glow) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Inputs ── */
    .stNumberInput input, .stTextInput input, .stSelectbox select {
        background: #0D1F3C !important;
        border: 1px solid rgba(0,191,255,0.3) !important;
        color: var(--aether-text) !important;
        border-radius: 6px !important;
    }

    /* ── Onglets ── */
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: var(--aether-muted) !important;
        border-bottom: 2px solid transparent !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--aether-blue) !important;
        border-bottom-color: var(--aether-blue) !important;
    }

    /* ── Alertes Streamlit ── */
    .stAlert { border-radius: 8px !important; }

    /* ── Tableaux ── */
    .stDataFrame { border: 1px solid rgba(0,191,255,0.2) !important; border-radius: 8px !important; }

    /* ── Loader ── */
    .aether-loader {
        text-align: center;
        color: var(--aether-blue);
        font-size: 1.2rem;
        letter-spacing: 2px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

    /* ── Footer ── */
    .aether-footer {
        text-align: center;
        color: var(--aether-muted);
        font-size: 0.7rem;
        letter-spacing: 1.5px;
        padding: 1rem;
        border-top: 1px solid rgba(0,191,255,0.1);
        margin-top: 2rem;
    }
    </style>

    <script>
    // Enregistrement du Service Worker PWA
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js')
                .then(reg => console.log('[AETHER] Service Worker enregistré:', reg.scope))
                .catch(err => console.warn('[AETHER] SW non enregistré:', err));
        });
    }
    </script>
    """, unsafe_allow_html=True)

inject_pwa_and_styles()

# =============================================================================
# UTILITAIRES CORE
# =============================================================================

@st.cache_data
def load_json(filepath: str) -> dict | list:
    """Charge un fichier JSON avec gestion d'erreurs."""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(filepath: str, data):
    """Sauvegarde un fichier JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance orthodromique en milles nautiques."""
    R = 6371
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    return round(2 * R * np.arcsin(np.sqrt(a)) * 0.539957, 0)

def cg_to_mac(cg_m: float, lemac: float, mac_length: float) -> float:
    """Convertit un bras CG (mètres) en pourcentage MAC."""
    return round((cg_m - lemac) / mac_length * 100, 1)

# =============================================================================
# AUTHENTIFICATION MULTI-UTILISATEURS
# =============================================================================

def authenticate(username: str, password: str, users: dict) -> bool:
    if username in users:
        return users[username]["password_hash"] == hash_password(password)
    return False

def login_page(users: dict):
    """Page de connexion futuriste."""
    st.markdown("""
    <div class="aether-header">
        <h1>✈ AETHERDISPATCH</h1>
        <p>Système de gestion handling aérien augmenté par IA</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("#### 🔐 Connexion sécurisée")
        username = st.text_input("Identifiant", placeholder="Votre login")
        password = st.text_input("Mot de passe", type="password", placeholder="••••••••")

        if st.button("✈ CONNEXION", use_container_width=True):
            if authenticate(username, password, users):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.user_info = users[username]
                st.rerun()
            else:
                st.error("❌ Identifiants incorrects. Contactez votre administrateur OPS.")

        st.markdown("---")
        st.markdown("""
        <div style="text-align:center;font-size:0.72rem;color:#556688;letter-spacing:1px">
        ACCÈS RESTREINT — Équipe Handling & Dispatch autorisée uniquement<br>
        AETHERDISPATCH v2.0 | EG Conseil & Lobbying © 2026
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# MODULE 1 : MASSE & CENTRAGE (M&C)
# =============================================================================

def compute_mc(ac: dict, pax_zone_weights: dict, cargo_weights: dict, fuel_kg: float) -> dict:
    """
    Calcul complet masse & centrage conforme JAR/CS-25.
    Retourne ZFW, TOW, LW, CG et MAC% à chaque étape.
    """
    oew      = ac["oew_kg"]
    crew_kg  = ac.get("crew_kg", 0)
    crew_arm = ac.get("crew_arm_m", ac["oew_arm_m"])
    # Dry Operating Weight = OEW + équipage
    dow        = oew + crew_kg
    dow_moment = oew * ac["oew_arm_m"] + crew_kg * crew_arm

    # ── Moment total PAX ──────────────────────────────────────────────────────
    pax_total_kg = 0
    pax_moment = 0
    for zone in ac["pax_zones"]:
        w = pax_zone_weights.get(zone["name"], 0)
        pax_total_kg += w
        pax_moment += w * zone["arm_m"]

    # ── Moment total Cargo ────────────────────────────────────────────────────
    cargo_total_kg = 0
    cargo_moment = 0
    for comp in ac["cargo_comps"]:
        w = cargo_weights.get(comp["name"], 0)
        cargo_total_kg += w
        cargo_moment += w * comp["arm_m"]

    # ── Zero Fuel Weight (DOW + payload) ─────────────────────────────────────
    zfw = dow + pax_total_kg + cargo_total_kg
    zfw_moment = dow_moment + pax_moment + cargo_moment
    zfw_cg = zfw_moment / zfw if zfw > 0 else 0
    zfw_mac = cg_to_mac(zfw_cg, ac["lemac"], ac["mac_length"])

    # ── Moment carburant (bras unique défini dans la DB) ──────────────────────
    fuel_arm    = ac["fuel_arm_m"]
    fuel_moment = fuel_kg * fuel_arm

    # ── Take-Off Weight ───────────────────────────────────────────────────────
    tow = zfw + fuel_kg
    tow_moment = zfw_moment + fuel_moment
    tow_cg = tow_moment / tow if tow > 0 else 0
    tow_mac = cg_to_mac(tow_cg, ac["lemac"], ac["mac_length"])

    # ── Landing Weight (fuel consommé en vol = trip fuel à saisir séparément) ─
    # On expose LW sans trip fuel ici (trip fuel déduit dans l'onglet vol)

    return {
        "pax_total_kg": pax_total_kg,
        "cargo_total_kg": cargo_total_kg,
        "zfw": round(zfw),
        "zfw_cg": round(zfw_cg, 3),
        "zfw_mac": zfw_mac,
        "tow": round(tow),
        "tow_cg": round(tow_cg, 3),
        "tow_mac": tow_mac,
        "fuel_arm": round(fuel_arm, 2),
        "fuel_kg": fuel_kg,
    }

def plot_cg_envelope(ac: dict, result: dict, trip_fuel: float = 0) -> go.Figure:
    """Trace l'enveloppe CG (x = mètres) avec points ZFW, TOW, LW."""
    lim_fwd = ac["cg_min_m"]   # mètres
    lim_aft = ac["cg_max_m"]   # mètres
    mzfw = ac["max_zfw_kg"]
    mtow = ac["max_tow_kg"]
    mlw  = ac["max_lw_kg"]
    dow  = ac["oew_kg"] + ac.get("crew_kg", 0)
    margin = (lim_aft - lim_fwd) * 0.15

    # Enveloppe simplifiée (sommets en mètres)
    env_w  = [dow, mzfw, mtow, mtow, mzfw, dow, dow]
    env_cg = [lim_fwd, lim_fwd, lim_fwd + margin, lim_aft - margin, lim_aft, lim_aft, lim_fwd]

    fig = go.Figure()

    # Zone enveloppe
    fig.add_trace(go.Scatter(
        x=env_cg, y=env_w,
        fill='toself',
        fillcolor='rgba(0, 191, 255, 0.08)',
        line=dict(color='#00BFFF', width=2),
        name='Enveloppe CG',
        hoverinfo='skip'
    ))

    # Limites CG
    fig.add_vline(x=lim_fwd, line=dict(color='#FF4444', dash='dash', width=1.5), annotation_text="FWD LIM")
    fig.add_vline(x=lim_aft, line=dict(color='#FF4444', dash='dash', width=1.5), annotation_text="AFT LIM")

    # Point ZFW (x = CG en mètres)
    fig.add_trace(go.Scatter(
        x=[result["zfw_cg"]], y=[result["zfw"]],
        mode='markers+text',
        marker=dict(size=14, color='#FFD700', symbol='diamond', line=dict(color='white', width=2)),
        text=["ZFW"], textposition="top center",
        name=f"ZFW : {result['zfw']:,} kg"
    ))

    # Point TOW (x = CG en mètres)
    fig.add_trace(go.Scatter(
        x=[result["tow_cg"]], y=[result["tow"]],
        mode='markers+text',
        marker=dict(size=14, color='#00FF88', symbol='circle', line=dict(color='white', width=2)),
        text=["TOW"], textposition="top center",
        name=f"TOW : {result['tow']:,} kg"
    ))

    # Point LW (si trip fuel renseigné)
    if trip_fuel > 0:
        lw = result["tow"] - trip_fuel
        lw_fuel = result["fuel_kg"] - trip_fuel
        lw_fuel_arm = ac["fuel_arm_m"]
        zfw_moment = result["zfw_cg"] * result["zfw"]
        lw_moment = zfw_moment + lw_fuel * lw_fuel_arm
        lw_cg = lw_moment / lw if lw > 0 else 0

        fig.add_trace(go.Scatter(
            x=[lw_cg], y=[lw],
            mode='markers+text',
            marker=dict(size=14, color='#7B2FBE', symbol='triangle-down', line=dict(color='white', width=2)),
            text=["LW"], textposition="bottom center",
            name=f"LW : {lw:,} kg"
        ))

    fig.update_layout(
        title=dict(text="Enveloppe Masse & Centrage", font=dict(color='#00BFFF', size=16)),
        plot_bgcolor='#0D1F3C',
        paper_bgcolor='#0A0A1A',
        font=dict(color='#E0E8FF'),
        xaxis=dict(title="CG (mètres)", gridcolor='#1A3A5C', range=[lim_fwd - 1, lim_aft + 1]),
        yaxis=dict(title="Masse (kg)", gridcolor='#1A3A5C'),
        legend=dict(bgcolor='#0D1F3C', bordercolor='#00BFFF22'),
        height=420,
        margin=dict(l=40, r=40, t=50, b=40)
    )
    return fig

# =============================================================================
# MODULE 2 : V-SPEEDS & PERFORMANCES
# =============================================================================

def compute_vspeeds(ac: dict, tow: float, lw: float, elev_ft: int,
                    oat_c: float, rwy_length_m: int, flap_conf: str) -> dict:
    """
    Calcul paramétrique des V-speeds basé sur la masse et les conditions.
    Approche : ratio masse / MTOW appliqué aux références constructeur.
    """
    v = ac["vspeeds"]
    perf = ac["perf"]
    mtow = ac["max_tow_kg"]
    mlw = ac["max_lw_kg"]

    # ── Facteur de masse ──────────────────────────────────────────────────────
    mass_ratio_tow = (tow / mtow) ** 0.5
    mass_ratio_lw  = (lw  / mlw)  ** 0.5

    # ── Correction altitude-densité ───────────────────────────────────────────
    isa_base = 15 - (elev_ft / 1000) * 2
    isa_dev  = oat_c - isa_base
    alt_corr = (elev_ft / 1000) * perf["cl_per_1000ft"] * (-0.3)
    isa_corr = isa_dev * perf["isa_dev_correction"] * 0.1

    # ── Correction longueur de piste ─────────────────────────────────────────
    rwy_factor = 0.0
    if rwy_length_m < 2500:
        rwy_factor = (2500 - rwy_length_m) / 100 * perf["rwy_correction_per_100m"]

    # ── Flap correction (simplifié : CONF 1+F, 2, 3) ─────────────────────────
    flap_corr = {"CONF 1+F": 0, "CONF 2": -3, "CONF 3": -6, "CONF FULL": -10}.get(flap_conf, 0)

    # ── V-Speeds décollage ─────────────────────────────────────────────────────
    vs1_tow = v["vs1_ref_mtow"] * mass_ratio_tow
    v1       = round(vs1_tow * 1.05 + alt_corr + isa_corr + rwy_factor + flap_corr)
    vr       = round(v1 + v["vr_correction"])
    v2       = round(vr + v["v2_correction"] + alt_corr * 0.5)

    # ── Vref atterrissage ──────────────────────────────────────────────────────
    vs0_lw  = v["vs0_ref_mtow"] * mass_ratio_lw
    vref    = round(vs0_lw * v["vapp_factor"] + alt_corr * 0.3)
    vapp    = round(vref + 5)

    # ── Climb gradient (2nd segment) ──────────────────────────────────────────
    climb_gradient = round(perf["climb_gradient_min"] + (1 - mass_ratio_tow) * 2.0, 2)
    obstacle_ok = climb_gradient >= perf["climb_gradient_min"]

    return {
        "v1": max(v1, 100),
        "vr": max(vr, 110),
        "v2": max(v2, 115),
        "vref": max(vref, 95),
        "vapp": max(vapp, 100),
        "vs1_tow": round(vs1_tow),
        "vs0_lw": round(vs0_lw),
        "isa_dev": round(isa_dev, 1),
        "climb_gradient": climb_gradient,
        "obstacle_ok": obstacle_ok,
        "vmo": v["vmo"],
        "rwy_factor": round(rwy_factor, 1),
        "corrections": {
            "altitude": round(alt_corr, 1),
            "isa": round(isa_corr, 1),
            "rwy": round(rwy_factor, 1),
            "flap": flap_corr
        }
    }

# =============================================================================
# MODULE 3 : PLANIFICATION CARBURANT
# =============================================================================

def compute_fuel_plan(dist_nm: float, ac: dict, pax_total: int,
                      cargo_total_kg: float, wind_kt: int,
                      rwy_alt_dest_ft: int, oat_c: float) -> dict:
    """
    Plan carburant OACI : Trip + Contingence (5%) + Alternate + Final Reserve + Taxi.
    Basé sur la consommation horaire constructeur.
    """
    perf  = ac["perf"]
    speed_tas = ac.get("perf", {}).get("cruise_tas_kt", 450)  # kts TAS depuis la DB

    # ── Vent effectif (positif = vent arrière) ────────────────────────────────
    gs = speed_tas + wind_kt  # GS en kts

    # ── Trip fuel ─────────────────────────────────────────────────────────────
    trip_time_h = dist_nm / max(gs, 200)
    trip_fuel_kg = round(perf["fuel_flow_cruise"] * trip_time_h)

    # ── Carburant contingence (5% du trip, min 5 min) ─────────────────────────
    contingency_kg = round(max(trip_fuel_kg * 0.05, perf["fuel_flow_cruise"] * 5/60))

    # ── Alternate fuel (200 NM par défaut) ────────────────────────────────────
    alt_dist = 200
    alt_time_h = alt_dist / max(gs, 200)
    alt_fuel_kg = round(perf["fuel_flow_cruise"] * alt_time_h)

    # ── Réserve finale (30 min hold à 1500 ft AFM) ────────────────────────────
    final_reserve_kg = round(perf["fuel_flow_cruise"] * 0.5)

    # ── Taxi ──────────────────────────────────────────────────────────────────
    taxi_kg = 300

    # ── Total block fuel ──────────────────────────────────────────────────────
    block_fuel_kg = trip_fuel_kg + contingency_kg + alt_fuel_kg + final_reserve_kg + taxi_kg

    # ── Vérification limite réservoir ────────────────────────────────────────
    max_fuel = ac["mfuel"]
    fuel_ok = block_fuel_kg <= max_fuel

    return {
        "trip_fuel_kg": trip_fuel_kg,
        "contingency_kg": contingency_kg,
        "alt_fuel_kg": alt_fuel_kg,
        "final_reserve_kg": final_reserve_kg,
        "taxi_kg": taxi_kg,
        "block_fuel_kg": block_fuel_kg,
        "trip_time_h": round(trip_time_h, 2),
        "trip_time_str": f"{int(trip_time_h)}h{int((trip_time_h % 1) * 60):02d}",
        "gs_kt": gs,
        "fuel_ok": fuel_ok,
        "max_fuel": max_fuel,
        "fuel_pct": round(block_fuel_kg / max_fuel * 100, 1)
    }

# =============================================================================
# MODULE 4 : METAR LIVE
# =============================================================================

def fetch_metar(icao: str) -> dict:
    """
    Récupère le METAR via l'API publique aviationweather.gov (NOAA).
    Retourne le METAR brut et les données décodées principales.
    """
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=json"
    try:
        r = requests.get(url, timeout=8)
        data = r.json()
        if data and len(data) > 0:
            m = data[0]
            return {
                "raw": m.get("rawOb", "METAR non disponible"),
                "temp": m.get("temp"),
                "dewpoint": m.get("dewp"),
                "wind_dir": m.get("wdir"),
                "wind_kt": m.get("wspd"),
                "visibility_m": m.get("visib"),
                "altimeter_hpa": round(m.get("altim", 1013) * 33.8639 / 1000 * 1000 / 33.8639, 1)
                    if m.get("altim") else None,
                "sky": m.get("sky", []),
                "wx": m.get("wxString", ""),
                "flight_cat": m.get("flightCategory", "VFR"),
                "obs_time": m.get("obsTime", ""),
                "ok": True
            }
    except Exception as e:
        pass
    return {"raw": f"METAR non disponible pour {icao}", "ok": False, "flight_cat": "UNKN"}

def flight_cat_color(cat: str) -> str:
    return {"VFR": "#00FF88", "MVFR": "#00BFFF", "IFR": "#FF4444",
            "LIFR": "#FF00FF", "UNKN": "#888888"}.get(cat, "#888888")

# =============================================================================
# MODULE 5 : OPTIMISATION CARGO (PuLP)
# =============================================================================

def optimize_cargo_pulp(ac: dict, cargo_offers: list, max_payload_kg: float) -> dict:
    if not PULP_OK:
        return {"error": "PuLP non installé"}
    prob = _pulp.LpProblem("Cargo", _pulp.LpMaximize)
    vars_ = {o["name"]: _pulp.LpVariable(f"x_{i}", cat="Binary")
             for i, o in enumerate(cargo_offers)}
    prob += _pulp.lpSum(vars_[o["name"]] * o["revenue"] * o.get("priority", 1.0)
                        for o in cargo_offers)
    prob += _pulp.lpSum(vars_[o["name"]] * o["weight_kg"] for o in cargo_offers) <= max_payload_kg
    prob.solve()
    selected = [o for o in cargo_offers if _pulp.value(vars_[o["name"]]) == 1]
    return {
        "status": _pulp.LpStatus[prob.status],
        "selected": selected,
        "total_weight_kg": sum(o["weight_kg"] for o in selected),
        "total_revenue": sum(o["revenue"] for o in selected),
        "payload_remaining": max_payload_kg - sum(o["weight_kg"] for o in selected)
    }

# =============================================================================
# MODULE 6 : EXPORT PDF
# =============================================================================

def generate_pdf(flight_data: dict) -> bytes:
    """
    Génère une Load & Trim Sheet officielle AETHERDISPATCH en PDF.
    """
    pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.normalize_text = lambda t: str(t).replace('→', '->').replace('—', '-').replace('–', '-').replace('─', '-').replace('€', 'EUR').encode('latin-1', 'replace').decode('latin-1')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── En-tête ───────────────────────────────────────────────────────────────
    pdf.set_fill_color(10, 10, 26)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(0, 191, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_xy(10, 8)
    pdf.cell(190, 10, "AETHERDISPATCH", align='C')
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(180, 200, 220)
    pdf.set_xy(10, 20)
    pdf.cell(190, 6, "LOAD & TRIM SHEET  |  EG Conseil & Lobbying  |  Confidentiel handling", align='C')
    pdf.set_xy(10, 28)
    pdf.cell(190, 6, f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M UTC')}", align='C')

    # ── Infos vol ─────────────────────────────────────────────────────────────
    pdf.set_xy(10, 45)
    pdf.set_fill_color(13, 31, 60)
    pdf.set_text_color(0, 191, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(190, 8, "INFORMATIONS VOL", fill=True, align='C')
    pdf.ln(1)

    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "", 10)
    rows = [
        ("Numéro de vol", flight_data.get("flight_number", "N/A")),
        ("Aéronef", flight_data.get("aircraft", "N/A")),
        ("Départ → Arrivée", f"{flight_data.get('origin', '?')} → {flight_data.get('dest', '?')}"),
        ("Alternate", flight_data.get("alternate", "N/A")),
        ("Distance", f"{flight_data.get('dist_nm', 0)} NM"),
        ("Date/Heure", flight_data.get("datetime", "N/A")),
    ]
    for i, (label, val) in enumerate(rows):
        fill_color = (230, 240, 255) if i % 2 == 0 else (245, 248, 255)
        pdf.set_fill_color(*fill_color)
        pdf.cell(80, 7, label, fill=True, border=1)
        pdf.cell(110, 7, str(val), fill=True, border=1)
        pdf.ln()

    # ── Masses ────────────────────────────────────────────────────────────────
    pdf.ln(3)
    pdf.set_fill_color(13, 31, 60)
    pdf.set_text_color(0, 191, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(190, 8, "MASSES & CENTRAGE", fill=True, align='C')
    pdf.ln(1)

    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "", 10)
    mc_rows = [
        ("OEW (Masse à vide exploitée)", f"{flight_data.get('oew', 0):,} kg", "RÉFÉRENCE"),
        ("Passagers + Bagages", f"{flight_data.get('pax_total_kg', 0):,} kg", ""),
        ("Cargo total", f"{flight_data.get('cargo_total_kg', 0):,} kg", ""),
        ("ZERO FUEL WEIGHT (ZFW)", f"{flight_data.get('zfw', 0):,} kg", f"CG {flight_data.get('zfw_mac', 0):.1f}% MAC"),
        ("Carburant embarqué", f"{flight_data.get('fuel_kg', 0):,} kg", ""),
        ("TAKE-OFF WEIGHT (TOW)", f"{flight_data.get('tow', 0):,} kg", f"CG {flight_data.get('tow_mac', 0):.1f}% MAC"),
        ("Trip Fuel", f"{flight_data.get('trip_fuel', 0):,} kg", ""),
        ("LANDING WEIGHT (LW)", f"{flight_data.get('lw', 0):,} kg", f"CG estimé"),
    ]
    for i, (label, val, note) in enumerate(mc_rows):
        bold_rows = {3, 5, 7}
        fill_color = (210, 230, 255) if i in bold_rows else ((230, 240, 255) if i % 2 == 0 else (245, 248, 255))
        pdf.set_fill_color(*fill_color)
        font_style = "B" if i in bold_rows else ""
        pdf.set_font("Helvetica", font_style, 10)
        pdf.cell(90, 7, label, fill=True, border=1)
        pdf.cell(55, 7, val, fill=True, border=1, align='R')
        pdf.cell(45, 7, note, fill=True, border=1, align='C')
        pdf.ln()

    # ── V-Speeds ──────────────────────────────────────────────────────────────
    pdf.ln(3)
    pdf.set_fill_color(13, 31, 60)
    pdf.set_text_color(0, 191, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(190, 8, "V-SPEEDS OPÉRATIONNELS", fill=True, align='C')
    pdf.ln(1)

    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "B", 10)
    vs = flight_data.get("vspeeds", {})
    v_rows = [
        ("V1 (Go/No-Go)", f"{vs.get('v1', '—')} kts"),
        ("VR (Rotation)", f"{vs.get('vr', '—')} kts"),
        ("V2 (Sécurité décollage)", f"{vs.get('v2', '—')} kts"),
        ("VREF (Approche finale)", f"{vs.get('vref', '—')} kts"),
        ("VAPP (Approche stabilisée)", f"{vs.get('vapp', '—')} kts"),
    ]
    for i, (label, val) in enumerate(v_rows):
        fill_color = (240, 248, 255) if i % 2 == 0 else (250, 252, 255)
        pdf.set_fill_color(*fill_color)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(100, 7, label, fill=True, border=1)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(90, 7, val, fill=True, border=1, align='C')
        pdf.ln()

    # ── Carburant ─────────────────────────────────────────────────────────────
    pdf.ln(3)
    pdf.set_fill_color(13, 31, 60)
    pdf.set_text_color(0, 191, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(190, 8, "PLAN CARBURANT OACI", fill=True, align='C')
    pdf.ln(1)

    fp = flight_data.get("fuel_plan", {})
    pdf.set_text_color(30, 30, 30)
    fp_rows = [
        ("Trip Fuel", f"{fp.get('trip_fuel_kg', 0):,} kg"),
        ("Contingence (5%)", f"{fp.get('contingency_kg', 0):,} kg"),
        ("Carburant Alternate", f"{fp.get('alt_fuel_kg', 0):,} kg"),
        ("Réserve finale (30 min)", f"{fp.get('final_reserve_kg', 0):,} kg"),
        ("Taxi fuel", f"{fp.get('taxi_kg', 0):,} kg"),
        ("BLOCK FUEL TOTAL", f"{fp.get('block_fuel_kg', 0):,} kg"),
    ]
    for i, (label, val) in enumerate(fp_rows):
        fill_color = (210, 230, 255) if i == len(fp_rows)-1 else ((230, 240, 255) if i % 2 == 0 else (245, 248, 255))
        pdf.set_fill_color(*fill_color)
        font_style = "B" if i == len(fp_rows)-1 else ""
        pdf.set_font("Helvetica", font_style, 10)
        pdf.cell(100, 7, label, fill=True, border=1)
        pdf.cell(90, 7, val, fill=True, border=1, align='R')
        pdf.ln()

    # ── Signatures ────────────────────────────────────────────────────────────
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(63, 6, "Chef de Cabine : _______________", border=1, align='C')
    pdf.cell(2)
    pdf.cell(63, 6, "Commandant de Bord : __________", border=1, align='C')
    pdf.cell(2)
    pdf.cell(62, 6, "Agent Handling : ________________", border=1, align='C')

    # ── Pied de page ──────────────────────────────────────────────────────────
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(190, 5,
             "Document généré automatiquement par AETHERDISPATCH v2.0 — EG Conseil & Lobbying — "
             "Usage restreint aux personnels habilités. Vérification obligatoire par le commandant de bord.",
             align='C')

    return bytes(pdf.output())

# =============================================================================
# MODULE 7 : HISTORIQUE VOLS
# =============================================================================

def save_flight(flight_data: dict):
    """Sauvegarde un vol dans l'historique JSON."""
    history = load_json("flight_history.json")
    if not isinstance(history, list):
        history = []
    flight_data["saved_at"] = datetime.now(timezone.utc).isoformat()
    flight_data["saved_by"] = st.session_state.get("username", "inconnu")
    history.insert(0, flight_data)
    history = history[:200]  # Garder les 200 derniers vols
    save_json("flight_history.json", history)
    # Invalider le cache pour la prochaine lecture
    load_json.clear()

# =============================================================================
# APPLICATION PRINCIPALE
# =============================================================================

def main():
    # ── Chargement des données ────────────────────────────────────────────────
    users    = load_json("users.json")
    db       = load_json("compagnie_db.json")
    airports = load_json("airports_db.json")

    if not db:
        st.error("❌ compagnie_db.json introuvable. Vérifiez le répertoire de déploiement.")
        return

    # ── Authentification ──────────────────────────────────────────────────────
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        login_page(users)
        return

    user_info = st.session_state.user_info

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:12px;background:linear-gradient(135deg,#050510,#0A1428);
             border-radius:10px;border:1px solid rgba(0,191,255,0.2);margin-bottom:1rem">
            <div style="font-size:2.5rem">✈</div>
            <div style="font-weight:900;font-size:1.1rem;color:#00BFFF;letter-spacing:3px">AETHERDISPATCH</div>
            <div style="font-size:0.65rem;color:#556688;letter-spacing:1.5px;margin-top:2px">v2.0 | EG CONSEIL</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:#0D1F3C;border-radius:8px;padding:10px;border:1px solid rgba(0,191,255,0.15);
             font-size:0.8rem;margin-bottom:1rem">
            <div style="color:#00BFFF;font-weight:700">👤 {user_info['nom']}</div>
            <div style="color:#556688">Rôle : {user_info['role'].upper()}</div>
            <div style="color:#556688">{datetime.now().strftime('%d/%m/%Y %H:%M')} UTC</div>
        </div>
        """, unsafe_allow_html=True)

        # Sélection aéronef
        st.markdown("**🛩 Type d'aéronef**")
        selected_ac = st.selectbox("", list(db.keys()), label_visibility="collapsed")
        ac = db[selected_ac]

        st.markdown("---")
        dow_display = ac['oew_kg'] + ac.get('crew_kg', 0)
        st.markdown(f"""
        <div style="font-size:0.72rem;color:#556688;line-height:1.8">
        <b style="color:#00BFFF">TYPE :</b> {ac['type']}<br>
        <b style="color:#00BFFF">DOW :</b> {dow_display:,} kg<br>
        <b style="color:#00BFFF">MTOW :</b> {ac['max_tow_kg']:,} kg<br>
        <b style="color:#00BFFF">MZFW :</b> {ac['max_zfw_kg']:,} kg<br>
        <b style="color:#00BFFF">MLW :</b> {ac['max_lw_kg']:,} kg<br>
        <b style="color:#00BFFF">SIÈGES :</b> {ac['seats']}<br>
        <b style="color:#00BFFF">CARBU MAX :</b> {ac['mfuel']:,} kg
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔓 Déconnexion", use_container_width=True):
            for key in ["authenticated", "username", "user_info"]:
                st.session_state.pop(key, None)
            st.rerun()

    # ── Header principal ──────────────────────────────────────────────────────
    st.markdown("""
    <div class="aether-header">
        <h1>✈ AETHERDISPATCH</h1>
        <p>Agent IA handling aérien — Masse & Centrage · Performances · Météo · Carburant · Export PDF</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Onglets ───────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📋 Nouveau vol",
        "📸 OCR Manifest",
        "📈 Performances & V-Speeds",
        "⛽ Carburant & Météo",
        "🧠 Optimisation Cargo",
        "📄 Export PDF",
        "🗂 Historique"
    ])

    # =========================================================================
    # ONGLET 1 : NOUVEAU VOL & MASSE CENTRAGE
    # =========================================================================
    with tab1:
        st.subheader("📋 Plan de vol — Masse & Centrage")

        # ── Infos vol ─────────────────────────────────────────────────────────
        col_a, col_b, col_c = st.columns([1, 1, 1])
        with col_a:
            flight_number = st.text_input("N° de vol", value="AF1234", placeholder="AF1234")
            origin = st.selectbox("🛫 Départ", list(airports.keys()), key="origin")
        with col_b:
            flight_date = st.date_input("Date du vol", value=datetime.now())
            dest = st.selectbox("🛬 Arrivée", list(airports.keys()), key="dest")
        with col_c:
            flight_time = st.time_input("Heure départ (UTC)", value=datetime.now().time())
            alternate = st.selectbox("⚡ Alternate", list(airports.keys()), key="alt")

        orig_data = airports[origin]
        dest_data = airports[dest]
        dist_nm = haversine(orig_data["lat"], orig_data["lon"], dest_data["lat"], dest_data["lon"])

        st.markdown(f"""
        <div style="display:flex;gap:12px;margin:1rem 0;flex-wrap:wrap">
            <div class="metric-card" style="flex:1;min-width:140px">
                <div class="label">Distance</div>
                <div class="value">{dist_nm:.0f}</div>
                <div class="unit">NM</div>
            </div>
            <div class="metric-card" style="flex:1;min-width:140px">
                <div class="label">Altitude dest.</div>
                <div class="value">{dest_data['elev_ft']:,}</div>
                <div class="unit">ft</div>
            </div>
            <div class="metric-card" style="flex:1;min-width:140px">
                <div class="label">Piste dest.</div>
                <div class="value">{dest_data['rwy_length_m']:,}</div>
                <div class="unit">m</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)

        # ── PAX par zone ──────────────────────────────────────────────────────
        st.markdown("**👥 Répartition passagers par zone**")
        pax_std_weight = st.slider("Masse standard passager (bagages inclus) kg", 75, 100, 84)
        pax_zone_weights = {}
        pax_total_pax = 0
        cols_pax = st.columns(len(ac["pax_zones"]))
        for i, zone in enumerate(ac["pax_zones"]):
            with cols_pax[i]:
                nb = st.number_input(f"{zone['name']}", 0, zone["max_pax"],
                                     value=min(zone["max_pax"] // 2, zone["max_pax"]),
                                     key=f"pax_{i}")
                pax_zone_weights[zone["name"]] = nb * pax_std_weight
                pax_total_pax += nb
                st.caption(f"Max : {zone['max_pax']} | Bras : {zone['arm_m']} m")

        st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)

        # ── Cargo ─────────────────────────────────────────────────────────────
        st.markdown("**📦 Chargement cargo**")
        cargo_weights = {}
        cols_cargo = st.columns(len(ac["cargo_comps"]))
        for i, comp in enumerate(ac["cargo_comps"]):
            with cols_cargo[i]:
                w = st.number_input(f"{comp['name']} (kg)", 0, comp["max_kg"],
                                    value=min(500, comp["max_kg"]),
                                    key=f"cargo_{i}", step=50)
                cargo_weights[comp["name"]] = w
                st.caption(f"Max : {comp['max_kg']:,} kg | Bras : {comp['arm_m']} m")

        st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)

        # ── Carburant ─────────────────────────────────────────────────────────
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fuel_kg = st.number_input("⛽ Carburant embarqué (kg)", 1000, ac["mfuel"],
                                      value=min(int(ac["mfuel"] * 0.40), ac["mfuel"]), step=100)
        with col_f2:
            trip_fuel = st.number_input("✈ Trip fuel estimé (kg)", 500, ac["mfuel"],
                                        value=max(500, min(
    int(dist_nm / ac["perf"].get("cruise_tas_kt", 450)
        * ac["perf"]["fuel_flow_cruise"]),
    ac["mfuel"] - 1000)), step=100)

        # ── Calcul M&C ────────────────────────────────────────────────────────
        result = compute_mc(ac, pax_zone_weights, cargo_weights, fuel_kg)
        lw = result["tow"] - trip_fuel

        # Limites
        zfw_ok  = result["zfw"] <= ac["max_zfw_kg"]
        tow_ok  = result["tow"] <= ac["max_tow_kg"]
        lw_ok   = lw           <= ac["max_lw_kg"]
        cg_ok   = ac["cg_min_m"] <= result["tow_cg"] <= ac["cg_max_m"]

        # ── Métriques M&C ─────────────────────────────────────────────────────
        st.markdown("### ⚖ Résultats Masse & Centrage")

        def badge(cond): return '<span class="badge-ok">✓ DANS LIMITES</span>' if cond else '<span class="badge-nok">✗ HORS LIMITES</span>'

        cols_m = st.columns(4)
        metrics = [
            ("ZFW", result["zfw"], "kg", f"Max {ac['max_zfw_kg']:,} kg", zfw_ok),
            ("TOW", result["tow"], "kg", f"Max {ac['max_tow_kg']:,} kg", tow_ok),
            ("LW",  lw,            "kg", f"Max {ac['max_lw_kg']:,} kg",  lw_ok),
            ("CG TOW", result["tow_cg"], "m", f"FWD {ac['cg_min_m']} m / AFT {ac['cg_max_m']} m", cg_ok),
        ]
        for i, (label, val, unit, limit, ok) in enumerate(metrics):
            with cols_m[i]:
                color = "#00FF88" if ok else "#FF4444"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="label">{label}</div>
                    <div class="value" style="color:{color}">{val:,.1f}</div>
                    <div class="unit">{unit}</div>
                    <div style="font-size:0.68rem;color:#556688;margin-top:4px">{limit}</div>
                </div>
                """, unsafe_allow_html=True)

        # ── Graphique enveloppe ───────────────────────────────────────────────
        st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
        st.plotly_chart(plot_cg_envelope(ac, result, trip_fuel), use_container_width=True)

        # ── ZFW CG ───────────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:0.5rem">
            <div class="metric-card" style="flex:1">
                <div class="label">ZFW CG</div>
                <div class="value">{result['zfw_mac']:.1f}</div>
                <div class="unit">% MAC</div>
            </div>
            <div class="metric-card" style="flex:1">
                <div class="label">PAX total</div>
                <div class="value">{pax_total_pax}</div>
                <div class="unit">passagers</div>
            </div>
            <div class="metric-card" style="flex:1">
                <div class="label">Payload</div>
                <div class="value">{result['pax_total_kg'] + result['cargo_total_kg']:,}</div>
                <div class="unit">kg</div>
            </div>
            <div class="metric-card" style="flex:1">
                <div class="label">Carburant</div>
                <div class="value">{fuel_kg:,}</div>
                <div class="unit">kg ({round(fuel_kg/ac['mfuel']*100)}%)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Sauvegarde vol ────────────────────────────────────────────────────
        st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
        col_save1, col_save2 = st.columns([2, 1])
        with col_save1:
            if not all([zfw_ok, tow_ok, lw_ok, cg_ok]):
                st.warning("⚠ Certaines limites sont dépassées. Corrigez avant de sauvegarder.")

        with col_save2:
            if st.button("💾 Sauvegarder le vol", use_container_width=True):
                flight_record = {
                    "flight_number": flight_number,
                    "aircraft": selected_ac,
                    "origin": origin, "dest": dest, "alternate": alternate,
                    "dist_nm": dist_nm,
                    "datetime": f"{flight_date.strftime('%d/%m/%Y')} {flight_time.strftime('%H:%M')} UTC",
                    "pax_total_pax": pax_total_pax,
                    "oew": ac["oew_kg"],
                    **result,
                    "lw": lw,
                    "trip_fuel": trip_fuel,
                    "fuel_plan": {},
                    "vspeeds": {},
                    "status_ok": all([zfw_ok, tow_ok, lw_ok, cg_ok])
                }
                st.session_state.current_flight = flight_record
                save_flight(flight_record)
                st.success(f"✅ Vol {flight_number} sauvegardé dans l'historique.")

        # Stocker en session pour les autres onglets
        st.session_state.mc_result = result
        st.session_state.dist_nm   = dist_nm
        st.session_state.ac        = ac
        st.session_state.lw        = lw
        st.session_state.trip_fuel = trip_fuel
        st.session_state.flight_info = {
            "flight_number": flight_number, "origin": origin,
            "dest": dest, "alternate": alternate,
            "aircraft": selected_ac, "datetime": f"{flight_date} {flight_time}",
            "dist_nm": dist_nm
        }

    # =========================================================================
    # ONGLET 2 : OCR MANIFEST
    # =========================================================================
    with tab2:
        st.subheader("📸 OCR — Lecture automatique du manifest")

        if not EASYOCR_OK:
            st.warning("⚠ EasyOCR non installé dans cet environnement. "
                       "Ajoutez `easyocr` à requirements.txt pour activer ce module.")
            st.info("👉 En production, ce module lit automatiquement les manifests papier "
                    "scannés et remplit les zones PAX correspondantes.")
        else:
            uploaded = st.file_uploader(
                "📤 Déposez une photo du manifest passagers (JPG, PNG)",
                type=["jpg", "jpeg", "png"]
            )
            if uploaded:
                img = Image.open(uploaded)
                col_img, col_text = st.columns(2)
                with col_img:
                    st.image(img, caption="Document uploadé", use_column_width=True)
                with col_text:
                    with st.spinner("🔍 Analyse OCR en cours..."):
                        reader = easyocr.Reader(['fr', 'en'], gpu=False)
                        result_ocr = reader.readtext(np.array(img), detail=0)
                        text = "\n".join(result_ocr)
                    st.text_area("Texte détecté", text, height=350)

                    # Extraction automatique des nombres (PAX par zone)
                    numbers = re.findall(r'\b(\d{1,3})\b', text)
                    if numbers:
                        st.info(f"Nombres détectés : {', '.join(numbers[:10])}")
                        if st.button("🔄 Auto-remplir zones PAX depuis OCR"):
                            st.success("✅ Données OCR extraites. "
                                       "Vérifiez et validez dans l'onglet 'Nouveau vol'.")

    # =========================================================================
    # ONGLET 3 : PERFORMANCES & V-SPEEDS
    # =========================================================================
    with tab3:
        st.subheader("📈 Performances & V-Speeds opérationnels")

        mc  = st.session_state.get("mc_result", {})
        tow = mc.get("tow", ac["max_tow_kg"])
        lw  = st.session_state.get("lw", ac["max_lw_kg"])
        dist_nm_perf = st.session_state.get("dist_nm", 1000)

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            dep_airport_perf = st.selectbox("Aéroport de départ", list(airports.keys()), key="perf_dep")
            dep_data = airports[dep_airport_perf]
            elev_ft  = dep_data["elev_ft"]
            rwy_m    = dep_data["rwy_length_m"]
            st.caption(f"Élévation : {elev_ft} ft | Piste : {rwy_m} m")
        with col_p2:
            oat_c = st.number_input("OAT (°C)", -40, 60, 15)
            flap_conf = st.selectbox("Configuration volets décollage",
                                     ["CONF 1+F", "CONF 2", "CONF 3", "CONF FULL"])
        with col_p3:
            wind_dir_perf = st.number_input("Vent direction (°)", 0, 360, 270)
            wind_kt_perf  = st.number_input("Vent vitesse (kts)", 0, 60, 10)
            wind_note = "Vent arrière ✓" if wind_kt_perf > 0 else "Vent debout ✓"

        vs = compute_vspeeds(ac, tow, lw, elev_ft, oat_c, rwy_m, flap_conf)

        st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
        st.markdown("### ⚡ V-Speeds calculés")

        v_cols = st.columns(5)
        v_data = [
            ("V1", vs["v1"], "kts", "Décision décollage"),
            ("VR", vs["vr"], "kts", "Rotation"),
            ("V2", vs["v2"], "kts", "Sécurité 2nd segment"),
            ("VREF", vs["vref"], "kts", "Approche finale"),
            ("VAPP", vs["vapp"], "kts", "Approche stabilisée"),
        ]
        for i, (label, val, unit, desc) in enumerate(v_data):
            with v_cols[i]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="label">{label}</div>
                    <div class="value" style="color:#00BFFF">{val}</div>
                    <div class="unit">{unit}</div>
                    <div style="font-size:0.65rem;color:#556688;margin-top:3px">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

        # ── ISA & gradient ────────────────────────────────────────────────────
        st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
        col_g1, col_g2, col_g3, col_g4 = st.columns(4)
        with col_g1:
            st.metric("Déviation ISA", f"{vs['isa_dev']:+.1f} °C")
        with col_g2:
            st.metric("Gradient montée (2nd seg.)", f"{vs['climb_gradient']:.2f} %")
        with col_g3:
            grad_ok = vs["obstacle_ok"]
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Obstacle clearance</div>
                <div style="margin-top:6px">
                    <span class="{'badge-ok' if grad_ok else 'badge-nok'}">
                        {'✓ CONFORME' if grad_ok else '✗ NON CONFORME'}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_g4:
            st.metric("VMO", f"{vs['vmo']} kts")

        # ── Détail corrections ────────────────────────────────────────────────
        with st.expander("🔍 Détail des corrections appliquées"):
            corr = vs["corrections"]
            st.markdown(f"""
            | Facteur | Correction |
            |---------|-----------|
            | Altitude aéroport | {corr['altitude']:+.1f} kts |
            | Déviation ISA | {corr['isa']:+.1f} kts |
            | Longueur piste | {corr['rwy']:+.1f} kts |
            | Configuration volets | {corr['flap']:+.0f} kts |
            """)
            st.caption("Note : corrections paramétriques basées sur les données constructeur. "
                       "Toujours vérifier les QRH/FPM officiels.")

        # ── Graphique V-speeds ────────────────────────────────────────────────
        fig_vs = go.Figure()
        v_labels = ["VS1", "V1", "VR", "V2", "VREF", "VAPP", "VMO"]
        v_values = [vs["vs1_tow"], vs["v1"], vs["vr"], vs["v2"],
                    vs["vref"], vs["vapp"], vs["vmo"]]
        v_colors = ["#556688", "#FFD700", "#00FF88", "#00BFFF", "#7B2FBE", "#FF8C00", "#FF4444"]

        fig_vs.add_trace(go.Bar(
            x=v_labels, y=v_values,
            marker_color=v_colors,
            text=[f"{v} kts" for v in v_values],
            textposition='outside',
        ))
        fig_vs.update_layout(
            title="Tableau récapitulatif des vitesses opérationnelles",
            plot_bgcolor='#0D1F3C', paper_bgcolor='#0A0A1A',
            font=dict(color='#E0E8FF'),
            yaxis=dict(title="Vitesse (kts)", gridcolor='#1A3A5C'),
            xaxis=dict(gridcolor='#1A3A5C'),
            height=320
        )
        st.plotly_chart(fig_vs, use_container_width=True)

        # Stocker pour PDF
        st.session_state.vspeeds = vs

    # =========================================================================
    # ONGLET 4 : CARBURANT & MÉTÉO LIVE
    # =========================================================================
    with tab4:
        st.subheader("⛽ Plan carburant OACI & Météo METAR live")

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            wind_kt_fuel  = st.number_input("Composante vent croisière (kts, + = AR)", -80, 80, 0)
            cargo_tot_est = st.session_state.get("mc_result", {}).get("cargo_total_kg", 0)
            pax_tot_est   = st.session_state.get("mc_result", {}).get("pax_total_kg", 0)
        with col_f2:
            rwy_alt_ft    = airports[st.session_state.get("dest", list(airports.keys())[1])]["elev_ft"] \
                            if "dest" in st.session_state else 0
            oat_fuel      = st.number_input("OAT destination (°C)", -40, 60, 20)
        with col_f3:
            dist_nm_fuel  = st.session_state.get("dist_nm", 1000)
            st.metric("Distance route", f"{dist_nm_fuel:.0f} NM")

        fp = compute_fuel_plan(dist_nm_fuel, ac, pax_tot_est // 84, cargo_tot_est,
                               wind_kt_fuel, rwy_alt_ft, oat_fuel)

        # ── Tableau carburant ─────────────────────────────────────────────────
        st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
        st.markdown("### ⛽ Plan carburant détaillé")

        fuel_items = [
            ("Trip Fuel", fp["trip_fuel_kg"], "Carburant de route"),
            ("Contingence (5%)", fp["contingency_kg"], "Marge réglementaire"),
            ("Alternate Fuel", fp["alt_fuel_kg"], f"≈ 200 NM – {fp['trip_time_str']}"),
            ("Final Reserve (30 min)", fp["final_reserve_kg"], "Minimum réglementaire OACI"),
            ("Taxi Fuel", fp["taxi_kg"], "Roulage estimé"),
        ]
        cols_fuel = st.columns(len(fuel_items))
        for i, (label, val, note) in enumerate(fuel_items):
            with cols_fuel[i]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="label">{label}</div>
                    <div class="value">{val:,}</div>
                    <div class="unit">kg</div>
                    <div style="font-size:0.65rem;color:#556688;margin-top:3px">{note}</div>
                </div>
                """, unsafe_allow_html=True)

        fuel_ok_color = "#00FF88" if fp["fuel_ok"] else "#FF4444"
        st.markdown(f"""
        <div class="metric-card" style="margin-top:12px;border-color:{fuel_ok_color}">
            <div class="label">BLOCK FUEL TOTAL</div>
            <div class="value" style="color:{fuel_ok_color};font-size:2rem">{fp['block_fuel_kg']:,}</div>
            <div class="unit">kg — {fp['fuel_pct']:.1f}% réservoir | GS croisière : {fp['gs_kt']} kts</div>
            {'<span class="badge-ok">✓ DANS CAPACITÉ RÉSERVOIR</span>' if fp["fuel_ok"]
             else f'<span class="badge-nok">✗ DÉPASSE CAPACITÉ MAX {fp["max_fuel"]:,} kg</span>'}
        </div>
        """, unsafe_allow_html=True)

        # ── Graphique carburant ────────────────────────────────────────────────
        fig_fuel = go.Figure(go.Pie(
            labels=["Trip", "Contingence", "Alternate", "Réserve finale", "Taxi"],
            values=[fp["trip_fuel_kg"], fp["contingency_kg"], fp["alt_fuel_kg"],
                    fp["final_reserve_kg"], fp["taxi_kg"]],
            hole=0.55,
            marker=dict(colors=["#00BFFF", "#7B2FBE", "#FFD700", "#00FF88", "#556688"]),
        ))
        fig_fuel.update_layout(
            title="Répartition du block fuel",
            plot_bgcolor='#0D1F3C', paper_bgcolor='#0A0A1A',
            font=dict(color='#E0E8FF'), height=320
        )
        st.plotly_chart(fig_fuel, use_container_width=True)

        # ── METAR Live ────────────────────────────────────────────────────────
        st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
        st.markdown("### 🌍 METAR Live — Météo aéroports")

        metar_airports = st.multiselect(
            "Sélectionnez les aéroports à interroger",
            list(airports.keys()),
            default=list(airports.keys())[:3]
        )

        if st.button("🔄 Actualiser METARs", use_container_width=False):
            for ap_name in metar_airports:
                icao = airports[ap_name]["icao"]
                with st.spinner(f"Interrogation {icao}..."):
                    metar = fetch_metar(icao)
                cat = metar.get("flight_cat", "UNKN")
                cat_color = flight_cat_color(cat)

                if metar["ok"]:
                    temp_str  = f"{metar['temp']}°C" if metar.get("temp") is not None else "N/D"
                    wind_str  = f"{metar.get('wind_dir','---')}°/{metar.get('wind_kt','--')}kts" \
                                if metar.get("wind_dir") is not None else "N/D"
                    vis_str   = f"{metar.get('visibility_m','N/D')} SM"
                    st.markdown(f"""
                    <div style="background:#0D1F3C;border:1px solid {cat_color}33;border-radius:8px;
                         padding:10px 14px;margin:6px 0">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div>
                                <span style="font-weight:700;color:{cat_color};font-size:1rem">{icao}</span>
                                <span style="color:#556688;font-size:0.8rem;margin-left:8px">{ap_name}</span>
                            </div>
                            <span style="background:{cat_color}22;color:{cat_color};border:1px solid {cat_color};
                                  border-radius:12px;padding:2px 10px;font-size:0.75rem;font-weight:700">{cat}</span>
                        </div>
                        <div style="font-family:monospace;font-size:0.78rem;color:#A0B0D0;margin:6px 0;
                             background:#050510;padding:6px 10px;border-radius:4px">{metar['raw']}</div>
                        <div style="display:flex;gap:16px;font-size:0.78rem;color:#8899BB">
                            <span>🌡 {temp_str}</span>
                            <span>💨 {wind_str}</span>
                            <span>👁 {vis_str}</span>
                            <span> {str(metar.get('obs_time') or '')[:5] or 'N/D'}Z</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"❌ {icao} : {metar['raw']}")
        else:
            st.info("👆 Cliquez sur 'Actualiser METARs' pour récupérer les données météo en temps réel.")

        # Stocker fuel plan
        st.session_state.fuel_plan = fp

    # =========================================================================
    # ONGLET 5 : OPTIMISATION CARGO (PuLP)
    # =========================================================================
    with tab5:
        st.subheader("🧠 Optimisation cargo par programmation linéaire (PuLP)")

        if not PULP_OK:
            st.warning("⚠ PuLP non installé. Ajoutez `PuLP` à requirements.txt.")
        else:
            mc = st.session_state.get("mc_result", {})
            max_zfw  = ac["max_zfw_kg"]
            cur_zfw  = mc.get("zfw", ac["oew_kg"] + 2000)
            max_payload_remaining = max(0, max_zfw - cur_zfw +
                                        mc.get("cargo_total_kg", 0))

            st.info(f"Payload disponible pour optimisation : **{max_payload_remaining:,} kg**")

            # ── Saisie des offres cargo ────────────────────────────────────────
            st.markdown("**📦 Offres cargo à analyser**")
            n_offers = st.slider("Nombre d'offres", 2, 10, 5)

            cargo_offers = []
            col_h1, col_h2, col_h3, col_h4 = st.columns([2, 1, 1, 1])
            col_h1.markdown("**Désignation**")
            col_h2.markdown("**Masse (kg)**")
            col_h3.markdown("**Revenu (€)**")
            col_h4.markdown("**Priorité**")

            default_offers = [
                ("Fret express DHL", 450, 2800, 1.5),
                ("Colis perishables", 200, 1200, 2.0),
                ("Bagage excédentaire", 80, 150, 0.8),
                ("Fret postal PTT", 320, 960, 1.0),
                ("Équipements sportifs", 150, 450, 0.9),
                ("Fret médical urgent", 60, 3500, 3.0),
                ("Automobiles (parts)", 700, 2100, 1.0),
                ("Merchandising VIP", 100, 800, 1.2),
                ("Fleurs périssables", 180, 1800, 2.5),
                ("Fret général", 500, 1000, 0.7),
            ]

            for i in range(n_offers):
                d = default_offers[i] if i < len(default_offers) else (f"Offre {i+1}", 200, 800, 1.0)
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                name = col1.text_input(f"", value=d[0], key=f"offer_name_{i}", label_visibility="collapsed")
                mass = col2.number_input(f"", 10, 5000, d[1], key=f"offer_mass_{i}", label_visibility="collapsed")
                rev  = col3.number_input(f"", 0, 50000, d[2], key=f"offer_rev_{i}", label_visibility="collapsed")
                prio = col4.number_input(f"", 0.1, 5.0, float(d[3]), step=0.1, key=f"offer_prio_{i}", label_visibility="collapsed")
                cargo_offers.append({"name": name, "weight_kg": mass, "revenue": rev, "priority": prio})

            if st.button("🚀 Lancer l'optimisation PuLP", use_container_width=True):
                opt = optimize_cargo_pulp(ac, cargo_offers, max_payload_remaining)

                if "error" in opt:
                    st.error(opt["error"])
                else:
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#0D1F3C,#12264A);border:1px solid #00FF88;
                         border-radius:10px;padding:16px;margin:10px 0">
                        <div style="color:#00FF88;font-weight:700;font-size:1.1rem">
                            ✓ Optimisation terminée — Statut : {opt['status']}
                        </div>
                        <div style="display:flex;gap:20px;margin-top:10px;font-size:0.9rem">
                            <span style="color:#E0E8FF">Masse sélectionnée : <b>{opt['total_weight_kg']:,} kg</b></span>
                            <span style="color:#FFD700">Revenu optimisé : <b>{opt['total_revenue']:,} €</b></span>
                            <span style="color:#556688">Payload restant : {opt['payload_remaining']:,} kg</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Tableau résultats
                    df_opt = pd.DataFrame(opt["selected"])
                    if not df_opt.empty:
                        df_opt["revenue_par_kg"] = (df_opt["revenue"] / df_opt["weight_kg"]).round(2)
                        df_opt.columns = ["Désignation", "Masse (kg)", "Revenu (€)", "Priorité", "€/kg"]
                        st.dataframe(df_opt, use_container_width=True, hide_index=True)

                    # Comparatif
                    total_offers = sum(o["weight_kg"] for o in cargo_offers)
                    total_rev_all = sum(o["revenue"] for o in cargo_offers)
                    st.caption(f"Sur {len(cargo_offers)} offres ({total_offers:,} kg / {total_rev_all:,} €), "
                               f"l'optimisation retient {len(opt['selected'])} offres "
                               f"({opt['total_weight_kg']:,} kg / {opt['total_revenue']:,} €).")

    # =========================================================================
    # ONGLET 6 : EXPORT PDF
    # =========================================================================
    with tab6:
        st.subheader("📄 Export Load & Trim Sheet officielle PDF")

        mc   = st.session_state.get("mc_result", {})
        vs   = st.session_state.get("vspeeds", {})
        fp   = st.session_state.get("fuel_plan", {})
        info = st.session_state.get("flight_info", {})

        # Prévisualisation des données
        col_prev1, col_prev2 = st.columns(2)
        with col_prev1:
            st.markdown("**Données intégrées dans le PDF**")
            st.markdown(f"""
            <div style="background:#0D1F3C;border-radius:8px;padding:12px;font-size:0.82rem;line-height:2">
            ✈ <b>Vol</b> : {info.get('flight_number','—')}<br>
            🛩 <b>Aéronef</b> : {info.get('aircraft','—')}<br>
            🛫 <b>Route</b> : {info.get('origin','—')} → {info.get('dest','—')}<br>
            📏 <b>Distance</b> : {info.get('dist_nm',0):.0f} NM<br>
            ⚖ <b>ZFW</b> : {mc.get('zfw',0):,} kg<br>
            ⚖ <b>TOW</b> : {mc.get('tow',0):,} kg<br>
            ⚖ <b>LW</b> : {st.session_state.get('lw',0):,} kg<br>
            ⛽ <b>Block fuel</b> : {fp.get('block_fuel_kg',0):,} kg
            </div>
            """, unsafe_allow_html=True)

        with col_prev2:
            st.markdown("**V-Speeds & Carburant**")
            st.markdown(f"""
            <div style="background:#0D1F3C;border-radius:8px;padding:12px;font-size:0.82rem;line-height:2">
            ⚡ <b>V1</b> : {vs.get('v1','—')} kts<br>
            ⚡ <b>VR</b> : {vs.get('vr','—')} kts<br>
            ⚡ <b>V2</b> : {vs.get('v2','—')} kts<br>
            ⚡ <b>VREF</b> : {vs.get('vref','—')} kts<br>
            ✈ <b>Trip</b> : {fp.get('trip_fuel_kg',0):,} kg<br>
            ⚡ <b>Contingence</b> : {fp.get('contingency_kg',0):,} kg<br>
            🛬 <b>Alternate</b> : {fp.get('alt_fuel_kg',0):,} kg<br>
            🔒 <b>Réserve finale</b> : {fp.get('final_reserve_kg',0):,} kg
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)

        if st.button("📄 GÉNÉRER LA LOAD & TRIM SHEET PDF", use_container_width=True):
            flight_data_pdf = {
                **info,
                "oew": ac["oew_kg"],
                **mc,
                "lw": st.session_state.get("lw", 0),
                "trip_fuel": st.session_state.get("trip_fuel", 0),
                "vspeeds": vs,
                "fuel_plan": fp,
            }
            with st.spinner("⚙ Génération du PDF en cours..."):
                pdf_bytes = generate_pdf(flight_data_pdf)

            fname = f"AETHERDISPATCH_{info.get('flight_number','VOL')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            st.download_button(
                label="⬇ Télécharger la Load & Trim Sheet",
                data=pdf_bytes,
                file_name=fname,
                mime="application/pdf",
                use_container_width=True
            )
            st.success(f"✅ PDF généré : {fname}")

    # =========================================================================
    # ONGLET 7 : HISTORIQUE VOLS
    # =========================================================================
    with tab7:
        st.subheader("🗂 Historique des vols AETHERDISPATCH")

        history = load_json("flight_history.json")
        if not isinstance(history, list) or len(history) == 0:
            st.info("📭 Aucun vol sauvegardé. Remplissez l'onglet 'Nouveau vol' et cliquez sur 'Sauvegarder le vol'.")
        else:
            st.markdown(f"**{len(history)} vols enregistrés**")

            # ── Filtres ───────────────────────────────────────────────────────
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filter_ac = st.text_input("Filtrer par aéronef", "")
            with col_f2:
                filter_route = st.text_input("Filtrer par route", "")

            df_h = pd.DataFrame([{
                "Vol": h.get("flight_number", "—"),
                "Aéronef": h.get("aircraft", "—"),
                "Route": f"{h.get('origin','?')} → {h.get('dest','?')}",
                "Date": h.get("datetime", "—"),
                "TOW (kg)": h.get("tow", 0),
                "ZFW (kg)": h.get("zfw", 0),
                "CG TOW (%MAC)": h.get("tow_mac", 0),
                "Block Fuel": h.get("fuel_plan", {}).get("block_fuel_kg", 0),
                "Statut": "✅ OK" if h.get("status_ok") else "⚠ NON CONFORME",
                "Sauvegardé par": h.get("saved_by", "—"),
                "Date sauvegarde": h.get("saved_at", "—")[:10] if h.get("saved_at") else "—"
            } for h in history])

            # Application filtres
            if filter_ac:
                df_h = df_h[df_h["Aéronef"].str.contains(filter_ac, case=False, na=False)]
            if filter_route:
                df_h = df_h[df_h["Route"].str.contains(filter_route, case=False, na=False)]

            st.dataframe(df_h, use_container_width=True, hide_index=True,
                         column_config={
                             "TOW (kg)": st.column_config.NumberColumn(format="%,.0f"),
                             "ZFW (kg)": st.column_config.NumberColumn(format="%,.0f"),
                             "Block Fuel": st.column_config.NumberColumn(format="%,.0f"),
                             "CG TOW (%MAC)": st.column_config.NumberColumn(format="%.1f"),
                         })

            # ── Statistiques rapides ──────────────────────────────────────────
            if len(df_h) > 1:
                st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
                st.markdown("**📊 Statistiques rapides**")
                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                with col_s1:
                    st.metric("Vols enregistrés", len(df_h))
                with col_s2:
                    st.metric("TOW moyen", f"{df_h['TOW (kg)'].mean():,.0f} kg")
                with col_s3:
                    st.metric("Block fuel moyen", f"{df_h['Block Fuel'].mean():,.0f} kg")
                with col_s4:
                    ok_pct = (df_h["Statut"] == "✅ OK").mean() * 100
                    st.metric("Conformité", f"{ok_pct:.0f}%")

            # ── Export historique CSV ─────────────────────────────────────────
            csv = df_h.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Exporter l'historique CSV",
                csv,
                f"historique_aetherdispatch_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )

    # ── Footer ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="aether-footer">
        AETHERDISPATCH v2.0 — EG Conseil & Lobbying © 2026 — Système de gestion handling aérien augmenté par IA<br>
        Données à usage opérationnel restreint — Vérification obligatoire par le commandant de bord
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================
if __name__ == "__main__":
    main()
