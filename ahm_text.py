# -*- coding: utf-8 -*-
"""Lecture d'un AHM 565 (formulaires EDP de données semi-permanentes) au format PDF ou Excel.

Les deux formats sont d'abord ramenés au même texte « en colonnes » (comme `pdftotext -layout`), puis lus par les
mêmes extracteurs. Chaque valeur est rattachée à sa feuille (lettre + numéro) et à sa page ou onglet d'origine.
Le module ne contient AUCUNE valeur de compagnie : tout provient du fichier lu. Ce qui est absent reste absent
et est signalé dans le rapport.
"""
import io
import re

NUM = r'[-+]?\d+(?:\.\d+)?'
CW = 4.2            # largeur d'un caractère en points : sert à rendre les retraits comme pdftotext
PAGE_W = 595.2


# ----------------------------------------------------------------------------------------------------------------
# Rendu « texte en colonnes »
# ----------------------------------------------------------------------------------------------------------------
def _layout(words, ytol=2.5):
    """words : (x0, y0, x1, y1, texte). Renvoie le texte de la page, une ligne par ordonnée, colonnes par abscisse."""
    ws = sorted(words, key=lambda w: (w[1] + w[3]) / 2)
    lines = []
    for w in ws:
        yc = (w[1] + w[3]) / 2
        if lines and abs(lines[-1][0] - yc) <= ytol:
            lines[-1][1].append(w)
        else:
            lines.append([yc, [w]])
    out = []
    for _, l in lines:
        l.sort(key=lambda w: w[0])
        s = ""
        for w in l:
            col = int(round(w[0] / CW))
            if col <= len(s):
                col = len(s) + (1 if s else 0)
            s += " " * (col - len(s)) + w[4]
        out.append(s.rstrip())
    return "\n".join(out)


def clean(s):
    s = re.sub(r'[ \t]{3,}', '  ', s)
    s = re.sub(r'\n\s*\n+', '\n', s)
    return s



def _regs_from_txt(txt):
    """Groupe(s) d'immatriculations de la feuille, y compris lorsque la liste est coupée sur plusieurs lignes."""
    lines = txt.split('\n')
    i0 = next((i for i, l in enumerate(lines) if 'Aircraft Type' in l), None)
    iR = next((i for i, l in enumerate(lines) if re.match(r'\s*Registrations:', l)), None)
    if iR is None:
        return ''
    lo = (i0 + 1) if (i0 is not None and i0 < iR) else iR
    hi = iR + 1
    while hi < len(lines) and hi < iR + 4 and not re.match(r'\s*\d+(\.\d+)*\s+\S', lines[hi]):
        hi += 1
    region = lines[lo:hi]
    first = re.sub(r'^\s*Registrations:\s*', '', lines[iR]).split()
    carrier = first[-1] if first and re.fullmatch(r'[A-Z0-9]{2}', first[-1]) else None
    toks = []
    for l in region:
        l = re.sub(r'^\s*Registrations:\s*', '', l)
        toks += l.split()
    if carrier and carrier in toks:
        toks.remove(carrier)
    out = ' '.join(toks)
    out = re.sub(r'-\s+(?=[A-Z0-9])', '-', out)
    return out.strip()

# ----------------------------------------------------------------------------------------------------------------
# Feuilles : PDF
# ----------------------------------------------------------------------------------------------------------------
def pdf_sheets(data: bytes):
    try:
        import pymupdf as pm
    except Exception:
        import fitz as pm
    doc = pm.open(stream=data, filetype='pdf')
    sheets = []
    for i in range(len(doc)):
        ws = [(w[0], w[1], w[2], w[3], w[4]) for w in doc[i].get_text("words")]
        txt = clean(_layout(ws))
        head = any(w[4] == 'AHM565' and w[1] < 60 for w in ws)
        if head:
            tl = {}
            for w in ws:
                if w[0] >= 250 and 48 <= w[1] <= 70 and not (w[0] > 440 and len(w[4]) == 1):
                    tl.setdefault(round(w[1] / 6), []).append(w)
            title = ' / '.join(" ".join(x[4] for x in sorted(v, key=lambda z: z[0])) for _, v in sorted(tl.items()))
            code = next((w[4] for w in ws if w[0] > 440 and w[1] < 50 and re.fullmatch(r'[A-H]', w[4])), '')
            shn = re.search(r'Sheet\s+([\d\.]+)', txt)
            sheets.append({'title': title, 'regs': _regs_from_txt(txt), 'sheet': shn.group(1) if shn else '',
                           'code': code, 'pages': [i + 1], 'txt': txt, 'where': 'page'})
        elif sheets:
            sheets[-1]['pages'].append(i + 1)
            sheets[-1]['txt'] += '\n' + txt
    return sheets


# ----------------------------------------------------------------------------------------------------------------
# Feuilles : Excel
# ----------------------------------------------------------------------------------------------------------------
def _xl_words(ws):
    from openpyxl.utils import get_column_letter as L
    ncol = ws.max_column
    widths = []
    for c in range(1, ncol + 1):
        d = ws.column_dimensions.get(L(c))
        widths.append(d.width if d is not None and d.width else (ws.sheet_format.defaultColWidth or 8.43))
    tot = sum(widths) or 1.0
    xs, acc = [], 0.0
    for w in widths:
        xs.append((acc / tot * PAGE_W, (acc + w) / tot * PAGE_W))
        acc += w
    dflt = ws.sheet_format.defaultRowHeight or 15.0
    ys, acc = {}, 0.0
    for r in range(1, ws.max_row + 1):
        ys[r] = acc * 0.6
        acc += ws.row_dimensions[r].height or dflt
    words = []
    for row in ws.iter_rows():
        for cell in row:
            v = cell.value
            if v is None or (isinstance(v, str) and not v.strip()):
                continue
            if isinstance(v, float) and v == int(v) and abs(v) < 1e15:
                v = int(v)
            x0, x1 = xs[cell.column - 1]
            for k, line in enumerate(str(v).splitlines() or [str(v)]):
                toks = line.split()
                if not toks:
                    continue
                total = sum(len(t) for t in toks) + len(toks) - 1
                pos, span = 0, max(x1 - x0, 1.0)
                for t in toks:
                    a = x0 + span * pos / total
                    b = x0 + span * (pos + len(t)) / total if len(toks) > 1 else x1
                    y0 = ys[cell.row] + 4.0 * k
                    words.append((a, y0, b, y0 + 8.0, t, cell.row, cell.column, k))
                    pos += len(t) + 1
    return words


