"""Parametric weapon parts, all in socket space (see wpn_common): blades and other flat-section pieces with real
cross-sections (bevelled edges, fullers, midribs), guards, grips, pommels, hafts, flanged and spiked heads, and the
rune inlays an enchanted copy carries. Each lays out its own UVs as it is built.
"""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix
from wpn_common import (uv_layer, rune_layer, set_uvs, grid_faces, cap_face, loft, ellipsoid, cone, box, torus, slab,
                        prism, spline, remove_obj, smoothstep, lerp)


class Builder:
    """One weapon's mesh while it is built: parts with their painted materials, plus notes for the game
    (string tips, missile rest...) in `meta`."""

    def __init__(self, magic=False):
        self.bm = bmesh.new()
        uv_layer(self.bm)
        rune_layer(self.bm)
        self.mats = []
        self.meta = {}
        self.magic = magic

    def part(self, mat, fn, *a, **k):
        n0 = len(self.bm.faces)
        r = fn(self.bm, *a, **k)
        self.bm.faces.ensure_lookup_table()
        if mat not in self.mats:
            self.mats.append(mat)
        mi = self.mats.index(mat)
        for f in self.bm.faces[n0:]:
            f.material_index = mi
        return r

    def transform(self, M):
        bmesh.ops.transform(self.bm, matrix=M, verts=self.bm.verts[:])


# ----------------------------------------------------------------------------------------- flat sections
def _side(e, sgn, style, h, bev):
    """Three points (top, middle, bottom) of one in-plane side of a section; sgn +1 for the high side."""
    if style == 'edge':
        return (e - sgn * bev, h), (e, 0.0), (e - sgn * bev, -h)
    if style == 'spine':
        return (e, h), (e + sgn * h * 0.45, 0.0), (e, -h)
    return (e, h), (e, 0.0), (e, -h)                    # 'flat'


def section(lo, hi, t, fw=0.0, fd=0.0, bev=0.006, styles=('edge', 'edge'), c=None):
    """14-point ring in (in-plane, thickness) for a flat piece between lo and hi, thickness t, with a fuller of
    half-width fw and depth fd down its middle on both faces (fd < 0 raises a midrib instead)."""
    h = max(t / 2, 0.0002)
    c = (lo + hi) / 2 if c is None else c
    w = (hi - lo) / 2
    bev = max(0.0, min(bev, w * 0.92))
    room = min(hi - (bev if styles[1] == 'edge' else 0) - c, c - (lo + (bev if styles[0] == 'edge' else 0))) - 0.0008
    fw = max(0.0, min(fw, room))
    fd = min(fd, h * 0.6)
    hiT, hiM, hiB = _side(hi, 1, styles[1], h, bev)
    loT, loM, loB = _side(lo, -1, styles[0], h, bev)
    top = [(c + fw, h), (c + fw * 0.5, h - fd), (c - fw * 0.5, h - fd), (c - fw, h)]
    bot = [(c - fw, -h), (c - fw * 0.5, -h + fd), (c + fw * 0.5, -h + fd), (c + fw, -h)]
    return [hiM, hiT] + top + [loT, loM, loB] + bot + [hiB]


def sheet(bm, rows, axis='Y', styles=('edge', 'edge'), bev=0.006, per_seg=2, cap0=True, cap1=True, z=0.0):
    """A flat piece lofted along `axis` ('Y': a blade, in-plane X; 'X': an axe head, in-plane Y) through rows
    (s, lo, hi, t[, fw, fd]). Returns the spline rows (for rune inlays)."""
    R = []
    for r in rows:
        r = list(r) + [0.0] * (6 - len(r))
        R.append(r)
    R = spline(R, per_seg)
    R[:, 3] = np.maximum(R[:, 3], 0.0006)
    R[:, 2] = np.maximum(R[:, 2], R[:, 1] + 0.0006)
    rings = []
    for s, lo, hi, t, fw, fd in R:
        pts = section(lo, hi, t, fw, fd, bev, styles)
        if axis == 'Y':
            rings.append([bm.verts.new(Vector((p, s, z + q))) for p, q in pts])
        else:
            rings.append([bm.verts.new(Vector((s, p, z + q))) for p, q in pts])
    grid_faces(bm, rings, close_j=True)
    if cap0:
        cap_face(bm, rings[0][::-1])
    if cap1:
        cap_face(bm, rings[-1])
    return R


