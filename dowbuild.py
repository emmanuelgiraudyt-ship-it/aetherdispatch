"""Construction de la masse/index à vide d'exploitation (DOW/DOI) à partir de l'AHM 565 :
   DOW = base (eau pleine) + équipage de conduite + équipage de cabine + pantry + ajustement d'eau potable.
   Toutes les valeurs viennent de l'AHM (feuilles « Dry Operating Weight Build-Up » et « Cabin and Crew Locations »)."""
import re
import ahm_text as T


def _grp(s, group):
    rg = T.regs_list(s['regs'])
    return 'ALL' in rg or group in rg


def _num_tokens(l):
    out = []
    for t in l.split():
        if re.fullmatch(r'-?\d+(?:\.\d+)?(?:[eE]-?\d+)?', t):
            out.append(float(t))
    return out


def x_pantry(sheets, group):
    """{code: {'kg': total, 'index': indice, 'remark': str}}"""
    res = {}
    for s in sheets:
        if 'Crew and Pantry Codes' not in s['title'] or not _grp(s, group):
            continue
        on, lines = False, s['txt'].split('\n')
        for l in lines:
            if re.match(r'\s*2\.3\s+Pantry', l):
                on = True
                continue
            if not on:
                continue
            if re.match(r'\s*Remarks', l):
                break
            tk = l.split()
            if len(tk) < 3 or not re.fullmatch(r'[A-Z0-9]{1,3}', tk[0]):
                continue
            ints, flt = [], []
            for t in tk[1:]:
                if re.fullmatch(r'\d+', t):
                    ints.append(int(t))
                elif t == '-':
                    continue
                elif re.fullmatch(r'-?\d+(?:\.\d+)?(?:[eE]-?\d+)?', t):
                    flt.append(float(t))
                else:
                    break
            tot = None
            for i in range(1, len(ints)):
                if sum(ints[:i]) == ints[i]:
                    tot = ints[i]
                    break
            if tot is None and len(ints) == 1:
                tot = ints[0]
            if tot is None:
                continue
            nums = _num_tokens(l.split(tk[0], 1)[1])
            idx = nums[-1] if len(nums) >= 2 else None
            res[tk[0]] = {'kg': float(tot), 'index': idx, 'remark': ' '.join(t for t in tk[1:] if not re.fullmatch(r'-?\d+(?:\.\d+)?|-', t))}
    return res


def _water_sheet_tables(sheets):
    """[(liste d'immatriculations de la feuille, {pourcentage: (kg, index)})] pour chaque feuille d'eau potable."""
    out = []
    for s in sheets:
        if 'Potable Water' not in s['title']:
            continue
        res = {}
        for l in s['txt'].split('\n'):
            m = re.match(r'\s*(\d+(?:/\d+)?)(%?)\s+(?:PTBLE|PW|Potable)', l)
            if not m:
                continue
            lab = m.group(1)
            pc = 100.0 * int(lab.split('/')[0]) / int(lab.split('/')[1]) if '/' in lab else float(lab)
            nums = []
            for t in l.split()[1:]:
                if '%' in t or '/' in t:
                    continue
                if re.fullmatch(r'-?\d+(?:\.\d+)?(?:[eE]-?\d+)?', t):
                    nums.append(float(t))
            if not nums:
                continue
            res[round(pc, 1)] = (nums[0], nums[-1] if len(nums) >= 2 else None)
        if res:
            if 100.0 not in res:
                res[100.0] = (0.0, 0.0)
            out.append((T.regs_list(s['regs']), res))
    return out


def x_water(sheets, group):
    """Table d'ajustement d'eau potable d'un groupe : {'table': {...} ou None, 'variants': {sous-groupe: table}, 'issues': [...]}.
    group peut être une liste « 350A, 350B » : si ses sous-groupes relèvent de tables différentes, la table n'est pas choisie
    (ambiguïté) ; si aucune feuille ne cite le groupe mais qu'une immatriculation en diffère d'un caractère, c'est signalé."""
    toks = [t.strip() for t in group.split(',') if t.strip()]
    tabs = _water_sheet_tables(sheets)
    variants, issues, needs_confirm = {}, [], False
    for tk in toks:
        hit = [t for rg, t in tabs if 'ALL' in rg or tk in rg]
        if hit:
            variants[tk] = hit[0]
        else:
            allr = [r for rg, _ in tabs for r in rg if r != 'ALL']
            near = [r for r in allr if len(r) == len(tk) - 1 and any(tk[:i] + tk[i + 1:] == r for i in range(len(tk)))]
            issues.append(f"Eau potable : aucune feuille ne cite le groupe « {tk} »" +
                          (f" (immatriculation voisine « {near[0]} » : faute de frappe probable dans l'AHM, à confirmer)" if near else "") + ".")
            if near:
                cand = [t for rg, t in tabs if near[0] in rg]
                if cand:
                    variants[f"{tk} (feuille « {near[0]} »)"] = cand[0]
                    needs_confirm = True
    distinct = []
    for v in variants.values():
        if v not in distinct:
            distinct.append(v)
    table = distinct[0] if len(distinct) == 1 and not needs_confirm else None
    if len(distinct) > 1:
        issues.append("Eau potable : les sous-groupes " + ", ".join(variants) + " relèvent de tables d'ajustement différentes ; "
                      "l'AHM ne dit pas à quel sous-groupe appartient chaque avion : choix à confirmer.")
    return {'table': table, 'variants': variants, 'issues': issues}