def xlsx_sheets(data: bytes):
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(data), data_only=True)
    sheets = []
    for n, name in enumerate(wb.sheetnames):
        ws = wb[name]
        W = _xl_words(ws)
        txt = clean(_layout([w[:5] for w in W]))
        top = [w for w in W if w[5] <= 12]
        cells = {}
        for w in top:
            cells.setdefault((w[5], w[6]), []).append(w)
        # en-tête : la cellule « AHM565 » donne la ligne ; le titre est la cellule à droite, la lettre la dernière
        row_ahm = next((k[0] for k, v in cells.items() if v[0][4] == 'AHM565'), None)
        if row_ahm is None:
            continue
        left_col = min(k[1] for k, v in cells.items() if k[0] == row_ahm and v[0][4] == 'AHM565')
        right = sorted([(k[1], " ".join(x[4] for x in sorted(v, key=lambda z: (z[7], z[0])))) for k, v in cells.items() if k[0] == row_ahm])
        code_col = right[-1][0] if len(right[-1][1]) == 1 else 10 ** 6
        tl = []
        for (r_, c_), v in sorted(cells.items()):
            if row_ahm <= r_ <= row_ahm + 3 and left_col < c_ < code_col:
                txt_ = " ".join(x[4] for x in sorted(v, key=lambda z: (z[7], z[0])))
                if re.match(r'^(Sheet|Carrier|Aircraft Type|Registrations)', txt_):
                    continue
                for ln_ in sorted({x[7] for x in v}):
                    tl.append(" ".join(x[4] for x in sorted([y for y in v if y[7] == ln_], key=lambda z: z[0])))
        title = ' / '.join(tl)
        code = right[-1][1] if len(right[-1][1]) == 1 else name[:1]
        shn = re.search(r'Sheet\s+([\d\.]+)', txt)
        sheets.append({'title': title, 'regs': _regs_from_txt(txt), 'sheet': shn.group(1) if shn else name[1:],
                       'code': code, 'pages': [n + 1], 'txt': txt, 'where': 'onglet', 'tab': name})
    return sheets


# ----------------------------------------------------------------------------------------------------------------
# Extracteurs (un par feuille de l'AHM 565)
# ----------------------------------------------------------------------------------------------------------------
def regs_list(s):
    if s.strip().upper() == 'ALL':
        return ['ALL']
    return [x.strip() for x in re.split(r'[,\s]+', s) if x.strip()]


def find_sheets(sheets, key, group=None):
    out = []
    for sh in sheets:
        if key.lower() in sh['title'].lower():
            rl = regs_list(sh['regs'])
            if group is None or 'ALL' in rl or group in rl:
                out.append(sh)
    return out


def pick(sheets, key, group, must=None):
    c = [s for s in find_sheets(sheets, key, group) if (must is None or must in s['txt'])]
    spec = [s for s in c if 'ALL' not in regs_list(s['regs'])]
    return (spec or c)


def fnum(x):
    return float(x.replace('+', ''))


def src(sh, code=None):
    return {'sheet': (code or sh.get('code') or '') + ' ' + sh['sheet'], 'pages': sh['pages'], 'where': sh.get('where')}


def x_ideal(sheets, group):
    """Feuille C7 : ligne et zone de centrage idéales (§ 4.3) et limites de basculement / stabilité au sol (§ 4.4)."""
    shs = pick(sheets, 'Ideal Trim Line', group)
    if not shs:
        return None
    sh = shs[0]
    line, sec, tabs, cur = [], None, [], None
    ref_kind = 'TOW'
    num = r'[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'
    for l in sh['txt'].split('\n'):
        t = l.strip()
        if re.match(r'4\.3\b', t):
            sec = '43'
        elif re.match(r'4\.4\b', t):
            sec = '44'
        if re.search(r'LIZFW', t):
            ref_kind = 'ZFW'
        if sec == '44':
            m = re.match(r'Table Name:\s*(\S.*)$', t)
            if m:
                cur = {'name': m.group(1).strip(), 'condition': '', 'points': []}
                tabs.append(cur)
                continue
            m = re.match(r'Condition:\s*(.*)$', t)
            if m and cur is not None:
                cur['condition'] = m.group(1).strip()
                continue
        toks = t.split()
        if toks and all(re.fullmatch(num, x) for x in toks):
            v = [fnum(x) for x in toks]
            if sec == '43' and len(v) in (3, 7) and v[0] >= 1000:
                line.append({'weight_kg': v[0], 'pct_mac': v[1], 'index': v[2],
                             'fwd_pct_mac': v[3] if len(v) == 7 else None, 'aft_pct_mac': v[5] if len(v) == 7 else None})
            elif sec == '44' and cur is not None and len(v) == 3 and v[0] >= 1000:
                if cur['points'] and v[0] < cur['points'][-1]['weight_kg']:      # nouvelle table sans nouvel en-tête
                    cur = {'name': cur['name'], 'condition': '', 'points': []}
                    tabs.append(cur)
                cur['points'].append({'weight_kg': v[0], 'pct_mac': v[1], 'index': v[2]})
    if not line:
        return None
    return {'registrations_group': sh['regs'], 'ideal_trim_line': line, 'ideal_trim_reference_remark': ref_kind,
            'tipping_tables': [t for t in tabs if t['points']], 'source': src(sh, 'C')}


def x_units(sheets):
    shs = find_sheets(sheets, 'Units of Measurement')
    if not shs:
        return None
    sh = shs[0]
    t = sh['txt']
    w = 'kg' if re.search(r'X\s*Kilograms', t) else ('lb' if re.search(r'X\s*US Pounds', t) else None)
    if re.search(r'X\s*Metres', t):
        l = 'm'
    elif re.search(r'X\s*Inches', t):
        l = 'in'
    else:
        l = None
    return {'weight': w, 'length': l, 'source': src(sh)}


def x_index(sheets):
    shs = find_sheets(sheets, 'Basic Index and MAC')
    if not shs:
        return None
    sh = shs[0]
    t = sh['txt']
    try:
        g = lambda pat: fnum(re.search(pat, t).group(1))
        u = re.search(r'Reference Arm at\s*=\s*' + NUM + r'\s+(meters|inches)', t).group(1)
        return {'length_unit': 'm' if u == 'meters' else 'in', 'ref_arm': g(r'Reference Arm at\s*=\s*(' + NUM + ')'),
                'K': g(r'K \(constant\)\s*=\s*(' + NUM + ')'), 'C': g(r'C \(constant\)\s*=\s*(' + NUM + ')'),
                'mac_length': g(r'Length of MAC\s*=\s*(' + NUM + ')'),
                'lemac': g(r'LEMAC\s*=\s*(' + NUM + r')\s*(?:meters|inches)'), 'source': src(sh)}
    except Exception:
        return None


