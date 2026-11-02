# 펜-종이 반복정밀도용 A3 표적지 생성기. 실행: python -I target_sheet.py  -> target_A3.pdf
# 좌표: 종이 가로(420 mm)가 θ 축에서 바깥쪽 반경 방향. 종이 왼쪽 변 = θ 축에서 X0 mm 지점(중심선 θ=0 위).
# 표적: R = 322, 354, 386 mm (펜 끝 = 손목 R_w + 64) x θ = -15, 0, +15 도 (9곳). 10 mm 격자.
import math
try:
    import pymupdf as fitz
except ImportError:
    import fitz

MM = 72.0 / 25.4
W, H = 420.0, 297.0
X0 = 290.0                       # 종이 왼쪽 변의 반경(mm)
RS = (322.0, 354.0, 386.0)
THS = (-15.0, 0.0, 15.0)

doc = fitz.open()
pg = doc.new_page(width=W * MM, height=H * MM)


def P(x, y):                     # 종이 mm -> pt
    return fitz.Point(x * MM, y * MM)


def polar(R, th):                # (R, θ) -> 종이 mm (θ 축이 종이 밖 왼쪽, 중심선 y=H/2)
    return (R * math.cos(math.radians(th)) - X0, H / 2 - R * math.sin(math.radians(th)))


# 10 mm 격자 (50 mm 마다 굵게)
for i in range(0, int(W) + 1, 10):
    thick = (i % 50 == 0)
    pg.draw_line(P(i, 0), P(i, H), color=(0.55, 0.55, 0.55) if thick else (0.8, 0.8, 0.8), width=0.6 if thick else 0.25)
for j in range(0, int(H) + 1, 10):
    thick = (j % 50 == 0)
    pg.draw_line(P(0, j), P(W, j), color=(0.55, 0.55, 0.55) if thick else (0.8, 0.8, 0.8), width=0.6 if thick else 0.25)
# 가장자리 눈금 라벨: 반경(R)
for i in range(0, int(W) + 1, 50):
    pg.insert_text(P(i + 0.8, 5.5), 'R%d' % (X0 + i), fontsize=6, color=(0.3, 0.3, 0.3))
# 호(동심원) R=322/354/386 와 방사선 θ
for R in RS:
    pts = []
    for k in range(-240, 241):
        th = k / 10.0
        x, y = polar(R, th)
        if 0 <= x <= W and 0 <= y <= H:
            pts.append(P(x, y))
    if len(pts) > 1:
        pg.draw_polyline(pts, color=(0.0, 0.4, 0.8), width=0.5, dashes='[3 2] 0')
for th in THS:
    a = polar(300.0, th); b = polar(400.0, th)
    pg.draw_line(P(*a), P(*b), color=(0.0, 0.4, 0.8), width=0.5, dashes='[3 2] 0')
# 표적: 십자 + 동심원(r=2, 5, 10 mm)
for R in RS:
    for th in THS:
        x, y = polar(R, th)
        red = (0.85, 0.1, 0.1)
        pg.draw_line(P(x - 12, y), P(x + 12, y), color=red, width=0.6)
        pg.draw_line(P(x, y - 12), P(x, y + 12), color=red, width=0.6)
        for r in (2, 5, 10):
            pg.draw_circle(P(x, y), r * MM, color=red, width=0.4)
        pg.insert_text(P(x + 3, y - 12.5), 'R%d t%+d' % (R, th), fontsize=6.5, color=red)
# 정합 표식(모서리 십자) + 사용법
for (cx, cy) in ((8, 8), (W - 8, 8), (8, H - 8), (W - 8, H - 8)):
    pg.draw_line(P(cx - 4, cy), P(cx + 4, cy), color=(0, 0, 0), width=0.8)
    pg.draw_line(P(cx, cy - 4), P(cx, cy + 4), color=(0, 0, 0), width=0.8)
note = ('arm bench repeatability target  |  A3 landscape, print at 100%% (no fit-to-page)  |  grid 10 mm, bold 50 mm\n'
        'Paper left edge is at radius %d mm from the theta axis on the theta=0 line; tape paper flat on a board.\n'
        'Targets R=%s mm (pen tip = wrist Rw + 64 mm) at theta=%s deg. Mark each point 10x, one-direction approach.' %
        (X0, '/'.join('%d' % r for r in RS), '/'.join('%+d' % t for t in THS)))
pg.insert_text(P(20, H - 24), note, fontsize=7, color=(0, 0, 0))
doc.save('target_A3.pdf')
print('target_A3.pdf', pg.rect.width / MM, 'x', pg.rect.height / MM, 'mm')
