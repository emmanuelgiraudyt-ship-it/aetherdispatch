# -*- coding: utf-8 -*-
"""
AETHERDISPATCH — répartition préliminaire des ULD dans les soutes (aéronefs chargés en ULD).

Module sans interface : il reçoit les positions de ULD du fichier AHM de la compagnie, les masses à charger
(bagages, fret, courrier), les tares et les contenus moyens par type de ULD, les limites de soute et de groupe,
puis les masses et moments du reste de l'avion (par état : ZFW, TOW, atterrissage) avec leurs limites de centrage.

Il renvoie le nombre réel de ULD et leur répartition, calculés dans cet ordre de priorité :
  1. toutes les limites sont respectées (masse brute de position, types admis, positions qui se recouvrent,
     masse de soute, masse de groupe de soutes, enveloppes de centrage) ;
  2. nombre minimal de ULD ;
  3. centrage au décollage aussi proche que possible d'une cible ;
  4. (à égalité) équilibre gauche / droite, à titre indicatif.

Aucune valeur propre à une compagnie n'est écrite dans ce module.
"""
import math

try:
    import pulp as _pulp
    PULP_OK = True
except Exception:                                              # PuLP absent : la fonction reste désactivée
    _pulp = None
    PULP_OK = False

NATURES = ("Bagages", "Fret", "Courrier")


def available() -> bool:
    return PULP_OK


def position_conflicts(rows: list) -> list:
    """Paires d'indices de positions qui se gênent : même soute, même côté et intervalles de bras qui se recouvrent."""
    out = []
    for i, a in enumerate(rows):
        for j in range(i + 1, len(rows)):
            b = rows[j]
            if a["hold"] != b["hold"] or not (set(a["sides"]) & set(b["sides"])):
                continue
            if min(a["to_m"], b["to_m"]) - max(a["from_m"], b["from_m"]) > 0.03:
                out.append((i, j))
    return out


def _side_sign(r: dict) -> int:
    s = set(r.get("sides") or [])
    if s == {"L"}:
        return -1
    if s == {"R"}:
        return 1
    return 0


def default_caps(rows: list, tare: dict) -> dict:
    """Contenu maximal par type de ULD, par la masse seule : plus grande masse brute de position, moins la tare."""
    caps = {}
    for r in rows:
        for t in (r.get("types") or []):
            caps[t] = max(caps.get(t, 0.0), float(r["max_kg"]) - float(tare.get(t, 0.0) or 0.0))
    return {t: max(v, 0.0) for t, v in caps.items()}


def theoretical_min(loads: dict, caps: dict) -> dict:
    """Nombre minimal de ULD par la masse seule : charge divisée par le plus grand contenu moyen admis, arrondie au-dessus."""
    best = {n: 0.0 for n in NATURES}
    for t, per in caps.items():
        for n in NATURES:
            best[n] = max(best[n], float(per.get(n, 0.0) or 0.0))
    out = {}
    for n in NATURES:
        l_ = float(loads.get(n, 0.0) or 0.0)
        out[n] = 0 if l_ <= 0 else (math.ceil(l_ / best[n] - 1e-9) if best[n] > 0 else None)
    return out


def _round_contents(items: list, loads: dict):
    """Arrondit les contenus au kilogramme en conservant exactement la masse de chaque nature."""
    for n in NATURES:
        grp = [it for it in items if it["nature"] == n]
        if not grp:
            continue
        target = int(round(float(loads.get(n, 0.0))))
        for it in grp:
            it["content"] = float(math.floor(it["content"] + 1e-9))
        rest = target - int(sum(it["content"] for it in grp))
        order = sorted(grp, key=lambda it: it["_frac"], reverse=True)
        k = 0
        while rest > 0 and order and k < 10 * len(order):
            it = order[k % len(order)]
            if it["content"] + 1 <= it["_ub"] + 1e-9:
                it["content"] += 1
                rest -= 1
            k += 1


