import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from field import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "field_overview.pdf")
MM = 72 / 25.4
S = 1 / 6.0  # A4 cannot hold 1:4 (250 mm); 1:6 used
OX, OY = 28.0, 46.0  # page position (mm) of field origin
BLUE = (0, 0.35, 0.75)
GREY = (0.45, 0.45, 0.45)
RED = (0.8, 0, 0)

doc = pymupdf.Document()
page = doc.new_page(width=210 * MM, height=297 * MM)


def P(x, y):
    return pymupdf.Point((OX + x * S) * MM, (OY + y * S) * MM)


def T(x, y, s, size=7, bold=False, color=(0, 0, 0), page_xy=False, rot=0):
    p = pymupdf.Point(x * MM, y * MM) if page_xy else P(x, y)
    page.insert_text(p, s, fontsize=size, fontname="mb" if bold else "mg",
                     fontfile=FONTB if bold else FONT, color=color, rotate=rot)


def line(a, b, color=BLUE, w=0.4):
    sh = page.new_shape()
    sh.draw_line(P(*a), P(*b))
    sh.finish(color=color, width=w)
    sh.commit()


def hdim(x1, x2, y, label, off=0):
    """horizontal dimension at field-y 'y' (extension lines drawn by caller)"""
    line((x1, y), (x2, y), BLUE, 0.4)
    for x in (x1, x2):
        line((x, y - 8), (x, y + 8), BLUE, 0.4)
    T((x1 + x2) / 2 - 6 * len(label) / 2.2 * 1.2, y - 6, label, 6.5, color=BLUE)


def vdim(x, y1, y2, label):
    line((x, y1), (x, y2), BLUE, 0.4)
    for y in (y1, y2):
        line((x - 8, y), (x + 8, y), BLUE, 0.4)
    T(x + 6, (y1 + y2) / 2 + 12, label, 6.5, color=BLUE)


page.insert_text(pymupdf.Point(15 * MM, 14 * MM), "연습 경기장 개요 (자기 진영 1000 × 1000 mm)", fontsize=14,
                 fontname="mb", fontfile=FONTB)
page.insert_text(pymupdf.Point(15 * MM, 20 * MM), "축척 1:6 (A4에 1:4=250 mm가 들어가지 않아 1:6 사용) · 원점 좌상단, +x 오른쪽, +y 아래 · 단위 mm",
                 fontsize=7.5, fontname="mg", fontfile=FONT, color=GREY)

# board
sh = page.new_shape()
sh.draw_rect(pymupdf.Rect(P(0, 0), P(1000, 1000)))
sh.finish(color=(0, 0, 0), width=0.6, fill=(0.97, 0.97, 0.97))
sh.commit()

# black polys
sh = page.new_shape()
for poly in black_polys():
    sh.draw_polyline([P(*q) for q in poly])
    sh.finish(fill=(0, 0, 0), color=None, closePath=True)
sh.commit()

# base circles
sh = page.new_shape()
for bid, x, y, h in BASES:
    for d in (100, 50):
        sh.draw_circle(P(x, y), d / 2 * S * MM)
sh.finish(color=GREY, width=0.4)
sh.commit()
for bid, x, y, h in BASES:
    sh = page.new_shape()
    sh.draw_circle(P(x, y), 4.2 * MM / 1.0 * 0.5)
    sh.finish(color=RED, fill=(1, 1, 1), width=0.5)
    sh.commit()
    T(x - 8, y - 58, str(bid), 9, True, RED)
    T(x - 15, y + 70, f"H{h}", 6, False, GREY)

