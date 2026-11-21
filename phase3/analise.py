import json,numpy as np,math,sys
from ciss import *
rng=np.random.default_rng(20261120)
col=json.load(open("coleta.json")); fin=json.load(open("fin2024.json")); gv=json.load(open("gv.json"))
EMP=["Allos","Ambev","Auren","AXS","Azzas","C&A","CBA","Cemig","Cogna","Copasa","Copel","CPFL","Engie","Klabin","Lojas Renner","Magalu","Minerva Foods","Movida","Natura","Pague Menos","TIM","WEG"]
FK={"Azzas":"Azzas 2154"}
IND=["EF3","EF4","SA1","SA2","SA3","SA5","GV1","GV2","GV3","GV5"]
DIM={"EF":["EF3","EF4"],"SA":["SA1","SA2","SA3","SA5"],"GV":["GV1","GV2","GV3","GV5"]}
ESC={"EF3":"OPEN_ZERO","EF4":"OPEN_NEG","SA1":"CLOSED","SA2":"OPEN_POSITIVE","SA3":"CLOSED","SA5":"OPEN_NEG","GV1":"CLOSED","GV2":"CLOSED","GV3":"CLOSED","GV5":"CLOSED"}
MENOR={"EF3":True,"EF4":False,"SA1":False,"SA2":True,"SA3":False,"SA5":True,"GV1":False,"GV2":False,"GV3":False,"GV5":False}
def raw(roic_key="roic_pct"):
    R=np.full((len(EMP),len(IND)),np.nan)
    for i,e in enumerate(EMP):
        f=fin.get(FK.get(e,e),{})
        for j,k in enumerate(IND):
            v=None
            if k=="EF4": v=f.get(roic_key) if roic_key!="roic_ef_pct" else (f.get("roic_ef_pct") if f.get("roic_ef_pct") is not None else f.get("roic_pct"))
            elif k=="SA2":
                x=col.get(e,{}).get("SA2",{}).get("valor"); v=None if x is None else x/f["rev_mi"]
            elif k.startswith("GV"):
                v=25*gv[e][k]["total"]
            else: v=col.get(e,{}).get(k,{}).get("valor")
            if v is not None: R[i,j]=v
    return R
def normalize(R,modo="principal",ln=True):
    N=np.full(R.shape,np.nan)
    for j,k in enumerate(IND):
        x=R[:,j].copy(); ok=~np.isnan(x)
        esc=ESC[k] if ln else "CLOSED"
        t=x.copy(); t[ok]=passo0(x[ok],esc)
        if modo=="z":
            mu,sd=np.nanmean(t),np.nanstd(t,ddof=1)
            z=(t-mu)/sd; v=np.full(len(t),np.nan); v[ok]=[0.5*(1+math.erf(a/math.sqrt(2))) for a in z[ok]]
            if MENOR[k]: v[ok]=1-v[ok]
            N[:,j]=v
        else: N[:,j]=passo0b(t,MENOR[k])
    return N
def scores(N,w):
    S=np.full((N.shape[0],3),np.nan); 
    for d,(dn,ks) in enumerate(DIM.items()):
        idx=[IND.index(k) for k in ks]
        for i in range(N.shape[0]): S[i,d]=passo1(N[i,idx],w[idx])
    return S
def cissvec(S):
    out=np.full(S.shape[0],np.nan)
    for i in range(S.shape[0]):
        x=S[i][~np.isnan(S[i])]
        if len(x)>=2: out[i]=ciss(x)[0]
    return out
def cronbach(M):
    M=np.asarray(M,float); k=M.shape[1]; v=M.var(axis=0,ddof=1).sum(); t=M.sum(axis=1).var(ddof=1)
    return float(k/(k-1)*(1-v/t)) if t>0 else float("nan")
def omega(M):
    M=np.asarray(M,float); C=np.corrcoef(M.T); k=C.shape[0]; h=np.ones(k)*0.5
    for _ in range(500):
        Cr=C.copy(); np.fill_diagonal(Cr,h); w,v=np.linalg.eigh(Cr); l=v[:,-1]*np.sqrt(max(w[-1],1e-12)); l=l*np.sign(l.sum()) 
        hn=np.clip(l**2,1e-3,0.995)
        if np.max(abs(hn-h))<1e-8: break
        h=hn
    num=l.sum()**2; return float(num/(num+np.sum(1-l**2)))
