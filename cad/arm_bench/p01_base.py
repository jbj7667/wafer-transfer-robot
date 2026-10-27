exec(open(r'C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2\public\cad\arm_bench\lib_bench.py', encoding='utf-8').read())
def run(_c):
    wipe('P01_base'); c = comp('P01_base')
    TX, TY = 100, 150; MY = TY - 114.3
    box(c, (0, 200), (0, 190), (0, 6))
    cyls(c, 'z', [(TX, TY, 11.5)], 36, 11)
    cyls(c, 'z', [(TX, TY, 9.8)], 22.2, 14.4, cut=True)
    cyls(c, 'z', [(TX, TY, 1.5)], 18, 5, cut=True)
    for x0, x1 in ((40, 80), (120, 160)):
        box(c, (x0, x1), (105, 175), (-1, 7), cut=True)
    slot(c, TX, MY, -1, 7, 23, 6, ax='y')
    for dx in (-15.5, 15.5):
        for dy in (-15.5, 15.5):
            slot(c, TX + dx, MY + dy, -1, 7, 3.4, 6, ax='y')
    cyls(c, 'z', [(18, 18, 3), (182, 18, 3), (18, 172, 3), (182, 172, 3)], 3.4, 8, cut=True)
    cyls(c, 'z', [(45, 95, 3), (155, 95, 3)], 5.6, 8, cut=True)
    done(c, 'P01_base')
