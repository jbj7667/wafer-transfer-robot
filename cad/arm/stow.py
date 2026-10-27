import math,sys,itertools
from lib_arm import *
D=math.radians
def ext(L,th,phi,s,mb):
    it,E,W=arm_items(L,(0,0),th,phi,s,0,mb)
    return bbox(it)
res={}
for L in (180,190):
    best=[]
    for thd in range(0,360,3):
      for phid in range(88,126,3):
        for s in (1,-1):
          for mbd in (180,120,-120,90,-90):
            e=ext(L,D(thd),D(phid),s,D(mbd))
            bx=min(((max(PX1,Tx+e[1])-min(PX0,Tx+e[0])),Tx) for Tx in range(-60,100-0,2) if Tx+62+21<=PX1)
            by=min(((max(PY,Ty+e[3])-min(-PY,Ty+e[2])),Ty) for Ty in range(-80,81,2))
            best.append((max(bx[0],by[0]),thd,phid,s,mbd,bx[1],by[1],bx[0],by[0]))
    best.sort(); print(L,len(best))
    for b in best[:6]: print(b)
