# AETHERDISPATCH - Rapport d'audit (version v7.0)

Date : 15/10/2026. Les corrections décrites ci-dessous sont incluses dans le paquet v7.0. Résultat des essais de réception sur le paquet : 32 réussis sur 32.

## 1. Périmètre et méthode

- 16 AHM 565 de la compagnie, chacun en Excel et en PDF : 62 groupes d'immatriculations importés, tous les groupes, sans erreur.
- Comparaison Excel contre PDF, groupe par groupe, avec tolérance d'arrondi.
- 16 tableaux DOW/DOI de la compagnie rapprochés de la formule de construction : environ 405 000 cellules.
- Liste « Flight - Pantry code list » rev. 36 : 1 457 liaisons lues.
- Essais de réception automatisés (Streamlit AppTest) : 20 essais d'origine, plus 12 essais ajoutés.

## 2. Défauts corrigés

| N° | Constat | Correction |
|---|---|---|
| 1 | A330F : l'AHM contient deux versions de soutes (TC-JDP, JDR, JDS, JCI, JOV, JOY, JOZ : BAY 51/52/53, CPT 5 à 3 468 kg ; TC-JDO et TC-JOO : BAY 51/53, CPT 5 à 1 881 kg). L'import retenait une seule version pour dix avions, sans le dire. | La flotte est découpée en 4 groupes selon les feuilles auxquelles chaque avion appartient. |
| 2 | A330F : table de carburant déduite à 16 224 kg au lieu de 78 024 kg (séquence de remplissage Excel lue de façon incomplète, simple avertissement). | Lecture des décimales corrigée ; une table incohérente (écart supérieur à 2 %) est rejetée et le bras du carburant reste à renseigner. |
| 3 | B737-800 et 737-8 MAX : positions 1A, 1B, 4A, 4B absentes. | Lues et rattachées à CPT 1 / CPT 4 puis à HOLD FWD / HOLD AFT. |
| 4 | Limites 7.3 combinées (ex. A321-231 : CPT 3 + CPT 4 + CPT 5 ≤ 3 400 kg) jamais appliquées. | Lues et appliquées via la chaîne de groupes (soute, groupe, limite combinée) dans l'optimisation, le contrôle et le PDF. |
| 5 | A321-271 : l'import échouait (masses écrites « 75600 kg »). | Lecture corrigée. |
| 6 | Positions ULD en notation scientifique (A330F, B777F) perdues dans l'Excel ; lignes parasites VERSION (B777-300). | Corrigé. |
| 7 | A350 : courbes de stabilité au sol par vent illisibles dans le PDF ; équipage standard 350D absent du PDF ; tableaux de cabine d'équipage illisibles dans tous les PDF. | Corrigé : Excel et PDF identiques. |
| 8 | Stabilité au sol : la plus contraignante de toutes les tables était appliquée sans le dire (A350 : 11 %MAC erroné). | Choix du vent à l'écran ; par défaut, la plus contraignante des tables interprétables, annoncée ; au-delà des tables, limite « non évaluée ». |
| 9 | Pas de construction du DOW/DOI. | Constructeur AHM : base + équipage + pantry + eau, retenu uniquement sur choix explicite. Contrôle : A350 TC-LGI, 139 725 kg et DOI 83,8, identiques au tableau. |
| 10 | LMC indicatives seulement. | LMC structurées : position, variation signée, recalcul ZFW/TOW/LW et centrage, dépassement détecté, lignes non évaluées signalées, reprise dans le PDF. |
| 11 | Empreinte de verrouillage incomplète. | Étendue : zones passagers, moments, DOW construit, vent, profil et édition AHM, limites, référentiel, résultat de la LMC. |
| 12 | Limites cumulées 7.2 des cargos non contrôlées. | Contrôle par zone (A330F, B777F), avec réserve sur le pont (voir 4). |
| 13 | Import sans état de conformité. | Tableau par rubrique : conforme / absent / non vérifiable / discordant, plus contrôle croisé Excel contre PDF. |

## 3. Résultats de la campagne