def x_cg(sheets, group):
    shs = pick(sheets, 'Centre of Gravity Limits', group, 'CG')
    shs = [s for s in shs if 'limits for loadsheet' in s['txt']]
    if not shs:
        return None
    sh = shs[0]
    EV = r'(TAKE ?OFF|ZERO FUEL|LANDING)\*{0,2}'
    tables, cur = [], None

    def new_table(name='STANDARD', cond=''):
        t = {'name': name, 'condition': cond, 'envelope_type': None,
             'envelopes': {'TAKEOFF': {'fwd': [], 'aft': []}, 'ZEROFUEL': {'fwd': [], 'aft': []}, 'LANDING': {'fwd': [], 'aft': []}}}
        tables.append(t)
        return t

    def pt(w, p, i, star=''):
        d = {'weight_kg': fnum(w), 'pct_mac': fnum(p), 'index': fnum(i)}
        if star:
            d['applicability'] = star
        return d

    for l in sh['txt'].split('\n'):
        m = re.match(r'\s*Table Name:\s*(.+)$', l)
        if m:
            cur = new_table(m.group(1).strip()); continue
        m = re.match(r'\s*Condition:\s*(.*)$', l)
        if m and cur is not None and not cur['condition']:
            cur['condition'] = m.group(1).strip(); continue
        m = re.match(r'\s*From:\s*(' + NUM + r')?\s*To:\s*(' + NUM + r')?\s*Type:\s*(.*)$', l)
        if m and cur is not None and (m.group(1) or m.group(2)):
            cur['applies'] = {'from': fnum(m.group(1)) if m.group(1) else None, 'to': fnum(m.group(2)) if m.group(2) else None,
                              'type': m.group(3).strip()}
            continue
        m = re.search(r'Curtailed:\s*(X)?', l)
        if m and cur is not None and cur['envelope_type'] is None and 'Certified' in l:
            cur['envelope_type'] = 'curtailed' if m.group(1) else 'certified'; continue
        m = re.match(r'\s*' + EV + r'(\*{0,2})\s+(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + r')(.*)$', l)
        if m and not m.group(6).strip() and cur is not None:
            # ligne seule (le texte est compacté) : colonne de droite si le poids repart en arrière de la fin de la colonne de gauche
            kk = m.group(1).replace(' ', '')
            fw_, af_ = cur['envelopes'][kk]['fwd'], cur['envelopes'][kk]['aft']
            w_ = fnum(m.group(3))
            ss = cur.setdefault('_ss', {})
            if fw_ and af_ and ((ss.get(kk) == 'aft' and w_ >= af_[-1]['weight_kg'])
                                or (ss.get(kk) is None and w_ < fw_[-1]['weight_kg'] and w_ >= af_[-1]['weight_kg'])):
                af_.append(pt(m.group(3), m.group(4), m.group(5), m.group(2)))
                ss[kk] = 'aft'
                continue
        if m:
            if cur is None:
                cur = new_table()
            k = m.group(1).replace(' ', '')
            star = re.match(r'\s*(?:TAKE ?OFF|ZERO FUEL|LANDING)(\*{0,2})', l).group(1)
            cur['envelopes'][k]['fwd'].append(pt(m.group(3), m.group(4), m.group(5), star))
            a2 = re.match(r'\s+' + EV + r'(\*{0,2})\s+(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + r')\s*$', m.group(6))
            if a2:
                cur['envelopes'][a2.group(1).replace(' ', '')]['aft'].append(pt(a2.group(3), a2.group(4), a2.group(5), a2.group(2)))
            continue
        m = re.match(r'\s{12,}' + EV + r'(\*{0,2})\s+(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + r')\s*$', l)
        if m and cur is not None:
            cur['envelopes'][m.group(1).replace(' ', '')]['aft'].append(pt(m.group(3), m.group(4), m.group(5), m.group(2)))
    for t_ in tables:
        t_.pop('_ss', None)
    if not tables:
        return None
    if len(tables) == 1 and tables[0]['envelope_type'] is None:
        tables[0]['envelope_type'] = 'curtailed' if re.search(r'Curtailed:\s*X', sh['txt']) else 'certified'
    return {'registrations_group': sh['regs'], 'tables': tables, 'source': src(sh)}


def x_weights(sheets, group):
    shs = [s for s in sheets if 'Maximum Weights Tables' in s['txt'] and
           ('ALL' in regs_list(s['regs']) or group in regs_list(s['regs']))]
    spec = [s for s in shs if 'ALL' not in regs_list(s['regs'])]
    shs = spec or shs
    if not shs:
        return None
    sh = shs[0]
    rows = []
    for l in sh['txt'].split('\n'):
        m = re.match(r'\s*(?:0\s+|-1\s+|-\s+)?(?:(WEIGHT VARIANT \d+)\s+)?([A-Z0-9]{1,2}-?\w+)\s+(\d{5,6})\s+(\d{5,6})\s+(\d{5,6})(?:\s+(\d{5,6}))?', l)
        if m:
            rows.append({'variant': m.group(1), 'reg': m.group(2), 'mzfw': int(m.group(3)), 'mlw': int(m.group(4)),
                         'mtow': int(m.group(5)), 'mtaxi': int(m.group(6)) if m.group(6) else None})
    uniq = sorted({(r['mzfw'], r['mlw'], r['mtow'], r['mtaxi'] or 0) for r in rows})
    lmc = re.search(r'((?:A|B)\d{3}[\w-]*)\s*:\s*(\d+)\s*kg\s*Total Weight', sh['txt'])
    return {'registrations_group': sh['regs'], 'n_aircraft': len({r['reg'] for r in rows}),
            'distinct_sets': [dict(zip(('mzfw', 'mlw', 'mtow', 'mtaxi'), (u[0], u[1], u[2], u[3] or None))) for u in uniq],
            'rows': rows, 'lmc_limit_kg': int(lmc.group(2)) if lmc else None, 'source': src(sh)}


def _nums(tokens):
    return [None if t == '-' else fnum(t) for t in tokens]


