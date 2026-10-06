# =============================================================================
# AETHERDISPATCH v6.2 — Agent IA Handling Aérien
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
try:
    import ahm565 as AHM          # import des fichiers AHM (PDF) : facultatif
except Exception:
    AHM = None
try:
    import uldplan as ULDP        # répartition préliminaire des ULD et des soutes en vrac : facultatif
except Exception:
    ULDP = None
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


# ── Aéroports : libellés, valeurs manquantes, regroupement par pays ──────────
def ap_label(ap: dict) -> str:
    """Libellé affiché dans les listes : OACI / IATA – nom (ville). Permet de chercher par code IATA."""
    codes = ap["icao"] + (f" / {ap['iata']}" if ap.get("iata") else "")
    city = ap.get("city") or ""
    nm = ap.get("name") or ""
    tail = f" ({city})" if city and city.lower() not in nm.lower() else ""
    return f"{codes} – {nm}{tail}"


def ap_elev_ft(ap: dict) -> int:
    """Altitude de l'aérodrome ; 0 si elle n'est pas renseignée (l'écran l'indique)."""
    v = ap.get("elev_ft")
    return int(v) if isinstance(v, (int, float)) else 0


def ap_rwy_text(ap: dict) -> str:
    v = ap.get("rwy_length_m")
    return f"{int(v):,}".replace(",", " ") if isinstance(v, (int, float)) else "n.c."


def ap_groups(ap: dict) -> list:
    """Groupes de pays d'un aéroport (filtre météo). La France d'outre-mer est un groupe à part."""
    c = ap.get("country") or "Autre"
    out = []
    for part in c.split("/"):
        part = part.strip()
        out.append("France – outre-mer" if part.endswith("(France)") else part)
    return out

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
        AETHERDISPATCH v6.2 | EG Conseil & Lobbying © 2026
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


CG_ENV_KEYS = {"zfw": "cg_envelope_zfw", "tow": "cg_envelope", "law": "cg_envelope_law"}


def cg_env_for(ac: dict, state: str):
    """Enveloppe de centrage d'un état (« zfw », « tow », « law ») : liste de points, ou None si elle n'est pas renseignée."""
    key = CG_ENV_KEYS.get(state, "cg_envelope") if ac.get("cg_limits_by_state") else "cg_envelope"
    env = _valid_pts(ac.get(key), "weight_kg", "fwd_m", "aft_m")
    return env if len(env) >= 2 else None


def cg_limits_at(ac: dict, weight: float, state: str = None):
    """Limites de centrage (avant, arrière) à une masse donnée : enveloppe si elle est renseignée, sinon limites constantes.
    Pour un type importé d'un AHM (une enveloppe par état), `state` choisit l'enveloppe. Renvoie None pour l'atterrissage
    quand le fichier de la compagnie n'en définit pas : la limite est alors « non définie par la compagnie »."""
    env = cg_env_for(ac, state)
    if env is not None:
        return _interp(env, weight, "weight_kg", "fwd_m"), _interp(env, weight, "weight_kg", "aft_m")
    if ac.get("cg_limits_by_state") and state == "law":
        return None
    return ac["cg_min_m"], ac["cg_max_m"]


def compute_mc(ac: dict, pax_zone_weights: dict, cargo_weights: dict, fuel_kg: float,
               extra_items=None, crew_delta_kg: float = 0.0, trip_kg: float = 0.0, cargo_moments=None) -> dict:
    """
    Masse et centrage : DOW, ZFW, TOW et LW, avec le centrage de chacun (en mètres).
    - fuel_kg : carburant au décollage ; trip_kg : carburant consommé en vol (pour la masse à l'atterrissage).
    - extra_items : autres masses (lest, consommables) sous la forme [(masse_kg, bras_m), ...], incluses dans le ZFW.
    - crew_delta_kg : écart d'équipage par rapport à la composition standard (appliqué au bras de l'équipage).
    - Le bras du carburant dépend de la quantité lorsqu'une table est renseignée (sinon bras unique).
    - cargo_moments : {soute: moment (kg.m)} imposé pour les soutes chargées en ULD (somme masse x bras de chaque position).
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
        cargo_moment += (cargo_moments or {}).get(comp["name"], w * comp["arm_m"])

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
        "raw_cg": {"dow": dow_cg, "zfw": zfw_cg, "tow": tow_cg, "lw": lw_cg},
        "raw_mass": {"zfw": zfw, "tow": tow, "lw": zfw + rem_fuel},
        "raw_moment": {"zfw": zfw_moment, "tow": tow_moment, "lw": lw_moment},
    }


def plot_cg_envelope(ac: dict, result: dict, trip_fuel: float = 0) -> go.Figure:
    """Enveloppe masse-centrage (x = mètres) avec les points ZFW, TOW et LW.
    Type importé d'un AHM : une enveloppe par état (ZFW, TOW, et atterrissage si le fichier en définit une)."""
    def outline(env):
        env = sorted(env, key=lambda p: p["weight_kg"])
        ws = [p["weight_kg"] for p in env]
        xs = [p["fwd_m"] for p in env] + [p["aft_m"] for p in reversed(env)]
        ys = ws + list(reversed(ws))
        return xs + [xs[0]], ys + [ys[0]]

    fig = go.Figure()
    envs = []
    if ac.get("cg_limits_by_state"):
        for st_, lab, col, dash in (("zfw", "Limites ZFW", "#FFD700", "dash"), ("tow", "Limites TOW", "#00BFFF", "solid"),
                                    ("law", "Limites atterrissage", "#7B2FBE", "dot")):
            e_ = cg_env_for(ac, st_)
            if e_:
                envs.append((lab, e_, col, dash))
    else:
        e_ = cg_env_for(ac, "tow")
        if e_:
            envs.append(("Limites de centrage", e_, "#00BFFF", "solid"))
    if envs:
        lo = min(p["fwd_m"] for _, e_, _, _ in envs for p in e_)
        hi = max(p["aft_m"] for _, e_, _, _ in envs for p in e_)
        for lab, e_, col, dash in envs:
            xs, ys = outline(e_)
            fig.add_trace(go.Scatter(x=xs, y=ys, fill='toself' if dash == "solid" else None,
                                     fillcolor='rgba(0, 191, 255, 0.08)', line=dict(color=col, width=2, dash=dash),
                                     name=lab, hoverinfo='skip'))
        title = "Enveloppe Masse & Centrage"
        if ac.get("cg_limits_by_state") and cg_env_for(ac, "law") is None:
            title += " (atterrissage : limite non définie par la compagnie)"
    else:
        lo, hi = ac["cg_min_m"], ac["cg_max_m"]
        dow = ac["oew_kg"] + (ac.get("crew_kg") or 0)
        xs = [lo, lo, hi, hi, lo]
        ys = [dow, ac["max_tow_kg"], ac["max_tow_kg"], dow, dow]
        title = "Masse & Centrage (limites constantes : enveloppe non renseignée)"
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
                    oat_c: float, rwy_length_m, flap_conf: str) -> dict:
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
    if isinstance(rwy_length_m, (int, float)) and rwy_length_m < 2500:
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
        return {"ok": False, "raw": "", "category": "INCONNUE", "error": "aucun METAR publié pour cette station (fréquent pour les petits aérodromes sans observation diffusée)"}
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
    if fs.get("uld_plan"):
        bag_lab = "Bagages (ULD et vrac)"
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
             aligns=["L", "R", "R", "R", "R", "R"], colors=colors, gap=(0.2 if fs.get("uld_plan") else 1.4))
        if fs.get("uld_plan"):
            pdf.set_x(10)
            pdf.set_font("Helvetica", "I", 6.8)
            pdf.set_text_color(*GREY)
            pdf.cell(190, 3.4, f"Soutes chargées en ULD : total = masse brute, tare comprise ({n(fs.get('uld_tare_total', 0))} kg de tare). "
                               "Détail position par position sur la page suivante.", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

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
    # ── Plan de chargement ULD ────────────────────────────────────────────
    _plan = fs.get("uld_plan") or []
    if _plan:
        pdf.add_page()
        pdf.set_y(12)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*GREY)
        pdf.cell(190, 5, f"LOAD & TRIM SHEET - Vol {fs.get('flight_number') or '-'} - Édition n°{fs.get('edition', 1)} (suite)",
                 align='C', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        section("PLAN DE CHARGEMENT ULD (masse brute = contenu + tare)")
        _hd = ("Position", "ULD", "Nature", "Contenu", "Tare", "Brut")
        _wd = [22, 13, 20, 14, 12, 14]
        half = (len(_plan) + 1) // 2
        _cols = [_plan[:half], _plan[half:]] if len(_plan) > 14 else [_plan, []]
        y0 = pdf.get_y()
        for ci, chunk in enumerate(_cols):
            if not chunk:
                continue
            x0 = 10 + ci * 96
            pdf.set_xy(x0, y0)
            pdf.set_fill_color(*HEAD)
            pdf.set_text_color(*NAVY)
            pdf.set_font("Helvetica", "B", 7.2)
            for t_, w_ in zip(_hd, _wd):
                pdf.cell(w_, 4.8, t_, border=1, align='C', fill=True)
            yy = y0 + 4.8
            for ri, x_ in enumerate(chunk):
                pdf.set_xy(x0, yy)
                pdf.set_fill_color(*(ZEBRA if ri % 2 else (255, 255, 255)))
                pdf.set_text_color(*TEXT)
                pdf.set_font("Helvetica", "", 7.2)
                vals = (x_["pos"][:12], x_["uld"], x_["nature"][:8], n(x_["content"]), n(x_["tare"]), n(x_["gross"]))
                for v_, w_, al in zip(vals, _wd, ("L", "C", "L", "R", "R", "R")):
                    pdf.cell(w_, 4.6, str(v_), border=1, align=al, fill=True)
                yy += 4.6
        pdf.set_y(y0 + 4.8 + 4.6 * len(_cols[0]) + 2)
        tot_c = sum(x_["content"] for x_ in _plan)
        tot_t = sum(x_["tare"] for x_ in _plan)
        band(f"{len(_plan)} position(s) chargée(s) | contenu {n(tot_c)} kg | tare {n(tot_t)} kg | brut {n(tot_c + tot_t)} kg"
             + ("" if fs.get("uld_ok", True) else " | CONTRÔLE ULD A CORRIGER"), GREEN if fs.get("uld_ok", True) else RED, gap=1.6)

    if pdf.get_y() > 297 - 31 - 84 - (10 if fs.get("ahm_print") else 0):
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
          ("Équipage", f"PNT {crew.get('flight', '-')} / PNC {crew.get('cabin', '-')}", "Écart d'équipage",
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
        if key == "lw" and fs.get("lw_cg_defined") is False:
            crows.append((lab, n(w), f"{cg:.2f}", "n.d.", "n.d.", "NON DEFINIE"))
            ccol[(i, 5)] = GREY
            continue
        lo, hi = (lims.get(key) or [fs.get("cg_min", 0), fs.get("cg_max", 0)])
        txt, col = state(bool(ok), "OK", "HORS LIMITES")
        crows.append((lab, n(w), f"{cg:.2f}", f"{lo:.2f}", f"{hi:.2f}", txt))
        ccol[(i, 5)] = col
    grid(crows, [34, 32, 32, 32, 32, 28], header=True, bold_cols=(0,), aligns=["L", "R", "R", "R", "R", "C"],
         colors=ccol, gap=1.0)
    _ap = fs.get("ahm_print") or {}
    if _ap:
        _k = list(_ap.keys())
        _w = 190.0 / len(_k)
        grid([tuple(_k), tuple(_ap[x] for x in _k)], [_w] * len(_k), header=True, aligns=["C"] * len(_k), gap=0.6)
        pdf.set_x(10)
        pdf.set_font("Helvetica", "I", 6.8)
        pdf.set_text_color(*GREY)
        _src = fs.get("ahm_ref") or {}
        pdf.cell(190, 3.4, f"Indices selon la formule du fichier AHM ({_src.get('organisme') or '-'}, édition "
                           f"{_src.get('edition') or '-'}), imprimés car prévus par ce fichier.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.8)
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
    pdf.cell(190, 3.8, "Document généré par AETHERDISPATCH v6.2. Vérification obligatoire par le commandant de bord.",
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
    ("crew_std_flight", "PNT standard (nombre)", "pers.", False),
    ("crew_std_cabin",  "PNC standard (nombre)",   "pers.", False),
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


MC_FIELDS = SCALAR_FIELDS      # données de masse et centrage (hors vitesses et performances)


def missing_fields(ac: dict, scope: str = "all") -> list:
    """Liste des données obligatoires manquantes (vide = calculs possibles).
    scope « mc » : uniquement ce qui est nécessaire à la masse et au centrage (les vitesses et performances ne bloquent pas la loadsheet)."""
    fields = MC_FIELDS if scope == "mc" else ALL_FIELDS
    out = [label for key, label, unit, req in fields if req and get_field(ac, key) is None]
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


def origin_counts(ac: dict, scope: str = "all") -> dict:
    counts = {k: 0 for k in STATUS_LABELS}
    for key, label, unit, req in (MC_FIELDS if scope == "mc" else ALL_FIELDS):
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


def origin_summary(ac: dict, scope: str = "all"):
    """Texte récapitulatif de l'origine des données + indicateur « entièrement issu de la compagnie »."""
    c = origin_counts(ac, scope)
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
                 "de 85 kg (PNT, équipage de conduite) et 75 kg (PNC, équipage de cabine)")


def default_referentiel() -> dict:
    def item(label, value, src):
        return {"label": label, "value": value, "status": "reglementaire", "source": src}
    return {
        "identification": {"organisme": "", "document": "", "version": "", "date_application": ""},
        "pax_masses": {"male": item("Hommes", 88, SRC_EASA_PAX), "female": item("Femmes", 70, SRC_EASA_PAX),
                       "child": item("Enfants", 35, SRC_EASA_PAX), "infant": item("Bébés", 0, SRC_EASA_INF)},
        "bag_masses": {"domestic": item("Vol intérieur", 11, SRC_BAG), "other": item("Autres vols", 13, SRC_BAG),
                       "intercontinental": item("Vol intercontinental", 15, SRC_BAG)},
        "crew_masses": {"flight": item("PNT", 85, SRC_EASA_CREW),
                        "cabin": item("PNC", 75, SRC_EASA_CREW)},
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
    wk = selected_ac + ("·" + str(ac["ahm_selection"]["config"]) if ac.get("ahm_selection") else "")   # clé des widgets
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
                          key=f"ls_status_{wk}")
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
                                             key=f"pax_{prefix}_{k}_{wk}"))
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
                                        key=f"paxz_{wk}_{i}_{status}_{seated}")
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


