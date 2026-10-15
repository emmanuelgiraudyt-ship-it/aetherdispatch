# -*- coding: utf-8 -*-
"""Essais de réception AETHERDISPATCH : Streamlit (AppTest), PuLP/CBC, PyMuPDF. Lancement : python tests/run_all.py"""
import os, sys, time, traceback
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import logging
logging.disable(logging.CRITICAL)
from streamlit.testing.v1 import AppTest

RESULTS = []


class Skip(Exception):
    """Essai non exécutable dans cet environnement (fichiers de la compagnie absents)."""


def check(name, fn):
    if os.environ.get("ONLY") and os.environ["ONLY"] not in name:      # ONLY="DOW/DOI" : n'exécute que les essais dont le nom contient ce texte
        return
    t = time.time()
    try:
        fn()
        RESULTS.append((name, "RÉUSSI", f"{time.time() - t:.1f} s", ""))
    except Skip as e:
        RESULTS.append((name, "IGNORÉ", f"{time.time() - t:.1f} s", str(e)[:200]))
    except AssertionError as e:
        RESULTS.append((name, "ÉCHEC", f"{time.time() - t:.1f} s", str(e)[:200]))
    except Exception as e:                                          # noqa
        RESULTS.append((name, "ERREUR", f"{time.time() - t:.1f} s", f"{type(e).__name__}: {e}"[:200]))


def new_app(typ):
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=600)
    at.session_state["authenticated"] = True
    at.session_state["username"] = "admin"
    at.session_state["user_info"] = {"role": "admin", "nom": "Admin"}
    at.run()
    sel = [s for s in at.selectbox if s.label.startswith("Type d'a")][0]
    sel.set_value(typ)
    at.run()
    return at


def num(at, prefix):
    return [x for x in at.number_input if x.key and x.key.startswith(prefix)][0]


def btn(at, text=None, prefix=None):
    for b in at.button:
        if (prefix and b.key and b.key.startswith(prefix)) or (text and text in (b.label or "")):
            return b
    return None


def no_exc(at, where=""):
    assert not at.exception, f"exception {where}: {[e.value[:150] for e in at.exception]}"


TYPES = ["Airbus A319-132", "Airbus A320-232", "Airbus A321-231", "Airbus A350-941", "Boeing 737-800", "Boeing 737-8 MAX",
         "Boeing 777-300ER", "Boeing 787-9", "Airbus A330-243F", "Boeing 777F"]
DEMO = " · démo"

for t in TYPES:
    check(f"Affichage sans exception : {t}", lambda t=t: no_exc(new_app(t + DEMO), t))


def t_fuel_blocked():
    at = new_app("Airbus A320-232" + DEMO)
    num(at, "bag_n_").set_value(100); at.run()
    num(at, "fuel_bloc_").set_value(6000); num(at, "fuel_taxi_").set_value(300); num(at, "fuel_trip_").set_value(9000); at.run()
    fs = at.session_state["flight_summary"]
    assert fs["fuel_blocked"] and not fs["status_ok"], "carburant incohérent non détecté"
    assert fs["lw"] >= fs["zfw"], "masse à l'atterrissage inférieure à la masse sans carburant"
    assert btn(at, "GÉNÉRER LA LOAD").disabled, "loadsheet éditable avec un carburant incohérent"


def t_fuel_ok():
    at = new_app("Airbus A320-232" + DEMO)
    num(at, "bag_n_").set_value(100); at.run()
    num(at, "fuel_bloc_").set_value(6000); num(at, "fuel_taxi_").set_value(300); num(at, "fuel_trip_").set_value(3000); at.run()
    fs = at.session_state["flight_summary"]
    assert not fs["fuel_blocked"], "carburant cohérent refusé"
    assert abs(fs["lw"] - (fs["zfw"] + 2700)) <= 1, "masse à l'atterrissage incohérente"
    assert not btn(at, "GÉNÉRER LA LOAD").disabled


check("Carburant incohérent : calcul refusé, loadsheet bloquée, masse à l'atterrissage cohérente", t_fuel_blocked)
check("Carburant cohérent : calcul accepté, masse à l'atterrissage = ZFW + carburant restant", t_fuel_ok)


