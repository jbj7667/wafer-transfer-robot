"""Field geometry shared by the practice-field generators (mm, origin top-left, +y down)."""
import math

W = 19.0
R = W / 2
FONT = "C:/Windows/Fonts/malgun.ttf"
FONTB = "C:/Windows/Fonts/malgunbd.ttf"

# straight centre-line segments: (name, (x1,y1), (x2,y2))
SEGMENTS = [
    ("트렁크(세로)", (500, 130), (500, 770)),
    ("하단 가로선", (400, 870), (130, 870)),
    ("출발·도착 바", (130, 820), (130, 920)),  # extents incl. round ends
]
ROWS = [("상단 행", 130, 270, 175), ("중단 행", 305, 220, 200), ("하단 행", 480, 170, 200)]
ARC = dict(c=(400, 770), r=100)  # from (500,770) to (400,870), quarter circle (angle 0 -> 90deg, y down)

BASES = [  # id, x, y, post top height
    (5, 130, 130, 175), (6, 870, 130, 175),
    (3, 180, 305, 200), (4, 820, 305, 200),
    (1, 230, 480, 200), (2, 770, 480, 200),
]


def capsule(p1, p2, w=W, n=24):
    """Convex polygon of a stadium with centre line p1-p2 and total width w."""
    r = w / 2
    a = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    pts = []
    for i in range(n + 1):  # cap at p2 : angles a-90 .. a+90
        t = a - math.pi / 2 + math.pi * i / n
        pts.append((p2[0] + r * math.cos(t), p2[1] + r * math.sin(t)))
    for i in range(n + 1):  # cap at p1
        t = a + math.pi / 2 + math.pi * i / n
        pts.append((p1[0] + r * math.cos(t), p1[1] + r * math.sin(t)))
    return pts


def bar(x, y, total=100.0, w=W):
    """Vertical stop bar, 'total' long INCLUDING the round ends."""
    h = total / 2 - w / 2
    return capsule((x, y - h), (x, y + h), w)


def arc_poly(n=96):
    cx, cy = ARC["c"]
    r = ARC["r"]
    outer, inner = [], []
    for i in range(n + 1):
        t = (math.pi / 2) * i / n
        outer.append((cx + (r + R) * math.cos(t), cy + (r + R) * math.sin(t)))
        inner.append((cx + (r - R) * math.cos(t), cy + (r - R) * math.sin(t)))
    return outer + inner[::-1]


def cap_disc(c, n=24):
    return [(c[0] + R * math.cos(2 * math.pi * i / (2 * n)), c[1] + R * math.sin(2 * math.pi * i / (2 * n))) for i in range(2 * n)]


def black_polys():
    """All filled black polygons of the field (mm)."""
    P = []
    P.append(capsule((500, 130), (500, 770)))
    P.append(arc_poly())
    P.append(capsule((400, 870), (130, 870)))
    P.append(bar(130, 870))  # start/finish
    for name, y, half, _ in ROWS:
        P.append(capsule((500 - half, y), (500 + half, y)))
        P.append(bar(500 - half, y))
        P.append(bar(500 + half, y))
    return P


def clip_poly(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman clip against an axis-aligned rect."""
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia:
                    out.append(inter(a, b))
                out.append(b)
            elif ia:
                out.append(inter(a, b))
        return out

    def ix(xc):
        return lambda a, b: (xc, a[1] + (b[1] - a[1]) * (xc - a[0]) / (b[0] - a[0]))

    def iy(yc):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yc - a[1]) / (b[1] - a[1]), yc)

    pts = poly
    for ins, it in ((lambda p: p[0] >= x0, ix(x0)), (lambda p: p[0] <= x1, ix(x1)),
                    (lambda p: p[1] >= y0, iy(y0)), (lambda p: p[1] <= y1, iy(y1))):
        if not pts:
            return []
        pts = clip(pts, ins, it)
    return pts


def poly_bbox(p):
    xs = [q[0] for q in p]
    ys = [q[1] for q in p]
    return min(xs), min(ys), max(xs), max(ys)
