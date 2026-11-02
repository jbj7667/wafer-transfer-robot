"""Tr12x4 사다리꼴 나사 생성기 (출력용 리드스크류 / 일체 암나사 컷터 공용).

사용법
------
    import sys; sys.path.insert(0, "public/cad/print")      # 또는 같은 폴더에서 import
    from lift_thread import thread_rod, nut_hole_cutter

    rod = thread_rod(0, 110)                    # 외나사: 축 Z, 중심 (0,0), Z 0~110, 양 끝은 평평하게 잘림
    cut = thread_rod(z0 - 1, z1 + 1, clearance=0.3)   # 같은 나사산을 법선 방향으로 0.3 부풀린 구멍용 컷터
    nut = diff(body, [cut])                     # 암나사 = 몸통 - 컷터  (v12_parts.diff)
    cut2 = nut_hole_cutter(z0, z1, cx=15, cy=0) # 위와 같지만 중심 이동 + 위아래 1 mm 여유 + clearance 0.3 기본값

starts (줄 수): thread_rod(..., lead=8.0, starts=2) = Tr12x8(P4) 2줄 나사 (피치 = lead/starts = 4, 나사산 단면 동일,
두 나선을 180도 위상으로 스윕). 기본값은 호환용 lead=4, starts=1. nut_hole_cutter 의 기본값은 lead=8, starts=2.
  승강 나사 수나사: thread_rod(z0, z1, lead=8.0, starts=2)   암나사 컷터: nut_hole_cutter(z0, z1, cx, cy)
사양: 외경 12, 골경 8.4, 리드 4 (단줄, 오른나사: 위에서 보아 반시계로 돌면 +Z), 30도 사다리꼴(반각 15도),
수나사 마루폭 0.366*리드. 높이 방향 위상은 z0 기준 고정이라, 같은 호출 인자면 항상 같은 나사산이다
(나사산 위상 = z0 에서 각도 0, 마루 중심은 z = z0 + 리드*(theta/2pi) 에 있다 -> 암나사와 수나사를 같은
z0 로 만들면 위상이 맞고, 어긋나도 회전만 하면 되므로 간극은 동일).
clearance>0: 나사산 단면을 법선 방향으로 clearance 만큼 오프셋(마루 반경, 골 반경도 +clearance).
방법: 단면(사다리꼴)을 나선으로 스윕한 닫힌 솔리드 + 코어 원기둥을 manifold 합집합 -> z0~z1 로 자름.
"""
import math

import numpy as np
import trimesh
from shapely.geometry import Polygon

ENGINE = "manifold"
MAJOR, MINOR, LEAD = 12.0, 8.4, 4.0   # thread_rod 의 기본(1줄, 호환용)
LIFT_LEAD, LIFT_STARTS = 8.0, 2.0       # 승강 나사 Tr12x8(P4) 2줄: 피치 4, 리드 8
HALF_ANGLE = 15.0          # 30도 나사산각의 반각


def _tooth_profile(major, minor, pitch, clearance, half_angle, flank_trim=0.0):
    """(r, z) 평면의 나사산 단면 (마루 중심 z=0). 코어 안쪽으로 0.6 mm 파묻힌 사다리꼴, clearance 만큼 오프셋."""
    t = math.tan(math.radians(half_angle))
    rt, r0 = major / 2, minor / 2 - 0.6
    # flank_trim>0: 수나사 플랭크를 법선 방향으로 그만큼 깎는다 (마루/골 반경은 그대로, 이 두께만 얇아짐).
    # 축방향 환산 = trim/cos(half_angle). 너트와 닿는 면에만 추가 간극을 주려는 용도 (2026-11-02, 0.3).
    crest = 0.366 * pitch / 2 - flank_trim / math.cos(math.radians(half_angle))   # 마루 반폭
    pts = [(r0, -(crest + (rt - r0) * t)), (rt, -crest), (rt, crest), (r0, crest + (rt - r0) * t)]
    poly = Polygon(pts)
    if clearance:
        poly = poly.buffer(clearance, join_style=2, mitre_limit=10.0)
    c = list(poly.exterior.coords)[:-1]
    # 반시계 정렬 보장 + 중복 제거
    return c