def compute_ahm_indices(ac: dict, result: dict):
    """Indices DOI, LIZFW, LITOW, LILAW, %MAC et calage du stabilisateur au décollage, avec la formule du fichier AHM.
    Renvoie None si le type n'a pas été importé d'un AHM."""
    h = ac.get("ahm")
    if not (AHM and h and result.get("raw_cg")):
        return None
    raw = result["raw_cg"]
    pct = {k: AHM.pct_mac_of(h, raw[k]) for k in ("zfw", "tow", "lw")}
    vals = {"DOI": AHM.index_of(h, result["dow"], raw["dow"]), "LIZFW": AHM.index_of(h, result["zfw"], raw["zfw"]),
            "LITOW": AHM.index_of(h, result["tow"], raw["tow"]), "LILAW": AHM.index_of(h, result["lw"], raw["lw"]),
            "MACZFW": pct["zfw"], "MACTOW": pct["tow"], "MACLAW": pct["lw"],
            "STABTO": AHM.stab_value(h.get("stab"), result["tow"], pct["tow"])}
    text = {}
    for k, v in vals.items():
        if v is None:
            continue
        text[k] = f"{v:.1f} %" if k.startswith("MAC") else (f"{v:.1f}" if k != "STABTO" else f"{v:.1f}")
    flags = h.get("impression") or {}
    return {"values": vals, "text": text, "print": [k for k in text if flags.get(k)]}


def render_pax_comparison(ac: dict, pax: dict, comp_loads: dict, tof: float, extra_items=None, crew_delta: float = 0.0,
                          cargo_moments=None):
    """Tableau prévu / final : sièges, bébés, ZFW, TOW, centrage."""
    st.markdown("**Comparaison prévu / final**")
    if not pax["has_final"]:
        st.caption("PAX final non saisi : la comparaison s'affichera dès qu'il le sera.")
        return

    def scenario(counts):
        return compute_mc(ac, zone_weights_from_counts(ac, counts, pax["masses"]), comp_loads, tof,
                          extra_items=extra_items, crew_delta_kg=crew_delta, cargo_moments=cargo_moments)

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
ULD_NATURES = ["Bagages", "Fret", "Courrier"]


def uld_conflicts(rows: list) -> list:
    """Paires de positions occupées qui se gênent : même côté de la soute et intervalles de bras qui se recouvrent."""
    out = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a["hold"] != b["hold"] or not (set(a["sides"]) & set(b["sides"])):
                continue
            if min(a["to_m"], b["to_m"]) - max(a["from_m"], b["from_m"]) > 0.03:
                out.append((a, b))
    return out


def render_uld_plan(ac: dict, wk: str):
    """Plan de chargement par position (conteneurs, palettes, pleine largeur). Renvoie un dict de résultats, ou None."""
    U = ac.get("uld") or {}
    rows = U.get("rows") or []
    if not rows:
        return None
    st.markdown("**🧱 Plan de chargement des ULD (positions du fichier AHM)**")
    st.caption("Saisissez le contenu de chaque ULD chargé : le centrage est calculé au bras exact de la position. "
               "La masse maximale de la position s'applique à la masse brute (contenu + tare). "
               "Une position vide reste à 0 kg.")
    types = sorted({t_ for r_ in rows for t_ in r_["types"]})
    specs = {sp_["type"]: sp_.get("tare") for sp_ in (U.get("specs") or []) if sp_.get("type")}
    tare_by = {}
    if types:
        st.markdown("Tare par type de ULD (kg)")
        for col, t_ in zip(st.columns(len(types)), types):
            tare_by[t_] = float(col.number_input(t_, 0.0, 2000.0, float(specs.get(t_) or 0.0), step=1.0, key=f"uldtare_{wk}_{t_}"))
        if not any(tare_by.values()):
            st.warning("Tares non renseignées (feuille B5 du fichier vide) : la masse brute des ULD est sous-estimée tant "
                       "que les tares ne sont pas saisies.")
    all_types = types or ["ULD"]
    holds = list(dict.fromkeys(r_["hold"] for r_ in rows))
    _ap = st.session_state.get(f"uld_applied_{wk}") or {}                # proposition appliquée (préremplissage)
    _amap = _ap.get("plan") or {}
    _ks = f"_v{_ap['ver']}" if _ap.get("ver") else ""
    edited = {}
    for tab, hold in zip(st.tabs([f"Soute {h_}" for h_ in holds]), holds):
        with tab:
            hr = [r_ for r_ in rows if r_["hold"] == hold]
            df = pd.DataFrame({"Position": [r_["label"] for r_ in hr],
                               "ULD": [(_amap.get(r_["label"]) or {}).get("uld") or (r_["types"] or all_types)[0] for r_ in hr],
                               "Nature": [(_amap.get(r_["label"]) or {}).get("nature") or "Bagages" for r_ in hr],
                               "Contenu (kg)": [float((_amap.get(r_["label"]) or {}).get("content") or 0.0) for r_ in hr],
                               "Tare (kg)": pd.Series([None] * len(hr), dtype="float64"),
                               "Maxi position (kg)": [r_["max_kg"] for r_ in hr]})
            edited[hold] = st.data_editor(
                df, hide_index=True, use_container_width=True, num_rows="fixed", key=f"uldplan_{wk}_{hold}{_ks}",
                disabled=["Position", "Maxi position (kg)"],
                column_config={"ULD": st.column_config.SelectboxColumn("ULD", options=all_types),
                               "Nature": st.column_config.SelectboxColumn("Nature", options=ULD_NATURES),
                               "Contenu (kg)": st.column_config.NumberColumn("Contenu (kg)", min_value=0, step=10),
                               "Tare (kg)": st.column_config.NumberColumn("Tare (kg)", min_value=0, step=1,
                                                                          help="Vide : tare du type de ULD."),
                               "Maxi position (kg)": st.column_config.NumberColumn("Maxi position (kg)", format="%.0f")})
    res = {"loads": {}, "moments": {}, "nat": {}, "plan": [], "errors": [], "tare_total": 0.0, "content_total": 0.0,
           "tare_by": dict(tare_by), "types": list(all_types)}
    occupied = []
    for hold in holds:
        hr = [r_ for r_ in rows if r_["hold"] == hold]
        for r_, rec in zip(hr, edited[hold].to_dict("records")):
            content = rec.get("Contenu (kg)")
            content = 0.0 if content is None or content != content else float(content)
            if content <= 0:
                continue
            ut = rec.get("ULD") or all_types[0]
            tare = rec.get("Tare (kg)")
            tare = tare_by.get(ut, 0.0) if tare is None or tare != tare else float(tare)
            gross = content + tare
            nat = rec.get("Nature") or "Bagages"
            if r_["types"] and ut not in r_["types"]:
                res["errors"].append(f"Position {r_['label']} : le type {ut} n'est pas compatible (types admis : {', '.join(r_['types'])}).")
            if gross > r_["max_kg"] + 1e-9:
                res["errors"].append(f"Position {r_['label']} : {gross:,.0f} kg bruts pour un maximum de {r_['max_kg']:,.0f} kg.")
            c = r_["comp"]
            res["loads"][c] = res["loads"].get(c, 0.0) + gross
            res["moments"][c] = res["moments"].get(c, 0.0) + gross * r_["arm_m"]
            nd = res["nat"].setdefault(c, {"Bagages": 0.0, "Fret": 0.0, "Courrier": 0.0})
            nd[nat] = nd.get(nat, 0.0) + content
            res["tare_total"] += tare
            res["content_total"] += content
            res["plan"].append({"pos": r_["label"], "hold": hold, "uld": ut, "nature": nat, "content": content, "tare": tare,
                                "gross": gross, "arm": r_["arm_m"], "max": r_["max_kg"], "comp": c})
            occupied.append(r_)
    for a, b in uld_conflicts(occupied):
        res["errors"].append(f"Positions {a['label']} et {b['label']} : occupées en même temps alors qu'elles se recouvrent.")
    for m_ in res["errors"]:
        st.error(m_)
    if res["plan"] and types and not any(tare_by.values()):
        pass
    n_pos = len(res["plan"])
    st.caption(f"{n_pos} position(s) chargée(s) · contenu {res['content_total']:,.0f} kg · tare {res['tare_total']:,.0f} kg · "
               f"masse brute {res['content_total'] + res['tare_total']:,.0f} kg.")
    res["ok"] = not res["errors"]
    return res


# ── Proposition préliminaire de répartition et plan de chargement (PDF) ──────
PLAN_COL = {"Bagages": (150, 185, 235), "Fret": (245, 190, 120), "Courrier": (150, 210, 155)}


def _plan_src(fs: dict) -> str:
    """Mention de la source des données du plan : fichier AHM de la compagnie (organisme, édition, date) ou référentiel."""
    r = fs.get("ahm_ref") or {}
    if r.get("organisme") or r.get("edition"):
        txt = f"AHM {r.get('organisme') or ''} éd. {r.get('edition') or '?'}" + (f" du {r['date']}" if r.get("date") else "")
        return txt.strip()[:46]
    return "données de l'application (type de base)"


