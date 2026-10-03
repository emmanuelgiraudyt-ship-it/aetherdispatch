# =============================================================================
# AETHERDISPATCH v5.0 — Agent IA Handling Aérien
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
import hmac
import secrets
import time
import html as _html
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
    """Sauvegarde atomique d'un fichier JSON (écriture temporaire puis remplacement)."""
    tmp = f"{filepath}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, filepath)


def read_json_fresh(filepath: str, default=None):
    """Lecture sans mémoire tampon : pour les fichiers que plusieurs sessions modifient (historique, journal)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return [] if default is None else default


AUDIT_FILE = "audit_log.json"


def audit(event: str, detail: str = "", user: str = None):
    """Journal des actions (qui, quand, quoi). Ne bloque jamais l'application en cas d'échec d'écriture."""
    try:
        info = st.session_state.get("user_info") or {}
        entry = {"t": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                 "user": user or st.session_state.get("username", "-"), "name": info.get("nom", ""),
                 "event": event, "detail": detail}
        entries = read_json_fresh(AUDIT_FILE)
        if not isinstance(entries, list):
            entries = []
        entries.insert(0, entry)
        save_json(AUDIT_FILE, entries[:2000])
    except Exception:
        pass

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

PBKDF2_ITERATIONS = 200_000


def hash_password_pbkdf2(pwd: str, salt: str = None, iterations: int = PBKDF2_ITERATIONS) -> dict:
    """Haché salé (PBKDF2-SHA256) : entrée à placer dans users.json."""
    salt = salt or os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), bytes.fromhex(salt), iterations).hex()
    return {"algo": "pbkdf2_sha256", "iterations": iterations, "salt": salt, "password_hash": dk}


def verify_password(pwd: str, entry: dict) -> bool:
    """Vérifie un mot de passe : PBKDF2 salé, ou ancien SHA-256 non salé (comptes existants)."""
    if entry.get("algo") == "pbkdf2_sha256":
        try:
            dk = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), bytes.fromhex(entry["salt"]),
                                     int(entry["iterations"])).hex()
        except (KeyError, ValueError):
            return False
        return hmac.compare_digest(dk, str(entry.get("password_hash", "")))
    return hmac.compare_digest(hash_password(pwd), str(entry.get("password_hash", "")))


def generate_password(length: int = 14) -> str:
    """Mot de passe aléatoire sans caractères ambigus, avec majuscule, minuscule et chiffre."""
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.islower() for c in pwd) and any(c.isupper() for c in pwd) and any(c.isdigit() for c in pwd):
            return pwd


