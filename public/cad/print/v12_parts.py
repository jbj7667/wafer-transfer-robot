"""v1.2 출력 부품 생성 (Fusion 없이 Python/trimesh 직접 생성).

P04 모터 브래킷 / P16 바퀴 본체 / P17 TPU 타이어 / P06 라인 헤드 슬롯 수정.
기준: params.md '실측값'. 좌표계는 로봇 좌표(+X 전진, +Y 좌, +Z 위) 값을 쓰고,
P04 STL은 출력 자세(판 바깥면이 베드)로 내보낸다: print(x, y, z) = (X, Z, 74.5 - Y).
"""
import math
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

OUT = Path(__file__).parent
ENGINE = "manifold"


def cyl(r, h, center, axis="z", sections=48):
    """원기둥. center = 중심 좌표, axis = 'x'|'y'|'z'."""
    m = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
    if axis == "x":
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
    elif axis == "y":
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    m.apply_translation(center)
    return m


def union(ms):
    return trimesh.boolean.union(ms, engine=ENGINE)


def diff(a, bs):
    return trimesh.boolean.difference([a] + list(bs), engine=ENGINE)


def save(mesh, path):
    """float32 저장 시 생기는 틈을 막기 위해 좌표를 0.001 mm로 정리하고, 다시 읽어 닫힌 형상인지 확인."""
    m = mesh.copy()
    m.vertices = np.round(m.vertices, 3)
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.export(path)
    r = trimesh.load(path)
    assert r.is_watertight and r.is_volume, f"{path}: 저장 후 닫힌 형상이 아님"
    return r


def extrude(poly, h, z0=0.0):
    m = trimesh.creation.extrude_polygon(poly, h)
    m.apply_translation([0, 0, z0])
    return m


# ---------------------------------------------------------------- P04 모터 브래킷
def make_p04():
    Y_FACE, T = 70.5, 4.0                # 모터 출력면, 판 두께 (판 Y 70.5~74.5)
    Y_OUT = Y_FACE + T                   # 74.5 = print z 0
    ZC, R_PCD, SHAFT_OFF = 25.0, 15.21, 7.5
    ang = (55.0, 175.0, 295.0)           # 축 방향(위) 0°, 출력면에서 시계방향
    # 왼쪽 모터(+Y, +Y에서 봄: 시야 오른쪽 = -X): X = -u, Z = ZC + v
    holes = []
    for a in ang:
        u, v = R_PCD * math.sin(math.radians(a)), R_PCD * math.cos(math.radians(a))
        holes.append((-u, ZC + v))
    shaft = (0.0, ZC + SHAFT_OFF)        # (0, 32.5) = 차축
    # 판 윤곽: 윗 직사각형 + 구멍 3개 둘레 hull
    lugs = unary_union([Point(h).buffer(4.8) for h in holes]).convex_hull
    outline = unary_union([box(-24, 28, 24, 52), lugs]).buffer(2).buffer(-2)
    outline = outline.difference(Point(*shaft).buffer(9.0, resolution=48))
    for h in holes:
        outline = outline.difference(Point(*h).buffer(1.7, resolution=24))
    plate = extrude(outline, T)          # print (x=X, y=Z, z=74.5-Y)

    # 상부 플랜지: Z 45~52(7 두께), X ±23, Y 49~74.5 (print z 0~25.5)
    flange = trimesh.creation.box(extents=[46, 7, 25.5])
    flange.apply_translation([0, 48.5, 12.75])
    # 삼각 리브: X ±21(두께 4), (Y,Z) = (70.5,45) (70.5,33) (58,45) -> print (z,y)
    tri = trimesh.creation.extrude_polygon(Polygon([(4, 45), (4, 33), (16.5, 45)]), 4)
    # extrude_polygon: 평면 (a=z, b=y), 압출 h -> x. (a,b,h) -> (x=h, y=b, z=a)
    tri.vertices = tri.vertices[:, [2, 1, 0]]
    tri.invert()
    ribs = []
    for sx in (-21.0, 21.0):
        r = tri.copy()
        r.apply_translation([sx - 2.0, 0, 0])
        ribs.append(r)
    body = union([plate, flange] + ribs)

    # 플랜지 체결: Ø3.4 관통(수직=y축) + 아래쪽 너트 포켓(AF 5.7, 깊이 2.6)
    cuts = []
    for sx in (-14.0, 14.0):
        for yy in (54.0, 66.0):
            z = Y_OUT - yy
            cuts.append(cyl(1.7, 12, (sx, 48.5, z), "y", 24))
            hexp = trimesh.creation.cylinder(radius=5.7 / math.sqrt(3), height=5.2, sections=6)
            hexp.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
            hexp.apply_translation([sx, 45.0, z])
            cuts.append(hexp)
    body = diff(body, cuts)
    assert body.is_watertight and body.volume > 0, "P04 mesh error"

    # 간섭 검사: 모터 몸통 Ø35, Y 1~70.5 (print z 4~73.5), 중심 (x=0, y=ZC)
    motor = cyl(17.5, 69.5, (0, ZC, 4 + 69.5 / 2), "z", 64)
    inter = trimesh.boolean.intersection([body, motor], engine=ENGINE)
    iv = inter.volume if len(inter.vertices) else 0.0
    print("P04 bbox", body.bounds.round(2).tolist(), "vol cm3 %.1f" % (body.volume / 1000),
          "motor overlap mm3 %.2f" % iv, "min Z (ground clr) %.2f" % body.bounds[0][1])
    for n in ("P04_motor_brkt_L.stl", "P04_motor_brkt_R.stl"):
        save(body, OUT / n)
    return body


