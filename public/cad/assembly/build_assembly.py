"""전체 조립 장면 생성: 매니페스트 -> 렌더(PNG) / 간섭 검사 / three.js 뷰어.

실행(워크트리 루트):  python public/cad/assembly/build_assembly.py [옵션]
  --placement-dir DIR  placement_*.json 위치(기본 public/cad/print)
  --out-dir DIR        산출물 폴더(기본 이 파일 폴더)
  --no-render / --no-interference / --no-viewer / --no-anim   일부 건너뛰기
  --frames N           승강 애니메이션 프레임 수(기본 60)

승강부 신규 부품은 STL + placement_*.json 이 모두 있어야 자동 포함된다(없으면 건너뛰고 보고).
placement 형식은 관대하게 해석: 부품 이름(STL 줄기 이름)을 키 또는 name/file/part 값으로 가진 노드 안의
16개 숫자(또는 4x4 중첩 리스트)를 출력자세 -> 로봇좌표 행렬(row-major)로 읽는다. 행렬이 여러 개면 인스턴스 여러 개.
모든 승강부 placement 는 '원점 자세(포크 윗면 f=155)' 기준으로 해석한다.
"""
import argparse
import base64
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Point, box as sbox

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRINT = ROOT / "public" / "cad" / "print"

F0, F_SOFT, F_MECH = 155.0, 215.0, 227.0
SCREW_AXIS = (15.0, 0.0)
LEAD = 8.0  # Tr12x8 두 줄: 리드 8 (피치 4)
ENGINE = "manifold"
ONLY_BUILD = False  # --only-build-anim: 조립 영상 프레임만 다시 렌더


# ------------------------------------------------------------------ 행렬 도우미
def T(x=0.0, y=0.0, z=0.0):
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m


RZ180 = np.diag([-1.0, -1.0, 1.0, 1.0])


def M_rows(rows):
    m = np.eye(4)
    m[:3, :] = np.array(rows, float)
    return m


def screw_rot(angle):
    c, s = math.cos(angle), math.sin(angle)
    R = np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])
    return T(*SCREW_AXIS, 0) @ R @ T(-SCREW_AXIS[0], -SCREW_AXIS[1], 0)


# ------------------------------------------------------------------ 부품 정의
class Part:
    def __init__(self, pid, label, group, step, color, mesh, mats, ex=(0, 0, 0), mover=None, ref=False, opacity=1.0, src="", mass=None):
        self.pid, self.label, self.group, self.step = pid, label, group, step
        self.color, self.mesh, self.mats = color, mesh, [np.array(m, float) for m in mats]
        self.ex, self.mover, self.ref, self.opacity, self.src = ex, mover, ref, opacity, src
        # 질량(인스턴스 1개, g): 출력 부품은 부피 x PETG 1.27 g/cm3 x 충전 0.4, 기성품 대역은 지정값
        if mass is None:
            mass = float(abs(mesh.volume)) / 1000.0 * 1.27 * 0.4
        self.mass = mass
        try:
            self.com = np.array(mesh.center_mass if mesh.is_watertight else mesh.centroid, float)
        except Exception:  # noqa
            self.com = np.array(mesh.bounds.mean(0), float)
        # 인스턴스 중심 Y 부호(분해 방향) - 원점 자세 기준
        self.sign = []
        for m in self.mats:
            c = (mesh.bounds[0] + mesh.bounds[1]) / 2
            wy = (m @ np.append(c, 1.0))[1]
            self.sign.append(0.0 if abs(wy) < 1.0 else math.copysign(1.0, wy))


def box_mesh(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return m


def cyl_mesh(r, z0, z1, cx=0.0, cy=0.0, sections=48):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sections)
    m.apply_translation([cx, cy, (z0 + z1) / 2])
    return m


def load_stl(stem):
    m = trimesh.load(PRINT / f"{stem}.stl", force="mesh")
    return m


# 출력자세 -> 로봇좌표
P04_L = M_rows([[1, 0, 0, 0], [0, 0, -1, 74.5], [0, 1, 0, 0]])
P04_R = RZ180 @ P04_L
WHEEL_L = M_rows([[1, 0, 0, 0], [0, 0, -1, 105], [0, 1, 0, 32.5]])
WHEEL_R = RZ180 @ WHEEL_L

# placement json 으로 배치되는 부품: stem -> (라벨, 단계, 색, 분해 (dx,dy부호,dz), 이동구분)
LIFT_SPECS = {
    "P23_mast_L": ("P23 마스트 L (레일 일체)", 2, "#4fb3bf", (0, 40, 40), None),
    "P23_mast_R": ("P23 마스트 R (레일 일체)", 2, "#4fb3bf", (0, 40, 40), None),
    "P02_deck2_v2": ("P02 상판 v2 (기둥 일체)", 4, "#5b8fd1", (0, 0, 150), None),
    "P15_panel_v2": ("P15 패널 v2", 10, "#8f7ac9", (0, 15, 215), None),
    "P11_limit_collar_v3": ("P11 원점 리밋 칼라 v3", 11, "#c9a24a", (0, 45, 200), None),
    "P20_leadscrew_v2": ("P20 리드스크류 Tr12x8 2줄", 12, "#e0c14a", (0, 0, 175), "screw"),
    "P12_carriage_v2": ("P12 캐리지 v2", 13, "#e07a4f", (0, 0, 235), "lift"),
    "P24_nut_float": ("P24 플로팅 너트", 14, "#f0c040", (0, 0, 270), "lift"),
    "P13_fork_v2": ("P13 포크 v2", 16, "#d9534f", (0, 0, 300), "lift"),
    "P10_mast_upper_v2": ("P10 마스트 상부 v2", 17, "#4fb3bf", (0, 0, 330), None),
}


