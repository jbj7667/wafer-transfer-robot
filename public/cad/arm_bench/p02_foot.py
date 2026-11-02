exec(open(r'C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2\public\cad\arm_bench\lib_bench.py', encoding='utf-8').read())
def run(_c):
    wipe('P02_foot'); c = comp('P02_foot')
    box(c, (-18, 18), (-18, 18), (0, 38))
    box(c, (-14, 14), (-14, 14), (-1, 34), cut=True)
    cyls(c, 'z', [(0, 0, 36)], 3.4, 8, cut=True)
    done(c, 'P02_foot')