def x_holds(sheets, group):
    shs = pick(sheets, 'Holds', group)
    if not shs:
        return None
    sh = shs[0]
    out = {'registrations_group': sh['regs'], 'entries': [], 'source': src(sh)}
    mode = deck = None
    for l in sh['txt'].split('\n'):
        if re.search(r'2\.1\s+Bulk Holds', l):
            mode = 'bulk'; continue
        if re.search(r'2\.2\s+ULD Holds', l):
            mode = 'uld'; continue
        if mode is None:
            continue
        m = re.match(r'\s*Deck Name:\s*(\w+)', l)
        if m:
            deck = m.group(1); continue
        m = re.match(r'\s*(HOLD(?:\s+[A-Z]+)?|(?:CPT|BAY)(?:\s+\d{1,3}(?=\s))?|(?:MAIN|LOWER)\s+[A-Z]+|(?:FWD|AFT)(?:\s+\d+&\d+|\s+\d{1,2}(?=\s))?)\s+((?:-|[-+]?\d+(?:\.\d+)?)(?:\s+(?:-|[-+]?\d+(?:\.\d+)?))*)\s*$', l)
        if not m:
            continue
        label = re.sub(r'\s+', ' ', m.group(1).strip())
        toks = m.group(2).split()
        lm = re.match(r'(HOLD|CPT|BAY)\s*$', label)
        if lm and toks and re.fullmatch(r'\d+', toks[0]):
            label = label + ' ' + toks[0]; toks = toks[1:]
        n = _nums(toks)
        kind = 'hold' if label.startswith('HOLD') else 'cpt'
        if len(n) == 6:
            v = dict(zip(('max_kg', 'volume', 'arm_centroid', 'arm_from', 'arm_to', 'index_per_kg'), n))
        elif len(n) == 5:
            v = dict(zip(('max_kg', 'arm_centroid', 'arm_from', 'arm_to', 'index_per_kg'), n))
        elif len(n) == 4:
            v = dict(zip(('max_kg', 'volume', 'arm_from', 'arm_to'), n)) if kind == 'hold' else dict(zip(('max_kg', 'arm_centroid', 'arm_from', 'arm_to'), n))
        elif len(n) == 3:
            v = dict(zip(('max_kg', 'arm_from', 'arm_to'), n)) if kind == 'hold' else dict(zip(('max_kg', 'arm_centroid', 'index_per_kg'), n))
        elif len(n) == 2:
            v = dict(zip(('arm_from', 'arm_to'), n))
        else:
            v = {'raw': n}
        out['entries'].append({'mode': mode, 'deck': deck, 'kind': kind, 'label': label, 'values': v})
    return out


def x_cabin(sheets, group):
    shs = pick(sheets, 'Cabin and Crew Locations', group)
    if not shs:
        return None
    sh = shs[0]
    sections = []
    for l in sh['txt'].split('\n'):
        m = re.match(r'\s*(\w{2})\s+(Main|Upper|Lower)\s+(\d+)\s+(\d+)\s+(' + NUM + r')\s+(' + NUM + r')\s*$', l)
        if m:
            sections.append({'section': m.group(1), 'deck': m.group(2), 'row_from': int(m.group(3)), 'row_to': int(m.group(4)),
                             'arm_centroid_m': fnum(m.group(5)), 'index_per_kg': fnum(m.group(6))})
    return {'registrations_group': sh['regs'], 'sections': sections, 'source': src(sh)}


def x_fuel(sheets, group='ALL'):
    out = {'tanks': [], 'source': []}
    for sh in find_sheets(sheets, 'Fuel', group if group != 'ALL' else None):
        if not sh['title'].strip().endswith('Fuel'):
            continue
        rl = regs_list(sh['regs'])
        if group != 'ALL' and 'ALL' not in rl and group not in rl:
            continue
        t = sh['txt']
        if 'Effect of fuel' in t:
            out['source'].append(src(sh))
            cur = None; dens = mv = mw = None
            for l in t.split('\n'):
                m = re.match(r'\s*Max Volume:\s*(' + NUM + ')', l)
                if m:
                    if cur is not None and not cur['points']:
                        cur['max_volume_l'] = fnum(m.group(1))
                    else:
                        mv = fnum(m.group(1))
                    continue
                m = re.match(r'\s*Max Weight:\s*(' + NUM + ')', l)
                if m:
                    if cur is not None and not cur['points']:
                        cur['max_weight_kg'] = fnum(m.group(1))
                    else:
                        mw = fnum(m.group(1))
                    continue
                m = re.match(r'\s*Fuel Density:\s*(' + NUM + ')', l)
                if m:
                    if cur is not None and not cur['points']:
                        cur['density'] = fnum(m.group(1))
                    else:
                        dens = fnum(m.group(1))
                    continue
                m = re.match(r'\s*Table Name:?\s+(.+)$', l)
                if m and 'SEPERATE' not in m.group(1) and 'SEPARATE' not in m.group(1):
                    cur = {'name': m.group(1).strip(), 'density': None, 'max_volume_l': None, 'max_weight_kg': None, 'points': []}
                    mv = mw = dens = None
                    out['tanks'].append(cur); continue
                m = re.match(r'\s*Tank Names:\s+(.+)$', l)
                if m and (cur is None or cur['points'] or cur['name'] != m.group(1).strip()) and (cur is None or cur['points']):
                    cur = {'name': m.group(1).strip(), 'density': dens, 'max_volume_l': mv, 'max_weight_kg': mw, 'points': []}
                    mv = mw = dens = None
                    out['tanks'].append(cur); continue
                m = re.match(r'\s*(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + r')\s*$', l)
                if m and cur is not None:
                    cur['points'].append({'volume_l': fnum(m.group(1)), 'weight_kg': fnum(m.group(2)),
                                          'arm': fnum(m.group(3)), 'index': fnum(m.group(4))})
        if 'Cumulative' in t:
            out['source'].append(src(sh))
            pts = []
            for l in t.split('\n'):
                m = re.match(r'\s*(' + NUM + r')\s+(' + NUM + r')\s*$', l)
                if m:
                    pts.append({'weight_kg': fnum(m.group(1)), 'index': fnum(m.group(2))})
            md = re.search(r'Max Volume:\s*(' + NUM + ')', t); mw_ = re.search(r'Max Weight:\s*(' + NUM + ')', t)
            out['cumulative'] = {'max_volume_l': fnum(md.group(1)) if md else None,
                                 'max_weight_kg': fnum(mw_.group(1)) if mw_ else None, 'points': pts}
    for tk in out['tanks']:
        if tk['points'] and tk['max_weight_kg'] is None:
            tk['max_weight_kg'] = max(p['weight_kg'] for p in tk['points']); tk['max_volume_l'] = max(p['volume_l'] for p in tk['points'])
    return out


