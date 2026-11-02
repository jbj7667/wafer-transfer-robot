# Fusion script body (run via fusion_mcp_execute). Set START/END (frame indices) before running.
import adsk.core, adsk.fusion, json, math, time, os
START, END = 0, 25
def run(_context):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    assert app.activeDocument.name == 'wafer_robot_print_v1'
    B = r'C:\Users\gy050\Videos\wafer_robot\out\build_frames'
    cam0 = json.load(open(B + r'\camera.json'))
    tl = design.timeline; vp = app.activeViewport
    feats = []
    for i in range(tl.count):
        e = tl.item(i).entity
        if e and e.objectType.split('::')[-1] in ('ExtrudeFeature', 'RevolveFeature'):
            feats.append((i, e.parentComponent.name))
    N = len(feats)
    t = cam0['target']; ey = cam0['eye']
    t0 = time.time()
    for k in range(START, min(END, N)):
        i, comp = feats[k]
        a = math.radians(40.0 * k / max(N - 1, 1))
        dx, dy = ey[0] - t[0], ey[1] - t[1]
        nx = t[0] + dx * math.cos(a) - dy * math.sin(a)
        ny = t[1] + dx * math.sin(a) + dy * math.cos(a)
        tl.markerPosition = i + 1
        c = vp.camera
        c.isFitView = False
        c.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        c.target = adsk.core.Point3D.create(*t)
        c.upVector = adsk.core.Vector3D.create(0, 0, 1)
        c.eye = adsk.core.Point3D.create(nx, ny, ey[2])
        c.viewExtents = cam0['ext'][0]
        vp.camera = c
        adsk.doEvents(); vp.refresh()
        vp.saveAsImageFile(B + r'\print_v1\f_%05d.png' % k, 1920, 1080)
        open(B + r'\frames.csv', 'a', encoding='utf-8').write('%d,%d,%s\n' % (k, i, comp))
        open(B + r'\progress.log', 'a').write('%d/%d %s %.1fs\n' % (k, N, comp, time.time() - t0))
    tl.moveToEnd()
    print('done', START, END, N, time.time() - t0)
