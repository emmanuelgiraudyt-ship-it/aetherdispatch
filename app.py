# =============================================================================
# AETHERDISPATCH v4.0 — Agent IA Handling Aérien
# Développé par EG Conseil & Lobbying | Mars 2026
# Modules : Masse & Centrage | Performances | V-Speeds | METAR Live
#           Carburant | Optimisation PuLP | Référentiel compagnie | Export PDF | PWA
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
import io
import re
import copy
import zlib

# ─── Tentative d'import PuLP (optionnel) ──────────────────────────────────────
try:
    import pulp as _pulp
    PULP_OK = True
except Exception:
    PULP_OK = False

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
        AETHERDISPATCH v4.0 | EG Conseil & Lobbying © 2026
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
    """
    Optimisation linéaire du chargement cargo par PuLP.
    cargo_offers: liste de dicts {name, weight_kg, revenue, priority}
    Objectif : maximiser le revenu dans la limite du payload disponible.
    """
    if not PULP_OK:
        return {"error": "PuLP non installé"}
    prob = _pulp.LpProblem("Cargo", _pulp.LpMaximize)
    # Variables binaires : on prend ou non chaque offre
    vars_ = {o["name"]: _pulp.LpVariable(f"x_{i}", cat="Binary")
             for i, o in enumerate(cargo_offers)}
    # Objectif : maximiser le revenu pondéré par la priorité
    prob += _pulp.lpSum(vars_[o["name"]] * o["revenue"] * o.get("priority", 1.0)
                        for o in cargo_offers)
    # Contrainte de masse
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

