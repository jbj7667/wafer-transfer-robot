import json,math
import final
from final import *
def gen(L):
    cf=final.CFG[L];T=cf['T'];mb=D(cf['mb'])
    fx=build_fixed(T,cf['sb'],cf['mbr'])
    S=lambda items:[dict(n=i[0],p=[[round(x,2),round(y,2)] for x,y in i[1]],z0=i[2],z1=i[3]) for i in items if i[3]>i[2]]
    rel=lambda p:[(x-T[0],y-T[1]) for x,y in p]
    parts={}
    parts['static']=dict(items=S(fx))
    parts['bases']=dict(items=S(base_items(T)))
    parts['link1']=dict(items=S([('link1',rect(0,L,-14,14),Z1[0],Z1[1],''),('hub_s',circ(0,0,20),Z1[0],Z1[1],''),('hub_e',circ(L,0,20),Z1[0],Z1[1],'')]))
    parts['link2']=dict(items=S([('link2',rect(0,L,-14,14),Z2[0],Z2[1],''),('hub_e',circ(0,0,20),Z2[0],Z2[1],''),('hub_w',circ(L,0,20),Z2[0],Z2[1],'')]))
    parts['fork']=dict(items=S([('fork%d'%k,p,FORK_TOP0-FORK_T,FORK_TOP0,'') for k,p in enumerate(fork_polys())]))
    mc=(55*math.cos(mb),55*math.sin(mb))
    parts['turntable']=dict(items=S([('turntable',circ(0,0,50),104,118,''),('Rmotor',xf(rect(-21,21,-21,21),0,*mc),118,152,'')]))
    car=[i for i in stage_items(T,0,D(cf['sb']),D(cf['mbr'])) if i[4]=='car']
    parts['carriage']=dict(items=S([(i[0],rel(i[1]),i[2],i[3],'') for i in car]))
    poses={}
    def pz(th,phi,dz):
        E,W=pose(L,T,th,phi,1)
        a1=math.atan2(E[1]-T[1],E[0]-T[0]);a2=math.atan2(W[1]-E[1],W[0]-E[0])
        return dict(static=[0,0,0,0],bases=[0,0,0,0],link1=[a1,T[0],T[1],dz],link2=[a2,E[0],E[1],dz],fork=[th,W[0],W[1],dz],turntable=[th,T[0],T[1],dz],carriage=[0,T[0],T[1],dz])
    th,ph=cf['stow']; poses['stow']=pz(D(th),D(ph),0)
    for k in (5,3):
        thd,R,top=BASES[k]; phi=math.acos((R-POCKET)/(2*L)); poses['reach%d'%k]=pz(D(thd),phi,max(0,top-10-FORK_TOP0))
    json.dump(dict(L=L,T=T,parts=parts,poses=poses),open('model_L%d.json'%L,'w'))
    print(L,{k:len(v['items']) for k,v in parts.items()})
gen(180);gen(190)
