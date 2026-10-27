# arm_bench 헬퍼: print/lib_print.py 를 불러와 출력 경로만 바꾸고 보조 함수를 추가. Fusion 스크립트 맨 위에서
#   exec(open(r'<이 파일 경로>', encoding='utf-8').read())
ROOT = r'C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2\public\cad'
exec(open(ROOT + r'\print\lib_print.py', encoding='utf-8').read())
OUT = ROOT + r'\arm_bench'


def slot(c, cx, cy, z0, z1, w, ln, ax='x', cut=True):
    """장공 (폭 w, 중심선 길이 ln, ax 방향) z0..z1 관통/절단"""
    h = ln / 2.0
    if ax == 'x':
        box(c, (cx - h, cx + h), (cy - w / 2, cy + w / 2), (z0, z1), cut=cut)
        cyls(c, 'z', [(cx - h, cy, (z0 + z1) / 2), (cx + h, cy, (z0 + z1) / 2)], w, z1 - z0, cut=cut)
    else:
        box(c, (cx - w / 2, cx + w / 2), (cy - h, cy + h), (z0, z1), cut=cut)
        cyls(c, 'z', [(cx, cy - h, (z0 + z1) / 2), (cx, cy + h, (z0 + z1) / 2)], w, z1 - z0, cut=cut)


def teeth(c, cx, cy, N, z0, z1, od):
    """GT2 이빨 홈 근사: 팁원 둘레에 지름 1.4 원 N개를 절단"""
    pts = []
    zm = (z0 + z1) / 2.0
    for k in range(N):
        a = 2 * math.pi * k / N
        pts.append((cx + od / 2 * math.cos(a), cy + od / 2 * math.sin(a), zm))
    cyls(c, 'z', pts, 1.4, z1 - z0, cut=True)


def pulley(c, cx, cy, N, z0, hub_od=0.0, hub_z1=None, bore=8.2, fl=1.0, w=6.0):
    """GT2 폴리: 플랜지 지름 PD+3, 이빨부 폭 w, 양 플랜지 두께 fl"""
    pd = 2.0 * N / math.pi
    od = pd - 0.76
    zt = z0 + fl + w + fl
    cyls(c, 'z', [(cx, cy, z0 + fl / 2)], pd + 3.0, fl, cut=False)      # 아래 플랜지
    cyls(c, 'z', [(cx, cy, z0 + fl + w / 2)], od, w, cut=False)         # 이빨부
    cyls(c, 'z', [(cx, cy, zt - fl / 2)], pd + 3.0, fl, cut=False)      # 위 플랜지
    teeth(c, cx, cy, N, z0 + fl, z0 + fl + w, od)
    return zt


# 주의: 다른 부품과 같은 좌표에서 절단하면 먼저 만든 부품도 잘린다(직접 모델링 문서에서 확인).
# 그래서 부품을 하나 끝낼 때마다 X 방향 멀리 '주차'시킨다.
_done0 = done


def done(c, tag):
    _done0(c, tag)
    occs = list(des().rootComponent.occurrences)
    for i, o in enumerate(occs):
        if o.component.name == c.name:
            M = adsk.core.Matrix3D.create()
            M.translation = V3(100.0 * (i + 2), 0, 0)
            o.transform2 = M