def _nums16(node):
    """노드 안의 16개 숫자 열(또는 4x4 중첩)을 모두 찾아 4x4 행렬 리스트로."""
    out = []

    def is_num(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def walk(n):
        if isinstance(n, list):
            if len(n) == 16 and all(is_num(v) for v in n):
                out.append(np.array(n, float).reshape(4, 4))
                return
            if len(n) == 4 and all(isinstance(r, list) and len(r) == 4 and all(is_num(v) for v in r) for r in n):
                out.append(np.array(n, float))
                return
            for v in n:
                walk(v)
        elif isinstance(n, dict):
            for v in n.values():
                walk(v)

    walk(node)
    return out


def load_placements(pdir):
    """placement_*.json 전체에서 {stem: [4x4,...]} 수집."""
    found = {}
    stems = sorted(LIFT_SPECS, key=len, reverse=True)

    def norm(s):
        s = str(s).replace("\\", "/").split("/")[-1]
        return s[:-4] if s.lower().endswith(".stl") else s

    def walk(n):
        if isinstance(n, dict):
            # name/file/part 값으로 식별되는 노드
            for k in ("name", "part", "file", "stl", "id"):
                if k in n and isinstance(n[k], str) and norm(n[k]) in LIFT_SPECS:
                    found.setdefault(norm(n[k]), []).extend(_nums16({kk: vv for kk, vv in n.items() if kk != k}))
                    return
            for k, v in n.items():
                if norm(k) in LIFT_SPECS:
                    found.setdefault(norm(k), []).extend(_nums16(v))
                else:
                    walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    files = sorted(Path(pdir).glob("placement_*.json"))
    for f in files:
        try:
            walk(json.loads(f.read_text(encoding="utf-8")))
        except Exception as e:  # noqa
            print(f"[경고] {f.name} 읽기 실패: {e}")
    return found, [f.name for f in files]


def build_parts(pdir):
    P = []
    missing = []

    def add(*a, **k):
        P.append(Part(*a, **k))

    def stl(stem, label, group, step, color, mats, ex, **k):
        if not (PRINT / f"{stem}.stl").exists():
            missing.append(f"{stem}.stl 없음")
            return
        add(stem, label, group, step, color, load_stl(stem), mats, ex, src=f"{stem}.stl", **k)

    I = np.eye(4)
    # ---- 출력 부품(하체) ------------------------------------------------
    stl("P01_deck1_v3", "P01 하판 v3", "하체", 1, "#5b8fd1", [I], (0, 0, 0))
    stl("P08_stepper_brkt", "P08 스테퍼 칼라", "상체", 3, "#c9a24a", [I], (-40, 0, 25))
    stl("P08_stepper_plate", "P08 스테퍼 판", "상체", 3, "#c9a24a", [I], (0, 0, 95))
    stl("P14_batt_cradle_v2_L", "P14 배터리 크래들 v2 L", "하체", 5, "#8f7ac9", [I], (0, 25, 35))
    stl("P14_batt_cradle_v2_R", "P14 배터리 크래들 v2 R", "하체", 5, "#8f7ac9", [I], (0, 25, 35))
    stl("P05_caster_spacer_v2", "P05 캐스터 스페이서 v2", "하체", 6, "#7aa7e0", [T(0, 0, 29)], (0, 0, -40))
    stl("P06_line_hanger", "P06 라인 행어", "하체", 9, "#d96e8c", [I], (50, 0, -15))
    stl("P06_line_head_t0", "P06 라인 헤드 t0", "하체", 9, "#d96e8c", [I], (110, 0, -15))
    stl("P04_motor_brkt_L", "P04 모터 브래킷 L", "하체", 7, "#e4a23b", [P04_L], (0, 60, -50))
    stl("P04_motor_brkt_R", "P04 모터 브래킷 R", "하체", 7, "#e4a23b", [P04_R], (0, 60, -50))
    stl("P16_wheel_body_v2", "P16 바퀴 본체 v2 (x2)", "하체", 8, "#3fae8f", [WHEEL_L, WHEEL_R], (0, 120, -50))
    stl("P17_wheel_tire_TPU", "P17 TPU 타이어 (x2)", "하체", 8, "#222222", [WHEEL_L @ T(0, 0, 1.5), WHEEL_R @ T(0, 0, 1.5)], (0, 170, -50))

    # ---- 기성품 대역 -----------------------------------------------------
    m = trimesh.creation.cylinder(radius=17.5, height=69.3, sections=64)
    m.apply_transform(M_rows([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0]]))  # 원기둥 z축 -> Y축
    m.apply_translation([0, (1.2 + 70.5) / 2, 25.0])
    d2 = Point(0, 0).buffer(3.0, resolution=32).intersection(sbox(-4, -4, 2.5, 4))
    shaft = trimesh.creation.extrude_polygon(d2, 12.0)  # 로컬 z 0..12 (D축, 플랫 x<=2.5)
    shaft.apply_transform(M_rows([[1, 0, 0, 0], [0, 0, 1, 70.5], [0, -1, 0, 32.5]]))
    add("REF_dc_motor", "DC 모터 몸통 Ø35 (대역, x2)", "기성품", 7, "#8a8f98", m, [I, RZ180], (0, 20, -50), ref=True, mass=150.0)
    add("REF_dc_shaft", "DC 모터 D축 Ø6 (대역, x2)", "기성품", 7, "#d5d8dc", shaft, [I, RZ180], (0, 20, -50), ref=True, mass=0.0)

    caster = trimesh.util.concatenate([
        box_mesh(-85, -65, -33.5, 33.5, 26, 29),            # 장착판 (구멍 간격 57)
        cyl_mesh(9.0, 12.0, 26.0, -75, 0),
        trimesh.creation.icosphere(subdivisions=3, radius=4.76).apply_translation([-75, 0, 4.76]),
        cyl_mesh(5.0, 4.76, 12.0, -75, 0)])
    add("REF_caster", "볼 캐스터 (대역, 높이 29, 구멍 간격 57)", "기성품", 6, "#9aa0a6", caster, [I], (0, 0, -85), ref=True, mass=40.0)

    for side, (y0, y1) in (("L", (0.0, 90.0)), ("R", (-90.0, 0.0))):
        add(f"REF_battery_{side}", f"배터리 팩 90x58x16 {side} (대역)", "기성품", 5, "#2f4f9f",
            box_mesh(-92, -34, y0, y1, 58, 74), [I], (0, 40, 75), ref=True, mass=200.0)
    add("REF_line_pcb", "라인센서 PCB 66x24x1.6 (대역)", "기성품", 9, "#1b6b3a",
        box_mesh(13, 37, -33, 33, 10.0, 11.6), [I], (150, 0, -15), ref=True, mass=15.0)
    add("REF_stepper", "스테퍼 SF2421 42x42x40 (대역)", "기성품", 3, "#303338",
        box_mesh(-6, 36, -21, 21, 56, 96), [I], (0, 0, 50), ref=True, mass=280.0)
    add("REF_stepper_shaft", "스테퍼 축 Ø5 Z96~118 (실측 22 mm, D플랫 15 mm 생략)", "기성품", 3, "#d5d8dc",
        cyl_mesh(2.5, 96, 118, 15, 0, 32), [I], (0, 0, 50), ref=True, mass=0.0)

    # 상판 전자부품 (deck2_layout.md 표). 보드는 판 위 4.8 띄움(Z 107.8~)
    add("REF_mega", "Mega + 쉴드 101.6x53.3 (대역, 보드 아래 4.8 띄움, Z<=130)", "기성품", 10, "#1f7a5c",
        box_mesh(-78, -24.7, -70, 31.6, 107.8, 130), [I], (0, 0, 215), ref=True, mass=90.0)
    add("REF_l298", "L298 43.5x43.5x29 (대역, 1/3개)", "기성품", 10, "#b53a3a",
        box_mesh(-73.75, -30.25, 34.6, 78.1, 107.8, 136.8), [I], (0, 0, 215), ref=True, mass=40.0)
    add("REF_drv", "DRV8825 15.5x20.5 (대역)", "기성품", 10, "#3a6bb5",
        box_mesh(-21.7, -1.2, 39.25, 54.75, 107.8, 117.0), [I], (0, 0, 215), ref=True, mass=5.0)
    add("REF_hm10", "HM-10 27x13 (대역)", "기성품", 10, "#2a5a9f",
        box_mesh(-21.7, -8.7, -18.5, 8.5, 103, 109), [I], (0, 0, 215), ref=True, mass=5.0)
    add("REF_perf", "만능기판 30x20 (대역, 가정 질량 5 g)", "기성품", 10, "#a0a050",
        box_mesh(-21.7, -1.7, -72, -42, 107.8, 112), [I], (0, 0, 215), ref=True, mass=5.0)

    # 마이크로 스위치 GSM-V1621A2: 캐리지 옆(-Y)에 세움(L x T 면이 바닥). P11 v3 (lift_collar_v3.py geometry)
    import sys as _sys
    _sys.path.insert(0, str(PRINT))
    import lift_collar_v3 as _lc
    _g = _lc.geometry()
    sw = box_mesh(_g["x0"], _g["x1"], _g["y0"], _g["y1"], _g["zb"], _g["zt"])                                    # 본체
    lev = box_mesh(_g["x0"] + 2.0, _g["x1"] - 2.0, _g["y0"] + 3.0, _g["tip_y"], _g["zt"] - 0.4, _g["zt"])         # 레버(원점 자세에서 평평하게 눌림). 뷰어에서 승강에 따라 힌지 중심으로 회전
    add("REF_switch", "원점 마이크로 스위치 GSM-V1621A2 29.4x16x10.3 (세움, 대역)", "기성품", 11, "#303338", sw, [I], (0, 45, 200), ref=True, mass=3.0)
    add("REF_switch_lever", "스위치 레버 (승강 연동: 캐리지가 내려오면 눌림)", "기성품", 11, "#ff5a4f", lev, [I], (0, 45, 200), mover="lever", ref=True, mass=0.0)

    # ---- placement 로 배치되는 부품 ---------------------------------------
    placements, pfiles = load_placements(pdir)
    for stem, (label, step, color, ex, mover) in LIFT_SPECS.items():
        has_stl = (PRINT / f"{stem}.stl").exists()
        mats = placements.get(stem)
        if not has_stl or not mats:
            missing.append(f"{stem}: " + ("STL 없음" if not has_stl else "placement 행렬 없음"))
            continue
        add(stem, label, "승강부" if step >= 11 or stem.startswith("P23") else "상체", step, color, load_stl(stem), mats, ex, mover=mover, src=f"{stem}.stl")
        if stem == "P24_nut_float":
            P[-1].mass = 6.7  # 지정 질량

    # IR / CD / 포크 의존 부품
    have_fork = any(p.pid == "P13_fork_v2" for p in P)
    # IR GP2Y0A21YK0F: 센서 중심 (54.7, 22.7), 렌즈면 Z = f-42, 본체 13(X) x 29.5(Y) x 18.9(렌즈 케이스 포함), 귀 44.5(Y) 두께 1.2 (렌즈면 아래 3.3)
    zf = F0 - 42.0
    ir = trimesh.util.concatenate([box_mesh(54.7 - 6.5, 54.7 + 6.5, 22.7 - 14.75, 22.7 + 14.75, zf - 18.9, zf),
                                   box_mesh(54.7 - 3, 54.7 + 3, 22.7 - 22.25, 22.7 + 22.25, zf - 4.5, zf - 3.3)])
    # 포크 넥 스위치(포크 밑에 매달림, lift_fork.py): 본체 X 30.2~59.6, Y ysw+-8.85 (ysw=-6.15), Z 139.7~150.0, 정지 레버 X 43.1~70.1, Y +-3, Z 150.2~154.0
    ysw = -(18.1 / 2 - 2.9)
    nsw = box_mesh(30.0 + 0.2, 59.8 - 0.2, ysw - 8.85, ysw + 8.85, 139.7, 150.0)
    nlev = box_mesh(43.1, 70.1, -3.0, 3.0, 150.2, 154.0)
    cd2 = Point(92, 0).buffer(60.0, resolution=96).difference(Point(92, 0).buffer(7.5, resolution=32))
    cd = trimesh.creation.extrude_polygon(cd2, 1.2)
    cd.apply_translation([0, 0, F0])
    if have_fork:
        add("REF_ir", "상향 IR GP2Y0A21YK0F (대역: 본체+귀+렌즈 케이스, 중심 (54.7, 22.7), 렌즈면 f-42)", "기성품", 15, "#202124", ir, [I], (60, 0, 260), mover="lift", ref=True, mass=10.0)
        add("REF_neck_switch", "넥 접촉 마이크로 스위치 GSM-V1621A2 (대역, 본체, 포크 밑에 매달림)", "기성품", 16, "#303338", nsw, [I], (40, 0, -60), mover="lift", ref=True, mass=3.0)
        add("REF_neck_lever", "넥 스위치 레버(정지 상태, 끝 Z 154)", "기성품", 16, "#8a8f98", nlev, [I], (40, 0, -60), mover="lift", ref=True, mass=0.0)
        add("REF_cd", "기준 CD Ø120x1.2 (대역, 가정 질량 15 g)", "기성품", 18, "#c8d6e5", cd, [I], (0, 0, 360), mover="lift", ref=True, opacity=0.85, mass=15.0)
    else:
        missing.append("REF_ir / REF_cd: 포크 v2 없음 -> 장면 제외")

    add("REF_floor", "경기장 기준 바닥판 (대역)", "기타", 0, "#e6e9ee", box_mesh(-350, 350, -250, 250, -2, 0), [I], (0, 0, 0), ref=True, mass=0.0)
    return P, missing, pfiles


