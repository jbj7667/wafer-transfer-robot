"""v1.4 점검 반영 수정 (조립 점검 + 레드팀).

1. P06 라인 헤드/행어: DC 모터 몸통(Ø35, 중심 X=0, Z=25, Y 1~70.5)과 겹쳐서 몸통 + 여유 1을 파냄.
   (조립 점검: 헤드 235 mm³, 행어 84 mm³ 겹침 x 2). 헤드는 판 뒤쪽 모서리가 약간 깎인다.
2. P16 바퀴 v2: 립을 Ø64 → Ø62 (타이어 OD 65가 눌려도 PETG 립이 바닥에 닿지 않게).
3. P01 하판 v3: 상판 일체 4번째 기둥용 구멍 (-3, -43) 추가 ((30,-65)는 소나 노치라 하판 재료 없음). 캐스터 구멍은 v13_caster.py가 만든 v2에 더한다.
"""
import sys
from pathlib import Path

import trimesh
from shapely.geometry import Point, box

from v12_parts import ENGINE, cyl, diff, extrude, save, union

OUT = Path(__file__).parent
MOTOR_R, MOTOR_Z, CLEAR = 17.5, 25.0, 1.0


def motor_cutters(extra=0.0):
    r = MOTOR_R + CLEAR + extra
    return [cyl(r, 70.0, (0.0, sy * 36.0, MOTOR_Z), "y", 96) for sy in (-1, 1)]


def fix_p06():
    for n in ("line_head_t0", "line_head_t5", "line_head_t10", "line_head_t15", "line_hanger"):
        p = OUT / f"P06_{n}.stl"
        m = trimesh.load(p)
        new = diff(m, motor_cutters(0.0 if n != "line_hanger" else -0.5))
        parts = new.split(only_watertight=False)
        r = save(new, p)
        print(p.name, "vol cm3 %.2f -> %.2f" % (m.volume / 1000, r.volume / 1000), "bodies", len(parts))


def wheel_v2():
    lip_r = 31.0
    ring = extrude(Point(0, 0).buffer(30.0, resolution=96).difference(Point(0, 0).buffer(26.0, resolution=96)), 26.0)
    lip_out = extrude(Point(0, 0).buffer(lip_r, resolution=96).difference(Point(0, 0).buffer(29.0, resolution=96)), 1.5)
    lip_in = extrude(Point(0, 0).buffer(lip_r, resolution=96).difference(Point(0, 0).buffer(29.0, resolution=96)), 1.5, 22.5)
    web = extrude(Point(0, 0).buffer(26.5, resolution=96), 3.0)
    hub = extrude(Point(0, 0).buffer(7.5, resolution=64), 30.0)
    body = union([ring, lip_out, lip_in, web, hub])
    bore2d = Point(0, 0).buffer(3.05, resolution=48).intersection(box(-4, -4, 2.5, 4))
    body = diff(body, [extrude(bore2d, 8.6, 21.5), cyl(1.4, 10.0, (6.0, 0, 24.5), "x", 24)])
    r = save(body, OUT / "P16_wheel_body_v2.stl")
    print("P16 v2 bbox", r.bounds.round(2).tolist(), "vol cm3 %.1f" % (r.volume / 1000))


def deck_v3():
    p = OUT / "P01_deck1_v2.stl"
    m = trimesh.load(p)
    cuts = [cyl(1.7, 8.0, (-3.0, -43.0, 54.0), "z", 24)]
    r = save(diff(m, cuts), OUT / "P01_deck1_v2.stl")
    print("P01 v2 + (-3,-43): vol cm3 %.3f -> %.3f" % (m.volume / 1000, r.volume / 1000))


def trim_heads(zmin=3.0):
    """경사 헤드 t5/t10/t15 후드 아랫단을 Z >= zmin 으로 평평하게 자름 (최저점 0.35~2.9 mm → 3 mm, 레드팀)."""
    for n in ("line_head_t5", "line_head_t10", "line_head_t15"):
        p = OUT / f"P06_{n}.stl"
        m = trimesh.load(p)
        if m.bounds[0][2] >= zmin - 1e-6:
            print(p.name, "이미 Z >=", zmin)
            continue
        cutter = trimesh.creation.box(extents=[200.0, 200.0, 20.0])
        cutter.apply_translation([25.0, 0.0, zmin - 10.0])
        r = save(diff(m, [cutter]), p)
        print(p.name, "min Z %.2f -> %.2f, bodies %d" % (m.bounds[0][2], r.bounds[0][2], len(r.split(only_watertight=False))))


if __name__ == "__main__":
    # 주의: p06 → trim 순서로 실행 (p06은 원본 STL이 아니라 현재 파일에 홈을 다시 판다 — 멱등)
    which = sys.argv[1:] or ["p06", "trim", "wheel", "deck"]
    if "p06" in which:
        fix_p06()
    if "trim" in which:
        trim_heads()
    if "wheel" in which:
        wheel_v2()
    if "deck" in which:
        deck_v3()
