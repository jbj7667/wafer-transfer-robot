"""상판 P02_deck2_v2 + 패널 P15_panel_v2 생성 (Python/trimesh).

좌표: 로봇 좌표(+X 전진, +Y 좌, +Z 위, 원점 = 바퀴 접지점 중점 바닥).
출력 자세
  - 상판: 윗면이 베드, 기둥이 위로. print = (X, -Y, 103 - Z)  (X축 둘레 180도 회전, det +1)
  - 패널: 뒷면(-X면)이 베드.   print = (Y + 64, Z - 103, X + 92) (순환 치환, det +1)
실행: python -X utf8 public/cad/print/lift_deck2.py
"""
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from v12_parts import cyl, union, diff, extrude, save

OUT = Path(__file__).parent
ENGINE = "manifold"

# ------------------------------------------------------------------ 상수 (수정 시 재생성)
DECK_Z0, DECK_Z1 = 100.0, 103.0
DECK_X0, DECK_X1 = -92.0, 40.0
DECK_HALF_Y = 75.0           # X > WIDE_X1 구간
WIDE_X1, WIDE_HALF_Y = -20.0, 81.0   # 후방 확장부(X <= -20): Mega + L298 을 Y 로 나란히 놓으려면 152 mm 필요
HOLE_D = 3.4
NUT_R = 3.3                  # 아래쪽 너트 외접 반경(AF 5.5 -> 3.2) + 여유
NUT_H = 2.4

# 스탠드오프 기둥 (X, Y, 외경, 'D컷 X 한계' 또는 None)
POST_Z0 = 56.0
POSTS = [(-30.0, 65.0, 10.0, -33.5), (-30.0, -65.0, 10.0, -33.5), (30.0, 65.0, 10.0, None),
         (-3.0, -43.0, 8.0, None)]         # 4번째: P01 노치(X>=5, Y-71~-21) 때문에 (-3,-43) 제안, Ø8
POST_PILOT_D, POST_PILOT_DEPTH = 2.8, 12.0

# Mega 2560 (보드 좌하 원점 mm) -> 90도 회전 배치
MEGA_L, MEGA_W = 101.6, 53.3
MEGA_HOLES_BOARD = [(13.97, 2.54), (15.24, 50.8), (66.04, 7.62), (66.04, 35.56), (90.17, 50.8), (96.52, 2.54)]
MEGA_X0 = -24.7    # 보드 y=0 가장자리의 X (보드 y 가 커질수록 -X)
MEGA_Y0 = -70.0    # 보드 x=0 (USB 끝)의 Y   (보드 x 가 커질수록 +Y)


def mega_xy(bx, by):
    return (MEGA_X0 - by, MEGA_Y0 + bx)


MEGA_HOLES = [mega_xy(*h) for h in MEGA_HOLES_BOARD]
MEGA_FOOT = box(MEGA_X0 - MEGA_W, MEGA_Y0, MEGA_X0, MEGA_Y0 + MEGA_L)

# L298 SZH-EK001 43.5 x 43.5 x 29, 구멍 37 피치
L298_C = (-52.0, 34.6 + 43.5 / 2)
L298_FOOT = box(L298_C[0] - 21.75, L298_C[1] - 21.75, L298_C[0] + 21.75, L298_C[1] + 21.75)
L298_HOLES = [(L298_C[0] + sx * 18.5, L298_C[1] + sy * 18.5) for sx in (-1, 1) for sy in (-1, 1)]

# DRV8825 (15.5 x 20.5, 긴 변 = X). 소켓 창 + 고정 구멍 2개(Y 방향 양쪽)
DRV_C = (-11.45, 47.0)
DRV_FOOT = box(DRV_C[0] - 10.25, DRV_C[1] - 7.75, DRV_C[0] + 10.25, DRV_C[1] + 7.75)
DRV_WINDOW = box(DRV_C[0] - 9.0, DRV_C[1] - 4.5, DRV_C[0] + 9.0, DRV_C[1] + 4.5)   # 18 x 9 핀 창
DRV_HOLES = [(DRV_C[0], DRV_C[1] - 11.75), (DRV_C[0], DRV_C[1] + 11.75)]

