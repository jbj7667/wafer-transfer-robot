"""승강부 리드스크류 P20 + 시험 조각 P20t / P21t 생성 및 검증.

실행: python public/cad/print/lift_screw.py   (워크트리 루트에서)
출력 자세: 허브가 베드(print z = 로봇 Z - 98). 나사 축은 (15, 0).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).parent))
from v12_parts import cyl, union, diff, save, OUT  # noqa: E402
from lift_thread import thread_rod, nut_hole_cutter, MAJOR, MINOR, LEAD  # noqa: E402

# ---- 상수 (실측 후 수정 가능)
SHAFT_LEN = 22.0          # 실측: 스테퍼 축이 모터 윗면(Z 96)에서 올라온 길이. D플랫 길이 15 (축 끝 기준)
BORE_D = 5.1              # 허브 축 구멍 지름
BORE_DEPTH = SHAFT_LEN + 1.0   # 25 -> Z 98~123 (축 끝 위로 1 mm 여유)
HUB_D, HUB_MID_D = 16.0, 11.0     # Z 98~103 Ø16 / Z 103~114 Ø11
HUB_LOW_H, HUB_MID_TOP, HUB_TOP = 5.0, 16.0, 20.0   # print z (Z 103 / 114 / 118)
Z_BASE = 98.0
THREAD_Z0, THREAD_Z1 = 118.0 - Z_BASE, 228.0 - Z_BASE   # print z 20~130
JOURNAL_D, JOURNAL_Z1 = 6.0, 240.0 - Z_BASE
SET_Z = 108.0 - Z_BASE    # 세트스크류 높이 (print z 10)
CX = 15.0
SCREW_FLANK_TRIM = 0.0    # v1 값. v2 는 FLANK_TRIM_V2 사용 (나사산 플랭크 법선 방향 깎임 mm, 편측)
FLANK_TRIM_V2 = 0.3       # v2: 너트와 닿는 플랭크를 편측 0.3 깎음 -> 나사산 이 두께 0.62 mm 감소, 마루/골 반경 불변


def make_screw(trim=SCREW_FLANK_TRIM):
    # 허브: Z 98~103 Ø16, Z 103~114 Ø11, Z 114~118 45도 근처 원뿔(Ø11 -> 골경 Ø8.4). 전체 Z <= 118.
    r_lo, r_mid, r_core = HUB_D / 2, HUB_MID_D / 2, MINOR / 2
    prof = [(0, 0), (r_lo, 0), (r_lo, HUB_LOW_H), (r_mid, HUB_LOW_H), (r_mid, HUB_MID_TOP),
            (r_core, HUB_TOP), (0, HUB_TOP)]
    hub = trimesh.creation.revolve(np.array(prof), sections=96)
    thread = thread_rod(HUB_MID_TOP, THREAD_Z1, lead=8.0, starts=2, flank_trim=trim)
    journal = cyl(JOURNAL_D / 2, JOURNAL_Z1 - THREAD_Z1 + 1.0, (0, 0, (THREAD_Z1 - 1.0 + JOURNAL_Z1) / 2), "z", 48)
    body = union([hub, thread, journal])
    cuts = [cyl(BORE_D / 2, BORE_DEPTH + 1, (0, 0, (BORE_DEPTH - 1) / 2), "z", 48)]
    for ang in (0.0, 90.0):
        c = cyl(1.4, 9.0, (0, 0, SET_Z), "x", 24)
        c.apply_translation([5.5, 0, 0])
        c.apply_transform(trimesh.transformations.rotation_matrix(math.radians(ang), [0, 0, 1]))
        cuts.append(c)
    body = diff(body, cuts)
    body.apply_translation([CX, 0, 0])
    return body


def make_tests(trim=SCREW_FLANK_TRIM):
    # 나사 시험 조각: 손잡이 Ø10 x10 + 나사 30 + 손잡이 Ø10 x10 (z 0~50)
    thr = thread_rod(10, 40, lead=8.0, starts=2, flank_trim=trim)
    h1 = cyl(4.0, 10.5, (0, 0, 10.5 / 2), "z", 64)   # Ø8.0 (골경 8.4보다 작아야 너트가 넘어간다. 이전 Ø9.8은 너트 구멍 Ø9.0보다 커서 입구부터 막힘 — 사용자 시험 2026-11-02)
    h2 = cyl(4.0, 10.5, (0, 0, 50 - 10.5 / 2), "z", 64)
    st = union([thr, h1, h2])
    nut_body = trimesh.creation.cylinder(radius=20 / math.sqrt(3), height=12, sections=6)
    nut_body.apply_translation([0, 0, 6])
    cutter = nut_hole_cutter(0, 12, 0, 0, clearance=0.3)
    nut = diff(nut_body, [cutter])
    return st, nut


def measure(screw_test, nut):
    res = {}
    # 외경/골경: z 슬라이스를 여러 높이에서 -> 반경 범위
    rmax, rmin = [], []
    for z in np.linspace(15, 35, 41):
        s = screw_test.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        v = s.vertices[:, :2]
        r = np.hypot(v[:, 0], v[:, 1])
        rmax.append(r.max())
        rmin.append(r.min())
    res["외경 mm (슬라이스 최대, 목표 12)"] = 2 * max(rmax)
    res["골경 mm (슬라이스 최소, 목표 8.4)"] = 2 * min(rmin)
    # 피치: y=0 평면 단면에서 x>0 마루 z 간격
    s = screw_test.section(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])
    v = s.vertices
    crest = np.sort(v[(v[:, 0] > 5.95) & (v[:, 2] > 12) & (v[:, 2] < 38)][:, 2])
    groups = np.split(crest, np.where(np.diff(crest) > 1.0)[0] + 1)
    centers = np.array([g.mean() for g in groups])
    res["피치 mm (마루 중심 간격, 목표 4)"] = np.diff(centers).tolist()
    # 리드: 각도 0도 / 90도 단면의 마루 위상 차 (리드 8 -> 2 mm, 리드 4 -> 1 mm; 피치 4 로 접힘)
    def crest_phase(normal, axis_col, sign):
        sc = screw_test.section(plane_origin=[0, 0, 0], plane_normal=normal)
        vv = sc.vertices
        sel = vv[(sign * vv[:, axis_col] > 5.95) & (vv[:, 2] > 12) & (vv[:, 2] < 38)][:, 2]
        g = np.split(np.sort(sel), np.where(np.diff(np.sort(sel)) > 2.0)[0] + 1)
        return g[2].mean() % 4.0  # 첫 마루 중심 (zrange 동일)
    ph0, ph90 = crest_phase([0, 1, 0], 0, 1), crest_phase([1, 0, 0], 1, 1)
    res["마루 위상차 0->90도 mm (리드8 기대 2.0, 리드4면 1.0)"] = (ph90 - ph0) % 4.0
    # 겹침: 나사(시험 조각의 나사부 z 10~40)를 너트(z 0~12)에 넣고 위상별 교차 부피
    ov = []
    for dz in np.arange(0.0, 4.0, 0.2):  # 회전=축이동이므로 위상 일치 자세 근처에서만 0
        sc = screw_test.copy()
        sc.apply_translation([0, 0, -22 + dz])        # 나사부 중간(z 22~34)이 너트 z 0~12 에 오도록
        inter = trimesh.boolean.intersection([sc, nut], engine="manifold")
        ov.append(float(inter.volume) if len(inter.vertices) else 0.0)
    res["겹침 부피 mm3 (dz=0..3.8 step 0.2; 0인 구간 = 축방향 유격)"] = [round(x, 3) for x in ov]
    return res


def main():
    screw = make_screw()
    r = save(screw, OUT / "P20_leadscrew.stl")
    st, nut = make_tests()
    r1 = save(st, OUT / "P20t_screw_test.stl")
    r2 = save(nut, OUT / "P21t_nut_test.stl")
    print("--- 저장/재로드 검증")
    for n, m in (("P20_leadscrew", r), ("P20t_screw_test", r1), ("P21t_nut_test", r2)):
        print(f"{n}: watertight={m.is_watertight} volume={m.is_volume} bbox={m.bounds.round(2).tolist()} "
              f"vol={m.volume / 1000:.2f} cm3 (PETG ~{m.volume / 1000 * 1.27:.1f} g 100%)")
    print("--- 측정 (시험 조각, 재로드본)")
    for k, v in measure(trimesh.load(OUT / "P20t_screw_test.stl"), trimesh.load(OUT / "P21t_nut_test.stl")).items():
        print(k, ":", v)
    # P20 본체 측정
    m20 = trimesh.load(OUT / "P20_leadscrew.stl")
    rr = []
    for z in np.linspace(40, 120, 81):
        s = m20.section(plane_origin=[15, 0, z], plane_normal=[0, 0, 1])
        v = s.vertices[:, :2] - [15, 0]
        rr.append(np.hypot(v[:, 0], v[:, 1]))
    print("P20 나사부 외경 %.3f 골경 %.3f" % (2 * max(x.max() for x in rr), 2 * min(x.min() for x in rr)))
    print(f"허브 구멍 깊이 {BORE_DEPTH} (Z 98~{98 + BORE_DEPTH}), 골경 코어 벽 두께 {(MINOR - BORE_D) / 2:.2f} mm")

    mats = {}
    for n, tz in (("P20_leadscrew", Z_BASE), ("P20t_screw_test", 0.0), ("P21t_nut_test", 0.0)):
        M = np.eye(4)
        M[2, 3] = tz
        mats[n] = {"matrix_row_major": M.flatten().tolist(),
                   "note": "출력 자세 -> 로봇 좌표. P20: print z = 로봇 Z - 98, 나사 축 (15,0)" if tz else "시험 조각(조립 없음), 항등"}
    (OUT / "placement_screw.json").write_text(json.dumps(mats, indent=2, ensure_ascii=False), encoding="utf-8")

    print("""
