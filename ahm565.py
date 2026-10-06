# -*- coding: utf-8 -*-
"""Lecture d'un fichier AHM 565 (formulaire IATA de données semi-permanentes EDP) au format PDF.

Le module lit le texte du PDF par coordonnées. Il ne contient AUCUNE valeur de compagnie :
tout ce qui est renvoyé provient du fichier lu. Ce qui est absent ou illisible reste à None
et est signalé dans la liste « avertissements ».
"""
import re

try:
    import pymupdf as _pm
except Exception:                                  # pragma: no cover
    try:
        import fitz as _pm
    except Exception:
        _pm = None

# ---------------------------------------------------------------------------
# Utilitaires de lecture
# ---------------------------------------------------------------------------
NUM_RE = re.compile(r'^[+\-]?\d+(?:[.,]\d+)?$')


def num(s):
    """Nombre à virgule décimale française ou point ; None si ce n'est pas un nombre."""
    if s is None:
        return None
    s = str(s).strip().replace('−', '-')
    if not NUM_RE.match(s):
        return None
    return float(s.replace(',', '.'))


def page_lines(page, ytol=2.5):
    """Lignes de la page : liste de (y, [(x0, x1, texte), ...]) triées de haut en bas, puis de gauche à droite."""
    ws = page.get_text("words")
    ws = sorted(ws, key=lambda w: (w[1] + w[3]) / 2)
    lines = []
    for w in ws:
        yc = (w[1] + w[3]) / 2
        if lines and abs(lines[-1][0] - yc) <= ytol:
            lines[-1][1].append(w)
        else:
            lines.append([yc, [w]])
    out = []
    for yc, l in lines:
        l.sort(key=lambda w: w[0])
        out.append((yc, [(w[0], w[2], w[4]) for w in l]))
    return out


def ltext(line):
    return ' '.join(t for _, _, t in line[1])


MARKERS = [
    ('units_ac',    r'Definitions of Aircraft Units of Measure'),
    ('ident',       r'AIRCRAFT TYPE OR FLEET'),
    ('balance_out', r'BALANCE AND SPECIAL INFORMATION'),
    ('index',       r'BASIC INDEX AND MAC'),
    ('cg',          r'CENTRE OF GRAVITY CHARTS'),
    ('fuel_cum',    r'Effect of Fuel\s*-\s*Cumulative'),
    ('fuel_dist',   r'Fuel Distribution\b.*Supply fueling|5\.3\s+Fuel Distribution'),
    ('fuel_tank',   r'Tank Names'),
    ('stab',        r'STABILI[SZ]ER TRIM'),
    ('regid',       r'AIRCRAFT IDENTIFICATION'),
    ('holds',       r'HOLDS AND COMPARTMENTS'),
    ('uldpos',      r'UNIT LOAD DEVICE \(ULD\) CONFIGURATIONS'),
    ('cabin',       r'Cabin Definitions'),
    ('seatplan',    r'6\.2\s+Seat Plan'),
    ('salecfg',     r'Saleable Configuration:'),
    ('regweights',  r'Aircraft Registration Weights'),
    ('limits',      r'Maximum Weights Tables'),
    ('minlimits',   r'Minimum Weights Tables'),
    ('uldcompat',   r'ULD COMPATIBILITY'),
    ('crew',        r'Crew weights'),
    ('pax',         r'Standard / Default Passenger'),
    ('bag',         r'Checked baggage weight'),
    ('uldspec',     r'ULD Specifications'),
    ('dow_spec',    r'Dry Operating Weight Specification'),
    ('crewcodes',   r'Crew Codes'),
    ('cover',       r'Issue Number'),
    ('autodocs',    r'AUTOMATICALLY PRODUCED DOCUMENTS'),
]


class Doc:
    def __init__(self, data: bytes = None, path: str = None):
        if _pm is None:
            raise RuntimeError("pymupdf n'est pas installé")
        self.pdf = _pm.open(path) if path else _pm.open(stream=data, filetype='pdf')
        self.n = len(self.pdf)
        self.warn = []
        self.pages = {}
        self._lines = {}
        self._text = {}
        for i in range(self.n):
            t = self.pdf[i].get_text()
            self._text[i] = t
            flat = re.sub(r'\s+', ' ', t)
            for key, pat in MARKERS:
                if re.search(pat, flat, re.I if key not in ('cabin',) else 0):
                    self.pages.setdefault(key, []).append(i)

    def lines(self, i):
        if i not in self._lines:
            self._lines[i] = page_lines(self.pdf[i])
        return self._lines[i]

    def text(self, i):
        return self._text[i]

    def w(self, msg):
        if msg not in self.warn:
            self.warn.append(msg)


# ---------------------------------------------------------------------------
# Cases à cocher : un « X » est rattaché à l'étiquette la plus proche à sa droite
# ---------------------------------------------------------------------------
def tick_labels(line, max_dx=40):
    """Dans une ligne, renvoie la liste des étiquettes cochées (texte de l'étiquette suivant chaque X isolé)."""
    out = []
    toks = line[1]
    for k, (x0, x1, t) in enumerate(toks):
        if t in ('X', 'x') and k + 1 < len(toks):
            nx0, _, nt = toks[k + 1]
            if nx0 - x1 <= max_dx:
                out.append((nx0, nt))
    return out


# ---------------------------------------------------------------------------
# Unités de mesure de l'avion (feuille C1)
# ---------------------------------------------------------------------------
def parse_units(doc: Doc):
    res = {"weight": None, "length": None, "liquid": None, "volume": None, "density": None, "moment": None}
    pgs = doc.pages.get('units_ac', [])
    if not pgs:
        doc.w("Unités de l'avion (feuille C1) introuvables")
        return res
    ls = doc.lines(pgs[0])
    prev_len_labels = None
    for ln in ls:
        txt = ltext(ln)
        ticks = tick_labels(ln)
        toks = [t for _, _, t in ln[1]]
        if txt.startswith('Weight') and ticks:
            res['weight'] = 'kg' if ticks[0][1].lower().startswith('kilo') else 'lb'
        elif 'Cubic' in txt and ticks:
            res['volume'] = 'm3' if ticks[0][0] < 300 else 'ft3'
        elif 'Liquid' in txt and ticks:
            res['liquid'] = 'l' if ticks[0][1].lower().startswith('litre') else 'gal'
        elif ticks and re.search(r'KG\s*/\s*Litre', txt):
            res['density'] = 'kg/l'
        elif ticks and re.search(r'KG\s*/\s*US', txt):
            res['density'] = 'kg/gal'
        elif ticks and re.search(r'KG\s+Inches|LB\s+Inches', txt):
            res['moment'] = 'kg.in' if ticks[0][1] == 'KG' else 'lb.in'
        elif ticks and re.search(r'KG\s+Centimeters', txt):
            res['moment'] = 'kg.cm' if ticks[0][1] == 'KG' else 'lb.cm'
        elif ticks and re.search(r'KG\s+Metres', txt):
            res['moment'] = 'kg.m' if ticks[0][1] == 'KG' else 'lb.m'
        elif ticks and 'Metres' in txt and 'Feet' in txt:
            res['length'] = 'm' if ticks[0][1].lower().startswith('metre') else 'ft'
        elif ticks and 'Centimeters' in txt and 'Inches' in txt:
            res['length'] = 'cm' if ticks[0][1].lower().startswith('cent') else 'in'
    # Les lignes « Length » : la case cochée est sur la ligne Metres/Feet ou Centimeters/Inches
    return res


# ---------------------------------------------------------------------------
# Identification, index, limites de masse
# ---------------------------------------------------------------------------
def _after_label(line, label_words, xmax=340):
    """Texte situé après une étiquette (suite de mots) dans une ligne, à gauche de xmax."""
    toks = line[1]
    words = [t for _, _, t in toks]
    n = len(label_words)
    for i in range(len(words) - n + 1):
        if [w.lower() for w in words[i:i + n]] == [w.lower() for w in label_words]:
            rest = [t for x0, _, t in toks[i + n:] if x0 < xmax]
            return ' '.join(rest).strip() or None
    return None


def parse_ident(doc: Doc):
    res = {"fabricant": None, "type_oaci": None, "sous_type": None, "nom": None, "registrations": []}
    for p in doc.pages.get('ident', [])[:1]:
        for ln in doc.lines(p):
            v = _after_label(ln, ['Manufacturer:'])
            if v: res['fabricant'] = v
            v = _after_label(ln, ['Aircraft', 'type:'])
            if v: res['type_oaci'] = v
            v = _after_label(ln, ['Series', 'or', 'subtype:'])
            if v: res['sous_type'] = v
            v = _after_label(ln, ['Aircraft', 'Name:'])
            if v: res['nom'] = v
    REG = re.compile(r'^[A-Z0-9]{1,2}-[A-Z0-9]{2,5}$')
    for p in doc.pages.get('regid', [])[:2]:
        for ln in doc.lines(p):
            toks = [t for _, _, t in ln[1]]
            if toks and REG.match(toks[0]):
                res['registrations'].append({"reg": toks[0], "msn": toks[1] if len(toks) > 1 else None,
                                             "nom": ' '.join(toks[2:]) or None})
    if not res['type_oaci'] and not res['nom']:
        doc.w("Identification de l'avion (feuille C1) introuvable")
    return res


