# 접힘 자세가 250x250 안에 들어가는지, 회전대 축의 허용 위치. 실행: python -I fold.py (출력 fold_out.md)
import math
out = []
P = out.append


def hull_pts(Lk, phi_deg, r_tt=50, r_boss=20, fork_len=129, fork_w=118):
    phi = math.radians(phi_deg)
    pts = [(r_tt * math.cos(math.radians(a)), r_tt * math.sin(math.radians(a))) for a in range(0, 360, 10)]
    ex, ey = Lk * math.cos(phi), Lk * math.sin(phi)
    wx = 2 * Lk * math.cos(phi)
    for a in range(0, 360, 20):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        pts.append((ex + r_boss * c, ey + r_boss * s))
        pts.append((wx + r_boss * c, r_boss * s))
    for (x, y) in ((wx, fork_w / 2), (wx, -fork_w / 2), (wx + fork_len, fork_w / 2), (wx + fork_len, -fork_w / 2)):
        pts.append((x, y))
    return pts


def extents(pts, rot_deg, mirror=False):
    a = math.radians(rot_deg)
    c, s = math.cos(a), math.sin(a)
    q = [((p[0] * c - p[1] * s), (p[0] * s + p[1] * c)) for p in pts]
    if mirror:
        q = [(x, -y) for x, y in q]
    xs = [p[0] for p in q]
    ys = [p[1] for p in q]
    return min(xs), max(xs), min(ys), max(ys)


P("## F1. 접힘 자세(phi=105 deg, 손목이 어깨 뒤쪽)의 회전대 축 기준 외곽 (로봇 좌표 x 전진, y 왼쪽)")
P("팔 좌표 u(팔 방향)를 로봇 좌표로 회전한 각 = θ_stow. 한계: 로봇 x -92..+158 (길이 250), y +-125 (폭 250). 축 위치 (x_T, y_T)에서 외곽이 들어가는 범위를 구한다.")
P("| L | θ_stow | 외곽 x 폭 | 외곽 y 폭 | x_T 허용 범위 | y_T 허용 범위 | 판정 |")
P("|---|---|---|---|---|---|---|")
for Lk in (205, 190, 175):
    best = None
    for rot in range(0, 360, 2):
        for mir in (False, True):
            x0, x1, y0, y1 = extents(hull_pts(Lk, 105), rot, mir)
            W, H = x1 - x0, y1 - y0
            score = max(W, H)
            if best is None or score < best[0]:
                best = (score, rot, mir, x0, x1, y0, y1)
    sc, rot, mir, x0, x1, y0, y1 = best
    # 축 허용: -92 <= x_T + x0, x_T + x1 <= 158
    xr = (-92 - x0, 158 - x1)
    yr = (-125 - y0, 125 - y1)
    ok = '가능' if xr[0] <= xr[1] and yr[0] <= yr[1] else '불가'
    P(f"| {Lk} | {rot}{'(거울)' if mir else ''} | {x1-x0:.0f} | {y1-y0:.0f} | {xr[0]:.0f} ~ {xr[1]:.0f} | {yr[0]:.0f} ~ {yr[1]:.0f} | {ok} |")
P("")
P("해석: L=205는 외곽 약 248 x 241(회전 후)로 여유 약 2mm라 사실상 실패 위험. L=190이면 약 237로 여유 13mm. 도달 한계(K3) 때문에 L=190에서도 phi_min 29deg로 R_손목 332까지 48mm 여유가 있다.")

P("")
P("## F2. 축을 몸체 중앙 근처(x_T 0~40, |y_T|<=20)에 두고 들어가는 최대 허용 L과 θ_stow (스캔: 접힘 phi 90~125 deg, 회전 0~358)")
P("| L | phi_stow | θ_stow | x_T 범위 | y_T 범위 |")
P("|---|---|---|---|---|")
for Lk in (205, 190, 180, 175, 170, 160):
    found = None
    for phi in range(90, 126, 5):
        for rot in range(0, 360, 2):
            for mir in (False, True):
                x0, x1, y0, y1 = extents(hull_pts(Lk, phi), rot, mir)
                xr = (max(-92 - x0, 0), min(158 - x1, 40))
                yr = (max(-125 - y0, -20), min(125 - y1, 20))
                if xr[0] <= xr[1] and yr[0] <= yr[1]:
                    found = (phi, rot, mir, xr, yr)
                    break
            if found: break
        if found: break
    if found:
        phi, rot, mir, xr, yr = found
        P(f"| {Lk} | {phi} | {rot}{'(거울)' if mir else ''} | {xr[0]:.0f} ~ {xr[1]:.0f} | {yr[0]:.0f} ~ {yr[1]:.0f} |")
    else:
        P(f"| {Lk} | - | 불가 | - | - |")
open('fold_out.md', 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
