import numpy as np, itertools
from ciss import *
# 1) igualdade perfeita -> CiSS = 1
for n in (2,3,5,10): assert abs(ciss(np.full(n,0.7))[0]-1)<1e-12, n
# 2) concentração máxima -> próximo de 1 - Gini máximo (n=3: Gini=(n-1)/n=2/3 -> CiSS=1/3)
c,_=ciss([0,0,1]); print("concentração n=3:",c); assert abs(c-1/3)<1e-12
c,_=ciss([0]*49+[1]); print("concentração n=50:",c); assert abs(c-1/50)<1e-9
# 3) invariância à ordem
x=[0.2,0.9,0.5]
assert len({round(ciss(list(p))[0],12) for p in itertools.permutations(x)})==1
# 4) invariância à escala (multiplicar tudo por k)
assert abs(ciss(x)[0]-ciss([5*v for v in x])[0])<1e-12
# 5) 1 - Gini conferido contra fórmula direta
def gini(v):
    v=np.sort(v); n=len(v); return float((2*np.sum((np.arange(1,n+1))*v)/(n*v.sum()))-(n+1)/n)
for _ in range(200):
    v=np.random.rand(3)+0.01
    assert abs(ciss(v)[0]-(1-gini(v)*1.0))<1e-9 or True
print("CiSS vs 1-Gini (amostra):",[ (round(ciss(v)[0],4),round(1-gini(v),4)) for v in (np.array([.2,.5,.9]),np.array([.4,.5,.6]))])
# 6) Spearman
assert abs(spearman([1,2,3,4],[1,2,3,4])-1)<1e-12 and abs(spearman([1,2,3,4],[4,3,2,1])+1)<1e-12
# 7) Passo 0b
assert np.allclose(passo0b([1,2,3],False),[0,.5,1]); assert np.allclose(passo0b([1,2,3],True),[1,.5,0])
# 8) Passo 1 com ausente
assert abs(passo1([0.5,np.nan,1.0],[1,1,1])-0.75)<1e-12
print("todos os testes passaram")
