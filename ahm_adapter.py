# -*- coding: utf-8 -*-
"""Adaptateur : type lu dans un AHM (ou dans le catalogue démo) -> enregistrement d'aéronef d'AETHERDISPATCH.

Le résultat a exactement la forme produite par ahm565.convert() : un enregistrement `ac` avec le bloc `ac["ahm"]`.
La barre latérale (Configuration, Immatriculation), apply_selection() et toute la loadsheet fonctionnent donc sans
modification. Deux modes : « demo » (catalogue sourcé, statut « démo ») et « client » (fichier de l'exploitant).
"""
import json
import re

LEN = {"m": 1.0, "in": 0.0254}
PHASE = {"ZEROFUEL": "zfw", "TAKEOFF": "tow", "LANDING": "law"}


def load_catalogue(path="aetherdispatch_aircraft_db.json"):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_envelope(fwd, aft, lemac_m, mac_m):
    """Enveloppe [{weight_kg, fwd_m, aft_m}] à partir des listes (masse, %MAC) avant et arrière."""
    def dedupe(pts):
        out = []
        for w, v in sorted(pts, key=lambda p: p[0]):
            if out and w <= out[-1][0]:
                w = out[-1][0] + 0.5
            out.append((w, v))
        return out

    def interp(pts, x):
        pts = sorted(pts)
        if x <= pts[0][0]:
            return pts[0][1]
        if x >= pts[-1][0]:
            return pts[-1][1]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= x <= x1:
                return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return pts[-1][1]
    f = dedupe([(w, lemac_m + pct / 100 * mac_m) for w, pct in fwd])
    a = dedupe([(w, lemac_m + pct / 100 * mac_m) for w, pct in aft])
    ws = sorted({round(w, 1) for w, _ in f} | {round(w, 1) for w, _ in a})
    return [{"weight_kg": w, "fwd_m": round(interp(f, w), 4), "aft_m": round(interp(a, w), 4)} for w in ws]


def _sheet(block):
    s = (block or {}).get("source")
    s = s[0] if isinstance(s, list) and s else (s or {})
    return s.get("sheet") or "?"


def _span(e):
    v = e["values"]
    if v.get("arm_from") is not None and v.get("arm_to") is not None:
        return (min(v["arm_from"], v["arm_to"]), max(v["arm_from"], v["arm_to"]))
    if v.get("arm_centroid") is not None:
        return (v["arm_centroid"], v["arm_centroid"])
    return None


def _rank(e):
    return (1 if e["kind"] == "cpt" else 0, len(e["label"]))


def _is_child(o, e):
    """o est contenu dans e (même mode et même pont) : étendue incluse, et plus fin (plus étroit, ou rang plus fin à étendue égale)."""
    so, se = _span(o), _span(e)
    if so is None or se is None or o is e or o["mode"] != e["mode"] or (o.get("deck") or "") != (e.get("deck") or ""):
        return False
    eps = 1e-6
    if not (se[0] - eps <= so[0] and so[1] <= se[1] + eps):
        return False
    wo, we = so[1] - so[0], se[1] - se[0]
    return wo < we - eps or (abs(wo - we) <= eps and _rank(o) > _rank(e))


