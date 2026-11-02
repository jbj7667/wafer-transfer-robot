import final,math
from final import *
for sb in range(-180,180,15):
    final.CFG[190]['sb']=sb
    cf=final.CFG[190];T=cf['T']
    fx=build_fixed(T,sb,45)
    st=[i for i in stage_items(T,0,D(sb),D(45)) if i[0]=='TH_stepper'][0]
    p=st[1]
    if max(q[0] for q in p)>PX1 or min(q[0] for q in p)<PX0 or max(q[1] for q in p)>PY or min(q[1] for q in p)<-PY: continue
    mv,E,W=moving(190,T,D(30),D(96),0.0,1,cf['mb'],sb,45)
    m,w=mincl(mv,fx)
    print(sb,round(m,1),w, [i[0] for i in fx if 'UNPL' in i[0]])
