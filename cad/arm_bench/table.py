# parts.json -> 마크다운 표 (arm_bench.md 용). 실행: python -I table.py
import json
P = {p['name']: p for p in json.load(open('parts.json', encoding='utf-8'))}
Q = {'P01_base': 1, 'P02_foot': 4, 'P03_turntable': 1, 'P04_theta_hub60': 1, 'P05_shoulder_hub60': 1,
     'P06_pulley52_hub': 2, 'P07_pulley26_hub': 1, 'P08_elbow_hub26': 1, 'P09_pulley20_D5': 2,
     'P10_link1_box': 1, 'P11_link1_lid': 1, 'P12_link2_box': 1, 'P13_link2_lid': 1, 'P14_pointer': 1,
     'P15_idler': 2, 'P16_belt_clamp': 2, 'P17_fork_stub': 1}
tg = tm = 0
rows = []
for n, q in Q.items():
    p = P[n]
    g = p['g'] * q
    m = 10 + 2.4 * g
    opt = n in ('P16_belt_clamp', 'P17_fork_stub')
    bb = 'x'.join(('%g' % v) for v in p['bbox'])
    rows.append('| %s%s | %d | %s | %s | %s | %.1f | %.1f | %.1f h |' % (n.replace('_', ' ', 1), ' (선택)' if opt else '', q, p['stl'], p['orient'], bb, p['vol'], p['g'], m / 60))
    if not opt:
        tg += g
        tm += m
rows.append('')
rows.append('합계(선택 제외): %d g, %.1f h' % (round(tg), tm / 60))
open('table_out.md', 'w', encoding='utf-8').write('\n'.join(rows))