def _comps(t, ix, f, status, srcfn):
    """Compartiments de soute (vrac, puis ULD par compartiment) : on garde les plus fins ; le plus petit parent donne le groupe.
    Un compartiment ULD qui recouvre, sur le même pont, un compartiment déjà retenu en vrac est une autre façon de charger
    la même soute : il n'est pas compté deux fois."""
    allents = [e for e in (t.get("holds") or {}).get("entries", []) if e["values"].get("max_kg")]
    out, used, kept = [], set(), []
    for mode in ("bulk", "uld"):
        ents = [e for e in allents if e["mode"] == mode]
        for e in ents:
            if any(_is_child(o, e) for o in ents):
                continue
            sp = _span(e)
            if mode == "uld" and sp and sp[1] > sp[0]:
                clash = False
                for k in kept:
                    sk = _span(k)
                    if sk and (k.get("deck") or "") == (e.get("deck") or ""):
                        ov = min(sp[1], sk[1]) - max(sp[0], sk[0])
                        if ov > 0.5 * min(sp[1] - sp[0], max(sk[1] - sk[0], 1e-9)):
                            clash = True
                if clash:
                    continue
            kept.append(e)
            v = e["values"]
            if v.get("index_per_kg") is not None:
                arm = ix["ref_m"] + ix["C_m"] * v["index_per_kg"]
            elif v.get("arm_centroid") is not None:
                arm = v["arm_centroid"] * f
            elif sp:
                arm = (sp[0] + sp[1]) / 2 * f
            else:
                continue
            parents = [o for o in ents if _is_child(e, o)]
            par = min(parents, key=lambda o: (o["values"]["max_kg"], -_rank(o)[0])) if parents else None
            tag = ""
            if mode == "uld":
                tag = " (ULD" + (", pont principal" if (e.get("deck") or "").upper() == "MAIN" else "") + ")"
            name = e["label"] + tag
            if name in used:
                name = f"{name} [{(e.get('deck') or '').title()}]"
            used.add(name)
            out.append({"name": name, "arm_m": round(arm, 4), "max_kg": v["max_kg"], "status": status,
                        "source": srcfn(f"feuille {_sheet(t['holds'])}, soutes"),
                        "groupe": (par["label"] + tag) if par else None,
                        "max_groupe_kg": par["values"]["max_kg"] if par else None, "volume_m3": v.get("volume"), "type": None})
    return out


_MAIN_CFG = re.compile(r"^(SINGLE ROW (PAG|PMC)|M SIZE (SBS|SINGLE))$")
_LOW_CFG = re.compile(r"^(AKE|PAG|PMC)$")


def _uld_rows(up, comps, f):
    """Positions ULD (feuille D3, § 3.1) au format du plan de chargement par position. Configurations retenues : pont principal
    en palettes une rangée (PAG, PMC) ou M SIZE côte à côte ; soute inférieure en AKE, PAG, PMC. Les autres variantes
    (centrales, latérales, A SIZE, longues) ne sont pas reprises. Les positions qui se recouvrent sont exclusives dans le calcul."""
    uc = [c for c in comps if "(ULD" in c["name"]]
    if not (up and up.get("positions") and uc):
        return None
    rows = []

    def comp_of(hold, arm_m):
        main = hold.upper().startswith("MAIN")
        cand = [c for c in uc if (("pont principal" in c["name"]) == main)]
        return min(cand, key=lambda c: abs(c["arm_m"] - arm_m))["name"] if cand else None

    for p in up["positions"]:
        main = p["hold"].upper().startswith("MAIN")
        if not (_MAIN_CFG.match(p["config"]) if main else _LOW_CFG.match(p["config"])):
            continue
        typ = re.sub(r"^SINGLE ROW ", "", p["config"])
        typ = re.sub(r" (SBS|SINGLE)$", "", typ)
        pos = p["pos"]
        arm_m = round(p["arm"] * f, 4)
        comp = comp_of(p["hold"], arm_m)
        if comp is None:
            continue
        if "/" in pos:
            a, b = pos.split("/")
            names = [(a, "L"), (a[:-1] + b, b)] if len(b) == 1 else [(a, "L"), (b, "R")]
            kind = "C"
        else:
            names = [(pos, None)]
            kind = "P"
        for nm, side in names:
            rows.append({"id": f"{nm}\u00b7{typ}", "label": f"{nm} \u00b7 {typ}", "hold": p["hold"], "pos": nm, "bay": nm[:-1] if side else nm,
                         "kind": kind, "sides": [side] if side else ["L", "R"], "max_kg": p["max_kg"], "arm_m": arm_m,
                         "from_m": round(p["from"] * f, 4), "to_m": round(p["to"] * f, 4), "types": [typ], "comp": comp})
    if not rows:
        return None
    order = {h: i for i, h in enumerate(dict.fromkeys(r["hold"] for r in rows))}
    rows.sort(key=lambda r: (order[r["hold"]], r["from_m"], r["id"]))
    return {"rows": rows, "specs": [], "comps": sorted({r["comp"] for r in rows})}


