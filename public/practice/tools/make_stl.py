import math, os, struct
from collections import Counter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stl")
N = 96


def ring(r, z):
    return [(r * math.cos(2 * math.pi * i / N), r * math.sin(2 * math.pi * i / N), z) for i in range(N)]


class Mesh:
    def __init__(self):
        self.v, self.t = [], []

    def ring(self, r, z):
        s = len(self.v)
        self.v += ring(r, z)
        return s

    def center(self, z):
        self.v.append((0.0, 0.0, z))
        return len(self.v) - 1

    def band(self, a, b, outward=True):
        """quad strip between ring a (lower) and ring b (upper)."""
        for i in range(N):
            j = (i + 1) % N
            if outward:
                self.t += [(a + i, a + j, b + j), (a + i, b + j, b + i)]
            else:
                self.t += [(a + i, b + j, a + j), (a + i, b + i, b + j)]

    def fan(self, c, a, facing_up):
        for i in range(N):
            j = (i + 1) % N
            self.t.append((c, a + i, a + j) if facing_up else (c, a + j, a + i))

    def annulus(self, outer, inner, facing_up):
        for i in range(N):
            j = (i + 1) % N
            if facing_up:
                self.t += [(outer + i, outer + j, inner + j), (outer + i, inner + j, inner + i)]
            else:
                self.t += [(outer + i, inner + j, outer + j), (outer + i, inner + i, inner + j)]


def write(mesh, name):
    with open(os.path.join(OUT, name), "wb") as f:
        f.write(b"practice field dummy base".ljust(80, b" "))
        f.write(struct.pack("<I", len(mesh.t)))
        for a, b, c in mesh.t:
            p, q, r = mesh.v[a], mesh.v[b], mesh.v[c]
            u = [q[k] - p[k] for k in range(3)]
            w = [r[k] - p[k] for k in range(3)]
            n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
            L = math.sqrt(sum(x * x for x in n)) or 1
            f.write(struct.pack("<12fH", *[x / L for x in n], *p, *q, *r, 0))


def base(h_total):
    m = Mesh()
    b0 = m.ring(50, 0)
    c0 = m.center(0)
    b1 = m.ring(50, 100)
    s1 = m.ring(25, 100)
    t1 = m.ring(25, h_total)
    ct = m.center(h_total)
    m.fan(c0, b0, False)
    m.band(b0, b1, True)
    m.annulus(b1, s1, True)
    m.band(s1, t1, True)
    m.fan(ct, t1, True)
    return m


def disc(R, r, th):
    m = Mesh()
    ob, ib = m.ring(R, 0), m.ring(r, 0)
    ot, it = m.ring(R, th), m.ring(r, th)
    m.annulus(ob, ib, False)
    m.annulus(ot, it, True)
    m.band(ob, ot, True)
    m.band(ib, it, False)
    return m


def check(name):
    d = open(os.path.join(OUT, name), "rb").read()
    n = struct.unpack("<I", d[80:84])[0]
    assert len(d) == 84 + 50 * n
    edges = Counter()
    mn, mx = [1e9] * 3, [-1e9] * 3
    vol = 0
    for k in range(n):
        rec = struct.unpack("<12fH", d[84 + 50 * k: 134 + 50 * k])
        vs = [tuple(round(x, 4) for x in rec[3 + 3 * i: 6 + 3 * i]) for i in range(3)]
        for i in range(3):
            edges[tuple(sorted((vs[i], vs[(i + 1) % 3])))] += 1
            for ax in range(3):
                mn[ax] = min(mn[ax], vs[i][ax])
                mx[ax] = max(mx[ax], vs[i][ax])
        p, q, r = vs
        vol += (p[0] * (q[1] * r[2] - q[2] * r[1]) - p[1] * (q[0] * r[2] - q[2] * r[0]) + p[2] * (q[0] * r[1] - q[1] * r[0])) / 6
    bad = [e for e, c in edges.items() if c != 2]
    print(f"{name}: tris={n} watertight={not bad} (bad edges {len(bad)}) bbox={[round(mx[i]-mn[i],3) for i in range(3)]} "
          f"signed vol={vol:.0f} mm3 -> {vol/1000:.1f} cm3, x1.24x0.25 = {vol/1000*1.24*0.25:.0f} g")


for name, mesh in (("base_200.stl", base(200)), ("base_175.stl", base(175)),
                   ("base_check_ring_120.stl", disc(60, 8, 1.2))):
    write(mesh, name)
    check(name)