def generate_pdf(fs: dict, include_speeds: bool = False) -> bytes:
    """
    Load & Trim Sheet A4, une page, simple et opérationnelle pour le dispatcher et le commandant de bord.
    Ordre : vol, trafic, soutes, carburant, calcul des masses, (vitesses), avion et commandant de bord.
    """
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    # La police standard ne gère que le latin-1 : remplacement des symboles non supportés
    pdf.normalize_text = lambda t: str(t).replace('→', '->').replace('—', '-').replace('–', '-').replace('─', '-').replace('−', '-').replace('€', 'EUR').replace('×', 'x').encode('latin-1', 'replace').decode('latin-1')

    NAVY, CYAN = (13, 31, 60), (0, 191, 255)
    HEAD, ZEBRA = (214, 228, 244), (244, 247, 252)
    GREEN, RED, TEXT = (0, 130, 70), (190, 30, 30), (30, 30, 30)
    H = 5.2

    def n(v):
        return f"{int(round(v)):,}".replace(",", " ")

    def section(title):
        pdf.set_x(10)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*CYAN)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(190, 5.8, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.6)

    def grid(rows, widths, header=False, bold_rows=(), bold_cols=(), aligns=None, colors=None, gap=1.6):
        for r, row in enumerate(rows):
            is_head = header and r == 0
            pdf.set_x(10)
            for c, (txt, w) in enumerate(zip(row, widths)):
                if is_head:
                    pdf.set_fill_color(*HEAD)
                    pdf.set_text_color(*NAVY)
                    pdf.set_font("Helvetica", "B", 8)
                else:
                    pdf.set_fill_color(*(ZEBRA if r % 2 else (255, 255, 255)))
                    pdf.set_text_color(*(colors or {}).get((r, c), TEXT))
                    pdf.set_font("Helvetica", "B" if (r in bold_rows or c in bold_cols) else "", 8.5)
                pdf.cell(w, H, str(txt), border=1, align=(aligns[c] if aligns else "L"), fill=True)
            pdf.ln(H)
        pdf.ln(gap)

    def state(ok, yes="OK", no="DÉPASSÉ"):
        return (yes if ok else no), (GREEN if ok else RED)

    # ── En-tête ───────────────────────────────────────────────────────────
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 25, "F")
    pdf.set_xy(10, 4.5)
    pdf.set_text_color(*CYAN)
    pdf.set_font("Helvetica", "B", 17)
    pdf.cell(190, 9, "LOAD & TRIM SHEET", align='C')
    pdf.set_xy(10, 15)
    pdf.set_text_color(200, 215, 230)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.cell(190, 5, f"AETHERDISPATCH  |  LOADSHEET {fs.get('ls_status', 'PRÉLIMINAIRE')}  |  "
                     f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} UTC", align='C')
    pdf.set_y(29)

    # ── Vol ───────────────────────────────────────────────────────────────
    section("VOL")
    grid([("Vol", fs.get("flight_number") or "-", "Date / heure (UTC)", fs.get("datetime", "-")),
          ("Départ", fs.get("origin", "-"), "Arrivée", fs.get("dest", "-")),
          ("Dégagement", fs.get("alternate", "-"), "Distance", f"{fs.get('dist_nm', 0):.0f} NM")],
         [30, 65, 30, 65], bold_cols=(0, 2))

    # ── Trafic ────────────────────────────────────────────────────────────
    section("TRAFIC")
    counts, masses = fs.get("pax_counts", {}), fs.get("pax_masses", {})
    keys = ("male", "female", "child", "infant")
    grid([("", "Hommes", "Femmes", "Enfants", "Bébés", "Sièges occupés"),
          ("Nombre", *[counts.get(k, 0) for k in keys], fs.get("seated", 0)),
          ("Masse unitaire (kg)", *[masses.get(k, 0) for k in keys], ""),
          ("Masse totale (kg)", *[n(counts.get(k, 0) * masses.get(k, 0)) for k in keys], n(fs.get("pax_mass_kg", 0)))],
         [34, 31, 31, 31, 31, 32], header=True, bold_cols=(0,), aligns=["L", "C", "C", "C", "C", "C"], gap=1.2)
    bag_lab = (f"Bagages ({fs.get('bag_pieces', 0)} x {fs.get('bag_std')} kg)"
               if fs.get("bag_mode") == "Masse forfaitaire" else "Bagages (pesée)")
    grid([("Passagers (kg)", bag_lab, "Fret (kg)", "Courrier (kg)", "CHARGE PAYANTE (kg)"),
          (n(fs.get("pax_mass_kg", 0)), n(fs.get("bag_total", 0)), n(fs.get("cargo_total", 0)),
           n(fs.get("mail_total", 0)), n(fs.get("payload", 0)))],
         [38, 38, 38, 38, 38], header=True, aligns=["C"] * 5, bold_rows=(1,))

    # ── Soutes ────────────────────────────────────────────────────────────
    comps = fs.get("comps", [])
    if comps:
        section("SOUTES (kg)")
        rows = [("Soute", "Bagages", "Fret", "Courrier", "Total", "Maxi")]
        colors = {}
        for i, c in enumerate(comps, start=1):
            rows.append((c["name"], n(c["bag"]), n(c["cargo"]), n(c["mail"]), n(c["total"]), n(c["max"])))
            if c["total"] > c["max"]:
                colors[(i, 4)] = RED
        rows.append(("TOTAL", n(sum(c["bag"] for c in comps)), n(sum(c["cargo"] for c in comps)),
                     n(sum(c["mail"] for c in comps)), n(sum(c["total"] for c in comps)),
                     n(sum(c["max"] for c in comps))))
        grid(rows, [46, 28, 28, 28, 30, 30], header=True, bold_rows=(len(rows) - 1,), bold_cols=(0,),
             aligns=["L", "R", "R", "R", "R", "R"], colors=colors)

    # ── Carburant ─────────────────────────────────────────────────────────
    fuel = fs.get("fuel", {})
    section("CARBURANT (kg)")
    grid([("Bloc fuel", "Taxi fuel", "Trip fuel", "Carburant au décollage"),
          (n(fuel.get("bloc", 0)), n(fuel.get("taxi", 0)), n(fuel.get("trip", 0)), n(fuel.get("tof", 0)))],
         [47.5] * 4, header=True, aligns=["C"] * 4, bold_rows=(1,))

    # ── Calcul des masses ─────────────────────────────────────────────────
    section("CALCUL DES MASSES (kg)")
    grid([("DOW", "+ Charge payante", "= ZFW", "+ Carb. décollage", "= TOW", "- Trip fuel", "= LW"),
          (n(fs.get("dow", 0)), n(fs.get("payload", 0)), n(fs.get("zfw", 0)), n(fuel.get("tof", 0)),
           n(fs.get("tow", 0)), n(fuel.get("trip", 0)), n(fs.get("lw", 0)))],
         [27.2, 27.2, 27.2, 27.2, 27.2, 27.2, 26.8], header=True, aligns=["C"] * 7, bold_rows=(1,), gap=0.8)
    cg_txt, cg_col = state(fs.get("cg_ok", False), "OK", "HORS LIMITES")
    pdf.set_x(10)
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(*cg_col)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(190, H, f"Centrage au décollage : {fs.get('tow_cg', 0):.2f} m   (limites {fs.get('cg_min', 0):.2f} à "
                     f"{fs.get('cg_max', 0):.2f} m)   -   {cg_txt}", border=1, align='C', fill=True)
    pdf.ln(H + 1.6)

    # ── Vitesses (facultatif) ─────────────────────────────────────────────
    vs = fs.get("vspeeds") or {}
    if include_speeds and vs:
        section("VITESSES INDICATIVES (formule approchée, non issues de l'AFM)")
        grid([("V1", "VR", "V2", "VREF", "VAPP"),
              (f"{vs.get('v1', '-')} kts", f"{vs.get('vr', '-')} kts", f"{vs.get('v2', '-')} kts",
               f"{vs.get('vref', '-')} kts", f"{vs.get('vapp', '-')} kts")],
             [38] * 5, header=True, aligns=["C"] * 5, bold_rows=(1,))

    # ── Avion et commandant de bord (en fin de document) ──────────────────
    section("AVION ET COMMANDANT DE BORD")
    grid([("Immatriculation", fs.get("registration") or "-", "Type", fs.get("type") or "-"),
          ("Commandant de bord", fs.get("cdb_name") or "", "Préparé par", fs.get("prepared_by") or "")],
         [40, 55, 32, 63], bold_cols=(0, 2), gap=1.2)
    rows, colors = [("Masse (kg)", "Calculée", "Maximum", "Marge", "État")], {}
    for i, (lab, val, mx, ok) in enumerate([("ZFW", fs.get("zfw", 0), fs.get("max_zfw", 0), fs.get("zfw_ok")),
                                           ("TOW", fs.get("tow", 0), fs.get("max_tow", 0), fs.get("tow_ok")),
                                           ("LW", fs.get("lw", 0), fs.get("max_lw", 0), fs.get("lw_ok"))], start=1):
        txt, col = state(bool(ok))
        rows.append((lab, n(val), n(mx), n(mx - val), txt))
        colors[(i, 4)] = col
    txt, col = state(bool(fs.get("cg_ok")), "OK", "HORS LIMITES")
    rows.append(("Centrage (m)", f"{fs.get('tow_cg', 0):.2f}", f"{fs.get('cg_min', 0):.2f} à {fs.get('cg_max', 0):.2f}", "", txt))
    colors[(4, 4)] = col
    txt, col = state(bool(fs.get("stock_ok", True)), "OK", "DÉPASSÉE")
    rows.append(("Capacité des soutes", "", "", "", txt))
    colors[(5, 4)] = col
    grid(rows, [40, 38, 38, 38, 36], header=True, bold_cols=(0,), aligns=["L", "R", "R", "R", "C"], colors=colors, gap=2.2)

    pdf.set_x(10)
    pdf.set_text_color(70, 70, 70)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(63, 9, "Commandant de bord :", border=1, align='L')
    pdf.cell(2)
    pdf.cell(63, 9, f"Dispatcher : {fs.get('prepared_by') or ''}", border=1, align='L')
    pdf.cell(2)
    pdf.cell(60, 9, "Agent handling :", border=1, align='L')

    # ── Pied de page : origine des données ────────────────────────────────
    certified = bool(fs.get("data_certified"))
    pdf.set_y(-27)
    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 7.6)
    pdf.set_text_color(*(GREEN if certified else RED))
    pdf.cell(190, 4, f"Origine des données : {fs.get('origin_text', '-')}"
             + ("" if certified else "   -   DONNÉES NON CERTIFIÉES"), align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.4)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(190, 3.8, f"Référentiel : {fs.get('referentiel_text', '-')}", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(190, 3.8, "Document généré par AETHERDISPATCH v4.0. Vérification obligatoire par le commandant de bord.",
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
# MODULE 8 : DONNÉES AÉRONEF MODIFIABLES · STATUTS D'ORIGINE · PROFIL COMPAGNIE
#            · PANNEAU PASSAGERS (PAX prévus / PAX final)
# =============================================================================

STATUS_LABELS = {
    "constructeur": "Constructeur",
    "reglementaire": "Réglementaire",
    "estime": "Estimé",
    "compagnie": "Compagnie",
    "a_renseigner": "À renseigner",
}
LABEL_TO_STATUS = {v: k for k, v in STATUS_LABELS.items()}

# (clé, libellé, unité, requis pour les calculs)
SCALAR_FIELDS = [
    ("max_seats",  "Capacité maximale (sièges)",                "sièges", False),
    ("seats",      "Sièges - configuration modèle",             "sièges", False),
    ("oew_kg",     "Masse à vide exploitée (OEW)",              "kg",     True),
    ("oew_arm_m",  "Bras de l'OEW",                             "m",      True),
    ("crew_kg",    "Équipage (masse)",                          "kg",     True),
    ("crew_arm_m", "Équipage (bras)",                           "m",      True),
    ("max_zfw_kg", "MZFW (masse maximale sans carburant)",      "kg",     True),
    ("max_tow_kg", "MTOW (masse maximale au décollage)",        "kg",     True),
    ("max_lw_kg",  "MLW (masse maximale à l'atterrissage)",     "kg",     True),
    ("mfuel",      "Capacité carburant maximale",               "kg",     True),
    ("fuel_arm_m", "Bras du carburant",                         "m",      True),
    ("cg_min_m",   "Limite de centrage avant",                  "m",      True),
    ("cg_max_m",   "Limite de centrage arrière",                "m",      True),
    ("lemac",      "LEMAC",                                     "m",      True),
    ("mac_length", "Longueur de la corde moyenne (MAC)",        "m",      True),
]
SPEED_FIELDS = [
    ("vspeeds.vmo",          "VMO",                               "kts", True),
    ("vspeeds.mmo",          "MMO",                               "Mach", False),
    ("vspeeds.vs0_ref_mtow", "VS0 de référence (au MTOW)",        "kts", True),
    ("vspeeds.vs1_ref_mtow", "VS1 de référence (au MTOW)",        "kts", True),
    ("vspeeds.vr_correction","Correction VR par rapport à V1",    "kts", True),
    ("vspeeds.v2_correction","Correction V2 par rapport à VR",    "kts", True),
    ("vspeeds.vapp_factor",  "Facteur VAPP / VS0",                "",    True),
]
PERF_FIELDS = [
    ("perf.cl_per_1000ft",           "Correction altitude (par 1000 ft)",   "",       True),
    ("perf.isa_dev_correction",      "Correction écart ISA",                "",       True),
    ("perf.rwy_correction_per_100m", "Correction piste courte (par 100 m)", "",       True),
    ("perf.climb_gradient_min",      "Gradient de montée minimal",          "%",      True),
    ("perf.fuel_flow_cruise",        "Consommation en croisière",           "kg/h",   True),
    ("perf.cruise_tas_kt",           "Vitesse de croisière (TAS)",          "kts",    False),
]
ALL_FIELDS = SCALAR_FIELDS + SPEED_FIELDS + PERF_FIELDS


def fmt_num(v, unit=""):
    """Format lisible ; « à renseigner » si la donnée est absente."""
    if v is None:
        return "à renseigner"
    try:
        s = f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"
    except (TypeError, ValueError):
        return str(v)
    return f"{s} {unit}".strip()


def get_field(ac: dict, key: str):
    if "." in key:
        sub, k = key.split(".", 1)
        return (ac.get(sub) or {}).get(k)
    return ac.get(key)


def set_field(ac: dict, key: str, value):
    if "." in key:
        sub, k = key.split(".", 1)
        if not isinstance(ac.get(sub), dict):
            ac[sub] = {}
        ac[sub][k] = value
    else:
        ac[key] = value


def _meta(ac: dict) -> dict:
    m = ac.setdefault("_meta", {})
    m.setdefault("status", {})
    m.setdefault("source", {})
    return m


def field_status(ac: dict, key: str) -> str:
    if get_field(ac, key) is None:
        return "a_renseigner"
    return _meta(ac)["status"].get(key) or "estime"


def missing_fields(ac: dict) -> list:
    """Liste des données obligatoires manquantes (vide = calculs possibles)."""
    out = [label for key, label, unit, req in ALL_FIELDS if req and get_field(ac, key) is None]
    zones = ac.get("pax_zones") or []
    if not zones:
        out.append("Zones passagers (au moins une zone avec son bras)")
    for z in zones:
        if z.get("arm_m") is None:
            out.append(f"Bras de la zone passagers « {z.get('name', '?')} »")
    for c in ac.get("cargo_comps") or []:
        if c.get("arm_m") is None:
            out.append(f"Bras de la soute « {c.get('name', '?')} »")
        if c.get("max_kg") is None:
            out.append(f"Capacité de la soute « {c.get('name', '?')} »")
    return out


def split_pax(total: int, zones: list) -> list:
    """Répartition automatique des passagers, proportionnelle à la capacité de chaque zone."""
    n = len(zones)
    if n == 0:
        return []
    caps = [max(int(z.get("max_pax") or 0), 0) for z in zones]
    capsum = sum(caps)
    raw = [total * c / capsum for c in caps] if capsum > 0 else [total / n] * n
    base = [int(x) for x in raw]
    rest = int(total) - sum(base)
    order = sorted(range(n), key=lambda i: raw[i] - base[i], reverse=True)
    for i in order[:max(rest, 0)]:
        base[i] += 1
    return base


def origin_counts(ac: dict) -> dict:
    counts = {k: 0 for k in STATUS_LABELS}
    for key, label, unit, req in ALL_FIELDS:
        if req:
            counts[field_status(ac, key)] += 1
    for row in (ac.get("pax_zones") or []) + (ac.get("cargo_comps") or []):
        s = "a_renseigner" if row.get("arm_m") is None else (row.get("status") or "estime")
        counts[s if s in counts else "estime"] += 1
    return counts


def origin_summary(ac: dict):
    """Texte récapitulatif de l'origine des données + indicateur « entièrement issu de la compagnie »."""
    c = origin_counts(ac)
    others = sum(v for k, v in c.items() if k != "compagnie")
    certified = c["compagnie"] > 0 and others == 0
    txt = " / ".join(f"{c[k]} {STATUS_LABELS[k]}" for k in ("compagnie", "constructeur", "reglementaire", "estime", "a_renseigner") if c[k])
    return txt or "aucune donnée", certified


def new_blank_aircraft(type_code: str = "") -> dict:
    r = {"type": type_code, "seats_typical": "", "fuel_density": 0.8, "loading_mode": "vrac",
         "pax_zones": [], "cargo_comps": [], "_meta": {"status": {}, "source": {}}}
    for key, label, unit, req in ALL_FIELDS:
        set_field(r, key, None)
        r["_meta"]["status"][key] = "a_renseigner"
    return r


def normalize_aircraft(rec: dict) -> dict:
    """Complète un enregistrement (clés absentes) sans modifier les valeurs existantes."""
    r = copy.deepcopy(rec)
    for key, label, unit, req in ALL_FIELDS:
        set_field(r, key, get_field(r, key))
    r.setdefault("type", "")
    r.setdefault("seats_typical", "")
    r.setdefault("fuel_density", 0.8)
    r.setdefault("loading_mode", "vrac")
    for k in ("pax_zones", "cargo_comps"):
        if not isinstance(r.get(k), list):
            r[k] = []
    _meta(r)
    return r


# ── Profil compagnie : export / import ───────────────────────────────────────
def export_profile_bytes(db: dict, profile_name: str, user_name: str, referentiel=None) -> bytes:
    payload = {
        "format": "aetherdispatch-profile", "version": 2,
        "name": (profile_name or "Profil compagnie").strip(),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_by": user_name,
        "aircraft": db,
        "referentiel": referentiel,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def import_profile_bytes(raw: bytes):
    """Retourne (ok, message, base_aéronefs, infos_profil)."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return False, "Fichier illisible (JSON invalide).", None, None
    if (not isinstance(data, dict) or data.get("format") != "aetherdispatch-profile"
            or not isinstance(data.get("aircraft"), dict) or not data["aircraft"]):
        return False, "Ce fichier n'est pas un profil AETHERDISPATCH valide.", None, None
    out = {}
    for name, rec in data["aircraft"].items():
        if not isinstance(rec, dict):
            return False, f"Le type « {name} » est invalide.", None, None
        out[str(name)] = normalize_aircraft(rec)
    info = {"name": data.get("name") or "Profil sans nom",
            "exported_at": data.get("exported_at", ""), "exported_by": data.get("exported_by", ""),
            "referentiel": data.get("referentiel")}
    return True, f"{len(out)} type(s) d'aéronef chargé(s).", out, info


def _mark_exported():
    st.session_state.dirty = False
    if not st.session_state.get("profile_info"):
        st.session_state.profile_info = {"name": st.session_state.get("profile_name") or "Profil compagnie"}


def render_profile_banner():
    info = st.session_state.get("profile_info")
    if st.session_state.get("dirty"):
        st.warning("Modifications non exportées : exportez votre profil (onglet « Données aéronef ») pour ne pas "
                   "les perdre lors du prochain redémarrage de l'application.")
    elif not info:
        st.warning("Profil compagnie non chargé : les valeurs affichées sont des valeurs constructeur ou estimées. "
                   "Importez votre profil dans l'onglet « Données aéronef » avant de produire une loadsheet.")
    else:
        st.success(f"Profil compagnie chargé : {info.get('name', '')}")


# ── Référentiel compagnie : masses standard et bagages ───────────────────────
SRC_EASA_PAX = ("Règlement (UE) n° 965/2012, AMC1 CAT.POL.MAB.100(e), tableau 1 "
                "(aéronefs de 20 sièges passagers ou plus)")
SRC_EASA_INF = ("AMC1 CAT.POL.MAB.100(e) : nourrisson porté par un adulte inclus dans la masse de l'adulte ; "
                "un nourrisson occupant un siège est traité comme un enfant. 10 kg si le GOM de la compagnie le prévoit.")
SRC_BAG = ("Masses forfaitaires de bagage en soute (11 / 13 / 15 kg) : règlement (UE) n° 965/2012 "
           "— à confirmer dans le MANEX")


def default_referentiel() -> dict:
    def item(label, value, src):
        return {"label": label, "value": value, "status": "reglementaire", "source": src}
    return {
        "identification": {"organisme": "", "document": "", "version": "", "date_application": ""},
        "pax_masses": {"male": item("Hommes", 88, SRC_EASA_PAX), "female": item("Femmes", 70, SRC_EASA_PAX),
                       "child": item("Enfants", 35, SRC_EASA_PAX), "infant": item("Bébés", 0, SRC_EASA_INF)},
        "bag_masses": {"domestic": item("Vol intérieur", 11, SRC_BAG), "other": item("Autres vols", 13, SRC_BAG),
                       "intercontinental": item("Vol intercontinental", 15, SRC_BAG)},
    }


def normalize_referentiel(r) -> dict:
    """Complète un référentiel (importé ou ancien) avec les valeurs par défaut manquantes."""
    base = default_referentiel()
    if not isinstance(r, dict):
        return base
    for grp in ("pax_masses", "bag_masses"):
        for k, it in base[grp].items():
            src = (r.get(grp) or {}).get(k)
            if isinstance(src, dict):
                v = _num(src.get("value"))
                if v is not None:
                    it["value"] = v
                if src.get("status") in STATUS_LABELS:
                    it["status"] = src["status"]
                if isinstance(src.get("source"), str):
                    it["source"] = src["source"]
    ident = r.get("identification") or {}
    for k in base["identification"]:
        if isinstance(ident.get(k), str):
            base["identification"][k] = ident[k]
    return base


def referentiel_label(ref: dict) -> str:
    i = ref["identification"]
    parts = [p for p in (i.get("organisme"), i.get("document"), i.get("version")) if p]
    return " - ".join(parts) if parts else "non renseigné (valeurs réglementaires par défaut)"


def ref_acceptable(ref: dict) -> bool:
    """Vrai si toutes les valeurs du référentiel sont réglementaires ou issues de la compagnie."""
    items = list(ref["pax_masses"].values()) + list(ref["bag_masses"].values())
    return all(it["status"] in ("compagnie", "reglementaire") for it in items)


# ── Passagers par catégorie ──────────────────────────────────────────────────
PAX_CATS = [("male", "Hommes"), ("female", "Femmes"), ("child", "Enfants"), ("infant", "Bébés")]
BAG_FLIGHT_TYPES = [("domestic", "Vol intérieur"), ("other", "Autres vols"), ("intercontinental", "Vol intercontinental")]


def ref_pax_masses(ref: dict) -> dict:
    return {k: ref["pax_masses"][k]["value"] for k, _ in PAX_CATS}


def pax_mass_total(counts: dict, masses: dict) -> float:
    return sum(counts[k] * masses[k] for k, _ in PAX_CATS)


def seated_count(counts: dict) -> int:
    """Sièges occupés : hommes, femmes et enfants (un bébé porté par un adulte n'occupe pas de siège)."""
    return counts["male"] + counts["female"] + counts["child"]


def zone_weights_from_counts(ac: dict, counts: dict, masses: dict, zone_counts=None) -> dict:
    """Masse passagers par zone : sièges occupés répartis par zone × masse moyenne par passager."""
    zones = ac.get("pax_zones") or []
    if not zones:
        return {}
    seated = seated_count(counts)
    zc = list(zone_counts) if zone_counts else split_pax(seated, zones)
    avg = pax_mass_total(counts, masses) / seated if seated else 0.0
    return {z["name"]: zc[i] * avg for i, z in enumerate(zones)}


# ── Bagages : répartition par priorité de chargement ─────────────────────────
def allocate_bags(comps: list, bag_total: float, used: dict):
    """Répartit les bagages entre les soutes. Retourne (répartition, mode, masse non placée)."""
    names = [c["name"] for c in comps]
    alloc = {n: 0 for n in names}
    total = max(int(round(bag_total)), 0)
    if not comps or total == 0:
        return alloc, "aucune", 0
    free = {c["name"]: max(int(c["max_kg"]) - int(used.get(c["name"], 0)), 0) for c in comps}
    ranked = sorted([c for c in comps if c.get("bag_rank") is not None], key=lambda c: c["bag_rank"])
    if ranked:
        mode, rest = "priorité", total
        order = [c["name"] for c in ranked] + [c["name"] for c in comps if c.get("bag_rank") is None]
        for n in order:
            take = min(free[n], rest)
            alloc[n] += take
            rest -= take
            if rest <= 0:
                break
        return alloc, mode, max(rest, 0)
    mode, capsum = "proportionnelle", sum(free.values())
    if capsum <= 0:
        return alloc, mode, total
    raw = {n: total * free[n] / capsum for n in names}
    base = {n: min(int(raw[n]), free[n]) for n in names}
    rest = total - sum(base.values())
    for n in sorted(names, key=lambda n: raw[n] - int(raw[n]), reverse=True):
        if rest <= 0:
            break
        add = min(free[n] - base[n], rest)
        base[n] += add
        rest -= add
    return base, mode, max(rest, 0)


def bag_priority_text(comps: list) -> str:
    ranked = sorted([c for c in comps if c.get("bag_rank") is not None], key=lambda c: c["bag_rank"])
    return " > ".join(c["name"] for c in ranked)


# ── Panneau passagers (catégories, prévus / final) ───────────────────────────
def render_pax_panel(ac: dict, selected_ac: str, ref: dict) -> dict:
    max_seats = ac.get("max_seats")
    zones = ac.get("pax_zones") or []
    typical = ac.get("seats_typical") or ""
    masses = ref_pax_masses(ref)

    st.markdown("**👥 Passagers : prévus et final**")
    c1, c2 = st.columns([1, 3])
    with c1:
        cap_txt = f"{int(max_seats):,}".replace(",", " ") if max_seats else "à renseigner"
        typ_txt = f"Typique : {typical}" if typical else ""
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Capacité maximale</div>
            <div class="value">{cap_txt}</div>
            <div class="unit">sièges</div>
            <div style="font-size:0.68rem;color:#556688;margin-top:4px">{typ_txt}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        status = st.radio("Statut de la loadsheet", ["Préliminaire", "Final"], horizontal=True,
                          key=f"ls_status_{selected_ac}")
        badge = "badge-ok" if status == "Final" else "badge-warn"
        st.markdown(f'<span class="{badge}">LOADSHEET {status.upper()}</span>', unsafe_allow_html=True)
        st.caption(f"Masses standard appliquées : hommes {masses['male']} kg, femmes {masses['female']} kg, "
                   f"enfants {masses['child']} kg, bébés {masses['infant']} kg (onglet « Données aéronef »).")

    default_each = int(max_seats // 4) if max_seats else 0

    def counts_row(prefix, title, defaults):
        st.markdown(f"*{title}*")
        out = {}
        for col, (k, label) in zip(st.columns(4), PAX_CATS):
            with col:
                out[k] = int(st.number_input(label, 0, 1000, int(defaults.get(k, 0)),
                                             key=f"pax_{prefix}_{k}_{selected_ac}"))
        return out

    prev = counts_row("prev", "PAX prévus", {"male": default_each, "female": default_each})
    final = counts_row("final", "PAX final (à saisir à la clôture)", {})

    active_counts = final if status == "Final" else prev
    seated = seated_count(active_counts)
    seated_prev, seated_final = seated_count(prev), seated_count(final)
    has_final = sum(final.values()) > 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Sièges occupés", seated)
    m2.metric("Bébés", active_counts["infant"])
    m3.metric("Écart final − prévu", f"{seated_final - seated_prev:+d}" if has_final else "—")
    m4.metric("Remplissage", f"{seated / max_seats * 100:.0f} %" if max_seats else "—")
    m5.metric("Places libres", f"{int(max_seats - seated)}" if max_seats else "—")

    if status == "Final" and not has_final:
        st.warning("Statut « Final » sélectionné, mais le PAX final n'est pas saisi.")
    if max_seats:
        if seated > max_seats:
            st.error(f"Sièges occupés ({seated}) supérieurs à la capacité maximale ({int(max_seats)} sièges).")
    else:
        st.info("Capacité maximale à renseigner (onglet « Données aéronef ») : l'alerte de dépassement est désactivée.")

    zone_counts = []
    if zones:
        auto = split_pax(seated, zones)
        with st.expander("Répartition par zone (automatique, ajustable)"):
            cols = st.columns(len(zones))
            for i, z in enumerate(zones):
                with cols[i]:
                    n = st.number_input(f"{z['name']}", 0, 1000, int(auto[i]),
                                        key=f"paxz_{selected_ac}_{i}_{status}_{seated}")
                    zone_counts.append(int(n))
                    cap = z.get("max_pax")
                    st.caption(f"Capacité : {cap if cap is not None else '—'} | Bras : {z.get('arm_m', '—')} m")
            if sum(zone_counts) != seated:
                st.warning(f"La somme des zones ({sum(zone_counts)}) diffère des sièges occupés ({seated}).")
    return {"status": status, "prev": prev, "final": final, "active_counts": active_counts, "seated": seated,
            "seated_prev": seated_prev, "seated_final": seated_final, "has_final": has_final,
            "zone_counts": zone_counts, "max_seats": max_seats, "masses": masses}


def render_pax_comparison(ac: dict, pax: dict, comp_loads: dict, tof: float):
    """Tableau prévu / final : sièges, bébés, ZFW, TOW, centrage."""
    st.markdown("**Comparaison prévu / final**")
    if not pax["has_final"]:
        st.caption("PAX final non saisi : la comparaison s'affichera dès qu'il le sera.")
        return

    def scenario(counts):
        return compute_mc(ac, zone_weights_from_counts(ac, counts, pax["masses"]), comp_loads, tof)

    rp, rf = scenario(pax["prev"]), scenario(pax["final"])
    rows = [
        ("Sièges occupés", f"{pax['seated_prev']}", f"{pax['seated_final']}", f"{pax['seated_final'] - pax['seated_prev']:+d}"),
        ("Bébés", f"{pax['prev']['infant']}", f"{pax['final']['infant']}", f"{pax['final']['infant'] - pax['prev']['infant']:+d}"),
        ("ZFW (kg)", f"{rp['zfw']:,}", f"{rf['zfw']:,}", f"{rf['zfw'] - rp['zfw']:+,}"),
        ("TOW (kg)", f"{rp['tow']:,}", f"{rf['tow']:,}", f"{rf['tow'] - rp['tow']:+,}"),
        ("CG au décollage (m)", f"{rp['tow_cg']:.2f}", f"{rf['tow_cg']:.2f}", f"{rf['tow_cg'] - rp['tow_cg']:+.2f}"),
    ]
    st.dataframe(pd.DataFrame(rows, columns=["Paramètre", "Prévu", "Final", "Écart"]),
                 hide_index=True, use_container_width=True)


# ── Onglet « Nouveau vol » ───────────────────────────────────────────────────
def render_flight_tab(ac: dict, selected_ac: str, airports: dict, blocked: bool, missing: list, user_info: dict):
    ref = st.session_state.referentiel
    st.subheader("📋 Plan de vol — Masse & Centrage")

    # ── 1. Vol ────────────────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        flight_number = st.text_input("N° de vol", value="AF1234", placeholder="AF1234")
        origin = st.selectbox("🛫 Départ", list(airports.keys()), key="origin")
    with col_b:
        flight_date = st.date_input("Date du vol", value=datetime.now())
        dest = st.selectbox("🛬 Arrivée", list(airports.keys()), index=min(1, len(airports) - 1), key="dest")
    with col_c:
        flight_time = st.time_input("Heure départ (UTC)", value=datetime.now().time())
        alternate = st.selectbox("⚡ Alternate", list(airports.keys()), index=min(2, len(airports) - 1), key="alt")
    registration = st.text_input("Immatriculation de l'avion", value="", key="registration",
                                 placeholder="ex. F-GKXA", max_chars=10).strip().upper()

    orig_data, dest_data = airports[origin], airports[dest]
    dist_nm = haversine(orig_data["lat"], orig_data["lon"], dest_data["lat"], dest_data["lon"])
    st.markdown(f"""
    <div style="display:flex;gap:12px;margin:1rem 0;flex-wrap:wrap">
        <div class="metric-card" style="flex:1;min-width:140px">
            <div class="label">Distance</div><div class="value">{dist_nm:.0f}</div><div class="unit">NM</div>
        </div>
        <div class="metric-card" style="flex:1;min-width:140px">
            <div class="label">Altitude dest.</div><div class="value">{dest_data['elev_ft']:,}</div><div class="unit">ft</div>
        </div>
        <div class="metric-card" style="flex:1;min-width:140px">
            <div class="label">Piste dest.</div><div class="value">{dest_data['rwy_length_m']:,}</div><div class="unit">m</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)

    # ── 2. Passagers ──────────────────────────────────────────────────────
    pax = render_pax_panel(ac, selected_ac, ref)
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)

    if blocked:
        blocked_message(missing)
        return

    # ── 3. Fret, courrier, bagages par soute ──────────────────────────────
    comps = ac.get("cargo_comps") or []
    st.markdown("**📦 Fret et courrier par soute**")
    if ac.get("loading_mode") == "uld":
        st.info("Chargement en ULD non géré dans cette version : saisie simplifiée par soute (masse totale).")
    cargo_w, mail_w = {}, {}
    if comps:
        for i, (col, comp) in enumerate(zip(st.columns(len(comps)), comps)):
            with col:
                st.markdown(f"**{comp['name']}**")
                cargo_w[comp["name"]] = int(st.number_input("Fret (kg)", 0, int(comp["max_kg"]), 0, step=50,
                                                            key=f"cargo_{selected_ac}_{i}"))
                mail_w[comp["name"]] = int(st.number_input("Courrier (kg)", 0, int(comp["max_kg"]), 0, step=10,
                                                           key=f"mail_{selected_ac}_{i}"))
                st.caption(f"Capacité : {int(comp['max_kg']):,} kg | Bras : {comp['arm_m']} m")

    st.markdown("**🧳 Bagages en soute**")
    bag_mode = st.radio("Mode de détermination", ["Masse forfaitaire", "Pesée réelle"], horizontal=True,
                        key=f"bag_mode_{selected_ac}")
    bag_pieces, bag_std, bag_ft_label = 0, None, ""
    if bag_mode == "Masse forfaitaire":
        b1, b2, b3 = st.columns(3)
        bag_pieces = int(b1.number_input("Nombre de bagages", 0, 3000, 0, key=f"bag_n_{selected_ac}"))
        ft_labels = [lab for _, lab in BAG_FLIGHT_TYPES]
        bag_ft_label = b2.selectbox("Type de vol", ft_labels, index=1, key=f"bag_ft_{selected_ac}")
        ft_key = dict((lab, k) for k, lab in BAG_FLIGHT_TYPES)[bag_ft_label]
        bag_std = ref["bag_masses"][ft_key]["value"]
        b3.metric("Masse par bagage", f"{bag_std} kg")
        bag_total = bag_pieces * bag_std
    else:
        bag_total = int(st.number_input("Masse réelle des bagages (kg)", 0, 100000, 0, key=f"bag_kg_{selected_ac}"))

    used = {c["name"]: cargo_w.get(c["name"], 0) + mail_w.get(c["name"], 0) for c in comps}
    alloc, alloc_mode, unplaced = allocate_bags(comps, bag_total, used)
    sig = zlib.crc32(repr(sorted(used.items())).encode())
    bag_w = dict(alloc)
    if comps and bag_total > 0:
        with st.expander("Répartition des bagages par soute (priorité de chargement, ajustable)"):
            if alloc_mode == "priorité":
                note = _meta(ac)["source"].get("bag_rank", "")
                st.caption(f"Priorité de chargement : {bag_priority_text(comps)}"
                           + (f" (source : {note})" if note else "") + " Modifiable dans « Données aéronef ».")
            else:
                st.warning("Priorité de chargement non renseignée pour ce type : répartition proportionnelle à la "
                           "capacité disponible. À renseigner dans « Données aéronef ».")
            for i, (col, comp) in enumerate(zip(st.columns(len(comps)), comps)):
                with col:
                    bag_w[comp["name"]] = int(st.number_input(
                        f"{comp['name']} (kg)", 0, int(comp["max_kg"]), int(alloc[comp["name"]]),
                        key=f"bagz_{selected_ac}_{i}_{int(bag_total)}_{sig}"))
            if sum(bag_w.values()) != int(bag_total):
                st.warning(f"La somme des soutes ({sum(bag_w.values())} kg) diffère de la masse de bagages "
                           f"({int(bag_total)} kg).")
    if unplaced > 0:
        st.error(f"Capacité des soutes dépassée de {unplaced} kg : les bagages ne peuvent pas tous être chargés.")
    comp_loads = {c["name"]: cargo_w.get(c["name"], 0) + mail_w.get(c["name"], 0) + bag_w.get(c["name"], 0)
                  for c in comps}
    for c in comps:
        if comp_loads[c["name"]] > c["max_kg"]:
            st.error(f"Soute {c['name']} : {comp_loads[c['name']]:,} kg chargés pour une capacité de "
                     f"{int(c['max_kg']):,} kg.")
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)

    # ── 4. Carburant (côté trafic) ────────────────────────────────────────
    st.markdown("**⛽ Carburant (côté trafic)**")
    mfuel = int(ac["mfuel"])
    trip_default = max(500, min(int(dist_nm / (ac["perf"].get("cruise_tas_kt") or 450) * ac["perf"]["fuel_flow_cruise"]),
                                mfuel - 1000))
    f1, f2, f3, f4 = st.columns(4)
    bloc = int(f1.number_input("Bloc fuel (kg)", 0, mfuel, min(int(mfuel * 0.40), mfuel), step=100,
                               key=f"fuel_bloc_{selected_ac}"))
    taxi = int(f2.number_input("Taxi fuel (kg)", 0, mfuel, min(300, mfuel), step=50, key=f"fuel_taxi_{selected_ac}"))
    trip = int(f3.number_input("Trip fuel (kg)", 0, mfuel, min(trip_default, mfuel), step=100,
                               key=f"fuel_trip_{selected_ac}"))
    tof = max(bloc - taxi, 0)
    f4.metric("Carburant au décollage", f"{tof:,} kg", help="Bloc fuel − taxi fuel")
    if taxi >= bloc and bloc > 0:
        st.error("Le taxi fuel est supérieur ou égal au bloc fuel.")
    if trip > tof:
        st.error(f"Le trip fuel ({trip:,} kg) dépasse le carburant au décollage ({tof:,} kg).")
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)

    # ── 5. Calculs ────────────────────────────────────────────────────────
    pax_weights = zone_weights_from_counts(ac, pax["active_counts"], pax["masses"], pax["zone_counts"])
    result = compute_mc(ac, pax_weights, comp_loads, tof)
    lw = result["tow"] - trip

    zfw_ok = result["zfw"] <= ac["max_zfw_kg"]
    tow_ok = result["tow"] <= ac["max_tow_kg"]
    lw_ok = lw <= ac["max_lw_kg"]
    cg_ok = ac["cg_min_m"] <= result["tow_cg"] <= ac["cg_max_m"]
    stock_ok = unplaced == 0 and all(comp_loads[c["name"]] <= c["max_kg"] for c in comps)

    st.markdown("### ⚖ Résultats Masse & Centrage")
    metrics = [
        ("ZFW", result["zfw"], "kg", f"Max {ac['max_zfw_kg']:,} kg · marge {ac['max_zfw_kg'] - result['zfw']:,} kg", zfw_ok),
        ("TOW", result["tow"], "kg", f"Max {ac['max_tow_kg']:,} kg · marge {ac['max_tow_kg'] - result['tow']:,} kg", tow_ok),
        ("LW", lw, "kg", f"Max {ac['max_lw_kg']:,} kg · marge {ac['max_lw_kg'] - lw:,} kg", lw_ok),
        ("CG TOW", result["tow_cg"], "m", f"FWD {ac['cg_min_m']} m / AFT {ac['cg_max_m']} m", cg_ok),
    ]
    for col, (label, val, unit, limit, ok) in zip(st.columns(4), metrics):
        with col:
            color = "#00FF88" if ok else "#FF4444"
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">{label}</div>
                <div class="value" style="color:{color}">{val:,.1f}</div>
                <div class="unit">{unit}</div>
                <div style="font-size:0.68rem;color:#556688;margin-top:4px">{limit}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
    render_pax_comparison(ac, pax, comp_loads, tof)
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
    st.plotly_chart(plot_cg_envelope(ac, result, min(trip, tof)), use_container_width=True)

    # ── 6. Récapitulatif pour le commandant de bord (en fin de page) ─────
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
    st.markdown("### 🧑‍✈️ Récapitulatif avion et commandant de bord")
    r1, r2, r3 = st.columns(3)
    r1.metric("Immatriculation", registration or "—")
    r2.metric("Type", ac.get("type") or "—")
    cdb_name = r3.text_input("Commandant de bord (nom)", key="cdb_name")
    recap = pd.DataFrame([
        ("ZFW", f"{result['zfw']:,}", f"{ac['max_zfw_kg']:,}", f"{ac['max_zfw_kg'] - result['zfw']:,}", "OK" if zfw_ok else "DÉPASSÉ"),
        ("TOW", f"{result['tow']:,}", f"{ac['max_tow_kg']:,}", f"{ac['max_tow_kg'] - result['tow']:,}", "OK" if tow_ok else "DÉPASSÉ"),
        ("LW", f"{lw:,}", f"{ac['max_lw_kg']:,}", f"{ac['max_lw_kg'] - lw:,}", "OK" if lw_ok else "DÉPASSÉ"),
    ], columns=["Masse (kg)", "Calculée", "Maximum", "Marge", "État"])
    st.dataframe(recap, hide_index=True, use_container_width=True)
    payload = result["pax_total_kg"] + sum(comp_loads.values())
    st.caption(f"Charge payante : {payload:,.0f} kg (passagers {result['pax_total_kg']:,.0f} kg, "
               f"bagages {bag_total:,} kg, fret {sum(cargo_w.values()):,} kg, courrier {sum(mail_w.values()):,} kg). "
               f"Carburant : bloc {bloc:,} kg, taxi {taxi:,} kg, trip {trip:,} kg, décollage {tof:,} kg.")

    # ── Synthèse du vol (alimente le PDF et l'historique) ─────────────────
    origin_txt, aircraft_certified = origin_summary(ac)
    fs = {
        "flight_number": flight_number, "registration": registration, "aircraft": selected_ac,
        "type": ac.get("type", ""), "origin": origin, "dest": dest, "alternate": alternate,
        "dist_nm": dist_nm,
        "datetime": f"{flight_date.strftime('%d/%m/%Y')} {flight_time.strftime('%H:%M')} UTC",
        "ls_status": pax["status"].upper(), "cdb_name": cdb_name.strip(),
        "prepared_by": user_info.get("nom", ""),
        "pax_counts": dict(pax["active_counts"]), "pax_masses": dict(pax["masses"]),
        "seated": pax["seated"], "pax_max": pax["max_seats"],
        "pax_prevus": pax["seated_prev"], "pax_final": pax["seated_final"],
        "pax_mass_kg": result["pax_total_kg"],
        "bag_mode": bag_mode, "bag_pieces": bag_pieces, "bag_std": bag_std, "bag_ft": bag_ft_label,
        "bag_total": bag_total, "cargo_total": sum(cargo_w.values()), "mail_total": sum(mail_w.values()),
        "payload": payload,
        "comps": [{"name": c["name"], "bag": bag_w.get(c["name"], 0), "cargo": cargo_w.get(c["name"], 0),
                   "mail": mail_w.get(c["name"], 0), "total": comp_loads[c["name"]], "max": int(c["max_kg"])}
                  for c in comps],
        "fuel": {"bloc": bloc, "taxi": taxi, "trip": trip, "tof": tof},
        "oew": ac["oew_kg"], "crew_kg": ac.get("crew_kg", 0), "dow": ac["oew_kg"] + ac.get("crew_kg", 0),
        "zfw": result["zfw"], "tow": result["tow"], "lw": lw,
        "max_zfw": ac["max_zfw_kg"], "max_tow": ac["max_tow_kg"], "max_lw": ac["max_lw_kg"],
        "zfw_ok": zfw_ok, "tow_ok": tow_ok, "lw_ok": lw_ok, "cg_ok": cg_ok, "stock_ok": stock_ok,
        "tow_cg": result["tow_cg"], "zfw_cg": result["zfw_cg"], "tow_mac": result["tow_mac"],
        "zfw_mac": result["zfw_mac"], "cg_min": ac["cg_min_m"], "cg_max": ac["cg_max_m"],
        "status_ok": all([zfw_ok, tow_ok, lw_ok, cg_ok, stock_ok]),
        "origin_text": origin_txt, "referentiel_text": referentiel_label(ref),
        "data_certified": bool(aircraft_certified and ref_acceptable(ref)),
    }
    st.session_state.flight_summary = fs
    st.session_state.mc_result = result
    st.session_state.pax_info = pax
    st.session_state.dist_nm = dist_nm
    st.session_state.ac = ac
    st.session_state.lw = lw
    st.session_state.trip_fuel = trip
    st.session_state.fuel_in = dict(fs["fuel"])
    st.session_state.flight_info = {"flight_number": flight_number, "origin": origin, "dest": dest,
                                    "alternate": alternate, "aircraft": selected_ac,
                                    "datetime": fs["datetime"], "dist_nm": dist_nm}

    # ── Sauvegarde du vol ────────────────────────────────────────────────
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
    col_save1, col_save2 = st.columns([2, 1])
    with col_save1:
        if not fs["status_ok"]:
            st.warning("⚠ Certaines limites sont dépassées. Corrigez avant de sauvegarder.")
    with col_save2:
        if st.button("💾 Sauvegarder le vol", use_container_width=True):
            record = dict(fs)
            record["fuel_plan"] = st.session_state.get("fuel_plan", {})
            record["vspeeds"] = st.session_state.get("vspeeds", {})
            st.session_state.current_flight = record
            save_flight(record)
            st.success(f"✅ Vol {flight_number} sauvegardé dans l'historique.")


# ── Onglet « Export PDF » ────────────────────────────────────────────────────
def render_pdf_tab(blocked: bool, missing: list):
    st.subheader("📄 Export Load & Trim Sheet officielle PDF")
    if blocked:
        blocked_message(missing)
        return
    fs = st.session_state.get("flight_summary")
    if not fs:
        st.info("Renseignez d'abord l'onglet « Nouveau vol ».")
        return
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Vol", fs["flight_number"] or "—")
    p2.metric("Immatriculation", fs["registration"] or "—")
    p3.metric("Statut", fs["ls_status"].capitalize())
    p4.metric("Contrôle des limites", "OK" if fs["status_ok"] else "À corriger")
    if not fs["data_certified"]:
        st.warning("Les données ne sont pas toutes issues de la compagnie : le PDF portera la mention "
                   "« DONNÉES NON CERTIFIÉES ».")
    include_speeds = st.checkbox("Inclure les vitesses (indicatives) dans le PDF", value=False, key="pdf_speeds")
    if include_speeds:
        st.caption("Les vitesses résultent d'une formule approchée, et non des tables de l'AFM : elles sont "
                   "indiquées comme telles sur le document.")
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
    if st.button("📄 GÉNÉRER LA LOAD & TRIM SHEET PDF", use_container_width=True):
        data = dict(fs)
        data["vspeeds"] = st.session_state.get("vspeeds", {})
        with st.spinner("⚙ Génération du PDF en cours..."):
            pdf_bytes = generate_pdf(data, include_speeds)
        fname = f"AETHERDISPATCH_{(fs['flight_number'] or 'VOL')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        st.download_button(label="⬇ Télécharger la Load & Trim Sheet", data=pdf_bytes, file_name=fname,
                           mime="application/pdf", use_container_width=True)
        st.success(f"✅ PDF généré : {fname}")


# ── Édition des données aéronef ──────────────────────────────────────────────
def _num(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
        f = float(v)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else f


def _txt(v) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    return str(v).strip()


def scalar_df(ac: dict) -> pd.DataFrame:
    meta = _meta(ac)
    rows = []
    for key, label, unit, req in ALL_FIELDS:
        rows.append({"Clé": key, "Paramètre": label + (" *" if req else ""), "Valeur": get_field(ac, key),
                     "Unité": unit, "Statut": STATUS_LABELS[field_status(ac, key)],
                     "Source / commentaire": meta["source"].get(key, "")})
    df = pd.DataFrame(rows)
    df["Valeur"] = pd.to_numeric(df["Valeur"], errors="coerce")
    return df.set_index("Clé")


def apply_scalar_edits(ac: dict, edited: pd.DataFrame) -> int:
    """Applique le tableau édité. Une valeur modifiée passe en « Compagnie » (sauf statut choisi par l'utilisateur)."""
    meta, changed = _meta(ac), 0
    for key, row in edited.iterrows():
        new_v, old_v = _num(row["Valeur"]), get_field(ac, key)
        old_status = field_status(ac, key)
        chosen = LABEL_TO_STATUS.get(row.get("Statut"), old_status)
        src, old_src = _txt(row.get("Source / commentaire")), meta["source"].get(key, "")
        if new_v is None:
            status = "a_renseigner"
        elif new_v != old_v:
            status = chosen if chosen not in (old_status, "a_renseigner") else "compagnie"
        else:
            status = chosen if chosen != "a_renseigner" else old_status
        if (new_v, status, src) != (old_v, old_status, old_src):
            changed += 1
        set_field(ac, key, new_v)
        meta["status"][key] = status
        meta["source"][key] = src
    return changed


RANK_COL = "Rang bagages (1 = premier)"


def rows_df(rows: list, name_col: str, cap_col: str, cap_key: str, with_rank: bool = False) -> pd.DataFrame:
    data = []
    for r in rows:
        d = {name_col: r.get("name"), "Bras (m)": r.get("arm_m"), cap_col: r.get(cap_key),
             "Statut": STATUS_LABELS.get(r.get("status") or "estime", "Estimé"),
             "Source / commentaire": r.get("source", "")}
        if with_rank:
            d[RANK_COL] = r.get("bag_rank")
        data.append(d)
    cols = [name_col, "Bras (m)", cap_col] + ([RANK_COL] if with_rank else []) + ["Statut", "Source / commentaire"]
    df = pd.DataFrame(data, columns=cols)
    for c in ["Bras (m)", cap_col] + ([RANK_COL] if with_rank else []):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def apply_rows_edits(ac: dict, list_key: str, df: pd.DataFrame, name_col: str, cap_col: str, cap_key: str,
                     with_rank: bool = False) -> int:
    old_by_name = {r.get("name"): r for r in (ac.get(list_key) or [])}
    new_rows, changed, rank_changed = [], 0, False
    for rec in df.to_dict("records"):
        name = _txt(rec.get(name_col))
        if not name:
            continue
        arm, cap = _num(rec.get("Bras (m)")), _num(rec.get(cap_col))
        chosen = LABEL_TO_STATUS.get(rec.get("Statut"))
        src = _txt(rec.get("Source / commentaire"))
        old = old_by_name.get(name)
        rank = old.get("bag_rank") if old else None
        if with_rank:
            rk = _num(rec.get(RANK_COL))
            rank = int(rk) if rk is not None else None
        if old is None:
            status = "a_renseigner" if arm is None else (chosen if chosen not in (None, "a_renseigner") else "compagnie")
            changed += 1
            rank_changed = rank_changed or rank is not None
        else:
            old_status = old.get("status") or "estime"
            if arm is None:
                status = "a_renseigner"
            elif (arm, cap) != (old.get("arm_m"), old.get(cap_key)):
                status = chosen if chosen not in (None, old_status, "a_renseigner") else "compagnie"
            else:
                status = chosen if chosen not in (None, "a_renseigner") else old_status
            if rank != old.get("bag_rank"):
                rank_changed, changed = True, changed + 1
            if (arm, cap, status, src) != (old.get("arm_m"), old.get(cap_key), old_status, old.get("source", "")):
                changed += 1
        row = {"name": name, "arm_m": arm, cap_key: cap, "status": status, "source": src}
        if with_rank or (old is not None and "bag_rank" in old):
            row["bag_rank"] = rank
        new_rows.append(row)
    changed += len(set(old_by_name) - {r["name"] for r in new_rows})
    ac[list_key] = new_rows
    if rank_changed:
        m = _meta(ac)
        m["status"]["bag_rank"] = "compagnie"
        m["source"]["bag_rank"] = "Saisi dans l'application (statut Compagnie)"
    return changed


# ── Référentiel compagnie : tableaux, modèle Excel, import ───────────────────
def kv_df(items: dict) -> pd.DataFrame:
    rows = [{"Clé": k, "Paramètre": it["label"], "Valeur (kg)": it["value"],
             "Statut": STATUS_LABELS[it["status"]], "Source / commentaire": it["source"]} for k, it in items.items()]
    df = pd.DataFrame(rows)
    df["Valeur (kg)"] = pd.to_numeric(df["Valeur (kg)"], errors="coerce")
    return df.set_index("Clé")


def apply_kv_edits(items: dict, edited: pd.DataFrame) -> int:
    """Applique les masses éditées ; une valeur modifiée passe en « Compagnie » sauf statut choisi."""
    changed = 0
    for key, row in edited.iterrows():
        it, new_v = items[key], _num(row["Valeur (kg)"])
        if new_v is None:
            continue
        chosen = LABEL_TO_STATUS.get(row.get("Statut"), it["status"])
        if chosen == "a_renseigner":
            chosen = it["status"]
        src = _txt(row.get("Source / commentaire"))
        before = (it["value"], it["status"], it["source"])
        status = (chosen if chosen != it["status"] else "compagnie") if new_v != it["value"] else chosen
        it["value"], it["status"], it["source"] = new_v, status, src
        changed += int(before != (it["value"], it["status"], it["source"]))
    return changed


REF_ROW_LABELS = [
    ("id.organisme", "Compagnie ou prestataire"), ("id.document", "Document de référence (AHM, GOM, MANEX)"),
    ("id.version", "Version / édition"), ("id.date_application", "Date d'application"),
    ("pax.male", "Masse standard - Hommes (kg)"), ("pax.female", "Masse standard - Femmes (kg)"),
    ("pax.child", "Masse standard - Enfants (kg)"), ("pax.infant", "Masse standard - Bébés (kg)"),
    ("bag.domestic", "Masse bagage - Vol intérieur (kg)"), ("bag.other", "Masse bagage - Autres vols (kg)"),
    ("bag.intercontinental", "Masse bagage - Vol intercontinental (kg)"),
]
RANK_SHEET_COL = "Rang bagages (1 = premier)"


def build_referentiel_template(db: dict, ref: dict):
    """Modèle Excel prérempli avec les valeurs actuelles. None si openpyxl n'est pas disponible."""
    try:
        import openpyxl  # noqa: F401
    except Exception:
        return None
    rows = []
    for key, label in REF_ROW_LABELS:
        grp, k = key.split(".")
        if grp == "id":
            rows.append({"Paramètre": label, "Valeur": ref["identification"].get(k, ""), "Statut": "",
                         "Source / commentaire": ""})
        else:
            it = ref["pax_masses" if grp == "pax" else "bag_masses"][k]
            rows.append({"Paramètre": label, "Valeur": it["value"], "Statut": STATUS_LABELS[it["status"]],
                         "Source / commentaire": it["source"]})
    prios = [{"Type d'aéronef": n, "Soute": c["name"], RANK_SHEET_COL: c.get("bag_rank")}
             for n, a in db.items() for c in (a.get("cargo_comps") or [])]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame(rows).to_excel(xw, sheet_name="Référentiel", index=False)
        pd.DataFrame(prios, columns=["Type d'aéronef", "Soute", RANK_SHEET_COL]).to_excel(
            xw, sheet_name="Priorités bagages", index=False)
        for ws, widths in ((xw.sheets["Référentiel"], (46, 34, 16, 90)), (xw.sheets["Priorités bagages"], (30, 18, 26))):
            for col, w in zip("ABCD", widths):
                ws.column_dimensions[col].width = w
    return buf.getvalue()


def apply_referentiel_xlsx(raw: bytes, db: dict, ref: dict):
    """Applique un fichier de référentiel. Retourne (ok, message, nouveau_référentiel, nouvelle_base, modifications)."""
    try:
        sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None)
    except Exception:
        return False, "Fichier Excel illisible.", ref, db, 0
    if "Référentiel" not in sheets:
        return False, "La feuille « Référentiel » est absente : utilisez le modèle fourni.", ref, db, 0
    new_ref, new_db, changed = copy.deepcopy(ref), copy.deepcopy(db), 0
    by_label = {label: key for key, label in REF_ROW_LABELS}
    for _, r in sheets["Référentiel"].iterrows():
        key = by_label.get(_txt(r.get("Paramètre")))
        if not key:
            continue
        grp, k = key.split(".")
        if grp == "id":
            t = _txt(r.get("Valeur"))
            if t != new_ref["identification"].get(k, ""):
                new_ref["identification"][k], changed = t, changed + 1
            continue
        it, v = new_ref["pax_masses" if grp == "pax" else "bag_masses"][k], _num(r.get("Valeur"))
        if v is None:
            continue
        chosen = LABEL_TO_STATUS.get(_txt(r.get("Statut")))
        src = _txt(r.get("Source / commentaire"))
        if v != it["value"]:
            it["value"] = v
            it["status"] = chosen if chosen not in (None, it["status"], "a_renseigner") else "compagnie"
            changed += 1
        elif chosen not in (None, "a_renseigner") and chosen != it["status"]:
            it["status"], changed = chosen, changed + 1
        if src and src != it["source"]:
            it["source"] = src
    label = referentiel_label(new_ref)
    if "Priorités bagages" in sheets:
        for _, r in sheets["Priorités bagages"].iterrows():
            ac = new_db.get(_txt(r.get("Type d'aéronef")))
            if not ac:
                continue
            rk = _num(r.get(RANK_SHEET_COL))
            rk = int(rk) if rk is not None else None
            for c in ac.get("cargo_comps") or []:
                if c.get("name") == _txt(r.get("Soute")) and rk != c.get("bag_rank"):
                    c["bag_rank"], changed = rk, changed + 1
                    m = _meta(ac)
                    m["status"]["bag_rank"] = "compagnie"
                    m["source"]["bag_rank"] = f"Référentiel importé : {label}"
    return True, f"{changed} modification(s) appliquée(s).", new_ref, new_db, changed


REF_DOCS_MAX_BYTES = 25 * 1024 * 1024   # limite totale des documents déposés pendant une session


def render_referentiel_section(can_edit: bool, ver: int, db: dict):
    ref = st.session_state.referentiel
    with st.expander("📚 Référentiel compagnie (AHM / GOM) : masses standard et bagages", expanded=False):
        st.caption("Ces valeurs pilotent le calcul des passagers et des bagages. Elles sont réglementaires par défaut "
                   "(règlement (UE) n° 965/2012) ; remplacez-les par celles de l'AHM ou du GOM applicables, en "
                   "indiquant la source (chapitre ou section). Les documents eux-mêmes ne sont pas conservés par "
                   "l'application : seules les valeurs saisies le sont.")
        ident = ref["identification"]
        c1, c2 = st.columns(2)
        organisme = c1.text_input("Compagnie ou prestataire", ident["organisme"], key=f"ref_org_{ver}", disabled=not can_edit)
        document = c2.text_input("Document de référence (AHM, GOM, MANEX)", ident["document"], key=f"ref_doc_{ver}",
                                 disabled=not can_edit)
        c3, c4 = st.columns(2)
        version = c3.text_input("Version / édition", ident["version"], key=f"ref_ver_{ver}", disabled=not can_edit)
        date_app = c4.text_input("Date d'application", ident["date_application"], key=f"ref_date_{ver}",
                                 disabled=not can_edit)
        opts = list(STATUS_LABELS.values())
        cfg = {"Valeur (kg)": st.column_config.NumberColumn("Valeur (kg)", min_value=0),
               "Statut": st.column_config.SelectboxColumn("Statut", options=opts)}
        st.markdown("**Masses standard des passagers**")
        pdf_df = kv_df(ref["pax_masses"])
        st.markdown("**Masses forfaitaires de bagage en soute**")
        bdf = kv_df(ref["bag_masses"])
        if can_edit:
            ed_p = st.data_editor(pdf_df, hide_index=True, use_container_width=True, key=f"ref_pax_{ver}",
                                  disabled=["Paramètre"], num_rows="fixed", column_config=cfg)
            ed_b = st.data_editor(bdf, hide_index=True, use_container_width=True, key=f"ref_bag_{ver}",
                                  disabled=["Paramètre"], num_rows="fixed", column_config=cfg)
            if st.button("💾 Enregistrer le référentiel", key=f"btn_ref_{ver}", use_container_width=True):
                changed = 0
                new_ident = {"organisme": organisme.strip(), "document": document.strip(),
                             "version": version.strip(), "date_application": date_app.strip()}
                if new_ident != ident:
                    ref["identification"] = new_ident
                    changed += 1
                changed += apply_kv_edits(ref["pax_masses"], ed_p) + apply_kv_edits(ref["bag_masses"], ed_b)
                if changed:
                    st.session_state.dirty = True
                    st.session_state.ed_version = ver + 1
                    st.session_state["_flash"] = (f"Référentiel enregistré ({changed} modification(s)). "
                                                  "Exportez votre profil pour le conserver.")
                    st.rerun()
                else:
                    st.info("Aucune modification à enregistrer.")
        else:
            st.dataframe(pdf_df, hide_index=True, use_container_width=True)
            st.dataframe(bdf, hide_index=True, use_container_width=True)

        st.markdown("**Fichier de référentiel (Excel)**")
        st.caption("Téléchargez le modèle, complétez-le d'après votre GOM (masses, priorités de chargement des bagages "
                   "par type d'avion), puis importez-le. Il ne contient aucun document de la compagnie.")
        tpl = build_referentiel_template(db, ref)
        if tpl is None:
            st.info("L'import et l'export Excel nécessitent le module openpyxl (à ajouter à requirements.txt).")
        else:
            st.download_button("⬇ Télécharger le modèle Excel (valeurs actuelles)", data=tpl,
                               file_name="referentiel_compagnie_modele.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key=f"btn_tpl_{ver}")
            if can_edit:
                up = st.file_uploader("Importer un référentiel rempli (.xlsx)", type=["xlsx"], key=f"ref_up_{ver}")
                if st.button("Appliquer ce référentiel", key=f"btn_apply_ref_{ver}", disabled=up is None):
                    ok, msg, new_ref, new_db, n = apply_referentiel_xlsx(up.getvalue(), db, ref)
                    if ok:
                        st.session_state.referentiel = new_ref
                        st.session_state.db = new_db
                        st.session_state.dirty = st.session_state.get("dirty", False) or n > 0
                        st.session_state.ed_version = ver + 1
                        st.session_state["_flash"] = f"Référentiel appliqué : {msg}"
                        st.rerun()
                    else:
                        st.error(msg)

        st.markdown("---")
        st.markdown("**Documents de référence (facultatif, consultation pendant la session)**")
        st.warning("Ces fichiers restent uniquement en mémoire pendant votre session : ils ne sont ni enregistrés, "
                   "ni inclus dans le profil, et disparaissent à la déconnexion ou au redémarrage de l'application. "
                   "Ne déposez que des documents que vous avez le droit de confier à ce service d'hébergement : "
                   "le GOM est un document interne de la compagnie, et l'AHM de l'IATA est une publication sous licence.")
        docs = st.session_state.setdefault("ref_docs", {})
        dv = st.session_state.get("ref_docs_ver", 0)
        if can_edit:
            ups = st.file_uploader("Déposer un ou plusieurs documents (PDF, Word, Excel ou texte)",
                                   type=["pdf", "docx", "xlsx", "txt"], accept_multiple_files=True,
                                   key=f"ref_docs_up_{dv}")
            for f in (ups or []):
                if f.name in docs:
                    continue
                if sum(len(b) for b in docs.values()) + f.size > REF_DOCS_MAX_BYTES:
                    st.error(f"« {f.name} » dépasse la limite totale de {REF_DOCS_MAX_BYTES // (1024 * 1024)} Mo "
                             "pour les documents de la session.")
                else:
                    docs[f.name] = f.getvalue()
        if not docs:
            st.caption("Aucun document déposé.")
        for name, data in list(docs.items()):
            c1, c2, c3 = st.columns([4, 1.4, 1])
            c1.markdown(f"{name} ({len(data) / (1024 * 1024):.1f} Mo)")
            c2.download_button("Télécharger", data=data, file_name=name, key=f"dl_doc_{dv}_{name}")
            if can_edit and c3.button("Retirer", key=f"rm_doc_{dv}_{name}"):
                del docs[name]
                st.session_state["ref_docs_ver"] = dv + 1
                st.rerun()


def _register_type(new_name: str, rec: dict):
    name = (new_name or "").strip()
    if not name:
        st.error("Saisissez un nom pour le type.")
        return
    if name in st.session_state.db:
        st.error("Ce nom de type existe déjà.")
        return
    st.session_state.db[name] = rec
    st.session_state.dirty = True
    st.session_state["_pending_select"] = name
    st.session_state["_flash"] = f"Type « {name} » créé. Renseignez ses données ci-dessous."
    st.session_state.ed_version = st.session_state.get("ed_version", 0) + 1
    st.rerun()


def render_data_tab(selected_ac: str, can_edit: bool, user_info: dict):
    db = st.session_state.db
    ac = db[selected_ac]
    ver = st.session_state.get("ed_version", 0)

    flash = st.session_state.pop("_flash", None)
    if flash:
        st.success(flash)

    st.subheader("🛠 Données aéronef — entièrement modifiables")
    st.caption("Chaque valeur porte un statut d'origine : Constructeur, Estimé, Compagnie ou À renseigner. "
               "Une valeur que vous modifiez passe automatiquement en « Compagnie ». "
               "Le PDF indique l'origine des données utilisées.")
    if not can_edit:
        st.info("Lecture seule : la modification des données est réservée aux profils admin et dispatcher. "
                "Vous pouvez en revanche importer le profil compagnie.")

    # ── Profil compagnie ──────────────────────────────────────────────────
    with st.expander("📁 Profil compagnie : importer / exporter", expanded=True):
        info = st.session_state.get("profile_info")
        st.markdown("Les modifications sont conservées pendant la session. Pour les retrouver après un redémarrage "
                    "de l'application : **Exporter mon profil**, puis **Importer mon profil** au prochain démarrage.")
        up = st.file_uploader("Importer mon profil (fichier .json)", type=["json"], key=f"profile_up_{ver}")
        if st.button("Charger ce profil", key="btn_load_profile", disabled=up is None):
            ok, msg, new_db, new_info = import_profile_bytes(up.getvalue())
            if ok:
                st.session_state.db = new_db
                st.session_state.profile_info = new_info
                st.session_state.referentiel = normalize_referentiel(new_info.get("referentiel"))
                st.session_state.dirty = False
                st.session_state.ed_version = ver + 1
                st.session_state["_flash"] = f"Profil « {new_info['name']} » chargé : {msg}"
                st.rerun()
            else:
                st.error(msg)
        if can_edit:
            pname = st.text_input("Nom du profil à exporter", value=(info or {}).get("name", "Profil compagnie"),
                                  key="profile_name")
            st.download_button("⬇ Exporter mon profil",
                               data=export_profile_bytes(db, pname, user_info.get("nom", ""), st.session_state.referentiel),
                               file_name=f"profil_compagnie_{datetime.now().strftime('%Y%m%d')}.json",
                               mime="application/json", on_click=_mark_exported, key="btn_export_profile")
        else:
            st.caption("L'export du profil est réservé aux profils admin et dispatcher.")

    render_referentiel_section(can_edit, ver, db)

    # ── Gestion des types ─────────────────────────────────────────────────
    if can_edit:
        with st.expander("➕ Ajouter / dupliquer / supprimer un type"):
            new_name = st.text_input("Nom du type (ex. : Airbus A320-200 — Compagnie X)", key="new_type_name")
            b1, b2 = st.columns(2)
            if b1.button("Créer un type vide", key="btn_new_blank"):
                _register_type(new_name, new_blank_aircraft(new_name))
            if b2.button("Dupliquer le type actuel", key="btn_dup"):
                _register_type(new_name, copy.deepcopy(ac))
            confirm = st.checkbox(f"Confirmer la suppression de « {selected_ac} »", key=f"del_ok_{selected_ac}")
            if st.button("Supprimer le type actuel", key="btn_del", disabled=(not confirm or len(db) <= 1)):
                del st.session_state.db[selected_ac]
                st.session_state.dirty = True
                st.session_state["_flash"] = f"Type « {selected_ac} » supprimé."
                st.session_state.ed_version = ver + 1
                st.rerun()

    # ── Édition du type sélectionné ───────────────────────────────────────
    st.markdown("---")
    txt, certified = origin_summary(ac)
    st.markdown(f"**Type sélectionné : {selected_ac}** — origine des données critiques : {txt}")
    miss = missing_fields(ac)
    if miss:
        st.warning(f"{len(miss)} donnée(s) à renseigner pour activer les calculs : "
                   + ", ".join(miss[:6]) + (" …" if len(miss) > 6 else ""))
    else:
        st.success("Toutes les données nécessaires aux calculs sont renseignées.")
    st.caption("* donnée nécessaire aux calculs de masse, centrage, performances et carburant.")

    k = f"{selected_ac}_{ver}"
    c1, c2, c3 = st.columns(3)
    type_code = c1.text_input("Code du type", value=ac.get("type", ""), key=f"ed_type_{k}", disabled=not can_edit)
    typical = c2.text_input("Sièges typiques (texte libre)", value=ac.get("seats_typical", ""),
                            key=f"ed_typ_{k}", disabled=not can_edit)
    mode_lab = c3.selectbox("Mode de chargement", ["Vrac", "ULD (non géré)"],
                            index=0 if ac.get("loading_mode", "vrac") == "vrac" else 1,
                            key=f"ed_mode_{k}", disabled=not can_edit)

    st_opts = list(STATUS_LABELS.values())
    sdf = scalar_df(ac)
    zdf = rows_df(ac.get("pax_zones") or [], "Zone", "Capacité (pax)", "max_pax")
    cdf = rows_df(ac.get("cargo_comps") or [], "Soute", "Capacité (kg)", "max_kg", with_rank=True)

    row_cfg = {"Bras (m)": st.column_config.NumberColumn("Bras (m)", format="%.2f"),
               "Statut": st.column_config.SelectboxColumn("Statut", options=st_opts)}

    st.markdown("**Paramètres généraux, vitesses et performances**")
    if can_edit:
        edited_s = st.data_editor(sdf, hide_index=True, use_container_width=True, key=f"ed_scalar_{k}",
                                  disabled=["Paramètre", "Unité"], num_rows="fixed",
                                  column_config={"Valeur": st.column_config.NumberColumn("Valeur"),
                                                 "Statut": st.column_config.SelectboxColumn("Statut", options=st_opts)})
    else:
        st.dataframe(sdf, hide_index=True, use_container_width=True)

    st.markdown("**Zones passagers** (bras en mètres, capacité en passagers)")
    if can_edit:
        edited_z = st.data_editor(zdf, hide_index=True, use_container_width=True, key=f"ed_zones_{k}",
                                  num_rows="dynamic", column_config=row_cfg)
    else:
        st.dataframe(zdf, hide_index=True, use_container_width=True)

    cargo_cfg = {**row_cfg, RANK_COL: st.column_config.NumberColumn(RANK_COL, min_value=1, step=1, format="%d")}
    st.markdown("**Soutes** (bras en mètres, capacité en kg, rang de chargement des bagages)")
    if can_edit:
        edited_c = st.data_editor(cdf, hide_index=True, use_container_width=True, key=f"ed_cargo_{k}",
                                  num_rows="dynamic", column_config=cargo_cfg)
    else:
        st.dataframe(cdf, hide_index=True, use_container_width=True)

    if can_edit and st.button("💾 Enregistrer les modifications de ce type", key=f"btn_save_{k}",
                              use_container_width=True):
        changed = 0
        if type_code.strip() != (ac.get("type") or "") or typical.strip() != (ac.get("seats_typical") or ""):
            ac["type"], ac["seats_typical"] = type_code.strip(), typical.strip()
            changed += 1
        new_mode = "vrac" if mode_lab == "Vrac" else "uld"
        if new_mode != ac.get("loading_mode", "vrac"):
            ac["loading_mode"] = new_mode
            changed += 1
        changed += apply_scalar_edits(ac, edited_s)
        changed += apply_rows_edits(ac, "pax_zones", edited_z, "Zone", "Capacité (pax)", "max_pax")
        changed += apply_rows_edits(ac, "cargo_comps", edited_c, "Soute", "Capacité (kg)", "max_kg", with_rank=True)
        if changed:
            st.session_state.dirty = True
            st.session_state.ed_version = ver + 1
            st.session_state["_flash"] = (f"{changed} modification(s) enregistrée(s) pour « {selected_ac} ». "
                                          "Exportez votre profil pour les conserver.")
            st.rerun()
        else:
            st.info("Aucune modification à enregistrer.")


def blocked_message(missing: list):
    """Message affiché dans les onglets dont les calculs sont impossibles faute de données."""
    st.warning(f"Calcul indisponible pour ce type : {len(missing)} donnée(s) à renseigner "
               "(onglet « Données aéronef »).")
    with st.expander("Voir les données manquantes"):
        for m in missing:
            st.markdown(f"- {m}")



# =============================================================================
# APPLICATION PRINCIPALE
# =============================================================================

def main():
    # ── Chargement des données ────────────────────────────────────────────────
    users    = load_json("users.json")
    base_db  = load_json("compagnie_db.json")
    airports = load_json("airports_db.json")

    if not base_db:
        st.error("❌ compagnie_db.json introuvable. Vérifiez le répertoire de déploiement.")
        return

    # ── Authentification ──────────────────────────────────────────────────────
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        login_page(users)
        return

    user_info = st.session_state.user_info
    can_edit = user_info.get("role") in ("admin", "dispatcher")

    # Base de travail de la session : modifiable, non persistante (voir profil compagnie)
    if "db" not in st.session_state:
        st.session_state.db = {k: normalize_aircraft(v) for k, v in base_db.items()}
        st.session_state.profile_info = None
        st.session_state.dirty = False
    if "referentiel" not in st.session_state:
        st.session_state.referentiel = default_referentiel()
    db = st.session_state.db

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:12px;background:linear-gradient(135deg,#050510,#0A1428);
             border-radius:10px;border:1px solid rgba(0,191,255,0.2);margin-bottom:1rem">
            <div style="font-size:2.5rem">✈</div>
            <div style="font-weight:900;font-size:1.1rem;color:#00BFFF;letter-spacing:3px">AETHERDISPATCH</div>
            <div style="font-size:0.65rem;color:#556688;letter-spacing:1.5px;margin-top:2px">v4.0 | EG CONSEIL</div>
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
        pending = st.session_state.pop("_pending_select", None)
        if pending in db:
            st.session_state["sel_ac"] = pending
        if st.session_state.get("sel_ac") not in db:
            # À l'ouverture : premier type dont les données sont complètes (calculs disponibles)
            st.session_state["sel_ac"] = next((k for k, v in db.items() if not missing_fields(v)), list(db.keys())[0])
        selected_ac = st.selectbox("Type d'aéronef", list(db.keys()), key="sel_ac", label_visibility="collapsed")
        ac = db[selected_ac]

        st.markdown("---")
        dow_display = (ac["oew_kg"] + ac["crew_kg"]) if ac.get("oew_kg") is not None and ac.get("crew_kg") is not None else None
        _origin_txt, _ = origin_summary(ac)
        st.markdown(f"""
        <div style="font-size:0.72rem;color:#556688;line-height:1.8">
        <b style="color:#00BFFF">TYPE :</b> {ac.get('type') or '—'}<br>
        <b style="color:#00BFFF">DOW :</b> {fmt_num(dow_display, 'kg')}<br>
        <b style="color:#00BFFF">MTOW :</b> {fmt_num(ac.get('max_tow_kg'), 'kg')}<br>
        <b style="color:#00BFFF">MZFW :</b> {fmt_num(ac.get('max_zfw_kg'), 'kg')}<br>
        <b style="color:#00BFFF">MLW :</b> {fmt_num(ac.get('max_lw_kg'), 'kg')}<br>
        <b style="color:#00BFFF">SIÈGES MAX :</b> {fmt_num(ac.get('max_seats'))}<br>
        <b style="color:#00BFFF">CARBU MAX :</b> {fmt_num(ac.get('mfuel'), 'kg')}<br>
        <b style="color:#00BFFF">DONNÉES :</b> {_origin_txt}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔓 Déconnexion", use_container_width=True):
            for key in ["authenticated", "username", "user_info", "db", "profile_info", "dirty", "sel_ac", "ed_version", "pax_info", "referentiel", "flight_summary", "fuel_in", "ref_docs", "ref_docs_ver"]:
                st.session_state.pop(key, None)
            st.rerun()

    # ── Header principal ──────────────────────────────────────────────────────
    st.markdown("""
    <div class="aether-header">
        <h1>✈ AETHERDISPATCH</h1>
        <p>Agent IA handling aérien — Masse & Centrage · Performances · Météo · Carburant · Export PDF</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Bandeau d'état du profil compagnie + contrôle des données du type ────
    render_profile_banner()
    missing = missing_fields(ac)
    blocked = bool(missing)

    # ── Onglets ───────────────────────────────────────────────────────────────
    tab1, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📋 Nouveau vol",
        "📈 Performances & V-Speeds",
        "⛽ Carburant & Météo",
        "🧠 Optimisation Cargo",
        "📄 Export PDF",
        "🗂 Historique",
        "🛠 Données aéronef"
    ])

    # =========================================================================
    # ONGLET 1 : NOUVEAU VOL & MASSE CENTRAGE
    # =========================================================================
    with tab1:
        render_flight_tab(ac, selected_ac, airports, blocked, missing, user_info)

    # =========================================================================
    # ONGLET 3 : PERFORMANCES & V-SPEEDS
    # =========================================================================
    with tab3:
        st.subheader("📈 Performances & V-Speeds opérationnels")
        if blocked:
            blocked_message(missing)
        else:

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
        if blocked:
            blocked_message(missing)
        else:

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

            # ── Contrôle : bloc fuel saisi (onglet 1) vs block fuel requis ────────
            fuel_loaded = (st.session_state.get("fuel_in") or {}).get("bloc", 0)
            fuel_margin = fuel_loaded - fp["block_fuel_kg"]
            if fuel_margin >= 0:
                st.success(f"Bloc fuel saisi ({fuel_loaded:,} kg) supérieur au block fuel requis "
                           f"({fp['block_fuel_kg']:,} kg) : marge de {fuel_margin:,} kg.")
            else:
                st.error(f"Bloc fuel saisi ({fuel_loaded:,} kg) INSUFFISANT : il manque "
                         f"{-fuel_margin:,} kg par rapport au block fuel requis ({fp['block_fuel_kg']:,} kg).")

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
            st.session_state.fuel_plan = fp

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
                            <span>🕐 {str(metar.get('obs_time') or '')[:5] or 'N/D'}Z</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"❌ {icao} : {metar['raw']}")
        else:
            st.info("👆 Cliquez sur 'Actualiser METARs' pour récupérer les données météo en temps réel.")


    # =========================================================================
    # ONGLET 5 : OPTIMISATION CARGO (PuLP)
    # =========================================================================
    with tab5:
        st.subheader("🧠 Optimisation cargo par programmation linéaire (PuLP)")

        if blocked:
            blocked_message(missing)
        elif not PULP_OK:
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
                name = col1.text_input("Désignation", value=d[0], key=f"offer_name_{i}", label_visibility="collapsed")
                mass = col2.number_input("Masse (kg)", 10, 5000, d[1], key=f"offer_mass_{i}", label_visibility="collapsed")
                rev  = col3.number_input("Revenu (EUR)", 0, 50000, d[2], key=f"offer_rev_{i}", label_visibility="collapsed")
                prio = col4.number_input("Priorité", 0.1, 5.0, float(d[3]), step=0.1, key=f"offer_prio_{i}", label_visibility="collapsed")
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
        render_pdf_tab(blocked, missing)

    # =========================================================================
    # ONGLET 7 : HISTORIQUE VOLS
    # =========================================================================
    with tab7:
        st.subheader("🗂 Historique des vols AETHERDISPATCH")

        history = load_json("flight_history.json")
        if not isinstance(history, list) or len(history) == 0:
            st.info("📭 Aucun vol sauvegardé. Remplissez l'onglet 'Nouveau vol' et cliquez sur 'Sauvegarder le vol'.")
        else:
            _n = len(history)
            st.markdown(f"**{_n} vol{'s' if _n > 1 else ''} enregistré{'s' if _n > 1 else ''}**")

            # ── Filtres ───────────────────────────────────────────────────────
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filter_ac = st.text_input("Filtrer par aéronef", "")
            with col_f2:
                filter_route = st.text_input("Filtrer par route", "")

            def _bloc(h):
                f = h.get("fuel") or {}
                return f.get("bloc", (h.get("fuel_plan") or {}).get("block_fuel_kg", 0))

            df_h = pd.DataFrame([{
                "Vol": h.get("flight_number", "—"),
                "Immat.": str(h.get("registration") or "—"),
                "Aéronef": h.get("aircraft", "—"),
                "Route": f"{h.get('origin','?')} → {h.get('dest','?')}",
                "Date": h.get("datetime", "—"),
                "Loadsheet": str(h.get("ls_status", "—")),
                "PAX prévus": str(h.get("pax_prevus", "—")),
                "PAX final": str(h.get("pax_final", "—")),
                "TOW (kg)": h.get("tow", 0),
                "ZFW (kg)": h.get("zfw", 0),
                "CG TOW (%MAC)": h.get("tow_mac", 0),
                "Block Fuel": _bloc(h),
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

    # =========================================================================
    # ONGLET 8 : DONNÉES AÉRONEF MODIFIABLES · PROFIL COMPAGNIE
    # =========================================================================
    with tab8:
        render_data_tab(selected_ac, can_edit, user_info)

    # ── Footer ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="aether-footer">
        AETHERDISPATCH v4.0 — EG Conseil & Lobbying © 2026 — Système de gestion handling aérien augmenté par IA<br>
        Données à usage opérationnel restreint — Vérification obligatoire par le commandant de bord
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================
if __name__ == "__main__":
    main()