def uld_flow(typ, bags, stock=None):
    at = new_app(typ + DEMO)
    num(at, "bag_n_").set_value(bags); at.run(); no_exc(at, "bagages")
    est = [i.value for i in list(at.info) + list(at.success) if "Nombre d'ULD à utiliser" in i.value]
    assert est, "estimation du nombre d'ULD absente"
    if stock:
        num(at, "akestock_").set_value(stock); at.run()
    btn(at, prefix="planbtn_").click(); at.run(); no_exc(at, "proposition")
    nb = [m.value for m in at.metric if m.label == "ULD bagages"]
    assert nb and int(nb[0]) > 0, "aucun ULD de bagages proposé"
    ap = btn(at, "Appliquer cette répartition")
    assert ap is not None and not ap.disabled, "application impossible"
    ap.click(); at.run(); no_exc(at, "application")
    ls = btn(at, "GÉNÉRER LA LOAD")
    assert not ls.disabled, "loadsheet bloquée après application"
    ls.click(); at.run(); no_exc(at, "loadsheet")
    return at


for t in ("Airbus A350-941", "Boeing 777-300ER", "Boeing 787-9"):
    check(f"Parcours ULD bagages → proposition → application → loadsheet : {t}", lambda t=t: uld_flow(t, 300))
check("Excédent d'AKE en soute vrac (A350, 300 bagages, 2 AKE)", lambda: uld_flow("Airbus A350-941", 300, stock=2))


def t_alt_mode():
    at = new_app("Airbus A320-232" + DEMO)
    r = [x for x in at.radio if x.label.startswith("Mode de chargement")]
    assert r, "choix vrac / ULD absent"
    r[0].set_value("ULD (AKH, PKC)"); at.run(); no_exc(at, "mode ULD")
    num(at, "bag_n_").set_value(150); at.run()
    btn(at, prefix="planbtn_").click(); at.run(); no_exc(at, "proposition")
    assert [m.value for m in at.metric if m.label == "ULD bagages"], "pas de proposition en mode ULD"


check("A320 : variante ULD (AKH, PKC) au choix du vol", t_alt_mode)


def t_freighter(typ):
    at = new_app(typ + DEMO)
    num(at, "uldcargo_").set_value(20000); at.run()
    est = [i.value for i in at.info if "Nombre d'ULD à utiliser pour le fret" in i.value]
    assert est, "estimation fret absente"
    btn(at, prefix="planbtn_").click(); at.run(); no_exc(at, "proposition")
    ap = btn(at, "Appliquer cette répartition"); assert ap is not None
    ap.click(); at.run(); no_exc(at, "application")
    ls = btn(at, "GÉNÉRER LA LOAD"); assert not ls.disabled
    ls.click(); at.run(); no_exc(at, "loadsheet")


for t in ("Airbus A330-243F", "Boeing 777F"):
    check(f"Cargo : fret → proposition par position → application → loadsheet : {t}", lambda t=t: t_freighter(t))


def t_solver():
    import app as A
    import uldplan as U
    dm = A.load_demo_types({})
    ac = dm["Airbus A350-941" + DEMO]
    rows = ac["uld"]["rows"]
    comps = {c["name"]: {"max": float(c["max_kg"]), "groupe": c.get("groupe"), "max_groupe": c.get("max_groupe_kg")}
             for c in ac["cargo_comps"] if c["name"] in set(ac["uld"]["comps"])}
    tare = {"AKE": 80, "PKC": 80, "PMC": 110, "PAG": 100}
    states = [{"name": "tow", "m_other": 200000, "mom_other": 200000 * 36.0, "lim": lambda w: (35.0, 38.0)}]
    caps = {t: {"Bagages": 1500 if t in ("AKE", "PKC") else 0, "Fret": 1500 if t in ("AKE", "PKC") else 5000,
                "Courrier": 1500 if t in ("AKE", "PKC") else 5000} for t in ("AKE", "PKC", "PMC", "PAG")}
    r = U.solve(rows, {"Bagages": 6000, "Fret": 0, "Courrier": 0}, tare, caps, comps, states, {"state": "tow", "arm_m": 36.5})
    assert r["ok"] or r["plan"], r["messages"]
    assert all(x["uld"] in ("AKE", "PKC") for x in r["plan"] if x["nature"] == "Bagages"), "bagages sur palette"
    gross = {}
    for x in r["plan"]:
        assert x["gross"] <= x["max"] + 1e-6, "masse de position dépassée"
    from itertools import combinations
    occ = [rows[x["row"]] for x in r["plan"]]
    for a, b in combinations(occ, 2):
        if a["hold"] == b["hold"] and set(a["sides"]) & set(b["sides"]):
            assert min(a["to_m"], b["to_m"]) - max(a["from_m"], b["from_m"]) <= 0.03, "positions qui se recouvrent"
    fx = [{"uld": "PMC", "nature": "Fret", "content": 4500}, {"uld": "PAG", "nature": "Courrier", "content": 900}]
    r2 = U.solve(rows, {"Bagages": 3000, "Fret": 0, "Courrier": 0}, tare, caps, comps, states, {"state": "tow", "arm_m": 36.5}, fixed=fx,
                 time_limit=20)
    assert sum(1 for x in r2["plan"] if x.get("fixed")) == 2, "ULD imposés non placés"


