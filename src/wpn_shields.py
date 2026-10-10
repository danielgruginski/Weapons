"""Shields: a buckler, the heater, the kite, the tower shield and the knight's shield, enchanted copies of four of them
and Sunguard. Built like the weapons (wpn_parts.Builder, the painted source materials of wpn_mats, UVs laid out as they
are built) but baked to an atlas of their own (T_Shields): their big painted faces would starve the weapons' atlas.

    import wpn_shields; wpn_shields.build_all()

Frame (the Humans Socket_Shield's, in Blender's axes): the origin is where the forearm crosses the shield's back (the
socket sits 6 cm out over the back of the left forearm); +Y out of the face; Z along the forearm, +Z toward the hand;
X up the shield. Unity mirrors X on import (Blender +X = Unity -X), so there the face is +Y and the forearm +Z, as on
Socket_Shield, and the shield's top is -X; the game turns the prop with ShieldDefinition.rotation.

A shield is a Shape: its outline in (u up, v across) and its curve (the back at w = -ku (u - uc)^2 - kv v^2, the face
a board's thickness out from it). Parts follow the face: the rim rolled over the edge, the boss, iron bands, the rune
ring of an enchanted copy, the straps round the forearm at the back.
"""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix
import wpn_mats
from wpn_common import uv_layer, grid_faces, ellipsoid, box, torus, loft, lerp, get_coll, remove_obj
from wpn_parts import Builder, ribbon

COLL = "WPN_Shields"


# ----------------------------------------------------------------------------------------- shapes
def _segments(segs, step):
    """Points along segments (functions t -> (u, v), t in 0..1, each ending where the next starts), sampled by their
    length, the corners between them kept."""
    pts = []
    for f in segs:
        n0 = 24
        length = sum(math.dist(f((k + 1) / n0), f(k / n0)) for k in range(n0))
        n = max(2, int(round(length / step)))
        pts += [f(k / n) for k in range(n)]
    return pts


def _arc_point(shoulder, point, h):
    """Radius and end angle of the arc from (shoulder, +-h) down to the point (point, 0), centred level with the
    shoulder on the far side: a heater's or a kite's lower edge."""
    R = ((point - shoulder) ** 2 + h * h) / (2 * h)
    return R, math.acos((R - h) / R)


def heater_outline(W=0.52, top=0.26, shoulder=0.05, point=-0.37, arch=0.012, step=0.035):
    """Flat-topped, straight sides, two arcs meeting in a point."""
    h = W / 2
    R, end = _arc_point(shoulder, point, h)
    return _segments([
        lambda t: (top + arch * (1 - lerp(h, -h, t) ** 2 / (h * h)), lerp(h, -h, t)),
        lambda t: (lerp(top, shoulder, t), -h),
        lambda t: (shoulder - R * math.sin(end * t), -(h - R + R * math.cos(end * t))),
        lambda t: (shoulder - R * math.sin(end * (1 - t)), h - R + R * math.cos(end * (1 - t))),
        lambda t: (lerp(shoulder, top, t), h),
    ], step)


def kite_outline(W=0.48, shoulder=0.07, crown=0.27, point=-0.66, step=0.035):
    """A rounded crown, widest at the shoulder, a long taper to the point."""
    h = W / 2
    R, end = _arc_point(shoulder, point, h)
    return _segments([
        lambda t: (shoulder + (crown - shoulder) * math.sin(math.pi * t), h * math.cos(math.pi * t)),
        lambda t: (shoulder - R * math.sin(end * t), -(h - R + R * math.cos(end * t))),
        lambda t: (shoulder - R * math.sin(end * (1 - t)), h - R + R * math.cos(end * (1 - t))),
    ], step)


