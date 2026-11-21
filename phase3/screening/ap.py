import sys,re,unicodedata
def norm(s): return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
f=sys.argv[1]; pat=sys.argv[2]; mx=int(sys.argv[3]) if len(sys.argv)>3 else 4
pages=open(f"raw/{f}.txt",errors='ignore').read().split('\f'); rx=re.compile(norm(pat)); n=0
for i,p in enumerate(pages,1):
    t=re.sub(r"\s+"," ",norm(p))
    for m in rx.finditer(t):
        a=max(0,m.start()-120); print("p.%d: ...%s"%(i,t[a:m.end()+160])); n+=1
        break
    if n>=mx: break