def authenticate(username: str, password: str, users: dict) -> bool:
    if username in users:
        return verify_password(password, users[username])
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
            wait = st.session_state.get("login_wait_until", 0) - time.time()
            if wait > 0:
                st.error(f"Trop de tentatives : réessayez dans {int(wait) + 1} s.")
            elif authenticate(username, password, users):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.user_info = users[username]
                st.session_state.pop("login_fails", None)
                st.session_state.pop("login_wait_until", None)
                audit("login_ok", "", user=username)
                st.rerun()
            else:
                fails = st.session_state.get("login_fails", 0) + 1
                st.session_state["login_fails"] = fails
                if fails >= 3:
                    st.session_state["login_wait_until"] = time.time() + min(2 ** (fails - 2), 30)
                audit("login_fail", f"tentative {fails}", user=username or "-")
                st.error("❌ Identifiants incorrects. Contactez votre administrateur OPS.")

        st.markdown("---")
        st.markdown("""
        <div style="text-align:center;font-size:0.72rem;color:#556688;letter-spacing:1px">
        ACCÈS RESTREINT — Équipe Handling & Dispatch autorisée uniquement<br>
        AETHERDISPATCH v5.0 | EG Conseil & Lobbying © 2026
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# MODULE 1 : MASSE & CENTRAGE (M&C)
# =============================================================================

def _interp(points: list, x: float, xkey: str, ykey: str):
    """Interpolation linéaire par morceaux, bornée aux extrémités du tableau."""
    pts = sorted((float(p[xkey]), float(p[ykey])) for p in points
                 if p.get(xkey) is not None and p.get(ykey) is not None)
    if not pts:
        return None
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def _valid_pts(points, *keys) -> list:
    return [p for p in (points or []) if all(p.get(k) is not None for k in keys)]


def fuel_arm_at(ac: dict, fuel_kg: float) -> float:
    """Bras du carburant : table (quantité -> bras) si elle est renseignée, sinon bras unique."""
    tbl = _valid_pts(ac.get("fuel_arm_table"), "fuel_kg", "arm_m")
    if len(tbl) >= 2:
        return _interp(tbl, fuel_kg, "fuel_kg", "arm_m")
    return ac["fuel_arm_m"]


def cg_limits_at(ac: dict, weight: float):
    """Limites de centrage (avant, arrière) à une masse donnée : enveloppe si elle est renseignée, sinon limites constantes."""
    env = _valid_pts(ac.get("cg_envelope"), "weight_kg", "fwd_m", "aft_m")
    if len(env) >= 2:
        return _interp(env, weight, "weight_kg", "fwd_m"), _interp(env, weight, "weight_kg", "aft_m")
    return ac["cg_min_m"], ac["cg_max_m"]


def compute_mc(ac: dict, pax_zone_weights: dict, cargo_weights: dict, fuel_kg: float,
               extra_items=None, crew_delta_kg: float = 0.0, trip_kg: float = 0.0) -> dict:
    """
    Masse et centrage : DOW, ZFW, TOW et LW, avec le centrage de chacun (en mètres).
    - fuel_kg : carburant au décollage ; trip_kg : carburant consommé en vol (pour la masse à l'atterrissage).
    - extra_items : autres masses (lest, consommables) sous la forme [(masse_kg, bras_m), ...], incluses dans le ZFW.
    - crew_delta_kg : écart d'équipage par rapport à la composition standard (appliqué au bras de l'équipage).
    - Le bras du carburant dépend de la quantité lorsqu'une table est renseignée (sinon bras unique).
    """
    oew = ac["oew_kg"]
    crew_kg = (ac.get("crew_kg") or 0) + crew_delta_kg
    crew_arm = ac["crew_arm_m"] if ac.get("crew_arm_m") is not None else ac["oew_arm_m"]
    dow = oew + crew_kg
    dow_moment = oew * ac["oew_arm_m"] + crew_kg * crew_arm
    dow_cg = dow_moment / dow if dow > 0 else 0

    pax_total_kg = pax_moment = 0
    for zone in ac["pax_zones"]:
        w = pax_zone_weights.get(zone["name"], 0)
        pax_total_kg += w
        pax_moment += w * zone["arm_m"]

    cargo_total_kg = cargo_moment = 0
    for comp in ac["cargo_comps"]:
        w = cargo_weights.get(comp["name"], 0)
        cargo_total_kg += w
        cargo_moment += w * comp["arm_m"]

    extra_kg = sum(m for m, _ in (extra_items or []))
    extra_moment = sum(m * a for m, a in (extra_items or []))

    zfw = dow + pax_total_kg + cargo_total_kg + extra_kg
    zfw_moment = dow_moment + pax_moment + cargo_moment + extra_moment
    zfw_cg = zfw_moment / zfw if zfw > 0 else 0
    zfw_mac = cg_to_mac(zfw_cg, ac["lemac"], ac["mac_length"])

    fuel_arm = fuel_arm_at(ac, fuel_kg)
    tow = zfw + fuel_kg
    tow_moment = zfw_moment + fuel_kg * fuel_arm
    tow_cg = tow_moment / tow if tow > 0 else 0
    tow_mac = cg_to_mac(tow_cg, ac["lemac"], ac["mac_length"])

    rem_fuel = max(fuel_kg - trip_kg, 0)
    lw = tow - trip_kg
    lw_moment = zfw_moment + rem_fuel * fuel_arm_at(ac, rem_fuel)
    lw_cg = lw_moment / (zfw + rem_fuel) if (zfw + rem_fuel) > 0 else 0
    lw_mac = cg_to_mac(lw_cg, ac["lemac"], ac["mac_length"])

    return {
        "dow": round(dow), "dow_cg": round(dow_cg, 3),
        "pax_total_kg": pax_total_kg, "cargo_total_kg": cargo_total_kg, "extra_kg": extra_kg,
        "zfw": round(zfw), "zfw_cg": round(zfw_cg, 3), "zfw_mac": zfw_mac,
        "tow": round(tow), "tow_cg": round(tow_cg, 3), "tow_mac": tow_mac,
        "lw": round(lw), "lw_cg": round(lw_cg, 3), "lw_mac": lw_mac,
        "fuel_arm": round(fuel_arm, 2), "fuel_kg": fuel_kg,
    }


def plot_cg_envelope(ac: dict, result: dict, trip_fuel: float = 0) -> go.Figure:
    """Enveloppe masse-centrage (x = mètres) avec les points ZFW, TOW et LW."""
    env = sorted(_valid_pts(ac.get("cg_envelope"), "weight_kg", "fwd_m", "aft_m"), key=lambda p: p["weight_kg"])
    if len(env) >= 2:
        ws = [p["weight_kg"] for p in env]
        xs = [p["fwd_m"] for p in env] + [p["aft_m"] for p in reversed(env)]
        ys = ws + list(reversed(ws))
        xs.append(xs[0]); ys.append(ys[0])
        lo, hi = min(p["fwd_m"] for p in env), max(p["aft_m"] for p in env)
        title = "Enveloppe Masse & Centrage"
    else:
        lo, hi = ac["cg_min_m"], ac["cg_max_m"]
        dow = ac["oew_kg"] + (ac.get("crew_kg") or 0)
        xs = [lo, lo, hi, hi, lo]
        ys = [dow, ac["max_tow_kg"], ac["max_tow_kg"], dow, dow]
        title = "Masse & Centrage (limites constantes : enveloppe non renseignée)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=ys, fill='toself', fillcolor='rgba(0, 191, 255, 0.08)',
                             line=dict(color='#00BFFF', width=2), name='Limites de centrage', hoverinfo='skip'))
    pts = [("ZFW", result["zfw_cg"], result["zfw"], '#FFD700', 'diamond', "top center"),
           ("TOW", result["tow_cg"], result["tow"], '#00FF88', 'circle', "top center")]
    if trip_fuel > 0 and result.get("lw_cg") is not None:
        pts.append(("LW", result["lw_cg"], result["lw"], '#7B2FBE', 'triangle-down', "bottom center"))
    for label, cg, w, color, symbol, pos in pts:
        fig.add_trace(go.Scatter(x=[cg], y=[w], mode='markers+text', text=[label], textposition=pos,
                                 marker=dict(size=14, color=color, symbol=symbol, line=dict(color='white', width=2)),
                                 name=f"{label} : {w:,} kg"))
    fig.update_layout(
        title=dict(text=title, font=dict(color='#00BFFF', size=16)),
        plot_bgcolor='#0D1F3C', paper_bgcolor='#0A0A1A', font=dict(color='#E0E8FF'),
        xaxis=dict(title="CG (mètres)", gridcolor='#1A3A5C', range=[lo - 1, hi + 1]),
        yaxis=dict(title="Masse (kg)", gridcolor='#1A3A5C'),
        legend=dict(bgcolor='#0D1F3C', bordercolor='#00BFFF22'), height=420,
        margin=dict(l=40, r=40, t=50, b=40))
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
                      rwy_alt_dest_ft: int, oat_c: float, alt_dist_nm: float = 200.0) -> dict:
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

    # ── Alternate fuel (distance du dégagement le plus éloigné ; 200 NM par défaut) ──
    alt_dist = alt_dist_nm
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
        "alt_fuel_kg": alt_fuel_kg, "alt_dist_nm": alt_dist,
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

AWC_URL = "https://aviationweather.gov/api/data/{kind}"
CAT_COLORS = {"VFR": "#00FF88", "MVFR": "#00BFFF", "IFR": "#FF4444", "LIFR": "#FF00FF", "INCONNUE": "#888888"}


@st.cache_data(ttl=60, show_spinner=False)
def _awc_text(kind: str, icao: str) -> str:
    """Texte brut d'un message METAR ou TAF (Aviation Weather Center, NOAA). Mémorisé 60 s ; les échecs ne le sont pas."""
    r = requests.get(AWC_URL.format(kind=kind), params={"ids": icao, "format": "raw"}, timeout=8)
    r.raise_for_status()
    return r.text or ""


def wx_error_text(e: Exception) -> str:
    """Cause lisible d'un échec d'appel au service météo."""
    if isinstance(e, requests.exceptions.Timeout):
        return "délai dépassé (8 s) : le service météo ne répond pas"
    if isinstance(e, requests.exceptions.ConnectionError):
        return "connexion impossible au service météo"
    if isinstance(e, requests.exceptions.HTTPError):
        code = getattr(getattr(e, "response", None), "status_code", None)
        if code == 429:
            return "quota du service atteint (HTTP 429) : réessayez dans une minute"
        return f"réponse du service météo en erreur (HTTP {code})"
    return f"erreur inattendue ({type(e).__name__})"


def parse_metar(raw: str) -> dict:
    """Décode un METAR au format OACI ou américain : vent, visibilité (m), plafond (ft), température, QNH, heure."""
    t = " ".join(str(raw).upper().replace("=", " ").split())
    out = {"raw": str(raw).strip(), "vis_m": None, "ceiling_ft": None, "cavok": False,
           "wind": None, "temp": None, "qnh": None, "obs_time": None}
    m = re.search(r"\b(\d{2})(\d{2})(\d{2})Z\b", t)
    if m:
        out["obs_time"] = f"{m.group(1)} à {m.group(2)}:{m.group(3)} UTC"
    w = re.search(r"\b(VRB|\d{3})(\d{2,3})(?:G(\d{2,3}))?(KT|MPS)\b", t)
    if w:
        out["wind"] = (f"{w.group(1)}°/{int(w.group(2))} {w.group(4).lower()}" if w.group(1) != "VRB"
                       else f"variable/{int(w.group(2))} {w.group(4).lower()}") + (f" rafales {int(w.group(3))}" if w.group(3) else "")
    if "CAVOK" in t.split():
        out["cavok"], out["vis_m"] = True, 9999
    else:
        mm = re.search(r"(?:KT|MPS)(?:\s\d{3}V\d{3})?\s(\d{4})\b", t)
        if mm:
            out["vis_m"] = int(mm.group(1))
        else:
            frac = re.search(r"\bM?(?:(\d+)\s)?(\d)/(\d)SM\b", t)
            whole = re.search(r"\b(\d+)SM\b", t)
            miles = None
            if frac:
                miles = int(frac.group(1) or 0) + int(frac.group(2)) / int(frac.group(3))
            elif whole:
                miles = int(whole.group(1))
            if miles is not None:
                out["vis_m"] = round(miles * 1609.34)
        bases = [int(b) * 100 for cov, b in re.findall(r"\b(BKN|OVC|VV)(\d{3})\b", t)]
        out["ceiling_ft"] = min(bases) if bases else None
    tt = re.search(r"\s(M?\d{2})/(M?\d{2})\s", t + " ")
    if tt:
        out["temp"] = int(tt.group(1).replace("M", "-"))
    q = re.search(r"\bQ(\d{4})\b", t)
    a_ = re.search(r"\bA(\d{4})\b", t)
    if q:
        out["qnh"] = int(q.group(1))
    elif a_:
        out["qnh"] = round(int(a_.group(1)) / 100 * 33.8639)
    return out


def flight_category(vis_m, ceiling_ft, cavok: bool = False) -> str:
    """Catégorie de vol (VFR, MVFR, IFR, LIFR) d'après la visibilité et le plafond ; « INCONNUE » si elle ne peut pas être établie."""
    if cavok:
        return "VFR"
    if vis_m is None:
        return "INCONNUE"
    ceil = ceiling_ft if ceiling_ft is not None else 99999
    sm = vis_m / 1609.34
    if sm < 1 or ceil < 500:
        return "LIFR"
    if sm < 3 or ceil < 1000:
        return "IFR"
    if sm <= 5 or ceil <= 3000:
        return "MVFR"
    return "VFR"


def fetch_metar(icao: str) -> dict:
    try:
        txt = _awc_text("metar", icao)
    except Exception as e:
        return {"ok": False, "raw": "", "category": "INCONNUE", "error": wx_error_text(e)}
    lines = [l.strip() for l in txt.strip().splitlines() if l.strip()]
    if not lines:
        return {"ok": False, "raw": "", "category": "INCONNUE", "error": "aucun METAR publié pour cette station"}
    d = parse_metar(lines[0])
    d["ok"] = True
    d["category"] = flight_category(d["vis_m"], d["ceiling_ft"], d["cavok"])
    return d


def fetch_taf(icao: str) -> dict:
    try:
        txt = _awc_text("taf", icao)
    except Exception as e:
        return {"ok": False, "raw": "", "error": wx_error_text(e)}
    lines = [l.strip() for l in txt.strip().splitlines() if l.strip()]
    if not lines:
        return {"ok": False, "raw": "", "error": "aucun TAF publié pour cette station (normal pour certains aérodromes)"}
    return {"ok": True, "raw": "\n".join(lines)}


def flight_cat_color(cat: str) -> str:
    return CAT_COLORS.get(cat, "#888888")


def wx_decoded_line(m: dict) -> str:
    parts = []
    if m.get("wind"):
        parts.append(f"vent {m['wind']}")
    if m.get("vis_m") is not None:
        parts.append("CAVOK" if m.get("cavok") else f"visibilité {m['vis_m']} m")
    if not m.get("cavok"):
        parts.append(f"plafond {m['ceiling_ft']} ft" if m.get("ceiling_ft") is not None else "pas de plafond (BKN/OVC)")
    if m.get("temp") is not None:
        parts.append(f"T {m['temp']} °C")
    if m.get("qnh"):
        parts.append(f"QNH {m['qnh']}")
    if m.get("obs_time"):
        parts.append(f"observé le {m['obs_time']}")
    return " · ".join(parts)


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
    Load & Trim Sheet A4, simple et opérationnelle pour le dispatcher et le commandant de bord.
    Ordre : vol, trafic (passagers, zones, bagages, fret, courrier), soutes, carburant, calcul des masses,
    chargements spéciaux et dernières modifications, (vitesses), avion et commandant de bord
    (maxima, centrages, contrôles). Une page dans le cas courant ; la suite passe à la page suivante.
    """
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=31)
    pdf.add_page()
    # La police standard ne gère que le latin-1 : remplacement des symboles non supportés
    pdf.normalize_text = lambda t: str(t).replace('→', '->').replace('—', '-').replace('–', '-').replace('─', '-').replace('−', '-').replace('€', 'EUR').replace('×', 'x').encode('latin-1', 'replace').decode('latin-1')

    NAVY, CYAN = (13, 31, 60), (0, 191, 255)
    HEAD, ZEBRA = (214, 228, 244), (244, 247, 252)
    GREEN, RED, TEXT, GREY = (0, 130, 70), (190, 30, 30), (30, 30, 30), (110, 110, 110)
    H = 4.6

    def n(v):
        try:
            return f"{int(round(float(v))):,}".replace(",", " ")
        except (TypeError, ValueError):
            return str(v)

    def section(title):
        pdf.set_x(10)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*CYAN)
        pdf.set_font("Helvetica", "B", 8.6)
        pdf.cell(190, 5.4, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.5)

    def grid(rows, widths, header=False, bold_rows=(), bold_cols=(), aligns=None, colors=None, gap=1.4):
        for r, row in enumerate(rows):
            is_head = header and r == 0
            pdf.set_x(10)
            for c, (txt, w) in enumerate(zip(row, widths)):
                if is_head:
                    pdf.set_fill_color(*HEAD)
                    pdf.set_text_color(*NAVY)
                    pdf.set_font("Helvetica", "B", 7.8)
                else:
                    pdf.set_fill_color(*(ZEBRA if r % 2 else (255, 255, 255)))
                    pdf.set_text_color(*(colors or {}).get((r, c), TEXT))
                    pdf.set_font("Helvetica", "B" if (r in bold_rows or c in bold_cols) else "", 8.2)
                pdf.cell(w, H, str(txt), border=1, align=(aligns[c] if aligns else "L"), fill=True)
            pdf.ln(H)
        pdf.ln(gap)

    def band(text, color=TEXT, gap=1.4, bold=True):
        pdf.set_x(10)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(*color)
        pdf.set_font("Helvetica", "B" if bold else "", 8.2)
        pdf.cell(190, H, text, border=1, align='C', fill=True)
        pdf.ln(H + gap)

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
    pdf.cell(190, 5, f"AETHERDISPATCH  |  LOADSHEET {fs.get('ls_status', 'PRÉLIMINAIRE')}  |  Édition n°{fs.get('edition', 1)}  |  "
                     f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} UTC", align='C')
    pdf.set_y(28.5)

    # ── Vol ───────────────────────────────────────────────────────────────
    section("VOL")
    alts = fs.get("alternates") or []
    alt_txt = ", ".join(f"{a_['icao']} ({a_['dist_nm']:.0f} NM)" for a_ in alts) or fs.get("alternate") or "-"
    grid([("Vol", fs.get("flight_number") or "-", "Date / heure (UTC)", fs.get("datetime", "-")),
          ("Départ", fs.get("origin", "-"), "Arrivée", fs.get("dest", "-")),
          ("Dégagements", alt_txt, "Distance", f"{fs.get('dist_nm', 0):.0f} NM")],
         [28, 82, 32, 48], bold_cols=(0, 2))

    # ── Trafic ────────────────────────────────────────────────────────────
    section("TRAFIC")
    counts, masses = fs.get("pax_counts", {}), fs.get("pax_masses", {})
    keys = ("male", "female", "child", "infant")
    grid([("", "Hommes", "Femmes", "Enfants", "Bébés", "Sièges occupés"),
          ("Nombre", *[counts.get(k, 0) for k in keys], fs.get("seated", 0)),
          ("Masse unitaire (kg)", *[masses.get(k, 0) for k in keys], ""),
          ("Masse totale (kg)", *[n(counts.get(k, 0) * masses.get(k, 0)) for k in keys], n(fs.get("pax_mass_kg", 0)))],
         [34, 31, 31, 31, 31, 32], header=True, bold_cols=(0,), aligns=["L", "C", "C", "C", "C", "C"], gap=1.0)
    zones = fs.get("zones") or []
    if zones:
        wz = (190 - 34) / (len(zones) + 1)
        zrows = [("Répartition par zone", *[z["name"][:26] for z in zones], "Total"),
                 ("Sièges occupés", *[z["count"] for z in zones], sum(z["count"] for z in zones))]
        zcol = {(1, i + 1): RED for i, z in enumerate(zones) if z.get("max") is not None and z["count"] > z["max"]}
        grid(zrows, [34] + [wz] * (len(zones) + 1), header=True, bold_cols=(0,),
             aligns=["L"] + ["C"] * (len(zones) + 1), colors=zcol, gap=1.0)
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
    grid([("DOW", "+ Charge payante", "+ Autres masses", "= ZFW", "+ Carb. décollage", "= TOW", "- Trip fuel", "= LW"),
          (n(fs.get("dow", 0)), n(fs.get("payload", 0)), n((fs.get("extra") or {}).get("total", 0)), n(fs.get("zfw", 0)),
           n(fuel.get("tof", 0)), n(fs.get("tow", 0)), n(fuel.get("trip", 0)), n(fs.get("lw", 0)))],
         [23, 26, 24, 22, 27, 22, 23, 23], header=True, aligns=["C"] * 8, bold_rows=(1,))

    # ── Chargements spéciaux et dernières modifications ───────────────────
    sp, lmc = fs.get("special") or [], fs.get("lmc") or []
    if sp:
        section("CHARGEMENTS SPÉCIAUX" + ("  -  NOTOC REQUIS" if fs.get("notoc_required") else ""))
        rows = [("Type", "N° ONU", "Classe", "Masse (kg)", "Soute", "Observations")]
        rows += [(r["type"], r["un"], r["cls"], n(r["kg"]) if r["kg"] is not None else "", r["hold"], r["obs"][:38]) for r in sp]
        grid(rows, [44, 24, 24, 24, 28, 46], header=True, aligns=["L", "L", "L", "R", "L", "L"], gap=0.8)
        if fs.get("notoc_required"):
            band("NOTOC requis : à remettre au commandant de bord, avec la confirmation signée du chargement.", RED)
    if lmc:
        section(f"DERNIÈRES MODIFICATIONS (LMC) - ÉDITION n°{fs.get('edition', 1)}")
        rows = [("Heure (UTC)", "Nature", "Description", "Variation (kg)")]
        rows += [(r["time"], r["nature"], r["desc"][:68], f"{r['kg']:+,.0f}".replace(",", " ") if r["kg"] is not None else "")
                 for r in lmc]
        grid(rows, [26, 30, 104, 30], header=True, aligns=["L", "L", "L", "R"], gap=0.8)
        if fs.get("lmc_max"):
            band(f"Nombre de modifications : {len(lmc)} (maximum : {fs['lmc_max']})"
                 + ("  -  NOUVELLE ÉDITION À ÉTABLIR" if fs.get("lmc_over") else ""), RED if fs.get("lmc_over") else TEXT)
    if not sp and not lmc:
        grid([("Chargements spéciaux", "AUCUN", "Dernières modifications (LMC)", "AUCUNE")], [48, 47, 48, 47], bold_cols=(0, 2))
    elif not sp:
        grid([("Chargements spéciaux", "AUCUN")], [48, 142], bold_cols=(0,))
    elif not lmc:
        grid([("Dernières modifications (LMC)", "AUCUNE")], [58, 132], bold_cols=(0,))

    # ── Vitesses (facultatif) ─────────────────────────────────────────────
    vs = fs.get("vspeeds") or {}
    if include_speeds and vs:
        section("VITESSES INDICATIVES (formule approchée, non issues de l'AFM)")
        grid([("V1", "VR", "V2", "VREF", "VAPP"),
              (f"{vs.get('v1', '-')} kts", f"{vs.get('vr', '-')} kts", f"{vs.get('v2', '-')} kts",
               f"{vs.get('vref', '-')} kts", f"{vs.get('vapp', '-')} kts")],
             [38] * 5, header=True, aligns=["C"] * 5, bold_rows=(1,))

    # ── Avion et commandant de bord (en fin de document, d'un seul tenant) ─
    if pdf.get_y() > 297 - 31 - 84:
        pdf.add_page()
        pdf.set_y(12)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*GREY)
        pdf.cell(190, 5, f"LOAD & TRIM SHEET - Vol {fs.get('flight_number') or '-'} - Édition n°{fs.get('edition', 1)} (suite)",
                 align='C', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    section("AVION ET COMMANDANT DE BORD")
    crew = fs.get("crew") or {}
    std = f"standard {crew.get('std_flight', '-') if crew.get('std_flight') is not None else '-'}/" \
          f"{crew.get('std_cabin', '-') if crew.get('std_cabin') is not None else '-'}"
    grid([("Immatriculation", fs.get("registration") or "-", "Type", fs.get("type") or "-"),
          ("Commandant de bord", fs.get("cdb_name") or "", "Préparé par", fs.get("prepared_by") or ""),
          ("Équipage", f"conduite {crew.get('flight', '-')} / cabine {crew.get('cabin', '-')}", "Écart d'équipage",
           f"{crew.get('delta_kg', 0):+,.0f} kg ({std})".replace(",", " "))],
         [40, 55, 32, 63], bold_cols=(0, 2), gap=1.2)
    rows, colors = [("Masse (kg)", "Calculée", "Maximum", "Marge", "Limite", "État")], {}
    for i, (lab, val, mx, ok, basis) in enumerate([
            ("ZFW", fs.get("zfw", 0), fs.get("max_zfw", 0), fs.get("zfw_ok"), "structure"),
            ("TOW", fs.get("tow", 0), fs.get("max_tow", 0), fs.get("tow_ok"), fs.get("tow_basis", "structure")),
            ("LW", fs.get("lw", 0), fs.get("max_lw", 0), fs.get("lw_ok"), fs.get("lw_basis", "structure"))], start=1):
        txt, col = state(bool(ok))
        rows.append((lab, n(val), n(mx), n(mx - val), basis, txt))
        colors[(i, 5)] = col
    grid(rows, [34, 32, 32, 32, 32, 28], header=True, bold_cols=(0,), aligns=["L", "R", "R", "R", "C", "C"],
         colors=colors, gap=1.0)
    lims = fs.get("cg_lims") or {}
    crows, ccol = [("Centrage", "Masse (kg)", "Centrage (m)", "Limite avant (m)", "Limite arrière (m)", "État")], {}
    crows.append(("DOW", n(fs.get("dow", 0)), f"{fs.get('dow_cg', 0):.2f}", "-", "-", "-"))
    for i, (lab, w, cg, key, ok) in enumerate([("ZFW", fs.get("zfw", 0), fs.get("zfw_cg", 0), "zfw", fs.get("zfw_cg_ok")),
                                               ("TOW", fs.get("tow", 0), fs.get("tow_cg", 0), "tow", fs.get("tow_cg_ok")),
                                               ("LW", fs.get("lw", 0), fs.get("lw_cg", 0), "lw", fs.get("lw_cg_ok"))], start=2):
        lo, hi = (lims.get(key) or [fs.get("cg_min", 0), fs.get("cg_max", 0)])
        txt, col = state(bool(ok), "OK", "HORS LIMITES")
        crows.append((lab, n(w), f"{cg:.2f}", f"{lo:.2f}", f"{hi:.2f}", txt))
        ccol[(i, 5)] = col
    grid(crows, [34, 32, 32, 32, 32, 28], header=True, bold_cols=(0,), aligns=["L", "R", "R", "R", "R", "C"],
         colors=ccol, gap=1.0)
    ctl = [("limites de masse", all(bool(fs.get(k, True)) for k in ("zfw_ok", "tow_ok", "lw_ok"))),
           ("centrage", bool(fs.get("cg_ok", True))), ("soutes", bool(fs.get("stock_ok", True))),
           ("zones passagers", bool(fs.get("zones_ok", True))), ("LMC", bool(fs.get("lmc_ok", True)))]
    band("Contrôles : " + " | ".join(f"{lab} {'OK' if ok else 'A CORRIGER'}" for lab, ok in ctl),
         GREEN if all(ok for _, ok in ctl) else RED, gap=1.8)

    pdf.set_x(10)
    pdf.set_text_color(70, 70, 70)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(63, 9, "Commandant de bord :", border=1, align='L')
    pdf.cell(2)
    pdf.cell(63, 9, f"Dispatcher : {fs.get('prepared_by') or ''}", border=1, align='L')
    pdf.cell(2)
    pdf.cell(60, 9, "Supervision du chargement :", border=1, align='L')

    # ── Pied de page : édition, origine des données ───────────────────────
    pdf.set_auto_page_break(auto=False)
    lk = fs.get("lock") or {}
    if lk.get("state") == "locked":
        lock_txt, lock_col = (f"Édition n°{lk.get('edition')} VERROUILLÉE le {lk.get('at')} UTC par {lk.get('by')} "
                              f"- empreinte {lk.get('hash')}"), GREEN
    elif lk.get("state") == "modified":
        lock_txt, lock_col = "Édition MODIFIÉE depuis son verrouillage - NOUVELLE ÉDITION À ÉTABLIR", RED
    else:
        lock_txt, lock_col = f"Édition n°{fs.get('edition', 1)} - non verrouillée (empreinte {lk.get('hash', '-')})", GREY
    certified = bool(fs.get("data_certified"))
    pdf.set_y(-31)
    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 7.6)
    pdf.set_text_color(*lock_col)
    pdf.cell(190, 3.9, lock_txt, align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*(GREEN if certified else RED))
    pdf.cell(190, 3.9, f"Origine des données : {fs.get('origin_text', '-')}"
             + ("" if certified else "   -   DONNÉES NON CERTIFIÉES"), align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.4)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(190, 3.8, f"Référentiel : {fs.get('referentiel_text', '-')}", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(190, 3.8, "Document généré par AETHERDISPATCH v5.0. Vérification obligatoire par le commandant de bord.",
             align='C')
    return bytes(pdf.output())


def generate_wx_pdf(wx: dict, ctx: dict) -> bytes:
    """Briefing météo (METAR et TAF des aéroports interrogés), A4."""
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.normalize_text = lambda t: str(t).replace('→', '->').replace('—', '-').replace('–', '-').replace('─', '-').replace('−', '-').replace('€', 'EUR').replace('×', 'x').replace('°', ' deg').encode('latin-1', 'replace').decode('latin-1')
    NAVY, CYAN, TEXT = (13, 31, 60), (0, 191, 255), (30, 30, 30)
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 24, "F")
    pdf.set_xy(10, 4.5)
    pdf.set_text_color(*CYAN)
    pdf.set_font("Helvetica", "B", 17)
    pdf.cell(190, 9, "BRIEFING MÉTÉO", align='C')
    pdf.set_xy(10, 15)
    pdf.set_text_color(200, 215, 230)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.cell(190, 5, f"AETHERDISPATCH  |  Interrogé le {wx.get('fetched_at', '-')} UTC", align='C')
    pdf.set_y(28)
    pdf.set_text_color(*TEXT)
    pdf.set_font("Helvetica", "", 9)
    if ctx:
        line = " | ".join(x for x in (f"Vol {ctx.get('flight_number')}" if ctx.get("flight_number") else "",
                                      f"{ctx.get('origin', '')} -> {ctx.get('dest', '')}" if ctx.get("origin") else "",
                                      ctx.get("datetime", "")) if x)
        if line:
            pdf.multi_cell(190, 5, line, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
    for it in wx.get("items", []):
        mt, tf = it["metar"], it["taf"]
        cat = mt.get("category", "INCONNUE")
        hexcol = CAT_COLORS.get(cat, "#888888").lstrip("#")
        rgb = tuple(int(hexcol[i:i + 2], 16) for i in (0, 2, 4))
        if pdf.get_y() > 240:
            pdf.add_page()
        pdf.set_x(10)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*CYAN)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.cell(150, 6.5, f"{it['icao']}  -  {it['name']}", fill=True)
        pdf.set_fill_color(*rgb)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(40, 6.5, f"Catégorie : {cat}", fill=True, align='C', new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*TEXT)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(190, 5, "METAR", new_x="LMARGIN", new_y="NEXT")
        if mt.get("ok"):
            pdf.set_font("Courier", "", 8.5)
            pdf.multi_cell(190, 4.2, mt["raw"], new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(190, 4.2, wx_decoded_line(mt), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*TEXT)
        else:
            pdf.set_font("Helvetica", "I", 8.5)
            pdf.multi_cell(190, 4.5, f"METAR indisponible : {mt.get('error', '')}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(190, 5, "TAF", new_x="LMARGIN", new_y="NEXT")
        if tf.get("ok"):
            pdf.set_font("Courier", "", 8.2)
            for l in tf["raw"].splitlines():
                pdf.multi_cell(190, 4.0, l, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Helvetica", "I", 8.5)
            pdf.multi_cell(190, 4.5, f"TAF indisponible : {tf.get('error', '')}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
    pdf.set_font("Helvetica", "I", 7.4)
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(190, 3.8, "Source : NOAA / NWS Aviation Weather Center (aviationweather.gov). Source non contractuelle : "
                             "les messages ci-dessus sont reproduits tels que reçus à l'heure d'interrogation et ne sont pas actualisés. "
                             "À vérifier auprès du service météorologique compétent avant toute décision opérationnelle.",
                   new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


# =============================================================================
# MODULE 7 : HISTORIQUE VOLS
# =============================================================================

def save_flight(flight_data: dict):
    """Sauvegarde un vol dans l'historique JSON."""
    history = read_json_fresh("flight_history.json")
    if not isinstance(history, list):
        history = []
    flight_data["saved_at"] = datetime.now(timezone.utc).isoformat()
    flight_data["saved_by"] = st.session_state.get("username", "inconnu")
    history.insert(0, flight_data)
    history = history[:200]  # Garder les 200 derniers vols
    save_json("flight_history.json", history)
    load_json.clear()
    audit("flight_saved", f"{flight_data.get('flight_number', '-')} · édition {flight_data.get('edition', 1)} · "
                          f"{flight_data.get('ls_status', '-')}")

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
    ("crew_std_flight", "Équipage de conduite standard (nombre)", "pers.", False),
    ("crew_std_cabin",  "Équipage de cabine standard (nombre)",   "pers.", False),
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
    for key in ("cg_envelope", "fuel_arm_table"):          # tables facultatives : comptées si elles sont renseignées
        if ac.get(key):
            s = _meta(ac)["status"].get(key) or "estime"
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
    for k in ("pax_zones", "cargo_comps", "cg_envelope", "fuel_arm_table"):
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
    audit("profile_exported", st.session_state.get("profile_name") or "profil compagnie")
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
SRC_EASA_CREW = ("Règlement (UE) n° 965/2012, AMC2 CAT.POL.MAB.100(d) : masses standard, bagage à main compris, "
                 "de 85 kg (équipage de conduite) et 75 kg (équipage de cabine)")


def default_referentiel() -> dict:
    def item(label, value, src):
        return {"label": label, "value": value, "status": "reglementaire", "source": src}
    return {
        "identification": {"organisme": "", "document": "", "version": "", "date_application": ""},
        "pax_masses": {"male": item("Hommes", 88, SRC_EASA_PAX), "female": item("Femmes", 70, SRC_EASA_PAX),
                       "child": item("Enfants", 35, SRC_EASA_PAX), "infant": item("Bébés", 0, SRC_EASA_INF)},
        "bag_masses": {"domestic": item("Vol intérieur", 11, SRC_BAG), "other": item("Autres vols", 13, SRC_BAG),
                       "intercontinental": item("Vol intercontinental", 15, SRC_BAG)},
        "crew_masses": {"flight": item("Équipage de conduite", 85, SRC_EASA_CREW),
                        "cabin": item("Équipage de cabine", 75, SRC_EASA_CREW)},
        "procedures": {"lmc_max": None},
    }


def normalize_referentiel(r) -> dict:
    """Complète un référentiel (importé ou ancien) avec les valeurs par défaut manquantes."""
    base = default_referentiel()
    if not isinstance(r, dict):
        return base
    for grp in ("pax_masses", "bag_masses", "crew_masses"):
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
    lm = _num((r.get("procedures") or {}).get("lmc_max"))
    base["procedures"]["lmc_max"] = int(lm) if lm and lm > 0 else None
    return base


def referentiel_label(ref: dict) -> str:
    i = ref["identification"]
    parts = [p for p in (i.get("organisme"), i.get("document"), i.get("version")) if p]
    return " - ".join(parts) if parts else "non renseigné (valeurs réglementaires par défaut)"


def ref_acceptable(ref: dict) -> bool:
    """Vrai si toutes les valeurs du référentiel sont réglementaires ou issues de la compagnie."""
    items = list(ref["pax_masses"].values()) + list(ref["bag_masses"].values()) + list(ref["crew_masses"].values())
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
    zones_over = [(z["name"], zone_counts[i], int(z["max_pax"])) for i, z in enumerate(zones)
                  if zone_counts and z.get("max_pax") is not None and zone_counts[i] > z["max_pax"]]
    for zname, zcount, zcap in zones_over:
        st.error(f"Zone {zname} : {zcount} passagers pour une capacité de {zcap} places.")
    return {"zones_over": zones_over, "status": status, "prev": prev, "final": final, "active_counts": active_counts, "seated": seated,
            "seated_prev": seated_prev, "seated_final": seated_final, "has_final": has_final,
            "zone_counts": zone_counts, "max_seats": max_seats, "masses": masses}


def render_pax_comparison(ac: dict, pax: dict, comp_loads: dict, tof: float, extra_items=None, crew_delta: float = 0.0):
    """Tableau prévu / final : sièges, bébés, ZFW, TOW, centrage."""
    st.markdown("**Comparaison prévu / final**")
    if not pax["has_final"]:
        st.caption("PAX final non saisi : la comparaison s'affichera dès qu'il le sera.")
        return

    def scenario(counts):
        return compute_mc(ac, zone_weights_from_counts(ac, counts, pax["masses"]), comp_loads, tof,
                          extra_items=extra_items, crew_delta_kg=crew_delta)

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
    # Date et heure : valeurs initiales fixées une seule fois (en UTC) puis conservées. Une valeur par défaut qui change
    # à chaque minute ferait réinitialiser le champ à chaque nouvelle interaction.
    _now_utc = datetime.now(timezone.utc)
    st.session_state.setdefault("flight_date", _now_utc.date())
    st.session_state.setdefault("flight_time", _now_utc.replace(second=0, microsecond=0).time())
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        flight_number = st.text_input("N° de vol", value="AF1234", placeholder="AF1234")
        origin = st.selectbox("🛫 Départ", list(airports.keys()), key="origin")
    with col_b:
        flight_date = st.date_input("Date du vol", key="flight_date")
        dest = st.selectbox("🛬 Arrivée", list(airports.keys()), index=min(1, len(airports) - 1), key="dest")
    with col_c:
        flight_time = st.time_input("Heure départ (UTC)", key="flight_time")
    registration = st.text_input("Immatriculation de l'avion", value="", key="registration",
                                 placeholder="ex. F-GKXA", max_chars=10).strip().upper()

    NONE_OPT = "— Aucun —"
    ap_names = list(airports.keys())
    ca1, ca2, ca3 = st.columns(3)
    alt1 = ca1.selectbox("⚡ Dégagement 1", ap_names, index=min(2, len(ap_names) - 1), key="alt")
    alt2 = ca2.selectbox("⚡ Dégagement 2 (facultatif)", [NONE_OPT] + ap_names, key="alt2")
    alt3 = ca3.selectbox("⚡ Dégagement 3 (facultatif)", [NONE_OPT] + ap_names, key="alt3")
    alt_names = []
    for n_ in (alt1, alt2, alt3):
        if n_ != NONE_OPT and n_ not in alt_names:
            alt_names.append(n_)

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
    alt_info = [{"name": n_, "icao": airports[n_]["icao"],
                 "dist_nm": haversine(dest_data["lat"], dest_data["lon"], airports[n_]["lat"], airports[n_]["lon"]),
                 "rwy_m": airports[n_].get("rwy_length_m")} for n_ in alt_names]
    far = max((a_["dist_nm"] for a_ in alt_info), default=0)
    alt_fuel_dist = float(far) if far > 0 else 200.0
    st.session_state.alternates = alt_names
    st.session_state.alt_dist_nm = alt_fuel_dist
    alternate = " / ".join(a_["icao"] for a_ in alt_info)
    st.dataframe(pd.DataFrame([{"Dégagement": a_["name"], "Distance depuis l'arrivée (NM)": round(a_["dist_nm"]),
                                "Piste (m)": a_["rwy_m"]} for a_ in alt_info]), hide_index=True, use_container_width=True)
    if far > 0:
        st.caption(f"Le carburant de dégagement est calculé sur le dégagement le plus éloigné : {alt_fuel_dist:.0f} NM.")
    else:
        st.warning("Dégagement identique à l'arrivée : la distance par défaut de 200 NM est utilisée pour le carburant.")
    if any(a_["name"] == dest for a_ in alt_info) and far > 0:
        st.warning("Un des dégagements est identique à l'aéroport d'arrivée.")
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

    # ── 4b. Équipage, autres masses, limites du jour, chargements spéciaux ────
    hold_names = [c["name"] for c in comps]
    arm_by_name = {c["name"]: c["arm_m"] for c in comps}
    st.markdown("**👩‍✈️ Équipage**")
    cm = ref["crew_masses"]
    m_f, m_c = cm["flight"]["value"], cm["cabin"]["value"]
    std_f, std_c = ac.get("crew_std_flight"), ac.get("crew_std_cabin")
    e1, e2, e3 = st.columns(3)
    n_f = int(e1.number_input("Équipage de conduite (nombre)", 0, 10, int(std_f) if std_f is not None else 2,
                              key=f"crew_f_{selected_ac}"))
    n_c = int(e2.number_input("Équipage de cabine (nombre)", 0, 30, int(std_c) if std_c is not None else 0,
                              key=f"crew_c_{selected_ac}"))
    crew_delta = ((n_f - int(std_f)) * m_f if std_f is not None else 0) + ((n_c - int(std_c)) * m_c if std_c is not None else 0)
    e3.metric("Écart de masse d'équipage", f"{crew_delta:+,.0f} kg",
              help=f"Écart par rapport à la composition standard ({std_f if std_f is not None else '—'} / "
                   f"{std_c if std_c is not None else '—'}), aux masses du référentiel.")
    if std_f is None or std_c is None:
        st.caption("Composition standard non renseignée pour ce type : aucun ajustement de masse n'est appliqué "
                   "(onglet « Données aéronef »).")

    with st.expander("Autres masses (lest, consommables autres que le carburant)"):
        o1, o2, o3, o4 = st.columns(4)
        ballast = int(o1.number_input("Lest (kg)", 0, 20000, 0, step=10, key=f"ballast_{selected_ac}"))
        ballast_pos = o2.selectbox("Position du lest", hold_names, key=f"ballast_pos_{selected_ac}") if hold_names else ""
        cons = int(o3.number_input("Consommables (kg)", 0, 20000, 0, step=10, key=f"cons_{selected_ac}"))
        cons_pos = o4.selectbox("Position des consommables", hold_names, key=f"cons_pos_{selected_ac}") if hold_names else ""
        st.caption("Ces masses sont incluses dans le ZFW. Leur position est approchée par le bras de la soute choisie.")
    extra_items = [(kg_, arm_by_name.get(pos_, ac["oew_arm_m"])) for kg_, pos_ in ((ballast, ballast_pos), (cons, cons_pos)) if kg_ > 0]
    extra_kg = ballast + cons

    with st.expander("Limites de masse du jour (performances : piste, météo)"):
        l1, l2 = st.columns(2)
        perf_tow = int(l1.number_input("TOW maximal limité par les performances (kg, 0 = aucune)", 0, 700000, 0, step=100,
                                       key=f"perf_tow_{selected_ac}"))
        perf_lw = int(l2.number_input("LW maximal limité par les performances (kg, 0 = aucune)", 0, 700000, 0, step=100,
                                      key=f"perf_lw_{selected_ac}"))
        st.caption("La limite retenue est la plus faible entre le maximum de structure et la limite de performances.")
    eff_tow, tow_basis = (perf_tow, "performances") if 0 < perf_tow < ac["max_tow_kg"] else (ac["max_tow_kg"], "structure")
    eff_lw, lw_basis = (perf_lw, "performances") if 0 < perf_lw < ac["max_lw_kg"] else (ac["max_lw_kg"], "structure")

    with st.expander("⚠ Chargements spéciaux (marchandises dangereuses, animaux vivants, restes humains, valeurs)"):
        sp_empty = pd.DataFrame({"Type": pd.Series(dtype="object"), "N° ONU": pd.Series(dtype="object"),
                                 "Classe / division": pd.Series(dtype="object"), "Masse (kg)": pd.Series(dtype="float"),
                                 "Soute": pd.Series(dtype="object"), "Observations": pd.Series(dtype="object")})
        sp_df = st.data_editor(sp_empty, num_rows="dynamic", hide_index=True, use_container_width=True,
                               key=f"special_{selected_ac}",
                               column_config={"Type": st.column_config.SelectboxColumn("Type", options=SPECIAL_TYPES),
                                              "Soute": st.column_config.SelectboxColumn("Soute", options=hold_names or [""]),
                                              "Masse (kg)": st.column_config.NumberColumn("Masse (kg)", min_value=0)})
        st.caption("Reportez la masse dans les champs fret ou courrier de la soute concernée : ce tableau n'en modifie pas le calcul.")
    special_rows = parse_special(sp_df)
    notoc_required = any(r_["type"] == "Marchandise dangereuse" for r_ in special_rows)
    if notoc_required:
        st.warning("NOTOC requis : l'information écrite sur les marchandises dangereuses, avec leur position de chargement, "
                   "doit être remise au commandant de bord, avec la confirmation signée du chargement. Elle est établie par "
                   "le personnel formé aux marchandises dangereuses.")
        if any(r_["type"] == "Marchandise dangereuse" and (not r_["un"] or not r_["hold"]) for r_ in special_rows):
            st.error("Marchandise dangereuse : le numéro ONU et la soute sont à renseigner pour le NOTOC.")
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)

    # ── 5. Calculs ────────────────────────────────────────────────────────
    pax_weights = zone_weights_from_counts(ac, pax["active_counts"], pax["masses"], pax["zone_counts"])
    result = compute_mc(ac, pax_weights, comp_loads, tof, extra_items=extra_items, crew_delta_kg=crew_delta,
                        trip_kg=min(trip, tof))
    lw = result["tow"] - trip
    payload = result["pax_total_kg"] + sum(comp_loads.values())

    lim_z, lim_t, lim_l = (cg_limits_at(ac, result["zfw"]), cg_limits_at(ac, result["tow"]), cg_limits_at(ac, lw))
    zfw_ok = result["zfw"] <= ac["max_zfw_kg"]
    tow_ok = result["tow"] <= eff_tow
    lw_ok = lw <= eff_lw
    zfw_cg_ok = lim_z[0] <= result["zfw_cg"] <= lim_z[1]
    tow_cg_ok = lim_t[0] <= result["tow_cg"] <= lim_t[1]
    lw_cg_ok = lim_l[0] <= result["lw_cg"] <= lim_l[1]
    cg_ok = zfw_cg_ok and tow_cg_ok and lw_cg_ok
    zones_ok = not pax.get("zones_over")
    stock_ok = unplaced == 0 and all(comp_loads[c["name"]] <= c["max_kg"] for c in comps)

    def card(label, val, unit, note, ok=None, fmt=",.0f"):
        color = "#E0E8FF" if ok is None else ("#00FF88" if ok else "#FF4444")
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value" style="color:{color}">{val:{fmt}}</div>
            <div class="unit">{unit}</div>
            <div style="font-size:0.68rem;color:#556688;margin-top:4px">{note}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### ⚖ Résultats Masse & Centrage")
    row1 = [("ZFW", result["zfw"], "kg", f"Max {ac['max_zfw_kg']:,} kg (structure) · marge {ac['max_zfw_kg'] - result['zfw']:,} kg", zfw_ok),
            ("TOW", result["tow"], "kg", f"Max {eff_tow:,} kg ({tow_basis}) · marge {eff_tow - result['tow']:,} kg", tow_ok),
            ("LW", lw, "kg", f"Max {eff_lw:,} kg ({lw_basis}) · marge {eff_lw - lw:,} kg", lw_ok),
            ("Charge payante", payload, "kg", "passagers, bagages, fret, courrier", None)]
    for col, (label, val, unit, note, ok) in zip(st.columns(4), row1):
        with col:
            card(label, val, unit, note, ok)
    row2 = [("CG DOW", result["dow_cg"], f"m · DOW {result['dow']:,} kg", "masse à vide + équipage", None),
            ("CG ZFW", result["zfw_cg"], "m", f"limites {lim_z[0]:.2f} à {lim_z[1]:.2f} m", zfw_cg_ok),
            ("CG TOW", result["tow_cg"], "m", f"limites {lim_t[0]:.2f} à {lim_t[1]:.2f} m", tow_cg_ok),
            ("CG LW", result["lw_cg"], "m", f"limites {lim_l[0]:.2f} à {lim_l[1]:.2f} m", lw_cg_ok)]
    for col, (label, val, unit, note, ok) in zip(st.columns(4), row2):
        with col:
            card(label, val, unit, note, ok, fmt=".2f")
    for lab, okc, cgv, lim in (("ZFW", zfw_cg_ok, result["zfw_cg"], lim_z), ("TOW", tow_cg_ok, result["tow_cg"], lim_t),
                               ("LW", lw_cg_ok, result["lw_cg"], lim_l)):
        if not okc:
            st.error(f"Centrage hors limites au {lab} : {cgv:.2f} m (limites {lim[0]:.2f} à {lim[1]:.2f} m).")
    if not (ac.get("cg_envelope") or []):
        st.caption("Limites de centrage constantes : l'enveloppe masse-centrage n'est pas renseignée pour ce type "
                   "(onglet « Données aéronef »).")

    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
    render_pax_comparison(ac, pax, comp_loads, tof, extra_items, crew_delta)
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
    st.plotly_chart(plot_cg_envelope(ac, result, min(trip, tof)), use_container_width=True)

    # ── 6. Édition, dernières modifications (LMC) et verrouillage ─────────
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
    st.markdown("### 📝 Édition, dernières modifications (LMC) et verrouillage")
    ed1, ed2 = st.columns([1, 3])
    edition = int(ed1.number_input("Édition n°", 1, 99, 1, key="ls_edition"))
    lmc_max = ref["procedures"].get("lmc_max")
    ed2.caption("Nombre maximal de dernières modifications avant nouvelle édition : "
                + (str(lmc_max) if lmc_max else "non renseigné (référentiel compagnie)"))
    lmc_empty = pd.DataFrame({"Heure (UTC)": pd.Series(dtype="object"), "Nature": pd.Series(dtype="object"),
                              "Description": pd.Series(dtype="object"), "Variation (kg)": pd.Series(dtype="float")})
    lmc_df = st.data_editor(lmc_empty, num_rows="dynamic", hide_index=True, use_container_width=True, key="lmc_editor",
                            column_config={"Nature": st.column_config.SelectboxColumn("Nature", options=LMC_NATURES)})
    lmc_rows = parse_lmc(lmc_df)
    lmc_over = bool(lmc_max) and len(lmc_rows) > lmc_max
    if lmc_over:
        st.error(f"Nombre maximal de dernières modifications dépassé ({len(lmc_rows)} pour un maximum de {lmc_max}) : "
                 "une nouvelle édition est à établir.")
    st.caption("Les variations sont indicatives : reportez-les dans les champs de saisie pour recalculer la loadsheet.")

    fp_payload = {"vol": flight_number, "immat": registration, "avion": selected_ac, "date": f"{flight_date} {flight_time}",
                  "route": [origin, dest, alternate], "statut": pax["status"], "pax": pax["active_counts"],
                  "bagages": bag_total, "soutes": comp_loads, "carburant": [bloc, taxi, trip], "equipage": [n_f, n_c],
                  "autres": [ballast, ballast_pos, cons, cons_pos], "limites": [perf_tow, perf_lw], "speciaux": special_rows,
                  "lmc": lmc_rows, "edition": edition, "zfw": result["zfw"], "tow": result["tow"], "lw": lw}
    fp = hashlib.sha256(json.dumps(fp_payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:8].upper()
    lock = st.session_state.get("locked")
    lock_state = "none" if not lock else ("locked" if lock["hash"] == fp else "modified")
    is_final = pax["status"] == "Final"
    cl1, cl2 = st.columns([3, 1])
    with cl1:
        if lock_state == "locked":
            st.success(f"Édition n°{lock['edition']} verrouillée le {lock['at']} UTC par {lock['by']} (empreinte {fp}).")
        elif lock_state == "modified":
            st.warning(f"Les données ont changé depuis le verrouillage de l'édition n°{lock['edition']} : "
                       "établissez une nouvelle édition.")
            st.button(f"Établir l'édition n°{int(lock['edition']) + 1}", on_click=_new_edition, key="btn_new_edition")
        else:
            st.caption("Édition non verrouillée." + ("" if is_final else " Le verrouillage nécessite le statut « Final »."))
    if cl2.button("🔒 Verrouiller l'édition", key="btn_lock", disabled=(not is_final or lock_state == "locked"),
                  use_container_width=True):
        st.session_state["locked"] = {"edition": edition, "hash": fp, "flight": flight_number,
                                      "at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M"),
                                      "by": st.session_state.get("preparer_name") or user_info.get("nom", "")}
        audit("edition_locked", f"{flight_number} · édition {edition} · empreinte {fp}")
        st.rerun()

    # ── 7. Récapitulatif pour le commandant de bord (en fin de page) ──────
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
    st.markdown("### 🧑‍✈️ Récapitulatif avion et commandant de bord")
    r1, r2 = st.columns(2)
    r1.metric("Immatriculation", registration or "—")
    r2.metric("Type", ac.get("type") or "—")
    r3, r4 = st.columns(2)
    cdb_name = r3.text_input("Commandant de bord (nom)", key="cdb_name")
    preparer = r4.text_input("Préparé par (nom et prénom)", value=user_info.get("nom", ""), key="preparer_name").strip()
    recap = pd.DataFrame([
        ("ZFW", f"{result['zfw']:,}", f"{ac['max_zfw_kg']:,}", f"{ac['max_zfw_kg'] - result['zfw']:,}", "structure", "OK" if zfw_ok else "DÉPASSÉ"),
        ("TOW", f"{result['tow']:,}", f"{eff_tow:,}", f"{eff_tow - result['tow']:,}", tow_basis, "OK" if tow_ok else "DÉPASSÉ"),
        ("LW", f"{lw:,}", f"{eff_lw:,}", f"{eff_lw - lw:,}", lw_basis, "OK" if lw_ok else "DÉPASSÉ"),
    ], columns=["Masse (kg)", "Calculée", "Maximum", "Marge", "Limite", "État"])
    st.dataframe(recap, hide_index=True, use_container_width=True)
    st.caption(f"Charge payante : {payload:,.0f} kg (passagers {result['pax_total_kg']:,.0f} kg, "
               f"bagages {bag_total:,} kg, fret {sum(cargo_w.values()):,} kg, courrier {sum(mail_w.values()):,} kg). "
               f"Carburant : bloc {bloc:,} kg, taxi {taxi:,} kg, trip {trip:,} kg, décollage {tof:,} kg. "
               f"Équipage : {n_f} / {n_c}.")

    # ── Synthèse du vol (alimente le PDF et l'historique) ─────────────────
    origin_txt, aircraft_certified = origin_summary(ac)
    lmc_ok = not lmc_over
    fs = {
        "flight_number": flight_number, "registration": registration, "aircraft": selected_ac,
        "type": ac.get("type", ""), "origin": origin, "dest": dest, "alternate": alternate, "alternates": alt_info,
        "dist_nm": dist_nm,
        "datetime": f"{flight_date.strftime('%d/%m/%Y')} {flight_time.strftime('%H:%M')} UTC",
        "ls_status": pax["status"].upper(), "cdb_name": cdb_name.strip(),
        "prepared_by": preparer or user_info.get("nom", ""), "account": st.session_state.get("username", ""),
        "pax_counts": dict(pax["active_counts"]), "pax_masses": dict(pax["masses"]),
        "seated": pax["seated"], "pax_max": pax["max_seats"],
        "pax_prevus": pax["seated_prev"], "pax_final": pax["seated_final"],
        "pax_mass_kg": result["pax_total_kg"],
        "zones": [{"name": z["name"], "count": pax["zone_counts"][i], "max": z.get("max_pax")}
                  for i, z in enumerate(ac.get("pax_zones") or []) if pax["zone_counts"]],
        "bag_mode": bag_mode, "bag_pieces": bag_pieces, "bag_std": bag_std, "bag_ft": bag_ft_label,
        "bag_total": bag_total, "cargo_total": sum(cargo_w.values()), "mail_total": sum(mail_w.values()),
        "payload": payload,
        "comps": [{"name": c["name"], "bag": bag_w.get(c["name"], 0), "cargo": cargo_w.get(c["name"], 0),
                   "mail": mail_w.get(c["name"], 0), "total": comp_loads[c["name"]], "max": int(c["max_kg"])}
                  for c in comps],
        "fuel": {"bloc": bloc, "taxi": taxi, "trip": trip, "tof": tof},
        "crew": {"flight": n_f, "cabin": n_c, "std_flight": std_f, "std_cabin": std_c, "delta_kg": crew_delta},
        "extra": {"ballast": ballast, "ballast_pos": ballast_pos, "cons": cons, "cons_pos": cons_pos, "total": extra_kg},
        "oew": ac["oew_kg"], "crew_kg": (ac.get("crew_kg") or 0) + crew_delta, "dow": result["dow"],
        "zfw": result["zfw"], "tow": result["tow"], "lw": lw,
        "max_zfw": ac["max_zfw_kg"], "max_tow": eff_tow, "max_lw": eff_lw,
        "tow_basis": tow_basis, "lw_basis": lw_basis, "struct_tow": ac["max_tow_kg"], "struct_lw": ac["max_lw_kg"],
        "zfw_ok": zfw_ok, "tow_ok": tow_ok, "lw_ok": lw_ok, "cg_ok": cg_ok, "stock_ok": stock_ok,
        "zfw_cg_ok": zfw_cg_ok, "tow_cg_ok": tow_cg_ok, "lw_cg_ok": lw_cg_ok, "zones_ok": zones_ok, "lmc_ok": lmc_ok,
        "zones_over": [list(z) for z in pax.get("zones_over", [])],
        "tow_cg": result["tow_cg"], "zfw_cg": result["zfw_cg"], "tow_mac": result["tow_mac"],
        "zfw_mac": result["zfw_mac"], "dow_cg": result["dow_cg"], "lw_cg": result["lw_cg"],
        "cg_min": lim_t[0], "cg_max": lim_t[1],
        "cg_lims": {"zfw": list(lim_z), "tow": list(lim_t), "lw": list(lim_l)},
        "special": special_rows, "notoc_required": notoc_required,
        "edition": edition, "lmc": lmc_rows, "lmc_max": lmc_max, "lmc_over": lmc_over,
        "lock": {"state": lock_state, "hash": fp, "edition": (lock or {}).get("edition"),
                 "at": (lock or {}).get("at"), "by": (lock or {}).get("by")},
        "status_ok": all([zfw_ok, tow_ok, lw_ok, cg_ok, stock_ok, zones_ok, lmc_ok]),
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
        audit("pdf_generated", f"{fs['flight_number'] or '-'} · édition {fs.get('edition', 1)} · {fs['ls_status']} · "
                               f"verrou {fs['lock']['state']} · {'données non certifiées' if not fs['data_certified'] else 'données certifiées'}")
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
    ("crew.flight", "Masse standard - Équipage de conduite (kg)"), ("crew.cabin", "Masse standard - Équipage de cabine (kg)"),
    ("proc.lmc_max", "Nombre maximal de dernières modifications (LMC) avant nouvelle édition"),
]
REF_GROUPS = {"pax": "pax_masses", "bag": "bag_masses", "crew": "crew_masses"}
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
        elif grp == "proc":
            rows.append({"Paramètre": label, "Valeur": ref["procedures"].get(k) or "", "Statut": "",
                         "Source / commentaire": ""})
        else:
            it = ref[REF_GROUPS[grp]][k]
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
        if grp == "proc":
            v = _num(r.get("Valeur"))
            v = int(v) if v and v > 0 else None
            if v != new_ref["procedures"].get(k):
                new_ref["procedures"][k], changed = v, changed + 1
            continue
        it, v = new_ref[REF_GROUPS[grp]][k], _num(r.get("Valeur"))
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
        st.markdown("**Masses standard de l'équipage**")
        cdf_ref = kv_df(ref["crew_masses"])
        lmc_val = st.number_input("Nombre maximal de dernières modifications (LMC) avant nouvelle édition (0 = non renseigné)",
                                  0, 99, int(ref["procedures"].get("lmc_max") or 0), key=f"ref_lmc_{ver}", disabled=not can_edit)
        if can_edit:
            ed_p = st.data_editor(pdf_df, hide_index=True, use_container_width=True, key=f"ref_pax_{ver}",
                                  disabled=["Paramètre"], num_rows="fixed", column_config=cfg)
            ed_b = st.data_editor(bdf, hide_index=True, use_container_width=True, key=f"ref_bag_{ver}",
                                  disabled=["Paramètre"], num_rows="fixed", column_config=cfg)
            ed_c = st.data_editor(cdf_ref, hide_index=True, use_container_width=True, key=f"ref_crew_{ver}",
                                  disabled=["Paramètre"], num_rows="fixed", column_config=cfg)
            if st.button("💾 Enregistrer le référentiel", key=f"btn_ref_{ver}", use_container_width=True):
                changed = 0
                new_ident = {"organisme": organisme.strip(), "document": document.strip(),
                             "version": version.strip(), "date_application": date_app.strip()}
                if new_ident != ident:
                    ref["identification"] = new_ident
                    changed += 1
                changed += (apply_kv_edits(ref["pax_masses"], ed_p) + apply_kv_edits(ref["bag_masses"], ed_b)
                            + apply_kv_edits(ref["crew_masses"], ed_c))
                new_lmc = int(lmc_val) if lmc_val > 0 else None
                if new_lmc != ref["procedures"].get("lmc_max"):
                    ref["procedures"]["lmc_max"] = new_lmc
                    changed += 1
                if changed:
                    st.session_state.dirty = True
                    st.session_state.ed_version = ver + 1
                    audit("referentiel_saved", f"{changed} modification(s)")
                    st.session_state["_flash"] = (f"Référentiel enregistré ({changed} modification(s)). "
                                                  "Exportez votre profil pour le conserver.")
                    st.rerun()
                else:
                    st.info("Aucune modification à enregistrer.")
        else:
            st.dataframe(pdf_df, hide_index=True, use_container_width=True)
            st.dataframe(bdf, hide_index=True, use_container_width=True)
            st.dataframe(cdf_ref, hide_index=True, use_container_width=True)

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
                        audit("referentiel_applied", msg)
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


