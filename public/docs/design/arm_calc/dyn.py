# 구조·하중·토크·질량·전도 안정성. 실행: python -I dyn.py (출력 dyn_out.md)
# 모든 입력은 가정(주석 [가정])이다. 실측 후 값만 바꿔 재실행한다.
import math
out = []
P = out.append
g = 9.81
L = 205.0
A = 64.0
S = (500.0, 240.0)
bases = {'5(상좌)': (130, 130), '6(상우)': (870, 130), '3(중좌)': (180, 305),
         '4(중우)': (820, 305), '1(하좌)': (230, 480), '2(하우)': (770, 480)}

# ---------------- D1 링크 단면 처짐 ----------------
E = 1800.0        # N/mm^2 [가정] PETG 인쇄 길이 방향 1.2~2.0 GPa
rho = 1.27e-3     # g/mm^3 PETG
fill = 0.80       # [가정] 4벽 상자의 실질 비율(벽 외 코너/내부 리브 포함)
P_tip = (16 + 35) * g / 1000  # N: CD 16g + 포크 일체 35g [가정]
P("## D1. 링크 단면 후보와 팔끝 처짐 (연속 외팔보 410mm, 하중·자중 모두 최대 길이로 보수 계산)")
P(f"E={E:.0f} N/mm^2 (가정), 끝단 하중 {P_tip:.2f} N (CD 16g + 포크 35g, 가정), 풀리·베어링 허브는 링크당 30g 추가 (가정)")
P("| 단면 w x h x t | I (mm^4) | 링크 1개 질량 (g) | 끝단하중 처짐 | 자중 처짐 | 합계 | 판정(<=1.5mm 목표) |")
P("|---|---|---|---|---|---|---|")
best = None
for (w, h, t) in ((22, 18, 1.6), (24, 20, 1.6), (28, 20, 1.6), (28, 24, 1.6), (30, 22, 2.0), (24, 28, 1.6)):
    I = (w * h ** 3 - (w - 2 * t) * (h - 2 * t) ** 3) / 12
    area = w * h - (w - 2 * t) * (h - 2 * t)
    m1 = area * L * rho * fill + 30  # g
    q = (2 * (m1 - 30) / 1000 * g) / (2 * L)  # N/mm 분포
    d_tip = P_tip * (2 * L) ** 3 / (3 * E * I)
    d_self = q * (2 * L) ** 4 / (8 * E * I)
    tot = d_tip + d_self
    P(f"| {w}x{h}x{t} | {I:.0f} | {m1:.0f} | {d_tip:.2f} | {d_self:.2f} | {tot:.2f} | {'OK' if tot <= 1.5 else '초과'} |")
P("")
P("관절 베어링 유격에 의한 기울기: 608 2개(간격 s_b=22mm), 반경 유격 합 c=0.02mm (가정) -> 기울기 c/s_b. 팔끝 영향 = 기울기 x 레버")
tilt = 0.02 / 22
P(f"기울기 {tilt*1000:.2f} mrad -> 어깨(레버 386): {tilt*386:.2f} mm, 팔꿈치(레버 205): {tilt*205:.2f} mm, 손목(레버 64): {tilt*64:.2f} mm, 합 {tilt*(386+205+64):.2f} mm")
P("-> 24x20x1.6 기준: 처짐 1.15 + 관절 기울기 0.60 = 약 1.8 mm (계산). E를 1200 N/mm^2로 낮추면(층간 약화) 처짐 1.7 + 0.6 = 2.3 mm. 판정 기준 3 mm 이내이나 벨트 처짐·판 휨은 미포함이므로 28x24 단면(0.69 mm)을 권장. 대책: 베어링 간격 30 mm 확대 시 기울기 -27%")


P("")
P("L=180 변형 처짐 (연속 외팔보 360 mm, 동일 조건)")
for (w, h, t) in ((24, 20, 1.6), (28, 20, 1.6), (28, 24, 1.6)):
    I = (w * h ** 3 - (w - 2 * t) * (h - 2 * t) ** 3) / 12
    area = w * h - (w - 2 * t) * (h - 2 * t)
    LL = 180.0
    q = (2 * (area * LL * rho * fill) / 1000 * g) / (2 * LL)
    tot2 = P_tip * (2 * LL) ** 3 / (3 * E * I) + q * (2 * LL) ** 4 / (8 * E * I)
    P(f"- {w}x{h}x{t}: 합계 {tot2:.2f} mm, 링크 1개 {area*LL*rho*fill+30:.0f} g")

