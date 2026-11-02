"""P11_limit_collar_v3: 원점 리밋 칼라 — 스위치를 캐리지 옆에 세우고, 캐리지가 내려오면 레버 끝을 위에서 누른다.

스위치 GSM-V1621A2 (2026-11-02 실측/사진): 길이 29.41 x 폭 ~16(사진 17.7) x 두께 ~10.3(가정).
 - 레버는 길이(L) x 두께(T) 면 위에 있고 폭(W) 방향으로 눌린다. 레버 끝 높이(레버 반대 면 기준) 미작동 20 / 작동 17.
 - 그래서 스위치는 L x T 면이 바닥인 '서 있는' 자세. 가장 넓은 면(L x W) 2개 = 좌우 벽이 감싸고, 레버가 튀어나온 쪽 좁은 끝면(W x T) 1개 = 끝벽. 3면.
 - 좌우 벽 사이로 두께 방향(X) M2 나사 2개: 본체 구멍(길이 21 / 폭 10 대각)을 지나 먼 쪽 벽에 체결.
 - 배선 3가닥은 반대쪽(힌지) 끝으로: 그쪽은 열려 있고 타이 슬릿.
 - 본체는 캐리지 옆(Y<-40)에 있고 레버 끝만 캐리지 아래로 10.3 mm 들어간다. 캐리지가 내려가 레버를 누른다(경사·캠 없음).
실행: python public/cad/print/lift_collar_v3.py  (워크트리 루트에서). 출력자세: 옆으로 눕힘(-Y 바깥 끝이 베드가 아닌, 아래 make() 주석 참고).
"""
import numpy as np
import trimesh

from v12_parts import cyl, union, diff, save, OUT
from lift_fork import box, vol_int, carriage_model, rails, RAIL_XY, RAIL_W, SCREW_XY

# ---- 스위치 ----
SW_L, SW_W, SW_T = 29.41, 16.0, 10.3          # 길이, 폭(눌림 방향 =Z), 두께(X). 폭은 사진 17.7/표준 15.9 사이 가정, 두께는 가정
H_FREE, H_PRESS = 20.0, 17.0                   # 바닥(레버 반대 면) 기준 레버 끝 높이 (실측)
LEVER_OVER = 10.3                              # 레버 끝이 본체 끝 밖으로 나온 길이
LEVER_FROM_TIP = 5.0                           # 눌리는 접점: 끝에서 안쪽
HOLE_DY, HOLE_DZ = 21.0, 10.0                  # 고정 구멍 대각 간격 (길이, 폭)
TAP_D = 1.8                                    # M2 자체탭 파일럿 (먼 쪽 벽)
CLR_HOLE_D = 2.4                               # 가까운 쪽 벽 통과(+머리 자리)
HEAD_D = 4.2
CLR = 0.3
SEAT_Z = 103.0                                 # 상판 윗면
# ---- 캐리지 ----
CAR_Z0 = 119.0
CAR_Y0 = -40.0                                 # 캐리지 -Y 옆면
BODY_X0 = -6.1                                 # 본체 -X 면: 가까운 벽(-X)이 HM-10 대역(X<=-8.7)과 0.6 띄도록
BODY_Y1 = -10.1                                # 본체 +Y 끝(레버가 튀어나온 쪽). 힌지·배선 끝벽이 만능기판 대역(Y<=-42)과 겹치지 않게
RELIEF_Z = 3.0                                 # 캐리지 아랫면 본체 위 홈 깊이(lift_mast.py 와 일치, 폭 W<=19 까지 허용)
# ---- 칼라 ----
COL_X, COL_Y, COL_Z0, COL_H = (5.9, 24.0), (-40.0, -20.0), 104.0, 8.0
RAIL_CLR, SET_D = 0.1, 2.8
WALL_NEAR, WALL_FAR = 2.0, 4.0                 # 나사 머리 쪽(가까운) / 탭 쪽(먼) 벽
SHELF_T = 3.0                                  # 바닥 선반 Z104~107?  본체는 Z103 에 앉으므로 선반은 상판에서 띄움(아래 참고)


def geometry():
    y1 = BODY_Y1                               # 본체 +Y 끝 (레버가 튀어나온 쪽)
    y0 = y1 - SW_L                             # 본체 -Y 끝 (힌지·배선 쪽)
    return dict(y0=y0, y1=y1, tip_y=y1 + LEVER_OVER, contact_y=y1 + LEVER_OVER - LEVER_FROM_TIP,
                x0=BODY_X0, x1=BODY_X0 + SW_T, zb=SEAT_Z, zt=SEAT_Z + SW_W)


