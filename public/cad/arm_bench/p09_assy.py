exec(open(r'C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2\public\cad\arm_bench\lib_bench.py', encoding='utf-8').read())
L = 180.0
def dummies():
    for n in ('X_motor', 'X_axle', 'X_bolt'):
        wipe(n)
    c = comp('X_motor')
    box(c, (-21, 21), (-21, 21), (-34, 0))
    cyls(c, 'z', [(0, 0, 12)], 5, 24)
    c = comp('X_axle'); cyls(c, 'z', [(0, 0, 65)], 8, 130)
    c = comp('X_bolt'); cyls(c, 'z', [(0, 0, 22.5)], 8, 45)
def comp_by(name):
    for o in des().rootComponent.occurrences:
        if o.component.name == name: return o
def M(x, y, z, ang):
    m = adsk.core.Matrix3D.create()
    if ang: m.setToRotation(math.radians(ang), V3(0, 0, 1), P3(0, 0, 0))
    m.translation = V3(x / 10.0, y / 10.0, z / 10.0)
    return m
def rot(x, y, a):
    r = math.radians(a); return (x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r))
def getocc(key, cname):
    r = des().rootComponent
    for o in r.occurrences:
        at = o.attributes.itemByName('bench', 'key')
        if at and at.value == key: return o
    o = None
    for q in r.occurrences:
        if q.component.name == cname and not q.attributes.itemByName('bench', 'key'):
            o = q; break
    if o is None:
        o = r.occurrences.addExistingComponent(comp_by(cname).component, M(0, 0, 0, 0))
    o.attributes.add('bench', 'key', key)
    return o
def place(key, x, y, z, ang, extra=False):
    cname = key.split('#')[0]
    o = getocc(key, cname); o.transform2 = M(x, y, z, ang); return o
def pose(alpha, beta, tag):
    a1, a2 = alpha + beta, alpha - beta
    E = rot(L, 0, a1); W = (E[0] + rot(L, 0, a2)[0], E[1] + rot(L, 0, a2)[1])
    rm = rot(-114.3, 0, alpha)
    cx, cy = 125 - 25, 150  # base local θ axis (100,150)
    place('P01_base', -100, -150, 38, 0)
    for i, (fx, fy) in enumerate(((18, 18), (182, 18), (18, 172), (182, 172))):
        place('P02_foot#%d' % i, fx - 100, fy - 150, 0, 0)
    place('P03_turntable', 0, 0, 101, alpha)
    place('P04_theta_hub60', 0, 0, 56, alpha)
    place('X_axle', 0, 0, 36, 0)
    place('X_motor#T', 0, -114.3, 38, 0)
    place('P09_pulley20_D5#T', 0, -114.3, 56, 0)
    place('X_motor#R', rm[0], rm[1], 101, alpha)
    place('P09_pulley20_D5#R', rm[0], rm[1], 108, alpha)
    place('P05_shoulder_hub60', 0, 0, 108, a1)
    place('P10_link1_box', 0, 0, 132, a1); place('P11_link1_lid', 0, 0, 150, a1)
    i1 = rot(90, 2, a1); place('P15_idler#1', i1[0], i1[1], 134, a1)
    place('P06_pulley52_hub#S', 0, 0, 141, alpha)
    place('P08_elbow_hub26', E[0], E[1], 141, a2)
    place('P07_pulley26_hub', E[0], E[1], 177.5, a1)
    place('X_bolt#E', E[0], E[1], 132, 0)
    place('P12_link2_box', E[0], E[1], 168.5, a2); place('P13_link2_lid', E[0], E[1], 186.5, a2)
    i2 = rot(90, 2, a2); place('P15_idler#2', E[0] + i2[0], E[1] + i2[1], 170.5, a2)
    place('P06_pulley52_hub#W', W[0], W[1], 177.5, alpha)
    place('P14_pointer', W[0], W[1], 202.5, alpha)
    place('X_bolt#W', W[0], W[1], 168.5, 0)
    place('P16_belt_clamp#a', -250, -100, 0, 0); place('P16_belt_clamp', -250, -130, 0, 0)
    place('P17_fork_stub', -250, -260, 0, 0)
    return E, W
def interf():
    d = des(); col = adsk.core.ObjectCollection.create()
    for o in d.rootComponent.occurrences: col.add(o)
    res = d.analyzeInterference(d.createInterferenceInput(col))
    out = []
    for r in res:
        bb = r.interferenceBody.boundingBox
        out.append((r.entityOne.parentComponent.name, r.entityTwo.parentComponent.name, round(r.interferenceBody.volume, 3),
                    [round(bb.minPoint.x * 10), round(bb.minPoint.y * 10), round(bb.minPoint.z * 10)],
                    [round(bb.maxPoint.x * 10), round(bb.maxPoint.y * 10), round(bb.maxPoint.z * 10)]))
    return out

def shot(tag):
    vp = app.activeViewport
    for nm, ori in (('iso', adsk.core.ViewOrientations.IsoTopRightViewOrientation), ('top', adsk.core.ViewOrientations.TopViewOrientation)):
        cam = vp.camera; cam.viewOrientation = ori; vp.camera = cam; vp.fit()
        vp.saveAsImageFile(OUT + '/bench_%s_%s.png' % (tag, nm), 1600, 1100)
def run(_c):
    if not comp_by('X_motor'): dummies()
    for tag, al, be in (('reach', 0, 26.5), ('folded', 216, 104)):
        E, W = pose(al, be, tag)
        print(tag, 'E', [round(v, 1) for v in E], 'W', [round(v, 1) for v in W], 'Rw', round(math.hypot(*W), 1))
        for t in interf(): print(t)
        shot(tag)
    log('assembly checked')