def get_units(parts):
    """조립 순서 단위: 각 단위는 한 덩어리로 u 방향(들어오는 쪽)에서 dmax 까지 끌어당겨 간섭을 본다."""
    P = {p.pid: p for p in parts}
    U = []

    def u(tag, step, name, items, dirv, dmax, skip=()):
        keep = [i for i in items if i.split(":")[0] in P]
        if keep:
            U.append(dict(tag=tag, step=step, name=name, items=keep, u=dirv, dmax=dmax, skip=set(skip)))

    u("deck1", 1, "P01 하판 v3", ["P01_deck1_v3"], (0, 0, 1), 60)
    u("mast_L", 2, "P23 마스트 L (위에서 내려놓고 하판 아래에서 M3x16)", ["P23_mast_L"], (0, 0, 1), 40)
    u("mast_R", 2, "P23 마스트 R", ["P23_mast_R"], (0, 0, 1), 40)
    u("stepper", 3, "스테퍼 칼라 + 스테퍼", ["P08_stepper_brkt", "REF_stepper", "REF_stepper_shaft"], (0, 0, 1), 60)
    u("plate", 3, "스테퍼 판", ["P08_stepper_plate"], (0, 0, 1), 40)
    u("deck2", 4, "P02 상판 v2 (레일 위로 내려놓음)", ["P02_deck2_v2"], (0, 0, 1), 150)
    u("cradle_L", 5, "배터리 크래들 L (뒤에서 밀어 넣음)", ["P14_batt_cradle_v2_L"], (-1, 0, 0), 80)
    u("cradle_R", 5, "배터리 크래들 R", ["P14_batt_cradle_v2_R"], (-1, 0, 0), 80)
    u("batt_L", 5, "배터리 L (뒤에서 수평으로 크래들에)", ["REF_battery_L"], (-1, 0, 0), 80)
    u("batt_R", 5, "배터리 R", ["REF_battery_R"], (-1, 0, 0), 80)
    u("caster", 6, "캐스터 스페이서 + 캐스터 (아래에서)", ["P05_caster_spacer_v2", "REF_caster"], (0, 0, -1), 60)
    u("motor_L", 7, "P04 L + 모터 서브어셈블리 (아래에서)", ["P04_motor_brkt_L", "REF_dc_motor:0", "REF_dc_shaft:0"], (0, 0, -1), 60)
    u("motor_R", 7, "P04 R + 모터 서브어셈블리 (아래에서)", ["P04_motor_brkt_R", "REF_dc_motor:1", "REF_dc_shaft:1"], (0, 0, -1), 60)
    u("wheel_L", 8, "바퀴 L + 타이어 (바깥에서)", ["P16_wheel_body_v2:0", "P17_wheel_tire_TPU:0"], (0, 1, 0), 60)
    u("wheel_R", 8, "바퀴 R + 타이어 (바깥에서)", ["P16_wheel_body_v2:1", "P17_wheel_tire_TPU:1"], (0, -1, 0), 60)
    u("hanger", 9, "라인 행어 (앞에서 밀어 넣어 하판 아래에)", ["P06_line_hanger"], (1, 0, 0), 60)
    u("head", 9, "라인 헤드 (앞에서 행어에 끼움)", ["P06_line_head_t0"], (1, 0, 0), 60)
    u("pcb", 9, "라인센서 PCB (아래에서)", ["REF_line_pcb"], (0, 0, -1), 40)
    u("panel", 10, "P15 패널 v2", ["P15_panel_v2"], (0, 0, 1), 40)
    u("mega", 10, "Mega + 쉴드", ["REF_mega"], (0, 0, 1), 30)
    u("l298", 10, "L298", ["REF_l298"], (0, 0, 1), 30)
    u("drv", 10, "DRV8825", ["REF_drv"], (0, 0, 1), 30)
    u("hm10", 10, "HM-10", ["REF_hm10"], (0, 0, 1), 30)
    u("perf", 10, "만능기판", ["REF_perf"], (0, 0, 1), 30)
    u("collar", 11, "리밋 칼라 + 마이크로 스위치 (칼라는 레일에 끼우고 세트스크류, 스위치는 두 벽 사이에 세워 M2 2개)", ["P11_limit_collar_v3", "REF_switch", "REF_switch_lever"], (0, 0, 1), 150)
    u("screw", 12, "리드스크류 (위에서 모터 축에 삽입)", ["P20_leadscrew_v2"], (0, 0, 1), 150)
    u("carriage", 13, "캐리지 (레일 위에서 내려 스크류를 통과)", ["P12_carriage_v2"], (0, 0, 1), 130)
    u("nut", 14, "플로팅 너트를 캐리지 윗면 카운터보어에 넣음", ["P24_nut_float"], (0, 0, 1), 60, skip=("P20_leadscrew_v2",))
    u("ir", 15, "IR 센서를 트레이에 넣고 센서 귀를 M3로 트레이에 고정", ["REF_ir"], (0, 0, 1), 80)
    u("fork", 16, "포크 v2 (레일 위에서, 판으로 너트를 덮음)", ["P13_fork_v2"], (0, 0, 1), 130)
    u("neck", 16, "넥 스위치를 포크 아래 하우징에 앞쪽에서 끼우고 M2 볼트/결속밴드로 고정", ["REF_neck_switch", "REF_neck_lever"], (1, 0, 0), 60)
    u("p10", 17, "P10 마스트 상부 (위에서 씌움)", ["P10_mast_upper_v2"], (0, 0, 1), 40)
    u("cd", 18, "기준 CD", ["REF_cd"], (0, 0, 1), 40)
    return U


def resolve_items(parts, unit):
    P = {p.pid: p for p in parts}
    out = []
    for it in unit["items"]:
        if ":" in it:
            pid, k = it.split(":")
            out.append((P[pid], int(k)))
        else:
            out += [(P[it], k) for k in range(len(P[it].mats))]
    return out


# ------------------------------------------------------------------ 자세/월드 메쉬
def pose_mats(part, dz=0.0, explode=0.0, spin=True):
    """부품 인스턴스별 월드 행렬. dz = f - 155."""
    out = []
    for m, sg in zip(part.mats, part.sign):
        M = m
        if part.mover == "lift":
            M = T(0, 0, dz) @ M
        elif part.mover == "screw" and spin:
            M = screw_rot(dz / LEAD * 2 * math.pi) @ M
        if explode:
            M = T(part.ex[0] * explode, part.ex[1] * sg * explode, part.ex[2] * explode) @ M
        out.append(M)
    return out


def world_mesh(part, M):
    w = part.mesh.copy()
    w.apply_transform(M)
    return w


def scene_bounds(parts, dzs=(0.0,), explode=0.0, skip_floor=True):
    lo, hi = np.full(3, 1e9), np.full(3, -1e9)
    for p in parts:
        if skip_floor and p.pid == "REF_floor":
            continue
        for dz in dzs:
            for M in pose_mats(p, dz, explode, spin=False):
                b = p.mesh.bounds
                corners = np.array([[x, y, z, 1] for x in b[:, 0] for y in b[:, 1] for z in b[:, 2]])
                w = (M @ corners.T).T[:, :3]
                lo, hi = np.minimum(lo, w.min(0)), np.maximum(hi, w.max(0))
    return lo, hi


# ------------------------------------------------------------------ 렌더
def render_all(parts, out, frames, want_anim=True, units=None, want_build=True):
    import pyvista as pv
    pv.OFF_SCREEN = True
    renders = out / "renders"
    renders.mkdir(parents=True, exist_ok=True)

    cache = {}

    def pvm(p):
        if p.pid not in cache:
            msh = p.mesh
            f = np.hstack([np.full((len(msh.faces), 1), 3), msh.faces]).ravel()
            cache[p.pid] = pv.PolyData(np.asarray(msh.vertices), f)
        return cache[p.pid]

    font = r"C:\Windows\Fonts\malgun.ttf"
    use_font = Path(font).exists()

    def new_plotter(w, h):
        pl = pv.Plotter(off_screen=True, window_size=(w, h))
        pl.set_background("white", top="#dfe6ef")
        try:
            pl.enable_anti_aliasing("ssaa")
        except Exception:
            pass
        return pl

    def cam(pl, kind, lo, hi, aspect):
        c = (lo + hi) / 2
        ext = hi - lo
        R = float(np.linalg.norm(ext)) / 2
        views = {"iso": ((1.0, 1.25, 0.8), (0, 0, 1)), "iso2": ((0.55, 1.0, 0.45), (0, 0, 1)),
                 "front": ((1, 0, 0), (0, 0, 1)), "side": ((0, 1, 0), (0, 0, 1)), "top": ((0, 0, 1), (1, 0, 0))}
        custom = isinstance(kind, tuple)
        if isinstance(kind, tuple):
            d, up = kind, (0, 0, 1)
            kind = "iso"
        else:
            d, up = views[kind]
        d = np.array(d, float) / np.linalg.norm(d)
        camobj = pl.camera
        if kind == "iso" or kind == "iso2":
            pl.disable_parallel_projection()
            camobj.view_angle = 30
            dist = R / math.sin(math.radians(15)) * (0.95 if kind == "iso2" else (0.62 if custom else 0.78))
            if aspect < 1.2:
                dist *= 1.1
        else:
            pl.enable_parallel_projection()
            dist = R * 3
            # 해당 방향에 보이는 가로/세로 크기로 스케일
            if kind == "front":
                w_, h_ = ext[1], ext[2]
            elif kind == "side":
                w_, h_ = ext[0], ext[2]
            else:
                w_, h_ = ext[1], ext[0]
            camobj.parallel_scale = max(h_ / 2, w_ / 2 / aspect) * 1.12
        camobj.position = tuple(c + d * dist)
        camobj.focal_point = tuple(c)
        camobj.up = up
        pl.renderer.reset_camera_clipping_range()

    def draw(path, kind, lo, hi, size, items, title=None):
        """items: [(part, [M..], color, opacity)]"""
        if ONLY_BUILD and "build_anim" not in str(path):
            return
        pl = new_plotter(*size)
        for p, Ms, color, op in items:
            for M in Ms:
                a = pl.add_mesh(pvm(p), color=color, opacity=op, smooth_shading=False, specular=0.25,
                                specular_power=20, ambient=0.25, diffuse=0.8)
                a.user_matrix = M
        cam(pl, kind, lo, hi, size[0] / size[1])
        if title:
            kw = dict(font_size=13, color="#222222", position="upper_left")
            if use_font:
                kw["font_file"] = font
            pl.add_text(title, **kw)
        pl.screenshot(str(path))
        pl.close()

    real = [p for p in parts if p.pid != "REF_floor"]
    floor = [p for p in parts if p.pid == "REF_floor"]
    lo0, hi0 = scene_bounds(parts, (0.0, F_SOFT - F0))

    def full_items(dz, explode=0.0, with_floor=True):
        it = [(p, pose_mats(p, dz, explode), p.color, p.opacity) for p in real]
        if with_floor and not explode:
            it += [(p, pose_mats(p), p.color, 1.0) for p in floor]
        return it

    n = 0
    # 4방향
    for kind, nm in (("iso", "iso"), ("front", "front"), ("side", "side"), ("top", "top")):
        draw(renders / f"view_{nm}.png", kind, lo0, hi0, (1400, 1000), full_items(0.0),
             f"{nm} view, lift f={F0:.0f}")
        n += 1
    # 분해도
    lo_e, hi_e = scene_bounds(parts, (0.0,), 1.0)
    draw(renders / "exploded.png", "iso2", lo_e, hi_e, (1400, 1500), full_items(0.0, 1.0), "exploded view")
    n += 1
    # 승강 2자세 (측면 + 등각)
    for f, nm in ((F0, "home_f155"), (F_SOFT, "top_f215")):
        draw(renders / f"lift_{nm}_iso.png", "iso", lo0, hi0, (1400, 1000), full_items(f - F0), f"lift f={f:.0f}")
        draw(renders / f"lift_{nm}_side.png", "side", lo0, hi0, (1400, 1000), full_items(f - F0), f"lift f={f:.0f} (side)")
        n += 2
    # 단계별
    steps = sorted({p.step for p in real})
    stepfiles = []
    for s in steps:
        items = []
        for p in real:
            if p.step > s:
                continue
            if p.step == s:
                items.append((p, pose_mats(p), "#ff7a00", 1.0))
            else:
                items.append((p, pose_mats(p), "#b9c6d8", 0.55))
        items += [(p, pose_mats(p), p.color, 1.0) for p in floor]
        names = ", ".join(p.label for p in real if p.step == s)
        fn = renders / f"step_{s:02d}.png"
        draw(fn, "iso", lo0, hi0, (1400, 1000), items, f"Step {s}: " + (names if use_font else f"{s}"))
        stepfiles.append(fn)
        n += 1
    # 애니메이션
    gif_frames = []
    if want_anim:
        adir = renders / "lift_anim"
        adir.mkdir(exist_ok=True)
        for old in adir.glob("*.png"):
            old.unlink()
        for i in range(frames):
            f = F0 + (F_SOFT - F0) * i / (frames - 1)
            fn = adir / f"frame_{i:03d}.png"
            draw(fn, "iso", lo0, hi0, (900, 700), full_items(f - F0), f"f = {f:5.1f} mm")
            gif_frames.append(fn)
            n += 1
        try:
            from PIL import Image
            ims = [Image.open(x).convert("P", palette=Image.ADAPTIVE) for x in gif_frames]
            seq = ims + ims[::-1]
            seq[0].save(adir / "lift_anim.gif", save_all=True, append_images=seq[1:], duration=60, loop=0)
        except Exception as e:  # noqa
            print("[경고] GIF 생성 실패:", e)

    # 조립 과정 애니메이션: 부품이 순서대로 날아와 자리잡는다
    if want_build and units:
        import shutil
        import subprocess
        bdir = renders / "build_anim"
        bdir.mkdir(exist_ok=True)
        for old in bdir.glob("*.png"):
            old.unlink()
        unit_of = {}
        for uu in units:
            for p_, k_ in resolve_items(parts, uu):
                unit_of[(p_.pid, k_)] = uu
        NF, FLY = 24, 16
        steps_b = sorted({uu["step"] for uu in units})
        total = len(steps_b) * NF + 16
        fi = 0
        srt = []
        FPS = 8.0

        def stamp(i):
            t = i / FPS
            h, r_ = divmod(t, 3600)
            m_, s_ = divmod(r_, 60)
            return ("%02d:%02d:%06.3f" % (h, m_, s_)).replace(".", ",")

        def smooth(x):
            x = min(max(x, 0.0), 1.0)
            return 1 - (1 - x) ** 3

        for si, st in enumerate(steps_b):
            names = [uu["name"] for uu in units if uu["step"] == st]
            cap = "단계 %d/%d: %s" % (si + 1, len(steps_b), " / ".join(names))
            srt.append((fi, fi + NF, cap))
            for i in range(NF):
                az = math.radians(20 + 90.0 * fi / total)
                el = math.radians(30)
                dvec = (math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))
                prog = smooth(i / (FLY - 1))
                items = []
                for p_ in real:
                    if p_.step > st:
                        continue
                    for k_, M_ in enumerate(pose_mats(p_)):
                        if p_.step == st:
                            uu = unit_of.get((p_.pid, k_))
                            off = np.zeros(3)
                            if uu is not None:
                                uv = np.array(uu["u"], float)
                                uv /= np.linalg.norm(uv)
                                off = uv * min(max(uu["dmax"], 60), 150) * (1 - prog)
                            items.append((p_, [T(*off) @ M_], "#ff7a00", 1.0))
                        else:
                            items.append((p_, [M_], "#b9c6d8", 1.0))
                items += [(p_, pose_mats(p_), p_.color, 1.0) for p_ in floor]
                draw(bdir / f"frame_{fi:04d}.png", dvec, lo0, hi0, (1280, 720), items, "Step %d/%d" % (si + 1, len(steps_b)))
                fi += 1
        srt.append((fi, fi + 16, "완성"))
        for i in range(16):
            az = math.radians(20 + 90.0 * fi / total)
            dvec = (math.cos(math.radians(30)) * math.cos(az), math.cos(math.radians(30)) * math.sin(az), math.sin(math.radians(30)))
            draw(bdir / f"frame_{fi:04d}.png", dvec, lo0, hi0, (1280, 720), full_items(0.0), "Done")
            fi += 1
        n += fi
        with open(renders / "build_anim.srt", "w", encoding="utf-8") as fsrt:
            for j, (a_, b_, c_) in enumerate(srt, 1):
                fsrt.write(f"{j}\n{stamp(a_)} --> {stamp(b_)}\n{c_}\n\n")
        ff = shutil.which("ffmpeg")
        if not ff:
            import glob
            g = glob.glob(str(Path.home() / "AppData/Local/Microsoft/WinGet/Packages/*FFmpeg*/**/bin/ffmpeg.exe"), recursive=True)
            ff = g[0] if g else None
        if ff:
            subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(bdir / "frame_%04d.png"),
                            "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20", str(renders / "build_anim.mp4")], check=False)
            print("build_anim.mp4 ->", renders / "build_anim.mp4", "(%d 프레임, %.0f 초)" % (fi, fi / FPS))
        else:
            print("[경고] ffmpeg 없음: mp4 생략")
    print(f"렌더 {n}장 -> {renders}")
    return n