def tower_outline(W=0.56, top=0.42, bottom=-0.62, r=0.05, step=0.05):
    """A tall rectangle with rounded corners."""
    h = W / 2

    def corner(cu, cv, a0):                               # a quarter turn about (cu, cv), the angle from +u toward +v
        return lambda t: (cu + r * math.cos(a0 - t * math.pi / 2), cv + r * math.sin(a0 - t * math.pi / 2))
    return _segments([
        lambda t: (top, lerp(h - r, -h + r, t)),
        corner(top - r, -h + r, 0.0),
        lambda t: (lerp(top - r, bottom + r, t), -h),
        corner(bottom + r, -h + r, -math.pi / 2),
        lambda t: (bottom, lerp(-h + r, h - r, t)),
        corner(bottom + r, h - r, math.pi),
        lambda t: (lerp(bottom + r, top - r, t), h),
        corner(top - r, h - r, math.pi / 2),
    ], step)


def round_outline(r, uc=0.0, n=40):
    return [(uc + r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]


class Shape:
    """A shield's outline (u up, v across), its curve and its thickness."""

    def __init__(self, outline, t=0.016, ku=0.0, kv=0.0, uc=0.0):
        self.O = np.asarray(outline, float)
        self.t, self.ku, self.kv, self.uc = t, ku, kv, uc
        self.c = self.O.mean(0)                           # what the face's rings shrink toward

    def back(self, u, v):
        return -self.ku * (u - self.uc) ** 2 - self.kv * v * v

    def front(self, u, v):
        return self.back(u, v) + self.t

    def at(self, u, v, lift=0.0):
        """The point on the face at (u, v), lifted off it along Y."""
        return Vector((u, self.front(u, v) + lift, v))

    def normal(self, u, v):
        return Vector((2 * self.ku * (u - self.uc), 1.0, 2 * self.kv * v)).normalized()

    def outward(self, i):
        """The outline's outward direction at point i, in (u, v)."""
        O = self.O
        tu, tv = O[(i + 1) % len(O)] - O[i - 1]
        d = np.array((tv, -tu)) / max(1e-9, math.hypot(tu, tv))
        return d if np.dot(d, O[i] - self.c) >= 0 else -d

    def inset(self, d):
        """The outline moved d in from the edge (convex outlines)."""
        return np.array([self.O[i] - self.outward(i) * d for i in range(len(self.O))])


# ----------------------------------------------------------------------------------------- parts (bmesh level)
def board_face(bm, S, side, scales=(1.0, 0.66, 0.33)):
    """One face of the board (side +1 the front, -1 the back): rings shrinking to the centre; planar UVs, the face as
    seen from its own side."""
    uvl = uv_layer(bm)
    rings = []
    for s in scales:
        rings.append([bm.verts.new(Vector((u, S.front(u, v) if side > 0 else S.back(u, v), v)))
                      for u, v in S.c + (S.O - S.c) * s])
    faces, _, _ = grid_faces(bm, rings, close_j=True)
    cu, cv = S.c
    ctr = bm.verts.new(Vector((cu, S.front(cu, cv) if side > 0 else S.back(cu, cv), cv)))
    last = rings[-1]
    for j in range(len(last)):
        faces.append(bm.faces.new((ctr, last[j], last[(j + 1) % len(last)])))
    for f in faces:
        for lp in f.loops:
            lp[uvl].uv = (side * lp.vert.co.z, lp.vert.co.x)


def board_edge(bm, S):
    front = [bm.verts.new(Vector((u, S.front(u, v), v))) for u, v in S.O]
    back = [bm.verts.new(Vector((u, S.back(u, v), v))) for u, v in S.O]
    grid_faces(bm, [front, back], close_j=True)


def rim_tube(bm, S, rr=0.0055, extra=0.0028, seg=5):
    """A metal rim rolled over the board's edge: a closed tube round the outline, centred mid-board."""
    rings = []
    for i, (u, v) in enumerate(S.O):
        out = S.outward(i)
        nrm = S.normal(u, v)
        o3 = Vector((out[0], 0.0, out[1]))
        o3 = (o3 - nrm * o3.dot(nrm)).normalized()
        mid = Vector((u, S.back(u, v) + S.t / 2, v))
        rings.append([bm.verts.new(mid + o3 * rr * math.cos(2 * math.pi * j / seg)
                                   + nrm * (S.t / 2 + extra) * math.sin(2 * math.pi * j / seg)) for j in range(seg)])
    grid_faces(bm, rings, close_j=True, close_i=True)


def dome_part(bm, S, center, radii, seg=10, rings=6):
    """An ellipsoid whose hidden half is pressed flat inside the board (it never shows through the back)."""
    uv_layer(bm)
    m = Matrix.Translation(Vector(center)) @ Matrix.Diagonal((radii[0], radii[1], radii[2], 1.0))
    made = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0, matrix=m, calc_uvs=True)
    for v in made['verts']:
        floor = S.back(v.co.x, v.co.z) + 0.0015
        if v.co.y < floor:
            v.co.y = floor