# ---------------- D2 질량 ----------------
P("")
P("## D2. 질량 추정 (g, 모두 가정/카탈로그 값. 실측 필요)")
items_base = [
    ('DC 기어드모터 Ø37 x2', 300, 0, 55), ('바퀴 65mm x2 + 캐스터', 85, 0, 0),
    ('배터리 2팩 (NiMH 6셀 + AA 6셀, 홀더 포함)', 350, -63, 0), ('Mega + 쉴드', 80, -20, 0),
    ('L298 x1 + 스테퍼 드라이버 3 + HM-10 + 배선', 90, -10, 0), ('센서(라인·IR·초음파·스위치)', 40, 25, 0),
    ('하판·상판·스탠드오프·나사', 330, -5, 0),
]
items_z = [
    ('Z 스테퍼 SF2421 (고정)', 250), ('가이드봉 Ø8x185 x2 + 클램프', 190), ('T8 리드스크류+커플러+너트+LM8UU', 110),
]
items_lift = [
    ('θ 스테퍼 (승강대에 탑재)', 250), ('R 스테퍼 (회전대에 탑재)', 250), ('회전대 판 + 큰 베어링/부싱 + 60T 풀리', 110),
    ('링크 2개 (24x20x1.6) + 허브 풀리/베어링/벨트', 220), ('포크 + IR + 레버 스위치 + 손목 허브', 70), ('캐리지·브래킷·나사', 90),
]
mb = sum(i[1] for i in items_base)
mz = sum(i[1] for i in items_z)
ml = sum(i[1] for i in items_lift)
P("| 구분 | 항목 | g |")
P("|---|---|---|")
for n, m, *_ in items_base:
    P(f"| 차체 | {n} | {m} |")
for n, m in items_z:
    P(f"| Z축(고정) | {n} | {m} |")
for n, m in items_lift:
    P(f"| 승강대(이동) | {n} | {m} |")
tot = mb + mz + ml
P(f"| 합계 | 차체 {mb} + Z고정 {mz} + 승강대 {ml} | **{tot}** |")
P(f"포크 방식 대비(승강대 = 포크+캐리지 약 180g 가정, Z스테퍼·봉 동일): {mb+mz+180} g -> 팔 방식은 약 {tot-(mb+mz+180)} g 증가")
P(f"PLAN 판정 기준 1.5kg 대비: 팔 방식 {tot/1000:.2f} kg, 포크 방식 약 {(mb+mz+180)/1000:.2f} kg -> 두 방식 모두 1.5kg를 넘을 가능성이 크다(가정 오차 +-15%). 실측 전 기준 재검토 권고")
P(f"Z 승강 하중(이동 질량) {ml} g + CD 16 g")

# ---------------- D3 관성·토크 ----------------
P("")
P("## D3. 관성·토크")
m_link, m_hub, m_fork, m_cd = 0.065, 0.030, 0.050, 0.016  # kg [가정]
m_rmot = 0.25


def inertia_pose(phi_deg):
    phi = math.radians(phi_deg)
    p1 = (L / 2 * math.cos(phi), L / 2 * math.sin(phi))
    el = (L * math.cos(phi), L * math.sin(phi))
    p2 = (1.5 * L * math.cos(phi), 0.5 * L * math.sin(phi))
    w = (2 * L * math.cos(phi), 0.0)
    pts = [(m_link, p1), (m_hub, el), (m_link, p2), (m_hub, w), (m_fork, (w[0] + 30, 0)), (m_cd, (w[0] + A, 0))]
    J = sum(m * (x * x + y * y) for m, (x, y) in pts) * 1e-6  # kg m^2 (mm->m)
    J += 2 * m_link * L * L / 12 * 1e-6  # 링크 자체 회전
    J += m_rmot * 40 ** 2 * 1e-6 + 0.00035  # R모터·회전대 본체 (반경 40, 가정)
    return J


P("θ 축(회전대 중심) 관성모멘트 J_θ")
P("| 자세 | phi | 손목 R_w | J_θ (kg m^2) |")
P("|---|---|---|---|")
Jp = inertia_pose(38.2)
Jc = inertia_pose(70.6)
Js = inertia_pose(105)
P(f"| 상단 행 뻗음 | 38.2 | 322 | {Jp:.4f} |")
P(f"| 운반(R_c=200) | 70.6 | 136 | {Jc:.4f} |")
P(f"| 접힘 | 105 | -106 | {Js:.4f} |")
alpha = math.radians(450)
fric = 0.02  # N m [가정] 베어링+벨트
eta = 0.85
n_th = 3.0
for lab, J in (('뻗음', Jp), ('운반', Jc)):
    T = J * alpha + fric
    P(f"θ 가속 450 deg/s^2, {lab}: 회전대 토크 {T:.3f} N m -> 모터축 {T/n_th/eta:.3f} N m (보유토크 0.15~0.20 대비 {T/n_th/eta/0.175*100:.0f}%)")
