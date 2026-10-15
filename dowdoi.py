"""Lecture des tableaux THY « Dry Operating Weight and Index » (PDF) -> {immat: {eau: {equipage: {pantry: (DOW, DOI)}}}}."""
import re, pymupdf

REG = re.compile(r'^TC-[A-Z]{3}$')
CREW = re.compile(r'^\d+\s*/\s*\d+$')


def parse(path):
    d = pymupdf.open(path)
    out, notes = {}, []
    cur = None
    for pn, pg in enumerate(d, 1):
        W = [(w[0], w[1], w[2], w[3], w[4]) for w in pg.get_text('words')]
        txt = pg.get_text()
        # immatriculation de la page : premier TC-xxx sous l'entête (page de tableaux)
        regs = [w for w in W if REG.match(w[4])]
        if 'EFFECTIVITY LIST' in txt:
            continue
        if regs:
            cur = sorted(regs, key=lambda w: w[1])[0][4]
        if cur is None:
            continue
        # titres d'eau : jeton avant POTABLE/POT. -> pourcentage
        waters = []
        for i, w in enumerate(W):
            if w[4].upper().rstrip('.') in ('POTABLE', 'POT') and i >= 1 and i + 1 < len(W) and W[i + 1][4].upper().startswith('WATER'):
                tk = W[i - 1][4]
                m = re.fullmatch(r'%?(\d+(?:\.\d+)?)%?', tk)
                m2 = re.fullmatch(r'(\d+)/(\d+)', tk)
                if m2:
                    pc = 100.0 * int(m2.group(1)) / int(m2.group(2))
                elif m:
                    pc = float(m.group(1))
                else:
                    continue
                waters.append((round(pc, 1), (w[0] + w[2]) / 2, w[1]))
        # tokens numériques
        ints = [w for w in W if re.fullmatch(r'\d{5,6}', w[4])]
        decs = [(w[0], w[1], w[2], w[3], w[4].replace(',', '.')) for w in W if re.fullmatch(r'-?\d{1,3}[.,]\d', w[4])]
        crews = []
        # étiquettes d'équipage "2 / 4" : tokens '2','/','4' ou '2/4'
        for i, w in enumerate(W):
            if re.fullmatch(r'\d+', w[4]) and i + 2 < len(W) and W[i + 1][4] == '/' and re.fullmatch(r'\d+', W[i + 2][4]) \
               and abs(W[i + 1][1] - w[1]) < 4:
                crews.append((f'{w[4]}/{W[i+2][4]}', w[0], (w[1] + w[3]) / 2))
            elif CREW.match(w[4]):
                crews.append((re.sub(r'\s', '', w[4]), w[0], (w[1] + w[3]) / 2))
        # en-têtes de pantry : lettres isolées au-dessus de chaque bloc
        hdr = [w for w in W if re.fullmatch(r'[A-Z]', w[4])]
        for it in ints:
            cx = (it[0] + it[2]) / 2
            cy = (it[1] + it[3]) / 2
            # DOI : décimal le plus proche en dessous
            c = [x for x in decs if abs((x[0] + x[2]) / 2 - cx) < 12 and 0 < x[1] - it[1] < 22]
            if not c:
                notes.append((cur, pn, 'DOI absent pour %s' % it[4])); continue
            doi = float(min(c, key=lambda x: x[1] - it[1])[4])
            # équipage : étiquette à gauche, même ligne, la plus proche
            dm = [x for x in decs if abs((x[0] + x[2]) / 2 - cx) < 12 and 0 < x[1] - it[1] < 22]
            mid = (it[1] + min(dm, key=lambda x: x[1] - it[1])[3]) / 2
            cr = [x for x in crews if x[1] < it[0] and abs(x[2] - mid) < 9]
            if cr:
                cr = [min(cr, key=lambda x: (abs(x[2] - mid), -x[1]))]
            if not cr:
                notes.append((cur, pn, 'équipage non trouvé pour %s' % it[4])); continue
            crew = max(cr, key=lambda x: x[1])[0]
            # pantry : lettre en-tête au-dessus la plus proche, même colonne
            h = [x for x in hdr if abs((x[0] + x[2]) / 2 - cx) < 20 and x[1] < it[1]]
            if not h:
                notes.append((cur, pn, 'pantry non trouvé pour %s' % it[4])); continue
            pan = max(h, key=lambda x: x[1])
            # eau : titre au-dessus le plus proche en ordonnée, puis le plus proche en abscisse
            wt = [x for x in waters if x[2] < it[1]]
            if wt:
                ymax = max(x[2] for x in wt)
                wt = [x for x in wt if abs(x[2] - ymax) < 6]
                wt = [min(wt, key=lambda x: abs(x[1] - cx))]
            if not wt:
                notes.append((cur, pn, 'eau non trouvée pour %s' % it[4])); continue
            water = wt[0][0]
            key = out.setdefault(cur, {}).setdefault(water, {}).setdefault(crew, {})
            if pan[4] in key and key[pan[4]] != (int(it[4]), doi):
                notes.append((cur, pn, 'valeurs concurrentes %s/%s/%s %s vs %s' % (water, crew, pan[4], key[pan[4]], (int(it[4]), doi))))
            key[pan[4]] = (int(it[4]), doi)
    return out, notes


if __name__ == '__main__':
    import sys, json
    o, n = parse(sys.argv[1])
    print(len(o), 'immat;', sum(len(c) for r in o.values() for w in r.values() for c in w.values()), 'valeurs;', len(n), 'notes')
    for k, v in list(o.items())[:2]:
        print(k, {w: len(c) for w, c in v.items()})
    for x in n[:10]:
        print(x)
