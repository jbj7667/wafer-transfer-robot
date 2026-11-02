"""P16 바퀴 본체 v3 (사용자 수정 요청 2026-11-02).

변경점 (v2 대비):
1. 축 구멍을 허브 끝까지 **완전 관통** (바깥면 z'=0 ~ 안쪽 끝 z'=30).
2. 구멍 **양쪽 끝 8 mm는 D가 아닌 완전한 원(Ø6.1)**, 가운데(z' 8~22)만 D.
3. 허브가 바닥판과 만나는 **안쪽 모서리에 필렛**(FILLET_R, 요청 'r50'은 허브 반경 7.5·바닥판 반경 26이라 불가능 → R5로 해석, 필요 시 상수 변경).
좌표: 바퀴 축 = z, z'=0 바깥면(베드), z'=30 안쪽 허브 끝. 나머지 치수는 v2와 동일(림 Ø60×26, 립 Ø62, 허브 Ø15).
"""
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Point, box

from v12_parts import cyl, diff, extrude, save, union

OUT = Path(__file__).parent
FILLET_R = 20.0         # 허브-바닥판 안쪽 모서리 필렛 반경 (mm) — 사용자 요청 R20 (R5에서 변경)
HUB_R, WEB_T = 7.5, 3.0
BORE_R, FLAT_X = 3.05, 2.5
ROUND_END = 8.0         # 양쪽 끝 원형 구간 길이
SETSCREW_Z = 24.5


def fillet_ring(r0, z0, rad):
    cx, cz = r0 + rad, z0 + rad
    th = np.radians(np.linspace(270, 180, 32))
    arc = np.c_[cx + rad * np.cos(th), cz + rad * np.sin(th)]
    prof = np.vstack([[r0 - 0.3, z0 - 0.3], [r0 + rad, z0 - 0.3], arc, [r0 - 0.3, z0 + rad], [r0 - 0.3, z0 - 0.3]])
    return trimesh.creation.revolve(prof, sections=96)


def build():
    lip_r = 31.0
    ring = extrude(Point(0, 0).buffer(30.0, resolution=96).difference(Point(0, 0).buffer(26.0, resolution=96)), 26.0)
    lip_out = extrude(Point(0, 0).buffer(lip_r, resolution=96).difference(Point(0, 0).buffer(29.0, resolution=96)), 1.5)
    lip_in = extrude(Point(0, 0).buffer(lip_r, resolution=96).difference(Point(0, 0).buffer(29.0, resolution=96)), 1.5, 22.5)
    web = extrude(Point(0, 0).buffer(26.5, resolution=96), WEB_T)
    hub = extrude(Point(0, 0).buffer(HUB_R, resolution=64), 30.0)
    parts = [ring, lip_out, lip_in, web, hub]
    if FILLET_R > 0:
        parts.append(fillet_ring(HUB_R, WEB_T, FILLET_R))
    body = union(parts)

    round2d = Point(0, 0).buffer(BORE_R, resolution=48)
    d2d = round2d.intersection(box(-4, -4, FLAT_X, 4))
    L = 30.0
    cuts = [
        extrude(round2d, ROUND_END + 0.2, -0.1),                         # 바깥 끝 원형 8
        extrude(d2d, L - 2 * ROUND_END, ROUND_END),                       # 가운데 D (z' 8~22)
        extrude(round2d, ROUND_END + 0.2, L - ROUND_END),                 # 안쪽 끝 원형 8 (z' 22~30.2)
        cyl(1.4, 10.0, (6.0, 0, SETSCREW_Z), "x", 24),                    # 세트스크류 Ø2.8 (+x, 안쪽 원형 구간 안)
    ]
    body = diff(body, cuts)
    r = save(body, OUT / "P16_wheel_body_v3.stl")
    print("P16 v3 bbox", r.bounds.round(2).tolist(), "vol cm3 %.1f" % (r.volume / 1000), "fillet R", FILLET_R)
    # 구멍 관통 확인: 중심선을 따라 z 방향 광선이 몸체에 맞지 않아야 함(축 구멍 중앙 Ø 작은 값)
    org = np.array([[0.0, 0.0, -5.0], [0.0, 0.0, 35.0]])
    hit0, _, _ = r.ray.intersects_location(org[:1], [[0, 0, 1.0]])
    hit1, _, _ = r.ray.intersects_location(org[1:], [[0, 0, -1.0]])
    print("중심선 관통: 바깥쪽 광선 명중 %d, 안쪽 광선 명중 %d (0이면 완전 관통)" % (len(hit0), len(hit1)))


if __name__ == "__main__":
    build()