# ----------------------------------------------------------------------------------------- parts (Builder level)
def board(b, S, face, back='wood_plank', edge='wood_plank'):
    b.part(face, board_face, S, 1)
    b.part(back, board_face, S, -1)
    b.part(edge, board_edge, S)


def rim(b, mat, S, rr=0.0055, extra=0.0028, seg=5):
    b.part(mat, rim_tube, S, rr, extra, seg)


def boss(b, mat, S, u, v, r, h, seg=10):
    """A dome on the face (half of it sunk in the board)."""
    b.part(mat, dome_part, S, tuple(S.at(u, v, -h * 0.15)), (r, h, r), seg, 6)


def stone(b, S, u, v, r, collar='steel'):
    """An enchanted copy's crystal dome in a metal collar."""
    c = S.at(u, v)
    b.part('crystal', dome_part, S, tuple(c), (r, r * 0.55, r), 10, 6)
    b.part(collar, torus, tuple(c), tuple(S.normal(u, v)), r * 1.02, r * 0.2, 14, 5)


def band(b, mat, S, u, v0, v1, half=0.017, thick=0.0022, n=14):
    """An iron band across the face at u, from v0 to v1 (the curve of the board under it)."""
    vs = np.linspace(v0, v1, n)
    P = [S.at(u, v, thick) for v in vs]
    N = [S.normal(u, v) for v in vs]
    A = [Vector((half, 0.0, 0.0)) for _ in vs]
    b.part(mat, ribbon, P, A, N, thick, False)
    return vs


def rivets(b, mat, S, pts, r=0.0045):
    for u, v in pts:
        b.part(mat, ellipsoid, tuple(S.at(u, v, 0.0005)), (r, r * 0.6, r), None, 6, 3)


def rune_ring(b, S, inset=0.036, half=0.008):
    """The enchanted copy's band of runes round the face, inside the rim."""
    pts = list(S.inset(inset))
    pts.append(pts[0])
    P = [S.at(u, v, 0.0004) for u, v in pts]
    N = [S.normal(u, v) for u, v in pts]
    A = []
    for k in range(len(P)):
        tg = (P[min(k + 1, len(P) - 1)] - P[max(k - 1, 0)]).normalized()
        A.append(N[k].cross(tg).normalized() * half)
    b.part('rune', ribbon, P, A, N)


def band_runes(b, S, u, v0, v1, thick=0.0022, half=0.007, n=12):
    """Runes along the top of an iron band."""
    vs = np.linspace(v0, v1, n)
    P = [S.at(u, v, thick * 2 + 0.0004) for v in vs]
    N = [S.normal(u, v) for v in vs]
    A = [Vector((half, 0.0, 0.0)) for _ in vs]
    b.part('rune', ribbon, P, A, N)


def straps(b, S, vs=(0.075, -0.075), arm=-0.06, r=0.047, mat='leather_dark'):
    """The two enarmes: leather loops nailed to the back that the forearm passes through (its axis at w = arm)."""
    for v in vs:
        top = S.back(0.06, v)
        rows = [(0.056, top + 0.001, v), (0.05, arm + r * 0.55, v), (0.0, arm - r, v), (-0.05, arm + r * 0.55, v),
                (-0.056, S.back(-0.06, v) + 0.001, v)]
        b.part(mat, loft, [(x, y, z, 0.0022, 0.015, 0.015) for x, y, z in rows], up=(0, 0, 1), seg=4, per_seg=3,
               cap0=0, cap1=0, shape=0.35)
        for u in (0.056, -0.056):                        # the nails, on the back
            b.part('iron', ellipsoid, (u, S.back(u, v) - 0.001, v), (0.004, 0.0025, 0.004), None, 6, 3)


