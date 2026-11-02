"""너트 시험 조각 간극 변형 (P21t_nut_test 가 입구부터 안 들어갈 때, 2026-11-02).

P21t_nut_c05 / c07 / c09 : 암나사 반경 간극 0.5 / 0.7 / 0.9 mm (기본 0.3) + 양 끝 입구 모따기(Ø8.4→Ø12.6 깔때기).
P20t_screw_test(수나사)와 짝으로 시험하고, 부드럽게 돌아가는 가장 작은 간극을 알려 주면
`lift_mast.py`(P24 플로팅 너트)·`lift_screw.py`의 clearance 상수를 그 값으로 바꿔 재생성한다.
"""
import math
from pathlib import Path

import numpy as np
import trimesh

from lift_thread import nut_hole_cutter
from v12_parts import diff, save

OUT = Path(__file__).parent


def chamfer_cutter(z_face, outward, r_in=6.0, r_out=8.0, depth=2.0):
    """입구 깔때기: 면(z_face)에서 반지름 r_out, 안으로 depth 들어가며 r_in 으로 좁아짐(회전체)."""
    s = 1.0 if outward > 0 else -1.0       # outward=+1: 위쪽 면(z_face 위가 바깥), -1: 아래쪽 면
    prof = np.array([[3.0, z_face + s * 0.2], [r_out + 0.2, z_face + s * 0.2], [r_in, z_face - s * depth],
                     [3.0, z_face - s * depth], [3.0, z_face + s * 0.2]])
    m = trimesh.creation.revolve(prof, sections=96)
    m.merge_vertices()
    if m.volume < 0:                       # 단면 방향에 따라 법선이 뒤집혀 나오면 바로잡는다
        m.invert()
    assert m.is_volume, "chamfer cutter is not a volume"
    return m


def make(clearance, name):
    body = trimesh.creation.cylinder(radius=20 / math.sqrt(3), height=12, sections=6)
    body.apply_translation([0, 0, 6])
    cutters = [nut_hole_cutter(0, 12, 0, 0, clearance=clearance),
               chamfer_cutter(0.0, -1.0), chamfer_cutter(12.0, +1.0)]
    nut = diff(body, cutters)
    r = save(nut, OUT / name)
    print(name, "clearance %.1f" % clearance, "vol cm3 %.2f" % (r.volume / 1000), "bbox", r.bounds.round(1).tolist())


if __name__ == "__main__":
    for c, n in ((0.5, "P21t_nut_c05.stl"), (0.7, "P21t_nut_c07.stl"), (0.9, "P21t_nut_c09.stl")):
        make(c, n)