def x_crew_table(sheets, group):
    """Tables « Crew Location / Weight / Index » de la feuille « Cabin and Crew Locations » :
       {'cockpit': {n: (kg, idx)}, 'cabin': {n: (kg, idx)}} (selon le libellé « N COCKPIT CREW » / « N CABIN CREW »)."""
    out = {'cockpit': {}, 'cabin': {}}
    for s in sheets:
        if 'Cabin and Crew Locations' not in s['title'] or not _grp(s, group):
            continue
        lines = [l.replace('İ', 'I').replace('ı', 'i') for l in s['txt'].split('\n')]
        for i, l in enumerate(lines):
            m = re.match(r'\s*(\d+)\s+(COCKPIT\s+CREW|CABIN\s+CREW|LOADMASTER)\s+(\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)', l, re.I)
            if not m:                                    # PDF : masse et index sur la ligne suivante
                m0 = re.match(r'\s*(\d+)\s+(COCKPIT\s+CREW|CABIN\s+CREW|LOADMASTER)\s*$', l, re.I)
                m1 = re.match(r'\s*(\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*$', lines[i + 1]) if m0 and i + 1 < len(lines) else None
                if m0 and m1:
                    class _M:
                        def group(self, k, a=m0, b=m1):
                            return {1: a.group(1), 2: a.group(2), 3: b.group(1), 4: b.group(2)}[k]
                    m = _M()
            if m:
                out['cockpit' if m.group(2).upper().startswith('COCKPIT') else 'cabin'][int(m.group(1))] = (float(m.group(3)), float(m.group(4).replace('+', '')))
        if out['cockpit'] or out['cabin']:
            return out
    return out


def x_crew_codes(sheets, group):
    """Codes équipage « 2/4 » : (conduite, cabine)."""
    codes = []
    for s in sheets:
        if 'Crew and Pantry Codes' not in s['title'] or not _grp(s, group):
            continue
        for l in s['txt'].split('\n'):
            m = re.match(r'\s*(\d+)/(\d+)\s+(\d+)\s+(\d+)\b', l)
            if m and int(m.group(1)) == int(m.group(3)) and int(m.group(2)) == int(m.group(4)):
                codes.append((int(m.group(1)), int(m.group(2))))
        if codes:
            return sorted(set(codes))
    return codes


def build(sheets, group):
    """Éléments de construction du DOW/DOI pour un groupe d'immatriculations (libellé complet du groupe)."""
    g0 = group.split(',')[0].strip()
    B = T.x_basic(sheets, g0)
    W = x_water(sheets, group)
    return {'basic': {a['reg']: {'kg': a['basic_weight_kg'], 'index': a.get('index'), 'arm': a.get('arm'), 'pct_mac': a.get('pct_mac')}
                      for a in (B['aircraft'] if B else [])},
            'pantry': x_pantry(sheets, g0), 'water': W['table'] or {}, 'water_variants': W['variants'], 'issues': W['issues'],
            'crew_table': x_crew_table(sheets, g0), 'crew_codes': x_crew_codes(sheets, g0)}


def compute(bd, reg, crew, pantry, water_pct):
    """(DOW, DOI) ou None si un élément manque. crew = (n_conduite, n_cabine)."""
    b = bd['basic'].get(reg)
    if b is None or b['index'] is None:
        return None
    p = bd['pantry'].get(pantry)
    w = bd['water'].get(water_pct)
    ck = bd['crew_table']['cockpit'].get(crew[0])
    cb = bd['crew_table']['cabin'].get(crew[1]) if crew[1] else (0.0, 0.0)
    if None in (p, w, ck, cb) or p['index'] is None or w[1] is None:
        return None
    return (b['kg'] + ck[0] + cb[0] + p['kg'] + w[0], b['index'] + ck[1] + cb[1] + p['index'] + w[1])


def to_record(bd):
    """Forme JSON (clés de dictionnaire en texte) de la construction du DOW/DOI."""
    return {'basic': bd['basic'],
            'pantry': bd['pantry'],
            'water': {str(k): list(v) for k, v in bd['water'].items()},
            'water_variants': {g: {str(k): list(v) for k, v in t.items()} for g, t in bd['water_variants'].items()},
            'issues': bd['issues'],
            'crew_table': {k: {str(n): list(v) for n, v in d.items()} for k, d in bd['crew_table'].items()},
            'crew_codes': [list(c) for c in bd['crew_codes']]}


def from_record(r):
    return {'basic': r['basic'], 'pantry': r['pantry'],
            'water': {float(k): tuple(v) for k, v in (r.get('water') or {}).items()},
            'water_variants': {g: {float(k): tuple(v) for k, v in t.items()} for g, t in (r.get('water_variants') or {}).items()},
            'issues': r.get('issues') or [],
            'crew_table': {k: {int(n): tuple(v) for n, v in d.items()} for k, d in r['crew_table'].items()},
            'crew_codes': [tuple(c) for c in r.get('crew_codes') or []]}
