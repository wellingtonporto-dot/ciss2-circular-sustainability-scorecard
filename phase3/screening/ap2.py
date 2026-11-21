import sys,re,unicodedata
def norm(s): return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
f=sys.argv[1]; pat=norm(sys.argv[2]).replace(" ",""); mx=int(sys.argv[3]) if len(sys.argv)>3 else 3
pages=open(f"raw/{f}.txt",errors='ignore').read().split('\f'); n=0
rx=re.compile(pat)
for i,p in enumerate(pages,1):
    t=norm(p); t=re.sub(r"\s+","",t)
    m=rx.search(t)
    if m:
        a=max(0,m.start()-110); print("p.%d: ...%s"%(i,t[a:m.end()+150])); n+=1
    if n>=mx: break