def parse_index(doc: Doc):
    res = {"ref_sta": None, "K": None, "C": None, "mac": None, "lemac": None, "unite_texte": None}
    pgs = doc.pages.get('index', [])
    if not pgs:
        doc.w("Formule d'index (feuille C4) introuvable")
        return res
    for ln in doc.lines(pgs[0]):
        t = ltext(ln)
        m = re.search(r'=\s*([+\-]?\d+(?:[.,]\d+)?)', t)
        if not m:
            continue
        v = num(m.group(1))
        tl = t.lower()
        if re.match(r'^reference (arm|sta\.?) at\b', tl):
            res['ref_sta'] = v
        elif tl.startswith('k (constant)'):
            res['K'] = v
        elif tl.startswith('c (constant)'):
            res['C'] = v
        elif tl.startswith('length of mac'):
            res['mac'] = v
        elif tl.startswith('lemac'):
            res['lemac'] = v
            mu = re.search(r'\d\s+(meters|metres|inches|centimeters|feet)', t, re.I)
            res['unite_texte'] = mu.group(1).lower() if mu else None
    for k in ('ref_sta', 'K', 'C', 'mac', 'lemac'):
        if res[k] is None:
            doc.w(f"Formule d'index : valeur « {k} » non lue")
    return res


def parse_limits(doc: Doc):
    """Masses limites (C? feuille « Aircraft limiting weights ») : MZFW, MLW, MTOW, masse rampe/roulage."""
    rows = []
    for p in doc.pages.get('limits', [])[:2]:
        ls = doc.lines(p)
        head_y = None
        for ln in ls:
            t = ltext(ln)
            if 'Zero' in t and 'Landing' in t and 'Take' in t:
                head_y = ln[0]
            if head_y is None or ln[0] <= head_y + 10:
                continue
            ints = [(x0, num(t_)) for x0, _, t_ in ln[1] if re.match(r'^\d{4,6}$', t_)]
            if len(ints) >= 4:
                txt = [t_ for _, _, t_ in ln[1] if not re.match(r'^\d+$', t_)]
                reg = next((t_ for t_ in txt if re.match(r'^[A-Z0-9]{1,2}-[A-Z0-9]{2,5}$', t_)), None)
                rows.append({"table": txt[0] if txt else None, "reg": reg,
                             "zfw": ints[0][1], "law": ints[1][1], "tow": ints[2][1], "taxi": ints[3][1]})
    if not rows:
        doc.w("Masses limites (MZFW, MLW, MTOW) introuvables")
    return rows


# ---------------------------------------------------------------------------
# Enveloppes de centrage (feuille C5)
# ---------------------------------------------------------------------------
GROUPS = [('zfw', re.compile(r'ZERO\s+FUEL', re.I)), ('tow', re.compile(r'TAKE\s*OFF', re.I)),
          ('law', re.compile(r'LANDING', re.I)), ('taxi', re.compile(r'TAXI|RAMP', re.I))]


def _triple(tokens):
    """Premier triplet (masse entière, %MAC décimal sans signe, index signé) dans une liste de jetons."""
    for i in range(len(tokens) - 2):
        a, b, c = tokens[i], tokens[i + 1], tokens[i + 2]
        if re.match(r'^\d{4,6}$', a) and re.match(r'^\d{1,3}(?:[,.]\d+)?$', b) and re.match(r'^[+\-]?\d{1,4}(?:[,.]\d+)?$', c):
            return num(a), num(b), num(c)
    return None


def parse_cg(doc: Doc):
    """Enveloppes {tableau: {'zfw'|'tow'|'law': {'fwd': [(masse, %MAC, index)], 'aft': [...]}}}."""
    out = {}
    for p in doc.pages.get('cg', []):
        ls = doc.lines(p)
        divider = None
        name = None
        cur = {'L': None, 'R': None}
        table = None
        for ln in ls:
            t = ltext(ln)
            toks = ln[1]
            if t.startswith('Table Name:'):
                name = ' '.join(tt for _, _, tt in toks[2:] if True).strip() or 'STD'
            if t.startswith('FORWARD') and 'AFT' in t:
                aft = [x0 for x0, _, tt in toks if tt == 'AFT']
                divider = (aft[0] - 25) if aft else 300
                table = out.setdefault(name or 'STD', {})
                continue
            if divider is None or table is None:
                continue
            if t.startswith('Click') or t.startswith('*'):
                break
            for side, sel in (('L', lambda x: x < divider), ('R', lambda x: x >= divider)):
                half = [(x0, tt) for x0, _, tt in toks if sel(x0)]
                htxt = ' '.join(tt for _, tt in half)
                for gk, gre in GROUPS:
                    if gre.search(htxt):
                        cur[side] = gk
                tr = _triple([tt for _, tt in half])
                if tr and cur[side]:
                    table.setdefault(cur[side], {'fwd': [], 'aft': []})['fwd' if side == 'L' else 'aft'].append(tr)
    if not out:
        doc.w("Enveloppe de centrage (feuille C5) introuvable")
    return out


# ---------------------------------------------------------------------------
# Masses standard : équipage, passagers, bagages (feuilles B2 à B4)
# ---------------------------------------------------------------------------
def _nearest_col(x, cols):
    """Colonne (nom) dont l'abscisse est la plus proche de x."""
    return min(cols, key=lambda c: abs(c[1] - x))[0]


def parse_masses(doc: Doc):
    res = {"equipage": {}, "pax": {}, "bagage_reel": None, "bagage_plan": {}}
    # --- équipage
    for p in doc.pages.get('crew', [])[:1]:
        ls = doc.lines(p)
        for ln in ls:
            toks = [t for _, _, t in ln[1]]
            if toks and toks[0] == 'Standard':
                vals = [num(t) for t in toks[1:] if num(t) is not None]
                if len(vals) >= 2:
                    res['equipage'] = {"pnt": vals[0], "pnc": vals[1]}
                    break
    if not res['equipage']:
        doc.w("Masses d'équipage (PNT, PNC) introuvables")
    # --- passagers
    for p in doc.pages.get('pax', [])[:1]:
        ls = doc.lines(p)
        cols = None
        for ln in ls:
            toks = ln[1]
            words = [t for _, _, t in toks]
            if 'Adult' in words and 'Child' in words and 'Infant' in words:
                cols = [(w.lower(), (x0 + x1) / 2) for x0, x1, w in toks if w in ('Adult', 'Male', 'Female', 'Child', 'Infant')]
                continue
            if cols and words and words[0] in ('Standard', 'Charter', 'Default'):
                row = {}
                for x0, x1, w in toks[1:]:
                    v = num(w)
                    if v is not None:
                        row[_nearest_col((x0 + x1) / 2, cols)] = v
                if words[0] == 'Standard' and row and 'standard' not in res['pax']:
                    res['pax']['standard'] = row
            if cols and (ltext(ln).startswith('*') or 'Remarks' in ltext(ln)):
                break
    if not res['pax']:
        doc.w("Masses standard des passagers introuvables")
    # --- bagages
    for p in doc.pages.get('bag', [])[:1]:
        ls = doc.lines(p)
        section = None
        for ln in ls:
            t = ltext(ln)
            if 'Checked baggage weight' in t:
                section = 'reel'
            elif 'Planning assumptions' in t:
                section = 'plan'
            toks = [x for _, _, x in ln[1]]
            if toks and toks[0] == 'Standard':
                if section == 'reel' and res['bagage_reel'] is None:
                    res['bagage_reel'] = {"par_piece": toks[2] if len(toks) > 2 else None,
                                          "par_pax": toks[3] if len(toks) > 3 else None}
                elif section == 'plan' and not res['bagage_plan']:
                    vals = [num(x) for x in toks[1:] if num(x) is not None]
                    if len(vals) >= 3:
                        res['bagage_plan'] = {"bagages_par_pax": vals[0], "masse_par_pax": vals[1], "volume": vals[2]}
    return res


# ---------------------------------------------------------------------------
# Masse à vide par configuration et par immatriculation (feuille E5)
# ---------------------------------------------------------------------------
REG_RE = re.compile(r'^[A-Z0-9]{1,2}-[A-Z0-9]{2,5}$')