# ------------------------------------------------------------------ 간섭·조립성·질량중심 분석
POSES = (155.0, 165.0, 175.0, 190.0, 195.0, 215.0, 227.0)
KNOWN = {
    frozenset(["P16_wheel_body_v2", "P17_wheel_tire_TPU"]): "의도된 압입: 타이어 ID 59.7 < 림 Ø60 (TPU 신축 끼움)",
    frozenset(["P20_leadscrew_v2", "P24_nut_float"]): "나사 맞물림: 정적 자세의 스크류 위상(0°) 때문. 위상 70~90° 에서 0 (5-2장)",
}


def _bb_overlap(a, b, tol=1e-6):
    return not np.any(np.minimum(a[1], b[1]) - np.maximum(a[0], b[0]) <= tol)


def _inter(wa, wb):
    r = trimesh.boolean.intersection([wa, wb], engine=ENGINE)
    if not len(r.faces):
        return 0.0, None
    return float(abs(r.volume)), r.bounds


def interference(parts):
    """POSES 각 자세에서 모든 인스턴스 쌍(AABB 후 불린). 고정 쌍은 한 번만 계산."""
    rows = {}
    skipped = []
    cache = {}
    n_bool = 0
    for f in POSES:
        dz = f - F0
        inst = []
        for p in parts:
            if p.pid == "REF_floor":
                continue
            for k, M in enumerate(pose_mats(p, dz, 0.0, spin=False)):
                inst.append((p, k, world_mesh(p, M)))
        for i in range(len(inst)):
            for j in range(i + 1, len(inst)):
                pa, ka, wa = inst[i]
                pb, kb, wb = inst[j]
                if not _bb_overlap(wa.bounds, wb.bounds):
                    continue
                moving = pa.mover == "lift" or pb.mover == "lift"
                key = (pa.pid, ka, pb.pid, kb)
                if not moving and key in cache:
                    vol, bb = cache[key]
                else:
                    try:
                        vol, bb = _inter(wa, wb)
                        n_bool += 1
                    except Exception as e:  # noqa
                        skipped.append(f"f={f:.0f}: {pa.pid}[{ka}] x {pb.pid}[{kb}]: {e}")
                        vol, bb = 0.0, None
                    if not moving:
                        cache[key] = (vol, bb)
                if vol > 0.5:
                    c = (bb[0] + bb[1]) / 2
                    sz = bb[1] - bb[0]
                    rk = (pa.pid, ka, pb.pid, kb, round(vol), tuple(np.round(c, 0)))
                    row = rows.setdefault(rk, dict(pa=pa, ka=ka, pb=pb, kb=kb, vol=vol, c=c, sz=sz, poses=[]))
                    row["poses"].append(f)
    print(f"간섭: 불린 {n_bool}회, 겹침 행 {len(rows)}")
    return list(rows.values()), skipped


def envelope(parts):
    out = []
    for f in (F0, F_SOFT, F_MECH):
        lo, hi = scene_bounds([p for p in parts if p.pid != "REF_floor"], (f - F0,), 0.0)
        out.append((f, lo, hi))
    return out


# ---- 조립 순서 sweep
SAMPLES = [1, 2, 3, 4, 6, 8, 10, 13, 16, 20, 25, 30, 40, 50, 60, 75, 90, 105, 120, 135, 150]


def origin_meshes(parts):
    wm = {}
    for p in parts:
        if p.pid == "REF_floor":
            continue
        for k, M in enumerate(p.mats):
            wm[(p.pid, k)] = world_mesh(p, M)
    return wm


def run_sweeps(parts, units, wm):
    inst_unit = {}
    for ui, uu in enumerate(units):
        for p, k in resolve_items(parts, uu):
            inst_unit[(p.pid, k)] = ui
    base_cache = {}
    results = []
    for ui, uu in enumerate(units):
        installed = [key for key, uj in inst_unit.items() if uj < ui and key[0] not in uu["skip"]]
        moving = [(p.pid, k) for p, k in resolve_items(parts, uu)]
        dirv = np.array(uu["u"], float)
        dirv /= np.linalg.norm(dirv)
        found = {}
        for d in [s for s in SAMPLES if s <= uu["dmax"]]:
            for mk in moving:
                wmov = wm[mk]
                mb = wmov.bounds + d * dirv
                for ik in installed:
                    if (mk, ik) in found:
                        continue
                    if not _bb_overlap(mb, wm[ik].bounds):
                        continue
                    sh = wmov.copy()
                    sh.apply_translation(d * dirv)
                    try:
                        vol, bb = _inter(sh, wm[ik])
                    except Exception:  # noqa
                        continue
                    if vol <= 0.5:
                        continue
                    if (mk, ik) not in base_cache:
                        try:
                            base_cache[(mk, ik)] = _inter(wmov, wm[ik])[0]
                        except Exception:  # noqa
                            base_cache[(mk, ik)] = 0.0
                    if vol > base_cache[(mk, ik)] + 0.5 and base_cache[(mk, ik)] <= 0.5:
                        found[(mk, ik)] = (d, vol, (bb[0] + bb[1]) / 2)
        results.append((uu, found))
        print(f"  sweep {uu['tag']:10s} 막힘 {len(found)}")
    return results


# ---- 공구 접근(육각렌치 원기둥) 검사
def tool_blockers(wm, keys, start, axis, r, length):
    axis = np.array(axis, float)
    axis /= np.linalg.norm(axis)
    cyl = trimesh.creation.cylinder(radius=r, height=length, sections=16)
    cyl.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], axis))
    cyl.apply_translation(np.array(start, float) + axis * length / 2)
    out = []
    for k in keys:
        if not _bb_overlap(cyl.bounds, wm[k].bounds):
            continue
        try:
            vol, bb = _inter(cyl, wm[k])
        except Exception:  # noqa
            continue
        if vol > 0.5:
            out.append((k[0] + (f"[{k[1]}]" if True else ""), vol))
    return out


