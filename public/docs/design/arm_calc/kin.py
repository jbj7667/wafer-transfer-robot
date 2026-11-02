# 팔 방식 기구학: 6개 베이스 (theta,R), 도달 여유, 팔꿈치 방향, 오차 민감도, 방향 추정, 접힘 포장 검사
# 실행: python -I kin.py  (출력 kin_out.md)
import math
S = (500.0, 240.0)
L = 205.0
A = 64.0  # 손목축 -> 포켓(CD 중심) 거리 [가정: 포크 루트=손목, mechanism.md 28->92]
bases = {'5(상좌)': (130, 130), '6(상우)': (870, 130), '3(중좌)': (180, 305),
         '4(중우)': (820, 305), '1(하좌)': (230, 480), '2(하우)': (770, 480)}


def polar(s, b):
    f = s[1] - b[1]
    l = s[0] - b[0]  # 로봇 전진=-y, 왼쪽=-x
    return math.degrees(math.atan2(l, f)), math.hypot(f, l)


out = []
P = out.append
P("## K1. 기준 (theta, R) 표 (계산) S=(500,240), 헤딩 북쪽, theta 왼쪽 +")
P("| 베이스 | theta(deg) | R_CD(mm) | R_손목=R-64 | 여유(410-R_손목) | phi=acos(R_손목/410) | 팔꿈치 x,y (s=+1) |")
P("|---|---|---|---|---|---|---|")
for n, b in bases.items():
    th, R = polar(S, b)
    Rw = R - A
    phi = math.degrees(math.acos(Rw / (2 * L)))
    ex = S[0] - L * math.sin(math.radians(th + phi))
    ey = S[1] - L * math.cos(math.radians(th + phi))
    P(f"| {n} | {th:+.1f} | {R:.1f} | {Rw:.1f} | {2*L-Rw:.1f} | {phi:.1f} | {ex:.0f}, {ey:.0f} |")
P("")
P("## K2. 포크 방향 대안별 필요 손목 반경 (R_max=386)")
P("| 포크 | 필요 R_손목 | 410 대비 | 판정 |")
P("|---|---|---|---|")
P(f"| U 바깥향(PLAN, 손목=루트가 안쪽) | {386-A:.0f} | 여유 {410-(386-A):.0f} | 가능 |")
P(f"| U 안쪽향(루트가 바깥) | {386+A:.0f} | 부족 {386+A-410:.0f} | 불가(L>=225 필요) |")
P("")
P("## K3. 링크 길이 L별 phi_min (R_손목,max=322 + 스톱오차 10 = 332)")
P("| L | 2L | phi_min(deg) | 특이점 여유(mm) |")
P("|---|---|---|---|")
for l in (160, 170, 180, 190, 205):
    rw = 332
    if rw < 2 * l:
        P(f"| {l} | {2*l} | {math.degrees(math.acos(rw/(2*l))):.1f} | {2*l-rw} |")
    else:
        P(f"| {l} | {2*l} | 불가 | {2*l-rw} |")


def tip_err(b, sx, sy, psi_deg):
    th, R = polar(S, b)
    ang = math.radians(th) + math.radians(psi_deg)
    px = sx - R * math.sin(ang)
    py = sy - R * math.cos(ang)
    return px, py, th, R


def comps(b, dx, dy, ps):
    px, py, th, R = tip_err(b, S[0] + dx, S[1] + dy, ps)
    t = math.radians(th)
    ex, ey = px - b[0], py - b[1]
    ux, uy = -math.sin(t), -math.cos(t)  # 포크 축(바깥) 월드
    vx, vy = -uy, ux
    return ex * vx + ey * vy, ex * ux + ey * uy, th, R


P("")
P("## K4. 정지오차 민감도 (공칭 명령 유지 시 포켓 위치오차 성분, mm)")
P("가로(lat)=포크 축에 수직(U 허용 +-14 대상), 깊이(dep)=포크 축 방향(원추 시트 +-10). 보정에 필요한 dR(mm), dtheta(deg)도 함께.")
P("| 베이스 | 오차원 | 가로 lat | 깊이 dep | 필요 dR | 필요 dth(deg) |")
P("|---|---|---|---|---|---|")
cases = {'S 북+10': (0, -10, 0), 'S 남+10': (0, 10, 0), '횡 +5': (5, 0, 0), '횡 -5': (-5, 0, 0),
         '헤딩 +2deg': (0, 0, 2), '헤딩 -2deg': (0, 0, -2)}
for n, b in bases.items():
    for lab, (dx, dy, ps) in cases.items():
        lat, dep, th, R = comps(b, dx, dy, ps)
        th2, R2 = polar((S[0] + dx, S[1] + dy), b)
        th2 -= ps
        P(f"| {n} | {lab} | {lat:+.1f} | {dep:+.1f} | {R2-R:+.1f} | {th2-th:+.2f} |")