def parse_regweights(doc: Doc):
    """Liste des configurations : {siege, equipage_txt, nb_pnt, nb_pnc, masse_flotte, index_flotte, ajustements}."""
    out = []
    for p in doc.pages.get('regweights', []):
        ls = doc.lines(p)
        cfg = {"siege": None, "equipage_txt": None, "pnt": None, "pnc": None, "masse_flotte": None,
               "pct_mac_flotte": None, "bras_flotte": None, "index_flotte": None, "ajustements": [], "page": p + 1}
        cols = None
        in_adj = False
        for ln in ls:
            t = ltext(ln)
            m = re.search(r'Seat Config:\s*(.*?)\s+Aircraft Type', t)
            if m:
                cfg['siege'] = m.group(1).strip()
            m = re.search(r'Load Config:\s*(.*?)\s+Registrations', t) or re.search(r'Load Config:\s*(.*)$', t)
            if m and 'Crew' in m.group(1):
                cfg['equipage_txt'] = m.group(1).strip()
                mm = re.search(r'(\d+)\s*/\s*(\d+)', m.group(1))
                if mm:
                    cfg['pnt'], cfg['pnc'] = int(mm.group(1)), int(mm.group(2))
            if t.startswith('2.7.2'):
                in_adj = False
            m = re.search(r'Fleet Weight:\s*((?:\d{1,3}(?:\s\d{3})+|\d+)(?:[.,]\d+)?)', t)
            if m and cfg['masse_flotte'] is None:
                cfg['masse_flotte'] = num(m.group(1).replace(' ', ''))
            m = re.search(r'Fleet Index:\s*([+\-]?[\d.,]+)', t)
            if m:
                cfg['index_flotte'] = num(m.group(1))
            m = re.search(r'Fleet %MAC:\s*([+\-]?[\d.,]+)', t)
            if m:
                cfg['pct_mac_flotte'] = num(m.group(1))
            m = re.search(r'Fleet Balance ARM:\s*([+\-]?[\d.,]+)', t)
            if m:
                cfg['bras_flotte'] = num(m.group(1))
            words = [x for _, _, x in ln[1]]
            if 'Tail' in words and 'Number' in words:
                hdr = {}
                for x0, x1, w in ln[1]:
                    wl = w.lower()
                    if wl == 'weight':
                        hdr['poids'] = (x0 + x1) / 2
                    elif wl.startswith('%mac'):
                        hdr['pct'] = (x0 + x1) / 2
                    elif wl == 'index':
                        hdr['index'] = (x0 + x1) / 2
                for lp in ls:
                    if 0 < lp[0] - ln[0] <= 14:
                        for x0, x1, w in lp[1]:
                            if w.lower() == 'arm':
                                hdr['bras'] = (x0 + x1) / 2
                cols = list(hdr.items())
                in_adj = True
                continue
            if in_adj and words and REG_RE.match(words[0]):
                row = {"reg": words[0], "poids": None, "pct": None, "bras": None, "index": None}
                for x0, x1, w in ln[1][1:]:
                    v = num(w)
                    if v is not None and cols:
                        row[_nearest_col((x0 + x1) / 2, cols)] = v
                cfg['ajustements'].append(row)
            if t.startswith('Click Here') and in_adj:
                in_adj = False
        if cfg['masse_flotte'] is not None:
            out.append(cfg)
    if not out:
        doc.w("Masses à vide par configuration (feuille E5) introuvables")
    return out


# ---------------------------------------------------------------------------
# Carburant : effet cumulé (feuille C9), densité, capacité
# ---------------------------------------------------------------------------
def parse_fuel(doc: Doc):
    res = {"table": [], "densite": None, "densite_min": None, "densite_max": None,
           "masse_max": None, "volume_max": None, "reservoirs": [], "taxi": None}
    cols = None
    for p in doc.pages.get('fuel_cum', []):
        ls = doc.lines(p)
        in_tab = False
        for ln in ls:
            t = ltext(ln)
            toks = ln[1]
            words = [w for _, _, w in toks]
            if t.startswith('Procedure Name') or 'Procedure Name:' in t:
                m = re.search(r'Max Volume:\s*([\d\s]+)', t)
            m = re.search(r'Max Weight:\s*((?:\d{1,3}(?:\s\d{3})+|\d+))', t)
            if m and res['masse_max'] is None:
                res['masse_max'] = num(m.group(1).replace(' ', ''))
            m = re.search(r'Max Volume:\s*((?:\d{1,3}(?:\s\d{3})+|\d+))', t)
            if m and res['volume_max'] is None:
                res['volume_max'] = num(m.group(1).replace(' ', ''))
            m = re.search(r'Fuel Density:\s*(\d[,.]\d+)', t)
            if m and res['densite'] is None:
                res['densite'] = num(m.group(1))
            m = re.search(r'Min:\s*(\d[,.]\d+)\s+.*Max:\s*(\d[,.]\d+)', t)
            if m and res['densite_min'] is None:
                res['densite_min'], res['densite_max'] = num(m.group(1)), num(m.group(2))
            if 'Volume' in words and 'Weight' in words and 'Balance' not in words:
                cols = {}
                for x0, x1, w in toks:
                    if w == 'Volume': cols['volume'] = (x0 + x1) / 2
                    if w == 'Weight': cols['poids'] = (x0 + x1) / 2
                for lp in ls:
                    if 0 < ln[0] - lp[0] <= 16:
                        for x0, x1, w in lp[1]:
                            if w == 'Arm': cols['bras'] = (x0 + x1) / 2
                            if w == 'Index': cols['index'] = (x0 + x1) / 2
                in_tab = True
                continue
            if in_tab and t.startswith(('Click', 'Remarks')):
                in_tab = False
            if in_tab and cols:
                vals = {}
                for x0, x1, w in toks:
                    v = num(w)
                    if v is not None and re.match(r'^[+\-]?\d+(?:[.,]\d+)?$', w):
                        vals[_nearest_col((x0 + x1) / 2, list(cols.items()))] = v
                if 'poids' in vals and 'index' in vals:
                    res['table'].append({"poids": vals['poids'], "index": vals['index'], "volume": vals.get('volume'),
                                         "bras": vals.get('bras')})
    for p in doc.pages.get('fuel_tank', []):
        nm = mw = mv = None
        for ln in doc.lines(p):
            t = ltext(ln)
            m = re.search(r'Table Name:\s*(\S+(?: \S+)*?)(?:\s+Max|$)', t)
            if m and nm is None: nm = m.group(1).strip()
            m = re.search(r'Max Weight:\s*(\d+)', t)
            if m and mw is None: mw = num(m.group(1))
            m = re.search(r'Max Volume:\s*(\d+)', t)
            if m and mv is None: mv = num(m.group(1))
        if nm:
            res['reservoirs'].append({"nom": nm, "masse_max": mw, "volume_max": mv})
    for p in doc.pages.get('fuel_dist', []):
        ls = doc.lines(p)
        for i, ln in enumerate(ls):
            if 'Taxi' in ltext(ln) and 'fuel' in ltext(ln) and ltext(ln).startswith('5.4'):
                for lp in ls[i + 1:i + 6]:
                    nums = [num(w) for _, _, w in lp[1] if re.match(r'^\d{2,4}$', w)]
                    if nums and 'Standard' not in ltext(lp):
                        res['taxi'] = nums[0]
                        break
    if not res['table']:
        doc.w("Effet du carburant (feuille C9) introuvable : bras du carburant non défini")
    return res


# ---------------------------------------------------------------------------
# Soutes (feuille D2)
# ---------------------------------------------------------------------------
SIGNED_RE = re.compile(r'^[+\-]\d+[.,]\d+$')


def _is_dec(w):
    return bool(re.match(r'^\d+[.,]\d+$', w)) or bool(SIGNED_RE.match(w))


def _hold_columns(ls, y_hdr):
    """Abscisses des colonnes du tableau des soutes, d'après la ligne d'en-tête (Weight … Centroid FWD AFT … wt unit)."""
    cols = {}
    cen = []
    for ln in ls:
        if abs(ln[0] - y_hdr) <= 3:
            for x0, x1, w in ln[1]:
                c = (x0 + x1) / 2
                if w == 'Weight': cols['max_kg'] = c
                elif w == 'Centroid': cen.append(c)
                elif w == 'From': cols['lat_de'] = c
                elif w == 'To': cols['lat_a'] = c
                elif w == 'FWD': cols['fwd'] = c
                elif w == 'AFT': cols['aft'] = c
                elif w in ('wt', 'unit'): cols.setdefault('_idx', []).append(c)
        if 0 < y_hdr - ln[0] <= 10:
            for x0, x1, w in ln[1]:
                if w == 'Volume': cols['volume'] = (x0 + x1) / 2
    if cen:
        cen.sort()
        if len(cen) >= 2:
            cols['lat_c'] = cen[0]
            cols['arm'] = cen[-1]
        else:
            cols['arm'] = cen[0]
    if cols.get('_idx'):
        cols['index'] = sum(cols['_idx']) / len(cols['_idx'])
    cols.pop('_idx', None)
    return cols


