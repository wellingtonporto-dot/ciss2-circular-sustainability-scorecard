#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CiSS 2.0 - Fase 3: concordancia entre codificadores nas rubricas de governanca (GV1, GV2, GV3, GV5).

Compara a ficha do segundo codificador (planilha 'data/Dupla_codificacao_GV.xlsx', aba 'Ficha')
com a codificacao principal (gv.json, campo 'c' = 4 criterios 0/1) e calcula:
  * concordancia percentual (por criterio, indicador e total);
  * kappa de Cohen e AC1 de Gwet nos julgamentos binarios (criterio atendido / nao atendido);
  * coeficiente de correlacao intraclasse (ICC) nas pontuacoes por indicador (0-100):
    ICC(2,1) concordancia absoluta [principal] e ICC(3,1) consistencia;
  * intervalos de 95% por bootstrap em blocos (a unidade de reamostragem e empresa x indicador).

Uso:
  python3 concordancia_gv.py --selftest                      # testes com valores de referencia
  python3 concordancia_gv.py --simulate 0.10                 # ficha simulada (10% de discordancia) e analise
  python3 concordancia_gv.py FICHA.xlsx [--gv gv.json] [--out PASTA]   # analise real

Somente biblioteca padrao + openpyxl. Semente fixa (20261120) como no restante da Fase 3.
"""
import argparse
import csv
import json
import math
import os
import random
import sys

import openpyxl

SEED = 20261120
IND = ["GV1", "GV2", "GV3", "GV5"]
NB = 5000  # replicas bootstrap


# --------------------------------------------------------------------------- metricas
def cohen_kappa(a, b):
    """Retorna (kappa, po, pe). kappa=None se indefinido (pe == 1)."""
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    if abs(1 - pe) < 1e-12:
        return None, po, pe
    return (po - pe) / (1 - pe), po, pe


def gwet_ac1(a, b):
    """AC1 de Gwet para duas categorias (robusto ao 'paradoxo do kappa')."""
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pi = (sum(a) + sum(b)) / (2 * n)
    pe = 2 * pi * (1 - pi)
    if abs(1 - pe) < 1e-12:
        return None
    return (po - pe) / (1 - pe)


def icc_all(X):
    """X: lista de linhas (alvos) x colunas (avaliadores). Retorna dict ICC(1,1), ICC(2,1), ICC(3,1)
    segundo Shrout & Fleiss (1979). Valores None quando indefinidos."""
    n, k = len(X), len(X[0])
    g = sum(sum(r) for r in X) / (n * k)
    rm = [sum(r) / k for r in X]
    cm = [sum(X[i][j] for i in range(n)) / n for j in range(k)]
    ssr = k * sum((m - g) ** 2 for m in rm)
    ssc = n * sum((m - g) ** 2 for m in cm)
    sst = sum((x - g) ** 2 for r in X for x in r)
    sse = sst - ssr - ssc
    msr = ssr / (n - 1)
    msc = ssc / (k - 1)
    mse = sse / ((n - 1) * (k - 1))
    msw = (ssc + sse) / (n * (k - 1))

    def ratio(num, den):
        return None if abs(den) < 1e-12 else num / den

    return {
        "ICC1": ratio(msr - msw, msr + (k - 1) * msw),
        "ICC2": ratio(msr - mse, msr + (k - 1) * mse + k * (msc - mse) / n),
        "ICC3": ratio(msr - mse, msr + (k - 1) * mse),
    }


def percentile(vals, q):
    s = sorted(vals)
    if not s:
        return None
    pos = q * (len(s) - 1)
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def boot_ci(units, stat, nb=NB, seed=SEED):
    """Bootstrap em blocos: 'units' e uma lista de blocos; 'stat' recebe a lista reamostrada."""
    rng = random.Random(seed)
    out = []
    n = len(units)
    for _ in range(nb):
        samp = [units[rng.randrange(n)] for _ in range(n)]
        v = stat(samp)
        if v is not None:
            out.append(v)
    if len(out) < 0.8 * nb:
        return None, None, len(out)
    return percentile(out, 0.025), percentile(out, 0.975), len(out)


# --------------------------------------------------------------------------- leitura
def to_bin(v, where):
    if v is None or (isinstance(v, str) and v.strip() == ""):
        raise ValueError(f"celula vazia em {where}")
    s = str(v).strip().replace(",", ".")
    try:
        x = float(s)
    except ValueError:
        raise ValueError(f"valor nao numerico '{v}' em {where} (use 25 ou 0)")
    if x in (25.0, 1.0):
        return 1
    if x == 0.0:
        return 0
    raise ValueError(f"valor '{v}' invalido em {where} (use 25 ou 0)")


def load_ficha(path):
    wb = openpyxl.load_workbook(path, data_only=False)
    ws = wb["Ficha"]
    crit_txt = {}
    if "Critérios" in wb.sheetnames:
        wc = wb["Critérios"]
        hdr = [c.value for c in wc[1]]
        tem_nome = len(hdr) > 1 and str(hdr[1]).strip().lower() == "nome"
        for r in wc.iter_rows(min_row=2, values_only=True):
            if r[0]:
                if tem_nome:
                    crit_txt[r[0]] = {"nome": r[1], "c": list(r[2:6])}
                else:  # ficha reexportada sem a coluna Nome
                    crit_txt[r[0]] = {"nome": "", "c": list(r[1:5])}
    rows, erros = [], []
    for i, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if r[0] in (None, ""):
            continue
        emp, arq, ind = str(r[0]).strip(), r[1], str(r[2]).strip()
        c = []
        for j in range(4):
            try:
                c.append(to_bin(r[3 + j], f"linha {i} ({emp} {ind}) critério {j + 1}"))
            except ValueError as e:
                erros.append(str(e))
                c.append(None)
        rows.append({"emp": emp, "ind": ind, "c": c, "pag": r[8] or "", "obs": r[9] or ""})
    return rows, crit_txt, erros


def build_pairs(rows, gv):
    unidades = []
    faltas = []
    for r in rows:
        if r["emp"] not in gv or r["ind"] not in gv[r["emp"]]:
            faltas.append(f"{r['emp']} {r['ind']} ausente em gv.json")
            continue
        p = gv[r["emp"]][r["ind"]]
        unidades.append({
            "emp": r["emp"], "ind": r["ind"],
            "c1": [int(x) for x in p["c"]], "c2": r["c"],
            "pag1": p.get("pag", ""), "nota1": p.get("nota", ""),
            "pag2": r["pag"], "obs2": r["obs"],
        })
    return unidades, faltas


# --------------------------------------------------------------------------- analise
def analyze(unidades, crit_txt):
    def flat(us):
        a = [x for u in us for x in u["c1"]]
        b = [x for u in us for x in u["c2"]]
        return a, b

    def kap(us):
        a, b = flat(us)
        return cohen_kappa(a, b)[0]

    def ac1(us):
        a, b = flat(us)
        return gwet_ac1(a, b)

    def icc2(us):
        X = [[25 * sum(u["c1"]), 25 * sum(u["c2"])] for u in us]
        return icc_all(X)["ICC2"]

    def icc3(us):
        X = [[25 * sum(u["c1"]), 25 * sum(u["c2"])] for u in us]
        return icc_all(X)["ICC3"]

    res = {"n_unidades": len(unidades), "n_julgamentos": 4 * len(unidades)}
    a, b = flat(unidades)
    k, po, pe = cohen_kappa(a, b)
    res["geral"] = {
        "pct_concordancia": 100 * po, "kappa": k, "ac1": gwet_ac1(a, b),
        "prevalencia_c1": sum(a) / len(a), "prevalencia_c2": sum(b) / len(b),
        "n_discordancias": sum(x != y for x, y in zip(a, b)),
    }
    lo, hi, nv = boot_ci(unidades, kap)
    res["geral"]["kappa_ic95"] = [lo, hi]
    lo, hi, nv = boot_ci(unidades, ac1)
    res["geral"]["ac1_ic95"] = [lo, hi]

    X = [[25 * sum(u["c1"]), 25 * sum(u["c2"])] for u in unidades]
    ic = icc_all(X)
    res["icc"] = {"ICC2_1": ic["ICC2"], "ICC3_1": ic["ICC3"], "n": len(X),
                  "ICC2_1_ic95": list(boot_ci(unidades, icc2)[:2]),
                  "ICC3_1_ic95": list(boot_ci(unidades, icc3)[:2]),
                  "dif_media_abs_pontos": sum(abs(x[0] - x[1]) for x in X) / len(X),
                  "pct_pontuacoes_identicas": 100 * sum(x[0] == x[1] for x in X) / len(X)}

    res["por_indicador"] = {}
    for ind in IND:
        us = [u for u in unidades if u["ind"] == ind]
        if not us:
            continue
        a_, b_ = flat(us)
        k_, po_, _ = cohen_kappa(a_, b_)
        X_ = [[25 * sum(u["c1"]), 25 * sum(u["c2"])] for u in us]
        res["por_indicador"][ind] = {
            "n_unidades": len(us), "pct_concordancia": 100 * po_, "kappa": k_,
            "ac1": gwet_ac1(a_, b_), "ICC2_1": icc_all(X_)["ICC2"] if len(us) > 2 else None,
            "n_discordancias": sum(x != y for x, y in zip(a_, b_)),
        }
    res["por_criterio"] = {}
    for ind in IND:
        for j in range(4):
            us = [u for u in unidades if u["ind"] == ind]
            if not us:
                continue
            ag = sum(u["c1"][j] == u["c2"][j] for u in us)
            res["por_criterio"][f"{ind}-C{j + 1}"] = {"concordam": ag, "n": len(us),
                                                       "pct": 100 * ag / len(us)}
    # pontuacao GV por empresa (media dos 4 indicadores) - exploratorio (n pequeno)
    emps = []
    for u in unidades:
        if u["emp"] not in emps:
            emps.append(u["emp"])
    por_emp = []
    for e in emps:
        us = [u for u in unidades if u["emp"] == e]
        por_emp.append({"empresa": e,
                        "GV_cod1": sum(25 * sum(u["c1"]) for u in us) / len(us),
                        "GV_cod2": sum(25 * sum(u["c2"]) for u in us) / len(us)})
    res["por_empresa_exploratorio"] = por_emp
    if len(por_emp) > 2:
        res["por_empresa_exploratorio_ICC2_1"] = icc_all(
            [[p["GV_cod1"], p["GV_cod2"]] for p in por_emp])["ICC2"]

    disc = []
    for u in unidades:
        for j in range(4):
            if u["c1"][j] != u["c2"][j]:
                tx = crit_txt.get(u["ind"], {}).get("c", [""] * 4)[j]
                disc.append({"empresa": u["emp"], "indicador": u["ind"], "criterio": j + 1,
                             "texto_criterio": tx, "cod1": 25 * u["c1"][j], "cod2": 25 * u["c2"][j],
                             "paginas_cod1": u["pag1"], "nota_cod1": u["nota1"],
                             "paginas_cod2": u["pag2"], "obs_cod2": u["obs2"]})
    res["discordancias"] = disc
    return res


# --------------------------------------------------------------------------- relatorio
def f(x, d=2):
    if x is None:
        return "n/d"
    if abs(x) < 0.5 * 10 ** (-d):
        x = 0.0
    return f"{x:.{d}f}"


def lk(k):
    if k is None:
        return "indefinido"
    for lim, lab in [(0.8, "quase perfeita"), (0.6, "substancial"), (0.4, "moderada"),
                     (0.2, "razoável")]:
        if k > lim:
            return lab
    return "fraca"


def kk(k):
    if k is None:
        return "undefined"
    for lim, lab in [(0.8, "almost perfect"), (0.6, "substantial"), (0.4, "moderate"), (0.2, "fair")]:
        if k > lim:
            return lab
    return "slight"


def icl_pt(v):
    if v is None:
        return "indefinida"
    return "excelente" if v > 0.9 else "boa" if v > 0.75 else "moderada" if v > 0.5 else "fraca"


def icl_en(v):
    if v is None:
        return "undefined"
    return "excellent" if v > 0.9 else "good" if v > 0.75 else "moderate" if v > 0.5 else "poor"


def write_outputs(res, out):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "concordancia_GV_resultados.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(out, "concordancia_GV_discordancias.csv"), "w", encoding="utf-8-sig",
              newline="") as fh:
        cols = ["empresa", "indicador", "criterio", "texto_criterio", "cod1", "cod2", "paginas_cod1",
                "nota_cod1", "paginas_cod2", "obs_cod2"]
        w = csv.DictWriter(fh, fieldnames=cols, delimiter=";")
        w.writeheader()
        for d in res["discordancias"]:
            w.writerow({c: d[c] for c in cols})

    g, ic = res["geral"], res["icc"]
    L = []
    L.append("# Concordância entre codificadores – rubricas de governança (Fase 3)\n")
    L.append(f"Unidades: {res['n_unidades']} (empresa × indicador); julgamentos binários: "
             f"{res['n_julgamentos']}. Discordâncias: {g['n_discordancias']}.\n")
    L.append("## Nível do critério (0/25)\n")
    L.append("| Medida | Valor | IC 95% (bootstrap em blocos) |\n|---|---|---|")
    L.append(f"| Concordância percentual | {f(g['pct_concordancia'], 1)}% | – |")
    L.append(f"| Kappa de Cohen | {f(g['kappa'])} ({lk(g['kappa'])}) | {f(g['kappa_ic95'][0])} a {f(g['kappa_ic95'][1])} |")
    L.append(f"| AC1 de Gwet | {f(g['ac1'])} | {f(g['ac1_ic95'][0])} a {f(g['ac1_ic95'][1])} |")
    L.append(f"\nPrevalência de 'atendido': cod. 1 = {f(100 * g['prevalencia_c1'], 0)}%; "
             f"cod. 2 = {f(100 * g['prevalencia_c2'], 0)}%.\n")
    L.append("## Pontuações por indicador (0–100)\n")
    L.append("| Medida | Valor | IC 95% |\n|---|---|---|")
    L.append(f"| ICC(2,1) – concordância absoluta | {f(ic['ICC2_1'])} ({icl_pt(ic['ICC2_1'])}) | {f(ic['ICC2_1_ic95'][0])} a {f(ic['ICC2_1_ic95'][1])} |")
    L.append(f"| ICC(3,1) – consistência | {f(ic['ICC3_1'])} | {f(ic['ICC3_1_ic95'][0])} a {f(ic['ICC3_1_ic95'][1])} |")
    L.append(f"\nPontuações idênticas: {f(ic['pct_pontuacoes_identicas'], 0)}%; diferença absoluta média: "
             f"{f(ic['dif_media_abs_pontos'], 1)} pontos.\n")
    L.append("## Por indicador\n")
    L.append("| Indicador | n | % concord. | Kappa | AC1 | ICC(2,1) | Discordâncias |\n|---|---|---|---|---|---|---|")
    for k_, v in res["por_indicador"].items():
        L.append(f"| {k_} | {v['n_unidades']} | {f(v['pct_concordancia'], 0)} | {f(v['kappa'])} | {f(v['ac1'])} | {f(v['ICC2_1'])} | {v['n_discordancias']} |")
    L.append("\n## Por critério (concordância em n empresas)\n")
    L.append("| Critério | Concordam | % |\n|---|---|---|")
    for k_, v in res["por_criterio"].items():
        L.append(f"| {k_} | {v['concordam']}/{v['n']} | {f(v['pct'], 0)} |")
    L.append("\n## Pontuação GV por empresa (exploratório; n pequeno)\n")
    L.append("| Empresa | GV cod. 1 | GV cod. 2 |\n|---|---|---|")
    for p in res["por_empresa_exploratorio"]:
        L.append(f"| {p['empresa']} | {f(p['GV_cod1'], 1)} | {f(p['GV_cod2'], 1)} |")
    if "por_empresa_exploratorio_ICC2_1" in res:
        L.append(f"\nICC(2,1) por empresa: {f(res['por_empresa_exploratorio_ICC2_1'])} (n = {len(res['por_empresa_exploratorio'])}; apenas indicativo).")
    L.append("\n## Discordâncias\n")
    if not res["discordancias"]:
        L.append("Nenhuma.")
    for d in res["discordancias"]:
        L.append(f"- {d['empresa']} {d['indicador']}-C{d['criterio']} (cod.1 = {d['cod1']}, cod.2 = {d['cod2']}): {d['texto_criterio']}")
    L.append("\n## Texto-modelo para a Seção 3.3.3 (conferir números antes de usar)\n")
    ki = f"{f(g['kappa_ic95'][0])}–{f(g['kappa_ic95'][1])}"
    ii = f"{f(ic['ICC2_1_ic95'][0])}–{f(ic['ICC2_1_ic95'][1])}"
    L.append(f"**PT:** A concordância entre os dois codificadores foi de {f(g['pct_concordancia'], 1)}% nos "
             f"{res['n_julgamentos']} julgamentos de critério (kappa de Cohen = {f(g['kappa'])}, IC 95% {ki}, "
             f"concordância {lk(g['kappa'])}; AC1 de Gwet = {f(g['ac1'])}). Nas pontuações por indicador "
             f"(n = {ic['n']}), o ICC(2,1) foi {f(ic['ICC2_1'])} (IC 95% {ii}), classificado como {icl_pt(ic['ICC2_1'])}. "
             f"Houve {g['n_discordancias']} discordâncias, concentradas em: [preencher a partir da lista acima].\n")
    L.append(f"**EN:** Agreement between the two coders was {f(g['pct_concordancia'], 1)}% across the "
             f"{res['n_julgamentos']} criterion-level judgments (Cohen's kappa = {f(g['kappa'])}, 95% CI {ki}, "
             f"{kk(g['kappa'])} agreement; Gwet's AC1 = {f(g['ac1'])}). For indicator scores (n = {ic['n']}), "
             f"ICC(2,1) was {f(ic['ICC2_1'])} (95% CI {ii}), rated {icl_en(ic['ICC2_1'])}. "
             f"There were {g['n_discordancias']} disagreements, concentrated in: [fill in from the list above].\n")
    L.append("Notas metodológicas: intervalos por bootstrap em blocos (empresa × indicador, "
             f"{NB} réplicas, semente {SEED}); com n = {res['n_unidades']} unidades os intervalos são amplos. "
             "A concordância não altera a codificação principal; apenas qualifica sua confiabilidade.\n")
    with open(os.path.join(out, "concordancia_GV_resumo.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    return "\n".join(L)


# --------------------------------------------------------------------------- testes e simulacao
def selftest():
    ok = True

    def chk(nome, got, want, tol=0.006):
        nonlocal ok
        good = got is not None and abs(got - want) <= tol
        ok &= good
        print(f"[{'OK' if good else 'FALHA'}] {nome}: {f(got, 4)} (esperado {want})")

    # kappa: tabela 2x2 (20, 5 / 10, 15) -> po=.70, pe=.50, kappa=.40
    a = [1] * 20 + [1] * 5 + [0] * 10 + [0] * 15
    b = [1] * 20 + [0] * 5 + [1] * 10 + [0] * 15
    chk("kappa 2x2", cohen_kappa(a, b)[0], 0.40)
    chk("kappa identicos", cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0])[0], 1.0)
    chk("kappa so acaso (simetrico)", cohen_kappa([1, 1, 0, 0], [1, 0, 1, 0])[0], 0.0)
    print("[OK] kappa indefinido quando tudo igual a 0:", cohen_kappa([0] * 5, [0] * 5)[0] is None)
    # ICC: Shrout & Fleiss (1979), 6 alvos x 4 avaliadores
    X = [[9, 2, 5, 8], [6, 1, 3, 2], [8, 4, 6, 8], [7, 1, 2, 6], [10, 5, 6, 9], [6, 2, 4, 7]]
    r = icc_all(X)
    chk("ICC(1,1) S&F", r["ICC1"], 0.17)
    chk("ICC(2,1) S&F", r["ICC2"], 0.29)
    chk("ICC(3,1) S&F", r["ICC3"], 0.71)
    chk("ICC identicos", icc_all([[0, 0], [25, 25], [50, 50], [100, 100]])["ICC2"], 1.0)
    # AC1: caso sem discordancia
    chk("AC1 identicos", gwet_ac1([1, 0, 1, 1], [1, 0, 1, 1]), 1.0)
    return ok


def simulate(p, template, gv_path, out_ficha):
    gv = json.load(open(gv_path, encoding="utf-8"))
    wb = openpyxl.load_workbook(template)
    ws = wb["Ficha"]
    rng = random.Random(SEED + 1)
    flips = 0
    for r in range(2, ws.max_row + 1):
        emp, ind = ws.cell(r, 1).value, ws.cell(r, 3).value
        if not emp:
            continue
        c = gv[emp][ind]["c"]
        for j in range(4):
            v = c[j]
            if rng.random() < p:
                v, flips = 1 - v, flips + 1
            ws.cell(r, 4 + j).value = 25 * v
        ws.cell(r, 9).value = "p. simulada"
    wb.save(out_ficha)
    return flips


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ficha", nargs="?", help="planilha preenchida pelo segundo codificador")
    ap.add_argument("--gv", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "gv.json"))
    ap.add_argument("--out", default=None, help="pasta de saida (padrao: pasta da ficha)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--simulate", type=float, metavar="P", help="gera ficha simulada com prob. P de inversao")
    ap.add_argument("--template", default="data/Dupla_codificacao_GV.xlsx")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(0 if selftest() else 1)

    ficha = a.ficha
    out = a.out
    if a.simulate is not None:
        ficha = "/tmp/ficha_simulada.xlsx"
        out = out or "/tmp/conc_simulada"
        n = simulate(a.simulate, a.template, a.gv, ficha)
        print(f"Ficha simulada criada com {n} inversoes (p = {a.simulate}).")
    if not ficha:
        ap.error("informe a ficha ou use --selftest / --simulate")
    out = out or os.path.dirname(os.path.abspath(ficha))

    gv = json.load(open(a.gv, encoding="utf-8"))
    rows, crit_txt, erros = load_ficha(ficha)
    if erros:
        print("PROBLEMAS NA FICHA (corrija antes de analisar):")
        for e in erros:
            print(" -", e)
        sys.exit(2)
    unidades, faltas = build_pairs(rows, gv)
    if faltas:
        print("PROBLEMAS DE CORRESPONDENCIA com gv.json:")
        for e in faltas:
            print(" -", e)
        sys.exit(2)
    if len(unidades) != 24:
        print(f"AVISO: {len(unidades)} unidades lidas (esperado 24 = 6 empresas x 4 indicadores).")
    res = analyze(unidades, crit_txt)
    print(write_outputs(res, out))
    print(f"\nArquivos gerados em: {out}")


if __name__ == "__main__":
    main()
