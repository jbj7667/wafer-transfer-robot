"""승강부 v2: P13_fork_v2 (포크 루트 판 + M3 체결 + 스위치 포켓) / P11_limit_collar_v2 (원점 리밋 칼라).

실행: python public/cad/print/lift_fork.py  (워크트리 루트에서)
입력: public/cad/print/P13_fork.stl (Fusion 산출물, 로봇 좌표, f=155, Z 145~157) -> 불린 수정.
좌표는 로봇 좌표(+X 전진, +Y 좌, +Z 위, mm). STL은 출력 자세로 내보내고 placement_fork.json에 변환 기록.
"""
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from trimesh.boolean import intersection

from v12_parts import cyl, union, diff, save, OUT, ENGINE

# ============================ 상수 (수정 시 재생성) ============================
F = 155.0                      # 포크 윗면 높이(원점)
F_MAX = 227.0                  # 기계적 상한
# 캐리지/구조 (사양서)
CAR_X, CAR_Y, CAR_Z0, CAR_H = (4.0, 28.0), 40.0, 119.0, 30.0   # 원점 Z119~149
RAIL_XY = [(15.0, -30.0), (15.0, 30.0)]
RAIL_W = 10.0
SCREW_XY, SCREW_R_THREAD = (15.0, 0.0), 6.0
HUB_R, HUB_Z = 8.0, (98.0, 118.0)
# 포크 루트 판
PLATE_X, PLATE_Y, PLATE_T = (6.0, 28.0), 40.0, 6.0
BOLT_XS = (11.0, 23.0)   # 사양서 10/22 는 X=10 머리 자리의 판 가장자리 벽이 0.9 라 +1
# 사양서는 Y +-28 이지만 그 위치는 레일 구멍(Y 24.8~35.2, X 9.8~20.2)과 겹친다 -> 기본은 +-17.
# 사양서 값을 쓰려면 BOLT_YS=(-28, 28)로 바꿔 보라(스크립트가 간섭을 경고한다).
BOLT_YS = (-17.0, 17.0)
BOLT_D, CB_D, CB_DEPTH = 3.4, 6.2, 2.5
RAIL_CLEAR = 10.6              # 판의 레일 통과 구멍(정사각)
SCREW_CLEAR_D = 14.0           # 판의 리드스크류 통과 구멍
# 구 캐리지 체결 구멍(루트 앞면 X=28, Y +-28, Z 150, Ø4, 깊이 ~6) 메우기
OLD_HOLES_Y, OLD_HOLE_Z = (-28.0, 28.0), 150.0
# 넥 접촉 마이크로 스위치 (가정, 누워서 레버가 +X)
# 실측 GSM-V1621A2: 본체 29.41(실측) x ~17.7(사진) x 10.3(가정) + 여유 0.4 -> 아래 값. 두께·구멍 지름은 미측정(확인 필요)
SW_LEN, SW_W, SW_T = 29.8, 18.1, 10.7
SW_HOLE_D = 2.4                # 가정(미측정)
SW_HOLE_DX, SW_HOLE_DY = 21.0, 10.0   # 구멍은 대각 모서리: 힌지 끝+레버 쪽 / 자유 끝+반대쪽
LEVER_OVER = 10.3              # 레버 자유 끝이 본체 끝 밖으로 나온 길이 (사진 10~11)
LEVER_FROM_TIP = 5.3           # 눌리는 접점이 자유 끝에서 안쪽으로 (포크: 접점 = 본체 앞 + 10.3 - 5.3)
LEVER_REST_H = 3.8             # 정지 시 레버 자유 끝이 본체 윗면 위로 (추정 3~5, 확인 필요)
LEVER_EDGE_OFF = 2.9           # 레버 중심선이 본체 긴 변(레버 쪽)에서 안쪽으로
SW_X_BACK = 30.0               # 스위치 본체 뒤끝 X (캐리지 앞면 28에서 2 띄움)
CD_BOTTOM_Z = 155.0            # CD 바닥(원판 Z 155~, 중심 (92,0), Ø120)
CD_CLEAR = 1.0                 # 스위치·레버(정지) 가 CD 바닥보다 아래여야 하는 최소 간극
SW_TOP_Z = CD_BOTTOM_Z - CD_CLEAR - 3.8   # 본체 윗면 Z (= 150.2; 3.8 = LEVER_REST_H) -> 본체 Z 139.5~150.2 (포크 밑에 매달림, 아래에서 삽입)
HOUSE_WALL = 2.0               # 포켓 하우징 벽 두께
HOUSE_BOT_Z = 137.5            # 하우징 벽 바닥(본체 바닥 139.5 보다 2 아래: 너트 자리)
LEVER_SLOT_W = 8.0             # 천장의 레버 통과 홈 폭, 홈 윗 피막 0.8
LEVER_SKIN = 0.8
CB2_D, CB2_DEPTH = 4.6, 2.0    # M2 머리 자리(위에서, 포크 윗면 아래)
NECK_X = 67.0                  # 넥 표면 X (가정, 기존 문서)
SW_CLR = 0.3                   # 포켓 여유(편측)
ROOT_FRONT_X = 50.0
# 리밋 칼라 (v2b: 상판 P02 위 Z104~118 공간, 스위치 누움)
COL_X = (5.9, 24.0)            # Mega 후방 이동으로 X 제약 해소; -X 벽 = 9.9-5.9 = 4.0
COL_Y = (-40.0, -20.0)         # 레일 중심 (15,-30) +-10
COL_Z0, COL_H = 104.0, 8.0     # Z 104~112 (상판 윗면 103 위 1 띄움)
RAIL_CLR = 0.1                 # 편측 -> 구멍 10.2 (X 최소 벽 = 9.9-9.5 = 0.4)
SET_D = 2.8                    # M3 자체탭 세트스크류 (+-Y 면)
ARM_T = 3.0                    # 암 판 두께 (Z 104~107)
SW_Y = -21.0                   # 스위치 중심 Y (캐리지 레일 구멍 Y>=-24.8 바깥: 레버가 캐리지 솔리드를 누름)
SW_X_REAR = 24.5               # 스위치 본체 뒤끝(레버가 -X 로 뻗는 쪽) X
POCKET_WALL, POCKET_H = 2.0, 5.0   # 포켓 벽 두께, 판 위 벽 높이 (Z107~112)
RHO = 1.27
RHO = 1.27