def parse_holds(doc: Doc):
    """Soutes en vrac (section 2.1). Renvoie les unités de chargement (« feuilles ») :
    [{nom, max_kg, volume, arm_centroide, index_par_kg, groupe, max_groupe_kg, sections:[...]}]"""
    recs = []
    for p in doc.pages.get('holds', []):
        ls = doc.lines(p)
        y21 = y22 = None
        for ln in ls:
            t = ltext(ln)
            if t.startswith('2.1') and 'Bulk' in t: y21 = ln[0]
            if t.startswith('2.2') and 'ULD' in t and y21 is not None: y22 = ln[0]
        if y21 is None:
            continue
        zones = [(y21, y22 or 10 ** 6, 'vrac')] + ([(y22, 10 ** 6, 'uld')] if y22 else [])
        for ya, yb, kind in zones:
            y_hdr = None
            for ln in ls:
                if ya < ln[0] < yb and any(w == 'FWD' for _, _, w in ln[1]) and any(w == 'AFT' for _, _, w in ln[1]):
                    y_hdr = ln[0]
                    break
            if y_hdr is None:
                continue
            cols = _hold_columns(ls, y_hdr)
            if 'max_kg' not in cols or 'index' not in cols:
                continue
            data_cols = [(k, v) for k, v in cols.items() if k in ('max_kg', 'volume', 'arm', 'fwd', 'aft', 'index', 'lat_c', 'lat_de', 'lat_a')]
            rows, names = [], []
            for ln in ls:
                if not (y_hdr + 3 < ln[0] < yb) or ltext(ln).startswith('Click'):
                    continue
                nm_toks = [w for x0, x1, w in ln[1] if x0 < 112]
                vals = {}
                for x0, x1, w in ln[1]:
                    if x0 >= 112 and re.match(r'^[+\-]?\d+(?:[.,]\d+)?$', w):
                        vals[_nearest_col((x0 + x1) / 2, data_cols)] = num(w)
                if 'max_kg' in vals and 'index' in vals:
                    rows.append({"y": ln[0], "nm": ' '.join(nm_toks), "v": vals})
                elif nm_toks:
                    names.append((ln[0], ' '.join(nm_toks)))
            for y, nm in names:
                if nm.lower().startswith('section') or not rows:
                    continue
                k = min(range(len(rows)), key=lambda i: abs(rows[i]['y'] - y))
                if abs(rows[k]['y'] - y) <= 22:
                    rows[k].setdefault('pieces', []).append((y, nm))
            for r in rows:
                full = ' '.join([n for _, n in sorted(r.get('pieces', []))] + ([r['nm']] if r['nm'] else []))
                full = re.sub(r'\s+', ' ', full).strip()
                v = r['v']
                rec = {"nom": full, "max_kg": v.get('max_kg'), "volume": v.get('volume'), "arm_centroide": v.get('arm'),
                       "fwd": v.get('fwd'), "aft": v.get('aft'), "index_par_kg": v.get('index'), "sections": [],
                       "type": kind}
                up = full.upper()
                if up.startswith('SECTION'):
                    if recs and not any(q['nom'] == rec['nom'] and q['max_kg'] == rec['max_kg'] for q in recs[-1]['sections']):
                        recs[-1]['sections'].append(rec)
                else:
                    rec['niveau'] = 'soute+cpt' if ('HOLD' in up and 'CPT' in up) else ('soute' if 'HOLD' in up else 'cpt')
                    key = (rec['nom'], rec['max_kg'], rec['arm_centroide'])
                    if not any((q['nom'], q['max_kg'], q['arm_centroide']) == key for q in recs):
                        recs.append(rec)
    # feuilles = compartiments sans enfant ; les « HOLD » parents donnent la limite de groupe
    leaves, parent = [], None
    for r in recs:
        if r['niveau'] == 'soute':
            parent = r
        elif r['niveau'] == 'cpt':
            r['groupe'] = parent['nom'] if parent else None
            r['max_groupe_kg'] = parent['max_kg'] if parent else None
            if parent:
                r['nom'] = f"{parent['nom']} {r['nom']}"
            leaves.append(r)
        else:
            parent = None
            r['groupe'], r['max_groupe_kg'] = None, None
            leaves.append(r)
    if not leaves:
        doc.w("Soutes (feuille D2, section 2.1) introuvables")
    return leaves


# ---------------------------------------------------------------------------
# Cabine : sections, postes équipage, offices (feuille D5), configurations (D8)
# ---------------------------------------------------------------------------
def page_siege(doc: Doc, p: int):
    """Configuration de sièges indiquée en en-tête de la page (« Seat Config: … »)."""
    for ln in doc.lines(p)[:14]:
        m = re.search(r'Seat Config:\s*(.*?)\s+(?:Aircraft Type|$)', ltext(ln))
        if m and m.group(1).strip():
            return m.group(1).strip()
    return None


def parse_cabin(doc: Doc):
    """Définitions de cabine, une entrée par page : [{siege, sections, poste_pilotage, poste_cabine}]."""
    defs = []
    for p in doc.pages.get('cabin', []):
        ls = doc.lines(p)
        d = {"siege": page_siege(doc, p), "sections": [], "poste_pilotage": [], "poste_cabine": [], "page": p + 1}
        part = None
        seen = set()
        for ln in ls:
            t = ltext(ln)
            if t.startswith('5.1') and 'Cabin Definitions' in t: part = 'sections'
            elif t.startswith('5.2') and 'Flight Deck' in t: part = 'pilotage'
            elif t.startswith('5.3') and 'Cabin Crew' in t: part = 'cabine'
            elif t.startswith('5.4') or t.startswith('5.5'): part = None
            words = [w for _, _, w in ln[1]]
            if not part or not words: continue
            sig = [w for w in words if SIGNED_RE.match(w)]
            if not sig: continue
            idx = num(sig[-1])
            dec = [num(w) for w in words if re.match(r'^\d+[.,]\d+$', w)]
            ints = [int(w) for w in words if re.match(r'^\d{1,4}$', w)]
            txt = ' '.join(w for w in words if not re.match(r'^[+\-]?\d+(?:[.,]\d+)?$', w)).lstrip('> ').strip()
            key = (part, txt, tuple(ints), tuple(dec))
            if key in seen: continue
            seen.add(key)
            if part == 'sections':
                parts_ = txt.split()
                d['sections'].append({"id": parts_[0] if parts_ else None, "pont": parts_[1] if len(parts_) > 1 else None,
                                      "rang_de": ints[0] if ints else None, "rang_a": ints[1] if len(ints) > 1 else None,
                                      "arm": dec[0] if dec else None, "index_par_kg": idx})
            else:
                d['poste_pilotage' if part == 'pilotage' else 'poste_cabine'].append(
                    {"nom": txt, "places": ints[0] if ints else None, "arm": dec[0] if dec else None, "index_par_kg": idx})
        if d['sections']:
            defs.append(d)
    if not defs:
        doc.w("Sections de cabine (feuille D5) introuvables")
    return defs


def parse_crewcodes(doc: Doc):
    """Codes équipage : [{siege, code, pnt, cabine: [(emplacement, nombre)]}]."""
    out = []
    for p in doc.pages.get('crewcodes', []):
        ls = doc.lines(p)
        cur = None
        for ln in ls:
            toks = ln[1]
            t = ltext(ln)
            if t.startswith('Click') or t.startswith('2.3'):
                break
            crew = [w for x0, x1, w in toks if x0 < 140]
            if len(crew) >= 2 and crew[0] == 'Crew' and re.match(r'^\d+/\d+$', crew[1]):
                cur = {"siege": page_siege(doc, p), "code": crew[1], "pnt": None, "cabine": []}
                out.append(cur)
                mid = [(x0, x1, w) for x0, x1, w in toks if 140 <= x0 < 300 or re.match(r'^\d+$', w) and 280 <= x0 < 300]
                tot = [int(w) for x0, x1, w in toks if re.match(r'^\d+$', w) and 280 <= x0 < 305]
                cur['pnt'] = tot[0] if tot else None
            if cur is None:
                continue
            loc = ' '.join(w for x0, x1, w in toks if 305 <= x0 < 425 and not re.match(r'^\d+$', w) or (305 <= x0 < 425 and re.match(r'^[A-Za-z]', w)))
            loc = ' '.join(w for x0, x1, w in toks if 305 <= x0 < 425)
            n = [int(w) for x0, x1, w in toks if re.match(r'^\d+$', w) and 425 <= x0 < 460]
            if loc and n:
                cur['cabine'].append((loc.strip(), n[0]))
    return out


def parse_salecfg(doc: Doc):
    """Configurations commercialisables : [{nom, sections:{id: sièges}, total, index...}]."""
    cfgs = []
    for p in doc.pages.get('salecfg', []):
        ls = doc.lines(p)
        cur = None
        hdr = None
        for ln in ls:
            t = ltext(ln)
            m = re.match(r'^Saleable Configuration:\s*(.+)$', t)
            if m:
                cur = {"nom": m.group(1).strip(), "sections": [], "page": p + 1}
                cfgs.append(cur)
                hdr = None
                continue
            if cur is None:
                continue
            if t.startswith('6.3.2'):
                cur = None
                continue
            words = [w for _, _, w in ln[1]]
            if words and re.match(r'^[O0][A-Z]$', words[0]) and any(SIGNED_RE.match(w) for w in words):
                sig = [w for w in words if SIGNED_RE.match(w)]
                dec = [num(w) for w in words if re.match(r'^\d+[.,]\d+$', w)]
                ints = [int(w) for w in words[1:] if re.match(r'^\d{1,3}$', w)]
                if not ints:
                    continue
                cur['sections'].append({"id": '0' + words[0][1], "sieges": ints[-1], "par_classe": ints[:-1] if len(ints) > 1 else ints,
                                        "arm": dec[0] if dec else None, "index_par_kg": num(sig[-1])})
    for c in cfgs:
        c['total'] = sum(s['sieges'] for s in c['sections']) if c['sections'] else None
    return cfgs


