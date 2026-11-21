"""CiSS 2.0 – implementação dos Passos 0–7 (+ Passo 0b) para a Fase 3. Somente numpy."""
import numpy as np, math

# ---------- Passo 0: transformação por escala ----------
def passo0(x, escala):
    x=np.asarray(x,float)
    if escala=="OPEN_POSITIVE": return np.log(x)
    if escala=="OPEN_ZERO":     return np.log1p(x)
    return x                      # CLOSED ou aberta com valores negativos: sem transformação

# ---------- Passo 0b: reescala 0-1 na amostra + inversão de direção ----------
def passo0b(v, menor_melhor):
    v=np.asarray(v,float); ok=~np.isnan(v); out=np.full(v.shape,np.nan)
    lo,hi=np.nanmin(v),np.nanmax(v)
    if hi==lo: out[ok]=0.5
    else: out[ok]=(v[ok]-lo)/(hi-lo)
    if menor_melhor: out[ok]=1-out[ok]
    return out

# ---------- Passo 1: score da dimensão (média ponderada dos disponíveis) ----------
def passo1(M, w):
    """M: (n_ind,) valores normalizados de UMA empresa para UMA dimensão (nan = ausente); w pesos"""
    M=np.asarray(M,float); w=np.asarray(w,float); ok=~np.isnan(M)
    if not ok.any(): return np.nan
    return float((w[ok]*M[ok]).sum()/w[ok].sum())

# ---------- Passos 2–7: Lorenz ----------
def ciss(X):
    """X: scores das dimensões de uma organização. Retorna (CiSS, SC)."""
    X=np.sort(np.asarray(X,float)); n=len(X)
    if np.any(X<0): raise ValueError("Xi negativo")
    S=X.sum()
    if S==0: return 1.0,0.0
    Phi=np.concatenate([[0.0],np.cumsum(X)/S])          # Φ(0)=0
    lorenz_sum=float(np.sum(Phi[:-1]+Phi[1:]))            # soma dos trapézios (sem o fator 1/2·ΔP)
    c=lorenz_sum/n
    return c,1-c

# ---------- Spearman (empates → posto médio) ----------
def rank(a):
    a=np.asarray(a,float); o=np.argsort(a,kind="mergesort"); r=np.empty(len(a)); r[o]=np.arange(1,len(a)+1)
    for v in np.unique(a):
        m=a==v
        if m.sum()>1: r[m]=r[m].mean()
    return r
def spearman(a,b):
    a,b=rank(a),rank(b)
    if a.std()==0 or b.std()==0: return float("nan")
    return float(np.corrcoef(a,b)[0,1])