# ----------------------------------------------------------------------------------------- the shields
def buckler(magic=False):
    """Iron buckler: a small dished disc, a big boss, a raised ring, a rolled rim."""
    b = Builder(magic)
    S = Shape(round_outline(0.17, n=32), t=0.004, ku=1.15, kv=1.15)
    board(b, S, 'iron', 'iron', 'iron')
    rim(b, 'iron', S, rr=0.006, extra=0.004)
    b.part('iron', torus, (0, S.front(0.105, 0) + 0.001, 0), (0, 1, 0), 0.105, 0.0035, 24, 4)
    boss(b, 'iron', S, 0.0, 0.0, 0.058, 0.04, 12)
    rivets(b, 'iron', S, [(0.135 * math.cos(a), 0.135 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)])
    straps(b, S, vs=(0.05, -0.05), r=0.045)
    return b


def heater(magic=False):
    """Steel-rimmed heater: a board faced in painted leather, blue with a white chevron."""
    b = Builder(magic)
    S = Shape(heater_outline(), t=0.016, kv=0.6)
    board(b, S, 'her_heater')
    rim(b, 'steel', S)
    straps(b, S)
    if magic:
        rune_ring(b, S)
        stone(b, S, 0.13, 0.0, 0.026)
    return b


def kite(magic=False):
    """Kite shield: long, round-crowned, red with an ochre cross, an iron boss where the arms meet."""
    b = Builder(magic)
    S = Shape(kite_outline(), t=0.016, kv=0.8)
    board(b, S, 'her_kite')
    rim(b, 'steel', S)
    if magic:
        rune_ring(b, S)
        stone(b, S, 0.06, 0.0, 0.034)
    else:
        boss(b, 'steel', S, 0.06, 0.0, 0.05, 0.032)
    straps(b, S)
    return b


def tower(magic=False):
    """Tower shield: planks bound by two iron bands, a green pale down the middle, an iron boss, a heavy iron rim."""
    b = Builder(magic)
    S = Shape(tower_outline(), t=0.022, kv=1.25)
    board(b, S, 'her_tower', 'wood_plank', 'wood_plank')
    rim(b, 'iron', S, rr=0.0075, extra=0.0035)
    h = 0.28 - 0.004
    for u in (0.27, -0.42):
        band(b, 'iron', S, u, -h, h)
        rivets(b, 'iron', S, [(u, v) for v in (-0.2, -0.07, 0.07, 0.2)], 0.0055)
        if magic:
            band_runes(b, S, u, -h + 0.02, h - 0.02)
    if magic:
        stone(b, S, -0.06, 0.0, 0.04, 'iron')
    else:
        boss(b, 'iron', S, -0.06, 0.0, 0.062, 0.036)
    straps(b, S)
    return b


def knight_shield(magic=False):
    """The knight's shield: a heater quartered blue and gold, a gilt rim, gilt studs at the corners."""
    b = Builder(magic)
    S = Shape(heater_outline(W=0.54, top=0.27, point=-0.39), t=0.016, kv=0.6)
    board(b, S, 'her_knight', 'leather', 'leather')
    rim(b, 'gold', S, rr=0.006, extra=0.003)
    rivets(b, 'gold', S, [(0.23, 0.22), (0.23, -0.22), (0.23, 0.0)], 0.006)
    if magic:
        rune_ring(b, S, inset=0.038)
        stone(b, S, 0.0, 0.0, 0.03, 'gold')
    straps(b, S, mat='leather_red')
    return b