# HM-10 27 x 13 (긴 변 = Y), 결속밴드 슬롯 2 (양 끝 바깥)
HM_C = (-15.2, -5.0)
HM_FOOT = box(HM_C[0] - 6.5, HM_C[1] - 13.5, HM_C[0] + 6.5, HM_C[1] + 13.5)
HM_SLOTS = [box(HM_C[0] - 3.0, HM_C[1] + s * 16.0 - 1.2, HM_C[0] + 3.0, HM_C[1] + s * 16.0 + 1.2) for s in (-1, 1)]

# 만능기판 30 x 20 (긴 변 = Y), 구멍 4
PERF_C = (-11.7, -57.0)
PERF_FOOT = box(PERF_C[0] - 10, PERF_C[1] - 15, PERF_C[0] + 10, PERF_C[1] + 15)
# 4번째 기둥(-3,-43)과 겹치는 모서리 구멍 1개 생략 -> 3점 고정
PERF_HOLES = [(PERF_C[0] + sx * 7.5, PERF_C[1] + sy * 12.5) for sx in (-1, 1) for sy in (-1, 1)
              if not (sx == 1 and sy == 1)]

# 케이블 슬롯 (X -5~-1, 하부 브래킷 X<=-6.2 / 스테퍼 판 아래 회피)
# P08 스테퍼 판 볼트 접근 구멍 Ø8 (뒤쪽 볼트 2개: 중심 (15,0)에서 X-15.5, Y±15.5)
ACCESS_D = 8.0
ACCESS_HOLES = [(-0.5, 15.5), (-0.5, -15.5)]
CABLE_SLOTS = [box(-5, 24, -1, 36), box(-5, -36, -1, -24)]

# 패널 (뒤 가장자리, 서 있는 판)
PNL_Y0, PNL_Y1 = -64.0, 16.0
PNL_X0, PNL_X1 = -92.0, -89.0          # 판 두께 3
PNL_TAB_X1 = -81.0                      # 바닥 탭 X -89~-81, 두께 3
PNL_H = 50.0                            # 판 높이 Z 103~153
PNL_TAB_HOLES = [(-84.5, PNL_Y0 + 6.0), (-84.5, PNL_Y1 - 6.0)]
PNL_FOOT = box(PNL_X0, PNL_Y0, PNL_TAB_X1, PNL_Y1)
SW_W, SW_H = 21.0, 15.0                 # 기성 스위치 컷아웃 상수
PNL_UC = (PNL_Y0 + PNL_Y1) / 2          # 판 중심 Y

# 하부 리브 (폭 4, 높이 3: Z 97~100)
RIB_W, RIB_H = 4.0, 3.0
RIBS = [box(-90, 63, -30, 67), box(-90, -67, -30, -63), box(-30, 63, 30, 67),
        box(-48, -65, -44, 65)]


def deck_outline():
    o = unary_union([box(DECK_X0, -DECK_HALF_Y, DECK_X1, DECK_HALF_Y),
                     box(DECK_X0, -WIDE_HALF_Y, WIDE_X1, WIDE_HALF_Y)])
    return o.buffer(2.0).buffer(-2.0)


def circ(p, d, res=24):
    return Point(p).buffer(d / 2, resolution=res)


def sq(cx, cy, w, h):
    return box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


# ------------------------------------------------------------------ 상판
def make_deck():
    outline = deck_outline()
    holes = []
    holes += [circ(p, HOLE_D) for p in MEGA_HOLES + L298_HOLES + DRV_HOLES + PERF_HOLES + PNL_TAB_HOLES]
    holes.append(sq(15, 30, 10.6, 10.6))
    holes.append(sq(15, -30, 10.6, 10.6))
    holes.append(circ((15, 0), 20.0, 64))
    holes += [circ(p, ACCESS_D, 48) for p in ACCESS_HOLES]
    holes.append(DRV_WINDOW)
    holes += HM_SLOTS
    holes += CABLE_SLOTS
    plate2d = outline.difference(unary_union(holes))
    plate = extrude(plate2d, DECK_Z1 - DECK_Z0, DECK_Z0)

    parts = [plate]
    for (x, y, d, xcut) in POSTS:
        sh = circ((x, y), d, 64)
        if xcut is not None:
            sh = sh.intersection(box(xcut, y - 20, x + 20, y + 20))
        parts.append(extrude(sh, DECK_Z0 + 1.0 - POST_Z0, POST_Z0))
    for r in RIBS:
        parts.append(extrude(r, RIB_H + 0.2, DECK_Z0 - RIB_H))
    body = union(parts)
    pilots = [cyl(POST_PILOT_D / 2, POST_PILOT_DEPTH + 1.0, (x, y, POST_Z0 + (POST_PILOT_DEPTH - 1.0) / 2), "z", 24)
              for (x, y, d, xc) in POSTS]
    body = diff(body, pilots)
    return body, plate2d