# ---------------------------------------------------------------- P16 바퀴 + P17 타이어
def make_wheel():
    """바퀴 축 = z, z'=0 바깥면(베드), z'=30 안쪽 허브 끝. 림 폭 26, 허브는 림 안쪽으로 4 돌출."""
    ring = extrude(Point(0, 0).buffer(30.0, resolution=96).difference(Point(0, 0).buffer(26.0, resolution=96)), 26.0)
    lip_out = extrude(Point(0, 0).buffer(32.0, resolution=96).difference(Point(0, 0).buffer(29.0, resolution=96)), 1.5)
    lip_in = extrude(Point(0, 0).buffer(32.0, resolution=96).difference(Point(0, 0).buffer(29.0, resolution=96)), 1.5, 22.5)
    web = extrude(Point(0, 0).buffer(26.5, resolution=96), 3.0)
    hub = extrude(Point(0, 0).buffer(7.5, resolution=64), 30.0)
    body = union([ring, lip_out, lip_in, web, hub])
    # D축 구멍: Ø6.1에 플랫 x<=2.5, 깊이 8.5 (z' 21.5~30), 고정나사 Ø2.8 (+x 방향, z'=26)
    bore2d = Point(0, 0).buffer(3.05, resolution=48).intersection(box(-4, -4, 2.5, 4))
    bore = extrude(bore2d, 8.6, 21.5)
    screw = cyl(1.4, 10.0, (6.0, 0, 26.0), "x", 24)
    body = diff(body, [bore, screw])
    assert body.is_watertight and body.volume > 0, "wheel mesh error"
    save(body, OUT / "P16_wheel_body.stl")
    print("P16 wheel bbox", body.bounds.round(2).tolist(), "vol cm3 %.1f" % (body.volume / 1000))

    tire = extrude(Point(0, 0).buffer(32.5, resolution=128).difference(Point(0, 0).buffer(29.7, resolution=128)), 20.5)
    save(tire, OUT / "P17_wheel_tire_TPU.stl")
    print("P17 tire bbox", tire.bounds.round(2).tolist(), "vol cm3 %.1f" % (tire.volume / 1000))


# ---------------------------------------------------------------- P06 헤드 슬롯
def fix_p06():
    for n in ("t0", "t5", "t10", "t15"):
        p = OUT / f"P06_line_head_{n}.stl"
        m = trimesh.load(p)
        cuts = []
        for s in (-1, 1):
            for y in np.arange(24.0, 28.01, 0.5):
                cuts.append(cyl(1.75, 10.0, (25.0, s * y, 14.0), "z", 24))
        new = diff(m, cuts)
        assert new.is_watertight and new.volume > 0, n
        save(new, p)
        print(p.name, "vol cm3 %.2f -> %.2f" % (m.volume / 1000, new.volume / 1000))


if __name__ == "__main__":
    make_p04()
    make_wheel()
    fix_p06()
