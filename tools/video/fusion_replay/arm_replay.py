# Drop-in build-up for direct-design docs. exec after setting globals:
# DOC, OUT, ORBIT, EXT, START, END (step range), ORDER (list "occ|name" / "body|occ|body"),
# HIDE (occ names hidden whole run), SHOWN_OCC_BODIES (occ names whose bodies start hidden), HOLD_END (sec, handled in build)
# Special: MODE='cam' -> compute camera json from INCLUDE occ names; MODE='restore'
exec(open(r'C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2\tools\video\fusion_replay\lib2.py', encoding='utf-8').read())
DZ = 8.0
def occ_of(rc, n):
    for o in rc.allOccurrences:
        if o.name == n: return o
    raise Exception('no occ ' + n)
def mat(a):
    m = adsk.core.Matrix3D.create(); m.setWithArray(a); return m
def nframes(order):
    return sum(1 if s.startswith('body') else 7 for s in order)
def run(_c):
    app, des = getdoc(DOC)
    rc = des.rootComponent; vp = app.activeViewport
    sf = B + r'\orig_%s.json' % OUT
    if MODE == 'cam':
        bb = None
        for n in INCLUDE:
            b = occ_of(rc, n).boundingBox
            if bb is None: bb = adsk.core.BoundingBox3D.create(b.minPoint.copy(), b.maxPoint.copy())
            else: bb.combine(b)
        cam = makecam(bb, ORBIT); cam['ext'] = cam['H'] * 1.1
        json.dump(cam, open(B + r'\camera_%s.json' % OUT, 'w')); print(cam); return
    if MODE == 'restore':
        o = json.load(open(sf))
        for oc in rc.allOccurrences:
            if oc.name in o['t']: oc.transform2 = mat(o['t'][oc.name])
            oc.isLightBulbOn = o['vis'].get(oc.name, True)
            for b in oc.component.bRepBodies: b.isLightBulbOn = True
        print('restored'); return
    if START == 0:
        o = {'t': {}, 'vis': {}}
        for oc in rc.allOccurrences:
            o['t'][oc.name] = oc.transform2.asArray(); o['vis'][oc.name] = oc.isLightBulbOn
        json.dump(o, open(sf, 'w'))
        for oc in rc.allOccurrences:
            oc.isLightBulbOn = False
        for n in SHOWN_OCC_BODIES:
            for b in occ_of(rc, n).component.bRepBodies: b.isLightBulbOn = False
        open(B + r'\frames_%s.csv' % OUT, 'w').close()
    o = json.load(open(sf))
    cam = json.load(open(B + r'\camera_%s.json' % OUT))
    TOT = nframes(ORDER)
    k = sum(nframes(ORDER[:START])) if False else nframes(ORDER[:START])
    t0 = time.time()
    for si in range(START, min(END, len(ORDER))):
        sp = ORDER[si].split('|')
        if sp[0] == 'body':
            oc = occ_of(rc, sp[1]); oc.isLightBulbOn = True
            for b in oc.component.bRepBodies:
                if b.name == sp[2]: b.isLightBulbOn = True
            setcam(vp, cam, ORBIT * k / (TOT - 1))
            shot(vp, B + r'\%s\f_%05d.png' % (OUT, k))
            open(B + r'\frames_%s.csv' % OUT, 'a', encoding='utf-8').write('%d,0.2,%s\n' % (k, sp[1].split(':')[0] + ' / ' + sp[2])); k += 1
        else:
            oc = occ_of(rc, sp[1]); orig = o['t'][oc.name]
            oc.isLightBulbOn = True
            nm = oc.name.split(':')[0]
            for j in range(7):
                rem = DZ * (1 - j / 6.0) ** 2
                a = list(orig); a[11] = orig[11] + rem
                oc.transform2 = mat(a)
                setcam(vp, cam, ORBIT * k / (TOT - 1))
                shot(vp, B + r'\%s\f_%05d.png' % (OUT, k))
                open(B + r'\frames_%s.csv' % OUT, 'a', encoding='utf-8').write('%d,%s,%s\n' % (k, 0.3 if j == 6 else 0.05, nm)); k += 1
        logp('%s step %d/%d %s frames=%d %.1fs' % (OUT, si, len(ORDER), ORDER[si], k, time.time() - t0))
    print('next START', si + 1, 'k', k, time.time() - t0)