def ribbon(bm, P, A, Nrm, thick=0.0004, rune=True):
    """A thin closed strip (an inlay): centre points P, half-width vectors A, outward normals Nrm (n x 3). Its top
    face carries the glyph strip in the "Rune" UV layer: u = metres along, v = 0..1 across."""
    rl = rune_layer(bm)
    rows = []
    for p, a, n in zip(P, A, Nrm):
        p, a, n = Vector(p), Vector(a), Vector(n).normalized()
        rows.append([bm.verts.new(p - a - n * thick), bm.verts.new(p + a - n * thick),
                     bm.verts.new(p + a + n * thick), bm.verts.new(p - a + n * thick)])
    faces, U, vv = grid_faces(bm, rows, close_j=True)
    cap_face(bm, rows[0][::-1])
    cap_face(bm, rows[-1])
    if rune:
        s = [0.0]
        for i in range(1, len(P)):
            s.append(s[-1] + (Vector(P[i]) - Vector(P[i - 1])).length)
        J = 4
        for i in range(len(rows) - 1):                  # the top face of each segment is index j = 2 (verts 2 -> 3)
            f = faces[i * J + 2]
            set_uvs(f, rl, ((s[i], 1.0), (s[i], 0.0), (s[i + 1], 0.0), (s[i + 1], 1.0)))


def fuller_runes(b, R, y0, y1, frac=0.42, axis='Y'):
    """Rune inlays on the floor of a blade's fuller, both faces, between y0 and y1 (rows from `sheet`)."""
    sel = [r for r in R if y0 <= r[0] <= y1 and r[4] > 0.002]
    if len(sel) < 2:
        return
    for sg in (1, -1):
        P, A, N = [], [], []
        for s, lo, hi, t, fw, fd in sel:
            c = (lo + hi) / 2
            zz = sg * (t / 2 - min(fd, t * 0.3))
            if axis == 'Y':
                P.append((c, s, zz)); A.append((fw * frac, 0, 0))
            else:
                P.append((s, c, zz)); A.append((0, fw * frac, 0))
            N.append((0, 0, sg))
        b.part('rune', ribbon, P, A, N)


def _row_at(R, s):
    """The sheet's section row at s (linear between the spline rows; R runs in increasing s)."""
    S = R[:, 0]
    i = int(np.clip(np.searchsorted(S, s), 1, len(S) - 1))
    t = 0.0 if S[i] == S[i - 1] else (s - S[i - 1]) / (S[i] - S[i - 1])
    return R[i - 1] + (R[i] - R[i - 1]) * min(1.0, max(0.0, t))


def sheet_runes(b, R, pts, half, axis='Y'):
    """A rune inlay on both faces of a flat piece (rows R from `sheet`) through points [(s, at)]: s along the
    sheet's axis, `at` 0..1 across it from lo to hi. It lies on the surface there (a fuller's floor, a midrib's
    top), whatever the taper."""
    for sg in (1, -1):
        P, A, N = [], [], []
        for s, at in pts:
            _, lo, hi, t, fw, fd = _row_at(R, s)
            c = (lo + hi) / 2
            p = lerp(lo, hi, at)
            z = t / 2
            if fw > 0.0015 and abs(p - c) < fw * 0.5:
                z = t / 2 - fd
            P.append(Vector((p, s, sg * z)) if axis == 'Y' else Vector((s, p, sg * z)))
            N.append(Vector((0, 0, sg)))
        for k in range(len(P)):                          # across the path, in the face
            tg = (P[min(k + 1, len(P) - 1)] - P[max(k - 1, 0)]).normalized()
            A.append(N[k].cross(tg).normalized() * half)
        b.part('rune', ribbon, P, A, N)