P("")
P("## K5. 헤딩오차 e에 의한 가로 팔끝오차 = R*sin(e)")
P("| e | R=326.5 | R=361 | R=386 | U 허용 14 대비(386) |")
P("|---|---|---|---|---|")
for e in (0.5, 1, 2, 3):
    f = lambda R: R * math.sin(math.radians(e))
    P(f"| {e} deg | {f(326.5):.1f} | {f(361):.1f} | {f(386):.1f} | {f(386)/14*100:.0f}% |")
P("")
P("## K6. 가로오차 예산 (상단 행 R=386)")
b = (130, 130)
a1 = abs(comps(b, 0, 10, 0)[0])
a2 = abs(comps(b, 5, 0, 0)[0])
a3 = abs(comps(b, 0, 0, 2)[0])
P(f"트렁크 +-10: 가로 {a1:.1f} / 횡 +-5: 가로 {a2:.1f} / 헤딩 2deg: 가로 {a3:.1f}")
P(f"선형합 {a1+a2+a3:.1f} mm, RSS {math.sqrt(a1**2+a2**2+a3**2):.1f} mm (U 허용 14) -> 헤딩 보정 필수")
P("")
P("## K7. 방향 추정: 중단 행선 통과 시 좌/우 외곽 채널 시간차")
P("psi = atan(v*dt/d), d = 외곽 채널 간격(가정, 확인필요). 틱 분해능 1 ms. 에지 지터 j(mm/채널)가 지배: sigma = atan(sqrt2*j/d), 상승+하강 4에지 평균 시 /sqrt2")
P("| d(mm) | v(mm/s) | 틱 분해능(deg) | 지터 j(mm) | sigma 1에지(deg) | 4에지 평균(deg) | 386mm 팔끝(mm) |")
P("|---|---|---|---|---|---|---|")
for d in (40, 48, 60):
    for v in (100, 150):
        res = math.degrees(math.atan(v * 0.001 / d))
        for j in (0.5, 1.0):
            s1 = math.degrees(math.atan(math.sqrt(2) * j / d))
            s4 = s1 / math.sqrt(2)
            P(f"| {d} | {v} | {res:.2f} | {j} | {s1:.2f} | {s4:.2f} | {386*math.sin(math.radians(s4)):.1f} |")


def pack(Lk, phi_deg, r_tt=50, r_boss=20, fork_len=129, fork_w=118):
    phi = math.radians(phi_deg)
    pts = [(r_tt * math.cos(math.radians(a)), r_tt * math.sin(math.radians(a))) for a in range(0, 360, 10)]
    ex, ey = Lk * math.cos(phi), Lk * math.sin(phi)
    wx = 2 * Lk * math.cos(phi)
    for a in range(0, 360, 20):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        pts.append((ex + r_boss * c, ey + r_boss * s))
        pts.append((wx + r_boss * c, r_boss * s))
    for (x, y) in ((wx, fork_w / 2), (wx, -fork_w / 2), (wx + fork_len, fork_w / 2), (wx + fork_len, -fork_w / 2)):
        pts.append((x, y))
    best, ba = 1e9, 0
    for ad in range(0, 90):
        a = math.radians(ad)
        c, s = math.cos(a), math.sin(a)
        xs = [p[0] * c + p[1] * s for p in pts]
        ys = [-p[0] * s + p[1] * c for p in pts]
        m = max(max(xs) - min(xs), max(ys) - min(ys))
        if m < best:
            best, ba = m, ad
    return best, ba


P("")
P("## K8. 접힘 자세 최소 외접 정사각형 (한계 250). 턴테이블 반경 50, 보스 r20, 포크 길이 129 x 폭 118(손목 기준)")
P("| L | phi=90 | phi=75 | phi=60 | 최적 phi | 최적 변(mm) | 회전각 |")
P("|---|---|---|---|---|---|---|")
for Lk in (205, 190, 175, 160, 150):
    r = {p: pack(Lk, p)[0] for p in (90, 75, 60)}
    bb = min((pack(Lk, p)[0], p) for p in range(20, 181, 5))
    P(f"| {Lk} | {r[90]:.0f} | {r[75]:.0f} | {r[60]:.0f} | {bb[1]} | {bb[0]:.0f} | {pack(Lk, bb[1])[1]} |")

P("")
P("## K9. 링크 길이 변형 비교 (L=205 PLAN / 190 / 180): 도달과 팔꿈치 원")
P("| L | phi_min (R_손목 332 기준) | 특이점 여유 | 팔꿈치 원 북단 y=240-L | 보스 r20 가장자리 | 중단 phi | 하단 phi |")
P("|---|---|---|---|---|---|---|")
for Lk in (205, 190, 180):
    P(f"| {Lk} | {math.degrees(math.acos(332/(2*Lk))):.1f} deg | {2*Lk-332} mm | {240-Lk} | {240-Lk-20} | {math.degrees(math.acos(262.5/(2*Lk))):.1f} | {math.degrees(math.acos(297.2/(2*Lk))):.1f} |")
open('kin_out.md', 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
