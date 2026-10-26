import adsk.core, adsk.fusion, math, json, os
app = adsk.core.Application.get()
OUT = r'C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2\public\cad\print'
P3 = adsk.core.Point3D.create
V3 = adsk.core.Vector3D.create
def des(): return adsk.fusion.Design.cast(app.activeProduct)
def log(m):
    open(OUT + r'\progress.log', 'a', encoding='utf-8').write(m + '\n')
def comp(name):
    r = des().rootComponent
    for o in r.occurrences:
        if o.component.name == name: return o.component
    o = r.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    o.component.name = name
    return o.component
def _plane(c, p, n):
    i = [abs(v) for v in n].index(1) if 1 in [abs(v) for v in n] else 2
    base = (c.yZConstructionPlane, c.xZConstructionPlane, c.xYConstructionPlane)[i]
    nn = base.geometry.normal
    nv = (nn.x, nn.y, nn.z)[i]
    off = p[i] / 10.0 * (1 if nv > 0 else -1)
    if abs(off) < 1e-9: return base
    pi = c.constructionPlanes.createInput()
    pi.setByOffset(base, adsk.core.ValueInput.createByReal(off))
    return c.constructionPlanes.add(pi)
def _run(c, sk, length, cut):
    coll = adsk.core.ObjectCollection.create()
    for p in sk.profiles: coll.add(p)
    ex = c.features.extrudeFeatures
    def mk(op):
        i = ex.createInput(coll, op)
        i.setSymmetricExtent(adsk.core.ValueInput.createByReal(length / 10), True)
        return ex.add(i)
    if cut: return mk(adsk.fusion.FeatureOperations.CutFeatureOperation)
    if c.bRepBodies.count == 0: return mk(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    try: return mk(adsk.fusion.FeatureOperations.JoinFeatureOperation)
    except Exception: return mk(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
def _sk(c, ax, mid_pt):
    n = [0, 0, 0]; n[ax] = 1
    return c.sketches.add(_plane(c, mid_pt, n))
def _pt(sk, p): return sk.modelToSketchSpace(P3(*[v / 10 for v in p]))
def box(c, x, y, z, cut=False, ax='z'):
    i = 'xyz'.index(ax); R = [x, y, z]
    lo = [x[0], y[0], z[0]]; hi = [x[1], y[1], z[1]]
    mid = (R[i][0] + R[i][1]) / 2; lo[i] = mid; hi[i] = mid
    sk = _sk(c, i, lo)
    sk.sketchCurves.sketchLines.addTwoPointRectangle(_pt(sk, lo), _pt(sk, hi))
    return _run(c, sk, R[i][1] - R[i][0], cut)
def cyls(c, ax, pts, r, length, cut=False):
    i = 'xyz'.index(ax)
    sk = _sk(c, i, pts[0])
    for p in pts:
        sk.sketchCurves.sketchCircles.addByCenterRadius(_pt(sk, p), r / 20)
    return _run(c, sk, length, cut)
def poly(c, ax, mid, pts2, length, cut=False):
    # polygon on plane normal ax at coordinate mid; pts2 in (a,b) = the two other axes in xyz order
    i = 'xyz'.index(ax); o = [k for k in range(3) if k != i]
    def m3(a, b):
        p = [0, 0, 0]; p[i] = mid; p[o[0]] = a; p[o[1]] = b; return p
    sk = _sk(c, i, m3(*pts2[0]))
    L = sk.sketchCurves.sketchLines
    n = len(pts2)
    for k in range(n):
        L.addByTwoPoints(_pt(sk, m3(*pts2[k])), _pt(sk, m3(*pts2[(k + 1) % n])))
    return _run(c, sk, length, cut)
def arcseg(c, cx, cy, r1, r2, t0, t1, z0, z1, cut=False):
    zm = (z0 + z1) / 2
    sk = _sk(c, 2, (cx, cy, zm))
    def q(r, t): return _pt(sk, (cx + r * math.cos(math.radians(t)), cy + r * math.sin(math.radians(t)), zm))
    tm = (t0 + t1) / 2
    A = sk.sketchCurves.sketchArcs; L = sk.sketchCurves.sketchLines
    A.addByThreePoints(q(r1, t0), q(r1, tm), q(r1, t1))
    A.addByThreePoints(q(r2, t0), q(r2, tm), q(r2, t1))
    L.addByTwoPoints(q(r1, t0), q(r2, t0)); L.addByTwoPoints(q(r1, t1), q(r2, t1))
    return _run(c, sk, z1 - z0, cut)
def info(c):
    v = 0; mn = [1e9] * 3; mx = [-1e9] * 3
    for b in c.bRepBodies:
        v += b.physicalProperties.volume
        bb = b.boundingBox
        for k, (a, bq) in enumerate(zip((bb.minPoint.x, bb.minPoint.y, bb.minPoint.z), (bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z))):
            mn[k] = min(mn[k], a * 10); mx[k] = max(mx[k], bq * 10)
    return v, mn, mx
def done(c, tag):
    v, mn, mx = info(c)
    s = '%s bodies=%d vol=%.2fcm3 min=%s max=%s' % (tag, c.bRepBodies.count, v, [round(a, 1) for a in mn], [round(a, 1) for a in mx])
    log(s); print(s)
def pexport(name, fname, rx=0, ry=0, rz=0):
    """rotate (deg about X, then Y, then Z) about origin, drop to bed (min z=0, min xy=10), export STL, restore."""
    d = des(); occ = None
    for o in d.rootComponent.occurrences:
        if o.component.name == name: occ = o
    M = adsk.core.Matrix3D.create()
    for ax, a in (((1, 0, 0), rx), ((0, 1, 0), ry), ((0, 0, 1), rz)):
        if a:
            R = adsk.core.Matrix3D.create()
            R.setToRotation(math.radians(a), V3(*ax), P3(0, 0, 0))
            R.transformBy(M); M = R
    occ.transform2 = M
    mn = [1e9] * 3; mx = [-1e9] * 3
    for b in occ.bRepBodies:
        bb = b.boundingBox
        for k, (a, q) in enumerate(zip((bb.minPoint.x, bb.minPoint.y, bb.minPoint.z), (bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z))):
            mn[k] = min(mn[k], a); mx[k] = max(mx[k], q)
    T2 = M.copy(); T2.translation = V3(1 - mn[0], 1 - mn[1], -mn[2])
    occ.transform2 = T2
    em = d.exportManager
    o = em.createSTLExportOptions(occ, OUT + '\\' + fname)
    o.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
    em.execute(o)
    bb = [round((mx[k] - mn[k]) * 10, 1) for k in range(3)]
    occ.transform2 = adsk.core.Matrix3D.create()
    s = 'EXPORT %s %s bbox_print=%s' % (name, fname, bb)
    log(s); print(s)
    return bb
def setname(name):
    pass

def wipe(name):
    for o in list(des().rootComponent.occurrences):
        if o.component.name == name: o.deleteMe()