def solve(rows: list, loads: dict, tare: dict, caps: dict, comps: dict, states: list, target: dict = None,
          extra_uld: int = 0, margin_m: float = 0.01, time_limit: int = 15) -> dict:
    """
    rows    : positions (id, label, hold, comp, kind, sides, max_kg, arm_m, from_m, to_m, types).
    loads   : {"Bagages": kg, "Fret": kg, "Courrier": kg} à placer dans les ULD.
    tare    : {type de ULD: tare en kg}.
    caps    : {type de ULD: {"Bagages": kg, "Fret": kg, "Courrier": kg}} contenu moyen maximal par ULD.
    comps   : {soute: {"max": kg, "groupe": nom ou None, "max_groupe": kg ou None}} (masses brutes, tare comprise).
    states  : [{"name", "m_other", "mom_other", "lim": fonction masse -> (avant, arrière) ou None}] ; m_other et mom_other
              sont la masse et le moment (kg et kg.m) de tout ce qui n'est pas chargé en ULD, pour cet état.
    target  : {"state": nom d'état, "arm_m": bras cible du centre de gravité (m)}.
    """
    res = {"ok": False, "status": "", "plan": [], "messages": [], "n_uld": {}, "n_total": 0, "cg": {}, "approx": False,
           "cg_relaxed": False, "theory": {}, "lateral_kg": 0.0}
    if not PULP_OK:
        res["status"] = "PuLP non installé"
        res["messages"].append("La bibliothèque PuLP n'est pas installée : la répartition automatique est indisponible.")
        return res
    loads = {n: max(float(loads.get(n, 0.0) or 0.0), 0.0) for n in NATURES}
    nats = [n for n in NATURES if loads[n] > 0]
    res["theory"] = theoretical_min(loads, caps)
    if not nats:
        res["ok"] = True
        res["status"] = "rien à charger"
        res["messages"].append("Aucune masse à placer dans les ULD.")
        return res
    all_types = sorted({t for r in rows for t in (r.get("types") or [])} | set(caps))

    # ── Variables ─────────────────────────────────────────────────────────
    P = _pulp
    combos = {}                                    # (p, type, nature) -> borne supérieure du contenu
    for p, r in enumerate(rows):
        for t in (r.get("types") or all_types):
            for n in nats:
                ub = min(float((caps.get(t) or {}).get(n, 0.0) or 0.0),
                         float(r["max_kg"]) - float(tare.get(t, 0.0) or 0.0))
                if ub > 0.5:
                    combos[(p, t, n)] = ub
    # types dominés : même position et même nature, contenu au plus égal et tare au moins égale
    for (p, t, n), ub in list(combos.items()):
        tt = float(tare.get(t, 0.0) or 0.0)
        for (p2, t2, n2), ub2 in combos.items():
            if p2 == p and n2 == n and t2 != t:
                tt2 = float(tare.get(t2, 0.0) or 0.0)
                if ub2 >= ub - 1e-9 and tt2 <= tt + 1e-9 and (ub2 > ub + 1e-9 or tt2 < tt - 1e-9 or t2 < t):
                    combos.pop((p, t, n), None)
                    break
    if not combos:
        res["status"] = "aucune position utilisable"
        res["messages"].append("Aucune position ne peut recevoir de contenu avec les contenus moyens et les tares saisis.")
        return res
    avail = {}
    for n in nats:
        best_by_p = {}
        for (p_, t_, n_), ub in combos.items():
            if n_ == n:
                best_by_p[p_] = max(best_by_p.get(p_, 0.0), ub)
        avail[n] = sum(best_by_p.values())
    short = [n for n in nats if loads[n] > avail[n] + 1e-6]
    conflicts = position_conflicts(rows)

    def build():
        prob = P.LpProblem("PlanULD", P.LpMinimize)
        y = {k: P.LpVariable(f"y_{i}", cat="Binary") for i, k in enumerate(combos)}
        c = {k: P.LpVariable(f"c_{i}", lowBound=0) for i, k in enumerate(combos)}
        used = {}
        for p in range(len(rows)):
            ks = [k for k in combos if k[0] == p]
            if ks:
                used[p] = P.LpVariable(f"u_{p}", cat="Binary")
                prob += P.lpSum(y[k] for k in ks) == used[p]
        for k, ub in combos.items():
            prob += c[k] <= ub * y[k]
        for n in nats:
            prob += P.lpSum(c[k] for k in combos if k[2] == n) == loads[n]
        for a, b in conflicts:
            if a in used and b in used:
                prob += used[a] + used[b] <= 1
        gross = {p: P.lpSum(c[k] + float(tare.get(k[1], 0.0) or 0.0) * y[k] for k in combos if k[0] == p) for p in used}
        by_comp, by_group = {}, {}
        for p, g in gross.items():
            by_comp.setdefault(rows[p]["comp"], []).append(g)
        for cn, gl in by_comp.items():
            cinfo = comps.get(cn) or {}
            if cinfo.get("max") is not None:
                prob += P.lpSum(gl) <= float(cinfo["max"])
            if cinfo.get("groupe") and cinfo.get("max_groupe") is not None:
                by_group.setdefault((cinfo["groupe"], float(cinfo["max_groupe"])), []).extend(gl)
        for (_, mx), gl in by_group.items():
            prob += P.lpSum(gl) <= mx
        return prob, y, c, used, gross

    def st_expr(gross, s):
        mass = s["m_other"] + P.lpSum(gross.values())
        mom = s["mom_other"] + P.lpSum(g * rows[p]["arm_m"] for p, g in gross.items())
        return mass, mom

    est_tare = 0.0
    for n in nats:
        mc_ = max([float((caps.get(t) or {}).get(n, 0.0) or 0.0) for t in all_types] or [0.0])
        tmax = max([float(tare.get(t, 0.0) or 0.0) for t in all_types] or [0.0])
        if mc_ > 0:
            est_tare += math.ceil(loads[n] / mc_) * tmax
    tot_load = sum(loads.values())

    def limits_at(extra_mass_by_state):
        out = {}
        for s in states:
            if s.get("lim") is None:
                continue
            lim = s["lim"](s["m_other"] + extra_mass_by_state)
            if lim is not None:
                out[s["name"]] = (lim[0] + margin_m, lim[1] - margin_m)
        return out

    def solve_once(lims, hard_cg=True):
        prob, y, c, used, gross = build()
        if hard_cg:
            for s in states:
                if s["name"] in lims:
                    mass, mom = st_expr(gross, s)
                    fw, af = lims[s["name"]]
                    prob += mom >= fw * mass
                    prob += mom <= af * mass
        eps = 1e-4
        count = P.lpSum(used.values())
        order_pen = P.lpSum(eps * (p + 1) / len(rows) * used[p] for p in used)
        lb = sum(v for v in res["theory"].values() if v)
        if lb:
            prob += count >= lb                       # borne inférieure : une seule nature par ULD
        mref = max(sum(s_["m_other"] for s_ in states[:1]) + tot_load + est_tare, 1.0)
        solver1 = P.PULP_CBC_CMD(msg=0, timeLimit=time_limit, gapAbs=0.002, threads=2)
        solver2 = P.PULP_CBC_CMD(msg=0, timeLimit=time_limit, gapAbs=0.003 * mref, threads=2)
        solver3 = P.PULP_CBC_CMD(msg=0, timeLimit=max(int(time_limit * 0.5), 3), gapAbs=0.003 * mref, threads=2)
        solver = solver1
        prob.setObjective(count + order_pen)
        prob.solve(solver)
        if P.LpStatus[prob.status] != "Optimal":
            return None
        approx = prob.sol_status != 1
        n_opt = round(sum(v.value() or 0 for v in used.values()))
        # étape 2 : centrage cible
        dev_opt = None
        if target:
            ts = next((s for s in states if s["name"] == target["state"]), None)
            if ts is not None:
                prob += count <= n_opt + max(int(extra_uld), 0)
                mass, mom = st_expr(gross, ts)
                dv = P.LpVariable("dev", lowBound=0)
                dd = mom - target["arm_m"] * mass
                prob += dv >= dd
                prob += dv >= -dd
                prob.setObjective(dv + order_pen)
                prob.solve(solver2)
                if P.LpStatus[prob.status] != "Optimal":
                    return None
                approx = approx or prob.sol_status != 1
                dev_opt = dv.value() or 0.0
                tol = 0.002 * max(ts["m_other"] + tot_load + est_tare, 1.0)
                # étape 3 : équilibre gauche / droite à centrage et nombre de ULD inchangés
                prob += dv <= dev_opt + tol
                lat = P.LpVariable("lat", lowBound=0)
                lexp = P.lpSum(g * _side_sign(rows[p]) for p, g in gross.items())
                prob += lat >= lexp
                prob += lat >= -lexp
                prob.setObjective(lat + order_pen)
                prob.solve(solver3)
                if P.LpStatus[prob.status] != "Optimal":
                    return None
                approx = approx or prob.sol_status != 1
        sol = []
        for k in combos:
            if (y[k].value() or 0) > 0.5:
                sol.append({"p": k[0], "uld": k[1], "nature": k[2], "content": float(c[k].value() or 0.0),
                            "_ub": combos[k]})
        return sol, approx, dev_opt

    # ── Résolution : 1. capacité seule, 2. avec centrage, 3. centrage assoupli ─
    if short:
        res["status"] = "capacité insuffisante"
        res["messages"].append("Capacité insuffisante pour : " + ", ".join(
            f"{n} ({loads[n]:,.0f} kg à charger pour {avail[n]:,.0f} kg disponibles avec les contenus moyens saisis)"
            for n in short) + ". Augmentez le contenu moyen par ULD, réduisez la charge ou prévoyez du vrac.")
        return res
    lims = limits_at(est_tare + tot_load)
    out = solve_once(lims, hard_cg=True)
    if out is not None:
        for _ in range(1):                                   # les limites dépendent de la masse : une seconde passe
            tare_real = sum(float(tare.get(it["uld"], 0.0) or 0.0) for it in out[0])
            lims2 = limits_at(tare_real + tot_load)
            if any(abs(lims2[k][0] - lims[k][0]) > 0.003 or abs(lims2[k][1] - lims[k][1]) > 0.003 for k in lims2):
                lims = lims2
                out2 = solve_once(lims, hard_cg=True)
                if out2 is not None:
                    out = out2
    if out is None:
        out = solve_once(lims, hard_cg=False)
        res["cg_relaxed"] = True
        if out is None:
            res["status"] = "aucune répartition possible"
            res["messages"].append("Aucune répartition ne respecte les masses de position, de soute et de groupe avec les valeurs "
                                   "saisies. Vérifiez les tares, les contenus moyens et la charge à placer.")
            return res
        res["messages"].append("Aucune répartition ne place le centrage dans l'enveloppe avec ces masses : la proposition "
                               "est la plus proche de la cible, mais elle est hors limites. Voir les centrages ci-dessous.")
    sol, approx, dev_opt = out
    res["approx"] = bool(approx)
    items = []
    for it in sol:
        it = dict(it)
        it["_frac"] = it["content"] - math.floor(it["content"] + 1e-9)
        items.append(it)
    _round_contents(items, loads)
    plan = []
    for it in sorted(items, key=lambda i: i["p"]):
        r = rows[it["p"]]
        tr = float(tare.get(it["uld"], 0.0) or 0.0)
        g = it["content"] + tr
        plan.append({"pos": r["label"], "hold": r["hold"], "comp": r["comp"], "uld": it["uld"], "nature": it["nature"],
                     "content": it["content"], "tare": tr, "gross": g, "arm": r["arm_m"], "max": float(r["max_kg"]),
                     "row": it["p"]})
    res["plan"] = plan
    res["n_total"] = len(plan)
    for n in NATURES:
        res["n_uld"][n] = sum(1 for x in plan if x["nature"] == n)
    gsum = sum(x["gross"] for x in plan)
    res["lateral_kg"] = sum(x["gross"] * _side_sign(rows[x["row"]]) for x in plan)
    for s in states:
        mass = s["m_other"] + gsum
        mom = s["mom_other"] + sum(x["gross"] * x["arm"] for x in plan)
        cg = mom / mass if mass > 0 else 0.0
        lim = s["lim"](mass) if s.get("lim") else None
        res["cg"][s["name"]] = {"mass": mass, "cg": cg, "lim": lim,
                                "ok": True if lim is None else (lim[0] - 1e-6 <= cg <= lim[1] + 1e-6)}
    res["ok"] = all(v["ok"] for v in res["cg"].values()) and not res["cg_relaxed"]
    res["status"] = "optimale" if not approx else "approchée (limite de temps atteinte)"
    if approx:
        res["messages"].append("Le calcul a atteint sa limite de temps : la répartition respecte toutes les limites, mais le "
                               "nombre de ULD ou le centrage peut ne pas être optimal.")
    return res