def to_app_record(t, mode="demo", info=None):
    """t : type (catalogue v2 ou résultat de ahm_text.build_entry). info : dict d'identité (label, organisme, edition, date,
    fichier, watermark). Renvoie (ac, rapport) ou (None, rapport)."""
    info = info or {}
    demo = mode == "demo"
    status = "demo" if demo else "compagnie"
    rap = []
    unit = t["units"]["length"]
    f = LEN[unit]
    b = t["balance"]
    wm = t["limits"]["maximum_weights_kg"]
    ix = {"ref_m": b["reference_arm"] * f, "C_m": b["C"] * f, "K": b["K"], "mac_m": b["mac_length"] * f, "lemac_m": b["lemac"] * f}
    org = "Catalogue démo AETHERDISPATCH" if demo else (info.get("organisme") or "compagnie")
    ed, dt = info.get("edition") or "?", info.get("date")

    def srcfn(txt):
        if demo:
            return f"Catalogue démo sourcé ({info.get('document', 'AHM THY')}, {ed}) : {txt}. DOCUMENT NON UTILISABLE POUR L'EXPLOITATION"
        return f"AHM {org} édition {ed}" + (f" du {dt}" if dt else "") + f" : {txt}"
    tabs = t["cg_envelopes"]["tables"]
    if len(tabs) > 1:
        rap.append(("attention", f"{len(tabs)} tables d'enveloppes dans l'AHM : la table « {tabs[0]['name']} » est utilisée."))
    env = {}
    for ph, key in PHASE.items():
        g = tabs[0]["envelopes"].get(ph)
        if g and len(g["fwd"]) >= 2 and len(g["aft"]) >= 2:
            env[key] = build_envelope([(p["weight_kg"], p["pct_mac"]) for p in g["fwd"]],
                                      [(p["weight_kg"], p["pct_mac"]) for p in g["aft"]], ix["lemac_m"], ix["mac_m"])
    if "zfw" not in env or "tow" not in env:
        return None, rap + [("erreur", "Enveloppes ZFW et TOW nécessaires : type non injectable.")]
    cum = (t.get("fuel") or {}).get("cumulative") or {}
    fuel = [{"fuel_kg": p["weight_kg"], "arm_m": round(ix["ref_m"] + ix["C_m"] * p["index"] / p["weight_kg"], 4)}
            for p in cum.get("points", []) if p["weight_kg"] > 0]
    if len(fuel) >= 2:
        fuel.insert(0, {"fuel_kg": 0.0, "arm_m": fuel[0]["arm_m"]})
    else:
        fuel = []
    mfuel = cum.get("max_weight_kg") or sum(tk.get("max_weight_kg") or 0 for tk in (t.get("fuel") or {}).get("tanks", [])) or None
    # équipage : PNT du fichier ; PNC = minimum réglementaire d'un PNC par tranche de 50 sièges (le fichier ne donne que
    # les emplacements disponibles, pas l'effectif). Inclus dans la masse à vide d'exploitation, au bras de la masse de base.
    cr = t.get("crew") or {}
    pnt = cr.get("pnt") or 2
    kg_pnt, kg_pnc = cr.get("kg_pnt", 85), cr.get("kg_pnc", 75)
    A = t["basic_weight"]["aircraft"]
    code = lambda a: a.get("demo_code") or a["reg"]

    def idx_native(a):
        if a.get("index") is not None:
            return a["index"], (a["arm"] if a.get("arm") is not None else
                                b["reference_arm"] + b["C"] * (a["index"] - b["K"]) / a["basic_weight_kg"])
        arm = b["lemac"] + a["pct_mac"] / 100 * b["mac_length"]
        return a["basic_weight_kg"] * (arm - b["reference_arm"]) / b["C"] + b["K"], arm
    base_rows = [(code(a), a["basic_weight_kg"], *idx_native(a)) for a in A]
    cabsec = {s["section"]: s for s in ((t.get("cabin") or {}).get("sections") or [])}
    cfgs = []
    for c in t["saleable_configurations"]["configurations"]:
        seats = sum(s["seats"] for s in c["sections"])
        pnc = -(-seats // 50) if seats else 0
        crew_kg = pnt * kg_pnt + pnc * kg_pnc
        rows = []
        for cd, w, i_b, arm in base_rows:
            rows.append((cd, w + crew_kg, i_b + crew_kg * (arm - b["reference_arm"]) / b["C"]))
        _, W0, I0 = rows[0]
        adj = {cd: (W - W0, I - I0) for cd, W, I in rows}
        zones = []
        cls = re.findall(r"(\d+)\s*([A-Z])", c["name"].replace(" ", ""))
        left = [[k_, int(n_)] for n_, k_ in cls] if len(cls) > 1 else []        # classes de la configuration, de l'avant vers l'arrière
        for s in c["sections"]:
            cs = cabsec.get(s["id"]) or {}
            by_class = {}
            if left:
                rest_s = s["seats"]
                for ent in left:                                                  # les classes avant occupent d'abord les sections avant
                    take = min(ent[1], rest_s)
                    if take > 0:
                        by_class[ent[0]] = take
                    ent[1] -= take
                    rest_s -= take
            rr = f" (R{cs['row_from']}–R{cs['row_to']})" if cs.get("row_from") and cs.get("row_to") else ""
            zones.append({"name": f"Cabine {s['id']}{rr}", "arm_m": round(ix["ref_m"] + ix["C_m"] * s["index_per_kg"], 4),
                          "max_pax": s["seats"], "status": status, **({"classes": by_class} if by_class else {}),
                          "source": srcfn(f"feuille {_sheet(t['saleable_configurations'])}, configuration {c['name']}")})
        cfgs.append({"nom": c["name"], "pnt": pnt, "pnc": pnc, "equipage_txt": None, "crew_kg": float(crew_kg), "crew_arm_m": None,
                     "dow_flotte_kg": W0, "dow_flotte_index": I0, "ajustements": adj, "zones": zones, "sieges": seats})
    rows = base_rows
    lim_default = {"zfw": wm["mzfw"], "law": wm["mlw"], "tow": wm["mtow"], "taxi": wm.get("mtaxi")}
    per = {}
    for k, v in ((t["limits"].get("per_registration")) or {}).items():
        per[k] = {"zfw": v["mzfw"], "law": v["mlw"], "tow": v["mtow"], "taxi": v.get("mtaxi")}
    for r_ in rows:
        per.setdefault(r_[0], lim_default)
    for c_ in cfgs:
        if not c_["zones"]:
            c_["zones"] = [{"name": "Aucun passager (avion cargo)", "arm_m": round(ix["ref_m"] + ix["C_m"] * (c_["dow_flotte_index"] - ix["K"]) / c_["dow_flotte_kg"], 4),
                            "max_pax": 0, "status": status, "source": srcfn("avion tout cargo : aucune cabine passagers (zone de capacité nulle)")}]
    d = cfgs[0]
    ac = {"type": info.get("label") or t.get("label") or "Type importé", "seats_typical": "",
          "fuel_density": (t.get("fuel") or {}).get("density_default_kg_per_l") or 0.8,
          "loading_mode": "vrac", "pax_zones": d["zones"], "cargo_comps": _comps(t, ix, f, status, srcfn),
          "cg_envelope": env["tow"], "cg_envelope_zfw": env["zfw"], "cg_envelope_tow": env["tow"], "fuel_arm_table": fuel,
          "lemac": round(ix["lemac_m"], 4), "mac_length": round(ix["mac_m"], 4),
          "max_zfw_kg": int(lim_default["zfw"]), "max_tow_kg": int(lim_default["tow"]), "max_lw_kg": int(lim_default["law"]),
          "mfuel": int(mfuel) if mfuel else None,
          "cg_min_m": round(min(p["fwd_m"] for p in env["tow"] + env["zfw"]), 4),
          "cg_max_m": round(max(p["aft_m"] for p in env["tow"] + env["zfw"]), 4),
          "crew_std_flight": pnt, "crew_std_cabin": pnc, "seats": d["sieges"],
          "max_seats": max(c["sieges"] for c in cfgs), "cg_limits_by_state": True}
    if "law" in env:
        ac["cg_envelope_law"] = env["law"]
    if ac["max_seats"] == 0:                       # avion tout cargo : plan de chargement par position de ULD
        U_ = _uld_rows(t.get("uld_positions"), ac["cargo_comps"], f)
        if U_:
            ac["uld"], ac["loading_mode"] = U_, "uld"
            rap.append(("info", f"Positions ULD lues dans l'AHM (feuille D3) : {len(U_['rows'])} positions. Les masses maximales sont celles "
                                "du fichier pour une position ; les limites cumulées (feuille 7.3) ne sont pas contrôlées."))
    if not ac["cargo_comps"]:
        rap.append(("attention", "Aucune soute en vrac exploitable : à saisir dans « Données aéronef »."))
    rap.append(("info", "Masse à vide injectée = masse de base de la feuille E5 + équipage (2 PNT et un PNC par tranche de 50 sièges, minimum réglementaire) ; offices, eau et pantry ne sont pas inclus : à ajuster."))
    if not ac.get("uld"):
        rap.append(("info", "Positions ULD non importées pour ce type : chargement en vrac par soute."))
    it = t.get("ideal_trim")
    if it and it.get("ideal_trim_line"):
        ac["ideal_trim"] = {"reference": it.get("ideal_trim_reference_remark") or "TOW",
                            "line": [{"weight_kg": p["weight_kg"], "pct_mac": p["pct_mac"], "fwd_pct_mac": p.get("fwd_pct_mac"),
                                      "aft_pct_mac": p.get("aft_pct_mac")} for p in it["ideal_trim_line"]],
                            "tipping": [{"name": x["name"], "condition": x.get("condition") or "",
                                         "points": [(p["weight_kg"], p["pct_mac"]) for p in x["points"]]}
                                        for x in (it.get("tipping_tables") or [])],
                            "source": srcfn("feuille C7, ligne de centrage idéale et limites de basculement")}
        if it.get("ideal_trim_reference_remark") == "ZFW":
            rap.append(("info", "La remarque de la feuille C7 cite le centrage à la masse sans carburant alors que le tableau est en masse au décollage : "
                                "la ligne est comparée au centrage au décollage."))
    else:
        rap.append(("info", "Pas de ligne de centrage idéale dans ce fichier : la répartition des bagages visera le milieu de l'enveloppe."))
    ac["ahm"] = {"source": {"fichier": info.get("fichier") or info.get("document"), "organisme": org, "edition": ed, "date": dt,
                            "type": ac["type"], "fabricant": None},
                 "unites_fichier": {"longueur": unit, "masse": "kg"}, "index": ix, "configs": cfgs,
                 "immatriculations": [{"reg": r_[0]} for r_ in rows], "limites_par_immat": per, "limites_defaut": lim_default,
                 "impression": {}, "impression_suppl": {}, "stab": None, "taxi_standard_kg": None, "masses": {}}
    std = t.get("standards") or {}
    pw, cw = std.get("pax_weights_kg") or {}, std.get("crew_weights_kg") or {}
    if pw or cw:
        ac["ahm"]["masses"] = {"pax": {"standard": {k: pw[k] for k in ("male", "female", "child", "infant") if k in pw}} if pw else {},
                               "equipage": {"pnt": cw.get("flight_deck"), "pnc": cw.get("cabin")} if cw else {}}
    ac["origine_import"] = {"mode": mode, "watermark": info.get("watermark")}
    return ac, rap