def tool_specs():
    """(이름, 위치 목록, 축, 반경, 길이, 조임 시점 단위 tag(또는 tags))."""
    S = []
    S.append(("P23 마스트 M3x16 (하판 아래에서 올려 조임)", [(6, 25, 51), (6, 35, 51), (6, -25, 51), (6, -35, 51)], (0, 0, -1), 3.5, 60, ["mast_R"]))
    S.append(("스테퍼 판 볼트 4개 (판 위에서)", [(-0.5, 15.5, 101), (-0.5, -15.5, 101), (30.5, 15.5, 101), (30.5, -15.5, 101)], (0, 0, 1), 3.5, 40, ["plate"]))
    S.append(("상판 기둥 볼트 M3x10 (하판 아래에서)", [(-30, 65, 51), (-30, -65, 51), (30, 65, 51), (-3, -43, 51)], (0, 0, -1), 3.5, 60, ["deck2"]))
    S.append(("브래킷 플랜지 볼트 L (하판 위 머리, 너트 포켓 선장전)", [(14, 54, 57), (14, 66, 57), (-14, 54, 57), (-14, 66, 57)], (0, 0, 1), 3.5, 40, ["motor_L"]))
    S.append(("브래킷 플랜지 볼트 R", [(14, -54, 57), (14, -66, 57), (-14, -54, 57), (-14, -66, 57)], (0, 0, 1), 3.5, 40, ["motor_R"]))
    R = 15.21
    hl = [(-R * math.sin(math.radians(a)), 75.5, 25 + R * math.cos(math.radians(a))) for a in (55, 175, 295)]
    S.append(("모터 M3x6 L (판 바깥면에서 +Y)", hl, (0, 1, 0), 3.5, 40, ["motor_L"]))
    S.append(("모터 M3x6 R", [(-x, -y, z) for x, y, z in hl], (0, -1, 0), 3.5, 40, ["motor_R"]))
    S.append(("바퀴 세트스크류 L (+X 쪽에서)", [(11, 80.5, 32.5)], (1, 0, 0), 1.5, 25, ["wheel_L"]))
    S.append(("바퀴 세트스크류 R (-X 쪽에서)", [(-11, -80.5, 32.5)], (-1, 0, 0), 1.5, 25, ["wheel_R"]))
    for nm, st, ax in (("+Y", (15, 9, 108), (0, 1, 0)), ("-Y", (15, -9, 108), (0, -1, 0)), ("+X", (24, 0, 108), (1, 0, 0)), ("-X", (6, 0, 108), (-1, 0, 0))):
        S.append((f"스크류 허브 세트스크류 {nm} 방향", [st], ax, 1.5, 40, ["screw"]))
    S.append(("칼라 세트스크류 +Y 쪽", [(15, -19.5, 108)], (0, 1, 0), 1.5, 40, ["collar"]))
    S.append(("칼라 세트스크류 -Y 쪽", [(15, -40.5, 108)], (0, -1, 0), 1.5, 40, ["collar"]))
    zf_ = F0 - 42.0
    S.append(("IR 센서 귀 M3x6 자체탭 볼트 머리 (위에서)", [(54.7, 22.7 + 18.5, zf_ - 3.3 + 1.0), (54.7, 22.7 - 18.5, zf_ - 3.3 + 1.0)], (0, 0, 1), 3.5, 40, ["ir"]))
    S.append(("넥 스위치 M2 볼트 머리 (포크 윗면 머리 자리, 위에서)", [(30.0 + 14.9 - 10.5, -6.15 + 5.0, 155.2), (30.0 + 14.9 + 10.5, -6.15 - 5.0, 155.2)], (0, 0, 1), 2.5, 30, ["neck"]))
    import lift_collar_v3 as _lc
    _g = _lc.geometry()
    _ym, _zm = (_g["y0"] + _g["y1"]) / 2, (_g["zb"] + _g["zt"]) / 2
    _hx = _g["x0"] - _lc.CLR - _lc.WALL_NEAR - 0.5
    S.append(("스위치 고정 M2 x2 (가까운 벽 -X 쪽에서, 두 벽·스위치 관통)", [(_hx, _ym - _lc.HOLE_DY / 2, _zm + _lc.HOLE_DZ / 2), (_hx, _ym + _lc.HOLE_DY / 2, _zm - _lc.HOLE_DZ / 2)], (1, 0, 0), 2.0, 40, ["collar"]))
    S.append(("스위치 배선 3가닥 (열린 -Y 끝으로, 자유 길이)", [(_g["x0"] + 5.0, _g["y0"] - 4.0, _zm)], (0, -1, 0), 3.0, 40, ["collar"]))
    S.append(("포크 볼트 M3x12 4개 (포크 위에서)", [(11, 17, 158), (11, -17, 158), (23, 17, 158), (23, -17, 158)], (0, 0, 1), 3.5, 40, ["fork"]))
    return S


def run_tools(parts, units, wm):
    idx = {u_["tag"]: i for i, u_ in enumerate(units)}
    all_keys = list(wm.keys())
    unit_of = {}
    for ui, uu in enumerate(units):
        for p, k in resolve_items(parts, uu):
            unit_of[(p.pid, k)] = ui
    res = []
    for name, pts, ax, r, ln, tags in tool_specs():
        if not any(t in idx for t in tags):
            continue
        ti = max(idx[t] for t in tags if t in idx)
        at = [k for k in all_keys if unit_of.get(k, 99) <= ti]
        row = {"name": name, "at": [], "final": [], "fl": None}
        if "세트스크류" in name or "자유 길이" in name:
            def free(keys):
                best, who = 0, ""
                for L_ in range(2, int(ln) + 1, 2):
                    bl = tool_blockers(wm, keys, pts[0], ax, r, L_)
                    if bl:
                        who = ", ".join(n for n, v in bl[:3])
                        return best, who
                    best = L_
                return best, who
            row["fl"] = (free(at), free(all_keys))
        else:
            for pt in pts:
                row["at"].append(tool_blockers(wm, at, pt, ax, r, ln))
                row["final"].append(tool_blockers(wm, all_keys, pt, ax, r, ln))
        res.append(row)
    return res


# ---- 질량 중심
def com_table(parts):
    out = []
    for f in POSES:
        dz = f - F0
        mt = 0.0
        acc = np.zeros(3)
        for p in parts:
            if p.pid == "REF_floor":
                continue
            for k, M in enumerate(pose_mats(p, dz, 0.0, spin=False)):
                pos = (M @ np.append(p.com, 1.0))[:3]
                acc += pos * p.mass
                mt += p.mass
        c = acc / mt
        g = 9.81
        a_front = g * (0 - c[0]) / c[2]
        a_rear = g * (c[0] + 75.0) / c[2]
        a_lat = g * (93.25 - abs(c[1])) / c[2]
        out.append((f, mt, c, a_front, a_rear, a_lat))
    return out


def mass_breakdown(parts):
    rows = []
    for p in parts:
        if p.pid == "REF_floor":
            continue
        rows.append((p.pid, len(p.mats), p.mass, p.mass * len(p.mats), p.ref))
    return sorted(rows, key=lambda r: -r[3])



def nut_float_test(parts):
    """P24 플로팅 너트: 8방향 +-1 mm 횡 이동 자세에서 캐리지·포크·레일(P23)과 겹침, 스크류 위상 탐색."""
    P = {p.pid: p for p in parts}
    if "P24_nut_float" not in P:
        return ["- P24_nut_float 없음: 시험 생략"]
    nut = P["P24_nut_float"]
    base = world_mesh(nut, nut.mats[0])
    others = [("캐리지 P12", world_mesh(P["P12_carriage_v2"], P["P12_carriage_v2"].mats[0])),
              ("포크 P13", world_mesh(P["P13_fork_v2"], P["P13_fork_v2"].mats[0])),
              ("레일 P23 L", world_mesh(P["P23_mast_L"], P["P23_mast_L"].mats[0])),
              ("레일 P23 R", world_mesh(P["P23_mast_R"], P["P23_mast_R"].mats[0]))]
    shifts = [(0.0, 0.0)] + [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in range(0, 360, 45)]
    rows = ["| 너트 이동 (dX, dY) mm | " + " | ".join(n for n, _ in others) + " |", "|---|" + "---|" * len(others)]
    worst = 0.0
    for dx, dy in shifts:
        sh = base.copy()
        sh.apply_translation([dx, dy, 0])
        cells = []
        for n, w in others:
            if not _bb_overlap(sh.bounds, w.bounds):
                cells.append("0")
                continue
            vol, _ = _inter(sh, w)
            worst = max(worst, vol)
            cells.append("0" if vol <= 0.5 else f"**{vol:.1f}**")
        rows.append(f"| ({dx:+.2f}, {dy:+.2f}) | " + " | ".join(cells) + " |")
    out = ["각 이동 자세에서 교집합 부피 mm³ (0.5 이하는 0 표기).", ""] + rows + [""]
    out.append(f"- 횡 유동 시험 최대 겹침: {worst:.1f} mm³ -> " + ("**수정 필요**" if worst > 0.5 else "통과(0)"))
    # 스크류 나사산 위상 탐색 (이동 0)
    sc = P["P20_leadscrew_v2"]
    best = (1e18, None)
    res = []
    for ang in range(0, 180, 10):
        M = screw_rot(math.radians(ang)) @ sc.mats[0]
        w = world_mesh(sc, M)
        vol, _ = _inter(base, w) if _bb_overlap(base.bounds, w.bounds) else (0.0, None)
        res.append((ang, vol))
        if vol < best[0]:
            best = (vol, ang)
    out.append("- 스크류 나사산 위상 탐색(0~170°, 10° 간격, 너트 이동 0): " + ", ".join(f"{a}°={v:.1f}" for a, v in res))
    out.append(f"- 최소 겹침 {best[0]:.1f} mm³ @ {best[1]}° -> " + ("통과(위상 맞춤 시 0)" if best[0] <= 0.5 else "**위상을 맞춰도 겹침 남음(나사 형상/간극 확인)**"))
    return out


def rear_hole_access(parts):
    """스테퍼 판 후방 접근 구멍 (-0.5, +-15.5): 캐리지 높이별 수직 공구 접근."""
    wm0 = origin_meshes(parts)
    lifters = [p for p in parts if p.mover == "lift"]
    out = ["| 포크 f | 공구 길이 20 | 공구 길이 40 |", "|---|---|---|"]
    first = {20: None, 40: None}
    for f in sorted(set(list(range(155, 228, 4)) + [215, 227])):
        dz = f - F0
        wm = dict(wm0)
        for p in lifters:
            for k, M in enumerate(pose_mats(p, dz, 0.0, spin=False)):
                wm[(p.pid, k)] = world_mesh(p, M)
        keys = list(wm.keys())
        cells = []
        for L in (20, 40):
            bl = []
            for y in (15.5, -15.5):
                bl += tool_blockers(wm, keys, (-0.5, y, 101.0), (0, 0, 1), 3.5, L)
            names = sorted({n.split("[")[0] for n, v in bl})
            cells.append("열림" if not bl else "막힘: " + ", ".join(names))
            if not bl and first[L] is None:
                first[L] = f
        if f in (155, 175, 195, 215, 227) or any(first[L] == f for L in (20, 40)):
            out.append(f"| {f} | {cells[0]} | {cells[1]} |")
    out.append("")
    out.append(f"- 수직 접근이 열리는 최소 f: 공구 길이 20 mm -> {first[20]}, 40 mm -> {first[40]} (원점 f=155 에서는 캐리지 뒷면 X -4~ 와 아랫면 Z 119 가 가림 여부를 위 표에서 확인).")
    return out



