"""Generate ui-v2/src/landing/alnstStrokes.js from the ALNST font (stdlib only).

The landing hero draws each ALNST glyph along its own lines: the glyph outline is revealed through a mask whose
strokes run along the glyph's centre lines, and the glyph's dots pop in afterwards. This script derives, per glyph,
the outline contours, the centre lines (a Zhang-Suen skeleton of a raster of the glyph, traced into polylines,
spurs pruned, simplified) and which contours are dots. Coordinates are font units with y pointing down from the
ascender, so they drop straight into an SVG viewBox.

    python ui-v2/scripts/gen_alnst_strokes.py            # writes ui-v2/src/landing/alnstStrokes.js
    python ui-v2/scripts/gen_alnst_strokes.py --report   # also prints per-glyph stroke and dot counts
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "src", "styles", "tokens", "fonts", "alnst-400-normal.ttf")
OUT = os.path.join(HERE, "..", "src", "landing", "alnstStrokes.js")

# Hero lines are uppercase, so only capitals, digits and punctuation are needed.
CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    "0123456789"
    " .,:;!?-–—'\"«»()/&+@#%·"
)
PX_PER_STROKE = 9.0  # raster resolution: pixels across one stroke
QUAD_STEPS = 10


class Font:
    def __init__(self, path):
        self.d = open(path, "rb").read()
        n = struct.unpack(">H", self.d[4:6])[0]
        self.t = {}
        for i in range(n):
            tag, _, off, ln = struct.unpack(">4sIII", self.d[12 + 16 * i: 28 + 16 * i])
            self.t[tag.decode("latin1")] = off
        h = self.t["head"]
        self.upm = self.u16(h + 18)
        self.long_loca = self.i16(h + 50) == 1
        self.num_glyphs = self.u16(self.t["maxp"] + 4)
        hh = self.t["hhea"]
        self.asc = self.i16(hh + 4)
        self.desc = self.i16(hh + 6)
        self.num_hm = self.u16(hh + 34)
        self.cmap = self._cmap()

    def u16(self, o):
        return struct.unpack(">H", self.d[o:o + 2])[0]

    def i16(self, o):
        return struct.unpack(">h", self.d[o:o + 2])[0]

    def u32(self, o):
        return struct.unpack(">I", self.d[o:o + 4])[0]

    def _cmap(self):
        base = self.t["cmap"]
        best = None
        for i in range(self.u16(base + 2)):
            pid, eid, so = struct.unpack(">HHI", self.d[base + 4 + 8 * i: base + 12 + 8 * i])
            if self.u16(base + so) == 4 and (pid, eid) in ((3, 1), (0, 3), (0, 4), (0, 1)):
                best = base + so
        st = best
        seg = self.u16(st + 6) // 2
        ends = [self.u16(st + 14 + 2 * k) for k in range(seg)]
        starts = [self.u16(st + 16 + 2 * seg + 2 * k) for k in range(seg)]
        deltas = [self.i16(st + 16 + 4 * seg + 2 * k) for k in range(seg)]
        ro_base = st + 16 + 6 * seg
        ros = [self.u16(ro_base + 2 * k) for k in range(seg)]
        m = {}
        for k in range(seg):
            for c in range(starts[k], ends[k] + 1):
                if c == 0xFFFF:
                    continue
                if ros[k] == 0:
                    g = (c + deltas[k]) & 0xFFFF
                else:
                    g = self.u16(ro_base + 2 * k + ros[k] + 2 * (c - starts[k]))
                    if g:
                        g = (g + deltas[k]) & 0xFFFF
                if g:
                    m[c] = g
        return m

    def advance(self, g):
        hm = self.t["hmtx"]
        return self.u16(hm + 4 * min(g, self.num_hm - 1))

    def loca(self, g):
        lo = self.t["loca"]
        if self.long_loca:
            return self.u32(lo + 4 * g), self.u32(lo + 4 * g + 4)
        return 2 * self.u16(lo + 2 * g), 2 * self.u16(lo + 2 * g + 2)

    def contours(self, g, dx=0, dy=0, sx=1.0, sy=1.0):
        """Contours as lists of (x, y, on_curve), in font units with y up."""
        a, b = self.loca(g)
        if a == b:
            return []
        o = self.t["glyf"] + a
        nc = self.i16(o)
        if nc < 0:
            return self._composite(o + 10)
        ends = [self.u16(o + 10 + 2 * k) for k in range(nc)]
        npts = ends[-1] + 1
        p = o + 10 + 2 * nc
        p += 2 + self.u16(p)
        flags = []
        while len(flags) < npts:
            f = self.d[p]
            p += 1
            flags.append(f)
            if f & 8:
                r = self.d[p]
                p += 1
                flags.extend([f] * r)
        xs, ys = [], []
        v = 0
        for f in flags:
            if f & 2:
                dv = self.d[p]
                p += 1
                v += dv if f & 16 else -dv
            elif not f & 16:
                v += self.i16(p)
                p += 2
            xs.append(v)
        v = 0
        for f in flags:
            if f & 4:
                dv = self.d[p]
                p += 1
                v += dv if f & 32 else -dv
            elif not f & 32:
                v += self.i16(p)
                p += 2
            ys.append(v)
        out, s = [], 0
        for e in ends:
            out.append([(xs[i] * sx + dx, ys[i] * sy + dy, bool(flags[i] & 1)) for i in range(s, e + 1)])
            s = e + 1
        return out

    def _composite(self, p):
        out = []
        while True:
            fl = self.u16(p)
            gi = self.u16(p + 2)
            p += 4
            if fl & 1:
                a1, a2 = self.i16(p), self.i16(p + 2)
                p += 4
            else:
                a1, a2 = struct.unpack(">bb", self.d[p:p + 2])
                p += 2
            sx = sy = 1.0
            if fl & 8:
                sx = sy = self.i16(p) / 16384
                p += 2
            elif fl & 0x40:
                sx, sy = self.i16(p) / 16384, self.i16(p + 2) / 16384
                p += 4
            elif fl & 0x80:
                sx, sy = self.i16(p) / 16384, self.i16(p + 6) / 16384
                p += 8
            out += self.contours(gi, a1 if fl & 2 else 0, a2 if fl & 2 else 0, sx, sy)
            if not fl & 0x20:
                return out


def segments(contour):
    """Quadratic contour → list of ('L', (x, y)) / ('Q', (cx, cy), (x, y)) starting at an on-curve point."""
    pts = contour[:]
    if not any(p[2] for p in pts):
        a, b = pts[0], pts[1]
        pts.insert(0, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, True))
    k = next(i for i, p in enumerate(pts) if p[2])
    pts = pts[k:] + pts[:k]
    start = pts[0]
    segs = []
    i, n = 1, len(pts)
    ctrl = None
    while i <= n:
        p = pts[i % n] if i < n else start
        if p[2]:
            segs.append(("Q", ctrl, p[:2]) if ctrl else ("L", p[:2]))
            ctrl = None
        else:
            if ctrl:
                mid = ((ctrl[0] + p[0]) / 2, (ctrl[1] + p[1]) / 2)
                segs.append(("Q", ctrl, mid))
            ctrl = p[:2]
        i += 1
    if ctrl:
        segs.append(("Q", ctrl, start[:2]))
    return start[:2], segs


def flatten(start, segs):
    pts = [start]
    cur = start
    for s in segs:
        if s[0] == "L":
            pts.append(s[1])
        else:
            c, e = s[1], s[2]
            for k in range(1, QUAD_STEPS + 1):
                t = k / QUAD_STEPS
                pts.append(((1 - t) ** 2 * cur[0] + 2 * (1 - t) * t * c[0] + t * t * e[0],
                            (1 - t) ** 2 * cur[1] + 2 * (1 - t) * t * c[1] + t * t * e[1]))
        cur = s[-1]
    return pts


def poly_area(p):
    return sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p))) / 2


def poly_len(p):
    return sum(math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) for i in range(len(p)))


def rasterize(polys, x0, y0, scale, w, h):
    """Nonzero-winding fill of polygons (font units, y up) into a w×h grid; row 0 is the top."""
    edges = []
    for p in polys:
        for i in range(len(p)):
            (ax, ay), (bx, by) = p[i - 1], p[i]
            if ay != by:
                edges.append((ax, ay, bx, by, 1 if by > ay else -1))
    grid = [[0] * w for _ in range(h)]
    for r in range(h):
        y = y0 - (r + 0.5) / scale
        xs = []
        for ax, ay, bx, by, wd in edges:
            if (ay <= y < by) or (by <= y < ay):
                xs.append((ax + (y - ay) * (bx - ax) / (by - ay), wd))
        xs.sort()
        wind = 0
        for k in range(len(xs) - 1):
            wind += xs[k][1]
            if wind:
                c0 = max(0, int(math.ceil((xs[k][0] - x0) * scale - 0.5)))
                c1 = min(w - 1, int(math.floor((xs[k + 1][0] - x0) * scale - 0.5)))
                for c in range(c0, c1 + 1):
                    grid[r][c] = 1
    return grid


def thin(grid):
    """Zhang-Suen thinning in place."""
    h, w = len(grid), len(grid[0])
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            kill = []
            for r in range(1, h - 1):
                row = grid[r]
                for c in range(1, w - 1):
                    if not row[c]:
                        continue
                    p2, p3, p4 = grid[r - 1][c], grid[r - 1][c + 1], grid[r][c + 1]
                    p5, p6, p7 = grid[r + 1][c + 1], grid[r + 1][c], grid[r + 1][c - 1]
                    p8, p9 = grid[r][c - 1], grid[r - 1][c - 1]
                    nb = (p2, p3, p4, p5, p6, p7, p8, p9)
                    b = sum(nb)
                    if b < 2 or b > 6:
                        continue
                    a = sum(1 for i in range(8) if not nb[i] and nb[(i + 1) % 8])
                    if a != 1:
                        continue
                    if step == 0 and (p2 * p4 * p6 or p4 * p6 * p8):
                        continue
                    if step == 1 and (p2 * p4 * p8 or p2 * p6 * p8):
                        continue
                    kill.append((r, c))
            for r, c in kill:
                grid[r][c] = 0
            changed = changed or bool(kill)
    return grid


N8 = [(-1, 0), (0, 1), (1, 0), (0, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)]


def trace(grid):
    """Skeleton pixels → polylines (lists of (r, c)); loops close on their first point."""
    px = {(r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if v}
    nb = {p: [(p[0] + dr, p[1] + dc) for dr, dc in N8 if (p[0] + dr, p[1] + dc) in px] for p in px}
    # drop diagonal links that a 4-neighbour pair already bridges, so corners do not read as junctions
    for p in px:
        keep = []
        for q in nb[p]:
            if q[0] != p[0] and q[1] != p[1]:
                if (p[0], q[1]) in px or (q[0], p[1]) in px:
                    continue
            keep.append(q)
        nb[p] = keep
    nodes = {p for p in px if len(nb[p]) != 2}
    seen = set()
    lines = []

    def walk(a, b):
        path = [a, b]
        seen.add(frozenset((a, b)))
        prev, cur = a, b
        while cur not in nodes:
            nxt = [q for q in nb[cur] if q != prev and frozenset((cur, q)) not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(frozenset((prev, cur)))
            path.append(cur)
            if cur == a:
                break
        return path

    for n in sorted(nodes):
        for q in nb[n]:
            if frozenset((n, q)) not in seen:
                lines.append(walk(n, q))
    for p in sorted(px):
        for q in nb[p]:
            if frozenset((p, q)) not in seen:
                lines.append(walk(p, q))
    return lines, nb


def prune_and_merge(lines, nb, min_len):
    deg = lambda p: len(nb[p])
    changed = True
    while changed:
        changed = False
        ends = {}
        for i, l in enumerate(lines):
            for e in (l[0], l[-1]):
                ends.setdefault(e, []).append(i)
        drop = set()
        for i, l in enumerate(lines):
            if l[0] == l[-1]:
                continue
            free = [e for e in (l[0], l[-1]) if len(ends[e]) == 1]
            if len(free) == 1 and len(l) < min_len and len(ends[[e for e in (l[0], l[-1]) if e not in free][0]]) >= 3:
                drop.add(i)
        if drop:
            lines = [l for i, l in enumerate(lines) if i not in drop]
            changed = True
            continue
        # join pairs of lines meeting at a point no third line touches
        for e, ids in ends.items():
            if len(ids) == 2 and ids[0] != ids[1]:
                a, b = lines[ids[0]], lines[ids[1]]
                if a[-1] != e:
                    a = a[::-1]
                if b[0] != e:
                    b = b[::-1]
                lines = [l for i, l in enumerate(lines) if i not in ids] + [a + b[1:]]
                changed = True
                break
    return [l for l in lines if len(l) >= 2]


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    (ax, ay), (bx, by) = pts[0], pts[-1]
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    best, idx = -1, 0
    for i in range(1, len(pts) - 1):
        px, py = pts[i]
        d = abs(dy * (px - ax) - dx * (py - ay)) / L if L else math.hypot(px - ax, py - ay)
        if d > best:
            best, idx = d, i
    if best > eps:
        return rdp(pts[:idx + 1], eps)[:-1] + rdp(pts[idx:], eps)
    return [pts[0], pts[-1]]


def glyph_data(font, ch):
    g = font.cmap.get(ord(ch))
    if g is None:
        return None
    adv = font.advance(g)
    raw = font.contours(g)
    conts = [segments(c) for c in raw]
    flat = [flatten(s, segs) for s, segs in conts]
    if not flat:
        return {"a": adv, "c": [], "s": [], "d": [], "w": 0}
    area = abs(sum(poly_area(p) for p in flat))
    per = sum(poly_len(p) for p in flat)
    w = 2 * area / per if per else 0  # stroke thickness, font units
    # dots: outer contours whose box is no wider than a couple of strokes
    dots = []
    for i, p in enumerate(flat):
        xs, ys = [q[0] for q in p], [q[1] for q in p]
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        if span <= 2.3 * w:
            inside_other = any(j != i and point_in(p[0], flat[j]) for j in range(len(flat)))
            if not inside_other:
                dots.append(i)
    body = [p for i, p in enumerate(flat) if i not in dots]
    strokes = []
    if body:
        scale = PX_PER_STROKE / w
        xs = [q[0] for p in body for q in p]
        ys = [q[1] for p in body for q in p]
        x0, y1 = min(xs) - 2 / scale, max(ys) + 2 / scale
        W = int((max(xs) - min(xs)) * scale) + 5
        H = int((max(ys) - min(ys)) * scale) + 5
        grid = thin(rasterize(body, x0, y1, scale, W, H))
        lines, nb = trace(grid)
        lines = prune_and_merge(lines, nb, 1.4 * PX_PER_STROKE)
        for l in lines:
            pts = [((c + 0.5) / scale + x0, font.asc - (y1 - (r + 0.5) / scale)) for r, c in l]
            closed = l[0] == l[-1] and len(l) > 2
            pts = rdp(pts, 0.7 / scale)
            if poly_len(pts) - (0 if closed else 0) < 0.4 * w:
                continue
            if not closed and (pts[-1][0], pts[-1][1]) < (pts[0][0], pts[0][1]):
                pts = pts[::-1]  # draw from the left end
            strokes.append(pts)
    out_c = []
    for (s, segs) in conts:
        flip = lambda q: (round(q[0]), round(font.asc - q[1]))
        arr = list(flip(s))
        for sg in segs:
            if sg[0] == "L":
                arr += [0, *flip(sg[1])]
            else:
                arr += [1, *flip(sg[1]), *flip(sg[2])]
        out_c.append(arr)
    return {
        "a": adv,
        "c": out_c,
        "s": [[round(v) for q in st for v in q] for st in strokes],
        "d": dots,
        "w": round(w),
    }


def point_in(pt, poly):
    x, y = pt
    inside = False
    for i in range(len(poly)):
        (ax, ay), (bx, by) = poly[i - 1], poly[i]
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            inside = not inside
    return inside


def main():
    font = Font(FONT)
    glyphs = {}
    for ch in CHARS:
        gd = glyph_data(font, ch)
        if gd is not None:
            glyphs[ch] = gd
            if "--report" in sys.argv:
                print(repr(ch), "contours", len(gd["c"]), "strokes", len(gd["s"]), "dots", gd["d"], "w", gd["w"])
    import json
    body = json.dumps(glyphs, ensure_ascii=False, separators=(",", ":"))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("// GENERATED by ui-v2/scripts/gen_alnst_strokes.py from alnst-400-normal.ttf; do not edit by hand.\n")
        f.write("// Per glyph: a = advance, c = outline contours ([x, y] then 0,x,y line or 1,cx,cy,x,y quad),\n")
        f.write("// s = centre-line polylines, d = indices of contours that are dots, w = stroke thickness.\n")
        f.write("// Font units, y down from the ascender.\n")
        f.write(f"export const UPM = {font.upm};\n")
        f.write(f"export const HEIGHT = {font.asc - font.desc};\n")
        f.write(f"export const GLYPHS = {body};\n")
    print("wrote", OUT, len(glyphs), "glyphs", os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