def box(x0, x1, y0, y1, z0, z1):
    b = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return b


def vol_int(a, b):
    r = intersection([a, b], engine=ENGINE)
    return float(r.volume) if len(r.vertices) else 0.0


def carriage_model(zc0=CAR_Z0):
    c = box(CAR_X[0], CAR_X[1], -CAR_Y, CAR_Y, zc0, zc0 + CAR_H)
    cuts = [box(x - 5.2, x + 5.2, y - 5.2, y + 5.2, zc0 - 1, zc0 + CAR_H + 1) for x, y in RAIL_XY]
    cuts.append(cyl(SCREW_R_THREAD, CAR_H + 2, (*SCREW_XY, zc0 + CAR_H / 2)))
    return diff(c, cuts)


def rails():
    return [box(x - 5, x + 5, y - 5, y + 5, 60, 240) for x, y in RAIL_XY]


def to_print(mesh, perm_fn, shift):
    m = mesh.copy()
    m.vertices = perm_fn(m.vertices) - shift
    return m


# ================================================================ P13_fork_v2
def make_fork():
    f = trimesh.load(OUT / "P13_fork.stl")
    print("P13 원본 bbox", f.bounds.round(2).tolist(), "vol %.1f cm3" % (f.volume / 1000), "(로봇 좌표, f=155)")
    z0 = F - 10.0
    # (d) 기존 중앙부(|Y|<20, X 28~50) 포켓·수직 구멍을 지우고 솔리드 블록으로 복원
    f = diff(f, [box(27.9, ROOT_FRONT_X + 1, -20, 20, z0 - 1, F + 1)])
    f = union([f, box(28, ROOT_FRONT_X, -20, 20, z0, F)])
    # (c) 구 캐리지 체결 구멍(Ø4 x 6, X=28 면) 메우기
    fills = [box(28, 34.5, y - 3, y + 3, OLD_HOLE_Z - 3, OLD_HOLE_Z + 3) for y in OLD_HOLES_Y]
    # (a) 루트 판 X 6~28, Y +-40, Z f-6~f
    plate = box(PLATE_X[0], PLATE_X[1], -PLATE_Y, PLATE_Y, F - PLATE_T, F)
    sw_front = SW_X_BACK + SW_LEN
    sw_top, sw_bot = SW_TOP_Z, SW_TOP_Z - SW_T
    ysw = -(SW_W / 2 - LEVER_EDGE_OFF)              # 레버 중심선이 Y=0(넥 중심)에 오도록 스위치를 -Y 로 오프셋
    y0h, y1h = ysw - SW_W / 2 - SW_CLR - HOUSE_WALL, ysw + SW_W / 2 + SW_CLR + HOUSE_WALL
    x1h = sw_front + SW_CLR + HOUSE_WALL
    house = box(28.0, x1h, y0h, y1h, HOUSE_BOT_Z, F)      # 뿌리 아래·앞으로 내려오는 하우징 (윗면은 포크 윗면 Z=F 이하)
    tongue = house
    f = union([f, plate, tongue] + fills)

    cuts = []
    # (b) 수직 M3 체결 구멍 + 머리 자리
    for x in BOLT_XS:
        for y in BOLT_YS:
            cuts.append(cyl(BOLT_D / 2, PLATE_T + 4, (x, y, F - PLATE_T / 2), "z", 32))
            cuts.append(cyl(CB_D / 2, CB_DEPTH + 2, (x, y, F - CB_DEPTH / 2 + 1), "z", 32))
    # 레일/스크류 통과
    for x, y in RAIL_XY:
        cuts.append(box(x - RAIL_CLEAR / 2, x + RAIL_CLEAR / 2, y - RAIL_CLEAR / 2, y + RAIL_CLEAR / 2, F - PLATE_T - 1, F + 1))
    cuts.append(cyl(SCREW_CLEAR_D / 2, PLATE_T + 2, (*SCREW_XY, F - PLATE_T / 2), "z", 48))
    # (d) 스위치 포켓: 아래에서 삽입(아래·앞 개방), 천장 Z=sw_top+0.2, 배선 노치(뒤벽), 레버 홈, M2 구멍
    ylv = ysw + SW_W / 2 - LEVER_EDGE_OFF               # 레버 중심선 Y (=0)
    cuts.append(box(SW_X_BACK - SW_CLR, x1h + 5, ysw - SW_W / 2 - SW_CLR, ysw + SW_W / 2 + SW_CLR, HOUSE_BOT_Z - 1, sw_top + 0.2))
    cuts.append(box(27.99, SW_X_BACK, ysw - SW_W / 2 - SW_CLR, ysw - SW_W / 2 - SW_CLR + 8.0, HOUSE_BOT_Z - 1, sw_top + 0.2))   # 배선 노치(뒤벽, 아래 개방)
    lever_x0 = SW_X_BACK + SW_LEN + LEVER_OVER - 27.0   # 레버 힌지 X (힌지~자유 끝 27)
    cuts.append(box(lever_x0 - 1.0, x1h + 5, ylv - LEVER_SLOT_W / 2, ylv + LEVER_SLOT_W / 2, sw_top + 0.1, F - LEVER_SKIN))   # 레버 홈
    xm = SW_X_BACK + SW_LEN / 2
    for sx, sy in ((-1, 1), (1, -1)):                   # 힌지 끝=뒤, 레버 쪽=+Y
        hx, hy = xm + sx * SW_HOLE_DX / 2, ysw + sy * SW_HOLE_DY / 2
        cuts.append(cyl(SW_HOLE_D / 2, F - sw_top + 2, (hx, hy, sw_top + (F - sw_top) / 2), "z", 24))
        cuts.append(cyl(CB2_D / 2, CB2_DEPTH + 1, (hx, hy, F - CB2_DEPTH / 2 + 0.5 - 0.5 + 0.0), "z", 24))
    f = diff(f, cuts)
    assert f.is_watertight and f.volume > 0

    # ---- 출력 자세: 똑바로(윗면 위), 루트 바닥 Z=145 가 베드 ----
    cx = round(float((f.bounds[0][0] + f.bounds[1][0]) / 2), 1)
    shift = np.array([cx, 0.0, HOUSE_BOT_Z])
    pm = f.copy()
    pm.vertices = pm.vertices - shift
    r = save(pm, OUT / "P13_fork_v2.stl")
    T = np.eye(4)
    T[:3, 3] = shift
    print("P13_fork_v2 출력자세 bbox", r.bounds.round(2).tolist(), "vol %.1f cm3 (원본 %.1f)" % (r.volume / 1000, 43.1),
          "질량 약 %.0f g (인필 환산 0.55)" % (r.volume / 1000 * RHO * 0.55))

    # ---- 검사 ----
    car = carriage_model()
    plate_slab = box(PLATE_X[0], PLATE_X[1], -PLATE_Y, PLATE_Y, F - PLATE_T, F)
    print("[검사] 포크 루트 판 아랫면 Z=%.2f, 캐리지 윗면 Z=%.2f -> 간극 %.2f" % (F - PLATE_T, CAR_Z0 + CAR_H, (F - PLATE_T) - (CAR_Z0 + CAR_H)))
    print("[검사] 포크 ↔ 캐리지(원점) 겹침 mm3: %.3f" % vol_int(f, car))
    rl = rails()
    print("[검사] 포크 ↔ 레일 겹침 mm3: %s" % [round(vol_int(f, r_), 3) for r_ in rl])
    sc = cyl(SCREW_R_THREAD, 120, (*SCREW_XY, 170), "z", 64)
    print("[검사] 포크 ↔ 스크류(Ø12) 겹침 mm3: %.3f; 판-스크류 반경 간극 %.2f" % (vol_int(f, sc), SCREW_CLEAR_D / 2 - SCREW_R_THREAD))
    hub = cyl(HUB_R, HUB_Z[1] - HUB_Z[0], (*SCREW_XY, sum(HUB_Z) / 2))
    print("[검사] 포크 ↔ 허브 겹침 mm3: %.3f (포크 최하 Z=%.0f > 허브 상단 %.0f)" % (vol_int(f, hub), z0, HUB_Z[1]))
    fm = f.copy()
    fm.apply_translation([0, 0, F_MAX - F])
    p10 = box(0, 30, -38, 38, 232, 245)
    print("[검사] f=227 포크 최상 Z=%.1f, P10 아랫면 232 -> 여유 %.1f ; 겹침 %.3f" % (fm.bounds[1][2], 232 - fm.bounds[1][2], vol_int(fm, p10)))
    low = [box(3, 27, 22, 38, 56, 72), box(3, 27, -38, -22, 56, 72)]
    print("[검사] 포크(f=155) ↔ 하부 블록 겹침: %s" % [round(vol_int(f, b), 3) for b in low])
    # 구멍 간섭 경고 (사양서 Y +-28 사용 시)
    for x in BOLT_XS:
        for y in BOLT_YS:
            for rx, ry in RAIL_XY:
                dx, dy = abs(x - rx), abs(y - ry)
                if dx < RAIL_CLEAR / 2 + CB_D / 2 and dy < RAIL_CLEAR / 2 + CB_D / 2:
                    print("  경고: 볼트 (%g,%g) 머리 자리가 레일 구멍과 겹침" % (x, y))
    d = min(math.hypot(x - SCREW_XY[0], y - SCREW_XY[1]) for x in BOLT_XS for y in BOLT_YS) - SCREW_CLEAR_D / 2 - CB_D / 2
    print("[검사] 볼트 머리 자리 ↔ 스크류 통과 구멍 최소 벽 %.2f ; 판 가장자리 최소 벽 X %.2f / Y %.2f" % (
        d, min(BOLT_XS) - CB_D / 2 - PLATE_X[0], PLATE_Y - max(abs(y) for y in BOLT_YS) - CB_D / 2))
    tip_rest = sw_top + LEVER_REST_H
    contact_x = sw_front + LEVER_OVER - LEVER_FROM_TIP
    frac = (contact_x - lever_x0) / 27.0
    zc_rest = sw_top + LEVER_REST_H * frac
    print("[참고] 스위치(포크 밑 매달림) 본체 Z %.1f~%.1f, X %.1f~%.1f, Y %.2f~%.2f ; 레버 끝 X=%.1f Z(정지)=%.1f (CD 바닥 %.0f 와 간극 %.1f)" % (
        sw_bot, sw_top, SW_X_BACK, sw_front, ysw - SW_W / 2, ysw + SW_W / 2, sw_front + LEVER_OVER, tip_rest, CD_BOTTOM_Z, CD_BOTTOM_Z - tip_rest))
    print("       접점 X=%.1f Z(정지)=%.1f ; 눌림 1.5~3 -> 접점 Z %.1f~%.1f ; 넥 표면 X=%.0f 와 하우징 앞면 X=%.1f 수평 간극 %.1f ; 레버 끝은 넥 %.1f 안쪽" % (
        contact_x, zc_rest, zc_rest - 3, zc_rest - 1.5, NECK_X, x1h, NECK_X - x1h, sw_front + LEVER_OVER - NECK_X))
    # 겹침: CD 원판, 스위치+레버(정지) 포함 어셈블리
    sw_b = box(SW_X_BACK, sw_front, ysw - SW_W / 2, ysw + SW_W / 2, sw_bot, sw_top)
    lev = box(lever_x0, sw_front + LEVER_OVER, ylv - 3, ylv + 3, sw_top, tip_rest)
    asm = union([f, sw_b, lev])
    cd = cyl(60.0, 3.0, (92.0, 0.0, CD_BOTTOM_Z + 1.5), "z", 128)
    print("[검사] CD 원판(Ø120, Z>=155, 중심(92,0)) ↔ 포크+스위치+레버(정지) 겹침 mm3: %.3f ; 어셈블리 Z 최고(원판 영역 내 하우징/스위치)=%.2f" % (vol_int(asm, cd), max(sw_top + LEVER_REST_H, 0)))
    house_only = box(28.0, x1h, y0h, y1h, HOUSE_BOT_Z, F)
    print("[검사] 하우징 최고 Z=%.1f (<= 포크 윗면 %.0f)" % (F, F))
    ir_tray = box(47, 63, 0, 46, 100, 114)
    rays = [cyl(4.2, 60, (x, y, 144.0)) for y in (11.4, 32.8) for x in (54.0, 63.0)]
    print("[검사] 스위치 어셈블리(하우징 포함, 스위치 구간 X<=%.1f) ↔ IR 트레이(X47~63,Y0~46,Z<=114) %.3f ; 센서 광선 기둥(Y 11.4/32.8, X 54/63, R4.2) %s" % (
        x1h, vol_int(union([house, sw_b, lev]), ir_tray), [round(vol_int(union([house, sw_b, lev]), r_), 3) for r_ in rays]))
    print("[검사] 하우징 Y %.1f~%.1f -> 렌즈 시야(Y>=7.2)와 Y 간극 %.1f ; 캐리지(X<=28)와 겹침 %.3f ; 상판 앞 가장자리(X<=40,Z<=103)와 Z 간극 %.1f" % (
        y0h, y1h, 7.2 - y1h, vol_int(union([house, sw_b]), car), HOUSE_BOT_Z - 103))
    return T


