# lib_arm.py : pure-python geometry helpers for arm-option go/no-go (mm, robot frame)
import math
def rect(x0,x1,y0,y1): return [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
def circ(cx,cy,r,n=24):
    rr=r/math.cos(math.pi/n)
    return [(cx+rr*math.cos(2*math.pi*(i+.5)/n),cy+rr*math.sin(2*math.pi*(i+.5)/n)) for i in range(n)]
def xf(poly,ang,tx,ty):
    c,s=math.cos(ang),math.sin(ang)
    return [(tx+c*x-s*y,ty+s*x+c*y) for x,y in poly]
def rbox(p0,p1,hw):  # rectangle from p0 to p1 with half width hw
    dx,dy=p1[0]-p0[0],p1[1]-p0[1]; l=math.hypot(dx,dy); a=math.atan2(dy,dx)
    return xf(rect(0,l,-hw,hw),a,p0[0],p0[1])
def _axes(p):
    for i in range(len(p)):
        x1,y1=p[i];x2,y2=p[(i+1)%len(p)]
        n=math.hypot(y2-y1,x2-x1)
        yield ((y1-y2)/n,(x2-x1)/n)
def penetration(a,b):
    """SAT depth (>0 overlap) between convex polys"""
    best=1e9
    for ax in list(_axes(a))+list(_axes(b)):
        pa=[x*ax[0]+y*ax[1] for x,y in a]; pb=[x*ax[0]+y*ax[1] for x,y in b]
        o=min(max(pa),max(pb))-max(min(pa),min(pb))
        if o<=0: return -1
        best=min(best,o)
    return best
def _pseg(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]; d=dx*dx+dy*dy
    t=0 if d==0 else max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/d))
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
def dist2d(a,b):
    if penetration(a,b)>0: return 0.0
    m=1e9
    for P,Q in ((a,b),(b,a)):
        for p in P:
            for i in range(len(Q)): m=min(m,_pseg(p,Q[i],Q[(i+1)%len(Q)]))
    return m
def gap(i,j):  # item=(name,poly,z0,z1): 3D clearance (approx: max of z gap, xy dist)
    dzg=max(i[2]-j[3],j[2]-i[3])
    d=dist2d(i[1],j[1])
    if dzg>0 and d==0: return dzg
    if dzg>0: return math.hypot(d,dzg)
    return d
# ---------------- constants ----------------
PX0,PX1,PY=-89.0,155.0,122.0   # deck plate 244x244
LINK_W,LINK_H,HUB_R=28.0,20.0,20.0
Z1=(118.0,138.0); Z2=(140.0,160.0); FORK_T=4.0; FORK_TOP0=165.0
FORK_W,FORK_LEN,SLOT_W,POCKET=118.0,129.0,78.0,64.0
TT_R=50.0
def fork_polys():
    s=FORK_W/2; u=SLOT_W/2; xb=POCKET-u
    return [rect(0,xb,-s,s),rect(xb,FORK_LEN,u,s),rect(xb,FORK_LEN,-s,-u)]
def pose(L,T,th,phi,s=1):
    u=(math.cos(th),math.sin(th)); v=(-u[1],u[0])
    W=(T[0]+2*L*math.cos(phi)*u[0],T[1]+2*L*math.cos(phi)*u[1])
    E=(T[0]+L*math.cos(phi)*u[0]+s*L*math.sin(phi)*v[0],T[1]+L*math.cos(phi)*u[1]+s*L*math.sin(phi)*v[1])
    return E,W
def arm_items(L,T,th,phi,s=1,dz=0.0,mot_bear=math.pi):
    """moving items (name,poly,z0,z1,grp) world coords"""
    E,W=pose(L,T,th,phi,s); it=[]
    it.append(('link1',rbox(T,E,LINK_W/2),Z1[0]+dz,Z1[1]+dz,'arm'))
    it.append(('hub_s1',circ(*T,HUB_R),Z1[0]+dz,Z1[1]+dz,'arm'))
    it.append(('hub_e1',circ(*E,HUB_R),Z1[0]+dz,Z1[1]+dz,'arm'))
    it.append(('link2',rbox(E,W,LINK_W/2),Z2[0]+dz,Z2[1]+dz,'arm'))
    it.append(('hub_e2',circ(*E,HUB_R),Z2[0]+dz,Z2[1]+dz,'arm'))
    it.append(('hub_w',circ(*W,HUB_R),Z2[0]+dz,Z2[1]+dz,'arm'))
    for k,p in enumerate(fork_polys()):
        it.append(('fork%d'%k,xf(p,th,*W),FORK_TOP0-FORK_T+dz,FORK_TOP0+dz,'arm'))
    it.append(('turntable',circ(*T,TT_R),104+dz,118+dz,'tt'))
    mc=(T[0]+55*math.cos(th+mot_bear),T[1]+55*math.sin(th+mot_bear))
    it.append(('Rmotor',xf(rect(-21,21,-21,21),th,*mc),118+dz,152+dz,'tt'))
    return it,E,W
