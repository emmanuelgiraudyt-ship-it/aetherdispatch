"""Liste THY « Flight - Pantry code list » : (départ, arrivée) -> codes de pantry, avec la rubrique de la liste.
Lecture par lignes de mots : départ, arrivée (un « * » est un renvoi de la liste), code, description."""
import re, pymupdf


def parse(path):
    d = pymupdf.open(path)
    recs, notes = [], []
    for pn, pg in enumerate(d, 1):
        rows = {}
        for w in pg.get_text("words"):
            rows.setdefault(round((w[1] + w[3]) / 2 / 3), []).append(w)
        for k in sorted(rows):
            tk = sorted(rows[k], key=lambda w: w[0])
            t = [w[4] for w in tk]
            if len(t) >= 4 and re.fullmatch(r"[A-Z]{3}", t[0]) and re.fullmatch(r"[A-Z]{3}\*{0,2}", t[1]) and re.fullmatch(r"[A-Z0-9]{1,3}\*{0,2}", t[2]):
                desc = " ".join(t[3:])
                if re.search(r"FLIGHTS?$", desc):
                    recs.append({"dep": t[0], "arr": t[1].rstrip("*"), "code": t[2].rstrip("*"), "desc": desc,
                                 "renvoi": t[1].endswith("*") or t[2].endswith("*"), "page": pn})
                    continue
            if t and re.fullmatch(r"[A-Z]{3}", t[0]) and len(t) >= 3 and pn >= 4:
                notes.append((pn, t))
    return recs, notes


def by_route(recs):
    out = {}
    for r in recs:
        out.setdefault((r["dep"], r["arr"]), []).append(r)
    return out


if __name__ == "__main__":
    import sys, collections
    r, n = parse(sys.argv[1])
    print(len(r), "lignes;", len(n), "non lues;", sum(1 for x in r if x["renvoi"]), "avec renvoi")
    print(collections.Counter(x["code"] for x in r))
    amb = {k: v for k, v in by_route(r).items() if len({x["code"] for x in v}) > 1}
    print(len(by_route(r)), "liaisons;", len(amb), "avec plusieurs codes")
    for k in list(amb)[:6]:
        print(k, [(x["code"], x["desc"]) for x in amb[k]])
    for x in n[:8]:
        print(x)