def shaft_runes(b, y0, y1, r, turns=0.0, half=0.004, n=10, phase=0.0):
    """A rune inlay running up a round shaft of radius r (a spiral when turns > 0), facing outward."""
    P, A, N = [], [], []
    for k in range(n + 1):
        t = k / n
        y = lerp(y0, y1, t)
        a = phase + turns * 2 * math.pi * t
        d = Vector((math.cos(a), 0, math.sin(a)))
        P.append(tuple(d * r + Vector((0, y, 0))))
        A.append(tuple(Vector((0, 1, 0)).cross(d) * half))
        N.append(tuple(d))
    b.part('rune', ribbon, P, A, N)


# ----------------------------------------------------------------------------------------- blades
def blade(b, mat, length, width, base=0.06, thick=0.0065, taper=0.55, tip=0.14, fuller=0.55, fw=0.007, fd=0.0012,
          single=False, curve=0.0, belly=0.0, bev=0.007, ricasso=0.0, runes=True, wave=None):
    """A sword or dagger blade from y = base up `length`: width at the base, `taper` of it left before the tip
    starts `tip` from the end; a fuller down `fuller` of the length; `single` = one edge (+X) and a spine (-X);
    `curve` bends the blade toward -X (a sabre's back curve); `belly` swells the edge near the tip (a falchion);
    wave = (amplitude, cycles, from u): a flamberge's snaking edges."""
    rows = []
    tip_u = 1 - tip / length
    us = [0.0, 0.12, 0.28, 0.44, 0.6] + [tip_u * 0.88, tip_u] + [lerp(tip_u, 1.0, v) for v in (0.35, 0.65, 0.88, 1.0)]
    if wave:
        us += [lerp(wave[2], tip_u, k / (wave[1] * 4)) for k in range(int(wave[1] * 4) + 1)]
    us = sorted(set(round(min(u, 1.0), 5) for u in us))
    w_end = width * taper * (1 + belly)
    for u in us:
        y = base + length * u
        wb = lerp(width, width * taper, min(1.0, u / tip_u))      # the width without the belly
        if u <= tip_u:
            w = wb * (1 + belly * smoothstep(0.25, 1.0, u / tip_u))
        else:
            v = (u - tip_u) / (1 - tip_u)
            w = w_end * max(0.0, 1 - v ** 1.7) ** 0.65             # an ogive into the point
        t = thick * lerp(1.0, 0.5, u) if u < 1 else 0.0008
        f = fw if u < fuller else fw * max(0.0, 1 - (u - fuller) / 0.12)
        if u * length < ricasso:
            f = 0.0
        off = -curve * length * (u ** 2)
        if wave and wave[2] < u < tip_u:                 # both edges swing together, dying out into the point
            k = (u - wave[2]) / (tip_u - wave[2])
            off += wave[0] * math.sin(2 * math.pi * wave[1] * k) * min(1.0, k * 6) * (1 - 0.5 * k)
        if single:                                       # the spine runs on straight; the edge sweeps up to it
            lo = off - wb * 0.42
            hi = lo + max(w, 0.001)
        else:
            lo, hi = off - w / 2, off + w / 2
            if u >= 1.0:
                lo, hi = off - 0.0005, off + 0.0005
        rows.append((y, lo, hi, t, f, fd))
    R = b.part(mat, sheet, rows, 'Y', ('spine' if single else 'edge', 'edge'), bev, 2 if (curve or belly) else 1)
    if b.magic and runes and fw > 0:
        fuller_runes(b, R, base + length * 0.04, base + length * fuller * 0.95)
    return R


