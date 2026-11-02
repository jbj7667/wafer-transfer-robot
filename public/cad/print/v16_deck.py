"""P01 하판 v3 (2026-11-02): 소나용 노치를 메우고 빠진 구멍을 추가.

문제: P01 오른쪽(-Y) 앞에 소나 노치(X 6~40, Y -71~-21)가 남아 있어서
 - 오른쪽 모터 브래킷 플랜지의 앞쪽 볼트 2개 자리 (14,-54),(14,-66)에 하판이 없음(2개만 체결 가능),
 - 오른쪽 마스트 블록 P23_R(X 3~27, Y -38~-22)이 하판 없이 허공에 걸침, 볼트 (6,-25),(6,-35) 자리도 없음.
소나는 기본 구성에서 제외(v1.1e)이므로 노치를 메운다. 입력은 P01_deck1_v2(캐스터 구멍, (-3,-43) 포함).
"""
from pathlib import Path

import trimesh

from v12_parts import cyl, diff, save, union

OUT = Path(__file__).parent
NOTCH = dict(x0=5.0, x1=40.0, y0=-71.5, y1=-20.5)      # 기존 하판과 0.5~1 mm 겹치게
HOLES = [(14.0, -54.0), (14.0, -66.0), (6.0, -25.0), (6.0, -35.0), (30.0, -65.0)]


def build():
    deck = trimesh.load(OUT / "P01_deck1_v2.stl")
    fill = trimesh.creation.box(extents=[NOTCH["x1"] - NOTCH["x0"], NOTCH["y1"] - NOTCH["y0"], 4.0])
    fill.apply_translation([(NOTCH["x0"] + NOTCH["x1"]) / 2, (NOTCH["y0"] + NOTCH["y1"]) / 2, 54.0])
    d = union([deck, fill])
    d = diff(d, [cyl(1.7, 8.0, (x, y, 54.0), "z", 24) for x, y in HOLES])
    r = save(d, OUT / "P01_deck1_v3.stl")
    print("P01 v3 vol cm3 %.2f -> %.2f" % (deck.volume / 1000, r.volume / 1000), r.bounds.round(1).tolist())
    # 확인: 각 구멍 주변 재료
    for x, y in HOLES:
        ring = [[x + dx, y + dy, 54.0] for dx in (-5, 5) for dy in (-5, 5)]
        print("(%g,%g) 주변 재료 %d/4, 구멍 중심 %s" % (x, y, r.contains(ring).sum(), "뚫림" if not r.contains([[x, y, 54.0]])[0] else "막힘"))


if __name__ == "__main__":
    build()
