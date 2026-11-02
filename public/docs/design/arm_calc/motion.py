# 동작 시간, 경로 간섭, 스텝 속도, 전력. 실행: python -I motion.py (출력 motion_out.md)
# 모든 속도·가속도·전류는 가정(주석 표기). 실측 후 상수만 바꿔 재실행한다.
import math
out = []
P = out.append
S = (500.0, 240.0)
L = 205.0
A = 64.0
bases = {'5': (130, 130), '6': (870, 130), '3': (180, 305), '4': (820, 305), '1': (230, 480), '2': (770, 480)}
post_top = {'5': 175, '6': 175, '3': 200, '4': 200, '1': 200, '2': 200}


def polar(b):
    f = S[1] - b[1]
    l = S[0] - b[0]
    return math.degrees(math.atan2(l, f)), math.hypot(f, l)


def phi_of(Rcd):
    return math.degrees(math.acos((Rcd - A) / (2 * L)))


def ttrap(d, v, a):
    d = abs(d)
    if d == 0:
        return 0.0
    if d >= v * v / a:
        return d / v + v / a
    return 2 * math.sqrt(d / a)


# ---- 가정 상수 ----
W_TH, A_TH = 150.0, 450.0          # deg/s, deg/s^2 (θ 회전대)
V_R, A_R = 400.0, 2000.0           # mm/s, mm/s^2 (손목 반경 방향 이동, 비접촉 구간)
V_INS = 120.0                      # mm/s (포크 삽입)
V_Z, A_Z = 30.0, 300.0             # mm/s, mm/s^2
R_C = 200.0                        # 운반 CD 중심 반경
APP = 80.0                         # 접근 거리(삽입 길이)
T_SENSE = 0.25                     # s IR 판정
T_SETTLE = 0.15                    # s 단계 사이 정착

P("## M1. 경로 간섭 점검 (팔꿈치 가지 s=+1: 팔꿈치 방향 = theta + phi, 전 행 공통)")
phi_c = phi_of(R_C)
P(f"운반 R_C={R_C:.0f} -> phi_C={phi_c:.1f} deg, 손목 반경 {2*L*math.cos(math.radians(phi_c)):.0f} mm")
P("| 행 | theta_L | theta_R(펼침 좌표) | 운반 중 팔꿈치 방향 범위 | 팔꿈치 중심 y_min(mm) | 보스 r20 가장자리 | 링크 가장자리(14) |")
P("|---|---|---|---|---|---|---|")
for nm, bl in (('상단', '5'), ('중단', '3'), ('하단', '1')):
    thL, R = polar(bases[bl])
    thR = 360 - thL
    # 운반 구간(θ: thL -> thR, phi=phi_c) + 뻗기(phi: phi_c -> phi_pick at thR)
    ymin = 1e9
    dmin, dmax = 1e9, -1e9
    n = 400
    for i in range(n + 1):
        th = thL + (thR - thL) * i / n
        d = th + phi_c
        y = S[1] - L * math.cos(math.radians(d))
        ymin = min(ymin, y)
        dmin, dmax = min(dmin, d), max(dmax, d)
    phip = phi_of(R)
    for i in range(101):
        phi = phi_c + (phip - phi_c) * i / 100
        d = thR + phi
        ymin = min(ymin, S[1] - L * math.cos(math.radians(d)))
    P(f"| {nm} | {thL:.1f} | {thR:.1f} | {dmin:.0f}~{dmax:.0f} | {ymin:.1f} | {ymin-20:.1f} | {ymin-14:.1f} |")
P("해석: 팔꿈치 원(반경 205)의 북쪽 끝 y=35가 최악. 보스 가장자리 약 15mm, S가 북쪽으로 10mm 틀어지면 약 5mm. 자기 구역 경계(y=0) 침범 여부는 대회 판정 방식 확인필요(바닥 투영만인지).")