- Excel contre PDF : identiques sur les 62 groupes (un seul écart, sans conséquence : décompte de lignes 7.5 de l'A330F, 3 contre 4).
- Conformité des 62 groupes : 652 rubriques conformes, 81 non vérifiables, 69 absentes, 4 discordantes (A330F : unité de longueur de la feuille d'unités, mètres, contredisant la formule d'index, pouces ; l'unité plausible est retenue et signalée).
- DOW/DOI : environ 99,7 % des cellules reproduites (DOW à 0,5 kg, DOI à 0,3). Les écarts viennent des tableaux eux-mêmes (section 5).

## 4. Réserves et points ouverts

- Limites cumulées 7.2 : l'AHM ne précise pas le pont. Le pont principal est supposé ; un dépassement est affiché en avertissement, sans blocage. À confirmer.
- Courbes de stabilité de l'A350 pour un vent de 80 km/h et plus : géométrie non interprétable avec certitude (« Je ne sais pas »). Écartées.
- A350 350A/350B : deux tables d'eau potable différentes (350A : -1 060 kg à 0/10, 350B : -1 500 kg). L'AHM ne dit pas à quel avion s'applique chacune : l'application demande le choix.
- B777-300, groupe 777C : la feuille d'eau potable est libellée « 77C ». Avec cette table, les 30 240 cellules du tableau DOW/DOI sont retrouvées exactement ; l'application demande tout de même la confirmation.
- Compositions d'équipage de cabine non tabulées (ex. 7 PNC sur A350) : refusées, aucune interpolation.
- Limites 7.1, 7.4 et 7.5 (cargos) : lues, comptées, non appliquées. Signalées « non vérifiable ».
- B777-300 : tableau VERSION 1 à 15 des soutes sans correspondance avec les immatriculations dans le texte : concept de version de soutes non traité.
- Le pré-calcul de la répartition idéale des bagages n'intègre pas encore le DOW construit ; le contrôle final, lui, l'intègre.
- Catalogue démo (aetherdispatch_aircraft_db.json) : régénéré dans la v7.0. Les positions CPT 1A, 1B, 4A et 4B du B737-800 (groupes 738A/738B) et du B737-8 MAX (groupe 738M) ont été reprises de l'AHM (feuille D 2) ; les autres types ont été comparés aux AHM sur leur groupe de référence, sans écart de soutes. Les types ATR n'ont pas de soutes dans le catalogue (fiches commerciales).
- Code pantry proposé d'après la liste rev. 36 ; plusieurs codes pour une liaison (TK ou AJET) : choix demandé, jamais imposé.

## 5. Anomalies des tableaux DOW/DOI de la compagnie (sources)

- A319 : pantry Z -1 kg, tous avions.
- A320-271 : équipages à 4 pilotes à 50 % d'eau, -85 kg (320M, 320N).
- A321-231 : TC-JMH à TC-JMK, 2/2 U à 75 %, +1 006 kg ; TC-JML +1 126 kg ; codes à 4 pilotes absents de l'AHM (320 cellules non calculables).
- TC-LBC et TC-LBD : 2/4 U à 75 %, -238 kg.
- A321-271 : 2/2 Y à 75 % (+427, +428, +350 kg, valeur identique à la colonne S).
- A330F : TC-JOY, pantry F répète des valeurs (25 cellules).
- B787-9 : trois immatriculations absentes du tableau DOW.

## 6. Essais de réception

Voir la dernière exécution : tests/run_all.py (variable AHM_DIR pour les fichiers de la compagnie ; sans eux, les essais concernés sont « IGNORÉS »).

## 7. Fichiers modifiés ou nouveaux (paquet v7.0)

Modifiés : app.py (étiquette v7.0), ahm_text.py, ahm_adapter.py, uldplan.py, tests/run_all.py, aetherdispatch_aircraft_db.json.
Nouveaux : dowbuild.py, conformity.py, pantry_routes.json, pantry_list.py, tests/campagne_ahm.py, tests/dowdoi.py, RAPPORT_AUDIT.md.