# ----------------------------------------------------------------------------------------- hilts
def crossguard(b, mat, y, half, r=0.007, thick=0.012, curve=0.0, flare=1.3, block=1.5, seg=8, finial=None):
    """A cross bar along X at y: `curve` bends the arms toward the blade (+) or the hand (-); `flare` widens the
    ends; `block` thickens the middle round the blade; finial = (mat, radius) balls on the ends."""
    xs = np.linspace(-half, half, 7)
    rows = []
    for x in xs:
        u = abs(x) / half
        rr = r * lerp(block, 1.0, smoothstep(0, 0.35, u)) * lerp(1.0, flare, smoothstep(0.6, 1.0, u))
        rows.append((x, y + curve * u * u, 0.0, thick / 2 * lerp(block, 1.0, smoothstep(0, 0.35, u)), rr, rr))
    b.part(mat, loft, rows, up=(0, 1, 0), seg=seg, per_seg=2, cap0=0.6, cap1=0.6)
    if finial:
        for sg in (1, -1):
            b.part(finial[0], ellipsoid, (sg * (half + finial[1] * 0.6), y + curve, 0), (finial[1],) * 3, None, 8, 6)


def grip(b, mat, y0, y1, r=0.0145, ridges=5, flat=0.82, seg=8, wire=None, swell=0.08):
    """A wrapped grip from y0 to y1: oval (narrower across the flat), a slight swell in the middle, leather wrap
    ridges; wire = (mat, count) adds wire rings."""
    rows = []
    n = max(2, ridges * 2)
    for k in range(n + 1):
        u = k / n
        y = lerp(y0, y1, u)
        rr = r * (1 + swell * math.sin(math.pi * u)) * (1.0 + (0.045 if k % 2 else 0.0))
        rows.append((0, y, 0, rr, rr * flat, rr * flat))
    b.part(mat, loft, rows, up=(0, 0, 1), seg=seg, per_seg=1, cap0=0.2, cap1=0.2)
    if wire:
        for y in np.linspace(y0 + 0.008, y1 - 0.008, wire[1]):
            rr = r * (1 + swell * math.sin(math.pi * (y - y0) / (y1 - y0))) * 1.06
            b.part(wire[0], loft, [(0, y - 0.0025, 0, rr, rr * flat, rr * flat), (0, y + 0.0025, 0, rr, rr * flat, rr * flat)],
                   up=(0, 0, 1), seg=seg, per_seg=1, cap0=0.3, cap1=0.3)


def collar(b, mat, y, r, h=0.008, seg=8, flat=0.85):
    b.part(mat, loft, [(0, y - h / 2, 0, r, r * flat, r * flat), (0, y + h / 2, 0, r, r * flat, r * flat)], up=(0, 0, 1),
           seg=seg, per_seg=1, cap0=0.3, cap1=0.3)