check("Solveur : bagages en conteneurs, positions exclusives, ULD imposés", t_solver)


# ── Essais ajoutés à l'audit : LMC, verrouillage, DOW/DOI, vent, cumul 7.2, import réel ───────────────────────
import glob, ast, json as _json
AHM_DIR = os.environ.get("AHM_DIR", "/mnt/user-data/uploads")


def ahm_file(sub, pat="*AHM565*.xlsx"):
    f = sorted(glob.glob(os.path.join(AHM_DIR, "**", sub, pat), recursive=True) + glob.glob(os.path.join(AHM_DIR, sub, pat)))
    if not f:
        raise Skip(f"fichier AHM {sub} absent ({AHM_DIR})")
    return f[0]


_CACHE = {}


def client_entry(sub, group, pat="*AHM565*.xlsx"):
    import ahm_text as T
    k = (sub, group, pat)
    if k not in _CACHE:
        p = ahm_file(sub, pat)
        sh, _ = T.read_sheets(open(p, "rb").read(), os.path.basename(p))
        _CACHE[k] = (sh, T.build_entry(sh, group), p)
    return _CACHE[k]


def new_app_client(sub, group, label):
    """Application avec un type client importé d'un AHM réel (fichier temporaire, supprimé ensuite)."""
    ent = client_entry(sub, group)
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    inj = ('    try:\n        import ahm_text as _T\n        _p = %r\n        _s, _ = _T.read_sheets(open(_p, "rb").read(), _p)\n'
           '        _e, _r = _T.build_entry(_s, %r)\n        _ac, _rap = AD.to_app_record(_e, "client", {"label": %r, "edition": "test"})\n'
           '        out[%r] = build_ahm_record(_ac, None, "compagnie")\n    except Exception:\n        pass\n    return out\n\n\ndef is_freighter_ac'
           % (ent[2], group, label, label))
    assert "    return out\n\n\ndef is_freighter_ac" in src
    path = os.path.join(ROOT, "_app_inj.py")
    open(path, "w", encoding="utf-8").write(src.replace("    return out\n\n\ndef is_freighter_ac", inj, 1))
    try:
        at = AppTest.from_file(path, default_timeout=600)
        at.session_state["authenticated"] = True
        at.session_state["username"] = "admin"
        at.session_state["user_info"] = {"role": "admin", "nom": "Admin"}
        at.run()
        sel = [x for x in at.selectbox if x.label.startswith("Type d'a")][0]
        assert label in sel.options, "type client non injecté"
        sel.set_value(label)
        at.run()
        no_exc(at, "type client")
        return at
    finally:
        pass


def lmc_app(rows, typ="Airbus A320-232" + DEMO):
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=600)
    at.session_state["authenticated"] = True
    at.session_state["username"] = "admin"
    at.session_state["user_info"] = {"role": "admin", "nom": "Admin"}
    at.run()
    [x for x in at.selectbox if x.label.startswith("Type d'a")][0].set_value(typ)
    at.run()
    num(at, "bag_n_").set_value(100); at.run()
    at.session_state["lmc_editor"] = {"edited_rows": {}, "deleted_rows": [], "added_rows": rows}
    at.run()
    no_exc(at, "LMC")
    return at


def lmc_row(pos, kg, nature="Bagages"):
    return {"Heure (UTC)": "10:00", "Nature": nature, "Position": pos, "Description": "essai", "Variation (kg)": float(kg)}


def t_lmc_eval():
    at = lmc_app([lmc_row("Carburant", 300), lmc_row("", -84, "Passagers")])
    mt = {m.label: m for m in at.metric}
    assert "TOW après modifications" in mt and mt["TOW après modifications"].delta.replace(" ", "").replace(" ", "").endswith("+300kg"), "effet carburant non recalculé"
    assert mt["ZFW après modifications"].delta.replace(" ", "").endswith("+0kg"), "ZFW modifié par une variation de carburant"
    assert any("sans position reconnue" in w.value for w in at.warning), "ligne sans position non signalée"