def generate_loading_plan_pdf(d: dict) -> bytes:
    """
    Plan de chargement A4 (document préliminaire) : vol, charge à placer, nombre de ULD (ou répartition par soute),
    schéma des soutes, détail position par position (ou soute par soute), totaux par soute et par groupe, centrage,
    hypothèses retenues et espace de signatures.
    d : mode ("uld" ou "bulk"), label, fs, loads, bag_text, plan, rows, comps, other, n_uld, theory, avg, tare, cg, notes.
    """
    class _PlanPDF(FPDF):
        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 6.8)
            self.set_text_color(110, 110, 110)
            self.cell(0, 4, f"AETHERDISPATCH - Plan de chargement {d.get('label', '').lower()} - document à confirmer par l'agent de "
                            f"chargement avant exécution - page {self.page_no()}", align="C")

    pdf = _PlanPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    pdf.normalize_text = lambda t: str(t).replace('→', '->').replace('—', '-').replace('–', '-').replace('─', '-').replace('−', '-').replace('€', 'EUR').replace('×', 'x').replace('≥', '>=').replace('≤', '<=').encode('latin-1', 'replace').decode('latin-1')
    NAVY, CYAN = (13, 31, 60), (0, 191, 255)
    HEAD, ZEBRA = (214, 228, 244), (244, 247, 252)
    GREEN, RED, TEXT, GREY = (0, 130, 70), (190, 30, 30), (30, 30, 30), (110, 110, 110)
    H = 4.6
    fs = d.get("fs") or {}
    mode = d.get("mode", "uld")

    def n(v):
        try:
            return f"{int(round(float(v))):,}".replace(",", " ")
        except (TypeError, ValueError):
            return str(v)

    def room(h):
        if pdf.get_y() + h > 297 - 16:
            pdf.add_page()
            pdf.set_y(12)

    def section(title):
        room(14)
        pdf.set_x(10)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*CYAN)
        pdf.set_font("Helvetica", "B", 8.6)
        pdf.cell(190, 5.4, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.5)

    def grid(rows, widths, header=False, bold_rows=(), bold_cols=(), aligns=None, colors=None, gap=1.4, fsz=8.2):
        for r, row in enumerate(rows):
            room(H + 1)
            is_head = header and r == 0
            pdf.set_x(10)
            for c, (txt, w) in enumerate(zip(row, widths)):
                if is_head:
                    pdf.set_fill_color(*HEAD)
                    pdf.set_text_color(*NAVY)
                    pdf.set_font("Helvetica", "B", fsz - 0.4)
                else:
                    pdf.set_fill_color(*(ZEBRA if r % 2 else (255, 255, 255)))
                    pdf.set_text_color(*(colors or {}).get((r, c), TEXT))
                    pdf.set_font("Helvetica", "B" if (r in bold_rows or c in bold_cols) else "", fsz)
                pdf.cell(w, H, str(txt), border=1, align=(aligns[c] if aligns else "L"), fill=True)
            pdf.ln(H)
        pdf.ln(gap)

    def note(text, size=6.9, color=GREY, style="I"):
        pdf.set_x(10)
        pdf.set_font("Helvetica", style, size)
        pdf.set_text_color(*color)
        pdf.multi_cell(190, 3.5, text, new_x="LMARGIN", new_y="NEXT")

    # ── En-tête ───────────────────────────────────────────────────────────
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 25, "F")
    pdf.set_xy(10, 4.5)
    pdf.set_text_color(*CYAN)
    pdf.set_font("Helvetica", "B", 17)
    pdf.cell(190, 9, "PLAN DE CHARGEMENT", align="C")
    pdf.set_xy(10, 15)
    pdf.set_text_color(200, 215, 230)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.cell(190, 5, f"AETHERDISPATCH  |  {d.get('label', 'PRÉLIMINAIRE')}  |  Chargement en {'ULD' if mode == 'uld' else 'vrac'}  |  "
                     f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} UTC", align="C")
    pdf.set_y(28.5)

    section("VOL")
    grid([("Vol", fs.get("flight_number") or "-", "Date / heure (UTC)", fs.get("datetime", "-")),
          ("Départ", fs.get("origin", "-"), "Arrivée", fs.get("dest", "-")),
          ("Immatriculation", fs.get("registration") or "-", "Type",
           (fs.get("type") or "-") + (f" (config. {fs['ahm_config']})" if fs.get("ahm_config") else "")),
          ("Préparé par", fs.get("prepared_by") or "-", "Données", _plan_src(fs))],
         [30, 70, 34, 56], bold_cols=(0, 2))

    # ── Charge à placer ──────────────────────────────────────────────────
    loads = d.get("loads") or {}
    section("CHARGE À PLACER (kg)")
    tot_l = sum(float(loads.get(k, 0) or 0) for k in ("Bagages", "Fret", "Courrier"))
    rows_ = [("", "Bagages", "Fret", "Courrier", "Total"),
             ("Masse (kg)", n(loads.get("Bagages", 0)), n(loads.get("Fret", 0)), n(loads.get("Courrier", 0)), n(tot_l))]
    colors = {}
    if mode == "uld":
        nu = d.get("n_uld") or {}
        th = d.get("theory") or {}
        rows_.append(("Nombre de ULD", nu.get("Bagages", 0), nu.get("Fret", 0), nu.get("Courrier", 0), sum(nu.values())))
        rows_.append(("Minimum par la masse seule", *[(th.get(k) if th.get(k) is not None else "-") for k in ("Bagages", "Fret", "Courrier")],
                      sum(v for v in th.values() if v)))
    else:
        rows_.append(("Bagages (pièces)", d.get("pieces") if d.get("pieces") is not None else "-", "", "", ""))
    grid(rows_, [58, 33, 33, 33, 33], header=True, bold_cols=(0,), bold_rows=(1,), aligns=["L", "C", "C", "C", "C"], gap=0.4,
         colors=colors)
    note(d.get("bag_text") or "")
    pdf.ln(1.2)

    plan = d.get("plan") or []
    if not plan:
        band_y = pdf.get_y()
        pdf.set_x(10)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*RED)
        pdf.cell(190, 8, "Aucune charge répartie : plan vide.", border=1, align="C")
        pdf.ln(10)
    # ── Schéma des soutes ────────────────────────────────────────────────
    if plan and mode == "uld":
        section("SCHÉMA DES SOUTES (avant à gauche ; L = côté gauche, R = côté droit)")
        rows = d.get("rows") or []
        loaded = {x["pos"]: x for x in plan}
        holds = list(dict.fromkeys(r["hold"] for r in rows))
        for hold in holds:
            hr = [r for r in rows if r["hold"] == hold]
            if not hr:
                continue
            room(28)
            lo, hi = min(r["from_m"] for r in hr), max(r["to_m"] for r in hr)
            scale = min(190.0 / max(hi - lo, 0.5), 15.0)
            wdt = (hi - lo) * scale
            x0 = 10 + (190 - wdt) / 2
            h = 7.6
            y0 = pdf.get_y()
            pdf.set_xy(10, y0)
            pdf.set_font("Helvetica", "B", 7.2)
            pdf.set_text_color(*NAVY)
            pdf.cell(190, 3.8, f"Soute {hold}", new_x="LMARGIN", new_y="NEXT")
            yL = y0 + 4.2
            yR = yL + h
            pdf.set_draw_color(190, 190, 190)
            for r in hr:
                if r["kind"] == "C":
                    yy = yL if "L" in r["sides"] else yR
                    pdf.rect(x0 + (r["from_m"] - lo) * scale, yy, (r["to_m"] - r["from_m"]) * scale, h)
            pdf.set_draw_color(40, 40, 40)
            for r in hr:
                x_ = loaded.get(r["label"])
                if not x_:
                    continue
                single = len(r["sides"]) == 1
                yy = yL if (not single or r["sides"][0] == "L") else yR
                hh = h if single else 2 * h
                xx, ww = x0 + (r["from_m"] - lo) * scale, (r["to_m"] - r["from_m"]) * scale
                pdf.set_fill_color(*PLAN_COL.get(x_["nature"], (220, 220, 220)))
                pdf.rect(xx, yy, ww, hh, "DF")
                pdf.set_text_color(*TEXT)
                pdf.set_font("Helvetica", "B", 6.2)
                pdf.set_xy(xx, yy + hh / 2 - 3.2)
                pdf.cell(ww, 3.2, str(r["pos"])[:8], align="C")
                pdf.set_font("Helvetica", "", 5.8)
                pdf.set_xy(xx, yy + hh / 2)
                pdf.cell(ww, 3.0, f"{n(x_['gross'])}", align="C")
            pdf.set_draw_color(0, 0, 0)
            pdf.set_y(yR + h + 3)
        pdf.set_x(10)
        lx = 10
        for k_, col_ in PLAN_COL.items():
            pdf.set_fill_color(*col_)
            pdf.rect(lx, pdf.get_y() + 0.6, 4, 3, "DF")
            pdf.set_xy(lx + 5, pdf.get_y())
            pdf.set_font("Helvetica", "", 6.8)
            pdf.set_text_color(*TEXT)
            pdf.cell(24, 4.2, k_)
            lx += 30
        pdf.set_xy(lx + 6, pdf.get_y())
        pdf.set_text_color(*GREY)
        pdf.cell(110, 4.2, "Valeur affichée : masse brute (contenu + tare), en kg. Position vide : contour gris.")
        pdf.ln(7)
    elif plan and mode == "bulk":
        section("SCHÉMA DES SOUTES (de l'avant vers l'arrière ; barre = taux de remplissage)")
        order = sorted(plan, key=lambda r: r["arm"])
        gap = 3.0
        wsum = sum(max(r["max"], 1.0) for r in order)
        avail = 190 - gap * (len(order) - 1)
        widths = [max(avail * max(r["max"], 1.0) / wsum, 28.0) for r in order]
        k = avail / sum(widths)
        widths = [w * k for w in widths]
        room(34)
        y0, x_ = pdf.get_y(), 10.0
        for r, w in zip(order, widths):
            pdf.set_draw_color(40, 40, 40)
            pdf.rect(x_, y0, w, 29)
            pdf.set_xy(x_, y0 + 0.8)
            pdf.set_font("Helvetica", "B", 6.8)
            pdf.set_text_color(*NAVY)
            pdf.cell(w, 3.6, str(r["comp"])[:int(w / 1.9)], align="C")
            pdf.set_font("Helvetica", "", 6.2)
            pdf.set_text_color(*TEXT)
            for i_, nat in enumerate(("Bagages", "Fret", "Courrier")):
                pdf.set_xy(x_ + 1, y0 + 5 + 3.5 * i_)
                extra = f" ({r['pieces']})" if (nat == "Bagages" and r.get("pieces") is not None) else ""
                pdf.cell(w - 2, 3.4, f"{nat[:4]}. {n(r[nat])} kg{extra}")
            pdf.set_xy(x_ + 1, y0 + 16)
            pdf.set_font("Helvetica", "B", 6.6)
            pdf.cell(w - 2, 3.4, f"{n(r['total'])} / {n(r['max'])} kg")
            ratio = r["total"] / r["max"] if r["max"] else 0
            pdf.set_fill_color(235, 235, 235)
            pdf.rect(x_ + 1, y0 + 21, w - 2, 3.4, "F")
            pdf.set_fill_color(*(GREEN if ratio <= 0.85 else ((230, 150, 0) if ratio <= 1.0 else RED)))
            pdf.rect(x_ + 1, y0 + 21, (w - 2) * min(ratio, 1.0), 3.4, "F")
            pdf.set_xy(x_, y0 + 24.6)
            pdf.set_font("Helvetica", "", 5.8)
            pdf.set_text_color(*GREY)
            pdf.cell(w, 3.2, f"bras {r['arm']:.2f} m - {ratio * 100:.0f} %", align="C")
            x_ += w + gap
        pdf.set_draw_color(0, 0, 0)
        pdf.set_y(y0 + 32)

    # ── Détail ───────────────────────────────────────────────────────────
    if plan and mode == "uld":
        section("DÉTAIL PAR POSITION (masse brute = contenu + tare)")
        rows_ = [("Soute", "Position", "ULD", "Nature", "Contenu", "Tare", "Brut", "Maxi", "Bras (m)")]
        colors = {}
        for i, x in enumerate(plan, start=1):
            rows_.append((x["comp"], x["pos"], x["uld"], x["nature"], n(x["content"]), n(x["tare"]), n(x["gross"]), n(x["max"]),
                          f"{x['arm']:.2f}"))
            if x["gross"] > x["max"] + 1e-9:
                colors[(i, 6)] = RED
        rows_.append(("TOTAL", f"{len(plan)} pos.", "", "", n(sum(x["content"] for x in plan)), n(sum(x["tare"] for x in plan)),
                      n(sum(x["gross"] for x in plan)), "", ""))
        grid(rows_, [42, 30, 14, 20, 18, 14, 18, 18, 16], header=True, bold_rows=(len(rows_) - 1,),
             aligns=["L", "L", "C", "L", "R", "R", "R", "R", "R"], colors=colors, gap=1.2, fsz=7.6)
    elif plan and mode == "bulk":
        section("DÉTAIL PAR SOUTE (kg)")
        rows_ = [("Soute", "Bras (m)", "Bagages", "Pièces", "Fret", "Courrier", "Total", "Maxi", "Taux")]
        colors = {}
        for i, r in enumerate(sorted(plan, key=lambda r: r["arm"]), start=1):
            rows_.append((r["comp"], f"{r['arm']:.2f}", n(r["Bagages"]), r["pieces"] if r.get("pieces") is not None else "-",
                          n(r["Fret"]), n(r["Courrier"]), n(r["total"]), n(r["max"]),
                          f"{(r['total'] / r['max'] * 100 if r['max'] else 0):.0f} %"))
            if r["total"] > r["max"] + 1e-9:
                colors[(i, 6)] = RED
        rows_.append(("TOTAL", "", n(sum(r["Bagages"] for r in plan)), sum(r["pieces"] or 0 for r in plan) if plan and plan[0].get("pieces") is not None else "-",
                      n(sum(r["Fret"] for r in plan)), n(sum(r["Courrier"] for r in plan)), n(sum(r["total"] for r in plan)),
                      n(sum(r["max"] for r in plan)), ""))
        grid(rows_, [44, 18, 20, 16, 20, 20, 20, 20, 12], header=True, bold_rows=(len(rows_) - 1,),
             aligns=["L", "R", "R", "R", "R", "R", "R", "R", "R"], colors=colors, gap=1.2, fsz=7.8)

    # ── Soutes (totaux par soute et par groupe) ──────────────────────────
    comps = d.get("comps") or []
    if plan and mode == "uld" and comps:
        section("TOTAUX PAR SOUTE (kg, tare comprise)")
        rows_ = [("Soute", "Bagages", "Fret", "Courrier", "Tare", "Total brut", "Maxi", "Taux")]
        colors = {}
        gsum = {}
        for i, c in enumerate(comps, start=1):
            xs = [x for x in plan if x["comp"] == c["name"]]
            tot = sum(x["gross"] for x in xs)
            rows_.append((c["name"], n(sum(x["content"] for x in xs if x["nature"] == "Bagages")),
                          n(sum(x["content"] for x in xs if x["nature"] == "Fret")),
                          n(sum(x["content"] for x in xs if x["nature"] == "Courrier")),
                          n(sum(x["tare"] for x in xs)), n(tot), n(c["max"]), f"{(tot / c['max'] * 100 if c['max'] else 0):.0f} %"))
            if tot > c["max"] + 1e-9:
                colors[(i, 5)] = RED
            if c.get("groupe") and c.get("max_groupe") is not None:
                g_ = gsum.setdefault(c["groupe"], [0.0, float(c["max_groupe"])])
                g_[0] += tot
        grid(rows_, [48, 22, 22, 22, 18, 24, 20, 14], header=True, bold_cols=(0,), aligns=["L"] + ["R"] * 7, colors=colors,
             gap=0.8, fsz=7.8)
        for g_, (tot, mx) in gsum.items():
            note(f"Groupe {g_} : {n(tot)} kg pour une limite de groupe de {n(mx)} kg"
                 + ("" if tot <= mx + 1e-9 else "  -  LIMITE DÉPASSÉE"), 7.2, RED if tot > mx + 1e-9 else TEXT, "")
        pdf.ln(1)
    oth = d.get("other") or []
    if oth:
        section("AUTRES SOUTES (vrac, hors plan ULD)")
        rows_ = [("Soute", "Bagages", "Fret", "Courrier", "Total", "Maxi")]
        for o in oth:
            rows_.append((o["name"], n(o["bag"]), n(o["cargo"]), n(o["mail"]), n(o["total"]), n(o["max"])))
        grid(rows_, [58, 26, 26, 26, 27, 27], header=True, bold_cols=(0,), aligns=["L"] + ["R"] * 5, gap=1.2, fsz=7.8)

    # ── Centrage ─────────────────────────────────────────────────────────
    cg = d.get("cg") or {}
    if cg:
        section("MASSES ET CENTRAGE AVEC CE PLAN")
        rows_ = [("État", "Masse (kg)", "Maxi (kg)", "CG (m)", "%MAC", "Limites de centrage (m)", "Contrôle")]
        colors = {}
        for i, (k_, lab) in enumerate((("zfw", "ZFW"), ("tow", "TOW"), ("lw", "LW")), start=1):
            v = cg.get(k_)
            if not v:
                continue
            lim = v.get("lim")
            ok = v.get("ok")
            rows_.append((lab, n(v["mass"]), n(v.get("max")) if v.get("max") else "-", f"{v['cg']:.2f}", f"{v['mac']:.1f}",
                          (f"{lim[0]:.2f} à {lim[1]:.2f}" if lim else "non définie par la compagnie"),
                          ("OK" if ok else "HORS LIMITES") if lim else "non contrôlé"))
            colors[(len(rows_) - 1, 6)] = GREEN if (ok or not lim) else RED
            if v.get("max") and v["mass"] > v["max"]:
                colors[(len(rows_) - 1, 1)] = RED
        grid(rows_, [18, 26, 26, 20, 18, 52, 30], header=True, bold_cols=(0,), aligns=["L", "R", "R", "R", "R", "C", "C"],
             colors=colors, gap=0.6)
        if d.get("target_mac") is not None:
            note(f"Cible de centrage au décollage : {d['target_mac']:.1f} %MAC ({d.get('target_txt', '')}).", 7.2, TEXT, "")
        pdf.ln(1)

    # ── Hypothèses et limites ────────────────────────────────────────────
    notes = d.get("notes") or []
    if notes:
        section("HYPOTHÈSES RETENUES ET LIMITES DU DOCUMENT")
        for t_ in notes:
            note("- " + t_, 7.2, TEXT, "")
        pdf.ln(1)

    # ── Signatures ───────────────────────────────────────────────────────
    room(26)
    section("VISAS")
    y0 = pdf.get_y() + 1
    for i_, lab in enumerate(("Préparé par (dispatch)", "Agent de chargement", "Commandant de bord")):
        x_ = 10 + i_ * 64
        pdf.set_xy(x_, y0)
        pdf.set_draw_color(80, 80, 80)
        pdf.rect(x_, y0, 62, 17)
        pdf.set_xy(x_ + 1, y0 + 0.8)
        pdf.set_font("Helvetica", "B", 7.2)
        pdf.set_text_color(*NAVY)
        pdf.cell(60, 3.6, lab)
        if i_ == 0:
            pdf.set_xy(x_ + 1, y0 + 5)
            pdf.set_font("Helvetica", "", 7.2)
            pdf.set_text_color(*TEXT)
            pdf.cell(60, 3.6, str(fs.get("prepared_by") or "")[:36])
    pdf.set_draw_color(0, 0, 0)
    pdf.set_y(y0 + 19)
    return bytes(pdf.output())