P("θ는 수직축이라 중력 토크 없음. 위 값은 가감속 토크이며 450 sps 이내에서 풀인 토크 약 60~70%(가정)를 쓰므로 여유가 있다.")

# R 축
def Jeff(phi_deg):
    phi = math.radians(phi_deg)
    c, s = math.cos(phi), math.sin(phi)
    d1 = (-L / 2 * s, L / 2 * c)
    dE = (-L * s, L * c)
    d2 = (-1.5 * L * s, 0.5 * L * c)
    dw = (-2 * L * s, 0.0)
    J = m_link * (d1[0] ** 2 + d1[1] ** 2) + m_hub * (dE[0] ** 2 + dE[1] ** 2) + m_link * (d2[0] ** 2 + d2[1] ** 2)
    J += m_hub * dw[0] ** 2 + (m_fork + m_cd) * dw[0] ** 2
    J *= 1e-6
    J += 2 * m_link * L * L / 12 * 1e-6
    return J


P("")
P("R 축(어깨 phi) 환산 관성과 토크: 손목 반경가속도 a_R=2 m/s^2 (CD 슬립 방지, 0.2 g), 마찰 0.015 N m (가정)")
P("| phi | J_eff (kg m^2) | phi_ddot (rad/s^2) | 어깨 토크 (N m) | 감속비 2:1 모터 | 3:1 모터 | 4:1 모터 |")
P("|---|---|---|---|---|---|---|")
for phi in (38.2, 50.2, 70.6):
    J = Jeff(phi)
    pdd = 2.0 / (2 * L / 1000 * math.sin(math.radians(phi)))
    T = J * pdd + 0.015
    P(f"| {phi} | {J:.4f} | {pdd:.1f} | {T:.3f} | {T/2/eta:.3f} | {T/3/eta:.3f} | {T/4/eta:.3f} |")
P("결론: R축은 수평면 운동이라 중력 토크 없음. 감속 3:1이면 필요 모터 토크 0.02~0.05 N m 수준으로 보유토크(0.15~0.20, 확인필요)의 1/4 이하. 감속비는 토크가 아니라 분해능(0.075deg/마이크로스텝 -> 팔끝 0.3~0.5mm)과 속도(모터 150 sps 환산)로 정해진다.")

# Z 축
P("")
P("Z 축 (T8 리드 8, 효율 η=0.30 가정(플라스틱 너트), 가이드 마찰 2 N 가정)")
P("| 승강 질량 (kg) | 상승 토크 (N m) | 자기 유지 | 판정 |")
P("|---|---|---|---|")
lead = 0.008
helix = math.degrees(math.atan(8 / (math.pi * 8)))
for M in (0.7, 0.9, 1.1):
    F = M * g + 2.0
    T = F * lead / (2 * math.pi * 0.30)
    P(f"| {M} | {T:.3f} | 나선각 {helix:.1f}deg > 마찰각 약 9deg 이므로 자기 유지 안 됨 -> 정지 중 홀딩 전류 필요 | {'OK' if T < 0.10 else '주의'} |")
P("Z는 스텝 탈조·낙하 방지를 위해 항상 ENABLE 유지(홀딩 전류), 전원 차단 시 하강(포크 방식과 동일). 승강대 질량이 포크 방식의 약 5배라 하강 충격 대비 하단 범퍼 필요.")

# ---------------- D4 전도 안정성 ----------------
P("")
P("## D4. 전도 안정성 (정적). 좌표: 바퀴축 중점 원점, +x 전진, +y 왼쪽")
wheels = [(0, 92), (0, -92)]  # 외측 폭 210, 바퀴 폭 26 -> 접지 중심 +-92
caster = (-75, 0)


def com_base(xT):
    parts = [(0.300, 0, 0), (0.085, 0, 0), (0.350, -63, 0), (0.080, -20, 0), (0.090, -10, 0), (0.040, 25, 0), (0.330, -5, 0)]
    m = sum(p[0] for p in parts)
    return m, sum(p[0] * p[1] for p in parts) / m, 0.0


