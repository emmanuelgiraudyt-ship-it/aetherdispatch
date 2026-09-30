# ✈ AETHERDISPATCH v2.0

**Agent IA de gestion handling aérien — Masse & Centrage · Performances · V-Speeds · Météo METAR · Carburant OACI · Optimisation Cargo · Export PDF**

Développé par **EG Conseil & Lobbying** | Mars 2026

---

## 🗂 Structure du dépôt

```
AETHERDISPATCH/
├── app.py                    # Application principale Streamlit
├── compagnie_db.json         # Base données aéronefs & compagnies
├── airports_db.json          # Base données aéroports (25 aéroports)
├── users.json                # Utilisateurs & mots de passe (SHA-256)
├── flight_history.json       # Historique vols (généré auto)
├── manifest.json             # Manifest PWA
├── sw.js                     # Service Worker PWA
├── requirements.txt          # Dépendances Python
├── README.md                 # Ce fichier
└── .streamlit/
    └── config.toml           # Thème futuriste AETHERDISPATCH
```

---

## 🚀 Déploiement sur Streamlit Community Cloud — 3 étapes

### Étape 1 : Préparer le dépôt GitHub

1. Créez un nouveau dépôt GitHub public ou privé (ex : `aetherdispatch`)
2. Uploadez **tous les fichiers** du projet dans ce dépôt
3. Vérifiez que `app.py` est à la racine du dépôt
4. Vérifiez que `requirements.txt` est présent

```bash
# Via Git en ligne de commande :
git init
git add .
git commit -m "AETHERDISPATCH v2.0 — déploiement initial"
git branch -M main
git remote add origin https://github.com/VOTRE_USER/aetherdispatch.git
git push -u origin main
```

### Étape 2 : Connecter à Streamlit Cloud

1. Rendez-vous sur **https://share.streamlit.io**
2. Connectez votre compte GitHub
3. Cliquez sur **"New app"**
4. Renseignez :
   - **Repository** : `VOTRE_USER/aetherdispatch`
   - **Branch** : `main`
   - **Main file path** : `app.py`
5. Cliquez sur **"Deploy!"**

### Étape 3 : Configurer et partager

1. Attendez le déploiement (2-5 minutes)
2. Votre URL sera : `https://VOTRE_USER-aetherdispatch-app-XXXX.streamlit.app`
3. Partagez l'URL avec votre équipe handling

> ⚠ **Note PWA** : Pour activer pleinement le PWA (service worker + manifest), vous aurez besoin d'un domaine HTTPS personnalisé. Sur Streamlit Cloud, le HTTPS est fourni automatiquement, mais le SW nécessite un serveur qui sert les fichiers statiques. Pour une PWA complète, envisagez un déploiement sur **Railway.app** ou **Render.com**.

---

## 🔐 Identifiants par défaut

| Utilisateur | Mot de passe | Rôle |
|-------------|-------------|------|
| `admin` | `admin` | Administrateur |
| `handling1` | `123` | Agent Handling |
| `dispatcher` | `password` | Dispatcher OPS |

> ⚠ **IMPORTANT** : Changez ces mots de passe immédiatement après déploiement.
> Modifiez `users.json` en générant de nouveaux hashes SHA-256 :
> ```python
> import hashlib; print(hashlib.sha256("VOTRE_MDP".encode()).hexdigest())
> ```

---

## 🛩 Aéronefs configurés

- **Airbus A320-200** (Air France) — 174 sièges
- **Boeing B737-800** (Transavia) — 189 sièges
- **ATR72-600** (HOP!) — 72 sièges

Pour ajouter un aéronef, éditez `compagnie_db.json` en respectant la structure existante.

---

## 📱 Installation PWA (Mobile)

### iPhone / iPad (Safari) :
1. Ouvrez l'URL AETHERDISPATCH dans Safari
2. Appuyez sur le bouton **Partager** (rectangle avec flèche)
3. Sélectionnez **"Sur l'écran d'accueil"**
4. Confirmez → AETHERDISPATCH apparaît comme une app native

### Android (Chrome) :
1. Ouvrez l'URL dans Chrome
2. Une bannière **"Ajouter à l'écran d'accueil"** apparaît automatiquement
3. Ou : menu ⋮ → **"Installer l'application"**

---

## ⚙ Fonctionnalités

| Module | Statut | Description |
|--------|--------|-------------|
| Masse & Centrage | ✅ Opérationnel | ZFW, TOW, LW, CG %MAC avec enveloppe Plotly |
| Performances & V-Speeds | ✅ Opérationnel | V1, VR, V2, VREF, VAPP avec corrections ISA/altitude/piste |
| Plan carburant OACI | ✅ Opérationnel | Trip + Contingence + Alternate + Réserve + Taxi |
| Météo METAR Live | ✅ Opérationnel | Via API aviationweather.gov (NOAA) |
| Optimisation Cargo PuLP | ✅ Opérationnel | Maximisation revenu par programmation linéaire |
| Export PDF | ✅ Opérationnel | Load & Trim Sheet complète A4 |
| OCR Manifest | ⚡ Optionnel | Requiert EasyOCR (lourd, RAM intensive) |
| Historique vols | ✅ Opérationnel | Stockage JSON local, export CSV |
| PWA Mobile | ✅ Manifest + SW | Installable sur iOS/Android |
| Multi-utilisateurs | ✅ Opérationnel | Auth SHA-256, 3 rôles |

---

## 🔧 Développement local

```bash
# Cloner le dépôt
git clone https://github.com/VOTRE_USER/aetherdispatch.git
cd aetherdispatch

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou : venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run app.py
```

Application disponible sur : http://localhost:8501

---

## 📊 Architecture technique

```
Streamlit (Frontend + Backend)
    │
    ├── Auth : hashlib SHA-256 + JSON users
    ├── M&C  : calculs Python + Plotly (enveloppe interactive)
    ├── Perf : formules paramétriques CS-25 (V-speeds)
    ├── Fuel : planning OACI complet
    ├── Météo: API REST aviationweather.gov
    ├── Optim: PuLP CBC (programmation linéaire entière)
    ├── OCR  : EasyOCR (optionnel)
    └── PDF  : FPDF2 (génération Load & Trim Sheet)
```

---

## ⚖ Avertissement réglementaire

> Ce système est un outil d'aide à la décision. Tous les calculs de masse & centrage, performances et plan carburant **doivent être vérifiés et validés par le commandant de bord** conformément aux réglementations OACI, EASA et au manuel d'exploitation (MEL/QRH) de chaque aéronef. AETHERDISPATCH ne se substitue en aucun cas aux systèmes de calcul certifiés des compagnies aériennes.

---

## 📞 Contact & Support

**EG Conseil & Lobbying**
www.egconseil.fr
AETHERDISPATCH © 2026 — Tous droits réservés
