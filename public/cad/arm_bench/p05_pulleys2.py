exec(open(r'C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2\public\cad\arm_bench\lib_bench.py', encoding='utf-8').read())
def ring3(r, a0=90):
    return [(r * math.cos(math.radians(a0 + k * 120)), r * math.sin(math.radians(a0 + k * 120)), 0) for k in range(3)]
def at(pts, z): return [(p[0], p[1], z) for p in pts]
def fixed(name, N):
    # 풀리 z0..8 + 위로 Ø16 목 (z 8..25, 덮개 구멍 통과) + 보어 8.2 + M3 세트스크루(z 22) + 포인터 체결 파일럿 2
    wipe(name); c = comp(name)
    pulley(c, 0, 0, N, 0)
    cyls(c, 'z', [(0, 0, 16.5)], 16, 17)
    cyls(c, 'z', [(0, 0, 12.5)], 8.2, 27, cut=True)
    cyls(c, 'x', [(4, 0, 22)], 2.6, 8, cut=True)
    cyls(c, 'z', [(5.5, 0, 24)], 2.8, 5, cut=True)
    cyls(c, 'z', [(-5.5, 0, 24)], 2.8, 5, cut=True)
    done(c, name)
def run(_c):
    fixed('P06_pulley52_hub', 52)
    fixed('P07_pulley26_hub', 26)
    # P08 elbow_hub_26: 26T(z0..8) + 목 Ø14 (8..12) + 허브 Ø30 (12..27.5) + 608x2 포켓(위에서 14.4) + 링크2 체결 3
    n = 'P08_elbow_hub26'; wipe(n); c = comp(n)
    pulley(c, 0, 0, 26, 0)
    cyls(c, 'z', [(0, 0, 10)], 14, 5)
    cyls(c, 'z', [(0, 0, 19.75)], 30, 15.5)
    cyls(c, 'z', [(0, 0, 20.3)], 22.2, 14.4, cut=True)
    cyls(c, 'z', [(0, 0, 13.5)], 8.4, 30, cut=True)
    cyls(c, 'z', at(ring3(13.1), 23.5), 2.8, 8, cut=True)
    done(c, n)
    # P09 pulley20_D5: 20T(z0..8) + 허브 Ø16 (8..18) + D보어 5 + 세트스크루
    n = 'P09_pulley20_D5'; wipe(n); c = comp(n)
    pulley(c, 0, 0, 20, 0)
    cyls(c, 'z', [(0, 0, 12.5)], 16, 11)
    cyls(c, 'z', [(0, 0, 9)], 5.2, 20, cut=True)
    box(c, (1.9, 2.6), (-1.8, 1.8), (0, 18))
    cyls(c, 'x', [(4, 0, 14)], 2.6, 8, cut=True)
    done(c, n)