def x_standards(sheets):
    out = {}
    for sh in find_sheets(sheets, 'Passenger and Carry-on Weights'):
        m = re.search(r'All flight except holiday charters\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', sh['txt'])
        if m:
            out['pax_weights_kg'] = {'adult': int(m.group(1)), 'male': int(m.group(2)), 'female': int(m.group(3)),
                                     'child': int(m.group(4)), 'infant': int(m.group(5)), 'source': src(sh)}
    for sh in find_sheets(sheets, 'Crew and Baggage Weights'):
        m = re.search(r'STANDARD\s+M\s+(\d+)\s+(\d+)', sh['txt'])
        if m:
            out['crew_weights_kg'] = {'flight_deck': int(m.group(1)), 'cabin': int(m.group(2)), 'source': src(sh)}
    for sh in find_sheets(sheets, 'Baggage Weights and Planning'):
        rows = []
        for l in sh['txt'].split('\n'):
            m = re.match(r'\s*(Domestic|International|ER-Longhaul|Charter)\s+All\s+(\d+)\s+(\d+)', l)
            if m:
                rows.append({'type': m.group(1), 'kg_per_piece': int(m.group(2)), 'kg_per_pax': int(m.group(3))})
        out['checked_baggage_kg'] = {'rows': rows, 'source': src(sh)}
    return out


def x_basic(sheets, group):
    shs = pick(sheets, 'Aircraft Registration Weights', group)
    if not shs:
        return None
    sh = shs[0]
    ac, sec = [], False
    for l in sh['txt'].split('\n'):
        if '2.7.2' in l:
            sec = True
        if not sec:
            continue
        m = re.match(r'\s*([A-Z0-9]{1,2}-?\w+)\s+(\d{5,6})\s+(' + NUM + r')(?:\s+(' + NUM + r')\s+(' + NUM + r'))?(?:\s+-)?(?:\s+(?:FREIGHTER|MSN).*)?$', l)
        if m:
            rem = l.split(m.group(3), 1)[1]
            rem = re.sub(r'^\s*(?:' + NUM + r'\s+' + NUM + r')?\s*(?:-\s+)?', '', rem).strip() if m.group(4) else rem.strip()
            if m.group(4):                       # trois colonnes publiées : %MAC, bras, index
                ac.append({'reg': m.group(1), 'basic_weight_kg': int(m.group(2)), 'pct_mac': fnum(m.group(3)),
                           'arm': fnum(m.group(4)), 'index': fnum(m.group(5)), 'remark': rem})
            else:                                # une seule valeur : elle figure sous la colonne « Index » (constaté sur tous les AHM THY)
                ac.append({'reg': m.group(1), 'basic_weight_kg': int(m.group(2)), 'pct_mac': None,
                           'arm': None, 'index': fnum(m.group(3)), 'remark': rem})
    return {'registrations_group': sh['regs'], 'aircraft': ac, 'source': src(sh)}


def x_saleable(sheets, group):
    """Configurations commercialisables avec, pour chacune, les sections de cabine (sièges, bras, index par kg).
    Dans l'AHM, la liste des noms vient d'abord, puis un tableau de sections par configuration, dans le même ordre."""
    shs = pick(sheets, 'Saleable Configurations', group)
    if not shs:
        return None
    sh = shs[0]
    names = [n.strip() for n in re.findall(r'Saleable Configuration:[ \t]*(\S[^\n]*)', sh['txt']) if not re.match(r'\d+\.\d', n.strip())]
    row = re.compile(r'\s*(0[A-Z])\s+((?:\d+\s+)+)(\d+(?:\.\d+)?)\s+(?:' + NUM + r'\s+){0,2}([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*$')
    blocks, cur = [], []
    for l in sh['txt'].split('\n'):
        m = row.match(l)
        if m:
            ints = [int(x) for x in m.group(2).split()]
            cur.append({'id': m.group(1), 'seats': ints[-1], 'arm': float(m.group(3)), 'index_per_kg': fnum(m.group(4))})
        elif re.match(r'\s*Total Per Class', l):
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    cfgs = []
    for i, n in enumerate(names):
        secs = blocks[i] if i < len(blocks) else []
        want = sum(int(x) for x in re.findall(r'(\d+)', n)) if re.search(r'\d', n) else None
        tot = sum(s_['seats'] for s_ in secs) if secs else None
        cfgs.append({'name': n, 'sections': secs, 'total': tot, 'name_total': want})
    return {'registrations_group': sh['regs'], 'configurations': cfgs, 'blocks': len(blocks), 'source': src(sh)}


def x_crew(sheets, group):
    """Équipage de la composition « STANDARD » : PNT (commandant + copilote) et PNC (total des emplacements cabine)."""
    shs = pick(sheets, 'Aircraft Registration Weights', group) + [s for s in find_sheets(sheets, 'Dry Operating Weight', group)]
    for sh in find_sheets(sheets, 'Aircraft Registration Weights', group) + find_sheets(sheets, 'Dry Operating', group):
        if 'Crew Codes' not in sh['txt']:
            continue
        lines = sh['txt'].split('\n')
        for i, l in enumerate(lines):
            if re.match(r'\s*STANDARD\s+', l):
                pnt = pnc = 0
                j = i
                while j < len(lines) and (j == i or not re.match(r'\s*[A-Z][A-Z0-9 ]{3,}\s+(Captain|First|Cockpit)', lines[j])):
                    t = lines[j]
                    m = re.search(r'(Captain|First Officer)\s+(\d+)', t)
                    if m:
                        pnt += int(m.group(2))
                    m = re.search(r'\b(FWD|AFT|MID|MIDDLE|CTR|UPPER)\b[^\d]*(\d+)\s*$', t)
                    if m:
                        pnc += int(m.group(2))
                    j += 1
                    if j - i > 8 or (j < len(lines) and re.match(r'\s*\*|\s*Remarks|\s*Click', lines[j])):
                        break
                if pnt and pnc:
                    return {'pnt': pnt, 'pnc': pnc, 'source': src(sh)}
    return None


# ----------------------------------------------------------------------------------------------------------------
# Assemblage d'un type (un groupe d'immatriculations) + rapport de contrôle
# ----------------------------------------------------------------------------------------------------------------
LEN_FACTOR = {'m': 1.0, 'in': 0.0254}