def make():
    g = geometry()
    y0, y1, x0, x1, zb, zt = g["y0"], g["y1"], g["x0"], g["x1"], g["zb"], g["zt"]
    cx, cy = RAIL_XY[0][0], -30.0
    rh = RAIL_W / 2 + RAIL_CLR
    cx0, cx1, cy0, cy1 = x0 - CLR, x1 + CLR, y0 - CLR, y1 + CLR   # 캐비티 (본체 ± 여유)
    wall_top = zt - 0.5

    block = box(COL_X[0], COL_X[1], COL_Y[0], COL_Y[1], COL_Z0, COL_Z0 + COL_H)         # 레일 클램프 블록
    # 좌우 벽 (가장 넓은 면 2개): 가까운 쪽 = -X(머리), 먼 쪽 = +X(탭). Y 는 본체 길이 + 끝벽까지, Z 는 선반 바닥 ~ 윗변
    wall_near = box(cx0 - WALL_NEAR, cx0, cy0 - 1.0, cy1 + 1.5, COL_Z0, wall_top)
    wall_far = box(cx1, cx1 + WALL_FAR, cy0 - 1.0, cy1 + 1.5, COL_Z0, wall_top)
    # 끝벽 (레버가 튀어나온 좁은 끝면, +Y): 본체 윗변 아래까지(레버는 그 위로 지나감)
    endw = box(cx0 - WALL_NEAR, cx1 + WALL_FAR, cy1, cy1 + 1.5, COL_Z0, wall_top)
    # 바닥 선반: 상판에서 1 띄운 Z104~(본체 바닥 Z103 보다 높아짐) -> 본체는 선반 윗면에 앉는다 => 본체 바닥을 선반 윗면(Z107)으로 올리면 높이가 변하므로
    # 선반은 두지 않고 본체가 상판(Z103)에 직접 앉는다. 벽·끝벽은 상판 위 Z104 에서 시작(1 mm 띄움)해 클램프 블록과 연결 암으로 이어진다.
    arm = box(cx0 - WALL_NEAR, COL_X[1] + 1.0, cy1 - 1.0, COL_Y[0] + 1.5, COL_Z0, COL_Z0 + 3.0)      # 블록과 끝벽 연결 (Y -41.5~-38.5)
    arm = box(cx0 - WALL_NEAR, max(COL_X[1] + 1.0, cx1 + WALL_FAR), COL_Y[0] - 2.5, COL_Y[0] + 1.5, COL_Z0, COL_Z0 + 3.0)
    body = union([block, wall_near, wall_far, endw])

    cuts = []
    cuts.append(box(cx - rh, cx + rh, cy - rh, cy + rh, COL_Z0 - 1, COL_Z0 + COL_H + 1))
    for s in (-1, 1):
        cuts.append(cyl(SET_D / 2, 7, (cx, cy + s * (10.0 + rh) / 2, COL_Z0 + COL_H / 2), "y", 24))
    # 캐비티: 두 벽 사이 (바닥 열림: 본체가 상판에 앉음), -Y 끝 열림 (힌지·배선 쪽)
    cuts.append(box(cx0, cx1, cy0 - 3.0, cy1, COL_Z0 - 1, zt + 5.0))
    # M2 나사 2개 (X 방향): 대각 (힌지끝·위쪽) / (레버끝·아래쪽). 구멍 Y,Z
    ymid, zmid = (y0 + y1) / 2, (zb + zt) / 2
    holes = [(ymid - HOLE_DY / 2, zmid + HOLE_DZ / 2), (ymid + HOLE_DY / 2, zmid - HOLE_DZ / 2)]
    for hy, hz in holes:
        cuts.append(cyl(CLR_HOLE_D / 2, WALL_NEAR + 2, (cx0 - WALL_NEAR / 2, hy, hz), "x", 24))                # 가까운 벽 통과
        cuts.append(cyl(HEAD_D / 2, 1.2 + 1, (cx0 - WALL_NEAR + 0.6 - 0.5, hy, hz), "x", 24))                  # 머리 자리 깊이 1.2
        cuts.append(cyl(TAP_D / 2, 4.5, (cx1 + 2.25 - 0.25, hy, hz), "x", 24))                                 # 먼 벽 파일럿 (벽 4 mm 중 깊이 ~4)
    # 배선 타이 슬릿 (-Y 끝 근처, 좌우 벽 관통: 다발을 벽에 묶음) Z zmid±3
    for tz in (zb + 4.0, zt - 4.0):
        cuts.append(box(cx0 - WALL_NEAR - 1, cx0 + 0.01, y0 + 1.5 - 0.8, y0 + 1.5 + 0.8, tz - 2.25, tz + 2.25))
        cuts.append(box(cx1 - 0.01, cx1 + WALL_FAR + 1, y0 + 1.5 - 0.8, y0 + 1.5 + 0.8, tz - 2.25, tz + 2.25))
    body = diff(body, cuts)
    assert body.is_watertight and body.volume > 0

    # 출력 자세: 먼 벽(+X) 바깥면이 베드: 로봇 (x,y,z) -> (-z..)  간단히 X 축을 Z 로: (x,y,z)->(y, z, -x)? det(+1)
    R = np.array([[0, 1, 0], [0, 0, 1], [-1, 0, 0]], float)    # (x,y,z)->(y, z, -x): +X 면이 아래(베드)
    v = body.vertices @ R.T
    mshift = v.min(0)
    v = v - mshift
    pm = body.copy()
    pm.vertices = v
    pm.fix_normals()
    r = save(pm, OUT / "P11_limit_collar_v3.stl")
    # placement: 로봇 = R^T (출력 + mshift)
    M = np.eye(4)
    M[:3, :3] = R.T
    M[:3, 3] = R.T @ mshift
    import json
    pj = OUT / "placement_fork.json"
    d = json.loads(pj.read_text(encoding="utf-8"))
    d["parts"]["P11_limit_collar_v3.stl"] = {"qty": 1, "matrix": [round(float(x), 4) for x in M.ravel()],
                                             "print_pose": "+X 벽 바깥면이 베드(옆으로 눕힘). 로봇 = M @ 출력"}
    d["parts"].pop("P11_limit_collar_v2.stl", None)
    pj.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print("P11_limit_collar_v3.stl placement 기록 (placement_fork.json)")
    print("P11_limit_collar_v3 출력자세(+X 벽 바깥면이 베드) bbox", r.bounds.round(2).tolist(), "vol %.2f cm3, 질량 약 %.1f g" % (r.volume / 1000, r.volume / 1000 * 1.27 * 0.6))

    # ---------------- 검사 (로봇 좌표) ----------------
    print("스위치: X %.1f~%.1f(두께) Y %.1f~%.1f(길이, -Y 끝=힌지·배선) Z %.1f~%.1f(폭) / 레버 끝 Y=%.1f 접점 Y=%.1f" % (
        x0, x1, y0, y1, zb, zt, g["tip_y"], g["contact_y"]))
    print("레버 끝 높이: 미작동 Z=%.1f(%.0f) -> 캐리지 아랫면 Z%.0f 에서 %.0f (작동 높이 %.0f, %.1f mm 더 눌림), 작동 시점은 스위치별(보통 OP~18.5)" % (
        SEAT_Z + H_FREE, H_FREE, CAR_Z0, CAR_Z0 - SEAT_Z, H_PRESS, H_PRESS - (CAR_Z0 - SEAT_Z)))
    car = carriage_model()
    sw = box(x0, x1, y0, y1, zb, zt)
    lever = box(x0 + 2.0, x1 - 2.0, y1, g["tip_y"], zt, SEAT_Z + H_FREE)           # 미작동 레버 (보수적 직육면체)
    asm = union([body, sw])
    items = {
        "레일": union(rails()), "캐리지(원점)": car, "스테퍼": box(-6, 36, -21, 21, 56, 100), "상판 P02 (Z100~103)": box(-93, 40, -75, 75, 100, 103),
        "허브 P20 r8": cyl(8.0, 20, (*SCREW_XY, 108.0)),
        "HM-10 대역(X-21.7~-8.7,Y-18.5~8.5,Z103~109)": box(-21.7, -8.7, -18.5, 8.5, 103, 109),
        "만능기판 대역(X-21.7~-1.7,Y-72~-42,Z107.8~112)": box(-21.7, -1.7, -72, -42, 107.8, 112),
        "Mega 대역": box(-78, -24.7, -26.7, 26.7, 103, 118),
    }
    for k, vv in items.items():
        print("[검사] 칼라+스위치 ↔ %-26s 겹침 %.3f mm3" % (k, vol_int(asm, vv)))
    print("[검사] 칼라 ↔ 미작동 레버 겹침 %.3f ; 칼라 bbox 로봇좌표 X %.1f~%.1f Y %.1f~%.1f Z %.1f~%.1f" % (
        vol_int(body, lever), body.bounds[0][0], body.bounds[1][0], body.bounds[0][1], body.bounds[1][1], body.bounds[0][2], body.bounds[1][2]))
    xc = (x0 + x1) / 2
    print("[검사] 레버 접점 위 캐리지 솔리드(X %.1f, Y %.1f, Z 125): %s ; 레버 끝 Y=%.1f 가 캐리지 아래(Y<40) %s" % (xc, g["contact_y"], bool(car.contains([[xc, g["contact_y"], 125.0], [xc, g["tip_y"] - 1, 125.0]]).all()), g["tip_y"], g["tip_y"] < 40))
    print("[검사] 나사 구멍 (Y,Z): %s ; 본체 가장자리까지 최소 %.1f ; 벽 높이 %.1f (본체 윗변 %.1f), 끝벽-캐리지 옆면 간극 %.1f" % (
        [(round(a, 1), round(b, 1)) for a, b in holes], min(min(a - y0, y1 - a, b - zb, zt - b) for a, b in holes), wall_top, zt, 0.0))
    return body


if __name__ == "__main__":
    make()