ENV_MAP = [("Masse (kg)", "weight_kg"), ("Limite avant (m)", "fwd_m"), ("Limite arrière (m)", "aft_m")]
FUEL_MAP = [("Carburant (kg)", "fuel_kg"), ("Bras (m)", "arm_m")]


def table_df(rows: list, mapping: list) -> pd.DataFrame:
    df = pd.DataFrame([{c: r.get(k) for c, k in mapping} for r in (rows or [])], columns=[c for c, _ in mapping])
    for c, _ in mapping:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def apply_table_edits(ac: dict, key: str, df: pd.DataFrame, mapping: list, src: str) -> int:
    """Enregistre un tableau facultatif (trié par la première colonne). Une modification passe en « Compagnie »."""
    new = []
    for rec in df.to_dict("records"):
        vals = {k: _num(rec.get(c)) for c, k in mapping}
        if all(v is None for v in vals.values()):
            continue
        new.append(vals)
    first = mapping[0][1]
    new.sort(key=lambda r: (r[first] is None, r[first] or 0))
    old = [{k: r.get(k) for _, k in mapping} for r in (ac.get(key) or [])]
    m = _meta(ac)
    changed = int(new != old)
    if new != old:
        ac[key] = new
        m["status"][key] = "compagnie" if new else "a_renseigner"
    src = (src or "").strip()
    if src != m["source"].get(key, ""):
        m["source"][key] = src
        changed += 1
    return changed