def read_sheets(data: bytes, filename: str = ""):
    """Détecte le format (PDF ou Excel) et renvoie les feuilles. Lève ValueError si ce n'est pas un AHM 565."""
    name = (filename or "").lower()
    if data[:4] == b'%PDF' or name.endswith('.pdf'):
        sheets = pdf_sheets(data)
        kind = 'pdf'
    elif data[:2] == b'PK' or name.endswith(('.xlsx', '.xlsm')):
        sheets = xlsx_sheets(data)
        kind = 'xlsx'
    else:
        raise ValueError("Format non reconnu : fournir un PDF ou un fichier Excel (.xlsx).")
    head = " ".join(s['txt'][:400] for s in sheets[:6])
    if 'AHM565' not in head.replace(' ', '') or not any('Basic Index and MAC' in s['title'] for s in sheets):
        raise ValueError("Ce fichier ne ressemble pas à un AHM 565 (formulaires EDP de données semi-permanentes).")
    return sheets, kind


def cover_info(sheets, filename=""):
    """Type, compagnie (code transporteur), édition et date : date = la plus récente des dates d'application des feuilles ;
    édition = numéro de révision du nom de fichier s'il y figure."""
    from datetime import date
    info = {'edition': None, 'date': None, 'organisme': None, 'type': None}
    best = None
    for s in sheets:
        if not info['type']:
            m = re.search(r'Aircraft Type:\s*(\S+(?: \S+)*?)\s{2,}Carrier', s['txt']) or re.search(r'Aircraft Type:\s*(\S+)', s['txt'])
            if m and m.group(1).strip() and m.group(1).strip() != 'Carrier':
                info['type'] = m.group(1).strip()
        if not info['organisme']:
            m = re.search(r'Registrations:[^\n]*?\s([A-Z0-9]{2})\s*$', s['txt'], re.M)
            if m:
                info['organisme'] = m.group(1)
        for m in re.finditer(r'Effective Date:\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', s['txt']):
            d_, mo, y = (int(x) for x in m.groups())
            y = y if y > 99 else 2000 + y
            try:
                dt = date(y, mo, d_)
            except ValueError:
                continue
            if best is None or dt > best:
                best = dt
    if best:
        info['date'] = best.strftime('%d/%m/%Y')
    m = re.search(r'rev\.?\s*0*(\d+)', filename or '', re.I)
    if m:
        info['edition'] = m.group(1)
    return info


def groups_of(sheets):
    """Groupes d'immatriculations qui ont des masses de base individuelles : [(groupe, nb_avions)]."""
    out = []
    for s in sheets:
        if 'Aircraft Registration Weights' in s['title'] and s['regs'].upper() != 'ALL':
            b = x_basic([s], s['regs'].split(',')[0].strip())
            n = len(b['aircraft']) if b else 0
            if n:
                out.append((s['regs'], n))
    if not out:
        for s in sheets:
            if 'Aircraft Registration Weights' in s['title']:
                b = x_basic([s], 'ALL')
                if b and b['aircraft']:
                    out.append((s['regs'], len(b['aircraft'])))
    return out


def x_uld_positions(sheets, group):
    """Feuille D3 « ULD Configurations » (§ 3.1) : positions de ULD par pont, avec masse maximale et bras (unités du fichier)."""
    shs = pick(sheets, 'ULD Configurations', group, must='ULD Positions')
    if not shs:
        return None
    sh = shs[0]
    rx = re.compile(r'^\s*(?P<cfg>[A-Z][A-Z ]*?[A-Z])\s+(?P<pos>[A-Z0-9]{1,4}(?:\s*[,/]\s*[A-Z0-9]{1,4})?)\s+'
                    r'(?P<max>\d+(?:\.\d+)?)\s+(?P<rest>[-+0-9.±\s]+?)(?:\s+-)?\s*$')
    out, hold = [], None
    for l in sh['txt'].split('\n'):
        m = re.match(r'\s*Hold Name:\s*(.+?)\s*$', l)
        if m:
            hold = re.sub(r'\s+', ' ', m.group(1)); continue
        if hold is None:
            continue
        m = rx.match(l)
        if not m:
            continue
        tk = m.group('rest').split()
        try:
            if len(tk) >= 7:
                arm, fwd, aft, idx = (float(x) for x in tk[-4:])
            elif len(tk) == 4:
                arm, fwd, aft, idx = (float(x) for x in tk)
            else:
                continue
        except ValueError:
            continue
        pos = re.sub(r'\s+', '', m.group('pos')).replace(',', '/')
        out.append({'hold': hold, 'config': re.sub(r'\s+', ' ', m.group('cfg')), 'pos': pos,
                    'max_kg': float(m.group('max')), 'arm': arm, 'from': fwd, 'to': aft, 'index_per_kg': idx})
    return {'registrations_group': sh['regs'], 'positions': out, 'source': src(sh)} if out else None