# ---------------------------------------------------------------------------
# Calage du stabilisateur (feuille C11), impressions de la loadsheet (C2, C3), documents (A5)
# ---------------------------------------------------------------------------
def parse_stab(doc: Doc):
    """Table de calage : {'pct_mac': [..], 'lignes': [(masse, [valeurs...]), ...], 'remarque': str}."""
    res = None
    for p in doc.pages.get('stab', []):
        ls = doc.lines(p)
        y_take = None
        for ln in ls:
            if 'Take' in ltext(ln) and 'Off' in ltext(ln) and 'Weight' in ltext(ln):
                y_take = ln[0]
        if y_take is None:
            continue
        hdr = None
        rows = []
        remark = []
        after_remarks = False
        for ln in ls:
            t = ltext(ln)
            if t.startswith('Remarks'):
                after_remarks = True
                continue
            if after_remarks and not t.startswith(('Completed', '(Signature')):
                remark.append(t)
            if ln[0] <= y_take:
                continue
            if t.startswith('Click'):
                break
            toks = ln[1]
            nums_ = [(x1 + x0) / 2 for x0, x1, w in toks if re.match(r'^\d{1,3}(?:[.,]\d+)?$', w)]
            if hdr is None and len(toks) >= 2 and all(re.match(r'^\d{1,3}(?:[.,]\d+)?$', w) for _, _, w in toks):
                hdr = [(num(w), (x0 + x1) / 2) for x0, x1, w in toks]
                continue
            if hdr:
                first = toks[0]
                if re.match(r'^\d{1,6}$', first[2]) and (first[0] + first[1]) / 2 < hdr[0][1] - 20:
                    vals = []
                    for pct, xc in hdr:
                        cand = [(abs((x0 + x1) / 2 - xc), w) for x0, x1, w in toks[1:] if num(w) is not None]
                        cand = [c for c in cand if c[0] < 14]
                        vals.append(num(min(cand)[1]) if cand else None)
                    rows.append((num(first[2]), vals))
        if hdr and rows:
            res = {"pct_mac": [h[0] for h in hdr], "lignes": rows, "remarque": ' '.join(remark).strip() or None}
            break
    return res


def _col_ticks(doc, p, header_markers):
    return None


def parse_balance_out(doc: Doc):
    """Éléments à imprimer sur la loadsheet (feuille C2) : {code: {'edp_final': bool, ...}}."""
    res = {}
    for p in doc.pages.get('balance_out', [])[:1]:
        ls = doc.lines(p)
        cols = None
        for ln in ls:
            t = ltext(ln)
            hd = [tk for tk in ln[1] if tk[2] in ('EDP', 'ACARS')]
            if len(hd) == 4:
                cols = [(['prelim_edp', 'prelim_acars', 'final_edp', 'final_acars'][i], (x0 + x1) / 2)
                        for i, (x0, x1, w) in enumerate(hd)]
                continue
            if not cols:
                continue
            if t.startswith('Click') or t.startswith('2.2'):
                break
            toks = ln[1]
            xs = [(x0 + x1) / 2 for x0, x1, w in toks if w in ('X', 'x')]
            if not xs:
                continue
            code = next((w for x0, x1, w in reversed(toks) if re.match(r'^[A-Z]{2,8}\*?$', w) and w not in ('EDP', 'ACARS', 'X')), None)
            if not code:
                continue
            code = code.rstrip('*')
            d = {k: False for k, _ in cols}
            for x in xs:
                d[_nearest_col(x, cols)] = True
            res[code] = d
    return res


def parse_suppl(doc: Doc):
    """Informations complémentaires imprimées (feuille C3) : {libellé: {'final_edp': bool, ...}}."""
    res = {}
    for p in doc.pages.get('balance_out', []):
        pass
    # La feuille C3 suit la C2 et porte le titre « Supplementary Information »
    for i in range(doc.n):
        if 'Supplementary Information' in doc.text(i) and 'Ballast Fuel' in doc.text(i):
            ls = doc.lines(i)
            cols = None
            for k, ln in enumerate(ls):
                t = ltext(ln)
                hd = [tk for tk in ln[1] if tk[2] in ('EDP', 'ACARS')]
                if len(hd) == 4:
                    cols = [(['prelim_edp', 'prelim_acars', 'final_edp', 'final_acars'][j], (x0 + x1) / 2)
                            for j, (x0, x1, w) in enumerate(hd)]
                    continue
                if not cols or t.startswith('Click'):
                    if t.startswith('Click'):
                        break
                    continue
                toks = ln[1]
                label = ' '.join(w for x0, x1, w in toks if w not in ('X', 'x') and x0 < 330)
                if not label or label.startswith(('AHM', 'Prelim', 'Final')):
                    continue
                d = {k_: False for k_, _ in cols}
                for x0, x1, w in toks:
                    if w in ('X', 'x'):
                        d[_nearest_col((x0 + x1) / 2, cols)] = True
                res[label] = d
            break
    return res


# ---------------------------------------------------------------------------
# Couverture du document
# ---------------------------------------------------------------------------
def parse_cover(doc: Doc):
    res = {"organisme": None, "edition": None, "date": None, "titre": None, "immatriculations": None}
    if doc.n == 0:
        return res
    ls = doc.lines(0)
    for i, ln in enumerate(ls):
        t = ltext(ln)
        m = re.match(r'^Issue Number\s*:\s*(\S+)', t)
        if m: res['edition'] = m.group(1)
        m = re.match(r'^Issue Date\s*:\s*(\S+)', t)
        if m: res['date'] = m.group(1)
        m = re.search(r'Copyright of this manual is with ([A-Za-zÀ-ÿ0-9 .&\-]+?)\.', t)
        if m: res['organisme'] = m.group(1).strip()
        if t.startswith('AHM 565') and i > 0:
            prev = [ltext(x) for x in ls[:i]]
            prev = [x for x in prev if x]
            if prev:
                res['titre'] = prev[0]
                if len(prev) > 1:
                    res['immatriculations'] = prev[1]
    return res


# ---------------------------------------------------------------------------
# Positions de conteneurs et palettes (ULD) : feuilles D2.2, D3 et G
# ---------------------------------------------------------------------------
_DEC = re.compile(r'^[+\-]?\d+(?:[.,]\d+)?$')
_GID = re.compile(r'^(\d[A-Z]\d*)/(\d+[LRP])/([\d.]+)-([\d.]+)')


def _dedupe_words(ws):
    """Le PDF superpose parfois deux fois le même texte (ex. « 40 » puis « 40,772 ») : on garde le plus long à la même position."""
    out = []
    for x0, x1, t in sorted(ws, key=lambda w: (round(w[0]), -len(w[2]))):
        if any(abs(x0 - o[0]) < 1.5 and (o[2].startswith(t) or t.startswith(o[2])) for o in out):
            continue
        out.append((x0, x1, t))
    return sorted(out, key=lambda w: w[0])


def _col(ws, lo, hi):
    c = [w for w in ws if lo <= w[0] < hi]
    return c[0][2] if c else None


def parse_uld(doc: Doc):
    """Positions ULD du fichier (valeurs dans les unités du fichier).
    Renvoie None si le fichier ne définit pas de positions de conteneurs."""
    pages = doc.pages.get('uldpos', [])
    if not pages:
        return None
    rows, fws = [], []
    for p in pages:
        ls = doc.lines(p)
        hold = None
        pending_gid = []
        in_fw = False
        for y, ws in ls:
            ws = _dedupe_words(ws)
            txt = ' '.join(t for _, _, t in ws)
            m = re.match(r'^Hold name:\s*(\S+)', txt)
            if m:
                hold, in_fw, pending_gid = m.group(1), False, []
                continue
            if txt.startswith('Full Width Positions'):
                in_fw = True
                continue
            if hold is None:
                continue
            first = ws[0] if ws else None
            gid = next((t for x, _, t in ws if x < 100 and _GID.match(t)), None)
            nm = _col(ws, 180, 215)
            mx = _col(ws, 222, 262)
            if not in_fw:
                if gid and nm and mx and _DEC.match(mx):
                    g = _GID.match(gid)
                    arm, fr, to, ix = _col(ws, 385, 430), _col(ws, 430, 470), _col(ws, 470, 512), _col(ws, 512, 600)
                    if None in (arm, fr, to, ix):
                        doc.w(f"Position ULD « {nm} » : colonnes de bras incomplètes, position ignorée.")
                        continue
                    rows.append({"hold": hold, "pos": nm, "gid": gid, "kind": g.group(1), "max": num(mx), "arm": num(arm),
                                 "from": num(fr), "to": num(to), "idx": num(ix)})
            else:
                if first and first[0] < 40 and first[2] == '+':
                    g2 = next((t for x, _, t in ws if _GID.match(t)), None)
                    if g2 and not pending_gid and fws:
                        fws[-1]["members"].append(_GID.match(g2).group(2))     # la 2e moitié suit la ligne de la position
                    elif g2:
                        pending_gid.append(g2)
                elif nm and mx and _DEC.match(mx) and re.match(r'^\d+$', nm):
                    arm, fr, to, ix = _col(ws, 385, 430), _col(ws, 430, 470), _col(ws, 470, 512), _col(ws, 512, 600)
                    split = next((t for x, _, t in ws if re.match(r'^\d+/\d+$', t)), None)
                    members = [_GID.match(g).group(2) for g in pending_gid if _GID.match(g)]
                    pending_gid = []
                    if None in (arm, fr, to, ix):
                        continue
                    fws.append({"hold": hold, "pos": nm, "max": num(mx), "arm": num(arm), "from": num(fr), "to": num(to),
                                "idx": num(ix), "split": split, "members": members})
                elif gid and not nm:
                    pending_gid.append(gid)
    if not rows:
        return None

    # compartiment de chaque position : feuille D2.2 (sections rangées par compartiment)
    sect_cpt = {}
    for p in doc.pages.get('holds', []):
        ls = doc.lines(p)
        y22 = next((ln[0] for ln in ls if ltext(ln).startswith('2.2') and 'ULD' in ltext(ln)), None)
        if y22 is None:
            continue
        cpt = None
        for y, ws in ls:
            if y <= y22:
                continue
            t = [w[2] for w in ws]
            if 'CPT' in t and t.index('CPT') + 1 < len(t):
                cpt = t[t.index('CPT') + 1]
            elif t and t[0] == 'Section' and len(t) > 1 and cpt:
                sect_cpt[t[1]] = cpt
    # compatibilité (feuille G)
    compat, compat_k, compat_fw = {}, {}, {}
    for p in doc.pages.get('uldcompat', []):
        cur_pos = None
        for y, ws in doc.lines(p):
            ws = _dedupe_words(ws)
            toks = [t for _, _, t in ws]
            pos = next((t for x, _, t in ws if x < 130 and re.match(r'^\d{2}[LRP]$', t)), None)
            gid = next((t for x, _, t in ws if x < 100 and _GID.match(t)), None)
            codes = [t for x, _, t in ws if x > 80 and re.match(r'^[A-Z]{3}$', t) and t not in ('Bay', 'BPP', 'Hold', 'ULD', 'Not')]
            fw = next((t for x, _, t in ws if x < 100 and re.match(r'^\d{2}$', t)), None) if '(FW)' in toks else None
            if fw and codes:
                compat_fw.setdefault(fw, [])
                compat_fw[fw] += [c for c in codes if c not in compat_fw[fw]]
            elif pos and not gid and codes:
                compat.setdefault(pos, [])
                compat[pos] += [c for c in codes if c not in compat[pos]]
            elif pos and not codes and not gid and len(toks) <= 2:
                cur_pos = pos
            elif gid and codes and not toks[0].startswith('+'):
                g = _GID.match(gid)
                compat_k.setdefault((g.group(2), g.group(1)), [])
                compat_k[(g.group(2), g.group(1))] += [c for c in codes if c not in compat_k[(g.group(2), g.group(1))]]
    # spécifications des ULD (feuille B5) : tare, masse maximale, volume
    specs = []
    for p in doc.pages.get('uldspec', []):
        ls = doc.lines(p)
        y0 = next((ln[0] for ln in ls if 'Tare' in ltext(ln)), None)
        if y0 is None:
            continue
        for y, ws in ls:
            if y <= y0 + 20 or y > 620:
                continue
            ws = _dedupe_words(ws)
            nums = [t for _, _, t in ws if _DEC.match(t)]
            codes = [t for x, _, t in ws if 320 < x < 380 and re.match(r'^[A-Z0-9]{2,4}$', t)]
            ty = [t for x, _, t in ws if x < 140 and re.match(r'^[A-Z0-9]{3}$', t)]
            if ty and len(nums) >= 2:
                specs.append({"type": ty[0], "tare": num(nums[-3]) if len(nums) >= 3 else None, "max": num(nums[-2]), "volume": num(nums[-1])})
    return {"rows": rows, "fullwidth": fws, "section_cpt": sect_cpt, "compat": compat, "compat_kind": {f"{k[0]}|{k[1]}": v for k, v in compat_k.items()},
            "compat_fw": compat_fw, "specs": specs}