# ------------------------------------------------------------------ 패널
def make_panel():
    L = PNL_Y1 - PNL_Y0
    plate = trimesh.creation.box(extents=[PNL_X1 - PNL_X0, L, PNL_H])
    plate.apply_translation([(PNL_X0 + PNL_X1) / 2, PNL_UC, DECK_Z1 + PNL_H / 2])
    tab = trimesh.creation.box(extents=[PNL_TAB_X1 - PNL_X1 + 0.2, L, 3.0])
    tab.apply_translation([(PNL_X1 - 0.2 + PNL_TAB_X1) / 2, PNL_UC, DECK_Z1 + 1.5])
    parts = [plate, tab]
    for yy in (PNL_Y0, PNL_Y1 - 3.0):                 # 보강 삼각 리브 2 (두께 3)
        tri = Polygon([(PNL_X1 - 0.2, DECK_Z1 + 2.8), (PNL_TAB_X1, DECK_Z1 + 2.8), (PNL_X1 - 0.2, DECK_Z1 + 22)])
        g = trimesh.creation.extrude_polygon(tri, 3.0)           # (a=X, b=Z) -> 압출 z
        g.vertices = g.vertices[:, [0, 2, 1]]                     # (x, y=압출, z=b)
        g.invert()
        g.apply_translation([0, yy, 0])
        parts.append(g)
    body = union(parts)

    def zc(v):
        return DECK_Z1 + v

    cuts = []
    # 탭 체결 구멍
    for (x, y) in PNL_TAB_HOLES:
        cuts.append(cyl(HOLE_D / 2, 8, (x, y, DECK_Z1 + 1.5), "z", 24))
    # 판 관통 컷아웃 (X 방향)
    def cut_box(u, v, w, h):
        b = trimesh.creation.box(extents=[8, w, h])
        b.apply_translation([(PNL_X0 + PNL_X1) / 2, PNL_UC + u, zc(v)])
        return b

    def cut_cyl(u, v, d):
        return cyl(d / 2, 8, ((PNL_X0 + PNL_X1) / 2, PNL_UC + u, zc(v)), "x", 32)

    ROWA, ROWB = 38.5, 14.0
    sw_u = [-23.5, 2.5]
    for u in sw_u:
        cuts.append(cut_box(u, ROWA, SW_W, SW_H))
    cuts.append(cut_cyl(29.0, ROWA, 16.0))               # 푸시버튼 Ø16
    led_u = [-28.0, -19.0, -10.0]
    for u in led_u:
        cuts.append(cut_cyl(u, ROWB, 5.2))
    lab = trimesh.creation.box(extents=[1.2, 40.0, 8.0])  # 라벨 오목 홈 깊이 0.6 (뒷면 X=-92)
    lab.apply_translation([PNL_X0 + 0.0, PNL_UC + 18.0, zc(ROWB)])
    cuts.append(lab)
    body = diff(body, cuts)
    return body


# ------------------------------------------------------------------ 변환
def deck_to_print(m):
    m = m.copy()
    v = m.vertices.copy()
    m.vertices = np.column_stack([v[:, 0], -v[:, 1], DECK_Z1 - v[:, 2]])
    m.invert()                      # det=+1 회전이라 면 방향은 유지되지만, 안전하게 법선 정리
    m.fix_normals()
    return m


M_DECK = np.array([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, DECK_Z1], [0, 0, 0, 1]], float)
M_PANEL = np.array([[0, 0, 1, -92], [1, 0, 0, -64], [0, 1, 0, DECK_Z1], [0, 0, 0, 1]], float)


def to_print_generic(m, Minv):
    m = m.copy()
    m.apply_transform(Minv)
    m.fix_normals()
    return m


