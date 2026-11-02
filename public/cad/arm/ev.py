import math,sys
from lib_arm import *
from checks import BASES,base_items,cd_item,fieldy
D=math.radians
SKIPP=lambda a,b: ((a[0].startswith('car_plate') and b[0].startswith('mast')) or (b[0].startswith('car_plate') and a[0].startswith('mast'))
   or (a[0]=='deck' or b[0]=='deck') or (a[4]==b[4]=='fix') or (a[0]=='turntable' and b[0].startswith('car_plate')) or (b[0]=='turntable' and a[0].startswith('car_plate'))
   or (a[0]=='turntable' and b[0]=='hub_s1') or (b[0]=='turntable' and a[0]=='hub_s1') or (a[4]==b[4]=='car'))
def stage(T,dz,sb,mbr): return stage_items(T,dz,D(sb),D(mbr))
def build_fixed(T,sb,mbr):
    st=stage(T,0,sb,mbr)
    avoid=[i[1] for i in st if i[0] in('Zstepper','TH_stepper') or i[0].startswith('mastrod')]
    avoid+=[circ(*T,0.1)]
    f=body_items(avoid)
    return f+[i for i in st if i[4]=='fix']
def moving(L,T,th,phi,dz,s,mb,sb,mbr):
    arm,E,W=arm_items(L,T,th,phi,s,dz,D(mb))
    car=[i for i in stage(T,dz,sb,mbr) if i[4]=='car']
    return arm+car,E,W
def _bb(i):
    xs=[p[0] for p in i[1]];ys=[p[1] for p in i[1]];return min(xs),max(xs),min(ys),max(ys)
def mincl(mv,others):
    m=1e9;w=None
    ob=[(b,_bb(b)) for b in others]
    for a in mv:
        ab=_bb(a)
        for b,bb in ob:
            dzg=max(a[2]-b[3],b[2]-a[3])
            lb=math.hypot(max(0,ab[0]-bb[1],bb[0]-ab[1],0),max(0,ab[2]-bb[3],bb[2]-ab[3]))
            if max(lb,dzg)>=m and max(lb,dzg)>0 and math.hypot(lb,max(dzg,0))>=m: continue
            if SKIPP(a,b): continue
            g=gap(a,b)
            if g<m: m=g;w=(a[0],b[0])
    return m,w
def swing(L,T,s,mb,sb,mbr,fx,row_top,thL,step=10):
    """left base angle thL(deg>0) -> right (360-thL) via rear, retracted Rw=150"""
    phi=math.acos(150/(2*L)); dz=row_top+15-FORK_TOP0
    worst=(1e9,None,None)
    others=fx
    for k in range(0,int(360-2*thL)//step*step+1,step) if False else range(0,1):
        pass
    a=thL
    angs=[]
    x=thL
    while x<360-thL: angs.append(x); x+=step
    angs.append(360-thL)
    for ad in angs:
        th=D(ad)
        mv,E,W=moving(L,T,th,phi,dz,s,mb,sb,mbr)
        mv=mv+[cd_item(W,th,row_top+15)]
        bs=[b for b in base_items(T,cd=True) if True]
        m,w=mincl(mv,fx+bs)
        if m<worst[0]: worst=(m,ad,w)
    return worst