def _sweep(profile, lead, zstart, turns, sections):
    n = len(profile)
    K = int(round(turns * sections))
    V = []
    for k in range(K + 1):
        th = 2 * math.pi * k / sections
        zs = zstart + lead * k / sections
        c, s = math.cos(th), math.sin(th)
        for (r, z) in profile:
            V.append((r * c, r * s, z + zs))
    V = np.array(V)
    F = []
    for k in range(K):
        for i in range(n):
            a, b = k * n + i, k * n + (i + 1) % n
            c_, d = (k + 1) * n + (i + 1) % n, (k + 1) * n + i
            F += [(a, b, c_), (a, c_, d)]
    for i in range(1, n - 1):
        F.append((0, i + 1, i))                    # 시작 캡
        F.append((K * n, K * n + i, K * n + i + 1))  # 끝 캡
    m = trimesh.Trimesh(V, np.array(F), process=True)
    if m.volume < 0:
        m.invert()
    return m


def thread_rod(z0, z1, major=MAJOR, minor=MINOR, lead=LEAD, clearance=0.0, sections=64,
               half_angle=HALF_ANGLE, starts=1, flank_trim=0.0):
    """Tr 나사 막대. 축 Z, 중심 (0,0), Z z0~z1 (양 끝 평면 절단). 닫힌 형상(watertight, is_volume)."""
    starts = int(starts)
    pitch = lead / starts
    prof = _tooth_profile(major, minor, pitch, clearance, half_angle, flank_trim)
    turns = (z1 - z0) / lead + 3.0
    zstart = z0 - 1.5 * lead
    tooth = _sweep(prof, lead, zstart, turns, sections)
    teeth = [tooth]
    for i in range(1, starts):                      # 나머지 줄: 360/starts 도씩 회전 (같은 중심)
        t = tooth.copy()
        t.apply_transform(trimesh.transformations.rotation_matrix(2 * math.pi * i / starts, [0, 0, 1]))
        teeth.append(t)
    core = trimesh.creation.cylinder(radius=minor / 2 + clearance, height=(z1 - z0) + 2 * lead,
                                     sections=sections * 2)
    core.apply_translation([0, 0, (z0 + z1) / 2])
    both = trimesh.boolean.union([core] + teeth, engine=ENGINE)
    big = major + 4 * clearance + 4
    box = trimesh.creation.box(extents=[big, big, z1 - z0])
    box.apply_translation([0, 0, (z0 + z1) / 2])
    out = trimesh.boolean.intersection([both, box], engine=ENGINE)
    assert out.is_watertight and out.is_volume, "thread_rod: 닫힌 형상 아님"
    return out


def nut_hole_cutter(z0, z1, cx=0.0, cy=0.0, clearance=0.3, extra=1.0, lead=LIFT_LEAD, starts=2, **kw):
    """암나사 컷터: z0~z1 구간 + 위아래 extra 만큼 연장, 중심 (cx, cy), 반경 간극 clearance."""
    m = thread_rod(z0 - extra, z1 + extra, clearance=clearance, lead=lead, starts=starts, **kw)
    m.apply_translation([cx, cy, 0])
    return m


if __name__ == "__main__":
    r = thread_rod(0, 30, lead=8.0, starts=2)
    c = thread_rod(-1, 31, clearance=0.3, lead=8.0, starts=2)
    print("rod", r.is_watertight, r.is_volume, r.bounds.round(2).tolist(), "vol %.1f" % r.volume)
    print("cutter", c.is_watertight, c.is_volume, c.bounds.round(2).tolist(), "vol %.1f" % c.volume)