def _register_type(new_name: str, rec: dict):
    name = (new_name or "").strip()
    if not name:
        st.error("Saisissez un nom pour le type.")
        return
    if name in st.session_state.db:
        st.error("Ce nom de type existe déjà.")
        return
    st.session_state.db[name] = rec
    audit("type_created", name)
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
                audit("profile_imported", new_info["name"])
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
                audit("type_deleted", selected_ac)
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

    st.markdown("**Enveloppe de centrage** (limites avant et arrière selon la masse ; à défaut, limites constantes)")
    env_df = table_df(ac.get("cg_envelope"), ENV_MAP)
    fuel_df = table_df(ac.get("fuel_arm_table"), FUEL_MAP)
    num_cfg = {c: st.column_config.NumberColumn(c, min_value=0) for c, _ in ENV_MAP + FUEL_MAP}
    if can_edit:
        edited_env = st.data_editor(env_df, hide_index=True, use_container_width=True, key=f"ed_env_{k}",
                                    num_rows="dynamic", column_config=num_cfg)
        env_src = st.text_input("Source de l'enveloppe (chapitre ou section du manuel)",
                                value=_meta(ac)["source"].get("cg_envelope", ""), key=f"ed_envsrc_{k}")
    else:
        st.dataframe(env_df, hide_index=True, use_container_width=True)
    if len(_valid_pts(ac.get("cg_envelope"), "weight_kg", "fwd_m", "aft_m")) < 2:
        st.caption("Enveloppe non renseignée (ou moins de deux points) : les limites constantes de la table "
                   "« Paramètres généraux » sont utilisées.")

    st.markdown("**Bras du carburant selon la quantité** (à défaut, bras unique)")
    if can_edit:
        edited_fuel = st.data_editor(fuel_df, hide_index=True, use_container_width=True, key=f"ed_fuel_{k}",
                                     num_rows="dynamic", column_config=num_cfg)
        fuel_src = st.text_input("Source de la table du carburant (chapitre ou section du manuel)",
                                 value=_meta(ac)["source"].get("fuel_arm_table", ""), key=f"ed_fuelsrc_{k}")
    else:
        st.dataframe(fuel_df, hide_index=True, use_container_width=True)
    if len(_valid_pts(ac.get("fuel_arm_table"), "fuel_kg", "arm_m")) < 2:
        st.caption("Table non renseignée (ou moins de deux points) : le bras unique du carburant est utilisé.")

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
        changed += apply_table_edits(ac, "cg_envelope", edited_env, ENV_MAP, env_src)
        changed += apply_table_edits(ac, "fuel_arm_table", edited_fuel, FUEL_MAP, fuel_src)
        if changed:
            audit("data_saved", f"{selected_ac} : {changed} modification(s)")
        if changed:
            st.session_state.dirty = True
            st.session_state.ed_version = ver + 1
            st.session_state["_flash"] = (f"{changed} modification(s) enregistrée(s) pour « {selected_ac} ». "
                                          "Exportez votre profil pour les conserver.")
            st.rerun()
        else:
            st.info("Aucune modification à enregistrer.")