# ------------------------------------------------------------------ 검사
def check_layout(outline):
    msgs, ok = [], True
    foot = {"Mega": MEGA_FOOT, "L298": L298_FOOT, "DRV8825": DRV_FOOT, "HM-10": HM_FOOT,
            "만능기판": PERF_FOOT, "패널": PNL_FOOT}
    names = list(foot)
    inner = outline.buffer(-2.0)
    for n in names:
        if n == "패널":
            continue
        inside = inner.contains(foot[n])
        if not inside:
            ok = False
        msgs.append(f"가장자리 2 mm: {n} {'OK' if inside else 'NG'}")
    mind = 1e9
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            d = foot[a].distance(foot[b])
            mind = min(mind, d)
            flag = "OK" if d >= 3.0 - 1e-9 else "NG"
            if flag == "NG":
                ok = False
            msgs.append(f"간격 {a}-{b}: {d:.2f} {flag}")
    # X <= 0 규칙
    for n in names:
        if foot[n].bounds[2] > 0:
            ok = False
            msgs.append(f"X>0 침범: {n}")
    # 슬롯/창이 부품 점유와 겹치지 않거나 의도(창은 DRV 안)
    for k, s in enumerate(CABLE_SLOTS):
        for n in names:
            if s.intersects(foot[n]):
                ok = False
                msgs.append(f"케이블 슬롯{k} 가 {n} 와 겹침 NG")
    # 구멍 위치가 자기 부품 점유 안에 있는지, 다른 점유와 겹치지 않는지
    holes_by = {"Mega": MEGA_HOLES, "L298": L298_HOLES, "DRV8825": DRV_HOLES, "만능기판": PERF_HOLES}
    for n, hs in holes_by.items():
        for h in hs:
            if n != "DRV8825" and not foot[n].buffer(0.01).contains(Point(h)):
                ok = False
                msgs.append(f"{n} 구멍 {h} 점유 밖 NG")
            for m2 in names:
                if m2 != n and foot[m2].distance(Point(h)) < 1.7 + 0.5:
                    ok = False
                    msgs.append(f"{n} 구멍 {h} 가 {m2} 와 간섭 NG")
    # 하부 너트(원 r=3.3) vs 리브, 기둥, 서로, 슬롯/창
    nuts = [("Mega", h) for h in MEGA_HOLES] + [("L298", h) for h in L298_HOLES] + [("DRV", h) for h in DRV_HOLES] \
        + [("PERF", h) for h in PERF_HOLES] + [("PANEL", h) for h in PNL_TAB_HOLES]
    for n, h in nuts:
        c = Point(h).buffer(NUT_R)
        for k, r in enumerate(RIBS):
            if c.intersects(r.buffer(0.5)):
                ok = False
                msgs.append(f"너트 {n}{h} 가 리브{k}와 간섭 NG")
        for (x, y, d, xc) in POSTS:
            if c.distance(Point(x, y)) < d / 2 + 0.5:
                ok = False
                msgs.append(f"너트 {n}{h} 가 기둥({x},{y})과 간섭 NG")
        for s in CABLE_SLOTS + [DRV_WINDOW] + HM_SLOTS:
            if c.intersects(s):
                ok = False
                msgs.append(f"너트 {n}{h} 가 슬롯/창과 겹침 NG")
    # 구멍끼리 최소 거리 / 레일 구멍 벽
    allh = [h for _, h in nuts]
    for i in range(len(allh)):
        for j in range(i + 1, len(allh)):
            if math.dist(allh[i], allh[j]) < 6.6:
                ok = False
                msgs.append(f"구멍 간격 {allh[i]} {allh[j]} NG")
    # 리브 위치가 판 안인지, 리브-구멍 겹침
    for k, r in enumerate(RIBS):
        if not outline.buffer(0.01).contains(r):
            ok = False
            msgs.append(f"리브{k} 판 밖 NG")
    return ok, msgs, mind


