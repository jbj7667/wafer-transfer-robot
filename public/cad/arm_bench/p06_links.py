exec(open(r'C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2\public\cad\arm_bench\lib_bench.py', encoding='utf-8').read())
L = 180.0
def hull(rA, rB):
    s = (rA - rB) / L; a = math.asin(s)
    ta = (rA * math.sin(a), rA * math.cos(a)); tb = (L + rB * math.sin(a), rB * math.cos(a))
    return [ta, tb, (tb[0], -tb[1]), (ta[0], -ta[1])]
def ring3(r, z):
    return [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), z) for a in (90, 210, 330)]
def outline(c, rA, rB, z0, z1, off=0.0, cut=False):
    m = (z0 + z1) / 2.0; h = z1 - z0
    poly(c, 'z', m, hull(rA - off, rB - off), h, cut=cut)
    cyls(c, 'z', [(0, 0, m)], 2 * (rA - off), h, cut=cut)
    cyls(c, 'z', [(L, 0, m)], 2 * (rB - off), h, cut=cut)
def box_part(name, rA, rB, kindA, kindB):
    wipe(name); c = comp(name)
    outline(c, rA, rB, 0, 18)
    outline(c, rA, rB, 2, 22, off=3.0, cut=True)
    for px in (45, 135):
        cyls(c, 'z', [(px, 0, 10)], 6, 16)
    cyls(c, 'z', [(45, 0, 12), (135, 0, 12)], 2.6, 12, cut=True)
    # 피벗 보스 z2..8
    if kindA == 'hub34':
        cyls(c, 'z', [(0, 0, 5)], 34, 6); cyls(c, 'z', ring3(14.5, 3), 3.4, 10, cut=True)
    else:
        cyls(c, 'z', [(0, 0, 5)], 30, 6); cyls(c, 'z', ring3(13.1, 3), 3.4, 10, cut=True)
    cyls(c, 'z', [(0, 0, 4)], 9, 12, cut=True)
    cyls(c, 'z', [(L, 0, 5)], 26, 6)
    if kindB == 'bolt':
        cyls(c, 'z', [(L, 0, 4)], 8.4, 12, cut=True)
        cyls(c, 'z', [(L, 0, 1.25)], 15, 4.5, cut=True)
    else:
        cyls(c, 'z', [(L, 0, 4.4)], 22.2, 7.2, cut=True)
        cyls(c, 'z', [(L, 0, 0.5)], 16, 3, cut=True)
    for sx in (84, 96):
        slot(c, sx, 0, -1, 3, 3.4, 12, ax='y')
    done(c, name)
def lid_part(name, rA, rB):
    wipe(name); c = comp(name)
    outline(c, rA, rB, 0, 2)
    cyls(c, 'z', [(0, 0, 1), (L, 0, 1)], 17, 4, cut=True)
    cyls(c, 'z', [(45, 0, 1), (135, 0, 1)], 3.4, 4, cut=True)
    done(c, name)
def run(_c):
    box_part('P10_link1_box', 22, 14, 'hub34', 'bolt')
    lid_part('P11_link1_lid', 22, 14)
    box_part('P12_link2_box', 19, 22, 'hub30', 'brg')
    lid_part('P13_link2_lid', 19, 22)
