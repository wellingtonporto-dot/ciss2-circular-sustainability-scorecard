"""Sensibilidade do CiSS a codificacao da governanca: recalcula o CiSS das 22 empresas usando a
codificacao do segundo codificador nas 6 empresas duplamente codificadas.
Cenarios: S2 = o segundo codificador substitui a 1a codificacao; MIN = criterio so vale se ambos pontuaram;
MAX = criterio vale se qualquer um pontuou. Nao altera resultados.json.
Uso: python3 sens_gv.py [FICHA.xlsx]   (padrao: data/Dupla_codificacao_GV.xlsx; saida em agreement/)"""
import os, sys, json, copy, numpy as np
import analise as A
from ciss import spearman
from concordancia_gv import load_ficha, build_pairs
ficha = sys.argv[1] if len(sys.argv) > 1 else "data/Dupla_codificacao_GV.xlsx"
gv0 = copy.deepcopy(A.gv)
rows, _, erros = load_ficha(ficha); assert not erros
un, faltas = build_pairs(rows, gv0); assert not faltas
def rodar(gv):
    A.gv = gv
    R = A.raw(); N = A.normalize(R); S = A.scores(N, np.ones(len(A.IND))); C = A.cissvec(S)
    gvidx = [A.IND.index(k) for k in A.DIM["GV"]]
    M = N[:, gvidx]
    return R, N, S, C, M
R0, N0, S0, C0, M0 = rodar(gv0)
def cenario(f):
    g = copy.deepcopy(gv0)
    for u in un:
        c = [int(f(a, b)) for a, b in zip(u["c1"], u["c2"])]
        g[u["emp"]][u["ind"]]["c"] = c; g[u["emp"]][u["ind"]]["total"] = sum(c)
    return g
out = {"principal_CiSS": C0.tolist(), "empresas": A.EMP, "cenarios": {}}
gvs = [k for k in A.DIM["GV"]]
for nome, f in (("segundo_codificador", lambda a, b: b), ("minimo", lambda a, b: min(a, b)), ("maximo", lambda a, b: max(a, b))):
    g = cenario(f); R, N, S, C, M = rodar(g)
    rk0 = (-C0).argsort().argsort() + 1; rk = (-C).argsort().argsort() + 1
    ok = ~np.isnan(M).any(axis=1)
    d = {"spearman_vs_principal": spearman(C0, C), "delta_max": float(np.nanmax(np.abs(C - C0))),
         "delta_medio_abs": float(np.nanmean(np.abs(C - C0))),
         "empresas_com_delta_gt_0_05": [A.EMP[i] for i in range(len(A.EMP)) if abs(C[i] - C0[i]) > 0.05],
         "empresas_mudam_posto": int((rk0 != rk).sum()), "max_mudanca_posto": int(np.abs(rk0 - rk).max()),
         "alfa_GV": A.cronbach(M[ok]), "omega_GV": A.omega(M[ok]),
         "GV_media_22": float(np.nanmean(S[:, 2])), "GV_media_principal": float(np.nanmean(S0[:, 2])),
         "CiSS": C.tolist()}
    out["cenarios"][nome] = d
d0 = {"alfa_GV": A.cronbach(M0[~np.isnan(M0).any(axis=1)]), "omega_GV": A.omega(M0[~np.isnan(M0).any(axis=1)])}
out["principal"] = d0
os.makedirs("agreement", exist_ok=True)
json.dump(out, open("agreement/sensibilidade_GV.json", "w"), ensure_ascii=False, indent=1)
print("principal:", {k: round(v, 3) for k, v in d0.items()})
for k, d in out["cenarios"].items():
    print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in d.items() if a != "CiSS"})