def build_entry(sheets, group_label):
    """Construit le type pour un groupe. Renvoie (entrée, rapport) ; entrée None si l'import est impossible.
    rapport : liste de (niveau, message) avec niveau « erreur », « attention » ou « info »."""
    rap = []
    er = lambda m: rap.append(('erreur', m))
    at = lambda m: rap.append(('attention', m))
    inf = lambda m: rap.append(('info', m))
    g = (group_label or 'ALL').split(',')[0].strip()
    U, I = x_units(sheets), x_index(sheets)
    if g == 'ALL':
        b0 = x_basic(sheets, 'ALL')
        if b0 and b0['aircraft'] and not x_cg(sheets, 'ALL'):
            g = b0['aircraft'][0]['reg']          # feuilles propres à chaque immatriculation (ex. avion cargo)
    if not U or not I:
        er("Unités ou formule d'index introuvables : import impossible.")
        return None, rap
    if U['weight'] != 'kg':
        er("Les masses du fichier ne sont pas en kilogrammes : l'application ne convertit pas les masses. Import impossible.")
        return None, rap
    unit = U['length']
    plaus = 'm' if I['mac_length'] < 30 else 'in'
    if unit is None or unit != I['length_unit']:
        at(f"Unités de longueur contradictoires (feuille d'unités : {unit}, formule d'index : {I['length_unit']}). "
           f"La longueur de la corde ({I['mac_length']:g}) correspond à des « {plaus} » : cette unité est retenue. À vérifier.")
        unit = plaus
    elif unit != plaus:
        at(f"La longueur de corde ({I['mac_length']:g}) paraît incohérente avec l'unité « {unit} » : à vérifier.")
    f = LEN_FACTOR[unit]
    W = x_weights(sheets, g)
    if not W or not W['distinct_sets']:
        er("Masses limites (MZFW, MLW, MTOW) introuvables : import impossible.")
        return None, rap
    CG = x_cg(sheets, g)
    if not CG:
        er("Enveloppes de centrage introuvables : import impossible.")
        return None, rap
    B = x_basic(sheets, g)
    if not B or not B['aircraft']:
        er("Masses de base par appareil (feuille E5) introuvables : import impossible.")
        return None, rap
    H, FU, CAB, SAL = x_holds(sheets, g), x_fuel(sheets, g), x_cabin(sheets, g), x_saleable(sheets, g)
    STD, CREW = x_standards(sheets), x_crew(sheets, g)
    ref = W['rows'][0] if W['rows'] else None
    sets = W['distinct_sets']
    base = sets[0]
    if len(sets) > 1:
        inf(f"{len(sets)} jeux de masses limites dans le groupe : la limite propre à chaque immatriculation est appliquée.")
    for st in sets:
        if not (st['mzfw'] <= st['mtow'] and st['mlw'] <= st['mtow'] and st['mzfw'] <= st['mlw'] * 1.25):
            at(f"Masses limites incohérentes (MZFW {st['mzfw']}, MLW {st['mlw']}, MTOW {st['mtow']}) : à vérifier dans le fichier.")
    # enveloppes : cohérence %MAC <-> index
    ref_a, C, K, mac, lem = I['ref_arm'], I['C'], I['K'], I['mac_length'], I['lemac']
    worst = 0.0
    for t in CG['tables']:
        for ph, e in t['envelopes'].items():
            for side in ('fwd', 'aft'):
                for p in e[side]:
                    calc = p['weight_kg'] * ((lem + p['pct_mac'] / 100 * mac) - ref_a) / C + K
                    worst = max(worst, abs(calc - p['index']))
    if worst > 0.2:
        at(f"Enveloppes : écart maximal de {worst:.2f} entre l'index du fichier et l'index recalculé depuis le %MAC (le %MAC est utilisé).")
    if len(CG['tables']) > 1:
        at(f"{len(CG['tables'])} tables d'enveloppes dans l'AHM : la table « {CG['tables'][0]['name']} » est appliquée, "
           "les autres ne sont pas utilisées.")
    if not CG['tables'][0]['envelopes']['LANDING']['fwd']:
        inf("Pas de limite de centrage à l'atterrissage dans ce fichier : elle n'est pas contrôlée.")
    # masses de base
    for a in B['aircraft']:                  # %MAC et bras déduits de l'index quand le fichier ne publie que l'index
        if a['index'] is not None and (a['arm'] is None or a['pct_mac'] is None):
            arm_ = ref_a + C * (a['index'] - K) / a['basic_weight_kg']
            a['arm'] = round(arm_, 4) if a['arm'] is None else a['arm']
            a['pct_mac'] = round((arm_ - lem) / mac * 100, 1)
            a['derived'] = True
    bad = [a for a in B['aircraft'] if not (0 <= a['pct_mac'] <= 120)]
    if bad:
        at(f"{len(bad)} appareil(s) avec un %MAC de masse de base hors de 0 à 120 : à vérifier.")
    for a in B['aircraft']:
        if a['arm'] is not None and a['index'] is not None:
            calc = a['basic_weight_kg'] * (a['arm'] - ref_a) / C + K
            if abs(calc - a['index']) > 0.3:
                at(f"{a['reg']} : l'index de masse de base du fichier diffère de la formule ({a['index']} / {calc:.2f}).")
                break
    # carburant
    cum = (FU or {}).get('cumulative') or {}
    if (not cum.get('points') or len(cum['points']) < 2) and FU:
        dcum, why = derive_fuel_cumulative(FU, x_fuel_sequence(sheets, g))
        if dcum:
            cum = dcum
            FU['cumulative'] = dcum
            at("Effet cumulé du carburant non publié : table déduite de la séquence de remplissage (5.3) et des tables par réservoir. À vérifier.")
            tot = sum(tk.get('max_weight_kg') or 0 for tk in FU['tanks'] if abs((tk.get('density') or 0.8) - 0.8) < 0.006)
            if tot and abs(dcum['max_weight_kg'] - tot) > 0.02 * tot:
                at(f"Table carburant déduite : capacité {dcum['max_weight_kg']:.0f} kg différente de la somme des réservoirs ({tot:.0f} kg).")
        else:
            at(f"Effet cumulé du carburant introuvable ({why}).")
    if not cum.get('points') or len(cum['points']) < 2:
        at("Effet cumulé du carburant introuvable (le fichier donne des tables par réservoir sans ordre de remplissage) : "
           "le bras du carburant reste « à renseigner » dans « Données aéronef ».")
    else:
        ws_ = [p['weight_kg'] for p in cum['points']]
        if ws_ != sorted(ws_):
            at("Table carburant cumulée non croissante : à vérifier.")
    # soutes
    bulk = [e for e in (H or {}).get('entries', []) if e['mode'] == 'bulk' and e['values'].get('max_kg')]
    if not bulk:
        at("Aucune soute en vrac lue : à saisir dans « Données aéronef ».")
    # configurations
    cfgs = (SAL or {}).get('configurations', [])
    cfgs_ok = []
    for c in cfgs:
        if not c['sections']:
            at(f"Configuration « {c['name']} » : sections de cabine non lues, configuration ignorée.")
            continue
        if c['name_total'] and c['total'] != c['name_total']:
            at(f"Configuration « {c['name']} » : total des sièges lus ({c['total']}) différent de celui du nom ({c['name_total']}), ignorée.")
            continue
        cfgs_ok.append(c)
    if not cfgs_ok and not cfgs and not (CAB or {}).get('sections') and any('FREIGHTER' in (a.get('remark') or '').upper() or 'F' in (U.get('type') or '') for a in B['aircraft']) or (not cfgs_ok and not cfgs and not (CAB or {}).get('sections')):
        cfgs_ok = [{'name': 'CARGO', 'sections': [], 'total': 0}]
        inf("Aucune configuration de sièges dans le fichier : avion tout cargo (aucun passager).")
    if not cfgs_ok:
        er("Aucune configuration de sièges exploitable : import impossible.")
        return None, rap
    if CREW:
        pnt, pnc = CREW['pnt'], CREW['pnc']
    else:
        pnt, pnc = 2, None
        at("Composition d'équipage « STANDARD » introuvable : à saisir dans « Données aéronef ».")
    cw = (STD.get('crew_weights_kg') or {})
    if not cw:
        at("Masses standard d'équipage absentes : valeurs de 85 kg (PNT) et 75 kg (PNC) utilisées.")
    entry = {
        'units': {'weight': 'kg', 'length': unit, 'source': U['source']},
        'balance': {'reference_arm': ref_a, 'K': K, 'C': C, 'mac_length': mac, 'lemac': lem, 'source': I['source']},
        'limits': {'maximum_weights_kg': {'mzfw': base['mzfw'], 'mlw': base['mlw'], 'mtow': base['mtow'], 'mtaxi': base['mtaxi']},
                   'per_registration': {r['reg']: {'mzfw': r['mzfw'], 'mlw': r['mlw'], 'mtow': r['mtow'], 'mtaxi': r['mtaxi']}
                                        for r in W['rows']},
                   'lmc_limit_kg': W['lmc_limit_kg'], 'source': W['source']},
        'cg_envelopes': CG, 'holds': H, 'fuel': {'tanks': (FU or {}).get('tanks', []), 'cumulative': cum,
                                                   'density_default_kg_per_l': (FU or {}).get('tanks', [{}])[0].get('density') if (FU or {}).get('tanks') else None,
                                                   'source': (FU or {}).get('source')},
        'cabin': CAB, 'basic_weight': B,
        'saleable_configurations': {'configurations': [{'name': c['name'], 'sections': c['sections'], 'seats': c['total']} for c in cfgs_ok],
                                    'source': SAL['source']},
        'crew': {'pnt': pnt, 'pnc': pnc, 'kg_pnt': cw.get('flight_deck', 85), 'kg_pnc': cw.get('cabin', 75), 'source': (CREW or {}).get('source')},
        'standards': STD, 'group': group_label,
        'ideal_trim': x_ideal(sheets, g),
        'uld_positions': x_uld_positions(sheets, g),
    }
    if not entry['ideal_trim']:
        inf("Ligne de centrage idéale (feuille C7) introuvable : la répartition des bagages visera le milieu de l'enveloppe.")
    return entry, rap


