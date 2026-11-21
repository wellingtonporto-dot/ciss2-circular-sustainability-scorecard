import sys,re,unicodedata
def norm(s): return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
f=sys.argv[1]; txt=open(f"raw/{f}.txt",errors='ignore').read(); pages=txt.split('\f')
npages=[norm(p).replace('\n',' ') for p in pages]
CR={
"GV1.1 politica":r"politica (de |da |global de |corporativa de )?(sustentabilidade|ambiental|esg|meio ambiente|socioambiental|ambiental e climatica)|(sustainability|environmental|esg) policy",
"GV1.2 CA aprova":r"(politica|diretriz)[^.]{0,120}(aprovad|homologad)[^.]{0,80}(conselho|board)|(conselho de administracao|board)[^.]{0,100}aprov[^.]{0,100}politica",
"GV1.3 circular":r"economia circular|circularidade|circular economy",
"GV1.4 metas":r"metas? (de |para )?(sustentabilidade|esg|ambientais?|climatic|residuos|reducao)|compromissos? (publicos|2030|ambientais)",
"GV2.1 GRI":r"(indice (de conteudo )?gri|gri content index|em referencia (aos|as) (padroes|normas) gri|with reference to the gri|sumario (de conteudo )?gri|indice remissivo gri|gri 1:|gri 1 )",
"GV2.2 SASB":r"sasb",
"GV2.3 TCFD/ISSB":r"tcfd|ifrs ?s[12]|issb|task force on climate",
"GV2.4 asseguracao":r"asseguracao (externa|independente|limitada|razoavel)|(relatorio|carta) de (asseguracao|auditoria independente)|assurance|verificacao externa|auditoria independente (limitada|dos indicadores)|limited assurance",
"GV3.1 mapa risco":r"(mapa|matriz|inventario|portfolio|categorias?) de riscos?[^.]{0,200}(climat|socioambient|ambiental|esg|sustentab)|riscos? (climatic|socioambient|esg|de sustentabilidade)[^.]{0,200}(mapa|matriz|gerenciamento de riscos|risco corporativo)",
"GV3.2 comite/area":r"comite (de )?(sustentabilidade|esg|riscos|estrategia|ambiental|clima)|(area|diretoria|gerencia) (de )?(sustentabilidade|esg|riscos|meio ambiente)",
"GV3.3 risco circular":r"riscos?[^.]{0,120}(residuos|escassez|recursos naturais|circular|materias-primas|agua|hidric)",
"GV3.4 CA acompanha":r"(conselho de administracao|conselho|board)[^.]{0,160}(acompanh|supervision|monitor|avali|revis)[^.]{0,140}(risco|climat|sustentab|esg)|(risco|climat|sustentab|esg)[^.]{0,140}(conselho de administracao|board)[^.]{0,120}(acompanh|periodic|trimestral|anual|semestral)",
"GV5.1 codigo forn":r"codigo de (conduta|etica)[^.]{0,60}fornecedor|fornecedores?[^.]{0,60}codigo de conduta|supplier code|codigo do fornecedor|politica de (relacionamento com )?fornecedores|codigo de conduta de terceiros",
"GV5.2 criterios":r"(criterios|requisitos|clausulas?|avaliacao)[^.]{0,100}(socioambient|ambiental|esg|sustentab|social)[^.]{0,100}(fornecedor|selecao|contrata|homolog)|(selecao|homologacao|contratacao)[^.]{0,100}(criterios|requisitos)[^.]{0,60}(socioambient|ambient|esg|sustentab)|308-1|414-1",
"GV5.3 auditoria":r"auditorias?[^.]{0,80}fornecedor|fornecedor[^.]{0,80}auditad|monitoramento (de|dos) fornecedores|fornecedores?[^.]{0,80}(monitorad|auditoria|visita|due diligence)",
"GV5.4 % avaliados":r"[0-9]{1,3}([.,][0-9]+)? ?%[^.]{0,80}fornecedor[^.]{0,60}(avaliad|auditad|homolog|triad|selecionad|criterios)|fornecedor[^.]{0,100}(avaliad|auditad|homolog|triad|selecionad)[^.]{0,60}[0-9]{1,3}([.,][0-9]+)? ?%|(308-1|414-1)[^.]{0,200}[0-9]{1,3} ?%|novos fornecedores.{0,100}[0-9]+ ?%",
}
ctx=int(sys.argv[2]) if len(sys.argv)>2 else 110
for k,pat in CR.items():
    rx=re.compile(pat); hits=[]
    for i,p in enumerate(npages,1):
        m=rx.search(p)
        if m: hits.append((i,m))
    pg=[h[0] for h in hits]
    print(f"## {k}: {len(hits)} págs {pg[:14]}")
    for i,m in hits[:2]:
        orig=npages[i-1]
        a=max(0,m.start()-30); sn=re.sub(r"\s+"," ",orig[a:a+ctx*2]); print("   p.%d: ...%s"%(i,sn))
