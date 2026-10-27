exec(open(r'C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2\public\cad\arm_bench\lib_bench.py', encoding='utf-8').read())
PARTS = [
 ('P01_base','P01_base.stl',0,'바닥 면 평평'),
 ('P02_foot','P02_foot_x4.stl',180,'뒤집어(뚜껑면 베드, 열린 쪽 위)'),
 ('P03_turntable','P03_turntable.stl',0,'바닥 면 평평'),
 ('P04_theta_hub60','P04_theta_hub60.stl',0,'60T 플랜지 면 베드, 관 위로'),
 ('P05_shoulder_hub60','P05_shoulder_hub60.stl',0,'60T 플랜지 면 베드'),
 ('P06_pulley52_hub','P06_pulley52_hub_x2.stl',0,'52T 플랜지 면 베드, 목 위로'),
 ('P07_pulley26_hub','P07_pulley26_hub.stl',0,'26T 플랜지 면 베드'),
 ('P08_elbow_hub26','P08_elbow_hub26.stl',0,'26T 플랜지 면 베드, 허브 위로(포켓 위)'),
 ('P09_pulley20_D5','P09_pulley20_D5_x2.stl',0,'20T 플랜지 면 베드'),
 ('P10_link1_box','P10_link1_box.stl',0,'바닥 면 평평(개방면 위)'),
 ('P11_link1_lid','P11_link1_lid.stl',0,'평평'),
 ('P12_link2_box','P12_link2_box.stl',0,'바닥 면 평평(개방면 위)'),
 ('P13_link2_lid','P13_link2_lid.stl',0,'평평'),
 ('P14_pointer','P14_pointer.stl',0,'바닥 면 평평, 펜 링 위로'),
 ('P15_idler','P15_idler_x2.stl',0,'판 면 베드, 기둥 위로'),
 ('P16_belt_clamp','P16_belt_clamp_x2.stl',0,'평평(홈 면 위)'),
 ('P17_fork_stub','P17_fork_stub.stl',0,'평평 (선택)'),
]
def run(_c):
    res = []
    for name, fn, rx, ori in PARTS:
        c = comp(name)
        v, mn, mx = info(c)
        bb = pexport(name, fn, rx=rx)
        g = v * 1.24 * 0.35
        res.append(dict(name=name, stl=fn, orient=ori, bbox=bb, vol=round(v, 2), g=round(g, 1)))
    open(OUT + r'\parts.json', 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=1))