def parse_all(data: bytes = None, path: str = None, filename: str = ""):
    """Lit un AHM 565 et renvoie toutes les données trouvées (valeurs d'origine du fichier, unités du fichier)."""
    doc = Doc(data=data, path=path)
    P = {"fichier": filename, "pages": doc.n}
    P["couverture"] = parse_cover(doc)
    P["identification"] = parse_ident(doc)
    P["unites"] = parse_units(doc)
    P["index"] = parse_index(doc)
    P["limites"] = parse_limits(doc)
    P["cg"] = parse_cg(doc)
    P["carburant"] = parse_fuel(doc)
    P["soutes"] = parse_holds(doc)
    P["cabines"] = parse_cabin(doc)
    P["configs_vente"] = parse_salecfg(doc)
    P["uld"] = parse_uld(doc)
    P["equipage_codes"] = parse_crewcodes(doc)
    P["masses"] = parse_masses(doc)
    P["masses_vide"] = parse_regweights(doc)
    P["stab"] = parse_stab(doc)
    P["impression"] = parse_balance_out(doc)
    P["impression_suppl"] = parse_suppl(doc)
    P["avertissements"] = list(doc.warn)
    return P


def is_ahm565(data: bytes) -> bool:
    """Vrai si le PDF ressemble à un AHM 565 (formulaires EDP)."""
    try:
        d = Doc(data=data)
        head = ' '.join(d.text(i) for i in range(min(d.n, 12)))
        return 'AHM' in head and ('565' in head) and ('SEMI' in head or 'EDP' in head)
    except Exception:
        return False


# ===========================================================================
# CONVERSION VERS LE MODÈLE DE L'APPLICATION (mètres, kilogrammes)
# ===========================================================================
LEN_M = {'m': 1.0, 'cm': 0.01, 'in': 0.0254, 'ft': 0.3048}
LEN_TEXT = {'meters': 'm', 'metres': 'm', 'inches': 'in', 'centimeters': 'cm', 'feet': 'ft'}
SRC_TXT = "AHM {org} édition {ed} du {date} : {feuille}"


def _interp_pts(pts, x):
    pts = sorted(pts)
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def _dedupe_weights(pts):
    """Garantit des masses strictement croissantes (une verticale de l'enveloppe est décalée de 0,5 kg)."""
    out = []
    for w, v in sorted(pts, key=lambda p: p[0]):
        if out and w <= out[-1][0]:
            w = out[-1][0] + 0.5
        out.append((w, v))
    return out


def build_envelope(fwd, aft, lemac_m, mac_m):
    """Enveloppe [{weight_kg, fwd_m, aft_m}] à partir des listes (masse, %MAC, index) avant et arrière."""
    f = _dedupe_weights([(w, lemac_m + pct / 100 * mac_m) for w, pct, _ in fwd])
    a = _dedupe_weights([(w, lemac_m + pct / 100 * mac_m) for w, pct, _ in aft])
    ws = sorted({round(w, 1) for w, _ in f} | {round(w, 1) for w, _ in a})
    return [{"weight_kg": w, "fwd_m": round(_interp_pts(f, w), 4), "aft_m": round(_interp_pts(a, w), 4)} for w in ws]


def _norm_loc(s):
    s = re.sub(r'\b(LH|RH|CTR|L|R)\b', '', s.upper())
    return re.sub(r'[^A-Z0-9]', '', s)


def _match_loc(name, defs):
    n = _norm_loc(name)
    for d in defs:
        if _norm_loc(d['nom']) == n:
            return d
    for d in defs:
        dn = _norm_loc(d['nom'])
        if dn and (dn.startswith(n) or n.startswith(dn)):
            return d
    return None


def fuzzy_hold_name(h):
    return h['nom']


def _convert_uld(u, f, ref_m, C_m, comps, rap, src):
    """Positions ULD converties en mètres, rattachées aux compartiments de l'application. Renvoie un dict ou None."""
    inf = lambda m: rap.append(("info", m))
    at = lambda m: rap.append(("attention", m))
    rows, bad_idx, no_cpt, no_types = [], 0, 0, 0
    uld_comps = [c for c in comps if (c.get('type') or '') == 'uld']

    def comp_of(pos):
        cpt = u['section_cpt'].get(pos)
        if cpt is None:
            return None
        hit = [c for c in uld_comps if re.search(r'CPT\s*' + re.escape(str(cpt)) + r'\b', c['name'])]
        return hit[0]['name'] if hit else None

    for r in u['rows']:
        pos, kind = r['pos'], r['kind']
        pallet = len(kind) > 1 and kind[1] == 'P'
        variant = kind[2:] if pallet else ''
        types = (u['compat_kind'].get(f"{pos}|{kind}") if pallet else u['compat'].get(pos)) or []
        arm = r['arm'] * f
        if abs(ref_m + C_m * r['idx'] - arm) > 0.03:
            bad_idx += 1
        comp = comp_of(pos)
        no_cpt += comp is None
        no_types += not types
        rows.append({"id": f"{pos}\u00b7{variant}" if pallet else pos,
                     "label": f"{pos} \u00b7 {variant} po" if pallet else pos,
                     "hold": r['hold'], "pos": pos, "bay": pos[:-1], "kind": "P" if pallet else "C",
                     "sides": ["L", "R"] if pos.endswith('P') else [pos[-1]],
                     "max_kg": r['max'], "arm_m": round(arm, 4), "from_m": round(r['from'] * f, 4), "to_m": round(r['to'] * f, 4),
                     "types": types, "comp": comp})
    for w in u['fullwidth']:
        mem = [m_ for m_ in w['members'] if m_ in u['section_cpt']] or [w['pos'] + 'L']
        comp = comp_of(mem[0])
        no_cpt += comp is None
        types = u['compat_fw'].get(w['pos']) or []
        no_types += not types
        if abs(ref_m + C_m * w['idx'] - w['arm'] * f) > 0.03:
            bad_idx += 1
        rows.append({"id": f"{w['pos']}FW", "label": f"{w['pos']} \u00b7 pleine largeur", "hold": w['hold'], "pos": w['pos'],
                     "bay": w['pos'], "kind": "FW", "sides": ["L", "R"], "max_kg": w['max'], "arm_m": round(w['arm'] * f, 4),
                     "from_m": round(w['from'] * f, 4), "to_m": round(w['to'] * f, 4), "types": types, "comp": comp})
    order = {h: i for i, h in enumerate(dict.fromkeys(r['hold'] for r in rows))}
    rows.sort(key=lambda r: (order[r['hold']], r['from_m'], r['kind'] != 'C', r['id']))
    if bad_idx:
        at(f"Positions ULD : {bad_idx} position(s) dont le bras diffère de plus de 3 cm du bras calculé par l'index : le bras du fichier est utilisé.")
    if no_cpt:
        at(f"Positions ULD : {no_cpt} position(s) sans compartiment identifié : elles ne pourront pas être chargées.")
        rows = [r for r in rows if r['comp']]
    if no_types:
        at(f"Positions ULD : {no_types} position(s) sans type de ULD compatible dans le fichier : type libre.")
    inf(f"Positions ULD lues : {sum(1 for r in rows if r['kind'] == 'C')} conteneurs, {sum(1 for r in rows if r['kind'] == 'P')} palettes, "
        f"{sum(1 for r in rows if r['kind'] == 'FW')} pleine largeur. La masse maximale de chaque position est celle du fichier.")
    inf("Compatibilité des ULD : un code listé pour une position est considéré compatible (le fichier ne montre pas de Y/N lisible) ; à vérifier.")
    specs = u.get('specs') or []
    if not any(sp.get('tare') for sp in specs):
        at("Tare des ULD absente du fichier (feuille B5 vide) : à saisir dans « Nouveau vol ». Sans tare, la masse brute des ULD est sous-estimée.")
    return {"rows": rows, "specs": specs, "comps": sorted({r['comp'] for r in rows})}