P("")
P("## M2. 픽 자세에서 링크 중심선과 넥(r=25)·다른 베이스 넥의 최소 거리 (링크 반폭 14 포함, 링크 높이대 z 약 125~165)")
P("| 픽 베이스 | 링크1 최소거리 | 링크2 최소거리 | 대상 | 필요(25+14=39) | 판정 |")
P("|---|---|---|---|---|---|")


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


for nm, b in bases.items():
    th, R = polar(b)
    ph = phi_of(R)
    # 월드 좌표: 방위 d(북에서 왼쪽 +) -> 벡터 (-sin d, -cos d)
    def w(r, d):
        return (S[0] - r * math.sin(math.radians(d)), S[1] - r * math.cos(math.radians(d)))
    sg = 1 if th > 0 else 1  # 모든 행 s=+1
    el = w(L, th + sg * ph)
    wr = w(R - A, th)
    best1 = (1e9, '')
    best2 = (1e9, '')
    for on, ob in bases.items():
        d1 = seg_dist(ob, S, el)
        d2 = seg_dist(ob, el, wr)
        if d1 < best1[0]:
            best1 = (d1, on)
        if d2 < best2[0]:
            best2 = (d2, on)
    tgt = f"링크1:{best1[1]}, 링크2:{best2[1]}"
    ok = 'OK' if min(best1[0], best2[0]) > 39 else '확인'
    P(f"| {nm} | {best1[0]:.0f} | {best2[0]:.0f} | {tgt} | 39 | {ok} |")
P("참고: 링크2 끝(손목)은 픽 대상 베이스에서 포크 길이 64mm 뒤에 있으므로 대상 넥과는 64-25-허브20=19mm 이상 떨어짐(자기 베이스는 위 표에서 제외되지 않음).")

P("")
P("## M3. 한 CD 사이클 시간 (가정 상수: θ 150 deg/s, 450 deg/s^2 / R 400 mm/s, 2 m/s^2 / 삽입 120 mm/s / Z 30 mm/s, 0.3 m/s^2)")
P("| 행 | θ 회전각(deg) | 접근 | 삽입 | 판정 | 승 | 후퇴 | 회전 | 뻗기 | 하강 | 빠져나옴 | 합계(s) |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|")
tot_cd = 0
cd_times = []
prev_theta = None
for nm, bl in (('상단 5->6', '5'), ('중단 3->4', '3'), ('하단 1->2', '1')):
    thL, R = polar(bases[bl])
    rot = 360 - 2 * thL
    # 접근: 이전 위치 -> θ_L (이전은 오른쪽 베이스 출구 근처 또는 접힘). 첫 행은 접힘(θ_home=48 -> θ_L) 사용
    if prev_theta is None:
        d_th = abs(thL - 48.0)
        t_R = ttrap(R - APP - A + 106, V_R, A_R) if False else ttrap(2 * L * (math.cos(math.radians(phi_of(R - APP))) - math.cos(math.radians(105))), V_R, A_R)
    else:
        d_th = prev_theta - thL if prev_theta > thL else thL - prev_theta
        t_R = ttrap(150.0, V_R, A_R)
    t_app = max(ttrap(d_th, W_TH, A_TH), t_R, ttrap(25, V_Z, A_Z)) + T_SETTLE
    t_ins = ttrap(APP, V_INS, 1000) + T_SETTLE
    t_sens = T_SENSE
    t_lift = ttrap(25, V_Z, A_Z) + T_SETTLE
    t_ret = ttrap(80, 200, 1000) + max(ttrap(R - A - (R_C - A) - 80 if False else (R - R_C) - 80, V_R, A_R), 0)
    t_rot = ttrap(rot, W_TH, A_TH)
    t_ext = ttrap(R - R_C, V_R, A_R) + T_SETTLE
    t_low = ttrap(25, V_Z, A_Z) + T_SETTLE
    t_out = ttrap(80, 200, 1000)
    t_all = t_app + t_ins + t_sens + t_lift + t_ret + t_rot + t_ext + t_low + t_out
    # 회전과 뻗기 겹침(0.5) 반영안 (보수). 겹침 시 절약량 추정
    P(f"| {nm} | {rot:.0f} | {t_app:.2f} | {t_ins:.2f} | {t_sens:.2f} | {t_lift:.2f} | {t_ret:.2f} | {t_rot:.2f} | {t_ext:.2f} | {t_low:.2f} | {t_out:.2f} | **{t_all:.2f}** |")
    cd_times.append(t_all)
    prev_theta = 360 - thL   # 다음 행은 오른쪽 출구에서 시작
    # 다음 행 접근은 θ가 작아지는 방향(오른쪽 -> 왼쪽, 후방 경유)
    prev_theta = 360 - thL