def pommel(b, mat, y, kind='wheel', r=0.022, gem=None, seg=10):
    """A pommel centred at y (below the grip): 'wheel' (a disc, faces +-Z), 'ball', 'pear' (scent stopper),
    'cap' (a rounded cap), 'ring', 'faceted'; gem = material of a stone set in both faces (wheel) or on top."""
    if kind == 'wheel':
        th = r * 0.55
        b.part(mat, loft, [(0, y, z, r, r, r) for z in (-th / 2, 0, th / 2)], up=(0, 1, 0), seg=seg, per_seg=1,
               cap0=0.25, cap1=0.25)
        b.part(mat, loft, [(0, y + r * 0.8, 0, r * 0.32, r * 0.32, r * 0.32), (0, y + r * 1.15, 0, r * 0.3, r * 0.3, r * 0.3)],
               up=(0, 0, 1), seg=8, per_seg=1, cap0=0.3, cap1=0.3)               # the tang's neck
        if gem:                                          # proud of the disc's domed faces
            for sg in (1, -1):
                b.part(gem, ellipsoid, (0, y, sg * (th / 2 + r * 0.25 - 0.0015)), (r * 0.4, r * 0.4, r * 0.2), None, 8, 5)
    elif kind == 'ball':
        b.part(mat, ellipsoid, (0, y, 0), (r, r * 0.9, r), None, seg, 7)
        if gem:
            b.part(gem, ellipsoid, (0, y - r * 0.85, 0), (r * 0.4, r * 0.35, r * 0.4), None, 8, 5)
    elif kind == 'pear':
        b.part(mat, loft, [(0, y + r * 0.9, 0, r * 0.45, r * 0.45, r * 0.45), (0, y + r * 0.3, 0, r * 0.85, r * 0.85, r * 0.85),
                           (0, y - r * 0.4, 0, r, r, r), (0, y - r * 1.1, 0, r * 0.55, r * 0.55, r * 0.55)],
               up=(0, 0, 1), seg=seg, per_seg=2, cap0=0.5, cap1=0.7, shape=1.0)
        if gem:
            b.part(gem, ellipsoid, (0, y - r * 1.25, 0), (r * 0.38, r * 0.3, r * 0.38), None, 8, 5)
    elif kind == 'faceted':
        b.part(mat, loft, [(0, y + r * 0.7, 0, r * 0.5, r * 0.5, r * 0.5), (0, y, 0, r, r, r), (0, y - r * 0.8, 0, r * 0.45, r * 0.45, r * 0.45)],
               up=(0, 0, 1), seg=6, per_seg=1, cap0=0.4, cap1=0.6, shape=1.0)
        if gem:
            b.part(gem, ellipsoid, (0, y - r * 0.95, 0), (r * 0.35, r * 0.3, r * 0.35), None, 6, 4)
    elif kind == 'ring':
        b.part(mat, torus, (0, y - r * 0.6, 0), (0, 0, 1), r * 0.75, r * 0.25, 10, 5)
    else:                                               # 'cap'
        b.part(mat, loft, [(0, y + r * 0.5, 0, r * 0.8, r * 0.8, r * 0.8), (0, y - r * 0.2, 0, r, r, r)], up=(0, 0, 1),
               seg=seg, per_seg=1, cap0=0.2, cap1=0.9)


# ----------------------------------------------------------------------------------------- hafted
def haft(b, mat, y0, y1, r0=0.016, r1=0.014, seg=8, flat=0.9, wobble=0.0, seed=0):
    rng = np.random.default_rng(seed)
    ys = np.linspace(y0, y1, max(3, int((y1 - y0) / 0.25) + 2))
    rows = []
    for k, y in enumerate(ys):
        u = (y - y0) / (y1 - y0)
        r = lerp(r0, r1, u)
        rows.append((wobble * math.sin(y * 7 + seed) + (rng.uniform(-1, 1) * wobble * 0.3 if 0 < k < len(ys) - 1 else 0),
                     y, 0, r, r * flat, r * flat))
    b.part(mat, loft, rows, up=(0, 0, 1), seg=seg, per_seg=2, cap0=0.3, cap1=0.3)


def rings(b, mat, ys, r, h=0.012, seg=8):
    for y in ys:
        collar(b, mat, y, r, h, seg, 1.0)


def langets(b, mat, y0, y1, r, w=0.012, t=0.003, n=2):
    """Iron strips nailed down the haft below a head (they keep it on), n round the shaft."""
    for k in range(n):
        a = k * 2 * math.pi / n + math.pi / 2
        d = Vector((math.cos(a), 0, math.sin(a)))
        rot = Matrix.Rotation(-a, 3, 'Y')
        b.part(mat, box, tuple(d * (r + t / 2) + Vector((0, (y0 + y1) / 2, 0))), (t, y1 - y0, w), rot)
        for y in (y0 + 0.012, (y0 + y1) / 2, y1 - 0.01):
            b.part(mat, ellipsoid, tuple(d * (r + t) + Vector((0, y, 0))), (0.0032,) * 3, None, 6, 3)


def butt_cap(b, mat, y, r, length=0.035, spike=False):
    if spike:
        b.part(mat, cone, (0, y + 0.01, 0), (0, y - length, 0), r * 1.05, 0.002, 8)
    else:
        b.part(mat, loft, [(0, y + length * 0.6, 0, r * 1.08, r * 1.08, r * 1.08), (0, y, 0, r * 1.12, r * 1.12, r * 1.12)],
               up=(0, 0, 1), seg=8, per_seg=1, cap0=0.2, cap1=0.5)


