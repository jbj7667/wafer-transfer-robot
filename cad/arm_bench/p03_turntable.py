exec(open(r'C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2\public\cad\arm_bench\lib_bench.py', encoding='utf-8').read())
def run(_c):
    wipe('P03_turntable'); c = comp('P03_turntable')
    RX = -114.3
    box(c, (-150, 35), (-34, 34), (0, 6))
    cyls(c, 'z', [(0, 0, 3)], 8.4, 8, cut=True)
    cyls(c, 'z', [(0, 0, 4.5)], 15, 3, cut=True)
    slot(c, RX, 0, -1, 7, 23, 6, ax='x')
    for dx in (-15.5, 15.5):
        for dy in (-15.5, 15.5):
            slot(c, RX + dx, dy, -1, 7, 3.4, 6, ax='x')
    pts = [(11 * math.cos(math.radians(a)), 11 * math.sin(math.radians(a)), 3) for a in (90, 210, 330)]
    cyls(c, 'z', pts, 3.4, 8, cut=True)
    done(c, 'P03_turntable')