# ═════════════════════════════════════════════════════════════════════════════
# Aéronefs à soutes en vrac : répartition des bagages, du fret et du courrier entre les soutes
# ═════════════════════════════════════════════════════════════════════════════
def solve_bulk(comps: list, loads: dict, states: list, target: dict = None, bag_unit: float = None,
               margin_m: float = 0.01, time_limit: int = 15) -> dict:
    """
    comps   : soutes en vrac [{"name", "arm_m", "max_kg", "groupe", "max_groupe_kg", "bag_rank", "fixed_kg"}] ;
              fixed_kg est la masse déjà imposée dans la soute (déduite de sa capacité).
    loads   : {"Bagages": kg, "Fret": kg, "Courrier": kg} à répartir.
    bag_unit: masse forfaitaire d'un bagage (kg) : les bagages sont alors répartis en nombre entier de pièces.
    states  : comme pour solve() ; target : {"state", "arm_m"}.
    Ordre de priorité : limites de soute, de groupe et de centrage ; puis centrage proche de la cible ; puis, à centrage
    équivalent, priorité de chargement des bagages de la compagnie (bag_rank).
    """
    res = {"ok": False, "status": "", "plan": [], "messages": [], "cg": {}, "cg_relaxed": False, "pieces": None}
    if not PULP_OK:
        res["status"] = "PuLP non installé"
        res["messages"].append("La bibliothèque PuLP n'est pas installée : la répartition automatique est indisponible.")
        return res
    if not comps:
        res["status"] = "aucune soute"
        res["messages"].append("Aucune soute en vrac n'est définie pour ce type.")
        return res
    P = _pulp
    loads = {n: max(float(loads.get(n, 0.0) or 0.0), 0.0) for n in NATURES}
    unit = float(bag_unit) if bag_unit and bag_unit > 0 else None
    pieces = int(round(loads["Bagages"] / unit)) if unit else None
    if unit:
        loads["Bagages"] = pieces * unit
    tot = sum(loads.values())
    if tot <= 0:
        res["ok"], res["status"] = True, "rien à charger"
        res["messages"].append("Aucune masse à répartir.")
        return res
    free = {c["name"]: max(float(c["max_kg"]) - float(c.get("fixed_kg") or 0.0), 0.0) for c in comps}
    if sum(free.values()) + 1e-6 < tot:
        res["status"] = "capacité insuffisante"
        res["messages"].append(f"Capacité insuffisante : {tot:,.0f} kg à répartir pour {sum(free.values()):,.0f} kg disponibles "
                               "dans les soutes en vrac.")
        return res
    fixed_m = {c["name"]: float(c.get("fixed_kg") or 0.0) for c in comps}
    arm = {c["name"]: float(c["arm_m"]) for c in comps}
    rank_max = max([c["bag_rank"] for c in comps if c.get("bag_rank") is not None] or [0]) + 1

    def build(hard_cg, lims):
        prob = P.LpProblem("PlanVrac", P.LpMinimize)
        x = {}
        for c in comps:
            for n in NATURES:
                if loads[n] > 0:
                    if n == "Bagages" and unit:
                        x[(c["name"], n)] = P.LpVariable(f"x_{len(x)}", lowBound=0, upBound=pieces, cat="Integer")
                    else:
                        x[(c["name"], n)] = P.LpVariable(f"x_{len(x)}", lowBound=0)

        def kg(k):
            return x[k] * (unit if (k[1] == "Bagages" and unit) else 1.0)
        for n in NATURES:
            if loads[n] > 0:
                if n == "Bagages" and unit:
                    prob += P.lpSum(x[(c["name"], n)] for c in comps) == pieces
                else:
                    prob += P.lpSum(x[(c["name"], n)] for c in comps) == loads[n]
        hold_kg = {c["name"]: P.lpSum(kg((c["name"], n)) for n in NATURES if loads[n] > 0) for c in comps}
        for c in comps:
            prob += hold_kg[c["name"]] <= free[c["name"]]
        groups = {}
        for c in comps:
            if c.get("groupe") and c.get("max_groupe_kg") is not None:
                groups.setdefault((c["groupe"], float(c["max_groupe_kg"])), []).append(c["name"])
        for (_, mx), names in groups.items():
            prob += P.lpSum(hold_kg[nm] + fixed_m[nm] for nm in names) <= mx
        gross = {nm: hold_kg[nm] for nm in hold_kg}
        if hard_cg:
            for s in states:
                if s["name"] in lims:
                    mass = s["m_other"] + P.lpSum(gross.values())
                    mom = s["mom_other"] + P.lpSum(g * arm[nm] for nm, g in gross.items())
                    fw, af = lims[s["name"]]
                    prob += mom >= fw * mass
                    prob += mom <= af * mass
        return prob, x, kg, gross

    def limits_at(extra):
        out = {}
        for s in states:
            if s.get("lim") is None:
                continue
            lim = s["lim"](s["m_other"] + extra)
            if lim is not None:
                out[s["name"]] = (lim[0] + margin_m, lim[1] - margin_m)
        return out

    def run(hard_cg, lims):
        prob, x, kg, gross = build(hard_cg, lims)
        solver = P.PULP_CBC_CMD(msg=0, timeLimit=time_limit, threads=2)
        ts = next((s for s in states if target and s["name"] == target["state"]), None)
        pen = P.lpSum(((c["bag_rank"] if c.get("bag_rank") is not None else rank_max) + 1) * kg((c["name"], "Bagages"))
                      for c in comps if ("%s" % c["name"], "Bagages") in x)
        scale = 1.0 / max(tot * (rank_max + 1), 1.0)
        if ts is not None:
            mass = ts["m_other"] + P.lpSum(gross.values())
            mom = ts["mom_other"] + P.lpSum(g * arm[nm] for nm, g in gross.items())
            dv = P.LpVariable("dev", lowBound=0)
            dd = mom - target["arm_m"] * mass
            prob += dv >= dd
            prob += dv >= -dd
            prob.setObjective(dv)
            prob.solve(solver)
            if P.LpStatus[prob.status] != "Optimal":
                return None
            dev = dv.value() or 0.0
            prob += dv <= dev + 0.002 * max(ts["m_other"] + tot, 1.0)
        # à égalité : peu de répartitions fractionnées (une nature n'est répartie que dans les soutes utiles)
        z = {}
        for k, v in x.items():
            ub = pieces if (k[1] == "Bagages" and unit) else min(loads[k[1]], free[k[0]])
            z[k] = P.LpVariable(f"z_{len(z)}", cat="Binary")
            prob += v <= max(ub, 0.0) * z[k]
        prob.setObjective(pen * scale + 0.02 * P.lpSum(z.values()) / max(len(z), 1))
        prob.solve(solver)
        if P.LpStatus[prob.status] != "Optimal":
            return None
        return {k: (v.value() or 0.0) for k, v in x.items()}

    lims = limits_at(tot)
    sol = run(True, lims)
    if sol is None:
        sol = run(False, lims)
        res["cg_relaxed"] = True
        if sol is None:
            res["status"] = "aucune répartition possible"
            res["messages"].append("Aucune répartition ne respecte les limites de soute et de groupe.")
            return res
        res["messages"].append("Aucune répartition ne place le centrage dans l'enveloppe avec ces masses : la proposition est "
                               "la plus proche de la cible, mais elle est hors limites. Voir les centrages ci-dessous.")
    # arrondi : bagages en pièces entières, autres natures au kilogramme près (masses totales conservées)
    kgs = {}
    for (nm, n), v in sol.items():
        kgs[(nm, n)] = v * (unit if (n == "Bagages" and unit) else 1.0)
    for n in NATURES:
        if loads[n] <= 0:
            continue
        keys = [k for k in kgs if k[1] == n]
        if n == "Bagages" and unit:
            for k in keys:
                kgs[k] = round(sol[k]) * unit
            continue
        fl = {k: math.floor(kgs[k] + 1e-9) for k in keys}
        rest = int(round(loads[n])) - sum(fl.values())
        for k in sorted(keys, key=lambda k: kgs[k] - fl[k], reverse=True):
            if rest <= 0:
                break
            if fl[k] + 1 <= free[k[0]] + 1e-9:
                fl[k] += 1
                rest -= 1
        for k in keys:
            kgs[k] = float(fl[k])
    plan = []
    for c in comps:
        nm = c["name"]
        row = {"comp": nm, "arm": arm[nm], "max": float(c["max_kg"]), "fixed": fixed_m[nm]}
        for n in NATURES:
            row[n] = float(kgs.get((nm, n), 0.0))
        row["total"] = sum(row[n] for n in NATURES)
        row["pieces"] = int(round(row["Bagages"] / unit)) if unit else None
        plan.append(row)
    res["plan"] = plan
    res["pieces"] = pieces
    gsum = sum(r["total"] for r in plan)
    for s in states:
        mass = s["m_other"] + gsum
        mom = s["mom_other"] + sum(r["total"] * r["arm"] for r in plan)
        cg = mom / mass if mass > 0 else 0.0
        lim = s["lim"](mass) if s.get("lim") else None
        res["cg"][s["name"]] = {"mass": mass, "cg": cg, "lim": lim,
                                "ok": True if lim is None else (lim[0] - 1e-6 <= cg <= lim[1] + 1e-6)}
    res["ok"] = all(v["ok"] for v in res["cg"].values()) and not res["cg_relaxed"]
    res["status"] = "optimale"
    return res