def flanges(b, mat, y0, y1, r_in, r_out, n=6, t=0.006, shape='round', phase=0.0):
    """A flanged mace head: n plates radiating round the haft between y0 and y1 (outline by `shape`)."""
    h = y1 - y0
    if shape == 'gothic':                               # pointed, notched flanges
        out = [(r_in, 0.0), (r_out * 0.75, 0.12 * h), (r_out, 0.45 * h), (r_out * 0.86, 0.55 * h), (r_out * 0.95, 0.72 * h),
               (r_in * 1.1, h * 1.02), (r_in, h)]
    elif shape == 'square':
        out = [(r_in, 0.0), (r_out * 0.8, 0.08 * h), (r_out, 0.3 * h), (r_out, 0.82 * h), (r_out * 0.75, h), (r_in, h)]
    else:
        out = [(r_in, 0.0), (r_out * 0.7, 0.1 * h), (r_out, 0.4 * h), (r_out * 0.92, 0.75 * h), (r_out * 0.55, 0.97 * h), (r_in, h)]
    out = [(x, y + y0) for x, y in out]
    for k in range(n):
        a = phase + k * 2 * math.pi / n
        b.part(mat, slab, out, Matrix.Rotation(a, 4, 'Y'), -t / 2, t / 2)


def spikes(b, mat, center, r, n=10, length=0.03, base=0.008, seed=3, cap=True):
    """Spikes out of a ball of radius r (a morning star): evenly spread (Fibonacci), plus one on top."""
    c = Vector(center)
    golden = math.pi * (3 - math.sqrt(5))
    for k in range(n):
        yv = 1 - 2 * (k + 0.5) / n
        rr = math.sqrt(max(0.0, 1 - yv * yv))
        a = golden * k + seed
        d = Vector((math.cos(a) * rr, yv, math.sin(a) * rr))
        if d.y < -0.75:                                 # none where the haft goes in
            continue
        b.part(mat, cone, c + d * (r * 0.85), c + d * (r + length), base, 0.0, 6)
    if cap:
        b.part(mat, cone, c + Vector((0, r * 0.85, 0)), c + Vector((0, r + length * 1.2, 0)), base * 1.1, 0.0, 6)


def rounded_block(b, mat, center, size, axis='X', shape=0.55, seg=8, bulge=0.0):
    """A hammer head: a squarish loft along `axis` (size = length along the axis, then the two other sides)."""
    cx, cy, cz = center
    L, s1, s2 = size
    rows = []
    for u in (-0.5, -0.42, 0.0, 0.42, 0.5):
        k = 1.0 + bulge * (1 - abs(u) * 2)
        f = 0.88 if abs(u) == 0.5 else 1.0
        if axis == 'X':
            rows.append((cx + u * L, cy, cz, s2 / 2 * k * f, s1 / 2 * k * f, s1 / 2 * k * f))
        else:
            rows.append((cx, cy + u * L, cz, s1 / 2 * k * f, s2 / 2 * k * f, s2 / 2 * k * f))
    up = (0, 1, 0) if axis == 'X' else (0, 0, 1)
    b.part(mat, loft, rows, up=up, seg=seg, per_seg=1, cap0=0.15, cap1=0.15, shape=shape)


# ----------------------------------------------------------------------------------------- gems and crystals
def gem(b, mat, center, size, facing=(0, 0, 1)):
    f = Vector(facing).normalized()
    rot = f.to_track_quat('Z', 'Y').to_matrix()
    b.part(mat, ellipsoid, center, (size, size, size * 0.55), rot, 8, 5)


def crystal(b, mat, base, tip, r, sides=6):
    """A pointed crystal from base to tip (a hexagonal prism with a point)."""
    base, tip = Vector(base), Vector(tip)
    d = tip - base
    mid = base + d * 0.7
    b.part(mat, cone, base - d.normalized() * r * 0.6, mid, r * 0.7, r, sides)
    b.part(mat, cone, mid, tip, r, 0.0, sides)
