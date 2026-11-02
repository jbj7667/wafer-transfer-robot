import math,sys,json
from lib_arm import *
D=math.radians; R2D=math.degrees
BASES={5:(73.4,386.0,175),6:(-73.4,386.0,175),3:(101.5,326.5,200),4:(-101.5,326.5,200),1:(131.6,361.2,200),2:(-131.6,361.2,200)}
CFG={180:dict(T=(22,-38),sb=90,mb=180,stow=(303,109)),190:dict(T=(28,54),sb=-90,mb=90,stow=(210,94))}
MBEAR=0.0
def base_items(T,skip=None,cd=True):
    it=[]
    for k,(th,R,top) in BASES.items():
        if k==skip: continue
        c=(T[0]+R*math.cos(D(th)),T[1]+R*math.sin(D(th)))
        it.append(('base%d_low'%k,circ(*c,50),0,100,'base'))
        it.append(('base%d_neck'%k,circ(*c,25),100,top,'base'))
        if cd: it.append(('base%d_CD'%k,circ(*c,60),top,top+1.2,'base'))
    return it
def cd_item(W,th,ft):
    c=(W[0]+POCKET*math.cos(th),W[1]+POCKET*math.sin(th))
    return ('CD',circ(*c,60),ft,ft+1.2,'cd')
def fixed(L):
    c=CFG[L];T=c['T']
    st=stage_items(T,0,D(c['sb']),MBEAR)
    avoid=[i[1] for i in st]+[circ(*T,55)]
    return body_items(avoid)
def moving(L,T,th,phi,dz,s=1):
    c=CFG[L]
    arm,E,W=arm_items(L,T,th,phi,s,dz,D(c['mb']))
    car=[i for i in stage_items(T,dz,D(c['sb']),MBEAR) if i[4]=='car']
    return arm+car,E,W
def fieldy(T,pts): return min(240-(p[0]-T[0]) for p in pts)
if __name__=='__main__':
    L=int(sys.argv[1]); c=CFG[L]; T=c['T']
    fx=fixed(L)+[i for i in stage_items(T,0,D(c['sb']),MBEAR) if i[4]=='fix']
    print('unplaced',[i[0] for i in fx if 'UNPLACED' in i[0]])
    print('fixed-fixed',collide(fx,fx))
    miny=1e9
    print('REACH L',L)
    for k,(thd,R,top) in BASES.items():
        th=D(thd); Rw=R-POCKET; phi=math.acos(Rw/(2*L)); ft=top-10; dz=max(0,ft-FORK_TOP0)
        mv,E,W=moving(L,T,th,phi,dz)
        pocket=(W[0]+POCKET*math.cos(th),W[1]+POCKET*math.sin(th))
        bc=(T[0]+R*math.cos(th),T[1]+R*math.sin(th))
        off=math.hypot(pocket[0]-bc[0],pocket[1]-bc[1])
        bs=base_items(T,skip=None,cd=True)
        # CD of target base sits on post; fork top below CD plane by 10
        col=collide(mv,bs+fx,tol=0.3)
        cl=min(gap(a,b) for a in mv for b in bs+fx if a[4]!='car' or True)
        pts=[p for i in mv for p in i[1]]+cd_item(W,th,top)[1]
        fy=fieldy(T,pts); miny=min(miny,fy)
        # forkyslot centre lateral wrt neck
        print(k,'th',thd,'R',R,'Rw %.1f phi %.1f sing %.1f'%(Rw,R2D(phi),2*L-Rw),'dz',dz,'slotoff %.2f'%off,'col',col[:3],'minclr %.1f'%cl,'fieldy_min %.1f'%fy)
    print('min field y over reach',round(miny,1))
