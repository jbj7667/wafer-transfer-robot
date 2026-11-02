"""v1.3 볼 캐스터 반영 (실측: 캐스터 높이 29, 고정 구멍 2개 간격 57).

- P05_caster_spacer_v2: 하판 아랫면(Z=52)과 캐스터 장착면(Z=29) 사이 높이 23의 사각 기둥.
  구멍 2개(Y ±28.5, X=-75)를 위/아래에서 Ø2.8 자체탭(M3, 깊이 10)으로 뚫음(캐스터 구멍 지름은 미확인).
- P01_deck1_v2: 캐스터 체결용 Ø3.4 구멍 2개 (-75, ±28.5) 추가 (기존 (-75,±10)은 사용 안 함).
- P14_batt_cradle_v2_L/R: 바닥(Z 56~58)에 볼트 머리 접근 구멍 Ø8 추가. 캐스터 볼트가 하판 위에서 들어오는데
  크래들이 바로 그 위에 놓이기 때문.
"""
from pathlib import Path

import trimesh

from v12_parts import cyl, diff, save, union

OUT = Path(__file__).parent
CASTER_X, CASTER_DY = -75.0, 28.5        # 구멍 간격 57
Z_CASTER, Z_DECK = 29.0, 52.0
H = Z_DECK - Z_CASTER                    # 23
TAP_D, TAP_DEPTH = 2.8, 10.0


def spacer():
    bar = trimesh.creation.box(extents=[12.0, 2 * CASTER_DY + 10.0, H])
    bar.apply_translation([CASTER_X, 0, Z_CASTER + H / 2])
    cuts = []
    for sy in (-CASTER_DY, CASTER_DY):
        cuts.append(cyl(TAP_D / 2, TAP_DEPTH, (CASTER_X, sy, Z_CASTER + TAP_DEPTH / 2), "z", 24))   # 캐스터 쪽(아래)
        cuts.append(cyl(TAP_D / 2, TAP_DEPTH, (CASTER_X, sy, Z_DECK - TAP_DEPTH / 2), "z", 24))     # 하판 쪽(위)
    m = diff(bar, cuts)
    m.apply_translation([0, 0, -Z_CASTER])          # 출력 자세: 바닥이 베드(Z 0~23)
    r = save(m, OUT / "P05_caster_spacer_v2.stl")
    print("P05 v2", r.bounds.round(2).tolist(), "vol cm3 %.1f" % (r.volume / 1000))


def deck():
    m = trimesh.load(OUT / "P01_deck1.stl")
    cuts = [cyl(1.7, 8.0, (CASTER_X, sy, 54.0), "z", 24) for sy in (-CASTER_DY, CASTER_DY)]
    r = save(diff(m, cuts), OUT / "P01_deck1_v2.stl")
    print("P01 v2 vol cm3 %.2f -> %.2f" % (m.volume / 1000, r.volume / 1000))


def cradles():
    for side, sy in (("L", CASTER_DY), ("R", -CASTER_DY)):
        m = trimesh.load(OUT / f"P14_batt_cradle_{side}.stl")
        r = save(diff(m, [cyl(4.0, 4.0, (CASTER_X, sy, 57.0), "z", 32)]), OUT / f"P14_batt_cradle_v2_{side}.stl")
        print(f"P14 v2 {side} vol cm3 %.2f -> %.2f" % (m.volume / 1000, r.volume / 1000))


if __name__ == "__main__":
    spacer()
    deck()
    cradles()