def t_lmc_limit():
    at0 = lmc_app([])
    hold = [c["name"] for c in at0.session_state["db"]["Airbus A320-232" + DEMO]["cargo_comps"]][0]
    at = lmc_app([lmc_row(hold, 90000)])
    assert any("après modification" in e.value for e in at.error), "dépassement de soute / masse non détecté après LMC"
    assert not at.session_state["flight_summary"]["status_ok"], "statut OK malgré une LMC hors limite"


def t_lock_invalidation():
    at = lmc_app([])
    [r for r in at.radio if r.label.startswith("Statut de la load")][0].set_value("Final"); at.run()
    for k in ("male", "female"):
        num(at, f"pax_final_{k}_").set_value(40)
    at.run()
    b = btn(at, prefix="btn_lock")
    assert b is not None and not b.disabled, "verrouillage indisponible en statut Final"
    b.click(); at.run()
    assert at.session_state["locked"], "verrou non posé"
    fp0 = at.session_state["locked"]["hash"]
    assert any("verrouillée" in s.value for s in at.success), "verrou non affiché"
    at.session_state["lmc_editor"] = {"edited_rows": {}, "deleted_rows": [], "added_rows": [lmc_row("Carburant", 100)]}
    at.run()
    assert any("ont changé depuis le verrouillage" in w.value for w in at.warning), "verrou non invalidé par une LMC"
    num(at, "pax_final_male_").set_value(41)
    at.session_state["lmc_editor"] = {"edited_rows": {}, "deleted_rows": [], "added_rows": []}
    at.run()
    assert any("ont changé depuis le verrouillage" in w.value for w in at.warning), "verrou non invalidé par un changement de PAX"


def t_dow_build():
    sh, (e, rap), p = client_entry("A350-941", "350C")
    at = new_app_client("A350-941", "350C", "A350 client essai")
    mt = {m.label: m.value for m in at.metric}
    assert mt.get("DOW construit") == "139,725 kg", f"DOW construit {mt.get('DOW construit')}"
    assert mt.get("DOI construit") == "83.80", f"DOI construit {mt.get('DOI construit')}"
    cb = [c for c in at.checkbox if c.key and c.key.startswith("dowb_use")][0]
    assert not cb.value, "construction utilisée sans choix explicite"
    cb.check(); at.run(); no_exc(at, "construction")
    assert any("DOW retenu" in i.value for i in at.info), "DOW construit non retenu"
    assert at.session_state["flight_summary"]["dow"] == 139725, "DOW du calcul différent de la construction"
    sbx = {c.key: c for c in at.selectbox if c.key and c.key.startswith("dowb_cc_")}
    k = list(sbx)[0]
    assert 7 not in sbx[k].options, "composition de cabine non tabulée proposée"


def t_wind_selector():
    at = new_app_client("A350-941", "350C", "A350 client essai")
    sel = [c for c in at.selectbox if c.key and c.key.startswith("gs_wind_")]
    assert sel, "choix du vent absent"
    opts = sel[0].options
    assert opts[0].startswith("Le plus") and "0 kt" in opts and "37.8 kt" in opts, opts
    assert not any(o.startswith(("43", "48", "54", "59", "64", "70", "75")) for o in opts), "courbe non interprétable proposée"
    sel[0].set_value("37.8 kt"); at.run(); no_exc(at, "vent")
    assert any("Stabilité au sol" in c.value for c in list(at.caption) + list(at.error)), "limite de stabilité non affichée"


def t_cumulative():
    import ahm_adapter as AD
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    fn = [n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "cumulative_check"][0]
    ns = {}
    exec(ast.get_source_segment(src, fn), ns)
    for sub in ("A330F", "B777F"):
        sh, (e, rap), p = client_entry(sub, "ALL" if sub == "B777F" else None or "TC-JDP, TC-JDR, TC-JDS, TC-JCI, TC-JOV, TC-JOY, TC-JOZ")
        ac, _ = AD.to_app_record(e, "client", {"label": sub})
        rows = [r for r in ac["uld"]["rows"] if "MAIN" in r["hold"].upper()]
        ok = ns["cumulative_check"](ac, [{"pos": r["label"], "hold": r["hold"], "comp": r["comp"], "arm": r["arm_m"], "gross": 1.0} for r in rows])
        assert ok and not ok["unassigned"] and not ok["msgs"], f"{sub} : {ok}"
        ko = ns["cumulative_check"](ac, [{"pos": r["label"], "hold": r["hold"], "comp": r["comp"], "arm": r["arm_m"], "gross": 9000.0} for r in rows[:4]])
        assert ko["msgs"], f"{sub} : dépassement cumulé non détecté"