# ----------------------------------------------------------------------------------------------------------------
# Effet cumulé du carburant déduit de la séquence de remplissage (feuille « Fuel », section 5.3)
# ----------------------------------------------------------------------------------------------------------------
def x_fuel_sequence(sheets, group):
    """Séquences de remplissage « Fuel Distribution » : [{name, density, max_volume, max_weight, steps:[{frm, to, tank}]}]."""
    out = []
    for sh in find_sheets(sheets, 'Fuel', group if group != 'ALL' else None):
        if not sh['title'].strip().endswith('Fuel') or 'Fuel Distribution' not in sh['txt']:
            continue
        cur = None
        for l in sh['txt'].split('\n'):
            m = re.match(r'\s*Distribution name:\s*(.+)$', l)
            if m:
                cur = {'name': m.group(1).strip(), 'density': None, 'max_volume': None, 'max_weight': None, 'steps': []}
                out.append(cur); continue
            if cur is None:
                continue
            m = re.match(r'\s*Maximum Volume:\s*(' + NUM + ')', l)
            if m:
                cur['max_volume'] = fnum(m.group(1)); continue
            m = re.match(r'\s*Fuel Density:\s*(' + NUM + ')', l)
            if m:
                cur['density'] = fnum(m.group(1)); continue
            m = re.match(r'\s*(?:Step\s+\d+|[A-Z][A-Z0-9&\. ]*?)\s+(\d+)\s+(\d+)\s+Vol\s+(.+?)\s+\d+\s+(?:\d+|#VALUE!)\s+\d\.\d+\s*$', l)
            if m:
                cur['steps'].append({'frm': float(m.group(1)), 'to': float(m.group(2)), 'tank': m.group(3).strip()})
    return [c for c in out if c['steps']]


def derive_fuel_cumulative(fuel, seqs):
    """Table cumulée {weight_kg, index} déduite des tables par réservoir et de la séquence de remplissage (volumes).
    Renvoie (cumulative | None, message)."""
    if not fuel or not fuel.get('tanks') or not seqs:
        return None, "séquence de remplissage ou tables par réservoir absentes"
    dens = sorted({tk['density'] for tk in fuel['tanks'] if tk.get('density')})
    d_tab = 0.8 if any(abs(d - 0.8) < 0.006 for d in dens) else (dens[0] if dens else None)
    tanks = {tk['name'].upper(): tk for tk in fuel['tanks']
             if len(tk['points']) >= 2 and (d_tab is None or not tk.get('density') or abs(tk['density'] - d_tab) < 0.006)}
    seq = next((s for s in seqs if d_tab and s['density'] and abs(s['density'] - d_tab) < 0.006), seqs[0])
    for st in seq['steps']:
        if st['tank'].upper() not in tanks:
            return None, f"réservoir « {st['tank']} » de la séquence absent des tables"

    def interp(tk, vol):
        pts = sorted((p['volume_l'], p['weight_kg'], p['index']) for p in tk['points'])
        pts = [(0.0, 0.0, 0.0)] + pts if pts[0][0] > 0 else pts
        if vol <= pts[0][0]:
            return pts[0][1], pts[0][2]
        if vol >= pts[-1][0]:
            return pts[-1][1], pts[-1][2]
        for (v0, w0, i0), (v1, w1, i1) in zip(pts, pts[1:]):
            if v0 <= vol <= v1:
                r = 0 if v1 == v0 else (vol - v0) / (v1 - v0)
                return w0 + r * (w1 - w0), i0 + r * (i1 - i0)
        return pts[-1][1], pts[-1][2]
    vmax = max(st['to'] for st in seq['steps'])
    cuts = sorted({0.0, vmax} | {st['frm'] for st in seq['steps']} | {st['to'] for st in seq['steps']} |
                  {vmax * k / 40 for k in range(1, 40)})
    pts = []
    for V in cuts:
        vols = {}
        for st in seq['steps']:
            part = max(0.0, min(V, st['to']) - st['frm'])
            vols[st['tank'].upper()] = vols.get(st['tank'].upper(), 0.0) + part
        W = I = 0.0
        for nm, v in vols.items():
            w, i = interp(tanks[nm], v)
            W += w
            I += i
        pts.append({'weight_kg': round(W, 1), 'index': round(I, 4)})
    return {'max_volume_l': vmax, 'max_weight_kg': pts[-1]['weight_kg'], 'points': pts,
            'derived_from': f"séquence « {seq['name']} » et tables par réservoir"}, None
