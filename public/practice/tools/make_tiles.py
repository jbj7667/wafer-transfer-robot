import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from field import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "field_tiles_A4.pdf")
MM = 72 / 25.4
UW, UH, OV = 190.0, 277.0, 10.0
SX, SY = UW - OV, UH - OV  # step 180, 267
NC, NR = 6, 4
MX, MY = 10.0, 10.0  # page offset of usable area
GREY = (0.45, 0.45, 0.45)

polys = black_polys()
doc = pymupdf.Document()


def pt(x, y):
    return pymupdf.Point(x * MM, y * MM)


def text(page, x, y, s, size=8, bold=False, color=(0, 0, 0)):
    page.insert_text(pt(x, y), s, fontsize=size, fontname="mb" if bold else "mg",
                     fontfile=FONTB if bold else FONT, color=color)


def cross(page, x, y, L=4):
    sh = page.new_shape()
    sh.draw_line(pt(x - L, y), pt(x + L, y))
    sh.draw_line(pt(x, y - L), pt(x, y + L))
    sh.finish(color=(0.85, 0, 0), width=0.4)
    sh.commit()


for r in range(NR):
    for c in range(NC):
        page = doc.new_page(width=210 * MM, height=297 * MM)
        x0, y0 = c * SX, r * SY  # field coords of tile origin
        x1, y1 = x0 + UW, y0 + UH
        fx0, fy0, fx1, fy1 = x0, y0, min(x1, 1000), min(y1, 1000)

        def P(x, y):  # field -> page pt
            return pt(MX + x - x0, MY + y - y0)

        sh = page.new_shape()
        # black polygons
        for poly in polys:
            bx = poly_bbox(poly)
            if bx[2] < x0 or bx[0] > x1 or bx[3] < y0 or bx[1] > y1:
                continue
            cp = clip_poly(poly, x0, y0, x1, y1)
            if len(cp) >= 3:
                sh.draw_polyline([P(*q) for q in cp])
                sh.finish(fill=(0, 0, 0), color=None, closePath=True, width=0)
        sh.commit()
        # usable frame + field boundary
        sh = page.new_shape()
        sh.draw_rect(pymupdf.Rect(MX * MM, MY * MM, (MX + UW) * MM, (MY + UH) * MM))
        sh.finish(color=(0.7, 0.7, 0.7), width=0.3, dashes="[2 2] 0")
        sh.commit()
        # 1000x1000 field outline
        sh = page.new_shape()
        ex0, ey0, ex1, ey1 = max(x0, 0), max(y0, 0), min(x1, 1000), min(y1, 1000)
        sh.draw_rect(pymupdf.Rect(P(ex0, ey0), P(ex1, ey1)))
        sh.finish(color=(0, 0.4, 0.8), width=0.5)
        sh.commit()
        # overlap shading (right and bottom strips are overlap with next tile; left/top with previous)
        sh = page.new_shape()
        if c > 0:
            sh.draw_rect(pymupdf.Rect(MX * MM, MY * MM, (MX + OV) * MM, (MY + UH) * MM))
        if c < NC - 1:
            sh.draw_rect(pymupdf.Rect((MX + UW - OV) * MM, MY * MM, (MX + UW) * MM, (MY + UH) * MM))
        if r > 0:
            sh.draw_rect(pymupdf.Rect(MX * MM, MY * MM, (MX + UW) * MM, (MY + OV) * MM))
        if r < NR - 1:
            sh.draw_rect(pymupdf.Rect(MX * MM, (MY + UH - OV) * MM, (MX + UW) * MM, (MY + UH) * MM))
        sh.finish(color=None, fill=(1, 0.85, 0.2), fill_opacity=0.12)
        sh.commit()
        # base circles + numbers
        sh = page.new_shape()
        for bid, bx_, by_, h in BASES:
            if x0 - 60 <= bx_ <= x1 + 60 and y0 - 60 <= by_ <= y1 + 60:
                for d in (100, 50):
                    sh.draw_circle(P(bx_, by_), d / 2 * MM)
                sh.draw_line(P(bx_ - 6, by_), P(bx_ + 6, by_))
                sh.draw_line(P(bx_, by_ - 6), P(bx_, by_ + 6))
        sh.finish(color=GREY, width=0.35)
        sh.commit()
        for bid, bx_, by_, h in BASES:
            tx, ty = bx_ - 3, by_ - 30
            if x0 <= tx <= x1 - 8 and y0 + 5 <= ty <= y1:
                text(page, MX + tx - x0, MY + ty - y0, str(bid), 14, True, GREY)
        # registration crosses at overlap-zone centres (same field coords on neighbouring tiles)
        for k in (c, c + 1):
            for j in (r, r + 1):
                cx, cy = SX * k + OV / 2, SY * j + OV / 2
                if x0 <= cx <= x1 and y0 <= cy <= y1:
                    cross(page, MX + cx - x0, MY + cy - y0)
        # header
        text(page, MX, 6.5, f"R{r + 1}C{c + 1}", 11, True)
        text(page, MX + 22, 6.5, f"원점 x={x0:.0f}, y={y0:.0f} mm  |  1:1  |  인쇄 시 '실제 크기(100%)'  |  굵은 선 폭 19 mm", 7)
        text(page, MX, 292.5, "빨간 십자(+)를 이웃 타일과 겹쳐 맞춤. 노란 음영=10 mm 겹침 구간. 파란 선=경기장 외곽(1000×1000). 회색 원=Ø100/Ø50 베이스 표시.", 6)
        # assembly map on first page
        if r == 0 and c == 0:
            mx0, my0 = MX + 110, MY + 195
            cell = 11.0
            cellh = cell * SY / SX
            sh = page.new_shape()
            for rr in range(NR):
                for cc in range(NC):
                    rect = pymupdf.Rect((mx0 + cc * cell) * MM, (my0 + rr * cellh) * MM,
                                        (mx0 + (cc + 1) * cell) * MM, (my0 + (rr + 1) * cellh) * MM)
                    sh.draw_rect(rect)
            sh.finish(color=(0, 0, 0), width=0.5, fill=(0.93, 0.93, 0.93))
            sh.commit()
            for rr in range(NR):
                for cc in range(NC):
                    text(page, mx0 + cc * cell + 1.8, my0 + rr * cellh + 8.5, f"R{rr + 1}C{cc + 1}", 5,
                         bold=(rr == 0 and cc == 0))
            # field outline on map: field 1000 / 180 per cell
            fs = cell / SX  # horizontal & vertical use same mm-per-mm below
            fsy = cellh / SY
            sh = page.new_shape()
            sh.draw_rect(pymupdf.Rect(mx0 * MM, my0 * MM, (mx0 + 1000 * fs) * MM, (my0 + 1000 * fsy) * MM))
            sh.finish(color=(0, 0.4, 0.8), width=0.8)
            sh.commit()
            text(page, mx0, my0 - 14, "조립 지도 (6열 × 4행 = 24장)", 8, True)
            text(page, mx0, my0 - 8, "행(R)=위→아래, 열(C)=왼→오른. 이 장이 R1C1.", 6.5)
            text(page, mx0, my0 - 3, "파란 사각형=경기장 1000×1000 (타일 격자는 180×267 간격)", 6.5)
            text(page, mx0, my0 + NR * cellh + 5, "각 장 유효영역 190×277 mm, 겹침 10 mm", 6.5)

doc.save(OUT)
print("saved", OUT, doc.page_count)