SPECIAL_COLS = ["Type", "N° ONU", "Classe / division", "Masse (kg)", "Soute", "Observations"]
SPECIAL_TYPES = ["Marchandise dangereuse", "Animaux vivants", "Restes humains", "Valeurs", "Autre"]
LMC_COLS = ["Heure (UTC)", "Nature", "Description", "Variation (kg)"]
LMC_NATURES = ["Passagers", "Bagages", "Fret", "Courrier", "Carburant", "Autre"]


def parse_special(df: pd.DataFrame) -> list:
    out = []
    for rec in df.to_dict("records"):
        row = {"type": _txt(rec.get("Type")), "un": _txt(rec.get("N° ONU")), "cls": _txt(rec.get("Classe / division")),
               "kg": _num(rec.get("Masse (kg)")), "hold": _txt(rec.get("Soute")), "obs": _txt(rec.get("Observations"))}
        if any(v not in ("", None) for v in row.values()):
            out.append(row)
    return out


def parse_lmc(df: pd.DataFrame) -> list:
    out = []
    for rec in df.to_dict("records"):
        row = {"time": _txt(rec.get("Heure (UTC)")), "nature": _txt(rec.get("Nature")),
               "desc": _txt(rec.get("Description")), "kg": _num(rec.get("Variation (kg)"))}
        if any(v not in ("", None) for v in row.values()):
            out.append(row)
    return out