def t_a330f_versions():
    import ahm_text as T
    sh, _e, p = client_entry("A330F", "TC-JDO")
    gl = [g for g, _n in T.groups_of(sh)]
    assert len(gl) == 4 and any(g == "TC-JDO" for g in gl), gl
    a = T.build_entry(sh, "TC-JDO")[0]
    b = T.build_entry(sh, [g for g in gl if g.startswith("TC-JDP")][0])[0]
    na = {h["label"] for h in a["holds"]["entries"]}
    nb = {h["label"] for h in b["holds"]["entries"]}
    assert "BAY 52" not in na and "BAY 52" in nb, (na, nb)
    assert len(b["basic_weight"]["aircraft"]) == 7 and len(a["basic_weight"]["aircraft"]) == 1
    cum = b["fuel"].get("cumulative") or {}
    assert cum and abs(cum["max_weight_kg"] - 78024) < 1 and len(cum["points"]) >= 40, f"table carburant déduite incomplète : {cum.get('max_weight_kg')}"


def t_groups_chain_737():
    import ahm_adapter as AD
    sh, (e, rap), p = client_entry("B737-800", "738A")
    ac, _ = AD.to_app_record(e, "client", {"label": "x"})
    names = [c["name"] for c in ac["cargo_comps"]]
    for n in ("CPT 1A", "CPT 1B", "CPT 4A", "CPT 4B"):
        assert n in names, f"{n} absent : {names}"
    c1a = [c for c in ac["cargo_comps"] if c["name"] == "CPT 1A"][0]
    assert len(c1a["groupes"]) >= 2 and c1a["groupes"][0][0] == "CPT 1", c1a["groupes"]


def t_conformity():
    import conformity as CF
    sh, (e, rap), p = client_entry("B777F", "ALL")
    rows = {r[0]: r[1] for r in CF.check(e, rap)}
    assert rows["Masses d'équipage"] == "absent" and rows["Limites structurelles (§ 7)"] == "non vérifiable", rows
    assert rows["Positions ULD"] == "conforme" and rows["Vitesses et performances"] == "absent", rows
    d = CF.diff({"a": {"limits": 100000.0, "x": [1.0, 2.0]}}, {"a": {"limits": 100000.4, "x": [1.0, 2.9]}})
    assert len(d) == 1 and d[0][0] == "/a/x[1]", d


def t_dow_formula_tables():
    sh, (e, rap), p = client_entry("A350-941", "350C")
    import dowbuild as DB
    bd = DB.from_record(e["dow_build"])
    r = DB.compute(bd, "TC-LGI", (2, 0), "A", 100.0)
    assert r and abs(r[0] - 139725) < 0.5 and abs(r[1] - 83.8) <= 0.15, r
    assert DB.compute(bd, "TC-LGI", (2, 7), "A", 100.0) is None, "composition non tabulée calculée"
    # groupe « 350A, 350B » : eau potable ambiguë, aucune table choisie d'office
    sh2, (e2, _r2), _p2 = client_entry("A350-941", "350A, 350B")
    b2 = DB.from_record(e2["dow_build"])
    assert not b2["water"] and len(b2["water_variants"]) == 2 and b2["issues"], "ambiguïté d'eau potable non signalée (A350 350A/350B)"
    assert DB.compute(b2, "TC-LGA", (2, 0), "A", 100.0) is None and DB.compute(b2, "TC-LGA", (2, 0), "A", 50.0) is None, "table d'eau choisie d'office"
    # groupe 777C : feuille d'eau libellée « 77C » (faute de frappe probable), confirmation exigée
    sh3, (e3, _r3), _p3 = client_entry("B777-300", "777C")
    b3 = DB.from_record(e3["dow_build"])
    assert not b3["water"] and any("77C" in k for k in b3["water_variants"]) and any("faute de frappe" in m for m in b3["issues"]), b3["issues"]