def sunguard(magic=True):
    """Sunguard, a blessed round shield: bright steel over oak, a gilt sun in relief round a crystal heart, a gilt rim,
    runes inside it."""
    b = Builder(True)
    S = Shape(round_outline(0.3, n=44), t=0.012, ku=0.5, kv=0.5)
    board(b, S, 'steel_fine', 'leather_dark', 'leather_dark')
    rim(b, 'gold', S, rr=0.0065, extra=0.003)
    b.part('gold', torus, (0, S.front(0.07, 0) + 0.002, 0), (0, 1, 0), 0.07, 0.006, 24, 5)
    for k in range(16):                                   # rays: tapering gilt strips over the dome, long and short
        a = 2 * math.pi * k / 16
        r1 = 0.215 if k % 2 == 0 else 0.15
        rs = np.linspace(0.082, r1, 6)
        P = [S.at(r * math.cos(a), r * math.sin(a), 0.0015) for r in rs]
        N = [S.normal(r * math.cos(a), r * math.sin(a)) for r in rs]
        side = Vector((-math.sin(a), 0.0, math.cos(a)))
        A = [side * lerp(0.016 if k % 2 == 0 else 0.011, 0.0012, (r - 0.082) / (r1 - 0.082)) for r in rs]
        b.part('gold', ribbon, P, A, N, 0.0015, False)
    stone(b, S, 0.0, 0.0, 0.052, 'gold')
    rune_ring(b, S, inset=0.034, half=0.008)
    straps(b, S)
    return b


# (name, builder, mode): mode as WEAPONS ('plain', 'both', 'rune')
SHIELDS = [
    ("Buckler", buckler, 'plain'),
    ("Heater", heater, 'both'),
    ("Kite", kite, 'both'),
    ("Tower", tower, 'both'),
    ("KnightShield", knight_shield, 'both'),
    ("Sunguard", sunguard, 'rune'),
]


# ----------------------------------------------------------------------------------------- build
def build_all(names=None):
    """Every shield into WPN_Shields (Shd_<Name>, Shd_<Name>_Rune) and a row of the Weapons catalog."""
    import wpn_build
    scn = wpn_build.scene()
    if bpy.context.window.scene != scn:
        bpy.context.window.scene = scn
    mats = wpn_mats.build_materials()
    coll = get_coll(COLL, scene=scn)
    built = []
    for name, fn, mode in SHIELDS:
        if names and name not in names:
            continue
        if mode in ('plain', 'both'):
            built.append(wpn_build.finish("Shd_" + name, fn(False), coll, mats, 'S'))
        if mode in ('both', 'rune'):
            built.append(wpn_build.finish("Shd_" + name + ("_Rune" if mode == 'both' else ""), fn(True), coll, mats, 'S'))
    coll.hide_viewport = False
    catalog(scn)
    return {o.name: wpn_build.tris(o) for o in built}


def catalog(scn, y=-0.9, gap=0.14):
    """The shields side by side under the weapons' rows, faces to the camera (-Y), tops up."""
    cat = get_coll("WPN_Catalog", scene=scn)
    for o in list(cat.objects):
        if o.name.startswith(("CAT_Shd_", "LBL_Shd_")):
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if isinstance(data, bpy.types.Curve) and data.users == 0:
                bpy.data.curves.remove(data)
    rows = [o.location.z for o in cat.objects if o.name.startswith("CAT_")]
    z0 = (min(rows) if rows else 0.0) - 1.6
    turn = Matrix(((0, 0, 1), (0, -1, 0), (1, 0, 0))).to_euler()   # X (up the shield) -> Z, the face (+Y) -> -Y
    coll = bpy.data.collections[COLL]
    x = 0.0
    for n, _, mode in SHIELDS:
        for nm in ("Shd_" + n, "Shd_" + n + "_Rune"):
            o = coll.objects.get(nm)
            if o is None:
                continue
            bb = [Vector(v) for v in o.bound_box]
            v0, v1 = min(v.z for v in bb), max(v.z for v in bb)
            c = bpy.data.objects.new("CAT_" + nm, o.data)
            cat.objects.link(c)
            c.rotation_euler = turn
            c.location = (x - v0, 0.0, z0)
            cu = bpy.data.curves.new("LBL_" + nm, 'FONT')
            cu.body = nm.replace("Shd_", "").replace("_Rune", "\n(rune)")
            cu.size = 0.035
            cu.align_x = 'CENTER'
            lbl = bpy.data.objects.new("LBL_" + nm, cu)
            lbl.location = (x + (v1 - v0) / 2, 0.0, z0 - 0.75)
            lbl.rotation_euler = (math.radians(90), 0, 0)
            cat.objects.link(lbl)
            x += (v1 - v0) + gap
    coll.hide_viewport = True