sum_cd = sum(cd_times)
P(f"3개 합 {sum_cd:.1f} s (보수: 회전·뻗기 순차). 회전 후반과 뻗기를 겹치면 CD당 약 0.4~0.6 s 절약 가능(가정).")
# 첫 행 접근의 d_th 처리 주의: 이후 행 접근은 θ가 큰 값에서 작은 값으로 이동하므로 회전각이 크다
extra = 0
P("")
P("접근 구간 상세(이전 행 오른쪽 출구 -> 다음 행 왼쪽 베이스 θ):")
thl = {k: polar(bases[k])[0] for k in ('5', '3', '1')}
P(f"상단->중단 접근 회전 {360-thl['5']-thl['3']:.0f} deg, 중단->하단 접근 회전 {360-thl['3']-thl['1']:.0f} deg")
# 위 접근 시간을 정확히 다시 계산
rows = [('5', None), ('3', '5'), ('1', '3')]
total_ops = 0
detail = []
for bl, prv in rows:
    thL, R = polar(bases[bl])
    rot = 360 - 2 * thL
    if prv is None:
        d_th = abs(thL - 48.0)
        t_R = ttrap(2 * L * (math.cos(math.radians(phi_of(R - APP))) - math.cos(math.radians(105))), V_R, A_R)
    else:
        d_th = 360 - polar(bases[prv])[0] - thL     # 오른쪽 출구(θ_R_prev) -> θ_L : 후방 경유 감소
        t_R = ttrap(150, V_R, A_R)
    t_app = max(ttrap(d_th, W_TH, A_TH), t_R, ttrap(25, V_Z, A_Z)) + T_SETTLE
    t_ins = ttrap(APP, V_INS, 1000) + T_SETTLE
    t_lift = ttrap(25, V_Z, A_Z) + T_SETTLE
    t_ret = ttrap(80, 200, 1000) + ttrap((R - R_C) - 80, V_R, A_R)
    t_rot = ttrap(rot, W_TH, A_TH)
    t_ext = ttrap(R - R_C, V_R, A_R) + T_SETTLE
    t_low = ttrap(25, V_Z, A_Z) + T_SETTLE
    t_out = ttrap(80, 200, 1000)
    t = t_app + t_ins + T_SENSE + t_lift + t_ret + t_rot + t_ext + t_low + t_out
    detail.append((bl, d_th, t_app, t))
    total_ops += t
P("| 행 | 접근 회전(deg) | 접근(s) | 사이클 합(s) |")
P("|---|---|---|---|")
for bl, d, ta, t in detail:
    P(f"| {bl} | {d:.0f} | {ta:.2f} | {t:.2f} |")
