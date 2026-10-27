import math,sys,json
from lib_arm import *
from checks import BASES,base_items,cd_item
from ev import *
D=math.radians;R2D=math.degrees
CFG={180:dict(T=(-8,2),stow=(216,108),mbr=45,mb=40,sb=0),190:dict(T=(40,-50),stow=(30,96),mbr=45,mb=70,sb=150)}
FWT=[(0,92),(0,-92),(-75,0),(95,70),(95,-70)]
def hull(pts):
    pts=sorted(set(pts))
    def cr(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[];up=[]
    for p in pts:
        while len(lo)>=2 and cr(lo[-2],lo[-1],p)<=0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up)>=2 and cr(up[-2],up[-1],p)<=0: up.pop()
        up.append(p)
    return lo[:-1]+up[:-1]
SUP=hull(FWT)
def tip_margin(c):
    m=1e9
    for i in range(len(SUP)):
        a,b=SUP[i],SUP[(i+1)%len(SUP)]
        d=((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/math.hypot(b[0]-a[0],b[1]-a[1])
        m=min(m,d)
    return m
def com(L,cf,th,phi,s=1):
    T=cf['T'];E,W=pose(L,T,th,phi,s)
    mx=T[0]+62*math.cos(D(cf['mbr']));my=T[1]+62*math.sin(D(cf['mbr']))
    sx=T[0]+114*math.cos(D(cf['sb']));sy=T[1]+114*math.sin(D(cf['sb']))
    mc=(T[0]+55*math.cos(th+D(cf['mb'])),T[1]+55*math.sin(th+D(cf['mb'])))
    pk=(W[0]+POCKET*math.cos(th),W[1]+POCKET*math.sin(th))
    parts=[(1275,(-20,0)),(550,(mx,my)),(250,(sx,sy)),(250,mc),(110+90,T),(110,((T[0]+E[0])/2,(T[1]+E[1])/2)),(110,((E[0]+W[0])/2,(E[1]+W[1])/2)),(70+16,pk)]
    M=sum(p[0] for p in parts)
    return (sum(p[0]*p[1][0] for p in parts)/M,sum(p[0]*p[1][1] for p in parts)/M),M
def run(L):
    cf=CFG[L];T=cf['T'];out=[]
    P=lambda *a:(out.append(' '.join(str(x) for x in a)),print(*a,flush=True))
    fx=build_fixed(T,cf['sb'],cf['mbr'])
    P('== L',L,cf,'unplaced',[i[0] for i in fx if 'UNPL' in i[0]])
    # 1 stow
    thd,phd=cf['stow']
    mv,E,W=moving(L,T,D(thd),D(phd),1,0.0,cf['mb'],cf['sb'],cf['mbr']) if False else moving(L,T,D(thd),D(phd),0.0,1,cf['mb'],cf['sb'],cf['mbr'])
    allit=fx+mv
    b=bbox(allit); zmax=max(i[3] for i in allit)
    P('STOW bbox X %.1f..%.1f (%.1f) Y %.1f..%.1f (%.1f) Z 0..%.1f'%(b[0],b[1],b[1]-b[0],b[2],b[3],b[3]-b[2],zmax),
      'margins X %.1f Y %.1f Z %.1f'%(250-(b[1]-b[0]),250-(b[3]-b[2]),250-zmax))
    m,w=mincl(mv,fx); P('STOW min clearance arm vs body/mast %.1f'%m,w)
    # 2 reach
    miny=1e9
    for k,(thd2,R,top) in BASES.items():
        th=D(thd2);Rw=R-POCKET;phi=math.acos(Rw/(2*L));dz=max(0,top-10-FORK_TOP0)
        mv,E,W=moving(L,T,th,phi,dz,1,cf['mb'],cf['sb'],cf['mbr'])
        pk=(W[0]+POCKET*math.cos(th),W[1]+POCKET*math.sin(th));bc=(T[0]+R*math.cos(th),T[1]+R*math.sin(th))
        bs=base_items(T)
        mb_,wb=mincl(mv,bs);mf,wf=mincl(mv,fx)
        # target base neck vs fork legs lateral clearance
        pts=[p for i in mv for p in i[1]]
        fy=fieldy(T,pts);elb_y=240-(E[0]-T[0])-LINK_W/2 ; miny=min(miny,fy)
        col=[c for c in collide(mv,bs+fx,0.3) if not SKIPP(next(i for i in mv if i[0]==c[0]),next(i for i in bs+fx if i[0]==c[1]))]
        P('REACH b%d th %.1f R %.1f Rw %.1f phi %.1f sing_margin %.1f dz %.0f slot-neck off %.2f clr_bases %.1f%s clr_body %.1f%s coll %s fieldy_min %.1f elbow_y(%.1f)'%(k,thd2,R,Rw,R2D(phi),2*L-Rw,dz,math.hypot(pk[0]-bc[0],pk[1]-bc[1]),mb_,wb,mf,wf,col,fy,240-(E[0]-T[0])))
        c,M=com(L,cf,th,phi);P('   CoM (%.0f,%.0f) M %.0fg tip margin %.1f'%(c[0],c[1],M,tip_margin(c)))
    P('REACH min field y %.1f'%miny)
    # 3 swing
    ms=1e9;mfy=1e9;mt=1e9
    for top,thL in ((175,73.4),(200,101.5),(200,131.6)):
        phi=math.acos(150/(2*L));dz=top+15-FORK_TOP0
        angs=[];x=thL
        while x<360-thL:angs.append(x);x+=10
        angs.append(360-thL)
        wst=(1e9,)
        for ad in angs:
            th=D(ad);mv,E,W=moving(L,T,th,phi,dz,1,cf['mb'],cf['sb'],cf['mbr']);mv=mv+[cd_item(W,th,top+15)]
            mb_,wb=mincl(mv,base_items(T));mf,wf=mincl(mv,fx)
            if min(mb_,mf)<wst[0]: wst=(min(mb_,mf),ad,wb if mb_<mf else wf,mb_,mf)
            fy=fieldy(T,[p for i in mv for p in i[1]]);mfy=min(mfy,fy)
            c,M=com(L,cf,th,phi);mt=min(mt,tip_margin(c))
        ms=min(ms,wst[0])
        P('SWING row top %d th %.1f->%.1f: min clearance %.1f at th %.0f pair %s (bases %.1f body %.1f)'%(top,thL,360-thL,wst[0],wst[1],wst[2],wst[3],wst[4]))
    P('SWING overall min clearance %.1f ; min field y %.1f ; min tip margin %.1f'%(ms,mfy,mt))
    return out
if __name__=='__main__':
    L=int(sys.argv[1]);o=run(L)
    open('result_L%d.txt'%L,'w').write('\n'.join(o))
