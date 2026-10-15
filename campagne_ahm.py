# -*- coding: utf-8 -*-
"""Campagne sur les AHM réels (Excel et PDF) : import de tous les groupes, conformité, comparaison Excel / PDF,
chaîne de groupes de soutes, construction DOW / DOI comparée aux tableaux de la compagnie.
Lancement : AHM_DIR=/chemin/des/fichiers python tests/campagne_ahm.py [sortie.json]   (les fichiers de la compagnie ne sont pas dans le dépôt)"""
import os, sys, glob, json, collections, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ahm_text as T, ahm_adapter as AD, dowbuild as DB, conformity as CF
import dowdoi

BASE = os.environ.get("AHM_DIR", "/mnt/user-data/uploads")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "campagne_ahm.json")


def read(path):
    s, _ = T.read_sheets(open(path, "rb").read(), os.path.basename(path))
    return s


def entries(sheets):
    out = {}
    for g in [g for g, _n in T.groups_of(sheets)] or ["ALL"]:
        try:
            out[g] = T.build_entry(sheets, g)
        except Exception as e:                                  # noqa
            out[g] = (None, [("erreur", "EXC " + repr(e)[:120])])
    return out


def dow_tables():
    reg = {}
    for p in sorted(glob.glob(BASE + "/**/*DOW*DOI*.pdf", recursive=True) + glob.glob(BASE + "/**/*DOWDOI*.pdf", recursive=True)):
        try:
            o, _n = dowdoi.parse(p)
        except Exception:                                       # noqa
            continue
        for r, v in o.items():
            reg.setdefault(r, {}).update(v)
    return reg


def dow_audit(ent, tabs):
    st = collections.Counter()
    bd = ent.get("dow_build")
    if not bd:
        return {"sans_construction": 1}
    bd = DB.from_record(bd)
    for reg in bd["basic"]:
        if reg not in tabs:
            st["immat_absente_des_tableaux"] += 1
            continue
        for wt, cr in tabs[reg].items():
            for crew, pans in cr.items():
                k = tuple(int(x) for x in crew.split("/"))
                for pc, (dw, di) in pans.items():
                    r = DB.compute(bd, reg, k, pc, wt)
                    if r is None:
                        st["non_calculable"] += 1
                        continue
                    st["dow_ok" if abs(dw - r[0]) < 0.5 else "dow_ecart"] += 1
                    st["doi_ok" if abs(di - r[1]) <= 0.3001 else "doi_ecart"] += 1
    return dict(st)


def main():
    t0 = time.time()
    tabs = dow_tables()
    rep = {"dow_tables_immat": len(tabs), "fichiers": {}}
    for xp in sorted(glob.glob(BASE + "/**/*AHM565*.xlsx", recursive=True)):
        d = os.path.dirname(xp)
        pdfs = [p for p in glob.glob(d + "/*AHM565*.pdf")]
        nm = os.path.basename(xp)
        fr = {"groupes": {}}
        sx = read(xp)
        ex = entries(sx)
        sp = read(pdfs[0]) if pdfs else None
        ep = entries(sp) if sp else {}
        for g, (e, rap) in ex.items():
            gr = {"erreurs": [m for lv, m in rap if lv == "erreur"], "attention": sum(1 for lv, _ in rap if lv == "attention")}
            if e:
                try:
                    ac, rap2 = AD.to_app_record(e, "client", {"label": nm})
                    gr["adapter"] = "ok" if ac else "refus"
                    gr["soutes"] = len(ac["cargo_comps"]) if ac else 0
                    gr["avec_chaine_groupes"] = sum(1 for c in (ac or {}).get("cargo_comps", []) if len(c.get("groupes") or []) > 1)
                except Exception as exc:                          # noqa
                    gr["adapter"] = "EXC " + repr(exc)[:100]
                st = collections.Counter(etat for _r, etat, _d in CF.check(e, rap))
                gr["conformite"] = dict(st)
                gr["dow"] = dow_audit(e, tabs)
                if pdfs and g in ep and ep[g][0]:
                    df = CF.diff(e, ep[g][0])
                    gr["ecarts_excel_pdf"] = len(df)
                    gr["ecarts_exemples"] = [(a, b, str(c)[:30], str(dd)[:30]) for a, b, c, dd in df[:5]]
                elif pdfs:
                    gr["ecarts_excel_pdf"] = "groupe absent du PDF"
            fr["groupes"][g] = gr
        rep["fichiers"][nm] = fr
        print(nm, len(ex), "groupes", round(time.time() - t0), "s", flush=True)
        json.dump(rep, open(OUT, "w"), ensure_ascii=False, indent=1, default=str)
    print("FIN", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
