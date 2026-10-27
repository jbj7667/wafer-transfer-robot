import math,sys
from lib_arm import *
D=math.radians
L=int(sys.argv[1]); MB=float(sys.argv[2]); cands=[]
for thd in range(0,360,6):
  for phid in range(88,126,4):
    for s in (1,):
      for mbd in (40,70):
        e=bbox(arm_items(L,(0,0),D(thd),D(phid),s,0,D(mbd))[0])
        for Tx in range(-20,100,4):
          if Tx+62*math.cos(D(MB))+30>PX1 or Tx+62*math.cos(D(MB))-30<PX0: continue
          for Ty in range(-70,71,4):
            if max(PX1,Tx+e[1])-min(PX0,Tx+e[0])>247.01 or max(PY,Ty+e[3])-min(-PY,Ty+e[2])>247.01: continue
            # margin to plate edges
            m=min(Tx+e[0]-PX0,PX1-Tx-e[1],Ty+e[2]+PY,PY-Ty-e[3])
            cands.append((math.hypot(Tx-10,Ty)-0.5*min(m,3),thd,phid,s,mbd,Tx,Ty,round(m,1)))
cands.sort(); n=0
for c in cands:
    _,thd,phid,s,mbd,Tx,Ty,m=c
    arm,E,W=arm_items(L,(Tx,Ty),D(thd),D(phid),s,0,D(mbd))
    for sb in (0,90,-90,180):
        st=stage_items((Tx,Ty),0,D(sb),D(MB))
        sp=[i[1] for i in st if i[0] in('TH_stepper','Zstepper')]
        if any(max(p[0] for p in q)>PX1 or min(p[0] for p in q)<PX0 or max(p[1] for p in q)>PY or min(p[1] for p in q)<-PY for q in sp): continue
        if collide(arm,st): continue
        print(L,c,'sbear',sb,'bbox',[round(v,1) for v in bbox(arm+st)]); n+=1;break
    if n>=8:break
print(len(cands))