for nm_, fn_ in (("LMC : variation signée à une position, recalcul des masses et du centrage", t_lmc_eval),
                 ("LMC : dépassement de limite détecté, statut du vol refusé", t_lmc_limit),
                 ("Verrouillage : invalidé par une LMC et par un changement de PAX", t_lock_invalidation),
                 ("DOW/DOI : construction AHM = tableau THY (A350 TC-LGI), choix explicite, compositions tabulées", t_dow_build),
                 ("DOW/DOI : formule reproduite, composition non tabulée refusée", t_dow_formula_tables),
                 ("Stabilité au sol : choix du vent, courbes non interprétables écartées", t_wind_selector),
                 ("Limites cumulées 7.2 (A330F, B777F) : conformité et dépassement", t_cumulative),
                 ("A330F : version de soutes selon l'immatriculation (4 groupes)", t_a330f_versions),
                 ("B737-800 : positions 1A, 1B, 4A, 4B et chaîne de groupes", t_groups_chain_737),
                 ("Conformité de l'import : états et comparaison Excel / PDF", t_conformity)):
    check(nm_, fn_)


def t_boeing_client_flow():
    at = new_app_client("B737-800", "738A", "B737 client essai")
    num(at, "bag_n_").set_value(160); at.run(); no_exc(at, "bagages 737")
    fs = at.session_state["flight_summary"]
    ld = {c["name"]: c["total"] for c in fs["comps"]}
    assert {"CPT 1A", "CPT 1B", "CPT 2", "CPT 3", "CPT 4A", "CPT 4B"} <= set(ld), list(ld)
    ac = at.session_state["db"]["B737 client essai"]
    mx = {c["name"]: c for c in ac["cargo_comps"]}
    for g in ("CPT 1", "CPT 4"):
        mem = [n for n, c in mx.items() if g in [x[0] for x in c["groupes"]]]
        lim = [x[1] for x in mx[mem[0]]["groupes"] if x[0] == g][0]
        assert sum(ld[n] for n in mem) <= lim + 1e-6, f"{g} : {sum(ld[n] for n in mem)} > {lim}"
    for g in ("HOLD FWD", "HOLD AFT"):
        mem = [n for n, c in mx.items() if g in [x[0] for x in c["groupes"]]]
        lim = [x[1] for x in mx[mem[0]]["groupes"] if x[0] == g][0]
        assert sum(ld[n] for n in mem) <= lim + 1e-6, f"{g} dépassé"
    assert fs["bag_total"] > 0 and not at.exception


check("Boeing 737-800 importé : bagages répartis sur 1A/1B/2/3/4A/4B, limites de groupes respectées", t_boeing_client_flow)


def t_pdf_equality():
    """Les valeurs du récapitulatif (écran) se retrouvent à l'identique dans le PDF, avec une LMC évaluée et un DOW construit."""
    import app as A
    import pymupdf
    at = new_app_client("A350-941", "350C", "A350 client essai")
    cb = [c for c in at.checkbox if c.key and c.key.startswith("dowb_use")][0]
    cb.check(); at.run()
    num(at, "bag_n_").set_value(120); at.run()
    at.session_state["lmc_editor"] = {"edited_rows": {}, "deleted_rows": [], "added_rows": [lmc_row("Carburant", 200)]}
    at.run(); no_exc(at, "pdf")
    fs = at.session_state["flight_summary"]
    txt = "".join(pg.get_text() for pg in pymupdf.open(stream=A.generate_pdf(fs, False), filetype="pdf"))
    flat = txt.replace("\u202f", " ").replace("\xa0", " ")
    fmt = lambda v: f"{int(round(float(v))):,}".replace(",", " ")
    for k in ("dow", "zfw", "tow", "lw"):
        assert fmt(fs[k]) in flat, f"{k} = {fmt(fs[k])} absent du PDF"
    ev = fs.get("lmc_eval")
    assert ev and fmt(ev["tow"]) in flat, "masse après LMC absente du PDF"
    assert fs["dow_source"].startswith("construction AHM"), fs["dow_source"]


check("PDF : DOW, ZFW, TOW, LW et résultat des LMC identiques à l'écran (A350 importé)", t_pdf_equality)

try:
    os.remove(os.path.join(ROOT, "_app_inj.py"))
except OSError:
    pass

w = max(len(r[0]) for r in RESULTS)
print("RAPPORT DES ESSAIS AETHERDISPATCH")
for n, s, d, m in RESULTS:
    print(f"{s:7} {n:<{w}}  {d}" + (f"  -> {m}" if m else ""))
bad = [r for r in RESULTS if r[1] not in ("RÉUSSI", "IGNORÉ")]
print(f"\n{len(RESULTS) - len(bad)} réussis sur {len(RESULTS)}")
sys.exit(1 if bad else 0)
