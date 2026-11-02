# shared helpers for replay v2 (exec'd inside Fusion script)
import adsk.core, adsk.fusion, math, time, json, os
B = r'C:\Users\gy050\Videos\wafer_robot\out\build_frames'
def logp(s):
    open(B + r'\progress2.log', 'a', encoding='utf-8').write(s + '\n')
def getdoc(name):
    app = adsk.core.Application.get()
    d = [x for x in app.documents if x.name == name][0]
    d.activate()
    return app, adsk.fusion.Design.cast(app.activeProduct)
def corners(bb):
    a, b = bb.minPoint, bb.maxPoint
    return [(x, y, z) for x in (a.x, b.x) for y in (a.y, b.y) for z in (a.z, b.z)]
def eye_at(cam, ang):
    t, ey = cam['target'], cam['eye']
    a = math.radians(ang)
    dx, dy = ey[0] - t[0], ey[1] - t[1]
    return (t[0] + dx*math.cos(a) - dy*math.sin(a), t[1] + dx*math.sin(a) + dy*math.cos(a), ey[2])
def proj(cs, eye, t):
    d = [t[i]-eye[i] for i in range(3)]; n = math.sqrt(sum(v*v for v in d)); d = [v/n for v in d]
    up = (0, 0, 1)
    r = [d[1]*up[2]-d[2]*up[1], d[2]*up[0]-d[0]*up[2], d[0]*up[1]-d[1]*up[0]]
    rn = math.sqrt(sum(v*v for v in r)); r = [v/rn for v in r]
    vu = [r[1]*d[2]-r[2]*d[1], r[2]*d[0]-r[0]*d[2], r[0]*d[1]-r[1]*d[0]]
    hs = [sum(vu[i]*c[i] for i in range(3)) for c in cs]
    ws = [sum(r[i]*c[i] for i in range(3)) for c in cs]
    return max(hs)-min(hs), max(ws)-min(ws)
def setcam(vp, cam, ang):
    c = vp.camera
    c.isFitView = False
    c.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    c.target = adsk.core.Point3D.create(*cam['target'])
    c.upVector = adsk.core.Vector3D.create(0, 0, 1)
    c.eye = adsk.core.Point3D.create(*eye_at(cam, ang))
    c.viewExtents = cam['ext']
    vp.camera = c
def shot(vp, path):
    adsk.doEvents(); vp.refresh()
    vp.saveAsImageFile(path, 1920, 1080)
def makecam(bb, orbit):
    cs = corners(bb)
    t = [(bb.minPoint.x+bb.maxPoint.x)/2, (bb.minPoint.y+bb.maxPoint.y)/2, (bb.minPoint.z+bb.maxPoint.z)/2]
    ey = [t[0]+57.74, t[1]-57.74, t[2]+57.74]
    cam = {'target': t, 'eye': ey}
    Hm = 0; Wm = 0
    for i in range(0, 11):
        h, w = proj(cs, eye_at(cam, orbit*i/10.0), t)
        Hm = max(Hm, h); Wm = max(Wm, w)
    cam['H'] = Hm; cam['W'] = Wm
    return cam
