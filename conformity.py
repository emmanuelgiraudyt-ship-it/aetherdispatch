"""Contrôle de conformité d'un import AHM : pour chaque rubrique attendue, l'un des quatre états
   « conforme » (lu et cohérent), « absent » (rubrique non trouvée dans le fichier), « non vérifiable » (lu, mais non
   contrôlable ou non appliqué) ou « discordant » (deux lectures ou deux sources se contredisent). Aucune valeur de substitution
   n'est présentée comme issue du fichier."""
import re

OK, ABS, NV, DISC = "conforme", "absent", "non vérifiable", "discordant"
SKIP = {"source", "where", "pages", "sheet", "not_applied", "remark", "libelle"}


def _txt(rap):
    return " ".join(m for _, m in rap)


def check(entry, rap):
    rows = []
    add = lambda rub, etat, det="": rows.append((rub, etat, det))
    rt = _txt(rap)
    if not entry:
        return [("Fichier", ABS, "aucune donnée exploitable")]
    # unités et index
    if re.search(r"Unités de longueur contradictoires|paraît incohérente", rt):
        add("Unités et formule d'index", DISC, "l'unité de longueur du fichier contredit la formule d'index : l'unité plausible est retenue, à vérifier")
    elif entry.get("balance") and entry.get("units"):
        add("Unités et formule d'index", OK, f"index = K + masse x (bras - réf.) / C ; longueurs en {entry['units'].get('length')}")
    else:
        add("Unités et formule d'index", ABS)
    # masses limites
    mw = (entry.get("limits") or {}).get("maximum_weights_kg") or {}
    pr = (entry.get("limits") or {}).get("per_registration") or {}
    if all(mw.get(k) for k in ("mzfw", "mtow", "mlw")):
        sets = {tuple(sorted((v or {}).items())) for v in pr.values()} if pr else set()
        add("Masses limites (MZFW, MTOW, MLW)", OK, f"{len(pr)} immatriculation(s)" + (f", {len(sets)} jeux de valeurs distincts" if len(sets) > 1 else ""))
    else:
        add("Masses limites (MZFW, MTOW, MLW)", ABS if not mw else NV, "valeur(s) manquante(s)" if mw else "")
    # enveloppes
    tabs = (entry.get("cg_envelopes") or {}).get("tables") or []
    envs = tabs[0].get("envelopes") if tabs else {}
    have = sorted(k for k, v in (envs or {}).items() if v and len(v.get("fwd", [])) >= 2 and len(v.get("aft", [])) >= 2)
    if have:
        det = ", ".join(have) + (f" ; {len(tabs)} tables dans l'AHM, la première est appliquée" if len(tabs) > 1 else "")
        add("Enveloppes de centrage", OK if len(tabs) == 1 else NV, det)
    else:
        add("Enveloppes de centrage", ABS)
    # base
    ba = (entry.get("basic_weight") or {}).get("aircraft") or []
    add("Masse et index de base", OK if ba else ABS, f"{len(ba)} appareil(s)" if ba else "")
    # soutes
    hs = (entry.get("holds") or {}).get("entries") or []
    add("Soutes (capacités, bras, groupes)", OK if hs else ABS, f"{len(hs)} entrée(s)" if hs else "")
    # carburant
    fu = entry.get("fuel") or {}
    cum = fu.get("cumulative") or {}
    if cum.get("points"):
        add("Carburant (table masse-bras)", NV if cum.get("derived_from") else OK,
            "table déduite de la séquence de remplissage, non publiée par l'AHM" if cum.get("derived_from") else f"{len(cum['points'])} points")
    else:
        add("Carburant (table masse-bras)", ABS)
    # cabine
    cf = (entry.get("saleable_configurations") or {}).get("configurations") or []
    if cf:
        add("Configurations de sièges", OK, f"{len(cf)} configuration(s)")
    else:
        add("Configurations de sièges", ABS, "avion tout cargo ou rubrique absente")
    # équipage standard
    if re.search(r"Masses standard d'équipage absentes", rt):
        add("Masses d'équipage", ABS, "absentes du fichier : valeurs de repli (85 / 75 kg) utilisées, non issues de l'AHM")
    else:
        add("Masses d'équipage", OK if entry.get("crew") else ABS)
    # ULD
    uld_need = any(str(h.get("mode")) == "uld" for h in hs) or bool(entry.get("uld_positions"))
    up = (entry.get("uld_positions") or {}).get("positions") or []
    if up:
        add("Positions ULD", OK, f"{len(up)} positions")
    else:
        add("Positions ULD", ABS if uld_need else NV, "" if uld_need else "non requis pour une soute en vrac")
    # DOW/DOI
    db = entry.get("dow_build") or {}
    if db.get("issues"):
        add("Construction DOW / DOI", NV, " ".join(db["issues"])[:240])
    elif db.get("pantry") and (db.get("crew_table") or {}).get("cockpit") and db.get("water"):
        add("Construction DOW / DOI", OK, "équipage, pantry et eau lus")
    else:
        add("Construction DOW / DOI", ABS, "tables d'équipage, de pantry ou d'eau potable incomplètes")
    # stabilité
    it = entry.get("ideal_trim") or {}
    tp = it.get("tipping_tables") or []
    if not it:
        add("Centrage idéal et stabilité au sol", ABS)
    elif any(len(t.get("points") or []) > 2 and re.search(r"km/h|wind speed", str(t.get("condition", "")).lower()) for t in tp):
        add("Centrage idéal et stabilité au sol", NV, "courbes de vent fort à géométrie non interprétable écartées")
    else:
        add("Centrage idéal et stabilité au sol", OK, f"{len(tp)} table(s)")
    # structurel
    stc = entry.get("structural") or {}
    na = stc.get("not_applied_count") or {}
    if na:
        add("Limites structurelles (§ 7)", NV, "lues mais non appliquées : " + ", ".join(f"§ {k} ({v} ligne(s))" for k, v in na.items()))
    elif stc.get("combined") or stc.get("cumulative"):
        add("Limites structurelles (§ 7)", OK, f"{len(stc.get('combined', []))} combinée(s), {len(stc.get('cumulative', []))} cumulée(s)")
    else:
        add("Limites structurelles (§ 7)", ABS, "aucune limite lue")
    add("Vitesses et performances", ABS, "ne figurent pas dans un AHM : estimées (type de base) ou à renseigner")
    return rows


def _num(a):
    return isinstance(a, (int, float)) and not isinstance(a, bool)


def diff(a, b, path="", out=None, tol=0.006):
    """Écarts entre deux lectures du même AHM (ex. Excel et PDF). Arrondis tolérés (0,6 % ou 0,6 unité de dernier chiffre)."""
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k in SKIP:
                continue
            if k not in a or k not in b:
                out.append((f"{path}/{k}", "présent d'un seul côté", None if k not in a else "présent", None if k not in b else "présent"))
            else:
                diff(a[k], b[k], f"{path}/{k}", out, tol)
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            out.append((path, "nombre d'éléments", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f"{path}[{i}]", out, tol)
    elif _num(a) and _num(b):
        if abs(a - b) > max(0.6, abs(a) * tol) and abs(a - b) > 1e-9:
            out.append((path, "valeur", a, b))
    elif a != b and not (a in (None, "") and b in (None, "")):
        if isinstance(a, str) and isinstance(b, str) and re.sub(r"\W+", "", a).lower() == re.sub(r"\W+", "", b).lower():
            return out
        out.append((path, "texte", str(a)[:40], str(b)[:40]))
    return out