def convert(P):
    """Renvoie (ac, rapport). `ac` est un enregistrement d'aéronef de l'application, avec la clé « ahm » qui porte
    les données dépendant de la configuration et de l'immatriculation. `rapport` : liste de (niveau, message)
    avec niveau parmi « erreur » (import impossible), « attention », « info »."""
    rap = []
    er = lambda m: rap.append(("erreur", m))
    at = lambda m: rap.append(("attention", m))
    inf = lambda m: rap.append(("info", m))
    U, I = P['unites'], P['index']
    cov = P['couverture']
    org = cov.get('organisme') or "compagnie"
    src = lambda feuille: SRC_TXT.format(org=org, ed=cov.get('edition') or '?', date=cov.get('date') or '?', feuille=feuille)

    # --- unités
    if U.get('weight') != 'kg':
        er("L'unité de masse du fichier n'est pas le kilogramme : l'application ne convertit pas les masses. Import impossible.")
    f = LEN_M.get(U.get('length'))
    tf = LEN_M.get(LEN_TEXT.get((I.get('unite_texte') or '').lower()))
    if f is None and tf is None:
        er("Unité de longueur illisible : import impossible.")
        f = 1.0
    elif f is None:
        f = tf
        at("Unité de longueur lue dans la feuille d'index (celle de la feuille C1 est illisible).")
    elif tf is not None and abs(tf - f) > 1e-9:
        er(f"Unités de longueur contradictoires dans le fichier (feuille C1 : {U.get('length')}, formule d'index : {I.get('unite_texte')}).")
    if U.get('length') not in (None, 'm'):
        inf(f"Longueurs du fichier en {U.get('length')} : converties en mètres (la constante C est convertie avec les longueurs). Les masses ne sont pas converties.")
    if U.get('density') not in (None, 'kg/l'):
        at("Densité du carburant exprimée dans une autre unité que kg/l : valeur non reprise.")

    for k in ('ref_sta', 'K', 'C', 'mac', 'lemac'):
        if I.get(k) is None:
            er(f"Formule d'index incomplète (valeur « {k} » absente) : import impossible.")
    if any(lv == 'erreur' for lv, _ in rap):
        return None, rap
    ref_m, C_m, mac_m, lemac_m, K = I['ref_sta'] * f, I['C'] * f, I['mac'] * f, I['lemac'] * f, I['K']
    idx_arm = lambda idx_per_kg: ref_m + C_m * idx_per_kg           # bras (m) à partir de l'index par kg
    to_pct = lambda arm_m: (arm_m - lemac_m) / mac_m * 100

    # --- limites de masse
    lim = P.get('limites') or []
    if not lim:
        er("Masses limites introuvables : import impossible.")
        return None, rap
    lim_default = next((r for r in lim if (r.get('table') or '').lower().startswith('standard')), lim[0])
    limits_by_reg = {}
    for r in lim:
        if r.get('reg'):
            limits_by_reg[r['reg']] = {k: r[k] for k in ('zfw', 'law', 'tow', 'taxi')}
    if len({tuple(sorted(v.items())) for v in limits_by_reg.values()}) > 1:
        inf("Masses limites différentes selon l'immatriculation : la limite de l'immatriculation choisie est utilisée.")

    # --- enveloppes de centrage
    cgs = P.get('cg') or {}
    tab = cgs.get('STD') or (next(iter(cgs.values())) if cgs else None)
    env = {}
    if not tab:
        er("Enveloppe de centrage introuvable : import impossible.")
        return None, rap
    for st_ in ('zfw', 'tow', 'law'):
        g = tab.get(st_)
        if g and len(g['fwd']) >= 2 and len(g['aft']) >= 2:
            env[st_] = build_envelope(g['fwd'], g['aft'], lemac_m, mac_m)
            # cohérence %MAC <-> index du fichier
            worst = 0.0
            for side in ('fwd', 'aft'):
                for w, pct, idx in g[side]:
                    sta = lemac_m + pct / 100 * mac_m
                    calc = w * (sta - ref_m) / C_m + K
                    worst = max(worst, abs(calc - idx))
            if worst > 0.1:
                at(f"Enveloppe {st_.upper()} : écart maximal de {worst:.2f} entre l'index du fichier et l'index recalculé depuis le %MAC (le %MAC du fichier est utilisé).")
        elif g:
            at(f"Enveloppe {st_.upper()} incomplète : ignorée.")
    if 'zfw' not in env or 'tow' not in env:
        er("Les enveloppes de centrage ZFW et TOW sont nécessaires : import impossible.")
        return None, rap
    if 'law' not in env:
        inf("Pas de limite de centrage à l'atterrissage dans ce fichier : elle est indiquée « non définie par la compagnie » et n'est pas contrôlée.")

    # --- carburant
    fu = P.get('carburant') or {}
    fuel_tab = []
    for r in fu.get('table') or []:
        if r['poids'] and r['poids'] > 0:
            fuel_tab.append({"fuel_kg": r['poids'], "arm_m": round(ref_m + C_m * r['index'] / r['poids'], 4)})
    fuel_tab.sort(key=lambda p: p['fuel_kg'])
    if len(fuel_tab) >= 2:
        fuel_tab.insert(0, {"fuel_kg": 0.0, "arm_m": fuel_tab[0]['arm_m']})
        wmin = fuel_tab[1]['fuel_kg']
        err = C_m * 0.005 / wmin
        coarse = all(abs(r['index'] - round(r['index'])) < 1e-9 for r in fu['table'])
        if coarse:
            at(f"Index du carburant donné à l'unité dans le fichier : précision du bras limitée (jusqu'à ± {C_m * 0.5 / wmin:.2f} m pour {wmin:.0f} kg).")
        bad = [p for p in fuel_tab[1:] if not (lemac_m - 2 * mac_m <= p['arm_m'] <= lemac_m + 3 * mac_m)]
        if bad:
            at(f"{len(bad)} point(s) du tableau carburant donnent un bras hors de la zone de la corde aérodynamique : à vérifier.")
    else:
        fuel_tab = []
        at("Effet du carburant introuvable : le bras du carburant restera à renseigner.")

    # --- soutes
    comps = []
    for h in P.get('soutes') or []:
        comps.append({"name": h['nom'], "arm_m": round(idx_arm(h['index_par_kg']), 4), "max_kg": h['max_kg'],
                      "status": "compagnie", "source": src("feuille D2, soutes et compartiments"),
                      "groupe": h.get('groupe'), "max_groupe_kg": h.get('max_groupe_kg'),
                      "volume_m3": h.get('volume') if (U.get('volume') == 'm3') else None, "type": h.get('type')})
    if not comps:
        at("Aucune soute lue : à saisir dans « Données aéronef ».")
    names = [c['name'] for c in comps]
    if len(set(names)) != len(names):
        for c in comps:
            c['name'] = f"{c['name']} ({c['max_kg']:.0f})" if names.count(c['name']) > 1 else c['name']

    uld = None
    if P.get('uld'):
        uld = _convert_uld(P['uld'], f, ref_m, C_m, comps, rap, src)

    # --- cabine, configurations
    cabins = P.get('cabines') or []
    cfgs_sale = P.get('configs_vente') or []
    regw = [c for c in (P.get('masses_vide') or []) if 'positioning' not in (c.get('siege') or '').lower()]
    crew_codes = P.get('equipage_codes') or []
    masses = P.get('masses') or {}
    crew_m = masses.get('equipage') or {}
    pnt_kg, pnc_kg = crew_m.get('pnt'), crew_m.get('pnc')
    if pnt_kg is None or pnc_kg is None:
        at("Masses standard PNT/PNC absentes : valeurs réglementaires (85 et 75 kg) utilisées par l'application.")
        pnt_kg, pnc_kg = 85.0, 75.0
    configs = []
    for ci, cfg in enumerate(regw):
        name = cfg['siege']
        sale = next((s for s in cfgs_sale if s['nom'] == name), None)
        if not sale:
            at(f"Configuration « {name} » : plan de sièges introuvable, configuration ignorée.")
            continue
        same = [d for d in cabins if (d.get('siege') or '').upper() in (name.upper(), 'ALL', '')]
        exact = [d for d in cabins if (d.get('siege') or '').upper() == name.upper()]
        cab = exact[0] if exact else (same[min(ci, len(same) - 1)] if same else (cabins[0] if cabins else None))
        if cab is None:
            at(f"Configuration « {name} » : définition de la cabine introuvable.")
            continue
        zones = []
        for s in sale['sections']:
            cs = next((x for x in cab['sections'] if x['id'] == s['id']), None)
            if cs is None:
                continue
            rows = f" (R{cs['rang_de']}–R{cs['rang_a']})" if cs.get('rang_de') and cs.get('rang_a') else ""
            zones.append({"name": f"Cabine {s['id']}{rows}", "arm_m": round(idx_arm(cs['index_par_kg']), 4),
                          "max_pax": s['sieges'], "status": "compagnie",
                          "source": src(f"feuilles D5 et D8 (configuration {name})")})
        if len(zones) != len(sale['sections']):
            at(f"Configuration « {name} » : une section de cabine n'a pas été retrouvée dans la définition de cabine.")
        # équipage : bras moyen
        cc = next((c for c in crew_codes if c['siege'] == name or (cfg.get('equipage_txt') and cfg['equipage_txt'].strip('()').split()[-1] == c['code'])), None)
        pnt, pnc = cfg.get('pnt'), cfg.get('pnc')
        crew_arm = None
        if cc:
            moments, mass = 0.0, 0.0
            fd = cab['poste_pilotage'][0] if cab['poste_pilotage'] else None
            if fd and pnt:
                moments += pnt * pnt_kg * idx_arm(fd['index_par_kg'])
                mass += pnt * pnt_kg
            unmatched = 0
            for loc, n in cc['cabine']:
                m_ = _match_loc(loc, cab['poste_cabine'])
                if m_ is None:
                    unmatched += 1
                    continue
                moments += n * pnc_kg * idx_arm(m_['index_par_kg'])
                mass += n * pnc_kg
            if unmatched:
                at(f"Configuration « {name} » : {unmatched} emplacement(s) d'équipage de cabine non retrouvé(s) ; bras moyen calculé avec les autres.")
            if mass > 0:
                crew_arm = moments / mass
        else:
            at(f"Configuration « {name} » : codes équipage introuvables ; le bras de l'équipage reste celui du DOW.")
        crew_kg = (pnt or 0) * pnt_kg + (pnc or 0) * pnc_kg
        # DOW de flotte -> bras
        W, Idx = cfg['masse_flotte'], cfg['index_flotte']
        if W is None or Idx is None:
            at(f"Configuration « {name} » : masse ou index de flotte absent, configuration ignorée.")
            continue
        adj = {a['reg']: (a.get('poids') or 0.0, a.get('index') or 0.0) for a in cfg['ajustements']}
        dow_pct = to_pct(ref_m + C_m * (Idx - K) / W)
        if not (0 <= dow_pct <= 60):
            at(f"Configuration « {name} » : le centrage du DOW calculé ({dow_pct:.1f} %MAC) est inhabituel : à vérifier.")
        configs.append({"nom": name, "pnt": pnt, "pnc": pnc, "equipage_txt": cfg.get('equipage_txt'),
                        "crew_kg": crew_kg, "crew_arm_m": None if crew_arm is None else round(crew_arm, 4),
                        "dow_flotte_kg": W, "dow_flotte_index": Idx, "ajustements": adj, "zones": zones,
                        "sieges": sale.get('total')})
    if not configs:
        er("Aucune configuration exploitable (masse à vide + plan de sièges) : import impossible.")
        return None, rap

    regs = [r['reg'] for r in (P['identification'].get('registrations') or [])]
    ident = P['identification']
    type_name = ident.get('sous_type') or ident.get('nom') or cov.get('titre') or "Type importé"
    dflt = configs[0]
    max_seats = max((c['sieges'] or 0) for c in configs)

    ac = {
        "type": type_name, "seats_typical": "", "fuel_density": fu.get('densite') if (U.get('density') in (None, 'kg/l') and fu.get('densite')) else 0.8,
        "loading_mode": "vrac", "pax_zones": dflt['zones'], "cargo_comps": comps,
        "cg_envelope": env['tow'], "cg_envelope_zfw": env['zfw'], "cg_envelope_tow": env['tow'],
        "fuel_arm_table": fuel_tab,
        "lemac": round(lemac_m, 4), "mac_length": round(mac_m, 4),
        "max_zfw_kg": int(lim_default['zfw']), "max_tow_kg": int(lim_default['tow']), "max_lw_kg": int(lim_default['law']),
        "mfuel": int(fu['masse_max']) if fu.get('masse_max') else None,
        "cg_min_m": round(min(p['fwd_m'] for p in env['tow'] + env['zfw']), 4),
        "cg_max_m": round(max(p['aft_m'] for p in env['tow'] + env['zfw']), 4),
        "crew_std_flight": dflt['pnt'], "crew_std_cabin": dflt['pnc'],
        "seats": dflt['sieges'], "max_seats": max_seats,
        "cg_limits_by_state": True,
    }
    if 'law' in env:
        ac['cg_envelope_law'] = env['law']
    if uld and uld['rows']:
        ac['uld'] = uld
        ac['loading_mode'] = 'uld'

    ac['ahm'] = {
        "source": {"fichier": P.get('fichier'), "organisme": org, "edition": cov.get('edition'), "date": cov.get('date'),
                   "type": type_name, "fabricant": ident.get('fabricant')},
        "unites_fichier": {"longueur": U.get('length'), "masse": U.get('weight')},
        "index": {"ref_m": ref_m, "C_m": C_m, "K": K, "mac_m": mac_m, "lemac_m": lemac_m},
        "configs": configs, "immatriculations": ident.get('registrations') or [],
        "limites_par_immat": limits_by_reg, "limites_defaut": {k: lim_default[k] for k in ('zfw', 'law', 'tow', 'taxi')},
        "impression": {k: bool(v.get('final_edp') or v.get('final_acars')) for k, v in (P.get('impression') or {}).items()},
        "impression_suppl": {k: bool(v.get('final_edp') or v.get('final_acars')) for k, v in (P.get('impression_suppl') or {}).items()},
        "stab": P.get('stab'), "taxi_standard_kg": fu.get('taxi'),
        "masses": masses,
    }
    return ac, rap