def _apply_uld_prop(wk: str, plan: list):
    """Rappel du bouton « Appliquer » : préremplit le plan de chargement des ULD (nouvelle version des tableaux de saisie)."""
    ap = st.session_state.get(f"uld_applied_{wk}") or {"ver": 0}
    st.session_state[f"uld_applied_{wk}"] = {
        "ver": int(ap.get("ver", 0)) + 1,
        "plan": {x["pos"]: {"uld": x["uld"], "nature": x["nature"], "content": float(x["content"])} for x in plan}}


def _apply_bulk_prop(wk: str, plan: list, bag_total: int):
    """Rappel du bouton « Appliquer » : préremplit le fret, le courrier et les bagages de chaque soute en vrac."""
    cargo = {r["comp"]: int(round(r["Fret"])) for r in plan}
    mail = {r["comp"]: int(round(r["Courrier"])) for r in plan}
    bag = {r["comp"]: int(round(r["Bagages"])) for r in plan}
    used = {nm: cargo[nm] + mail[nm] for nm in cargo}
    ap = st.session_state.get(f"bulk_applied_{wk}") or {"ver": 0}
    st.session_state[f"bulk_applied_{wk}"] = {
        "ver": int(ap.get("ver", 0)) + 1, "cargo": cargo, "mail": mail, "bag": bag,
        "sig": zlib.crc32(repr(sorted(used.items())).encode()), "bag_total": int(bag_total)}
    st.session_state[f"use_cargo_{wk}"] = True


def _cg_state_summary(ac: dict, mcres: dict, fs: dict) -> dict:
    """Masses, centrages (m et %MAC), limites et contrôle pour ZFW, TOW et atterrissage."""
    out = {}
    for k, state, mx in (("zfw", "zfw", "max_zfw"), ("tow", "tow", "max_tow"), ("lw", "law", "max_lw")):
        mass, cg = mcres[k], mcres[f"{k}_cg"]
        lim = cg_limits_at(ac, mass, state)
        out[k] = {"mass": mass, "cg": cg, "mac": mcres[f"{k}_mac"], "lim": lim,
                  "ok": True if lim is None else (lim[0] <= cg <= lim[1]), "max": fs.get(mx)}
    return out


def render_loading_proposal(ac: dict, wk: str, ctx: dict):
    """Proposition préliminaire de répartition (ULD ou soutes en vrac) et édition du plan de chargement en PDF."""
    mode = ctx["mode"]
    fs = ctx["fs"]
    st.markdown("### 🧮 Proposition préliminaire de répartition et plan de chargement")
    if ULDP is None or not ULDP.available():
        st.info("La répartition automatique n'est pas disponible : le module uldplan.py est absent du dépôt, ou la "
                "bibliothèque PuLP n'est pas installée.")
        return
    key_res = f"loadprop_{wk}"
    NAT = ("Bagages", "Fret", "Courrier")

    # ── 1. Charge à répartir ──────────────────────────────────────────────
    if mode == "uld":
        loads = {"Bagages": float(ctx["bag_for_uld"]), "Fret": float(ctx["uld_cargo"]), "Courrier": float(ctx["uld_mail"])}
        bag_unit = None
        st.caption("Charge à placer dans les ULD : bagages = bagages déclarés moins la réserve en soute vrac ; fret et courrier "
                   "= totaux saisis plus haut. La proposition remplit les positions du fichier AHM de la compagnie.")
    else:
        c1, c2 = st.columns(2)
        cargo_in = int(c1.number_input("Fret à répartir entre les soutes (kg)", 0, 300000, int(ctx["cargo_default"]), step=50,
                                       key=f"plancargo_{wk}"))
        mail_in = int(c2.number_input("Courrier à répartir entre les soutes (kg)", 0, 300000, int(ctx["mail_default"]), step=10,
                                      key=f"planmail_{wk}"))
        loads = {"Bagages": float(ctx["bag_total"]), "Fret": float(cargo_in), "Courrier": float(mail_in)}
        bag_unit = float(ctx["bag_std"]) if (ctx.get("bag_mode") == "Masse forfaitaire" and ctx.get("bag_std")) else None
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Bagages", f"{loads['Bagages']:,.0f} kg" + (f" ({ctx['bag_pieces']} pièces)" if bag_unit else ""))
    m2.metric("Fret", f"{loads['Fret']:,.0f} kg")
    m3.metric("Courrier", f"{loads['Courrier']:,.0f} kg")
    m4.metric("Total", f"{sum(loads.values()):,.0f} kg")
    if sum(loads.values()) <= 0:
        st.caption("Aucune charge à répartir : renseignez les bagages, le fret ou le courrier.")
        return

    # ── 2. Paramètres ─────────────────────────────────────────────────────
    base = ctx["mc_without"]()
    tot_load = sum(loads.values())
    lim_est = cg_limits_at(ac, base["raw_mass"]["tow"] + tot_load, "tow")
    mid_arm = (lim_est[0] + lim_est[1]) / 2
    mid_mac = cg_to_mac(mid_arm, ac["lemac"], ac["mac_length"])
    t_mode = st.radio("Cible de centrage au décollage", ["Milieu de l'enveloppe", "Valeur imposée (%MAC)"], horizontal=True,
                      key=f"plantgt_{wk}")
    if t_mode.startswith("Valeur"):
        pct = float(st.number_input("Cible (%MAC)", -50.0, 150.0, float(round(mid_mac, 1)), step=0.5, key=f"plantgtv_{wk}"))
        t_arm = ac["lemac"] + pct / 100 * ac["mac_length"]
        t_txt = "valeur imposée"
    else:
        pct, t_arm, t_txt = mid_mac, mid_arm, f"milieu de l'enveloppe, de {lim_est[0]:.2f} à {lim_est[1]:.2f} m"
    st.caption(f"Cible retenue : {pct:.1f} %MAC ({t_arm:.2f} m). Les limites sont toujours respectées en priorité ; "
               "la cible n'est approchée que dans leur marge.")
    caps, extra, tare_by, rows = {}, 0, {}, []
    if mode == "uld":
        U = ac.get("uld") or {}
        rows = U.get("rows") or []
        tare_by = ctx["tare_by"]
        types = sorted({t_ for r_ in rows for t_ in r_["types"]}) or ["ULD"]
        dflt = ULDP.default_caps(rows, tare_by)
        st.markdown("Contenu moyen visé par ULD (kg), au plus égal à la masse maximale de la position moins la tare")
        at_limit = True
        for col, t_ in zip(st.columns(len(types)), types):
            mx = max(int(dflt.get(t_, 0)), 1)
            cb = int(col.number_input(f"{t_} · bagages", 1, mx, mx, step=10, key=f"uldcapb_{wk}_{t_}_{mx}"))
            cf = int(col.number_input(f"{t_} · fret et courrier", 1, mx, mx, step=10, key=f"uldcapf_{wk}_{t_}_{mx}"))
            at_limit = at_limit and cb == mx and cf == mx
            caps[t_] = {"Bagages": float(cb), "Fret": float(cf), "Courrier": float(cf)}
        extra = int(st.number_input("ULD supplémentaires tolérés pour améliorer le centrage", 0, 5, 0, key=f"uldextra_{wk}"))
        if at_limit:
            st.warning("Contenus moyens égaux à la limite de masse des positions : le volume des ULD n'est pas contrôlé, donc le "
                       "nombre de ULD calculé est un minimum. Saisissez le contenu moyen observé pour chaque type pour obtenir "
                       "un nombre réel.")
        if not any(tare_by.values()):
            st.warning("Tares non renseignées : la masse brute des ULD est sous-estimée (saisie des tares au-dessus du plan).")

    # ── 3. Calcul ─────────────────────────────────────────────────────────
    sig = repr((mode, sorted(loads.items()), sorted((k, sorted(v.items())) for k, v in caps.items()), sorted(tare_by.items()),
                extra, round(t_arm, 3), round(base["raw_mass"]["tow"]), round(base["raw_moment"]["tow"]), bag_unit))
    if st.button("🧮 Calculer la proposition de répartition", key=f"planbtn_{wk}", type="primary"):
        states = []
        for sname, key in (("zfw", "zfw"), ("tow", "tow"), ("law", "lw")):
            states.append({"name": sname, "m_other": base["raw_mass"][key], "mom_other": base["raw_moment"][key],
                           "lim": (lambda w, sname=sname: cg_limits_at(ac, w, sname))})
        target = {"state": "tow", "arm_m": t_arm}
        with st.spinner("Calcul de la répartition en cours..."):
            if mode == "uld":
                comps_d = {c["name"]: {"max": float(c["max_kg"]), "groupe": c.get("groupe"),
                                       "max_groupe": c.get("max_groupe_kg")}
                           for c in (ac.get("cargo_comps") or []) if c["name"] in set((ac.get("uld") or {}).get("comps") or [])}
                res = ULDP.solve(rows, loads, tare_by, caps, comps_d, states, target, extra_uld=extra)
                pl_loads = {}
                pl_mom = {}
                for x in res["plan"]:
                    pl_loads[x["comp"]] = pl_loads.get(x["comp"], 0.0) + x["gross"]
                    pl_mom[x["comp"]] = pl_mom.get(x["comp"], 0.0) + x["gross"] * x["arm"]
            else:
                comps_b = [{"name": c["name"], "arm_m": c["arm_m"], "max_kg": c["max_kg"], "groupe": c.get("groupe"),
                            "max_groupe_kg": c.get("max_groupe_kg"), "bag_rank": c.get("bag_rank"), "fixed_kg": 0}
                           for c in (ac.get("cargo_comps") or [])]
                res = ULDP.solve_bulk(comps_b, loads, states, target, bag_unit=bag_unit)
                pl_loads = {r["comp"]: r["total"] for r in res["plan"]}
                pl_mom = None
        cgsum = _cg_state_summary(ac, ctx["mc_with"](pl_loads, pl_mom), fs) if res["plan"] else {}
        st.session_state[key_res] = {"res": res, "sig": sig, "cg": cgsum, "loads": dict(loads), "caps": caps,
                                     "tare": dict(tare_by), "target": (pct, t_txt), "at_limit": (at_limit if mode == "uld" else False)}
        audit("loading_proposal", f"{fs.get('flight_number') or '-'} · {mode} · {res.get('status')}")

    sr = st.session_state.get(key_res)
    if not sr:
        return
    res = sr["res"]
    if sr["sig"] != sig:
        st.warning("Les données ont changé depuis le calcul (charge, tares, contenus, cible ou masses du vol) : relancez le calcul "
                   "avant d'appliquer ou d'éditer cette proposition.")
    for m_ in res.get("messages", []):
        (st.warning if res.get("plan") else st.error)(m_)
    if not res.get("plan"):
        st.error(f"Aucune proposition : {res.get('status') or 'calcul impossible'}.")
        return
    if res["ok"]:
        st.success("Proposition calculée : toutes les limites sont respectées.")
    else:
        st.error("Proposition hors limites : voir les contrôles ci-dessous.")

    # ── 4. Résultat ───────────────────────────────────────────────────────
    if mode == "uld":
        nu, th = res["n_uld"], res["theory"]
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("ULD bagages", nu["Bagages"], help=f"Minimum par la masse seule : {th.get('Bagages')}")
        k2.metric("ULD fret", nu["Fret"], help=f"Minimum par la masse seule : {th.get('Fret')}")
        k3.metric("ULD courrier", nu["Courrier"], help=f"Minimum par la masse seule : {th.get('Courrier')}")
        k4.metric("Total ULD", res["n_total"], help=f"Minimum par la masse seule : {sum(v for v in th.values() if v)}")
        st.dataframe(pd.DataFrame([{"Soute": x["comp"], "Position": x["pos"], "ULD": x["uld"], "Nature": x["nature"],
                                    "Contenu (kg)": round(x["content"]), "Tare (kg)": round(x["tare"]),
                                    "Brut (kg)": round(x["gross"]), "Maxi (kg)": round(x["max"]), "Bras (m)": round(x["arm"], 2)}
                                   for x in res["plan"]]), hide_index=True, use_container_width=True)
        st.caption(f"Équilibre gauche / droite : écart de {abs(res.get('lateral_kg', 0)):,.0f} kg entre les côtés (indicatif : "
                   "l'AHM ne donne pas de limite latérale).")
    else:
        st.dataframe(pd.DataFrame([{"Soute": r["comp"], "Bras (m)": round(r["arm"], 2), "Bagages (kg)": round(r["Bagages"]),
                                    "Pièces": r["pieces"] if r.get("pieces") is not None else None,
                                    "Fret (kg)": round(r["Fret"]), "Courrier (kg)": round(r["Courrier"]),
                                    "Total (kg)": round(r["total"]), "Maxi (kg)": round(r["max"]),
                                    "Taux (%)": round(r["total"] / r["max"] * 100) if r["max"] else None}
                                   for r in res["plan"]]), hide_index=True, use_container_width=True)
    cgs = sr.get("cg") or {}
    if cgs:
        rows_cg = []
        for k_, lab in (("zfw", "ZFW"), ("tow", "TOW"), ("lw", "LW")):
            v = cgs[k_]
            rows_cg.append({"État": lab, "Masse (kg)": f"{v['mass']:,}", "CG (m)": round(v["cg"], 2), "%MAC": v["mac"],
                            "Limites (m)": (f"{v['lim'][0]:.2f} à {v['lim'][1]:.2f}" if v["lim"] else "non définie par la compagnie"),
                            "Contrôle": ("OK" if v["ok"] else "HORS LIMITES") if v["lim"] else "non contrôlé"})
        st.dataframe(pd.DataFrame(rows_cg), hide_index=True, use_container_width=True)
        st.caption(f"Cible au décollage : {sr['target'][0]:.1f} %MAC ({sr['target'][1]}).")

    # ── 5. Application et PDF ─────────────────────────────────────────────
    b1, b2 = st.columns(2)
    if mode == "uld":
        b1.button("✅ Appliquer cette répartition au plan de chargement", key=f"planapply_{wk}", use_container_width=True,
                  on_click=_apply_uld_prop, args=(wk, res["plan"]), disabled=(sr["sig"] != sig))
    else:
        b1.button("✅ Appliquer cette répartition aux soutes", key=f"planapply_{wk}", use_container_width=True,
                  on_click=_apply_bulk_prop, args=(wk, res["plan"], int(ctx["bag_total"])), disabled=(sr["sig"] != sig))

    def bag_text():
        if ctx.get("bag_mode") == "Masse forfaitaire":
            return (f"Bagages : {ctx['bag_pieces']} pièces x {ctx['bag_std']} kg ({ctx.get('bag_ft', '')}) = "
                    f"{ctx['bag_total']:,} kg. Source de la masse forfaitaire : {ctx.get('bag_src', '')}.").replace(",", " ")
        return f"Bagages : masse réelle pesée, {ctx['bag_total']:,} kg.".replace(",", " ")

    def notes(prop: bool):
        out = []
        if mode == "uld":
            tr = ", ".join(f"{k} {v:.0f} kg" for k, v in sorted((sr.get("tare") or {}).items()))
            out.append("Nombre de ULD calculé par la masse : contenu moyen par ULD saisi pour chaque type (bagages, fret et "
                       "courrier), borné par la masse maximale de position du fichier AHM moins la tare. Le volume des ULD n'est "
                       "pas contrôlé : le nombre réel de ULD peut être supérieur."
                       + (" Les contenus moyens retenus sont égaux à la limite de masse." if sr.get("at_limit") else ""))
            out.append("Tares retenues : " + (tr if tr and any((sr.get("tare") or {}).values()) else "non renseignées (0 kg), masse brute sous-estimée") + ".")
            out.append("Limites de position, de soute et de groupe, types de ULD admis et enveloppes de centrage : fichier AHM de la "
                       "compagnie. Verrouillage, arrimage et compatibilité des ULD avec l'avion : règles non appliquées.")
        else:
            out.append("Répartition calculée entre les soutes en vrac dans le respect des masses maximales de soute, des limites de "
                       "groupe et des enveloppes de centrage ; à centrage équivalent, la priorité de chargement des bagages de la "
                       "compagnie est suivie.")
        out.append(bag_text())
        if prop:
            out.append("Proposition établie par calcul avant le chargement : elle est à confirmer ou à ajuster par l'agent de "
                       "chargement. Le plan définitif est celui de la loadsheet.")
        else:
            out.append("Plan tel que saisi dans l'application ; il est à confirmer par l'agent de chargement.")
        return out

    def pdf_dict(label, plan, cgsum, prop):
        if mode == "uld":
            placed = {n_: sum(x["content"] for x in plan if x["nature"] == n_) for n_ in NAT}
            nu = {n_: sum(1 for x in plan if x["nature"] == n_) for n_ in NAT}
            d = {"mode": "uld", "label": label, "fs": fs, "loads": placed, "bag_text": bag_text(), "plan": plan, "rows": rows,
                 "comps": [{"name": c["name"], "max": c["max_kg"], "groupe": c.get("groupe"), "max_groupe": c.get("max_groupe_kg")}
                           for c in (ac.get("cargo_comps") or []) if c["name"] in set((ac.get("uld") or {}).get("comps") or [])],
                 "other": ctx.get("other_holds") or [], "n_uld": nu,
                 "theory": ULDP.theoretical_min(placed, {t_: {n_: v for n_, v in sr["caps"][t_].items()} for t_ in sr["caps"]})
                 if sr.get("caps") else {}}
        else:
            placed = {n_: sum(r[n_] for r in plan) for n_ in NAT}
            d = {"mode": "bulk", "label": label, "fs": fs, "loads": placed, "bag_text": bag_text(), "plan": plan,
                 "pieces": (sum(r["pieces"] or 0 for r in plan) if plan and plan[0].get("pieces") is not None else None)}
        d["cg"] = cgsum
        d["target_mac"], d["target_txt"] = sr["target"]
        d["notes"] = notes(prop)
        return d

    fname = f"AETHERDISPATCH_PLAN_{(fs.get('flight_number') or 'VOL')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    try:
        pdf_prop = generate_loading_plan_pdf(pdf_dict("PROPOSITION PRÉLIMINAIRE", res["plan"], sr.get("cg") or {}, True))
        b2.download_button("📄 PDF du plan de chargement (proposition)", data=pdf_prop, file_name=fname,
                           mime="application/pdf", key=f"planpdf_{wk}", use_container_width=True,
                           on_click=audit, args=("loading_plan_pdf", f"{fs.get('flight_number') or '-'} · proposition · {mode}"))
    except Exception as e:                                           # le PDF ne doit jamais bloquer l'application
        b2.error(f"PDF de la proposition indisponible : {e}")
    cur = ctx.get("current_plan")
    if cur:
        try:
            pdf_cur = generate_loading_plan_pdf(pdf_dict("PLAN SAISI", cur, ctx.get("current_cg") or {}, False))
            st.download_button("📄 PDF du plan de chargement (plan saisi dans l'application)", data=pdf_cur,
                               file_name=fname.replace("PLAN_", "PLANSAISI_"), mime="application/pdf",
                               key=f"planpdfcur_{wk}", use_container_width=True,
                               on_click=audit, args=("loading_plan_pdf", f"{fs.get('flight_number') or '-'} · plan saisi · {mode}"))
        except Exception as e:
            st.error(f"PDF du plan saisi indisponible : {e}")