def arm_parts(th_deg, phi_deg, xT):
    """로봇 좌표에서 이동 질량(승강대 포함) 위치. th: 로봇 전진 기준 왼쪽+, 팔 방향"""
    th = math.radians(th_deg)
    phi = math.radians(phi_deg)
    # 팔 좌표(u: 팔 방향, v: 팔 방향 기준 왼쪽) -> 로봇 좌표 (전진 x, 왼쪽 y)
    def tr(u, v):
        return (xT + u * math.cos(th) - v * math.sin(th), u * math.sin(th) + v * math.cos(th))
    lst = [(m_link, tr(L / 2 * math.cos(phi), L / 2 * math.sin(phi))), (m_hub, tr(L * math.cos(phi), L * math.sin(phi))),
           (m_link, tr(1.5 * L * math.cos(phi), 0.5 * L * math.sin(phi))), (m_hub, tr(2 * L * math.cos(phi), 0)),
           (m_fork, tr(2 * L * math.cos(phi) + 30, 0)), (m_cd, tr(2 * L * math.cos(phi) + A, 0))]
    # 회전대·승강대 본체 (0.25+0.25+0.11+0.09 kg)는 축 위
    lst.append((0.25 + 0.25 + 0.11 + 0.09, (xT, 0.0)))  # θ·R 스테퍼, 회전대, 캐리지(축 위)
    return lst


def pt_edge_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    return ((p[0] - ax) * dy - (p[1] - ay) * dx) / math.hypot(dx, dy)


def margin(poly, p):
    # 볼록 다각형(반시계) 내부 점의 최소 변 거리 (음수면 바깥)
    n = len(poly)
    return min(-pt_edge_dist(p, poly[i], poly[(i + 1) % n]) for i in range(n))


def poses(xT):
    res = []
    for n, b in bases.items():
        f = S[1] - b[1]
        l = S[0] - b[0]
        th = math.degrees(math.atan2(l, f))
        R = math.hypot(f, l)
        phi = math.degrees(math.acos((R - A) / (2 * L)))
        res.append((n + ' 뻗음', th, phi))
    res.append(('운반 후방 θ=180', 180, 70.6))
    res.append(('접힘 θ=48 phi=105', 48, 105))
    return res


mB, xB, yB = com_base(0)
mz_fixed = 0.55  # Z 스테퍼+봉+스크류, 위치 xmast
P(f"차체 질량 {mB:.2f} kg(무게중심 x={xB:.0f}), Z 고정부 0.55 kg, 승강대 1.0 kg (D2 반올림)")
P("터닝 축 x_T(회전대 중심)와 마스트 위치를 달리하여 최소 안정 여유(최단 변 거리, mm)를 계산. 마스트는 회전대에서 앞쪽 +60 mm에 배치(가정: 팔이 지나지 않는 전방 섹터)")
polyA = [(-75, 0), (0, -92), (0, 92)]
# 반시계: caster(-75,0) -> (0,-92) -> (0,92)
for lab, poly in (
    ('A: 구동륜 2 + 후방 캐스터 (삼각형)', polyA),
    ('B: A + 전방 스키드 2개 (x=+95, y=+-70)', [(-75, 0), (0, -92), (95, -70), (95, 70), (0, 92)]),
    ('C: 구동륜 + 전방 스키드(x=+80, y=+-85) + 후방 캐스터 2개(x=-70, y=+-60)', [(-70, -60), (0, -92), (80, -85), (80, 85), (0, 92), (-70, 60)]),
):
    P("")
    P(f"### 지지 다각형 {lab}")
    P("| x_T | " + " | ".join(n for n, _, _ in poses(0)) + " |")
    P("|---|" + "---|" * len(poses(0)))
    for xT in (-30, 0, 20, 40):
        row = []
        for n, th, phi in poses(xT):
            parts = [(mB, (xB, 0.0)), (mz_fixed, (xT + 60, 0.0))] + arm_parts(th, phi, xT)
            M = sum(p[0] for p in parts)
            cx = sum(p[0] * p[1][0] for p in parts) / M
            cy = sum(p[0] * p[1][1] for p in parts) / M
            row.append(f"{margin(poly, (cx, cy)):+.0f} (CoM {cx:.0f},{cy:.0f})")
        P(f"| {xT} | " + " | ".join(row) + " |")
P("")
P("해석: 값은 가장 가까운 변까지 거리(mm), 음수면 전도. 목표 >= +20 mm(진동·경사 0.5deg 여유). 구성 A는 앞변이 구동륜 축선이라 팔이 앞을 향하는 자세에서 여유가 작거나 음수 -> 전방 스키드 필수.")
P("스키드는 볼 캐스터를 지면보다 1~2 mm 띄워(스페이서) 정상 주행엔 닿지 않고 전도 시에만 접촉하도록 한다(라인 단차·교차점 걸림 방지).")
open('dyn_out.md', 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