IR_LENS_DY = (-11.3, 10.1)
IR_LENS_R = 4.2
IR_C = (54.7, 22.7)


def lens_ray_test(parts):
    """IR 렌즈 중심 + 반경 4.2 원둘레에서 위(+Z)로 광선: 포크·캐리지·P10 등 맞음 0 이어야 함(CD 는 목표물이라 제외)."""
    meshes = {}
    for p in parts:
        if p.pid in ("REF_floor", "REF_ir", "REF_cd"):
            continue
        meshes[p.pid] = p
    out = ["| 포크 f | 광선 수 | 맞음 | 맞은 부품 |", "|---|---|---|---|"]
    for f in POSES:
        dz = f - F0
        origins = []
        for dy in IR_LENS_DY:
            cx, cy = IR_C[0], IR_C[1] + dy
            origins.append((cx, cy))
            for t in np.linspace(0, 2 * math.pi, 8, endpoint=False):
                origins.append((cx + IR_LENS_R * math.cos(t), cy + IR_LENS_R * math.sin(t)))
        z0 = f - 42.0 + 0.05
        o = np.array([[x, y, z0] for x, y in origins])
        d = np.tile([0.0, 0.0, 1.0], (len(o), 1))
        hit_names = {}
        for pid, p in meshes.items():
            for k, M in enumerate(pose_mats(p, dz, 0.0, spin=False)):
                w = world_mesh(p, M)
                if w.bounds[1][2] < z0:
                    continue
                try:
                    hit = w.ray.intersects_any(o, d)
                except Exception:  # noqa
                    hit = np.zeros(len(o), bool)
                if hit.any():
                    hit_names[pid] = hit_names.get(pid, 0) + int(hit.sum())
        n = sum(hit_names.values())
        out.append(f"| {f:.0f} | {len(o)} | {n} | " + (", ".join(f"{k}({v})" for k, v in hit_names.items()) or "-") + " |")
    return out


def column_table(parts, wm0):
    """하단 원기둥 R50 Z 0~100 + 목 Ø50 Z 100~top 의 중심 (92-e, oy) 에 대한 IR·트레이(캐리지)·포크·스위치 간극."""
    P = {p.pid: p for p in parts}
    sel = [("IR", "REF_ir"), ("트레이(캐리지)", "P12_carriage_v2"), ("포크", "P13_fork_v2"), ("스위치", "REF_neck_switch")]  # 레버는 넥에 닿는 설계라 제외
    sel = [(n, pid) for n, pid in sel if pid in P]
    pts0 = {}
    for n, pid in sel:
        w = world_mesh(P[pid], P[pid].mats[0])
        pts0[pid] = np.vstack([np.asarray(w.vertices), trimesh.sample.sample_surface(w, 20000)[0]])
    # 하체(비 승강 부품) 점
    body = []
    for p in parts:
        if p.pid == "REF_floor" or p.mover == "lift" or p.pid in ("P10_mast_upper_v2",):
            continue
        for k, M in enumerate(p.mats):
            w = wm0[(p.pid, k)]
            body.append(np.vstack([np.asarray(w.vertices), trimesh.sample.sample_surface(w, 3000)[0]]))
    body = np.vstack(body)
    body = body[body[:, 2] < 100.0]
    out = []
    for label, cases in (("UNDER_WAFER_MM = 10", ((165.0, 175.0), (190.0, 200.0))),
                         ("UNDER_WAFER_MM = 7", ((168.0, 175.0), (193.0, 200.0)))):
        for f, top in cases:
            dz = f - F0
            out += ["", f"**{label}, f = {f:.0f} (웨이퍼 행 Z {top:.0f}, 목 Z 100~{top:.0f})**", "",
                    "| e | oy | " + " | ".join(f"{n} 수직" for n, _ in sel) + " | " + " | ".join(f"{n} 목 수평" for n, _ in sel) + " | 하체-원기둥 수평 |",
                    "|---|---|" + "---|" * (2 * len(sel) + 1)]
            for e in (0, 2, 3, 5):
                for oy in (0, 8, 14):
                    cx, cy = 92.0 - e, float(oy)
                    cells = []
                    hcells = []
                    for n, pid in sel:
                        pts = pts0[pid] + np.array([0, 0, dz])
                        dxy = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
                        inside = pts[dxy <= 50.0]
                        cells.append("-" if len(inside) == 0 else f"{inside[:, 2].min() - 100.0:.1f}")
                        neck = (pts[:, 2] >= 100.0) & (pts[:, 2] <= top)
                        hcells.append(f"{dxy[neck].min() - 25.0:.1f}" if neck.any() else "-")
                    dxy_b = np.hypot(body[:, 0] - cx, body[:, 1] - cy)
                    hb = dxy_b.min() - 50.0
                    out.append(f"| {e} | {oy} | " + " | ".join(cells) + " | " + " | ".join(hcells) + f" | {hb:.1f} |")
    return out