def render_flight_tab(ac: dict, selected_ac: str, airports: dict, blocked: bool, missing: list, user_info: dict):
    wk = selected_ac + ("·" + str(ac["ahm_selection"]["config"]) if ac.get("ahm_selection") else "")   # clé des widgets
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
        origin = st.selectbox("🛫 Départ", list(airports.keys()), key="origin",
                              format_func=lambda k: ap_label(airports[k]))
    with col_b:
        flight_date = st.date_input("Date du vol", key="flight_date")
        dest = st.selectbox("🛬 Arrivée", list(airports.keys()), index=min(1, len(airports) - 1), key="dest",
                            format_func=lambda k: ap_label(airports[k]))
    with col_c:
        flight_time = st.time_input("Heure départ (UTC)", key="flight_time")
    _sel = ac.get("ahm_selection")
    if _sel and _sel.get("immat"):
        registration = str(_sel["immat"]).strip().upper()
        st.caption(f"Immatriculation : **{registration}**, configuration **{_sel['config']}** "
                   "(choisies dans la barre latérale, selon le fichier AHM importé).")
    else:
        registration = st.text_input("Immatriculation de l'avion", value="", key="registration",
                                     placeholder="ex. F-GKXA", max_chars=10).strip().upper()

    NONE_OPT = "— Aucun —"
    ap_names = list(airports.keys())
    ca1, ca2, ca3 = st.columns(3)
    _fmt_ap = lambda k: k if k == NONE_OPT else ap_label(airports[k])
    alt1 = ca1.selectbox("⚡ Dégagement 1", ap_names, index=min(2, len(ap_names) - 1), key="alt", format_func=_fmt_ap)
    alt2 = ca2.selectbox("⚡ Dégagement 2 (facultatif)", [NONE_OPT] + ap_names, key="alt2", format_func=_fmt_ap)
    alt3 = ca3.selectbox("⚡ Dégagement 3 (facultatif)", [NONE_OPT] + ap_names, key="alt3", format_func=_fmt_ap)
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
            <div class="label">Altitude dest.</div><div class="value">{ap_elev_ft(dest_data):,}</div><div class="unit">ft</div>
        </div>
        <div class="metric-card" style="flex:1;min-width:140px">
            <div class="label">Piste dest.</div><div class="value">{ap_rwy_text(dest_data)}</div><div class="unit">m</div>
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
                                "Piste (m)": (a_["rwy_m"] if a_["rwy_m"] is not None else "n.c.")} for a_ in alt_info]), hide_index=True, use_container_width=True)
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
    comps_all = ac.get("cargo_comps") or []
    uld_on = ac.get("loading_mode") == "uld" and bool((ac.get("uld") or {}).get("rows"))
    uld_names = set(ac["uld"]["comps"]) if uld_on else set()
    comps = [c for c in comps_all if c["name"] not in uld_names]          # soutes en vrac (saisie par soute)
    st.markdown("**📦 Fret et courrier par soute**" + (" (soutes en vrac)" if uld_on else ""))
    if ac.get("loading_mode") == "uld" and not uld_on:
        st.info("Positions de ULD non définies pour ce type : saisie simplifiée par soute (masse totale).")
    uld_cargo_kg = uld_mail_kg = 0
    if uld_on:
        st.caption("Les soutes chargées en ULD (" + ", ".join(sorted(uld_names)) + ") se renseignent dans le plan de "
                   "chargement ci-dessous. Cette partie ne concerne que les soutes en vrac.")
        u1, u2 = st.columns(2)
        uld_cargo_kg = int(u1.number_input("Fret à placer en ULD (kg)", 0, 300000, 0, step=50, key=f"uldcargo_{wk}"))
        uld_mail_kg = int(u2.number_input("Courrier à placer en ULD (kg)", 0, 300000, 0, step=10, key=f"uldmail_{wk}"))
        st.caption("Ces deux totaux alimentent la proposition de répartition : la masse comptée reste celle du plan de chargement.")
    bap = st.session_state.get(f"bulk_applied_{wk}") or {}               # répartition appliquée (soutes en vrac)
    ks = f"_v{bap['ver']}" if bap.get("ver") else ""
    cargo_w = {c["name"]: 0 for c in comps_all}
    mail_w = {c["name"]: 0 for c in comps_all}
    use_cargo = st.checkbox("Saisir fret et courrier", value=False, key=f"use_cargo_{wk}")
    keep = st.session_state.setdefault(f"cargo_keep_{wk}", {})
    if use_cargo and comps:
        for i, (col, comp) in enumerate(zip(st.columns(len(comps)), comps)):
            with col:
                st.markdown(f"**{comp['name']}**")
                cap_ = int(comp["max_kg"])
                _dc = (bap.get("cargo") or {}).get(comp["name"])
                _dm = (bap.get("mail") or {}).get(comp["name"])
                cargo_w[comp["name"]] = int(st.number_input("Fret (kg)", 0, cap_,
                                                            min(int(_dc if _dc is not None else keep.get(f"c{i}", 0)), cap_),
                                                            step=50, key=f"cargo_{wk}_{i}{ks}"))
                mail_w[comp["name"]] = int(st.number_input("Courrier (kg)", 0, cap_,
                                                           min(int(_dm if _dm is not None else keep.get(f"m{i}", 0)), cap_),
                                                           step=10, key=f"mail_{wk}_{i}{ks}"))
                keep[f"c{i}"], keep[f"m{i}"] = cargo_w[comp["name"]], mail_w[comp["name"]]
                st.caption(f"Capacité : {cap_:,} kg | Bras : {comp['arm_m']} m"
                           + (f" | Groupe {comp['groupe']} : {int(comp['max_groupe_kg']):,} kg max"
                              if comp.get("groupe") and comp.get("max_groupe_kg") else ""))
    elif comps:
        kept_total = sum(int(v) for v in keep.values())
        st.caption("Fret et courrier non saisis : 0 kg compté."
                   + (f" Des valeurs saisies ({kept_total:,} kg) sont conservées, mais ne sont pas comptées tant que la case "
                      "est décochée." if kept_total else ""))

    st.markdown("**🧳 Bagages en soute**")
    bag_mode = st.radio("Mode de détermination", ["Masse forfaitaire", "Pesée réelle"], horizontal=True,
                        key=f"bag_mode_{wk}")
    bag_pieces, bag_std, bag_ft_label, bag_src = 0, None, "", ""
    if bag_mode == "Masse forfaitaire":
        b1, b2, b3 = st.columns(3)
        bag_pieces = int(b1.number_input("Nombre de bagages", 0, 3000, 0, key=f"bag_n_{wk}"))
        ft_labels = [lab for _, lab in BAG_FLIGHT_TYPES]
        bag_ft_label = b2.selectbox("Type de vol", ft_labels, index=1, key=f"bag_ft_{wk}")
        ft_key = dict((lab, k) for k, lab in BAG_FLIGHT_TYPES)[bag_ft_label]
        bag_std = ref["bag_masses"][ft_key]["value"]
        bag_src = ref["bag_masses"][ft_key].get("source", "")
        b3.metric("Masse par bagage", f"{bag_std} kg")
        bag_total = bag_pieces * bag_std
    else:
        bag_total = int(st.number_input("Masse réelle des bagages (kg)", 0, 100000, 0, key=f"bag_kg_{wk}"))

    used = {c["name"]: cargo_w.get(c["name"], 0) + mail_w.get(c["name"], 0) for c in comps}
    reserve_kg = 0
    if uld_on:
        alloc, alloc_mode, unplaced = {c["name"]: 0 for c in comps}, "manuel", 0
        if bag_total > 0:
            st.caption("Chargement en ULD : les bagages sont placés dans les ULD du plan de chargement (nature « Bagages ») "
                       "ou, pour le vrac, dans la répartition ci-dessous.")
        if comps:
            reserve_kg = int(st.number_input("Réserve en soute vrac pour les bagages tardifs (kg)", 0,
                                             max(int(sum(c["max_kg"] for c in comps)), 1), 0, step=10, key=f"bagreserve_{wk}"))
            if reserve_kg > bag_total:
                st.error("La réserve en soute vrac dépasse la masse de bagages déclarée.")
                reserve_kg = int(bag_total)
            if reserve_kg > 0:
                alloc, alloc_mode, unplaced = allocate_bags(comps, reserve_kg, used)
    else:
        alloc, alloc_mode, unplaced = allocate_bags(comps, bag_total, used)
    sig = zlib.crc32(repr(sorted(used.items())).encode())
    bag_w = {c["name"]: 0 for c in comps_all}
    bag_w.update(alloc)
    if comps and bag_total > 0:
        with st.expander("Répartition des bagages par soute (priorité de chargement, ajustable)"):
            if alloc_mode == "manuel":
                st.caption("Masse de bagages en vrac à saisir pour chaque soute en vrac.")
            elif alloc_mode == "priorité":
                note = _meta(ac)["source"].get("bag_rank", "")
                st.caption(f"Priorité de chargement : {bag_priority_text(comps)}"
                           + (f" (source : {note})" if note else "") + " Modifiable dans « Données aéronef ».")
            else:
                st.warning("Priorité de chargement non renseignée pour ce type : répartition proportionnelle à la "
                           "capacité disponible. À renseigner dans « Données aéronef ».")
            for i, (col, comp) in enumerate(zip(st.columns(len(comps)), comps)):
                with col:
                    _bd = (bap.get("bag") or {}).get(comp["name"]) if (
                        bap and not uld_on and bap.get("sig") == sig and bap.get("bag_total") == int(bag_total)) else None
                    bag_w[comp["name"]] = int(st.number_input(
                        f"{comp['name']} (kg)", 0, int(comp["max_kg"]),
                        min(int(_bd if _bd is not None else alloc[comp["name"]]), int(comp["max_kg"])),
                        key=f"bagz_{wk}_{i}_{int(bag_total)}_{sig}_r{reserve_kg}{ks}"))
            if sum(bag_w.values()) != int(bag_total) and not uld_on:
                st.warning(f"La somme des soutes ({sum(bag_w.values())} kg) diffère de la masse de bagages "
                           f"({int(bag_total)} kg).")
    if unplaced > 0:
        st.error(f"Capacité des soutes dépassée de {unplaced} kg : les bagages ne peuvent pas tous être chargés.")
    bag_for_uld = max(float(bag_total) - sum(bag_w.get(c["name"], 0) for c in comps), 0.0) if uld_on else 0.0
    prop_box = st.container()          # rempli plus bas : la proposition a besoin du carburant et des masses du vol
    uld_res = None
    if uld_on:
        st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
        uld_res = render_uld_plan(ac, wk)
        for cn, nd in (uld_res or {}).get("nat", {}).items():
            bag_w[cn], cargo_w[cn], mail_w[cn] = nd["Bagages"], nd["Fret"], nd["Courrier"]
        _bag_all = sum(bag_w.values())
        if bag_total > 0 and abs(_bag_all - bag_total) > 0.5:
            st.warning(f"Bagages déclarés : {int(bag_total):,} kg. Bagages placés (ULD et vrac) : {_bag_all:,.0f} kg. "
                       "Écart à rapprocher avant d'éditer la loadsheet.")
    comps = comps_all
    comp_loads = {c["name"]: cargo_w.get(c["name"], 0) + mail_w.get(c["name"], 0) + bag_w.get(c["name"], 0)
                  for c in comps_all}
    if uld_res:
        for cn, gross in uld_res["loads"].items():
            comp_loads[cn] = gross                     # masse brute des ULD (tare comprise)
    for c in comps:
        if comp_loads[c["name"]] > c["max_kg"]:
            st.error(f"Soute {c['name']} : {comp_loads[c['name']]:,} kg chargés pour une capacité de "
                     f"{int(c['max_kg']):,} kg.")
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)

    # ── 4. Carburant (côté trafic) ────────────────────────────────────────
    st.markdown("**⛽ Carburant (côté trafic)**")
    mfuel = int(ac["mfuel"])
    _perf = ac.get("perf") or {}
    if _perf.get("fuel_flow_cruise"):
        trip_default = max(500, min(int(dist_nm / (_perf.get("cruise_tas_kt") or 450) * _perf["fuel_flow_cruise"]), mfuel - 1000))
    else:
        trip_default = max(500, min(int(mfuel * 0.15), mfuel - 1000))      # consommation non renseignée : valeur indicative
    _taxi_std = ((ac.get("ahm") or {}).get("taxi_standard_kg"))
    taxi_default = min(int(_taxi_std), mfuel) if _taxi_std else min(300, mfuel)
    f1, f2, f3, f4 = st.columns(4)
    bloc = int(f1.number_input("Bloc fuel (kg)", 0, mfuel, min(int(mfuel * 0.40), mfuel), step=100,
                               key=f"fuel_bloc_{wk}"))
    taxi = int(f2.number_input("Taxi fuel (kg)", 0, mfuel, taxi_default, step=50, key=f"fuel_taxi_{wk}",
                               help=("Valeur initiale : taxi standard du fichier AHM." if _taxi_std else None)))
    trip = int(f3.number_input("Trip fuel (kg)", 0, mfuel, min(trip_default, mfuel), step=100,
                               key=f"fuel_trip_{wk}"))
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
    st.markdown("**👩‍✈️ Équipage (PNT et PNC)**")
    cm = ref["crew_masses"]
    m_f, m_c = cm["flight"]["value"], cm["cabin"]["value"]
    std_f, std_c = ac.get("crew_std_flight"), ac.get("crew_std_cabin")
    e1, e2, e3 = st.columns(3)
    n_f = int(e1.number_input("PNT (nombre)", 0, 10, int(std_f) if std_f is not None else 2,
                              key=f"crew_f_{wk}"))
    n_c = int(e2.number_input("PNC (nombre)", 0, 30, int(std_c) if std_c is not None else 0,
                              key=f"crew_c_{wk}"))
    crew_delta = ((n_f - int(std_f)) * m_f if std_f is not None else 0) + ((n_c - int(std_c)) * m_c if std_c is not None else 0)
    e3.metric("Écart de masse d'équipage", f"{crew_delta:+,.0f} kg",
              help=f"Écart par rapport à la composition standard ({std_f if std_f is not None else '—'} / "
                   f"{std_c if std_c is not None else '—'}), aux masses du référentiel.")
    if std_f is None or std_c is None:
        st.caption("Composition standard non renseignée pour ce type : aucun ajustement de masse n'est appliqué "
                   "(onglet « Données aéronef »).")

    with st.expander("Autres masses (lest, consommables autres que le carburant)"):
        o1, o2, o3, o4 = st.columns(4)
        ballast = int(o1.number_input("Lest (kg)", 0, 20000, 0, step=10, key=f"ballast_{wk}"))
        ballast_pos = o2.selectbox("Position du lest", hold_names, key=f"ballast_pos_{wk}") if hold_names else ""
        cons = int(o3.number_input("Consommables (kg)", 0, 20000, 0, step=10, key=f"cons_{wk}"))
        cons_pos = o4.selectbox("Position des consommables", hold_names, key=f"cons_pos_{wk}") if hold_names else ""
        st.caption("Ces masses sont incluses dans le ZFW. Leur position est approchée par le bras de la soute choisie.")
    extra_items = [(kg_, arm_by_name.get(pos_, ac["oew_arm_m"])) for kg_, pos_ in ((ballast, ballast_pos), (cons, cons_pos)) if kg_ > 0]
    extra_kg = ballast + cons

    with st.expander("Limites de masse du jour (performances : piste, météo)"):
        l1, l2 = st.columns(2)
        perf_tow = int(l1.number_input("TOW maximal limité par les performances (kg, 0 = aucune)", 0, 700000, 0, step=100,
                                       key=f"perf_tow_{wk}"))
        perf_lw = int(l2.number_input("LW maximal limité par les performances (kg, 0 = aucune)", 0, 700000, 0, step=100,
                                      key=f"perf_lw_{wk}"))
        st.caption("La limite retenue est la plus faible entre le maximum de structure et la limite de performances.")
    eff_tow, tow_basis = (perf_tow, "performances") if 0 < perf_tow < ac["max_tow_kg"] else (ac["max_tow_kg"], "structure")
    eff_lw, lw_basis = (perf_lw, "performances") if 0 < perf_lw < ac["max_lw_kg"] else (ac["max_lw_kg"], "structure")

    with st.expander("⚠ Chargements spéciaux (marchandises dangereuses, animaux vivants, restes humains, valeurs)"):
        sp_empty = pd.DataFrame({"Type": pd.Series(dtype="object"), "N° ONU": pd.Series(dtype="object"),
                                 "Classe / division": pd.Series(dtype="object"), "Masse (kg)": pd.Series(dtype="float"),
                                 "Soute": pd.Series(dtype="object"), "Observations": pd.Series(dtype="object")})
        sp_df = st.data_editor(sp_empty, num_rows="dynamic", hide_index=True, use_container_width=True,
                               key=f"special_{wk}",
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
                        trip_kg=min(trip, tof), cargo_moments=(uld_res.get("moments") if uld_res else None))
    lw = result["tow"] - trip
    payload = result["pax_total_kg"] + sum(comp_loads.values())

    lim_z, lim_t, lim_l = (cg_limits_at(ac, result["zfw"], "zfw"), cg_limits_at(ac, result["tow"], "tow"),
                           cg_limits_at(ac, lw, "law"))
    lw_cg_defined = lim_l is not None
    zfw_ok = result["zfw"] <= ac["max_zfw_kg"]
    tow_ok = result["tow"] <= eff_tow
    lw_ok = lw <= eff_lw
    zfw_cg_ok = lim_z[0] <= result["zfw_cg"] <= lim_z[1]
    tow_cg_ok = lim_t[0] <= result["tow_cg"] <= lim_t[1]
    lw_cg_ok = True if lim_l is None else (lim_l[0] <= result["lw_cg"] <= lim_l[1])
    cg_ok = zfw_cg_ok and tow_cg_ok and lw_cg_ok
    zones_ok = not pax.get("zones_over")
    stock_ok = unplaced == 0 and all(comp_loads[c["name"]] <= c["max_kg"] for c in comps) and (uld_res is None or uld_res["ok"])
    _groups = {}
    for c_ in comps:
        if c_.get("groupe") and c_.get("max_groupe_kg") is not None:
            _groups.setdefault(c_["groupe"], [float(c_["max_groupe_kg"]), 0.0])[1] += comp_loads[c_["name"]]
    group_over = [(g_, v_[1], v_[0]) for g_, v_ in _groups.items() if v_[1] > v_[0]]
    for g_, load_, mx_ in group_over:
        st.error(f"Groupe de soutes {g_} : {load_:,.0f} kg chargés pour une limite de groupe de {mx_:,.0f} kg.")
    stock_ok = stock_ok and not group_over

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
            ("CG LW", result["lw_cg"], "m",
             (f"limites {lim_l[0]:.2f} à {lim_l[1]:.2f} m" if lim_l else "limite non définie par la compagnie"),
             lw_cg_ok if lim_l else None)]
    for col, (label, val, unit, note, ok) in zip(st.columns(4), row2):
        with col:
            card(label, val, unit, note, ok, fmt=".2f")
    for lab, okc, cgv, lim in (("ZFW", zfw_cg_ok, result["zfw_cg"], lim_z), ("TOW", tow_cg_ok, result["tow_cg"], lim_t),
                               ("LW", lw_cg_ok, result["lw_cg"], lim_l)):
        if lim is not None and not okc:
            st.error(f"Centrage hors limites au {lab} : {cgv:.2f} m (limites {lim[0]:.2f} à {lim[1]:.2f} m).")
    if not lw_cg_defined:
        st.caption("Centrage à l'atterrissage : limite non définie par la compagnie dans le fichier importé, donc non contrôlée.")
    if not (ac.get("cg_envelope") or []):
        st.caption("Limites de centrage constantes : l'enveloppe masse-centrage n'est pas renseignée pour ce type "
                   "(onglet « Données aéronef »).")

    ahm_idx = compute_ahm_indices(ac, result)
    if ahm_idx:
        with st.expander("🧮 Indices et calage du stabilisateur (formule du fichier AHM)"):
            st.dataframe(pd.DataFrame([{"Indice": k, "Valeur": v, "Imprimé sur la loadsheet": ("oui" if k in ahm_idx["print"] else "non")}
                                       for k, v in ahm_idx["text"].items()]), hide_index=True, use_container_width=True)
            st.caption("Les indices sont recalculés avec la formule et les constantes du fichier. Ils sont imprimés sur le PDF "
                       "uniquement si le fichier de la compagnie (feuille C2) le prévoit. Le calage du stabilisateur est "
                       "interpolé dans le tableau du fichier.")
    st.markdown('<div class="aether-divider"></div>', unsafe_allow_html=True)
    render_pax_comparison(ac, pax, comp_loads, tof, extra_items, crew_delta, uld_res.get("moments") if uld_res else None)
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
                  "lmc": lmc_rows, "edition": edition, "zfw": result["zfw"], "tow": result["tow"], "lw": lw,
                  "uld": [(x["pos"], x["uld"], x["nature"], x["content"], x["tare"]) for x in (uld_res or {}).get("plan", [])]}
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
               f"PNT / PNC : {n_f} / {n_c}.")

    # ── Synthèse du vol (alimente le PDF et l'historique) ─────────────────
    origin_txt, aircraft_certified = origin_summary(ac, "mc")
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
        "bag_total": bag_total if not uld_on else round(sum(bag_w.values())),
        "cargo_total": sum(cargo_w.values()), "mail_total": sum(mail_w.values()),
        "payload": payload,
        "comps": [{"name": c["name"], "bag": bag_w.get(c["name"], 0), "cargo": cargo_w.get(c["name"], 0),
                   "mail": mail_w.get(c["name"], 0), "total": comp_loads[c["name"]], "max": int(c["max_kg"]),
                   "tare": round(sum(x_["tare"] for x_ in (uld_res or {}).get("plan", []) if x_["comp"] == c["name"]), 1)}
                  for c in comps],
        "uld_plan": list((uld_res or {}).get("plan", [])), "uld_ok": (uld_res["ok"] if uld_res else True),
        "uld_tare_total": round((uld_res or {}).get("tare_total", 0.0), 1),
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
        "cg_lims": {"zfw": list(lim_z), "tow": list(lim_t), "lw": (list(lim_l) if lim_l else None)},
        "lw_cg_defined": lw_cg_defined,
        "ahm_print": ({k: ahm_idx["text"][k] for k in ahm_idx["print"]} if ahm_idx else {}),
        "ahm_ref": ((ac.get("ahm") or {}).get("source") or {}),
        "ahm_config": (ac.get("ahm_selection") or {}).get("config"),
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

    # ── Proposition préliminaire de répartition et plan de chargement (PDF) ──
    if comps_all:
        _planned = {c["name"] for c in comps_all if (not uld_on or c["name"] in uld_names)}
        _base_loads = {c["name"]: (0 if c["name"] in _planned else comp_loads[c["name"]]) for c in comps_all}

        def _mc_with(pl_loads, pl_mom=None):
            cl = dict(_base_loads)
            cl.update(pl_loads)
            return compute_mc(ac, pax_weights, cl, tof, extra_items=extra_items, crew_delta_kg=crew_delta,
                              trip_kg=min(trip, tof), cargo_moments=pl_mom)

        _cur_plan, _cur_cg, _other = None, None, []
        if uld_on:
            if uld_res and uld_res.get("plan"):
                _cur_plan, _cur_cg = list(uld_res["plan"]), _cg_state_summary(ac, result, fs)
            _other = [{"name": c["name"], "bag": bag_w.get(c["name"], 0), "cargo": cargo_w.get(c["name"], 0),
                       "mail": mail_w.get(c["name"], 0), "total": comp_loads[c["name"]], "max": int(c["max_kg"])}
                      for c in comps_all if c["name"] not in uld_names and comp_loads[c["name"]] > 0]
        else:
            _rows = [{"comp": c["name"], "arm": c["arm_m"], "max": float(c["max_kg"]), "Bagages": float(bag_w.get(c["name"], 0)),
                      "Fret": float(cargo_w.get(c["name"], 0)), "Courrier": float(mail_w.get(c["name"], 0)),
                      "total": float(comp_loads[c["name"]]),
                      "pieces": (int(round(bag_w.get(c["name"], 0) / bag_std)) if (bag_mode == "Masse forfaitaire" and bag_std) else None)}
                     for c in comps_all]
            if sum(r_["total"] for r_ in _rows) > 0:
                _cur_plan, _cur_cg = _rows, _cg_state_summary(ac, result, fs)
        with prop_box:
            render_loading_proposal(ac, wk, {
                "mode": "uld" if uld_on else "bulk", "fs": fs, "mc_with": _mc_with, "mc_without": lambda: _mc_with({}, None),
                "bag_total": bag_total, "bag_std": bag_std, "bag_mode": bag_mode, "bag_pieces": bag_pieces,
                "bag_ft": bag_ft_label, "bag_src": bag_src, "cargo_default": sum(cargo_w.values()),
                "mail_default": sum(mail_w.values()), "bag_for_uld": bag_for_uld, "uld_cargo": uld_cargo_kg,
                "uld_mail": uld_mail_kg, "tare_by": (uld_res or {}).get("tare_by", {}), "current_plan": _cur_plan,
                "current_cg": _cur_cg, "other_holds": _other})

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
    ("crew.flight", "Masse standard - PNT (kg)"), ("crew.cabin", "Masse standard - PNC (kg)"),
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


