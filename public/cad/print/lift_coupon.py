"""공차 시험 조각: 큰 부품(마스트·캐리지·상판)을 뽑기 전에 프린터 공차를 확인한다.

P25t_fit_coupon : 판 100x34x6 — 사각 구멍 10.2/10.4/10.6, 원 구멍 Ø2.8/2.9/3.0(M3 자체탭), Ø3.4/3.5(관통), Ø6.8/7.0(저널)
P26t_rail_stub  : 10.0 x 10.0 x 30 레일 토막 — 위 사각 구멍에 끼워 보며 설계 간극(0.2/면 = 10.4)을 확인
출력: 둘 다 PETG, 층 0.2, 벽 3줄. 판은 바닥이 베드(구멍 수직), 토막은 눕혀서(레일과 같은 자세).
"""
from pathlib import Path

import trimesh
from shapely.geometry import Point, box

from v12_parts import cyl, diff, extrude, save

OUT = Path(__file__).parent


def coupon():
    plate = trimesh.creation.box(extents=[100.0, 34.0, 6.0])
    plate.apply_translation([50.0, 17.0, 3.0])
    cuts = []
    # 사각 구멍(위 줄)
    for i, s in enumerate((10.2, 10.4, 10.6)):
        cuts.append(trimesh.creation.box(extents=[s, s, 8.0]))
        cuts[-1].apply_translation([14.0 + i * 16.0, 24.0, 3.0])
    # 원 구멍(아래 줄)
    for i, d in enumerate((2.8, 2.9, 3.0, 3.4, 3.5, 6.8, 7.0)):
        cuts.append(cyl(d / 2, 8.0, (9.0 + i * 13.0, 9.0, 3.0), "z", 48))
    m = diff(plate, cuts)
    r = save(m, OUT / "P25t_fit_coupon.stl")
    print("P25t", r.bounds.round(1).tolist(), "vol cm3 %.1f" % (r.volume / 1000))


def stub():
    m = trimesh.creation.box(extents=[30.0, 10.0, 10.0])
    m.apply_translation([15.0, 5.0, 5.0])
    r = save(m, OUT / "P26t_rail_stub.stl")
    print("P26t", r.bounds.round(1).tolist())


if __name__ == "__main__":
    coupon()
    stub()