# ---- 보고서
def write_report(out, parts, missing, pfiles, stat, skipped, env, sweeps, tools, com, extra=None):
    L = []
    L.append("# 간섭·조립성·질량중심 점검 보고 (자동 생성: build_assembly.py, 2차)\n")
    L.append("좌표 = 로봇 좌표(원점 바퀴 접지점 중점 바닥, +X 전진, +Y 좌, +Z 위), mm. placement 파일: " + ", ".join(pfiles) + "\n")
    L.append("포함 부품: " + ", ".join(sorted({p.pid for p in parts if p.pid != 'REF_floor'})) + "\n")
    if missing:
        L.append("**누락**: " + "; ".join(missing) + "\n")

    # --- 1. 정적 간섭
    L.append("\n## 1. 정적 간섭 (f = " + ", ".join(f"{f:.0f}" for f in POSES) + ")\n")
    L.append("방법: 각 자세에서 인스턴스 쌍을 AABB로 거른 뒤 불린 교집합 부피 계산, **0.5 mm³ 초과**만 기재(면 접촉 제외). 위치 = 교집합 AABB 중심, 크기 = 교집합 AABB 치수. 승강 포즈에서 캐리지·포크·IR·CD 는 +Z 이동(f-155). 스크류 회전은 무시.\n")
    fixrows, refrows, known = [], [], []
    for r in sorted(stat, key=lambda r: -r["vol"]):
        key = frozenset([r["pa"].pid, r["pb"].pid])
        if key in KNOWN:
            known.append((r, KNOWN[key]))
        elif r["pa"].ref or r["pb"].ref:
            refrows.append(r)
        else:
            fixrows.append(r)

    def fmt_pose(r):
        ps = r["poses"]
        return "전 자세" if len(ps) == len(POSES) else ",".join(f"{x:.0f}" for x in ps)

    def table(rows, extra):
        L.append("| 부품 A | 부품 B | 부피 mm³ | 위치 (X, Y, Z) | 크기 (dX, dY, dZ) | 자세 f | " + extra[0] + " |")
        L.append("|---|---|---|---|---|---|---|")
        for r in rows:
            c, sz = r["c"], r["sz"]
            L.append(f"| {r['pa'].pid}[{r['ka']}] | {r['pb'].pid}[{r['kb']}] | {r['vol']:.1f} | ({c[0]:.1f}, {c[1]:.1f}, {c[2]:.1f}) | ({sz[0]:.1f}, {sz[1]:.1f}, {sz[2]:.1f}) | {fmt_pose(r)} | {extra[1](r)} |")
        L.append("")

    L.append(f"### 1-1. 출력 부품끼리 — **수정 필요 {len(fixrows)}행**\n")
    if fixrows:
        table(fixrows, ("책임(둘 중 고칠 쪽)", lambda r: f"{r['pa'].pid} / {r['pb'].pid}"))
    else:
        L.append("없음.\n")
    L.append(f"### 1-2. 기성품 대역 포함 {len(refrows)}행 (대역 치수·위치 가정이 맞으면 출력 부품 수정 필요)\n")
    if refrows:
        table(refrows, ("고칠 출력 부품", lambda r: (r["pb"].pid if r["pa"].ref else r["pa"].pid) if not (r["pa"].ref and r["pb"].ref) else "(대역끼리: 위치 가정)"))
    else:
        L.append("없음.\n")
    if known:
        L.append("### 1-3. 의도된 간섭\n")
        table([k[0] for k in known], ("비고", lambda r: KNOWN[frozenset([r['pa'].pid, r['pb'].pid])]))
    if skipped:
        L.append("### 검사 못 한 쌍\n")
        L += [f"- {x}" for x in skipped]
        L.append("")

    # --- 2. 출발 크기
    L.append("\n## 2. 출발 크기 규정 (전 부품 합집합 AABB; 바닥판 제외)\n")
    L.append("규정: X −93~157 (250), Y 폭 210, Z ≤ 245.\n")
    L.append("| 자세 f | X 범위 | 길이 | Y 범위 | 폭 | Z 범위 | 높이 | 판정 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for f, lo, hi in env:
        ok = lo[0] >= -93 - 1e-6 and hi[0] <= 157 + 1e-6 and (hi[1] - lo[1]) <= 210 + 1e-6 and hi[2] <= 245 + 1e-6
        L.append(f"| {f:.0f} | {lo[0]:.1f} ~ {hi[0]:.1f} | {hi[0]-lo[0]:.1f} | {lo[1]:.1f} ~ {hi[1]:.1f} | {hi[1]-lo[1]:.1f} | {lo[2]:.1f} ~ {hi[2]:.1f} | {hi[2]-lo[2]:.1f} | {'통과' if ok else '**초과**'} |")
    L.append("")

    # --- 3. 조립 순서
    L.append("\n## 3. 조립 순서 sweep (각 단위를 들어오는 방향에서 최대 dmax 까지 끌어당기며 이미 설치된 부품과 겹침 검사)\n")
    L.append("고정된 최종 위치에서 이미 겹치는 쌍은 제외(1장에서 보고). 스크류 나사 맞물림(회전 삽입)은 캐리지 sweep 에서 스크류를 제외하고 별도 판단. u = 단위가 들어오는 쪽(최종 위치에서 +u 로 떨어진 곳에서 시작).\n")
    L.append("| 단계 | 단위 | 들어오는 방향 u | dmax | 결과 |")
    L.append("|---|---|---|---|---|")
    blocked_units = []
    for uu, found in sweeps:
        if not found:
            L.append(f"| {uu['step']} | {uu['name']} | {uu['u']} | {uu['dmax']} | 통과 |")
        else:
            blocked_units.append((uu, found))
            items = "; ".join(f"d={d:.0f} mm 에서 {mk[0]}[{mk[1]}] x {ik[0]}[{ik[1]}] {v:.0f} mm³ @({c[0]:.0f},{c[1]:.0f},{c[2]:.0f})" for (mk, ik), (d, v, c) in list(found.items())[:4])
            more = f" (+{len(found)-4}건)" if len(found) > 4 else ""
            L.append(f"| {uu['step']} | {uu['name']} | {uu['u']} | {uu['dmax']} | **막힘**: {items}{more} |")
    L.append("")

    # --- 4. 공구 접근
    L.append("\n## 4. 볼트·세트스크류 공구 접근 (육각렌치 원기둥: 볼트 Ø7 길이 40~60, 세트스크류는 Ø3 육각키로 자유 길이(최대 25~40 mm) 측정)\n")
    L.append("'조임 시점' = 그 단위를 설치한 직후까지의 부품만 있을 때, '완성 후' = 전 부품이 있을 때. 막히면 막는 부품 표시(정비 시 분해 필요).\n")
    L.append("| 항목 | 조임 시점 | 완성 후(정비) |")
    L.append("|---|---|---|")

    def summ(lst):
        flat = {}
        for bl in lst:
            for n, v in bl:
                flat[n] = max(flat.get(n, 0), v)
        if not flat:
            return "접근 가능"
        nblk = sum(1 for bl in lst if bl)
        return f"{nblk}/{len(lst)}곳 막힘: " + ", ".join(f"{n}({v:.0f})" for n, v in sorted(flat.items(), key=lambda x: -x[1])[:4])

    def fls(t, full):
        n, who = t
        return f"자유 길이 {n} mm 이상" + ("" if n >= full else f" (이후 {who} 에 막힘)") if n >= 0 else ""

    for r in tools:
        if r["fl"]:
            L.append(f"| {r['name']} (자유 길이 측정) | {fls(r['fl'][0], 25)} | {fls(r['fl'][1], 25)} |")
        else:
            L.append(f"| {r['name']} | {summ(r['at'])} | {summ(r['final'])} |")
    L.append("")

    # --- 5. 질량 중심
    L.append("\n## 5. 질량 중심과 전복 감속도\n")
    L.append("질량: 출력 부품 = 부피 x 1.27 g/cm³ x 0.4(충전, TPU 포함 동일 가정), 기성품 = DC모터 150 g x2, 스테퍼 280, Mega+쉴드 90, L298 40, 배터리 200 x2, DRV 5, HM-10 5, IR 10, 캐스터 40, 라인센서 15 (지정값), **가정**: 만능기판 5, 마이크로 스위치 3, CD 15. 배선·볼트·너트 질량은 미포함.\n")
    L.append("전복 지지점: 바퀴 접지선 X=0(앞쪽 전복 축), 캐스터 X=−75(뒤쪽), 바퀴 접지 Y ±93.25. 급제동(앞 전복) 한계 감속도 a = g·(0 − X_com)/Z_com (X_com > 0 이면 정적으로 앞으로 쏠림), 급가속(뒤 전복) a = g·(X_com + 75)/Z_com, 횡 a = g·(93.25 − |Y_com|)/Z_com.\n")
    L.append("| 포크 f | 총질량 g | COM X | COM Y | COM Z | 급제동 한계 m/s² (g) | 급가속 한계 m/s² | 횡 한계 m/s² |")
    L.append("|---|---|---|---|---|---|---|---|")
    for f, mt, c, af, ar, al in com:
        afs = "**정적 전복(X_com>0)**" if af <= 0 else f"{af:.2f} ({af/9.81:.2f} g)"
        L.append(f"| {f:.0f} | {mt:.0f} | {c[0]:.1f} | {c[1]:.1f} | {c[2]:.1f} | {afs} | {ar:.2f} | {al:.2f} |")
    L.append("")
    L.append("### 질량 상위 부품\n")
    L.append("| 부품 | 수량 | 개당 g | 합계 g |")
    L.append("|---|---|---|---|")
    for pid, n, m1, mt, ref in mass_breakdown(parts)[:14]:
        L.append(f"| {pid}{' (대역)' if ref else ''} | {n} | {m1:.1f} | {mt:.1f} |")
    L.append("")
    L += (extra or [])
    L.append("\n## 6. 점검에서 발견한 조립 제약 (설계 조치 또는 절차 반영 필요)\n")
    L.append("1. **모터는 브래킷에 먼저 달고 서브어셈블리로 부착**: 두 브래킷 판 사이 간격 141 mm 에 모터 2개(길이 69.5 x 2 = 139)가 들어가므로 브래킷을 하판에 먼저 달면 모터를 끼울 수 없다.")
    L.append("2. **모터 서브어셈블리를 라인 헤드·행어보다 먼저**: 반대 순서면 모터가 아래에서 올라올 때 d=2 mm 에서 헤드와 68 mm³, PCB·행어와 각각 1 mm³ 겹쳐 막힌다(헤드·행어는 앞(+X)에서 밀어 넣음).")
    L.append("3. **스테퍼 판 볼트**: 앞쪽 2개(30.5, ±15.5)는 상판 설치 후 캐리지·상판이 가려 접근 불가 -> 상판을 올리기 전에 4개 모두 조인다. 뒤쪽 2개(−0.5, ±15.5)는 P02 의 Ø8 접근 구멍으로 완성 후에도 재조임 가능(표 4장 '스테퍼 판 볼트'의 '완성 후' 열에서 막힌 곳 수 확인).")
    L.append("4. **마스트 M3x16 4개·상판 기둥 (−3, −43) 볼트는 모터가 달리기 전에 조여야 함**(모터 몸통이 바로 아래, 교집합 1224/1285 mm³). 정비 시 모터 분리.")
    L.append("5. **배터리는 크래들에 수평(뒤→앞)으로만 삽입**: 상판 후방 보강 리브(Z 97~100, Y ±65)가 있어 위에서 내리면 d=25 mm 근처에서 상판과 952 mm³ 겹쳐 막힌다.")
    L.append("6. **바퀴 세트스크류**: 구멍을 z'=24.5(림 끝에서 1.5 mm 안쪽)로 옮긴 P16 v2 기준 접근 길이는 4장 표 참조.")
    L.append("7. **스크류 허브 세트스크류**: +X 방향만 자유(40 mm 이상). −X 14 mm(HM-10), +Y 16 mm(마스트 L), −Y 10 mm(칼라). 허브 고정은 +X 와 +Y 로.")
    L.append("8. 캐리지는 레일 위에서 내려 **스크류를 돌려** 나사 맞물림(직선 sweep 은 스크류 제외, 레일·상판·칼라와는 막힘 없음). 포크는 루트 판 레일 구멍으로 레일 위에서 내려 캐리지에 얹힘(막힘 없음). 칼라는 P10 설치 전에 레일 위에서 내려 Z 104~112 에 둔다(막힘 없음).")
    L.append("\n## 7. 가정/주의\n")
    L.append("- 승강부 placement 는 모두 원점 자세(f=155) 기준. 승강 시 캐리지·포크·IR·CD 가 +Z, 스크류는 제자리 회전(정적 검사에서는 무시).")
    L.append("- 캐스터는 Z 0~29, 스페이서 Z 29~52. Mega/L298/DRV/HM-10/만능기판 높이는 가정(Mega Z 107.8~130, L298 107.8~136.8, DRV 107.8~117, HM-10 103~109, 만능기판 107.8~112).")
    L.append("- 마이크로 스위치 GSM-V1621A2 대역: 본체 29.4x17.7x10.3(두께 가정), lift_fork.py 상수(SW_X_REAR 24.5, SW_Y -21, LEVER_OVER 10.3, 눌린 레버 Z 117.3~119). 넥 스위치는 포크 밑에 매달림(본체 Z 139.7~150, 정지 레버 끝 Z 154, 접점 X 64.8, 레버 끝 X 70.1).")
    L.append("- IR GP2Y0A21YK0F 대역: 중심 (54.7, 22.7), 렌즈면 f-42, 본체 13x29.5x18.9(렌즈 케이스 포함), 귀 44.5 x 6 x 1.2. 스테퍼 축 Z 96~118(D플랫 15 mm 생략). 모터 대역 Y 1.2~70.5(길이 69.3): 두 모터 사이 간극 141 - 2x69.3 = 2.4 mm.")
    (out / "interference.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("보고 ->", out / "interference.md")
    return fixrows, refrows, blocked_units


# ------------------------------------------------------------------ 뷰어
def b64(arr):
    return base64.b64encode(np.ascontiguousarray(arr).tobytes()).decode()


def write_viewer(parts, out):
    data = []
    total = 0
    for p in parts:
        m = p.mesh.copy()
        m.merge_vertices()
        v = np.asarray(m.vertices, np.float32)
        f = np.asarray(m.faces, np.uint32)
        total += v.nbytes + f.nbytes
        data.append({
            "id": p.pid, "label": p.label, "group": p.group, "step": p.step, "color": p.color,
            "ex": list(p.ex), "mover": p.mover, "ref": p.ref, "opacity": p.opacity,
            "mats": [[round(float(x), 5) for x in M.ravel()] for M in p.mats], "sign": p.sign,
            "v": b64(v), "i": b64(f),
        })
    html = VIEWER_HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    import lift_collar_v3 as _lc2
    _g2 = _lc2.geometry()
    html = html.replace("__LEV__", json.dumps([round(_g2["y0"] + 3.0, 3), round(_g2["zt"], 3), round(_g2["tip_y"] - (_g2["y0"] + 3.0), 3)]))
    html = html.replace("__F0__", str(F0)).replace("__FSOFT__", str(F_SOFT)).replace("__FMECH__", str(F_MECH))
    (out / "viewer.html").write_text(html, encoding="utf-8")
    sz = (out / "viewer.html").stat().st_size / 1e6
    print(f"뷰어 -> {out / 'viewer.html'} ({sz:.2f} MB, 메시 원본 {total/1e6:.2f} MB)")
    assert sz < 16, "viewer.html 이 16MB 초과 - 메시 간소화 필요"


VIEWER_HTML = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Robot Assembly Viewer</title>
<style>
:root{--bg:#f4f6f9;--panel:#fff;--fg:#1d232b;--mut:#5e6b7a;--bd:#d5dbe3;--ac:#e8590c}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14181d;--panel:#1d232b;--fg:#e8edf2;--mut:#9aa7b5;--bd:#333d49}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,"Malgun Gothic",sans-serif;display:flex;height:100vh;overflow:hidden}
#side{width:320px;max-width:42vw;background:var(--panel);border-right:1px solid var(--bd);overflow:auto;padding:12px 16px}
#view{flex:1;position:relative;min-width:0}canvas{display:block;width:100%;height:100%}
h1{font-size:16px;margin:0 0 8px}h2{font-size:13px;margin:14px 0 4px;color:var(--mut);text-transform:none}
label.sl{display:block;margin:8px 0 2px}.row{display:flex;justify-content:space-between;gap:8px}
input[type=range]{width:100%}button{background:var(--panel);color:var(--fg);border:1px solid var(--bd);border-radius:6px;padding:4px 10px;cursor:pointer}
.part{display:flex;align-items:center;gap:6px;padding:1px 0}.sw{width:12px;height:12px;border-radius:3px;border:1px solid var(--bd);flex:none}
.part span.n{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#hint{position:absolute;left:12px;bottom:8px;color:var(--mut);font-size:12px;pointer-events:none}
@media (max-width:700px){body{flex-direction:column}#side{width:100%;max-width:none;height:42vh;border-right:0;border-bottom:1px solid var(--bd)}}
</style></head><body>
<div id="side">
<h1>Wafer robot assembly</h1>
<label class="sl row"><span>분해 (explode)</span><b id="vE">0%</b></label><input id="sE" type="range" min="0" max="100" value="0">
<label class="sl row"><span>승강 포크 윗면 f (mm)</span><b id="vL">__F0__</b></label><input id="sL" type="range" min="__F0__" max="__FSOFT__" step="0.5" value="__F0__">
<div class="row" style="margin-top:6px"><button id="bP">승강 재생</button><button id="bR">시점 초기화</button><button id="bA">전체 켜기</button><button id="bN">전체 끄기</button></div>
<label class="sl row"><span>조립 단계 (이하 표시)</span><b id="vS">전체</b></label><input id="sS" type="range" min="0" max="16" value="16">
<h2>부품 (체크로 켜기/끄기)</h2><div id="list"></div>
</div>
<div id="view"><div id="hint">드래그: 회전 / 휠: 확대 / 우클릭 드래그: 이동</div></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
const DATA=__DATA__;
const F0=__F0__, LEAD=8, AX=15, LEV=__LEV__;
function dec(s,T){const b=atob(s),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return new T(u.buffer);}
const view=document.getElementById('view');
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));view.appendChild(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(getComputedStyle(document.body).backgroundColor);
const camera=new THREE.PerspectiveCamera(35,1,1,5000);camera.up.set(0,0,1);
scene.add(new THREE.HemisphereLight(0xffffff,0x667788,0.75));
const dl=new THREE.DirectionalLight(0xffffff,0.8);dl.position.set(300,200,500);scene.add(dl);
const dl2=new THREE.DirectionalLight(0xffffff,0.35);dl2.position.set(-300,-300,200);scene.add(dl2);
const parts=[];const list=document.getElementById('list');
let maxStep=0;
DATA.forEach((d,pi)=>{
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.BufferAttribute(dec(d.v,Float32Array),3));
  g.setIndex(new THREE.BufferAttribute(dec(d.i,Uint32Array),1));
  const ng=g.toNonIndexed();ng.computeVertexNormals();
  const mat=new THREE.MeshStandardMaterial({color:d.color,roughness:0.65,metalness:0.1,transparent:d.opacity<1,opacity:d.opacity,side:THREE.DoubleSide});
  const inst=d.mats.map((m,k)=>{const me=new THREE.Mesh(ng,mat);me.matrixAutoUpdate=false;
    const base=new THREE.Matrix4().set(...m);scene.add(me);return {me,base,sign:d.sign[k]};});
  const row=document.createElement('label');row.className='part';
  row.innerHTML='<input type="checkbox" checked><span class="sw" style="background:'+d.color+'"></span><span class="n" title="'+d.label+'">'+(d.step?d.step+'. ':'')+d.label+'</span>';
  list.appendChild(row);
  const p={d,inst,on:true,cb:row.querySelector('input')};
  p.cb.onchange=()=>{p.on=p.cb.checked;upd();};
  parts.push(p);maxStep=Math.max(maxStep,d.step);
});
const sS=document.getElementById('sS');sS.max=maxStep;sS.value=maxStep;
const sE=document.getElementById('sE'),sL=document.getElementById('sL');
function upd(){
  const e=sE.value/100,f=parseFloat(sL.value),dz=f-F0,st=parseInt(sS.value);
  document.getElementById('vE').textContent=Math.round(e*100)+'%';
  document.getElementById('vL').textContent=f.toFixed(1);
  document.getElementById('vS').textContent=st>=maxStep?'전체':st;
  parts.forEach(p=>{
    const vis=p.on&&p.d.step<=st&&!(p.d.id==='REF_floor'&&e>0.01);
    p.inst.forEach(o=>{
      o.me.visible=vis;
      const m=new THREE.Matrix4();
      if(p.d.mover==='lift')m.multiply(new THREE.Matrix4().makeTranslation(0,0,dz));
      if(p.d.mover==='lever'){const zc=119+dz,h=Math.min(20,Math.max(16,zc-103)),tipz=103+h,th=Math.atan2(tipz-LEV[1],LEV[2]);
        m.multiply(new THREE.Matrix4().makeTranslation(0,LEV[0],LEV[1])).multiply(new THREE.Matrix4().makeRotationX(th)).multiply(new THREE.Matrix4().makeTranslation(0,-LEV[0],-LEV[1]));}
      if(p.d.mover==='screw'){const a=dz/LEAD*2*Math.PI;
        m.multiply(new THREE.Matrix4().makeTranslation(AX,0,0)).multiply(new THREE.Matrix4().makeRotationZ(a)).multiply(new THREE.Matrix4().makeTranslation(-AX,0,0));}
      m.multiply(o.base);
      const t=new THREE.Matrix4().makeTranslation(p.d.ex[0]*e,p.d.ex[1]*o.sign*e,p.d.ex[2]*e);
      o.me.matrix.copy(t.multiply(m));o.me.matrixWorldNeedsUpdate=true;
    });
  });
}
sE.oninput=sL.oninput=sS.oninput=upd;
document.getElementById('bA').onclick=()=>{parts.forEach(p=>{p.on=true;p.cb.checked=true});upd();};
document.getElementById('bN').onclick=()=>{parts.forEach(p=>{p.on=false;p.cb.checked=false});upd();};
let playing=false,dirn=1;
document.getElementById('bP').onclick=e=>{playing=!playing;e.target.textContent=playing?'정지':'승강 재생';};
// 간단한 궤도 카메라 (Z-up)
let az=0.9,el=0.5,dist=700,tgt=new THREE.Vector3(10,0,110);
function cam(){camera.position.set(tgt.x+dist*Math.cos(el)*Math.cos(az),tgt.y+dist*Math.cos(el)*Math.sin(az),tgt.z+dist*Math.sin(el));camera.lookAt(tgt);}
document.getElementById('bR').onclick=()=>{az=0.9;el=0.5;dist=700;tgt.set(10,0,110);cam();};
let drag=null;const cv=renderer.domElement;
cv.addEventListener('contextmenu',e=>e.preventDefault());
cv.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,b:e.button};cv.setPointerCapture(e.pointerId);});
cv.addEventListener('pointerup',()=>drag=null);
cv.addEventListener('pointermove',e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.x=e.clientX;drag.y=e.clientY;
  if(drag.b===2||e.shiftKey){const s=dist*0.0015;const r=new THREE.Vector3().setFromMatrixColumn(camera.matrix,0),u=new THREE.Vector3().setFromMatrixColumn(camera.matrix,1);
    tgt.addScaledVector(r,-dx*s).addScaledVector(u,dy*s);}
  else{az-=dx*0.006;el=Math.max(-1.5,Math.min(1.5,el+dy*0.006));}cam();});
