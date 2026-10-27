import math,sys
from ev import *
L=int(sys.argv[1]); T=eval(sys.argv[2]); s=int(sys.argv[3]); SB=int(sys.argv[4])
best=[]
for mbr in (0,25,45,-25):
  for sb in (SB,):
    for mb in (-40,40,-70,70,180):
        fx=build_fixed(T,sb,mbr)
        if any('UNPL' in i[0] for i in fx): continue
        # swing: use row top 175 and 200 worst (left->right)
        r=[]
        for top,thL in ((175,73.4),(200,101.5),(200,131.6)):
            r.append(swing(L,T,s,mb,sb,mbr,fx,top,thL,step=20))
        m=min(x[0] for x in r)
        print(mbr,sb,mb,round(m,1),flush=True)
        best.append((round(m,1),mbr,sb,mb,[(round(x[0],1),x[1],x[2]) for x in r]))
best.sort(reverse=True)
for b in best[:6]: print(b)