t_stow = max(ttrap(60, W_TH, A_TH), ttrap(220, V_R, A_R), ttrap(25, V_Z, A_Z)) + 0.5
t_drive_out = 4.5   # 가정: 출발 -> S (약 960 mm, 평균 0.25 m/s + 교차 감지·65mm 전진·정착)
t_spin = 1.5        # 가정: S에서 180도 제자리 회전
t_drive_back = 5.3  # 가정: S -> 출발구역 정지
mission = t_drive_out + total_ops + t_stow + t_spin + t_drive_back
P("")
P("## M4. 총 임무 시간 (예선 기준, 위치가 왼쪽인 경우)")
P("| 구간 | s | 비고 |")
P("|---|---|---|")
P(f"| 출발 -> S 정지 | {t_drive_out:.1f} | 가정: 960mm, 평균 0.25 m/s, 교차 감지·65mm 전진 포함 |")
P(f"| 3 CD 이송 | {total_ops:.1f} | M3 상세 (보수) |")
P(f"| 접힘 복귀 | {t_stow:.1f} | |")
P(f"| 180도 회전 | {t_spin:.1f} | 가정 |")
P(f"| S -> 출발구역 | {t_drive_back:.1f} | 가정 |")
P(f"| **합계** | **{mission:.1f}** | 포크 방식 약 58 s |")
fail_extra = 3 * (ttrap(APP, V_INS, 1000) + T_SETTLE + T_SENSE + ttrap(80, 200, 1000)) + 3 * (ttrap(360 - 2 * 100, W_TH, A_TH) * 0.2)
P(f"본선(무작위 배치) 최악: 각 행에서 첫 방문이 빈 베이스 -> 행마다 삽입·판정·후퇴 추가 + 반대편 이동: +{fail_extra:.1f} s 정도 -> {mission+fail_extra:.1f} s (150 s 대비 여유 {150-mission-fail_extra:.0f} s)")

P("")
P("## M5. CD 이탈 점검 (운반 중, R_C=200)")
w = math.radians(W_TH)
al = math.radians(A_TH)
ac = w * w * R_C / 1000
at = al * R_C / 1000
P(f"구심가속 {ac:.2f} m/s^2, 접선가속 {at:.2f} m/s^2, 합성 {math.hypot(ac,at):.2f} m/s^2 = {math.hypot(ac,at)/9.81:.2f} g")
P("PETG-CD 마찰계수 0.3~0.4 (가정, 확인필요) -> 마찰만으로는 한계. 림 턱(2mm)이 수평 이탈을 기하적으로 차단하므로 허용. 시제품에서 W_TH를 100/150/200 deg/s로 올리며 CD 이동량 측정.")

P("")
P("## M6. 스텝 속도와 타이머")
ms = {'θ': 8, 'R': 8, 'Z': 4}
th_sps = W_TH * 3 / 1.8 * ms['θ']
phi_dot = V_R / 1000 / (2 * L / 1000 * math.sin(math.radians(38.2)))
r_sps = math.degrees(phi_dot) * 3 / 1.8 * ms['R']
z_sps = V_Z * 25 * ms['Z']
P("| 축 | 감속/기구 | 마이크로스텝 | 최대 속도 | 최대 스텝률(sps) | 분해능 |")
P("|---|---|---|---|---|---|")
P(f"| θ | 20T:60T = 3:1 | 1/8 | {W_TH:.0f} deg/s | {th_sps:.0f} | 0.075 deg -> 386mm에서 {386*math.radians(1.8/3/8):.2f} mm |")
P(f"| R | 어깨 3:1 | 1/8 | {V_R:.0f} mm/s | {r_sps:.0f} | {2*L*math.sin(math.radians(38.2))*math.radians(1.8/3/8):.2f} mm (phi=38.2) |")
P(f"| Z | T8 리드 8 | 1/4 | {V_Z:.0f} mm/s | {z_sps:.0f} | {1/(25*4):.3f} mm |")
tot = th_sps + r_sps + z_sps
P(f"세 축 동시 최대 합 {tot:.0f} sps. 20 kHz DDA 한 개 ISR이면 각 축 최대 10 kHz까지 가능, 평균 부하 (ISR 약 120 사이클 가정, 16 MHz): {120*20000/16e6*100:.0f}% CPU.")
P("실제 SF2421 풀인 한계는 7.2V에서 풀스텝 환산 약 800~1000 sps(가정) -> θ 풀스텝 환산 250 sps, R 약 150 sps, Z 750 sps로 모두 한계의 1/4~3/4. Z가 가장 빠듯하므로 Z 속도는 30 -> 20 mm/s로 낮출 수 있다.")