def bbox(items):
    xs=[p[0] for it in items for p in it[1]]; ys=[p[1] for it in items for p in it[1]]
    return min(xs),max(xs),min(ys),max(ys)

# ---------- fixed body + stage ----------
def stage_items(T,dz=0.0,sbear=0.0,mbear=0.0):
    it=[]; mx=T[0]+62*math.cos(mbear); my=T[1]+62*math.sin(mbear)
    it.append(('Zstepper',xf(rect(-21,21,-21,21),mbear,mx,my),56,96,'fix'))
    for k,dy in enumerate((-16,0,16)):
        c=xf([(0,dy)],mbear,mx,my)[0]
        it.append(('mastrod%d'%k,circ(c[0],c[1],4.5),56,245,'fix'))
    it.append(('mastblock',xf(rect(-21,21,-21,21),mbear,mx,my),232,245,'fix'))
    it.append(('car_plate_m',rbox(T,(mx,my),22),100+dz,104+dz,'car'))
    sx=T[0]+114*math.cos(sbear); sy=T[1]+114*math.sin(sbear)
    it.append(('car_plate_s',rbox(T,(sx,sy),21),100+dz,104+dz,'car'))
    it.append(('TH_stepper',xf(rect(-21,21,-21,21),sbear,sx,sy),58+dz,100+dz,'car'))
    return it
def body_items(avoid):
    """body: returns items; greedy-places deck electronics avoiding polys in avoid"""
    it=[('deck',rect(PX0,PX1,-PY,PY),52,56,'fix')]
    for sg in (1,-1):
        it.append(('wheel%d'%sg,rect(-32.5,32.5,sg*79 if sg>0 else -105,105 if sg>0 else -79) if False else rect(-32.5,32.5,min(sg*79,sg*105),max(sg*79,sg*105)),0,65,'fix'))
        it.append(('dcmotor%d'%sg,rect(-18,18,min(sg*9,sg*79),max(sg*9,sg*79)),14,51,'fix'))
        it.append(('skid%d'%sg,circ(95,sg*70,10),0,52,'fix'))
    it.append(('caster',circ(-75,0,10),0,52,'fix'))
    boxes=[('batt1',58,90,56,72),('batt2',58,90,56,72),('mega',54,102,56,83),('L298',44,44,56,85),
           ('drv1',20,16,56,66),('drv2',20,16,56,66),('drv3',20,16,56,66)]
    placed=[]
    for n,w,d,z0,z1 in boxes:
        ok=False
        for cx in range(int(PX0+w/2+3),int(PX1-w/2-3),4):
            for cy in range(int(-PY+d/2+3),int(PY-d/2-3),4):
                p=rect(cx-w/2-3,cx+w/2+3,cy-d/2-3,cy+d/2+3)
                if any(penetration(p,q)>0 for q in avoid+[b[1] for b in placed]): continue
                placed.append((n,rect(cx-w/2,cx+w/2,cy-d/2,cy+d/2),z0,z1,'fix')); ok=True;break
            if ok:break
        if not ok: placed.append((n+'_UNPLACED',rect(0,1,0,1),0,0,'fix'))
    return it+placed
def collide(A,B,tol=0.3,skip=()):
    out=[]
    for a in A:
        for b in B:
            if a is b or (a[0],b[0]) in skip: continue
            if min(a[3],b[3])-max(a[2],b[2])<=tol: continue
            p=penetration(a[1],b[1])
            if p>tol: out.append((a[0],b[0],round(p,1)))
    return out
