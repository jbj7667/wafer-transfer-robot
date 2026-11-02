# exec after setting globals: DOC, OUT (frame subdir), ORBIT, START, END, EXT, KINDS (None=all items)
exec(open(r'C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2\tools\video\fusion_replay\lib2.py', encoding='utf-8').read())
def run(_c):
    app, des = getdoc(DOC)
    tl = des.timeline; vp = app.activeViewport
    cam = json.load(open(B + r'\camera_%s.json' % OUT)); cam['ext'] = EXT
    feats = []
    for i in range(tl.count):
        it = tl.item(i)
        e = it.entity
        if KINDS is None:
            nm = it.name
            try:
                if e and e.objectType.split('::')[-1] == 'Occurrence':
                    nm = e.name
            except: pass
            feats.append((i, nm))
        elif e and e.objectType.split('::')[-1] == 'Occurrence' and 'Occurrence' in KINDS:
            feats.append((i, e.name.split(':')[0].strip()))
        elif e and e.objectType.split('::')[-1] in KINDS:
            feats.append((i, e.parentComponent.name))
    N = len(feats); t0 = time.time()
    for k in range(START, min(END, N)):
        i, comp = feats[k]
        tl.markerPosition = i + 1 + (1 if (KINDS and 'Occurrence' in KINDS) else 0)
        setcam(vp, cam, ORBIT * k / max(N - 1, 1))
        shot(vp, B + r'\%s\f_%05d.png' % (OUT, k))
        open(B + r'\frames_%s.csv' % OUT, 'a', encoding='utf-8').write('%d,%d,%s\n' % (k, i, comp))
        logp('%s %d/%d %s %.1fs' % (OUT, k, N, comp, time.time() - t0))
        if time.time() - t0 > 85: break
    print('last k', k, 'N', N, time.time() - t0)
    tl.moveToEnd()