# ── Import d'un fichier AHM (PDF) ────────────────────────────────────────
def _ahm_src(h: dict, feuille: str) -> str:
    so = h.get("source") or {}
    return f"AHM {so.get('organisme') or 'compagnie'} édition {so.get('edition') or '?'} du {so.get('date') or '?'} : {feuille}"


def _has_speeds(rec: dict) -> bool:
    return (get_field(rec, "vspeeds.vmo") is not None and get_field(rec, "perf.fuel_flow_cruise") is not None
            and not rec.get("ahm"))


def _ahm_default_base(db: dict, type_name: str):
    """Type de base proposé pour les vitesses et performances : celui dont le nom partage le numéro de série du type importé."""
    m = re.search(r"\d{3}", type_name or "")
    if not m:
        return None
    for k, v in db.items():
        if m.group(0) in k and _has_speeds(v):
            return k
    return None


def build_ahm_record(ac_raw: dict, base_rec) -> dict:
    """Enregistrement de type prêt à être ajouté à la base de la session, à partir du résultat de la conversion."""
    rec = copy.deepcopy(ac_raw)
    h = rec["ahm"]
    regs = [r_["reg"] for r_ in (h.get("immatriculations") or []) if r_.get("reg")]
    rec = AHM.apply_selection(rec, h["configs"][0]["nom"], regs[0] if regs else None)
    rec.pop("ahm_selection", None)
    tbl = rec.get("fuel_arm_table") or []
    rec["fuel_arm_m"] = round(_interp(tbl, (rec.get("mfuel") or 0) / 2, "fuel_kg", "arm_m"), 4) if len(tbl) >= 2 else None
    rec["seats_typical"] = ""
    rec["vspeeds"], rec["perf"] = None, None
    if base_rec:
        rec["vspeeds"] = copy.deepcopy(base_rec.get("vspeeds"))
        rec["perf"] = copy.deepcopy(base_rec.get("perf"))
    meta = {"status": {}, "source": {}}
    rec["_meta"] = meta
    comp_keys = {
        "max_seats": "feuille D5, plans de sièges", "seats": "feuille D5, plans de sièges",
        "oew_kg": "masse à vide de la 1re configuration (remplacée selon la configuration choisie)",
        "oew_arm_m": "index de la 1re configuration (remplacé selon la configuration choisie)",
        "crew_kg": "composition d'équipage de la configuration", "crew_arm_m": "emplacements d'équipage de la configuration",
        "crew_std_flight": "composition d'équipage de la configuration", "crew_std_cabin": "composition d'équipage de la configuration",
        "max_zfw_kg": "masses limites (feuille C1)", "max_tow_kg": "masses limites (feuille C1)", "max_lw_kg": "masses limites (feuille C1)",
        "mfuel": "feuille D4, carburant", "fuel_arm_m": "table du carburant (valeur à mi-capacité, repli seulement)",
        "cg_min_m": "enveloppes de centrage (valeur extrême ; l'enveloppe est utilisée)",
        "cg_max_m": "enveloppes de centrage (valeur extrême ; l'enveloppe est utilisée)",
        "lemac": "formule d'index", "mac_length": "formule d'index"}
    for key, label, unit, req in ALL_FIELDS:
        if key in comp_keys and get_field(rec, key) is not None:
            meta["status"][key] = "compagnie"
            meta["source"][key] = _ahm_src(h, comp_keys[key])
        elif key.startswith(("vspeeds.", "perf.")) and get_field(rec, key) is not None:
            meta["status"][key] = "estime"
            meta["source"][key] = "Valeur estimée du type de base (absente de l'AHM)"
        else:
            meta["status"][key] = "a_renseigner"
    meta["status"]["cg_envelope"] = "compagnie"
    meta["source"]["cg_envelope"] = _ahm_src(h, "enveloppe de centrage au décollage (feuille C3)")
    meta["status"]["fuel_arm_table"] = "compagnie"
    meta["source"]["fuel_arm_table"] = _ahm_src(h, "effet du carburant sur l'index (feuille D4), converti en bras")
    return normalize_aircraft(rec)