def main():
    R=raw(); N=normalize(R); w0=np.ones(len(IND)); S=scores(N,w0); C=cissvec(S)
    res={"emp":EMP,"raw":np.where(np.isnan(R),None,R).tolist()}
    cov={k:int((~np.isnan(R[:,j])).sum()) for j,k in enumerate(IND)}; res["cobertura"]=cov
    res["principal"]={"S":np.where(np.isnan(S),None,S).tolist(),"CiSS":C.tolist(),"SC":(1-C).tolist(),"media":np.nanmean(S,axis=1).tolist()}
    # sensibilidade de pesos: uma de cada vez ±20%
    maxd=np.zeros(len(EMP)); oat=[]
    for j in range(len(IND)):
        for f in (0.8,1.2):
            w=w0.copy(); w[j]=f; C2=cissvec(scores(N,w)); d=np.abs(C2-C); maxd=np.maximum(maxd,d); oat.append((IND[j],f,float(d.max()),spearman(C,C2)))
    res["oat"]={"maxdelta_por_empresa":maxd.tolist(),"maxdelta_global":float(maxd.max()),"min_spearman":min(o[3] for o in oat),"detalhe":oat}
    # Monte Carlo
    B=10000; dmax=np.zeros(B); sp=np.zeros(B); dfirm=np.zeros((B,len(EMP)))
    for b in range(B):
        w=rng.uniform(0.8,1.2,len(IND)); C2=cissvec(scores(N,w)); d=np.abs(C2-C); dfirm[b]=d; dmax[b]=d.max(); sp[b]=spearman(C,C2)
    res["mc"]={"B":B,"prop_estavel":float((dmax<0.05).mean()),"maxdelta_p95":float(np.percentile(dmax,95)),"maxdelta_max":float(dmax.max()),"spearman_min":float(sp.min()),"spearman_p05":float(np.percentile(sp,5)),"spearman_med":float(np.median(sp)),
                "prop_estavel_por_empresa":(dfirm<0.05).mean(axis=0).tolist(),"delta_max_por_empresa":dfirm.max(axis=0).tolist()}
    # normalização
    var={}
    var["principal"]=C
    var["sem_ln"]=cissvec(scores(normalize(R,ln=False),w0))
    var["z_cdf"]=cissvec(scores(normalize(R,modo="z"),w0))
    var["roic_efetivo"]=cissvec(scores(normalize(raw("roic_ef_pct")),w0))
    keep=[i for i,e in enumerate(EMP) if e not in ("Auren","Azzas")]
    Rk=R[keep]; Ck=cissvec(scores(normalize(Rk),w0)); var["sem_Auren_Azzas"]=None
    res["norm"]={k:{"spearman_vs_principal":(spearman(C,v) if v is not None else spearman(C[keep],Ck)),"delta_max":(float(np.abs(C-v).max()) if v is not None else float(np.abs(C[keep]-Ck).max()))} for k,v in var.items() if k!="principal"}
    res["norm"]["_CiSS"]={k:(v.tolist() if v is not None else Ck.tolist()) for k,v in var.items()}
    # ranking por media de scores vs CiSS
    mean=np.nanmean(S,axis=1)
    res["discriminacao"]={"CiSS":{"media":float(np.nanmean(C)),"dp":float(np.nanstd(C,ddof=1)),"min":float(np.nanmin(C)),"q1":float(np.nanpercentile(C,25)),"med":float(np.nanmedian(C)),"q3":float(np.nanpercentile(C,75)),"max":float(np.nanmax(C))},
        "media_scores":{"media":float(mean.mean()),"dp":float(mean.std(ddof=1)),"min":float(mean.min()),"max":float(mean.max())},
        "spearman_CiSS_media":spearman(C,mean),"pearson_CiSS_media":float(np.corrcoef(C,mean)[0,1])}
    # consistência interna
    def boot(M,fn,B=2000):
        n=M.shape[0]; v=[]
        for _ in range(B):
            Mb=M[rng.integers(0,n,n)]
            try:
                x=fn(Mb)
                if np.isfinite(x): v.append(x)
            except Exception: pass
        return float(np.percentile(v,2.5)),float(np.percentile(v,97.5)),len(v)
    cons={}
    for dn,ks in DIM.items():
        idx=[IND.index(k) for k in ks]; M=N[:,idx]; ok=~np.isnan(M).any(axis=1); Mc=M[ok]
        d={"n_completos":int(ok.sum()),"itens":ks}
        if dn=="EF":
            if ok.sum()>=3: d["spearman_EF3_EF4"]=spearman(Mc[:,0],Mc[:,1]); d["pearson_EF3_EF4"]=float(np.corrcoef(Mc.T)[0,1])
        else:
            if ok.sum()>=5:
                d["alfa"]=cronbach(Mc); d["alfa_IC95"]=boot(Mc,cronbach)[:2]
                try: d["omega"]=omega(Mc); d["omega_IC95"]=boot(Mc,omega)[:2]
                except Exception as e: d["omega"]=None
                d["corr_item_total_corrigida"]={ks[j]:float(np.corrcoef(Mc[:,j],np.delete(Mc,j,axis=1).sum(axis=1))[0,1]) if np.delete(Mc,j,axis=1).sum(axis=1).std()>0 and Mc[:,j].std()>0 else None for j in range(len(ks))}
        cons[dn]=d
    # alfa SA usando só SA1,SA2 (maior cobertura) para referência
    idx=[IND.index(k) for k in ("SA1","SA2")]; M=N[:,idx]; ok=~np.isnan(M).any(axis=1)
    cons["SA_so_SA1_SA2"]={"n":int(ok.sum()),"spearman":spearman(M[ok][:,0],M[ok][:,1])}
    res["consistencia"]=cons
    # correlações entre indicadores (Spearman pareado)
    Cm=[[None]*len(IND) for _ in IND]
    for a in range(len(IND)):
        for b in range(len(IND)):
            ok=~np.isnan(N[:,a])&~np.isnan(N[:,b])
            if ok.sum()>=6: Cm[a][b]=spearman(N[ok,a],N[ok,b])
    res["corr_ind"]=Cm
    # variabilidade (teto): proporção com 100 nos GV
    res["teto_GV"]={k:int((R[:,IND.index(k)]>=100).sum()) for k in ("GV1","GV2","GV3","GV5")}
    json.dump(res,open("resultados.json","w"),ensure_ascii=False,indent=1)
    return res,R,N,S,C
if __name__=="__main__": main(); print("ok")