--- 출력 설명
소재 PETG, 노즐 0.4, 층 높이 0.16~0.2 (나사산 품질: 0.16 권장), 벽 최소 3줄(루프 3), 채움 40% 이상 (축 구멍 둘레는 벽으로 충분).
P20 리드스크류: 허브를 아래로 세워 출력, 브림 5~8 mm 권장 (직경 12 막대가 길어 흔들림 -> 브림 + 냉각 팬 100%).
  서포트 없음 (허브 위는 45도 원뿔, 나사산 아래 플랭크는 15도 오버행이라 거칠어질 수 있음: 시험 조각으로 확인).
  리드 8 (2줄, 피치 4): 모터 1회전당 8 mm. 세트스크류는 머리 없는 무두볼트(M3 grub screw)를 쓴다(Z 108 구멍, 축에 눌림).
  세트스크류(Z 108)는 축의 D플랫 면(축 끝 Z 118 기준 Z 103~118)에 닿도록 방향을 맞춰 조일 것.
  세트스크류 구멍 Ø2.8 은 M3 자체탭, 허브 구멍 Ø5.1 은 필요 시 5.0 드릴로 다듬는다.
시험 순서: 1) P20t_screw_test + P21t_nut_test 출력, 2) 너트가 손잡이로 부드럽게 돌아가는지, 흔들림/뻑뻑함 확인,
  3) 뻑뻑하면 lift_screw.py 의 nut_hole_cutter clearance 를 0.4 로 올려 재생성, 4) 확인 후 P20 출력.
""")


def main_v2():
    """v2: 플랭크 0.3 깎은 스크류. 기존 파일은 덮어쓰지 않고 *_v2.stl 로 저장."""
    save(make_screw(FLANK_TRIM_V2), OUT / "P20_leadscrew_v2.stl")
    st, _ = make_tests(FLANK_TRIM_V2)
    save(st, OUT / "P20t_screw_test_v2.stl")


if __name__ == "__main__":
    import sys as _s
    main_v2() if "v2" in _s.argv[1:] else main()