def _new_edition():
    """Établit une nouvelle édition de la loadsheet : numéro suivant, verrouillage levé."""
    st.session_state["ls_edition"] = int(st.session_state.get("ls_edition", 1)) + 1
    st.session_state.pop("locked", None)


def render_admin_tab(user_info: dict, users: dict):
    st.subheader("📜 Journal et comptes")
    role = user_info.get("role")
    if role not in ("admin", "dispatcher"):
        st.info("Accès réservé aux profils admin et dispatcher.")
        return
    st.markdown("### Journal des actions")
    st.caption("Le journal est conservé sur le serveur de l'application : l'hébergement gratuit peut l'effacer lors d'un "
               "redémarrage. Exportez-le régulièrement.")
    entries = read_json_fresh(AUDIT_FILE)
    entries = entries if isinstance(entries, list) else []
    f1, f2 = st.columns(2)
    ev_sel = f1.multiselect("Événement", sorted({e.get("event", "") for e in entries}), key="audit_ev")
    usr_txt = f2.text_input("Utilisateur ou nom contient", key="audit_user").strip().lower()
    rows = [e for e in entries if (not ev_sel or e.get("event") in ev_sel)
            and (not usr_txt or usr_txt in f"{e.get('user', '')} {e.get('name', '')}".lower())]
    if rows:
        df = pd.DataFrame(rows)[["t", "user", "name", "event", "detail"]]
        df.columns = ["Date (UTC)", "Compte", "Nom", "Événement", "Détail"]
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.download_button("⬇ Exporter le journal (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                           f"journal_aetherdispatch_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="audit_csv")
    else:
        st.info("Aucun événement enregistré.")

    if role != "admin":
        st.caption("L'assistant de création de comptes est réservé au profil admin.")
        return
    st.markdown("---")
    st.markdown("### Assistant de création de comptes")
    st.caption("Les comptes sont définis dans le fichier users.json du dépôt. Cet assistant prépare le contenu complet du "
               "fichier avec le nouveau compte (mot de passe haché et salé). L'application ne conserve aucun mot de passe.")
    c1, c2, c3 = st.columns(3)
    login = c1.text_input("Identifiant", key="acc_login").strip()
    full_name = c2.text_input("Nom et prénom", key="acc_name").strip()
    role_sel = c3.selectbox("Profil", ["agent", "dispatcher", "admin"], key="acc_role")
    kind = st.radio("Type de compte", ["Individuel", "Partagé"], horizontal=True, key="acc_kind",
                    help="Un compte partagé n'identifie pas la personne qui prépare la loadsheet : celle-ci devra saisir son nom.")
    mode = st.radio("Mot de passe", ["Générer un mot de passe robuste", "Saisir un mot de passe"], horizontal=True, key="acc_mode")
    if mode.startswith("Saisir"):
        pwd = st.text_input("Mot de passe (12 caractères minimum)", type="password", key="acc_pwd")
        generated = False
    else:
        pwd = st.session_state.setdefault("acc_gen_pwd", generate_password())
        st.text_input("Mot de passe généré", pwd, disabled=True, key="acc_pwd_show")
        st.button("Générer un autre mot de passe", on_click=lambda: st.session_state.update(acc_gen_pwd=generate_password()),
                  key="acc_regen")
        generated = True
    valid_login = bool(login) and all(ch.isalnum() or ch in "._-" for ch in login)
    if login and not valid_login:
        st.error("Identifiant : lettres, chiffres, point, tiret et tiret bas uniquement.")
    if not generated and pwd and len(pwd) < 12:
        st.error("Le mot de passe doit comporter au moins 12 caractères.")
    ready = valid_login and bool(full_name) and bool(pwd) and (generated or len(pwd) >= 12)
    if st.button("Préparer le compte", key="acc_make", disabled=not ready):
        entry = {**hash_password_pbkdf2(pwd), "role": role_sel, "nom": full_name,
                 "type": "partagé" if kind == "Partagé" else "individuel"}
        st.session_state["acc_result"] = {"login": login, "password": pwd if generated else None, "exists": login in users,
                                          "json": json.dumps({**users, login: entry}, ensure_ascii=False, indent=2)}
        audit("account_prepared", f"{login} ({role_sel}, {entry['type']})")
        if generated:
            st.session_state.pop("acc_gen_pwd", None)
    res = st.session_state.get("acc_result")
    if res:
        st.success(f"Compte « {res['login']} » préparé" + (" (il remplace le compte existant du même nom)." if res["exists"] else "."))
        if res["password"]:
            st.warning(f"Mot de passe à transmettre à l'utilisateur par un canal sûr : **{res['password']}**  "
                       "Il n'est affiché qu'ici et n'est conservé nulle part.")
        st.markdown("Sur GitHub : ouvrez `users.json`, cliquez sur le crayon, sélectionnez tout (Ctrl+A), collez le contenu "
                    "ci-dessous, puis « Commit changes ». L'application redémarre seule.")
        st.code(res["json"], language="json")
        st.button("Effacer ce résultat", on_click=lambda: st.session_state.pop("acc_result", None), key="acc_clear")


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
            <div style="font-size:0.65rem;color:#556688;letter-spacing:1.5px;margin-top:2px">v5.0 | EG CONSEIL</div>
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
            audit("logout", "")
            for key in ["authenticated", "username", "user_info", "db", "profile_info", "dirty", "sel_ac", "ed_version", "pax_info", "referentiel", "flight_summary", "fuel_in", "ref_docs", "ref_docs_ver", "preparer_name", "cdb_name", "locked", "ls_edition", "wx", "wx_sel", "lmc_editor", "acc_result", "acc_gen_pwd", "flight_date", "flight_time"]:
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
    if user_info.get("type") == "partagé":
        st.info("Compte partagé : il n'identifie pas la personne qui prépare la loadsheet. Saisissez votre nom et prénom "
                "dans le champ « Préparé par » (onglet « Nouveau vol »).")
    missing = missing_fields(ac)
    blocked = bool(missing)

    # ── Onglets ───────────────────────────────────────────────────────────────
    tab1, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📋 Nouveau vol",
        "📈 Performances & V-Speeds",
        "⛽ Carburant & Météo",
        "🧠 Optimisation Cargo",
        "📄 Export PDF",
        "🗂 Historique",
        "🛠 Données aéronef",
        "📜 Journal et comptes"
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
                st.caption("Le vent n'intervient pas dans ce calcul. Valeurs indicatives (formule approchée), "
                           "à ne pas utiliser en exploitation.")

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
                                   wind_kt_fuel, rwy_alt_ft, oat_fuel,
                                   alt_dist_nm=st.session_state.get("alt_dist_nm", 200.0))

            # ── Tableau carburant ─────────────────────────────────────────────────
            st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
            st.markdown("### ⛽ Plan carburant détaillé")

            fuel_items = [
                ("Trip Fuel", fp["trip_fuel_kg"], "Carburant de route"),
                ("Contingence (5%)", fp["contingency_kg"], "Marge réglementaire"),
                ("Alternate Fuel", fp["alt_fuel_kg"], f"dégagement le plus éloigné : {fp['alt_dist_nm']:.0f} NM"),
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

        # ── Météo : METAR et TAF ──────────────────────────────────────────────
        st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
        st.markdown("### 🌍 Météo aéroports — METAR et TAF")
        ap_all = list(airports.keys())
        flight_aps = []
        for n_ in [st.session_state.get("origin"), st.session_state.get("dest")] + list(st.session_state.get("alternates", [])):
            if n_ in ap_all and n_ not in flight_aps:
                flight_aps.append(n_)
        st.session_state.setdefault("wx_sel", flight_aps or ap_all[:3])

        def _use_flight_airports():
            st.session_state["wx_sel"] = flight_aps or ap_all[:3]

        sel = st.multiselect("Aéroports à interroger", ap_all, key="wx_sel")
        wc1, wc2 = st.columns([1, 2])
        wc2.button("Utiliser les aéroports du vol", on_click=_use_flight_airports, key="wx_use_flight")
        if wc1.button("🔄 Actualiser la météo", key="wx_refresh"):
            items = []
            with st.spinner("Interrogation du service météo..."):
                for ap_name in sel:
                    icao = airports[ap_name]["icao"]
                    items.append({"name": ap_name, "icao": icao, "metar": fetch_metar(icao), "taf": fetch_taf(icao)})
            st.session_state["wx"] = {"fetched_at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M"), "items": items}
        wx = st.session_state.get("wx")
        if not wx:
            st.info("Cliquez sur « Actualiser la météo » pour récupérer les METAR et les TAF en temps réel.")
        else:
            st.caption(f"Interrogé le {wx['fetched_at']} UTC · source : NOAA / NWS Aviation Weather Center (aviationweather.gov). "
                       "Source non contractuelle : à vérifier auprès du service météorologique compétent pour la préparation opérationnelle.")
            for it in wx["items"]:
                mt, tf = it["metar"], it["taf"]
                cat = mt.get("category", "INCONNUE")
                col = flight_cat_color(cat)
                metar_html = (f'<div style="font-family:monospace;font-size:0.78rem;color:#A0B0D0;margin:6px 0;'
                              f'background:#050510;padding:6px 10px;border-radius:4px">{_html.escape(mt["raw"])}</div>'
                              f'<div style="font-size:0.78rem;color:#8899BB">{_html.escape(wx_decoded_line(mt))}</div>'
                              if mt.get("ok") else
                              f'<div style="color:#FF8888;font-size:0.8rem;margin:6px 0">METAR indisponible : {_html.escape(mt.get("error", ""))}</div>')
                taf_html = (f'<div style="font-family:monospace;font-size:0.76rem;color:#A0B0D0;margin:6px 0;background:#050510;'
                            f'padding:6px 10px;border-radius:4px">{"<br>".join(_html.escape(l) for l in tf["raw"].splitlines())}</div>'
                            if tf.get("ok") else
                            f'<div style="color:#E0B060;font-size:0.8rem;margin:6px 0">TAF indisponible : {_html.escape(tf.get("error", ""))}</div>')
                st.markdown(f"""
                <div style="background:#0D1F3C;border:1px solid {col}55;border-radius:8px;padding:10px 14px;margin:8px 0">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div><span style="font-weight:700;color:{col};font-size:1rem">{it['icao']}</span>
                             <span style="color:#556688;font-size:0.8rem;margin-left:8px">{_html.escape(it['name'])}</span></div>
                        <span style="background:{col}22;color:{col};border:1px solid {col};border-radius:12px;
                              padding:2px 10px;font-size:0.75rem;font-weight:700">{cat}</span>
                    </div>
                    <div style="color:#8899BB;font-size:0.72rem;margin-top:6px">METAR</div>{metar_html}
                    <div style="color:#8899BB;font-size:0.72rem;margin-top:4px">TAF</div>{taf_html}
                </div>
                """, unsafe_allow_html=True)
            if st.button("📄 Générer le briefing météo (PDF)", key="wx_pdf_btn"):
                ctx = st.session_state.get("flight_info") or {}
                wx_bytes = generate_wx_pdf(wx, ctx)
                st.download_button("⬇ Télécharger le briefing météo", data=wx_bytes,
                                   file_name=f"AETHERDISPATCH_meteo_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                                   mime="application/pdf", key="wx_pdf_dl", use_container_width=True)


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

        history = read_json_fresh("flight_history.json")
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
                "Édition": str(h.get("edition", "—")),
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

    # =========================================================================
    # ONGLET 9 : JOURNAL DES ACTIONS ET ASSISTANT DE COMPTES
    # =========================================================================
    with tab9:
        render_admin_tab(user_info, users)

    # ── Footer ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="aether-footer">
        AETHERDISPATCH v5.0 — EG Conseil & Lobbying © 2026 — Système de gestion handling aérien augmenté par IA<br>
        Données à usage opérationnel restreint — Vérification obligatoire par le commandant de bord
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================
if __name__ == "__main__":
    main()