P("")
P("## M7. 전력 예산 (7.2 V NiMH 6셀 팩 하나로 스테퍼 3 + DC 모터 2, Mega는 별도 AA 팩)")
Ilim = 0.7           # A/상 [가정] SF2421 정격 확인필요
Rcoil = 3.6          # ohm [가정]
V = 7.2
Phold = Ilim ** 2 * Rcoil        # 마이크로스텝 정지: 두 코일 합 I^2R = Imax^2 R
Ihold = Phold / V / 0.85
Imove = Ihold * 1.4
Idc_run, Idc_peak = 0.8, 2.0     # A 두 모터 합 [가정]
P(f"스테퍼 1개 정지(전류 제한 {Ilim} A/상): 코일 손실 {Phold:.2f} W -> 팩 전류 약 {Ihold:.2f} A (효율 85%, 가정). 이동 중 약 {Imove:.2f} A.")
P("| 상황 | 스테퍼 3개 | DC 2개 | 합계(A) | 팩 전압(내부저항 0.25 ohm, 가정) |")
P("|---|---|---|---|---|")
for lab, i1, i2 in (('홀딩만(DC 정지)', 3 * Ihold, 0), ('팔 이동', 3 * Imove, 0), ('주행(스테퍼 홀딩)', 3 * Ihold, Idc_run), ('주행 가속 피크', 3 * Ihold, Idc_peak)):
    P(f"| {lab} | {i1:.2f} | {i2:.2f} | {i1+i2:.2f} | {V-0.25*(i1+i2):.2f} V |")
t_arm = total_ops + t_stow
t_drv = t_drive_out + t_drive_back + t_spin
q = (3 * Imove * t_arm + 3 * Ihold * (mission - t_arm) + Idc_run * t_drv) / 3600
cap = 1900 * 0.8 / 1000   # Ah 사용 가능(80%) [가정]
P(f"임무 1회 전하량 {q*1000:.1f} mAh -> 팩 {cap*1000:.0f} mAh(1900 mAh x 80%, 가정) 로 약 {cap/q:.0f}회. 홀딩만 켠 대기는 {cap/(3*Ihold):.1f} 시간.")
P("SLEEP 전략: DRV8834 SLEEP은 인덱서를 초기화하고 nENBL은 위상을 유지하지만 로터가 최근접 극으로 끌려가 풀스텝(θ에서 팔끝 4 mm)만큼 위치가 어긋날 수 있다. -> θ·R·Z 모두 출발 후 계속 enable 유지(전류 약 0.8 A), 대기·충전 중 및 임무 종료 후 정지 상태에서만 disable. 필요 시 R·θ는 이동 사이에 홀딩 전류를 낮춰주는 TMC2208(UART/자동 정지전류)로 교체.")
P("전원 안정: 모터 팩은 스테퍼·DC 전용, Mega는 별도 팩이라 순간 강하로 리셋되지 않음. 드라이버마다 VMOT에 100 uF 이상 전해 커패시터 필수(배선 길이 5cm 이내).")

P("")
P("## M8. 원점 복귀(전원 인가 시) 소요 시간")
P("| 단계 | 동작 | 속도 | 시간(s) |")
P("|---|---|---|---|")
P(f"| 1 Z | 하단 리밋까지 하강(최대 행정 60mm) 후 2mm 후퇴, 저속 재접근 | 15 mm/s | {60/15+0.4+0.5:.1f} |")
P(f"| 2 R | phi 증가 방향 접힘 리밋까지(최대 약 70deg) | 60 deg/s | {70/60+0.6:.1f} |")
P(f"| 3 θ | 접힘 자세에서 θ 홈 스위치 확인, 눌려 있지 않으면 한 방향 탐색(최대 120deg) | 30 deg/s | {120/30+0.6:.1f} |")
open('motion_out.md', 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