def make_collar():
    z_plate1 = COL_Z0 + ARM_T                       # 107
    sw_bot, sw_top = z_plate1, z_plate1 + SW_T      # 107~117
    tip_free = sw_top + LEVER_REST_H                # 레버 자유 끝 정지 높이
    press = tip_free - CAR_Z0                       # 원점(캐리지 바닥 Z119)에서의 눌림량
    rise = LEVER_REST_H                        # 본체 윗면 위로 레버 끝이 올라와야 하는 높이 (가정 상수 계산값)
    cx, cy = RAIL_XY[0]
    cy = -30.0
    sw_x1 = SW_X_REAR + SW_LEN
    hw = SW_W / 2 + SW_CLR
    col = box(COL_X[0], COL_X[1], COL_Y[0], COL_Y[1], COL_Z0, COL_Z0 + COL_H)
    arm = box(COL_X[1] - 1, sw_x1 + POCKET_WALL, SW_Y - hw - POCKET_WALL, SW_Y + hw + POCKET_WALL, COL_Z0, COL_Z0 + ARM_T)
    walls = box(COL_X[1] - 1, sw_x1 + POCKET_WALL, SW_Y - hw - POCKET_WALL, SW_Y + hw + POCKET_WALL, COL_Z0, z_plate1 + POCKET_H)
    body = union([col, walls])
    cuts = []
    rh = RAIL_W / 2 + RAIL_CLR
    cuts.append(box(cx - rh, cx + rh, cy - rh, cy + rh, COL_Z0 - 1, COL_Z0 + COL_H + 1))
    zs = COL_Z0 + COL_H / 2
    for s in (-1, 1):                                  # +-Y 면 세트스크류 (벽 4.9)
        cuts.append(cyl(SET_D / 2, 7, (cx, cy + s * (10.0 + rh) / 2, zs), "y", 24))
    # 스위치 포켓: 위 개방, -X 쪽 개방(레버), 판 위 벽은 ±Y, +X 끝
    cuts.append(box(SW_X_REAR, sw_x1 + POCKET_WALL + 1, SW_Y - hw, SW_Y + hw, z_plate1, z_plate1 + POCKET_H + 3))   # +X 끝은 배선 출구로 개방
    cuts.append(box(COL_X[1] - 0.99, SW_X_REAR, SW_Y - hw, SW_Y + hw, z_plate1, z_plate1 + POCKET_H + 3))  # 레버 쪽 홈
    xm = SW_X_REAR + SW_LEN / 2
    for sx, sy in ((1, 1), (-1, -1)):                  # 힌지 끝=+X, 레버 쪽=+Y: 구멍 (+X,+Y) (-X,-Y), Z 관통
        cuts.append(cyl(SW_HOLE_D / 2, ARM_T + 2, (xm + sx * SW_HOLE_DX / 2, SW_Y + sy * SW_HOLE_DY / 2, COL_Z0 + ARM_T / 2), "z", 24))
    body = diff(body, cuts)
    assert body.is_watertight and body.volume > 0

    shift = np.array([body.bounds[0][0], body.bounds[0][1], COL_Z0])
    pm = body.copy()
    pm.vertices = pm.vertices - shift
    r = save(pm, OUT / "P11_limit_collar_v2.stl")
    T = np.eye(4)
    T[:3, 3] = shift
    print("P11_limit_collar_v2 출력자세(Z 그대로, 바닥 Z104=베드) bbox", r.bounds.round(2).tolist(), "vol %.2f cm3, 질량 약 %.1f g" % (r.volume / 1000, r.volume / 1000 * RHO * 0.6))
    print("  스위치(누움) 본체 Z %.1f~%.1f, X %.1f~%.1f, Y %.1f~%.1f ; 레버 자유 끝 Z=%.1f (본체 윗면 +%.1f), 레버 X %.1f~%.1f" % (
        sw_bot, sw_top, SW_X_REAR, sw_x1, SW_Y - SW_W / 2, SW_Y + SW_W / 2, tip_free, rise, SW_X_REAR - LEVER_OVER, sw_x1))
    print("  원점: 캐리지 아랫면 Z=%.0f 가 끝을 %.1f 눌러 Z=%.1f ; 칼라 Z %.0f~%.0f" % (CAR_Z0, press, CAR_Z0, COL_Z0, COL_Z0 + COL_H))
    print("  경고: 레일 구멍 -X 쪽 벽 두께 %.2f mm (X>=9.5 제약), 상판 윗면 103 과 간극 %.1f" % (cx - rh - COL_X[0], COL_Z0 - 103))
    # --- 겹침 검사 (로봇 좌표) ---
    ylv = SW_Y + SW_W / 2 - LEVER_EDGE_OFF
    print("  레버 중심선 Y=%.1f (+Y 변), 접점 X≈%.1f~%.1f, 눌림 %.1f (허용 3)" % (ylv, SW_X_REAR - LEVER_OVER, SW_X_REAR - LEVER_OVER + LEVER_FROM_TIP, press))
    assert press <= 3.0 and press >= 1.5, "눌림량 범위 밖"
    lever = box(SW_X_REAR - LEVER_OVER, sw_x1, ylv - 3, ylv + 3, sw_top, CAR_Z0)  # 눌린 상태 레버(끝 Z119)
    sw = box(SW_X_REAR, sw_x1, SW_Y - SW_W / 2, SW_Y + SW_W / 2, sw_bot, sw_top)
    assembly = union([body, lever, sw])
    car = carriage_model()
    rl = rails()
    hub = union([cyl(5.5, 15, (*SCREW_XY, 110.5)), cyl(5.5, 4, (*SCREW_XY, 116))])      # P20 허브 R5.5 Z103~118 (보수적)
    items = {
        "레일 -Y": rl[0], "레일 +Y": rl[1], "캐리지(원점)": car, "허브 P20": hub,
        "스테퍼 SF2421 (X-6~36,Y+-21,Z56~100)": box(-6, 36, -21, 21, 56, 100),
        "상판 P02 (Z100~103)": box(-93, 40, -75, 75, 100, 103),
        "Mega 대역 후방 (X-78~-24.7,Y+-26.7,Z103~118)": box(-78, -24.7, -26.7, 26.7, 103, 118),
        "IR 트레이 (X45~75, Y7~37, Z106~110)": box(45, 75, 7, 37, 106, 110),
        "하부 블록 (Z56~72)": box(3, 27, -38, -22, 56, 72),
    }
    for k, v in items.items():
        print("[검사] 칼라+스위치+눌린 레버 ↔ %-42s 겹침 %.3f mm3" % (k, vol_int(assembly, v)))
    # 간극
    pq = trimesh.proximity.ProximityQuery(hub)
    d = -pq.signed_distance(body.vertices).max()
    print("[검사] 암/칼라 ↔ 허브 최소 간극(꼭짓점) %.2f mm ; 암 최대 Y=%.1f (허브 Y>=-5.5)" % (d, body.bounds[1][1]))
    print("[검사] 칼라 최소 X=%.2f (Mega 후방 이동, 상판 위 X>0 전자부품 금지 구역 밖) ; 최대 높이 Z=%.1f (캐리지 아랫면 119 까지 %.1f)" % (body.bounds[0][0], body.bounds[1][2], CAR_Z0 - body.bounds[1][2]))
    print("[검사] 레버 접점 (Y %.1f) 위 캐리지 솔리드 여부: %s" % (ylv, bool(car.contains([[14.5, ylv, 125.0], [20.0, ylv, 125.0], [27.0, ylv, 125.0]]).all())))
    return T


def main():
    Tf = make_fork()
    Tc = make_collar()
    pl = {
        "convention": "p_robot = M * p_print ; row-major 16 values ; 포크는 원점 f=155 기준 ; 단위 mm",
        "parts": {
            "P13_fork_v2.stl": {"qty": 1, "matrix": [round(float(v), 4) for v in Tf.ravel()],
                                "print_pose": "똑바로(윗면 위), 루트 바닥(Z=145)이 베드. 포크 f가 변하면 Z 이동만(+f-155)."},
            "P11_limit_collar_v2.stl": {"qty": 1, "matrix": [round(float(v), 4) for v in Tc.ravel()],
                                        "print_pose": "로봇 자세 그대로(Z 위), 바닥 Z=104 가 베드. Y=-30 레일(원점 스위치)용; 칼라는 상판 위 Z104~112, 위아래 미세 조절 가능."},
        },
    }
    (OUT / "placement_fork.json").write_text(json.dumps(pl, ensure_ascii=False, indent=2), encoding="utf-8")
    print("placement_fork.json 기록")


if __name__ == "__main__":
    main()
