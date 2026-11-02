exec(open(r'C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2\public\cad\arm_bench\lib_bench.py', encoding='utf-8').read())
def ring3(r, a0=90):
    return [(r * math.cos(math.radians(a0 + k * 120)), r * math.sin(math.radians(a0 + k * 120)), 0) for k in range(3)]
def at(pts, z): return [(p[0], p[1], z) for p in pts]
def run(_c):
    # P04 theta_hub_60: 60T + 관 (회전대 아래, 벨트면 위로 37mm 관)
    wipe('P04_theta_hub60'); c = comp('P04_theta_hub60')
    pulley(c, 0, 0, 60, 0)
    cyls(c, 'z', [(0, 0, 26.5)], 27, 37)
    cyls(c, 'z', [(0, 0, 22.5)], 17, 47, cut=True)
    cyls(c, 'z', at(ring3(11), 41), 2.8, 10, cut=True)
    done(c, 'P04_theta_hub60')
    # P05 shoulder_hub_60: 60T + 허브(608 x2 포켓 위·아래) + 링크1 체결 구멍 3
    wipe('P05_shoulder_hub60'); c = comp('P05_shoulder_hub60')
    pulley(c, 0, 0, 60, 0)
    cyls(c, 'z', [(0, 0, 16)], 34, 16)
    cyls(c, 'z', [(0, 0, 3.1)], 22.2, 8.2, cut=True)
    cyls(c, 'z', [(0, 0, 20.9)], 22.2, 8.2, cut=True)
    cyls(c, 'z', [(0, 0, 12)], 9, 26, cut=True)
    cyls(c, 'z', at(ring3(14.5), 20), 2.8, 8, cut=True)
    done(c, 'P05_shoulder_hub60')
