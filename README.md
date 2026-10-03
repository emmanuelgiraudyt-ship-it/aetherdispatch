# AETHERDISPATCH v5.0

Prototype d'aide à la préparation de la loadsheet et au suivi trafic pour le handling aérien : masse et centrage, carburant, météo, export PDF.

**Statut : prototype non certifié.** Cet outil n'est pas un système approuvé de masse et centrage. Il ne remplace ni le système de la compagnie, ni la vérification par le commandant de bord, et ne doit pas être utilisé en exploitation sans validation préalable par l'exploitant.

---

## Fonctions

L'application comporte huit onglets.

| Onglet | Contenu |
|---|---|
| Nouveau vol | Masse et centrage : DOW, ZFW, TOW et LW, avec le centrage de chacun et le contrôle des limites. Passagers par catégorie (prévus et final), bagages (masse forfaitaire ou pesée), fret et courrier par soute, répartition des bagages par priorité de chargement. Carburant (bloc, taxi, trip). Équipage, autres masses, limites de masse du jour, chargements spéciaux (signalement NOTOC), dernières modifications (LMC), numéro d'édition avec verrouillage, récapitulatif pour le commandant de bord. |
| Performances et V-Speeds | Vitesses indicatives calculées par une formule approchée. Elles ne proviennent pas des tables du manuel de vol. |
| Carburant et météo | Plan carburant estimatif, METAR et TAF des aéroports du vol, briefing météo en PDF. |
| Optimisation cargo | Répartition du fret par programmation linéaire. |
| Export PDF | Load & Trim Sheet au format A4, avec option d'inclure les vitesses. |
| Historique | Vols enregistrés, filtres, export CSV. |
| Données aéronef | Édition des données par type, enveloppe de centrage, bras du carburant selon la quantité, référentiel compagnie, import et export du profil, modèle Excel. |
| Journal et comptes | Journal des actions et assistant de création de comptes (réservés aux profils habilités). |

## Types d'aéronefs

31 types sont référencés.

- **9 types complets**, avec des valeurs estimées de démonstration : Airbus A319-100, A320-200, A321-200, A350-900 ; Boeing 737-800, 737-900ER, 777-300ER ; ATR 42-600, ATR 72-600.
- **22 types partiels** : capacité et masse maximale au décollage renseignées, calculs de masse et centrage bloqués tant que les données ne sont pas saisies.
- **Hors périmètre** : Boeing 777X, avions cargo, chargement en conteneurs (ULD).

## Origine des données

Chaque valeur porte un statut visible dans l'application : constructeur, estimé, réglementaire, compagnie ou à renseigner. Le PDF indique l'origine des données et porte la mention « DONNÉES NON CERTIFIÉES » tant que toutes les données critiques ne proviennent pas de la compagnie ou de la réglementation.

- Aucune donnée issue du MANEX ou du GOM d'une compagnie n'est incluse dans ce dépôt.
- Les masses standard des passagers et de l'équipage sont celles du règlement (UE) n° 965/2012, aéronefs de 20 sièges passagers ou plus. Les masses forfaitaires de bagage (11, 13 et 15 kg) sont à confirmer dans le MANEX de l'exploitant.
- La météo provient de l'API publique du NOAA / NWS Aviation Weather Center (aviationweather.gov). Cette source n'est pas contractuelle : elle est à vérifier auprès du service météorologique compétent.

## Limites connues

- L'hébergement gratuit peut effacer l'historique, le journal et les modifications non exportées lors d'un redémarrage. Le profil compagnie doit être exporté puis réimporté à chaque session.
- Les limites de centrage sont constantes tant que l'enveloppe masse-centrage n'est pas saisie pour le type concerné.
- Le calcul du carburant et des vitesses est approximatif.
- Le verrouillage d'une édition est un repère d'intégrité, et non une signature électronique.
- Le NOTOC n'est pas généré par l'application : seul son besoin est signalé.

## Accès

Les identifiants sont attribués par l'administrateur. Ils ne figurent pas dans ce dépôt.

## Déploiement sur Streamlit Community Cloud

Fichiers du dépôt :

```
app.py                  Application principale
compagnie_db.json       Données des aéronefs
airports_db.json        Aéroports
users.json              Comptes
requirements.txt        Dépendances
.streamlit/config.toml  Thème
README.md               Ce fichier
```

Au besoin, l'application crée elle-même `flight_history.json` et `audit_log.json`.

1. Déposer ces fichiers sur GitHub.
2. Sur share.streamlit.io, créer une application depuis le dépôt, avec `app.py` comme fichier principal.
3. Pour mettre à jour : déposer le fichier modifié sur GitHub (il remplace l'ancien). L'application redémarre seule en une à cinq minutes ; « Manage app », puis « Reboot app » force le redémarrage.

Les fichiers `manifest.json`, `sw.js` et le dossier `static/` des versions précédentes ne servent plus : ils peuvent être supprimés.

## Développement local

```bash
git clone <adresse-du-dépôt>
cd aetherdispatch
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Architecture technique

- Interface : Streamlit.
- Calcul : pandas, numpy ; optimisation : PuLP (version 2.9.0).
- Graphiques : plotly. PDF : fpdf2. Fichiers Excel (modèle de référentiel) : openpyxl.
- Météo : requests, API publique du NOAA.
- Données : fichiers JSON.

## Avertissement réglementaire

Les résultats de cet outil sont fournis à titre indicatif. Les calculs de masse et centrage, de carburant et de performances relèvent de la responsabilité de l'exploitant et du commandant de bord, qui doivent les vérifier avec les données et procédures approuvées. L'utilisation d'un système informatisé de masse et centrage impose à l'exploitant de contrôler la fiabilité des résultats produits.

## Contact

emmanuelgiraud.yt@gmail.com