# row dims along bottom/top edges
# top: stop bar x positions
hdim(230, 770, -22, "540")
hdim(280, 720, -48, "440")
hdim(330, 670, -74, "340")
# bars extension lines
hdim(0, 1000, -100, "1000")
# left side vertical dims
vdim(-30, 0, 130, "130")
vdim(-30, 130, 305, "175")
vdim(-30, 305, 480, "175")
vdim(-55, 0, 1000, "")
T(-70, 520, "1000", 6.5, color=BLUE, rot=90)
# trunk & row labels
T(525, 600, "x=500", 6.5, color=BLUE)
T(525, 770 + 40, "R100", 6.5, color=RED)
T(130 + 15, 960, "출발·도착", 6.5, True)
T(130 + 15, 985, "(130, 820~920)", 5.5, color=GREY)
T(250, 118, "상단 행 y=130", 5.5, color=GREY)
T(300, 293, "중단 행 y=305", 5.5, color=GREY)
T(350, 468, "하단 행 y=480", 5.5, color=GREY)
# bases x dims bottom
# bottom: x distances of base centres
# base coordinates table in legend
lx, ly = 15, 219
page.insert_text(pymupdf.Point(lx * MM, ly * MM), "범례", fontsize=10, fontname="mb", fontfile=FONTB)
items = [
    ("black", "검정 선 폭 19 mm, 끝은 반원(R9.5). 정지선/출발·도착 바는 둥근 끝 포함 전체 길이 100 mm"),
    ("grey", "회색 얇은 원 Ø100 / Ø50 = 웨이퍼 베이스 위치 (번호는 빨강)"),
    ("red", "베이스 번호: 왼쪽 1(하단)·3(중단)·5(상단), 오른쪽 2·4·6. H=기둥 상단 높이(mm)"),
]
yy = ly + 7
for kind, txt in items:
    sh = page.new_shape()
    r = pymupdf.Rect(lx * MM, (yy - 3) * MM, (lx + 8) * MM, (yy - 0.5) * MM)
    if kind == "black":
        sh.draw_rect(r); sh.finish(fill=(0, 0, 0), color=None)
    elif kind == "grey":
        sh.draw_circle(pymupdf.Point((lx + 4) * MM, (yy - 1.7) * MM), 1.4 * MM); sh.finish(color=GREY, width=0.5)
    else:
        sh.draw_circle(pymupdf.Point((lx + 4) * MM, (yy - 1.7) * MM), 1.4 * MM); sh.finish(color=RED, width=0.6)
    sh.commit()
    page.insert_text(pymupdf.Point((lx + 12) * MM, yy * MM), txt, fontsize=7.5, fontname="mg", fontfile=FONT)
    yy += 5.2

# table
rows = [("행", "y", "행 선 x 범위", "정지선 x", "베이스 L/R", "기둥 높이")]
rows += [("상단", "130", "230~770", "230 / 770", "5 (130) / 6 (870)", "175"),
         ("중단", "305", "280~720", "280 / 720", "3 (180) / 4 (820)", "200"),
         ("하단", "480", "330~670", "330 / 670", "1 (230) / 2 (770)", "200")]
cw = [18, 16, 34, 30, 44, 24]
ty = yy + 5
for i, row in enumerate(rows):
    x = lx
    for w_, cell in zip(cw, row):
        page.insert_text(pymupdf.Point(x * MM, ty * MM), cell, fontsize=7.5, fontname="mb" if i == 0 else "mg",
                         fontfile=FONTB if i == 0 else FONT)
        x += w_
    ty += 5.5
notes = [
    "트렁크: x=500, y=130→770 직선 → R100 호(중심 (400,770), (500,770)→(400,870)) → y=870, x=400→130 직선.",
    "출발·도착 바: x=130, y=820~920. 정지선: 각 행 끝에서 y±50. 베이스 중심은 정지선에서 바깥으로 100 mm.",
    "모든 치수 허용오차 ±1 mm(대회 규격 p.7). 규격 도면과 대조하여 불일치 없음.",
    "실제 크기(1:1) 출력은 field_tiles_A4.pdf, 테이프 시공은 field_tape_guide.pdf 참조.",
]
ty += 3
for n in notes:
    page.insert_text(pymupdf.Point(lx * MM, ty * MM), "· " + n, fontsize=7, fontname="mg", fontfile=FONT)
    ty += 4.5

doc.save(OUT)
print("ok")