def apply_selection(ac, cfg_name=None, reg=None):
    """Copie de `ac` avec la configuration et l'immatriculation choisies : DOW, équipage, zones passagers, limites."""
    import copy as _copy
    h = ac.get('ahm')
    if not h:
        return ac
    e = _copy.deepcopy(ac)
    cfg = next((c for c in h['configs'] if c['nom'] == cfg_name), h['configs'][0])
    ix = h['index']
    W, Idx = cfg['dow_flotte_kg'], cfg['dow_flotte_index']
    dw, di = cfg['ajustements'].get(reg, (0.0, 0.0)) if reg else (0.0, 0.0)
    W += dw
    Idx += di
    arm = ix['ref_m'] + ix['C_m'] * (Idx - ix['K']) / W
    crew_kg = cfg['crew_kg']
    crew_arm = cfg['crew_arm_m'] if cfg['crew_arm_m'] is not None else arm
    oew = W - crew_kg
    e['oew_kg'] = round(oew, 1)
    e['oew_arm_m'] = round((W * arm - crew_kg * crew_arm) / oew, 4)
    e['crew_kg'] = crew_kg
    e['crew_arm_m'] = round(crew_arm, 4)
    e['crew_std_flight'], e['crew_std_cabin'] = cfg['pnt'], cfg['pnc']
    e['pax_zones'] = cfg['zones']
    e['seats'] = cfg['sieges']
    lim = h['limites_par_immat'].get(reg) or h['limites_defaut']
    e['max_zfw_kg'], e['max_tow_kg'], e['max_lw_kg'] = int(lim['zfw']), int(lim['tow']), int(lim['law'])
    e['ahm_selection'] = {"config": cfg['nom'], "immat": reg, "dow_kg": round(W, 1), "dow_index": round(Idx, 2),
                          "dow_arm_m": round(arm, 4), "dow_pct_mac": round((arm - ix['lemac_m']) / ix['mac_m'] * 100, 2),
                          "ajustement_kg": dw, "ajustement_index": di, "taxi_max_kg": lim.get('taxi')}
    return e


def index_of(h, weight, arm_m):
    ix = h['index']
    return weight * (arm_m - ix['ref_m']) / ix['C_m'] + ix['K']


def pct_mac_of(h, arm_m):
    ix = h['index']
    return (arm_m - ix['lemac_m']) / ix['mac_m'] * 100


def stab_value(stab, weight, pct):
    """Valeur de calage du stabilisateur : interpolation linéaire en masse puis en %MAC (bornée aux extrémités)."""
    if not stab or not stab.get('lignes') or not stab.get('pct_mac'):
        return None
    cols = stab['pct_mac']
    rows = sorted(stab['lignes'], key=lambda r: r[0])

    def at_weight(ci):
        pts = [(w, v[ci]) for w, v in rows if v[ci] is not None]
        return _interp_pts(pts, weight) if pts else None
    pts = [(cols[i], at_weight(i)) for i in range(len(cols))]
    pts = [p for p in pts if p[1] is not None]
    return _interp_pts(pts, pct) if pts else None