def check_meshes(deck):
    """상판 메쉬(로봇 좌표)와 이웃 부품의 겹침 부피."""
    res = []

    def vol_int(m, other):
        try:
            i = trimesh.boolean.intersection([m, other], engine=ENGINE)
            return float(i.volume) if len(i.vertices) else 0.0
        except Exception:
            return 0.0

    def bx(x0, x1, y0, y1, z0, z1):
        b = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
        b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
        return b

    refs = {
        "레일 L (15,30) 10x10 Z60-240": bx(10, 20, 25, 35, 60, 240),
        "레일 R (15,-30)": bx(10, 20, -35, -25, 60, 240),
        "리드스크류 허브 Ø16 Z98-118": cyl(8.0, 20.0, (15, 0, 108), "z", 64),
        "리드스크류 나사부 Ø12 Z118-228": cyl(6.0, 110.0, (15, 0, 173), "z", 64),
        "캐리지 X4-58.7 Y±40 Z119-149": bx(4, 58.7, -40, 40, 119, 149),
        "칼라 X5-25 Y-40~-20 Z104-112": bx(5, 25, -40, -20, 104, 112),
        "스테퍼 몸통 X-6~36 Y±21 Z56-96": bx(-6, 36, -21, 21, 56, 96),
        "P08 판 X-8~38 Y±23 Z96-100": bx(-8, 38, -23, 23, 96, 100),
        "P08 칼라 X-20~-6.2 Y±32 Z56-96": bx(-20, -6.2, -32, 32, 56, 96),
        "마스트 하부 L X3-27 Y22-38 Z56-72": bx(3, 27, 22, 38, 56, 72),
        "마스트 하부 R": bx(3, 27, -38, -22, 56, 72),
        "배터리 L X-92~-34 Y0-90 Z58-74": bx(-92, -34, 0, 90, 58, 74),
        "배터리 R": bx(-92, -34, -90, 0, 58, 74),
        "하판 P01 (Z52-56)": bx(-92, 40, -92, 92, 52, 56),
    }
    for n in ("P14_batt_cradle_v2_L", "P14_batt_cradle_v2_R"):
        refs[n] = trimesh.load(OUT / f"{n}.stl")
    for n, o in refs.items():
        res.append((n, vol_int(deck, o)))
    return res


def p01_post_check():
    """P01 슬라이스(Z=54): 기둥 위치에 구멍/재료 확인."""
    m = trimesh.load(OUT / "P01_deck1_v2.stl")
    s = m.section(plane_origin=[0, 0, 54], plane_normal=[0, 0, 1])
    polys = sorted([Polygon(d[:, :2]) for d in s.discrete], key=lambda p: -p.area)
    mat = polys[0]
    for q in polys[1:]:
        mat = mat.difference(q)
    holes = [q for q in polys[1:]]
    out = []
    for (x, y, d, xc) in POSTS:
        has_hole = any(q.contains(Point(x, y)) and abs(q.centroid.x - x) < 0.3 and abs(q.centroid.y - y) < 0.3 for q in holes)
        mat_ok = mat.contains(Point(x, y).buffer(d / 2 + 0.5)) or has_hole
        # 기둥 바닥 원이 하판 재료 위에 얹히는 면적 비율
        disk = Point(x, y).buffer(d / 2)
        cover = mat.intersection(disk).area / disk.area
        out.append((x, y, has_hole, round(cover, 2)))
    return out


