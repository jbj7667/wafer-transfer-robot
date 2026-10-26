import adsk.core, adsk.fusion
C = adsk.core
def design():
    return adsk.fusion.Design.cast(C.Application.get().activeProduct)
def sh(p):
    t = adsk.fusion.TemporaryBRepManager.get()
    if p[0] in ('box', 'nbox'):
        x0, x1, y0, y1, z0, z1 = p[1:7]
        o = C.OrientedBoundingBox3D.create(C.Point3D.create((x0+x1)/20, (y0+y1)/20, (z0+z1)/20), C.Vector3D.create(1, 0, 0), C.Vector3D.create(0, 1, 0), (x1-x0)/10, (y1-y0)/10, (z1-z0)/10)
        return t.createBox(o)
    a, b0, c0, ax, r, L = p[1:7]
    e = [a, b0, c0]
    e[{'x': 0, 'y': 1, 'z': 2}[ax]] += L
    return t.createCylinderOrCone(C.Point3D.create(a/10, b0/10, c0/10), r/10, C.Point3D.create(e[0]/10, e[1]/10, e[2]/10), r/10)
def mk(name, parts, rgb=None):
    d = design()
    occ = d.rootComponent.occurrences.addNewComponent(C.Matrix3D.create())
    comp = occ.component
    comp.name = name
    t = adsk.fusion.TemporaryBRepManager.get()
    bf = comp.features.baseFeatures.add()
    bf.startEdit()
    bodies = []
    for p in parts:
        b = sh(p)
        if p[0].startswith('n'):
            for x in bodies:
                t.booleanOperation(x, b, adsk.fusion.BooleanTypes.DifferenceBooleanType)
        else:
            bodies.append(b)
    for i, b in enumerate(bodies):
        nb = comp.bRepBodies.add(b, bf)
        nb.name = '%s_b%d' % (name, i)
    bf.finishEdit()
    return occ