def _ahm_ref_changes(h: dict, ref: dict):
    """Valeurs du référentiel proposées par le fichier : liste de (groupe, clé, libellé, valeur actuelle, valeur du fichier)."""
    ms = h.get("masses") or {}
    out = []
    std = (ms.get("pax") or {}).get("standard") or {}
    for k, lab in (("male", "Hommes"), ("female", "Femmes"), ("child", "Enfants"), ("infant", "Bébés")):
        v = std.get(k)
        if v is not None:
            out.append(("pax_masses", k, lab, ref["pax_masses"][k]["value"], v))
    eq = ms.get("equipage") or {}
    for k, key, lab in (("flight", "pnt", "PNT"), ("cabin", "pnc", "PNC")):
        v = eq.get(key)
        if v is not None:
            out.append(("crew_masses", k, lab, ref["crew_masses"][k]["value"], v))
    return out


def render_ahm_import(can_edit: bool, ver: int, db: dict):
    with st.expander("📥 Importer un fichier AHM (PDF de la compagnie)", expanded=bool(st.session_state.get("ahm_import"))):
        if AHM is None:
            st.error("Le module d'import (fichier ahm565.py) est absent du dépôt, ou la bibliothèque pymupdf n'est pas installée.")
            return
        if not can_edit:
            st.info("L'import est réservé aux profils admin et dispatcher.")
            return
        st.markdown("Le fichier AHM (formulaires EDP) contient les masses, les limites de centrage, le carburant, les soutes, "
                    "les cabines et les configurations d'un type d'avion. L'application l'analyse, vous montre le résultat, "
                    "et n'applique rien sans votre confirmation.")
        st.caption("Les données importées restent dans votre session : exportez ensuite votre profil pour les conserver. "
                   "Elles ne sont jamais écrites dans le dépôt de l'application. Les vitesses et performances ne figurent pas "
                   "dans un AHM : elles restent estimées (type de base) ou à renseigner.")
        up = st.file_uploader("Fichier AHM (PDF)", type=["pdf"], key=f"ahm_up_{ver}")
        if st.button("🔎 Analyser le fichier", key=f"ahm_go_{ver}", disabled=up is None):
            raw = up.getvalue()
            with st.spinner("Lecture du PDF en cours..."):
                try:
                    if not AHM.is_ahm565(raw):
                        st.session_state["ahm_import"] = {"err": "Ce PDF ne ressemble pas à un AHM (formulaires EDP)."}
                    else:
                        P = AHM.parse_all(data=raw, filename=up.name)
                        ac_raw, rap = AHM.convert(P)
                        st.session_state["ahm_import"] = {"name": up.name, "ac": ac_raw, "rap": rap,
                                                          "warn": P.get("avertissements") or [],
                                                          "hash": hashlib.sha256(raw).hexdigest()[:10]}
                except Exception as exc:                                    # fichier illisible : message clair, rien n'est modifié
                    st.session_state["ahm_import"] = {"err": f"Lecture impossible ({type(exc).__name__}). Le fichier n'est pas modifié."}
        imp = st.session_state.get("ahm_import")
        if not imp:
            return
        if imp.get("err"):
            st.error(imp["err"])
            return
        ac_raw, rap = imp["ac"], imp["rap"]
        icon = {"erreur": "🔴", "attention": "🟠", "info": "🔵"}
        st.markdown(f"**Résultat de l'analyse de « {imp['name']} »**")
        for lv, msg in rap:
            st.markdown(f"{icon.get(lv, '•')} **{lv.capitalize()}** : {msg}")
        for w_ in imp.get("warn") or []:
            st.markdown(f"🟠 **Attention** : {w_}")
        if ac_raw is None:
            st.error("Import impossible : aucune donnée n'a été modifiée.")
            return
        h = ac_raw["ahm"]
        so, ix = h["source"], h["index"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Type", so.get("type") or "—")
        c2.metric("Compagnie", so.get("organisme") or "—")
        c3.metric("Édition", so.get("edition") or "—")
        c4.metric("Date", so.get("date") or "—")
        st.caption(f"Unités du fichier : longueurs en {h['unites_fichier'].get('longueur')}, masses en {h['unites_fichier'].get('masse')}. "
                   f"Formule d'index : position de référence {ix['ref_m']:.4f} m, K = {ix['K']:g}, C = {ix['C_m']:g} (en mètres), "
                   f"LEMAC {ix['lemac_m']:.4f} m, MAC {ix['mac_m']:.4f} m.")

        st.markdown("**Configurations (masse à vide d'exploitation de la flotte, équipage, sièges)**")
        rows = []
        for c_ in h["configs"]:
            arm = ix["ref_m"] + ix["C_m"] * (c_["dow_flotte_index"] - ix["K"]) / c_["dow_flotte_kg"]
            rows.append({"Configuration": c_["nom"], "Sièges": c_["sieges"], "PNT": c_["pnt"], "PNC": c_["pnc"],
                         "DOW flotte (kg)": c_["dow_flotte_kg"], "DOW (%MAC)": round(AHM.pct_mac_of(h, arm), 2),
                         "Équipage (kg)": c_["crew_kg"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        st.markdown("**Immatriculations et limites de masse**")
        lim_rows = []
        for r_ in h.get("immatriculations") or []:
            lm = h["limites_par_immat"].get(r_.get("reg")) or h["limites_defaut"]
            lim_rows.append({"Immatriculation": r_.get("reg"), "MZFW": lm["zfw"], "MTOW": lm["tow"], "MLW": lm["law"],
                             "Masse maxi roulage": lm.get("taxi")})
        if lim_rows:
            st.dataframe(pd.DataFrame(lim_rows), hide_index=True, use_container_width=True)
        else:
            st.caption("Aucune immatriculation lue : limites standard utilisées.")

        st.markdown("**Soutes**")
        st.dataframe(pd.DataFrame([{"Soute": c_["name"], "Bras (m)": c_["arm_m"], "Capacité (kg)": c_["max_kg"],
                                    "Groupe": c_.get("groupe") or "", "Limite du groupe (kg)": c_.get("max_groupe_kg")}
                                   for c_ in ac_raw["cargo_comps"]]), hide_index=True, use_container_width=True)
        n_env = lambda k: len(ac_raw.get(k) or [])
        st.markdown(
            f"**Enveloppes de centrage :** ZFW {n_env('cg_envelope_zfw')} points · décollage {n_env('cg_envelope_tow')} points · "
            + (f"atterrissage {n_env('cg_envelope_law')} points" if n_env("cg_envelope_law") else "atterrissage : non définie par la compagnie")
            + f"  \n**Carburant :** {len(ac_raw['fuel_arm_table'])} points · capacité {fmt_num(ac_raw.get('mfuel'), 'kg')} · "
            f"densité {ac_raw.get('fuel_density')}"
            + (f" · taxi standard {fmt_num(h.get('taxi_standard_kg'), 'kg')}" if h.get("taxi_standard_kg") else ""))
        flags = [k for k, v in (h.get("impression") or {}).items() if v]
        st.markdown("**Impression sur la loadsheet (feuille C2) :** " + (", ".join(flags) if flags else "aucun indice demandé")
                    + (" · calage du stabilisateur lu dans le fichier" if h.get("stab") else " · pas de tableau de calage du stabilisateur"))

        ref = st.session_state.referentiel
        chg = _ahm_ref_changes(h, ref)
        upd_ref = False
        if chg:
            st.markdown("**Masses standard du référentiel proposées par le fichier**")
            st.dataframe(pd.DataFrame([{"Masse": lab, "Valeur actuelle (kg)": cur, "Valeur du fichier (kg)": new,
                                        "Changement": "oui" if abs(cur - new) > 1e-9 else "non"} for _, _, lab, cur, new in chg]),
                         hide_index=True, use_container_width=True)
            upd_ref = st.checkbox("Mettre à jour le référentiel avec ces masses (statut « Compagnie »)", value=True, key=f"ahm_ref_{ver}")
        bp = (h.get("masses") or {}).get("bagage_plan") or {}
        if bp.get("masse_par_pax"):
            st.caption(f"Le fichier prévoit {bp.get('masse_par_pax'):g} kg de bagages par passager pour la planification : "
                       "cette valeur n'est pas reprise (bagages : masse forfaitaire du référentiel ou pesée réelle).")

        st.markdown("**Vitesses et performances (absentes de l'AHM)**")
        bases = [k for k, v in db.items() if _has_speeds(v)]
        dflt = _ahm_default_base(db, so.get("type") or "")
        NONE_B = "— Aucun (à renseigner) —"
        base_sel = st.selectbox("Type de base pour des vitesses et performances estimées", [NONE_B] + bases,
                                index=(bases.index(dflt) + 1) if dflt in bases else 0, key=f"ahm_base_{ver}")
        if base_sel == NONE_B:
            st.caption("Vitesses et performances « à renseigner » : la loadsheet fonctionne, mais les onglets de performances "
                       "et de carburant restent bloqués tant qu'elles ne sont pas saisies.")
        else:
            st.caption("Valeurs estimées copiées du type de base : elles sont signalées comme telles et ne remplacent pas "
                       "les données du manuel de vol.")
        default_name = f"{so.get('type') or 'Type importé'} — {so.get('organisme') or 'compagnie'}"
        new_name = st.text_input("Nom du type dans l'application", value=default_name, key=f"ahm_name_{ver}").strip()
        exists = new_name in db
        replace = False
        if exists:
            replace = st.checkbox(f"Un type « {new_name} » existe déjà : le remplacer", key=f"ahm_replace_{ver}")
        ok_prev = st.checkbox("J'ai vérifié cet aperçu : les données correspondent au fichier de la compagnie", key=f"ahm_ok_{ver}")
        if st.button("✅ Appliquer l'import", key=f"ahm_apply_{ver}", disabled=not (ok_prev and new_name and (not exists or replace)),
                     use_container_width=True):
            rec = build_ahm_record(ac_raw, db.get(base_sel) if base_sel != NONE_B else None)
            rec["type"] = so.get("type") or new_name
            st.session_state.db[new_name] = rec
            if upd_ref and chg:
                nref = copy.deepcopy(ref)
                for grp, k, lab, cur, new in chg:
                    nref[grp][k].update({"value": float(new), "status": "compagnie",
                                         "source": _ahm_src(h, "masses standard (feuille C2/D)")})
                nref["identification"].update({"organisme": so.get("organisme") or "", "document": "AHM",
                                               "version": f"édition {so.get('edition') or '?'}",
                                               "date_application": so.get("date") or ""})
                st.session_state.referentiel = nref
            audit("ahm_imported", f"{new_name} · {imp['name']} · empreinte {imp['hash']}")
            st.session_state.dirty = True
            st.session_state["_pending_select"] = new_name
            st.session_state["_flash"] = (f"Type « {new_name} » importé depuis l'AHM. Choisissez la configuration et "
                                          "l'immatriculation dans la barre latérale. Exportez votre profil pour le conserver.")
            st.session_state.pop("ahm_import", None)
            st.session_state.ed_version = ver + 1
            st.rerun()
        if st.button("Annuler l'import", key=f"ahm_cancel_{ver}"):
            st.session_state.pop("ahm_import", None)
            st.rerun()


def render_ahm_type_info(ac: dict):
    """Données propres à un type importé d'un AHM (lecture seule)."""
    h = ac.get("ahm")
    if not h:
        return
    so = h.get("source") or {}
    with st.expander("📄 Données issues de l'AHM pour ce type", expanded=False):
        st.markdown(f"Fichier : **{so.get('fichier')}** · {so.get('organisme')} · édition {so.get('edition')} du {so.get('date')}.")
        st.caption("La masse à vide, l'équipage, les zones passagers et les limites de masse dépendent de la configuration et de "
                   "l'immatriculation choisies dans la barre latérale : les valeurs saisies à la main pour ces champs sont "
                   "remplacées par celles du fichier. Pour les changer, réimportez le fichier.")
        for st_, lab in (("zfw", "Enveloppe ZFW"), ("law", "Enveloppe atterrissage")):
            env = cg_env_for(ac, st_)
            if env:
                st.markdown(f"**{lab}**")
                st.dataframe(pd.DataFrame([{"Masse (kg)": p_["weight_kg"], "Limite avant (m)": p_["fwd_m"], "Limite arrière (m)": p_["aft_m"]}
                                           for p_ in env]), hide_index=True, use_container_width=True)
            elif st_ == "law":
                st.caption("Enveloppe d'atterrissage : non définie par la compagnie (limite non contrôlée).")
        st.caption("L'enveloppe au décollage est modifiable dans le tableau « Enveloppe de centrage » ci-dessous.")


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
    render_ahm_import(can_edit, ver, db)

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
    render_ahm_type_info(ac)
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
    mode_lab = c3.selectbox("Mode de chargement", ["Vrac", "ULD (positions du fichier AHM)"],
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
            <div style="font-size:0.65rem;color:#556688;letter-spacing:1.5px;margin-top:2px">v6.2 | EG CONSEIL</div>
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
        if ac.get("ahm"):
            if AHM is None:
                st.warning("Module d'import AHM absent (fichier ahm565.py) : configuration et immatriculation indisponibles.")
            else:
                _h = ac["ahm"]
                st.markdown("**🛋 Configuration et immatriculation (AHM)**")
                _cfgs = {c_["nom"]: c_ for c_ in _h["configs"]}
                _cfg_sel = st.selectbox("Configuration", list(_cfgs), key=f"ahm_cfg_{selected_ac}",
                                        format_func=lambda n_: f"{n_} · PNT {_cfgs[n_].get('pnt')} / PNC {_cfgs[n_].get('pnc')}")
                _OTHER = "Autre (hors liste)"
                _regs = [r_["reg"] for r_ in (_h.get("immatriculations") or []) if r_.get("reg")]
                _reg_sel = st.selectbox("Immatriculation", _regs + [_OTHER], key=f"ahm_reg_{selected_ac}")
                if _reg_sel == _OTHER:
                    st.caption("Immatriculation hors liste : aucun ajustement de masse à vide ni limites propres à l'avion ; "
                               "les limites standard du fichier sont utilisées.")
                ac = AHM.apply_selection(ac, _cfg_sel, None if _reg_sel == _OTHER else _reg_sel)

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
            for k_ in [k_ for k_ in st.session_state if str(k_).startswith(("cargo_keep_", "use_cargo_"))]:
                del st.session_state[k_]
            for key in ["authenticated", "username", "user_info", "db", "profile_info", "dirty", "sel_ac", "ed_version", "pax_info", "referentiel", "flight_summary", "fuel_in", "ref_docs", "ref_docs_ver", "preparer_name", "cdb_name", "locked", "ls_edition", "wx", "wx_sel", "wx_country", "lmc_editor", "acc_result", "acc_gen_pwd", "flight_date", "flight_time", "ahm_import"]:
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
    missing_mc = missing_fields(ac, "mc")
    blocked_mc = bool(missing_mc)

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
        render_flight_tab(ac, selected_ac, airports, blocked_mc, missing_mc, user_info)

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
                dep_airport_perf = st.selectbox("Aéroport de départ", list(airports.keys()), key="perf_dep",
                                                format_func=lambda k: ap_label(airports[k]))
                dep_data = airports[dep_airport_perf]
                elev_ft  = ap_elev_ft(dep_data)
                rwy_m    = dep_data.get("rwy_length_m")
                _elev_txt = f"{elev_ft} ft" if dep_data.get("elev_ft") is not None else "non renseignée (0 ft utilisé)"
                if rwy_m is None:
                    st.caption(f"Élévation : {_elev_txt} | Piste : non renseignée (aucune correction de longueur de piste appliquée)")
                else:
                    st.caption(f"Élévation : {_elev_txt} | Piste : {rwy_m} m")
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
                rwy_alt_ft    = ap_elev_ft(airports[st.session_state.get("dest", list(airports.keys())[1])]) \
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
        ap_all_full = list(airports.keys())
        _countries = sorted({g_ for a_ in airports.values() for g_ in ap_groups(a_)},
                            key=lambda c_: (0 if c_ == "France" else 1 if c_ == "France – outre-mer" else 2, c_))
        _ALL = "Tous les pays"
        wx_country = st.selectbox("Filtrer la liste par pays", [_ALL] + _countries, key="wx_country")
        ap_all = ap_all_full if wx_country == _ALL else [
            k_ for k_, a_ in airports.items() if wx_country in ap_groups(a_)]
        flight_aps = []
        for n_ in [st.session_state.get("origin"), st.session_state.get("dest")] + list(st.session_state.get("alternates", [])):
            if n_ in ap_all_full and n_ not in flight_aps:
                flight_aps.append(n_)
        st.session_state.setdefault("wx_sel", flight_aps or ap_all_full[:3])

        def _use_flight_airports():
            st.session_state["wx_sel"] = flight_aps or ap_all_full[:3]

        _opts = ap_all + [k_ for k_ in st.session_state.get("wx_sel", []) if k_ not in ap_all]
        sel = st.multiselect("Aéroports à interroger", _opts, key="wx_sel",
                             format_func=lambda k: ap_label(airports[k]))
        WX_MAX = 12
        if len(sel) > WX_MAX:
            st.warning(f"{len(sel)} aéroports sélectionnés : seuls les {WX_MAX} premiers seront interrogés à chaque actualisation.")
            sel = sel[:WX_MAX]
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
        render_pdf_tab(blocked_mc, missing_mc)

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
        AETHERDISPATCH v6.2 — EG Conseil & Lobbying © 2026 — Système de gestion handling aérien augmenté par IA<br>
        Données à usage opérationnel restreint — Vérification obligatoire par le commandant de bord
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================
if __name__ == "__main__":
    main()
