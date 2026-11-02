"""승강부 v2 마스트: P23 일체 마스트(하부 블록+레일) L/R, P10 상부 블록, P12 캐리지.

실행(워크트리 루트):  python public/cad/print/lift_mast.py [mast|upper|carriage|nut|check|all]
  mast     P23_mast_L/R 생성        upper  P10_mast_upper_v2 생성
  carriage P12_carriage_v2 생성     check  간섭 검사(생성된 STL이 아니라 같은 함수로 다시 만든 메쉬 사용)
  all      전부(기본). 각 단계는 독립이라 부분 실행해도 placement_mast.json 은 항목별로 갱신된다.
좌표 = 로봇 좌표(+X 전진, +Y 좌, +Z 위, mm). STL은 출력 자세. 행렬 M: p_robot = M @ p_print (row-major 16).

설계 결정
- P23: 하부 블록(X3~27, Y sy±8, Z56~72)과 레일(10x10, Z56~240)을 한 덩어리로. 접합부에 45도 리브(Z72~79, X 양쪽).
  하판 체결 = 하판 아래에서 M3x16 을 올려 블록의 Ø2.8 자체탭(Z56~70). 레일 윗끝(Z236, +X 면)에 P10 고정용
  M3 자체탭 Ø2.8 깊이 8.5. 레일 윗끝 모따기 0.5.
  출력 자세: 레일 길이 방향이 베드와 평행, 블록의 안쪽 면(|Y|=22)이 베드. 레일은 베드에서 3 mm 떠 있어
  레일 아래에 얇은 서포트가 필요하다(블록 때문에 레일 면을 베드에 둘 수 없음).
- P10: 소켓 10.4(편측 0.2) 깊이 8, 저널 구멍 Ø7.0, 측면 고정은 Ø3.4 관통(M3x16 이 P10 벽을 지나 레일 탭에 체결).
- P12: IR 센서를 X≈58, Y≈+27 로 이동(센서면 Z=zc-6, 바닥판 2 mm). 포크 체결 탭 (X11·23, Y±17).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Point, Polygon
from shapely.geometry import box as sbox

sys.path.insert(0, str(Path(__file__).parent))
from v12_parts import OUT, cyl, diff, save, union  # noqa: E402

ENGINE = "manifold"
RHO, INFILL, SHELL_T = 1.27, 0.4, 1.2

# ---- 상수 (수정 시 재생성) ----
RAIL = 10.0
RAIL_CH = 0.3                # 레일 모서리 모따기
RAIL_TOP_CH = 0.5            # 레일 윗끝 모따기
RAIL_Z0, RAIL_Z1 = 56.0, 240.0
SOCK = 10.4                  # P10 레일 소켓 (편측 0.2)
CAR_HOLE = 10.4              # 캐리지 레일 구멍 (편측 0.2)
JOURNAL_HOLE_R = 3.5         # P10 저널 구멍 Ø7.0
NUT_CLEARANCE = 0.3          # P24 너트 암나사 반경 간극
BODY_X0 = -4.0               # 캐리지 뒷면 (카운터보어가 X -1.5 까지 가므로 뒤로 확장; 앞면 X=28 은 포크 루트 때문에 고정)
NUT_HOLE_R = 11.0            # 캐리지 관통 구멍 Ø22 (너트 몸통 Ø20, 반경 유동 ±1.0)
NUT_BODY_R, NUT_BODY_L = 10.0, 20.0
NUT_FL_R, NUT_FL_T = 15.5, 3.5       # 플랜지 Ø31 x 3.5 (D형: 앞면 평면 X=26, Y 평면 ±12.5)
NUT_FL_FRONT, NUT_FL_HALFY = 11.0, 12.5
POCKET_R, POCKET_HALFY, POCKET_DEPTH = 16.5, 13.5, 3.8   # 카운터보어 Ø33, Y 평면 ±13.5 (회전 방지), 앞쪽은 열림, 깊이 3.8 (상하 유동 0.3)
RAIL_X = 15.0
RAIL_Y = (30.0, -30.0)
FORK_BOLT_X = (11.0, 23.0)
FORK_BOLT_Y = 17.0
# ---- IR 센서 GP2Y0A21YK0F (실측): 본체 29.5(Y) x 13(X), 귀 포함 44.5, 전체 높이 18.9(렌즈 케이스 포함), 귀 Ø3.2 간격 37,
#      귀 두께 1.2 (렌즈면에서 3.3 아래), 렌즈 중심 = 본체 중심 기준 긴 변 방향 -11.3 / +10.1 (앞면 사진 오른쪽이 +Y) ----
IR_BODY_L, IR_BODY_W, IR_TOTAL_H = 29.5, 13.5, 18.9   # 폭 13.5 실측(2026-11-02, 창이 13.4라 안 들어갔음)
IR_EAR_SPAN, IR_EAR_Z, IR_EAR_T = 37.0, 3.3, 1.2
IR_LENS_DY = (-11.3, 10.1)
IR_LENS_R = 4.2                          # 광선 시험용 보수적 반경
IR_CX, IR_CY = 54.7, 22.7                # 센서 중심 (X, Y): 렌즈 Y = 11.4 / 32.8 (U 개구 |Y|<39 안쪽 6.2), 렌즈 X 50.5~58.9
FORK_F_ABOVE_ZC = 36.0                   # f = zc + 36
IR_FACE_BELOW_F = 42.0                   # 센서면 = f - 42  (필요 시 +-3 조정)
IR_FACE_DZ = FORK_F_ABOVE_ZC - IR_FACE_BELOW_F     # 센서면 Z = zc + IR_FACE_DZ
IR_PLATE_T = 4.0
IR_WIN_L, IR_WIN_W = IR_BODY_L + 0.8, IR_BODY_W + 0.8     # 플레이트 창
IR_PLATE_X0 = 44.0                       # 플레이트 뒤끝(뒷 웹), 암 바와 겹침
IR_PLATE_FRONT = IR_CX + IR_WIN_W / 2 + 2.2             # 플레이트 앞 가장자리 (= 60.2 <= 61, 목 R25 @ X92 회피)
IR_PLATE_MARGIN_Y = 5.5
assert IR_PLATE_FRONT <= 64.5   # 목 R25 @ (92,0): 판 앞모서리(64,-1.3)까지 28 > 25
ZC0, ZC1 = 119.0, 191.0


def box(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return m


def prism_xz(pts, y0, y1):
    """(X,Z) 다각형을 Y y0~y1 로 압출."""
    m = trimesh.creation.extrude_polygon(Polygon(pts), y1 - y0)
    m.vertices = m.vertices[:, [0, 2, 1]]
    m.vertices[:, 1] += y0
    m.fix_normals()
    if m.volume < 0:
        m.invert()
    return m


def oct_poly(cx, cy, half, c):
    h = half
    pts = [(-h + c, -h), (h - c, -h), (h, -h + c), (h, h - c), (h - c, h), (-h + c, h), (-h, h - c), (-h, -h + c)]
    return [(cx + x, cy + y) for x, y in pts]


def mass_g(m):
    shell = min(m.area * SHELL_T, m.volume)
    return RHO * (shell + INFILL * (m.volume - shell)) / 1000.0


def flat(M):
    return [round(float(v), 6) for v in np.asarray(M).reshape(-1)]


def apply(m, M):
    r = m.copy()
    r.apply_transform(M)
    return r


def to_print(m, M):
    """로봇 좌표 메쉬 -> 출력 자세 (M 은 출력->로봇)."""
    return apply(m, np.linalg.inv(M))


def update_placement(name, entry):
    p = OUT / "placement_mast.json"
    d = {"convention": "p_robot = M @ p_print ; M 4x4 row-major 16 ; 단위 mm", "parts": {}}
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
    for old in ("P22_rail.stl", "P09_mast_lower_v2_L.stl", "P09_mast_lower_v2_R.stl"):
        d["parts"].pop(old, None)           # 폐기 (P23 로 교체)
    d["parts"][name] = entry
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- P23 일체 마스트
def make_p23_robot(sy):
    """로봇 좌표의 일체 마스트. sy = +30(L) / -30(R)."""
    block = box(3, 27, sy - 8, sy + 8, 56, 72)
    z_top = RAIL_Z1 - RAIL_TOP_CH
    rail = trimesh.creation.extrude_polygon(Polygon(oct_poly(RAIL_X, sy, RAIL / 2, RAIL_CH)), z_top - RAIL_Z0)
    rail.apply_translation([0, 0, RAIL_Z0])
    inner = Polygon(oct_poly(RAIL_X, sy, RAIL / 2 - RAIL_TOP_CH, RAIL_CH))
    ring_a = np.array([(x, y, z_top) for x, y in oct_poly(RAIL_X, sy, RAIL / 2, RAIL_CH)])
    ring_b = np.array([(x, y, RAIL_Z1) for x, y in inner.exterior.coords][:-1])
    cap = trimesh.convex.convex_hull(np.vstack([ring_a, ring_b]))
    ribs = []
    for pts in ([(19, 71), (27, 71), (27, 72), (20, 79), (19, 79)], [(11, 71), (3, 71), (3, 72), (10, 79), (11, 79)]):
        ribs.append(prism_xz(pts, sy - 5, sy + 5))
    body = union([block, rail, cap] + ribs)
    cuts = []
    for dy in (-5, 5):                                   # 하판 체결: 아래에서 M3x16, Ø2.8 자체탭 Z56~70
        cuts.append(cyl(1.5, 14.5, (6, sy + dy, 55.75 + 14.5 / 2), "z", 24))
    cuts.append(cyl(1.5, 8.5, (21.0 - 4.25, sy, 236.0), "x", 24))   # P10 고정 M3 탭: X 12.5~21, +X 면에서
    return diff(body, cuts)


def p23_matrix(sy):
    if sy > 0:   # 출력 (x,y,z) -> 로봇: Z=56+x, X=y, Y=22+z   (안쪽 면 Y=22 가 베드)
        R = [[0, 1, 0, 0], [0, 0, 1, 22], [1, 0, 0, 56], [0, 0, 0, 1]]
    else:        # 거울 부품: Z=56+x, X=30-y, Y=-22-z  (proper rotation, 안쪽 면 Y=-22 가 베드)
        R = [[0, -1, 0, 30], [0, 0, -1, -22], [1, 0, 0, 56], [0, 0, 0, 1]]
    return np.array(R, float)


def make_mast():
    out = {}
    for sy, n in ((30.0, "P23_mast_L.stl"), (-30.0, "P23_mast_R.stl")):
        m = make_p23_robot(sy)
        M = p23_matrix(sy)
        p = to_print(m, M)
        p.apply_translation(-p.bounds[0] * 0)        # 이미 베드 위(z>=0) 확인
        assert abs(p.bounds[0][2]) < 1e-6 and abs(p.bounds[0][0]) < 1e-6, p.bounds
        save(p, OUT / n)
        update_placement(n, {"qty": 1, "matrix": flat(M),
                             "note": "레일 길이 방향 = 출력 X, 안쪽 면(|Y|=22)이 베드, 레일 아래 서포트 필요. R 은 좌우 거울 부품"})
        out[n] = m
    return out


# ---------------------------------------------------------------- P10 상부 블록
def make_p10_robot():
    body = box(0, 30, -38, 38, 232, 245)
    cuts = []
    for sy in RAIL_Y:
        cuts.append(box(RAIL_X - SOCK / 2, RAIL_X + SOCK / 2, sy - SOCK / 2, sy + SOCK / 2, 231.5, 240))
        cuts.append(cyl(1.7, 10.5, (25.0, sy, 236), "x", 24))        # Ø3.4 관통 (X 19.75~30.25), M3x16 -> 레일 탭
    cuts.append(cyl(JOURNAL_HOLE_R, 9.5, (RAIL_X, 0, 231.5 + 9.5 / 2), "z", 48))   # Z 231.5~241
    return diff(body, cuts)


P10_M = np.array([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 245], [0, 0, 0, 1]], float)


def make_upper():
    m = make_p10_robot()
    save(to_print(m, P10_M), OUT / "P10_mast_upper_v2.stl")
    update_placement("P10_mast_upper_v2.stl", {"qty": 1, "matrix": flat(P10_M),
                                               "note": "캡면(Z245)이 베드, 소켓·저널 구멍 위로 열림"})
    return m


# ---------------------------------------------------------------- P12 캐리지
def make_carriage(zc=ZC0, thread=True):
    z0, z1 = zc, zc + 30
    body = box(BODY_X0, 28, -40, 40, z0, z1)
    zf = zc + IR_FACE_DZ                       # 센서면 (위를 향함)
    zpt = zf - IR_EAR_Z - IR_EAR_T             # 플레이트 윗면 = 귀 아랫면
    zpb = zpt - IR_PLATE_T                     # 플레이트 바닥
    px0, px1 = IR_PLATE_X0, IR_PLATE_FRONT
    ea = IR_EAR_SPAN / 2
    py0, py1 = IR_CY - ea - IR_PLATE_MARGIN_Y, IR_CY + ea + IR_PLATE_MARGIN_Y
    plate = box(px0, px1, py0, py1, zpb, zpt)
    bar_b = zpb + 2.5                          # 암 바 바닥 = 플레이트 바닥 + 2.5 (P02 Z103 위로 여유)
    bar = box(26, px0 + 2.0, 8.0, 40.0, bar_b, bar_b + IR_PLATE_T)
    wedge = prism_xz([(26, z0 + 2), (28, z0 + 2), (28 + (z0 + 2 - bar_b), bar_b), (26, bar_b)], 8.0, 40.0)   # 45도 받침
    body = union([body, plate, bar, wedge])
    cuts = []
    for sy in RAIL_Y:
        cuts.append(box(RAIL_X - CAR_HOLE / 2, RAIL_X + CAR_HOLE / 2, sy - CAR_HOLE / 2, sy + CAR_HOLE / 2, z0 - 1, z1 + 1))
    for bx in FORK_BOLT_X:
        for by in (FORK_BOLT_Y, -FORK_BOLT_Y):
            cuts.append(cyl(1.5, 12.5, (bx, by, z1 - 12 + 12.5 / 2), "z", 24))
    cuts.append(box(IR_CX - IR_WIN_W / 2, IR_CX + IR_WIN_W / 2, IR_CY - IR_WIN_L / 2, IR_CY + IR_WIN_L / 2, zpb - 1, zpt + 1))
    for sgn in (-1, 1):
        by = IR_CY + sgn * ea
        cuts.append(cyl(1.5, IR_PLATE_T + 2, (IR_CX, by, (zpb + zpt) / 2), "z", 24))   # Ø3.0 자체탭 관통(탭 두께 4 전체), M3x6
    for zz in (z0 + 5.0, z0 + 13.0):                     # 이동 케이블 결속밴드: Y 방향 관통 Ø3.4, X=0 (뒤쪽 확장부)
        cuts.append(cyl(1.7, 82, (0.0, 0, zz), "y", 24))
    cuts.append(cyl(NUT_HOLE_R, 32, (RAIL_X, 0, (z0 + z1) / 2), "z", 96))            # 너트 몸통 관통 Ø22
    # P11 원점 스위치 본체 위 홈(캐리지 아랫면 Z119~122): 본체 윗면과 부딪히지 않게. 레버 끝(Y>-9.5)은 평평한 아랫면이 누름. lift_collar_v3.py BODY_X0/BODY_Y1/RELIEF_Z 와 일치
    cuts.append(box(BODY_X0 - 1, 6.0, -41.0, -9.5, z0 - 1, z0 + 3.0))
    cuts.append(pocket_cutter(z1))
    return diff(body, cuts), True


def pocket_cutter(z1):
    circ = Point(RAIL_X, 0).buffer(POCKET_R, resolution=96).intersection(sbox(-10, -POCKET_HALFY, 30, POCKET_HALFY))
    m = trimesh.creation.extrude_polygon(circ, POCKET_DEPTH + 1.0)
    m.apply_translation([0, 0, z1 - POCKET_DEPTH])
    return m


def nut_poly():
    return Point(RAIL_X, 0).buffer(NUT_FL_R, resolution=96).intersection(
        sbox(-10, -NUT_FL_HALFY, RAIL_X + NUT_FL_FRONT, NUT_FL_HALFY))


def make_nut_robot(zc=ZC0, dx=0.0, dy=0.0, dz=0.0):
    """P24 플로팅 너트(로봇 좌표, 캐리지 바닥 zc 기준 안착 위치). dx,dy,dz = 유동 이동량."""
    from lift_thread import nut_hole_cutter
    zfl0 = zc + 30 - POCKET_DEPTH                        # 플랜지 아랫면 = 카운터보어 바닥
    ztop = zfl0 + NUT_FL_T
    body = cyl(NUT_BODY_R, NUT_BODY_L + 0.5, (RAIL_X, 0, zfl0 - NUT_BODY_L / 2 + 0.25), "z", 96)
    poly = nut_poly()
    fl = trimesh.creation.extrude_polygon(poly, NUT_FL_T - 0.5)
    fl.apply_translation([0, 0, zfl0])
    ring_a = np.array([(x, y, ztop - 0.5) for x, y in poly.exterior.coords][:-1])
    ring_b = np.array([(x, y, ztop) for x, y in poly.buffer(-0.5, join_style=2).exterior.coords][:-1])
    cap = trimesh.convex.convex_hull(np.vstack([ring_a, ring_b]))
    nut = union([body, fl, cap])
    nut = diff(nut, [nut_hole_cutter(zfl0 - NUT_BODY_L, ztop, cx=RAIL_X, cy=0.0, clearance=NUT_CLEARANCE)])
    nut.apply_translation([dx, dy, dz])
    return nut


NUT_M = np.array([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, ZC0 + 30 - POCKET_DEPTH + NUT_FL_T], [0, 0, 0, 1]], float)  # 플랜지가 베드


def make_nut():
    m = make_nut_robot(ZC0)
    save(to_print(m, NUT_M), OUT / "P24_nut_float.stl")
    update_placement("P24_nut_float.stl", {"qty": 1, "matrix": flat(NUT_M),
                                           "note": "캐리지와 함께 이동(zc-119 만큼 Z 이동). 원점 자세 zc=119. 플랜지(포크 판 쪽 면)가 베드. 앞면 평면이 +X(앞)"})
    return m



CAR_M = np.array([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, ZC0 + 30], [0, 0, 0, 1]], float)   # 윗면이 베드


def make_carriage_part():
    m, threaded = make_carriage(ZC0)
    save(to_print(m, CAR_M), OUT / "P12_carriage_v2.stl")
    update_placement("P12_carriage_v2.stl", {"qty": 1, "matrix": flat(CAR_M),
                                             "note": "원점 자세 zc=119. 윗면(포크 체결면)이 베드. 다른 zc 는 행렬 Z 이동에 zc-119 를 더함",
                                             "internal_thread_applied": threaded})
    return m, threaded


# ---------------------------------------------------------------- 검사
def inter_vol(a, b):
    r = trimesh.boolean.intersection([a, b], engine=ENGINE)
    return float(r.volume) if len(r.vertices) else 0.0


def min_dist(a, b, n=4000):
    pts = np.vstack([a.sample(n), a.vertices])
    _, d, _ = trimesh.proximity.closest_point(b, pts)
    return float(d.min())


def load_fork(zc):
    m = trimesh.load(OUT / "P13_fork_v2.stl")
    m.apply_translation([81.5, 0, 145 + (zc + 36 - 155)])
    return m


def sensor_model(zc):
    """GP2Y0A21YK0F 개략 형상(로봇 좌표): 본체 + 귀 + 렌즈 케이스. 렌즈면 Z = zc + IR_FACE_DZ."""
    zf = zc + IR_FACE_DZ
    body = box(IR_CX - IR_BODY_W / 2, IR_CX + IR_BODY_W / 2, IR_CY - IR_BODY_L / 2, IR_CY + IR_BODY_L / 2, zf - IR_TOTAL_H, zf)
    ears = box(IR_CX - 6.5, IR_CX + 6.5, IR_CY - 22.25, IR_CY + 22.25, zf - IR_EAR_Z - IR_EAR_T, zf - IR_EAR_Z)
    return union([body, ears])


def ir_checks(zc, car, fork, st):
    from shapely.ops import unary_union
    zf = zc + IR_FACE_DZ
    sens = sensor_model(zc)
    ea = IR_EAR_SPAN / 2
    # 광선 시험: 렌즈 중심 + 반경 4.2 원둘레 8점, 렌즈면에서 위로
    obst = {"포크": fork, "캐리지": car, "P10": st["P10"], "P23_L": st["P23_L"], "P23_R": st["P23_R"]}
    hits = {k: 0 for k in obst}
    nray = 0
    for dy in IR_LENS_DY:
        pts = [(IR_CX, IR_CY + dy)] + [(IR_CX + IR_LENS_R * math.cos(t), IR_CY + dy + IR_LENS_R * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
        o = np.array([[x, y, zf + 0.05] for x, y in pts])
        d = np.tile([0, 0, 1.0], (len(o), 1))
        for k, m in obst.items():
            hits[k] += int(m.ray.intersects_any(o, d).sum())
        nray += len(o)
    print(f"   IR 광선 {nray}개(렌즈 Y {IR_CY + IR_LENS_DY[0]:.1f}/{IR_CY + IR_LENS_DY[1]:.1f}, X {IR_CX}, 반경 {IR_LENS_R}) 명중: {hits}")
    # 수평 여유: 포크 투영(+기둥 목 Ø50 @ (92,0)) 까지, 렌즈 반경 제외
    tri = fork.triangles[:, :, :2]
    ar = lambda t: abs((t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) - (t[2][0] - t[0][0]) * (t[1][1] - t[0][1]))
    sil = unary_union([Polygon(t) for t in tri if ar(t) > 1e-6] + [Point(92, 0).buffer(25)])
    neck = Point(92, 0).buffer(25)
    for dy in IR_LENS_DY:
        p = Point(IR_CX, IR_CY + dy)
        print(f"   렌즈 Y={IR_CY + dy:5.1f}: 포크 투영까지 {p.distance(sil) - IR_LENS_R:5.2f} (반경 제외), 기둥 목 Ø50 까지 {p.distance(neck) - IR_LENS_R:5.2f}")
    # 목(R25, 중심 (92-e, +-oy)) 과의 수평 간극표: 판(앞 X 60.2) / 센서 본체
    plate_fp = sbox(IR_PLATE_X0, IR_CY - ea - IR_PLATE_MARGIN_Y, IR_PLATE_FRONT, IR_CY + ea + IR_PLATE_MARGIN_Y)
    body_fp = sbox(IR_CX - IR_BODY_W / 2, IR_CY - IR_BODY_L / 2, IR_CX + IR_BODY_W / 2, IR_CY + IR_BODY_L / 2)
    if zc == ZC0:
        print("   목 간극표(판/본체, mm; 음수=간섭):  e\oy  " + "  ".join(f"{oy:>11d}" for oy in (0, 8, 14)))
        for e in (0, 2, 3, 5, 8):
            row = []
            for oy in (0, 8, 14):
                g = []
                for sg in (1, -1):
                    c = Point(92 - e, sg * oy)
                    g.append((plate_fp.distance(c) - 25 if not plate_fp.contains(c) else -99, body_fp.distance(c) - 25))
                row.append("%5.1f/%5.1f" % (min(x[0] for x in g), min(x[1] for x in g)))
            print(f"      e={e}:      " + "  ".join(row))
    others = dict(st, **{"포크": fork, "캐리지": car})
    print("   센서 형상 교차:", {k: round(inter_vol(sens, v), 3) for k, v in others.items()},
          " 최소거리:", {k: round(min_dist(sens, v, 2000), 2) for k, v in others.items() if k in ("스테퍼", "P02", "포크", "캐리지")})
    plate_bot = zf - IR_EAR_Z - IR_EAR_T - IR_PLATE_T
    print(f"   센서면 Z={zf:.1f}(f-{zc + 36 - zf:.0f}), 트레이 바닥 Z={plate_bot:.1f}(f-57.5={zc + 36 - 57.5:.1f}), 센서 바닥 Z={zf - IR_TOTAL_H:.1f}; "
          f"센서 본체-기둥(92,0) 수평거리 {Point(92, 0).distance(sbox(IR_CX - 6.5, IR_CY - 14.75, IR_CX + 6.5, IR_CY + 14.75)):.1f} "
          f"(하단 원기둥 반경이 이보다 작아야 센서 바닥이 Z100 아래로 내려가도 안전)")


def checks():
    from lift_thread import thread_rod
    print("== 간섭 검사 (교차 부피 mm3 / 최소 거리 mm) ==")
    stepper = box(-6, 36, -21, 21, 56, 96)
    p02 = trimesh.load(OUT / "P02_deck2.stl")
    screw = trimesh.load(OUT / "P20_leadscrew.stl")
    screw.apply_translation([0, 0, 98])
    mastL, mastR, p10 = make_p23_robot(30.0), make_p23_robot(-30.0), make_p10_robot()
    st = {"P23_L": mastL, "P23_R": mastR, "P10": p10, "스테퍼": stepper, "P02": p02}
    for zc in (ZC0, ZC1):
        car, _ = make_carriage(zc)
        fork = load_fork(zc)
        nut = make_nut_robot(zc)
        print(f"-- zc={zc:.0f} (캐리지 Z {zc:.0f}~{zc + 30:.0f}), 포크 f={zc + 36:.0f}; 너트 Z {nut.bounds[0][2]:.1f}~{nut.bounds[1][2]:.1f}")
        for k, s in dict(st, **{"포크P13": fork}).items():
            print(f"   캐리지 vs {k:6s} 교차 {inter_vol(car, s):8.3f}  최소거리 {min_dist(car, s, 3000):7.3f}")
        for k, s in dict(st, **{"포크P13": fork, "캐리지": car}).items():
            print(f"   너트(안착) vs {k:6s} 교차 {inter_vol(nut, s):8.3f}  최소거리 {min_dist(nut, s, 3000):7.3f}")
        # 스크류 나사산 위상 정렬: 암나사 컷터 z0 = (너트 최하 Z) - 1 에 맞춤 (8 mm 배수 차)
        zn0 = zc + 30 - POCKET_DEPTH - NUT_BODY_L
        sc = thread_rod(zn0 - 1 - 16, zn0 + 40, lead=8.0, starts=2)
        sc.apply_translation([RAIL_X, 0, 0])
        print(f"   너트 vs 스크류 나사산(위상 정렬) 교차 {inter_vol(nut, sc):8.3f}  최소거리 {min_dist(sc, nut, 15000):7.3f}")
        print(f"   너트 vs 스크류 전체(P20 실형상, 위상 임의) 최소거리 {min_dist(nut, screw, 4000):.3f}")
        # 유동 이동: 8방향 x {0.5, 1.0}
        worst = {}
        for r in (0.5, 1.0):
            vs = []
            for ang in range(0, 360, 45):
                dx, dy = r * math.cos(math.radians(ang)), r * math.sin(math.radians(ang))
                n2 = make_nut_robot(zc, dx, dy)
                vs.append(max(inter_vol(n2, car), inter_vol(n2, fork)))
            worst[r] = max(vs)
        print(f"   너트 횡이동 최악 교차 (±0.5: {worst[0.5]:.3f}, ±1.0 반경: {worst[1.0]:.3f}) mm3")
        ir_checks(zc, car, fork, st)
    print("-- 정적 부품")
    for a_ in ("P23_L", "P23_R"):
        for b_ in ("P10", "스테퍼", "P02"):
            print(f"   {a_} vs {b_}: 교차 {inter_vol(st[a_], st[b_]):.3f}")
    for b_ in ("P10", "스테퍼", "P02", "P23_L"):
        print(f"   스크류전체 vs {b_}: 교차 {inter_vol(screw, st[b_]):.3f}  최소거리 {min_dist(screw, st[b_], 4000):.3f}")
    # 구조 치수
    car, _ = make_carriage(ZC0)
    pk = Point(RAIL_X, 0).buffer(POCKET_R, resolution=96).intersection(sbox(-10, -POCKET_HALFY, 30, POCKET_HALFY))
    from shapely.geometry import Point as P_
    taps = [P_(bx, by).buffer(1.4) for bx in FORK_BOLT_X for by in (FORK_BOLT_Y, -FORK_BOLT_Y)]
    rails = [sbox(RAIL_X - CAR_HOLE / 2, sy - CAR_HOLE / 2, RAIL_X + CAR_HOLE / 2, sy + CAR_HOLE / 2) for sy in RAIL_Y]
    print(f"벽: 카운터보어-탭 최소 {min(pk.distance(t) for t in taps):.2f}, 카운터보어-레일구멍 {min(pk.distance(r) for r in rails):.2f}, "
          f"카운터보어 뒤쪽-캐리지 뒷면 {RAIL_X - POCKET_R - BODY_X0:.2f}, 관통구멍 앞쪽-앞면 {28 - RAIL_X - NUT_HOLE_R:.2f}")
    plate = sbox(6, -40, 28, 40).difference(Point(RAIL_X, 0).buffer(7.0, resolution=96))
    print(f"포크 판이 가두는 플랜지 면적(판 X6~28, 구멍 Ø14 제외): {nut_poly().intersection(plate).area:.0f} / 플랜지 전체 {nut_poly().area:.0f} mm2")
    print(f"유동 한계: 몸통 반경 {NUT_HOLE_R - NUT_BODY_R:.1f}, 플랜지 X 뒤 {POCKET_R - NUT_FL_R:.1f}, Y {POCKET_HALFY - NUT_FL_HALFY:.1f}, 상하 {POCKET_DEPTH - NUT_FL_T:.1f}")
    print(f"레일 10 / 캐리지 구멍 {CAR_HOLE} = 편측 {(CAR_HOLE - RAIL) / 2:.2f}, P10 소켓 {SOCK} = 편측 {(SOCK - RAIL) / 2:.2f}")


def report(name, m):
    b = m.bounds
    print(f"{name:26s} bbox {np.round(b[1] - b[0], 1).tolist()}  vol {m.volume / 1000:6.2f} cm3  "
          f"mass {mass_g(m):5.1f} g  watertight={m.is_watertight and m.is_volume}")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("mast", "all"):
        make_mast()
        for n in ("P23_mast_L.stl", "P23_mast_R.stl"):
            report(n, trimesh.load(OUT / n))
    if what in ("upper", "all"):
        make_upper()
        report("P10_mast_upper_v2.stl", trimesh.load(OUT / "P10_mast_upper_v2.stl"))
    if what in ("carriage", "all"):
        make_carriage_part()
        report("P12_carriage_v2.stl", trimesh.load(OUT / "P12_carriage_v2.stl"))
    if what in ("nut", "all"):
        make_nut()
        report("P24_nut_float.stl", trimesh.load(OUT / "P24_nut_float.stl"))
    if what in ("check", "all"):
        checks()