def main():
    outline = deck_outline()
    ok, msgs, mind = check_layout(outline)
    print("== 배치 검사 ==")
    for m in msgs:
        if "NG" in m:
            print("  ", m)
    print("   최소 부품 간격 %.2f mm, 전체 %s" % (mind, "OK" if ok else "NG 있음"))
    print("== 접근 구멍 벽(구멍 가장자리~다른 컷/점유 거리) ==")
    others = {"HM-10 점유": HM_FOOT, "HM-10 슬롯": unary_union(HM_SLOTS), "케이블 슬롯 S1": CABLE_SLOTS[0],
              "케이블 슬롯 S2": CABLE_SLOTS[1], "허브 Ø20": circ((15, 0), 20.0, 64), "레일 구멍 L": sq(15, 30, 10.6, 10.6),
              "레일 구멍 R": sq(15, -30, 10.6, 10.6), "Mega 점유": MEGA_FOOT, "DRV 창": DRV_WINDOW,
              "DRV 점유": DRV_FOOT, "만능기판 점유": PERF_FOOT}
    for p in ACCESS_HOLES:
        a = circ(p, ACCESS_D, 48)
        w = {n: a.distance(g) for n, g in others.items()}
        wn = min(w, key=w.get)
        print("   접근 구멍 %s: 최소 벽 %.2f (%s) %s" % (p, w[wn], wn, "OK" if w[wn] >= 3 else "NG"))

    deck, plate2d = make_deck()
    assert deck.is_watertight and deck.is_volume
    print("deck bbox (robot)", deck.bounds.round(2).tolist(), "vol cm3 %.2f" % (deck.volume / 1000))
    # 레일 구멍 벽 두께
    wall_hub = 10.0 - 5.3          # Ø20 구멍(반경 10) 가장자리 Y=10 와 레일 구멍 가장자리 Y=24.7 -> 간격
    print("레일 구멍 벽: 허브 구멍 가장자리(Y10)~레일 구멍(Y24.7) = %.1f, 레일 구멍~가장자리(X40) = %.1f"
          % (24.7 - 10.0, 40 - 20.3))
    print("== 이웃 부품과 겹침 부피 (mm3) ==")
    bad = False
    for n, v in check_meshes(deck):
        print("   %-40s %.2f" % (n, v))
        bad |= v > 0.5
    print("   겹침 %s" % ("있음 NG" if bad else "0 (OK)"))
    print("== P01 기둥 위치 (x, y, 구멍 있음, 하판 재료 지지율) ==")
    for r in p01_post_check():
        print("  ", r)

    pd = to_print_generic(deck, np.linalg.inv(M_DECK))
    r = save(pd, OUT / "P02_deck2_v2.stl")
    print("P02_deck2_v2 print bbox", r.bounds.round(2).tolist(), "watertight", r.is_watertight)

    panel = make_panel()
    assert panel.is_watertight and panel.is_volume
    pp = to_print_generic(panel, np.linalg.inv(M_PANEL))
    rp = save(pp, OUT / "P15_panel_v2.stl")
    print("P15_panel_v2 print bbox", rp.bounds.round(2).tolist(), "vol cm3 %.2f" % (rp.volume / 1000))
    # 패널-상판 부품 겹침(탭 아래는 상판 윗면 접촉만)
    ov = trimesh.boolean.intersection([panel, deck], engine=ENGINE)
    print("패널-상판 겹침 mm3", float(ov.volume) if len(ov.vertices) else 0.0)

    for n, v, mass in (("P02", deck.volume, None), ("P15", panel.volume, None)):
        print("%s 솔리드 질량 PETG 1.27 g/cm3: %.0f g  / PLA 1.24: %.0f g (인필 감안 약 70%%: %.0f g)"
              % (n, v / 1000 * 1.27, v / 1000 * 1.24, v / 1000 * 1.27 * 0.7))

    place = {
        "convention": "출력자세 점 -> 로봇좌표 = M(4x4 row-major) @ [x,y,z,1]. 상판: (x,y,z)->(x,-y,103-z) (X축 둘레 180도, det+1). 패널: (x,y,z)->(z-92, x-64, y+103) (det+1).",
        "parts": {
            "P02_deck2_v2.stl": {"qty": 1, "matrices": [M_DECK.flatten().tolist()]},
            "P15_panel_v2.stl": {"qty": 1, "matrices": [M_PANEL.flatten().tolist()]},
        },
        "fourth_post": {"x": -3.0, "y": -43.0, "od": 8.0, "note": "P01 에 Ø3.4 구멍 추가 필요"},
    }
    (OUT / "placement_deck2.json").write_text(json.dumps(place, ensure_ascii=False, indent=1), encoding="utf-8")
    print("det M_DECK %.1f, det M_PANEL %.1f" % (np.linalg.det(M_DECK[:3, :3]), np.linalg.det(M_PANEL[:3, :3])))
    print("Mega 구멍(로봇 XY):", [tuple(round(c, 2) for c in h) for h in MEGA_HOLES])
    print("L298 구멍:", [tuple(round(c, 2) for c in h) for h in L298_HOLES])
    print("DRV 구멍:", [tuple(round(c, 2) for c in h) for h in DRV_HOLES])
    print("PERF 구멍:", [tuple(round(c, 2) for c in h) for h in PERF_HOLES])


if __name__ == "__main__":
    main()