cv.addEventListener('wheel',e=>{e.preventDefault();dist=Math.max(80,Math.min(3000,dist*Math.exp(e.deltaY*0.001)));cam();},{passive:false});
function resize(){const w=view.clientWidth,h=view.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}
addEventListener('resize',resize);resize();cam();upd();
(function loop(){requestAnimationFrame(loop);
  if(playing){let f=parseFloat(sL.value)+dirn*0.5;if(f>=__FSOFT__){f=__FSOFT__;dirn=-1}if(f<=__F0__){f=__F0__;dirn=1}sL.value=f;upd();}
  renderer.render(scene,camera);})();
</script></body></html>
"""


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--placement-dir", default=str(PRINT))
    ap.add_argument("--out-dir", default=str(HERE))
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--no-interference", action="store_true")
    ap.add_argument("--no-viewer", action="store_true")
    ap.add_argument("--no-anim", action="store_true")
    ap.add_argument("--no-build-anim", action="store_true")
    ap.add_argument("--frames", type=int, default=60)
    ap.add_argument("--only-build-anim", action="store_true")
    a = ap.parse_args()
    global ONLY_BUILD
    ONLY_BUILD = a.only_build_anim
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    parts, missing, pfiles = build_parts(a.placement_dir)
    units = get_units(parts)
    print("placement 파일:", pfiles or "없음")
    print("포함 부품:", len(parts), "개 /", sum(len(p.mats) for p in parts), "인스턴스")
    for p in parts:
        print(f"  step{p.step:2d} {p.pid:24s} x{len(p.mats)} {p.group} {p.mass:.1f}g")
    print("누락:", missing or "없음")

    if not a.no_interference:
        stat, sk = interference(parts)
        env = envelope(parts)
        wm = origin_meshes(parts)
        print("sweep ...")
        sweeps = run_sweeps(parts, units, wm)
        tools = run_tools(parts, units, wm)
        com = com_table(parts)
        extra = ["", "## 5-2. P24 플로팅 너트 횡 유동 시험 (8방향 +-1 mm)", ""] + nut_float_test(parts)
        extra += ["", "## 5-3. 스테퍼 판 후방 접근 구멍 (-0.5, +-15.5) 수직 접근 (상판 Ø8 구멍 통과, 캐리지 높이별)", ""] + rear_hole_access(parts) + [""]
        extra += ["", "## 5-4. IR 렌즈 광선 시험 (렌즈 중심 + 반경 4.2 원둘레 9점 x 2렌즈, 위로)", ""] + lens_ray_test(parts) + [""]
        extra += ["", "## 5-5. 기둥 간극 표 (하단 원기둥 R50 Z 0~100 + 목 Ø50, 중심 X = 92 - e, Y = oy; 단위 mm, 음수 = 간섭)", "",
                  "수직 = 해당 부품 중 원기둥(R50) 영역 위에 있는 점의 최저 Z - 100. 수평 = Z 100~목 윗면 사이의 점과 목 축 사이 거리 - 25. 하체-원기둥 수평 = 로봇 하체(Z<100, 승강부 제외)와 원기둥 R50 사이 거리.", ""] + column_table(parts, wm) + [""]
        write_report(out, parts, missing, pfiles, stat, sk, env, sweeps, tools, com, extra)
    if not a.no_viewer:
        write_viewer(parts, out)
    if not a.no_render:
        try:
            render_all(parts, out, a.frames, want_anim=not a.no_anim, units=units, want_build=not a.no_build_anim)
        except ImportError:
            print("[경고] pyvista 없음: pip install pyvista")
            raise


if __name__ == "__main__":
    sys.exit(main())
