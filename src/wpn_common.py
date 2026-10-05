"""Shared helpers for the weapon kit: lofted tubes, flat-section sheets, UVs laid out as parts are built.

Adapted from Goblins/src/gob_common.py and the builder primitives of gob_gear.py.

Socket space (every weapon is modelled in it, origin = where the fist closes):
    +Y along the handle toward the business end (blade, head, prod),
    +X the knuckles' side: a single edge faces +X, an axe's bit is on +X,
    +Z square to both (a blade's flat faces are +-Z).
Bows and crossbows are left-hand props (the goblin archer's convention): the bow's back faces -X.
"""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix

ROOT = r"E:\Unity\Projects\GameArtGeneration\Weapons"
CAPK = 3          # rings per rounded loft cap


def _cr(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def spline(ctrl, per_seg=4):
    """Uniform Catmull-Rom through the control rows (any number of columns)."""
    c = np.asarray(ctrl, float)
    if len(c) < 2 or per_seg <= 1:
        return c.copy()
    ext = np.vstack([2 * c[0] - c[1], c, 2 * c[-1] - c[-2]])
    out = []
    for i in range(len(c) - 1):
        for k in range(per_seg):
            out.append(_cr(ext[i], ext[i + 1], ext[i + 2], ext[i + 3], k / per_seg))
    out.append(c[-1])
    return np.array(out)


# ----------------------------------------------------------------------------------------- UVs
# Every building block lays out its own UVs as it is made, in metres (true scale), with its seams where the
# construction already has them. The bake only averages island scale and packs (no automatic unwrap).
def uv_layer(bm):
    return bm.loops.layers.uv.verify()


def rune_layer(bm):
    """Second UV layer: where the glyph strip lies on a rune inlay (u along it in metres, v 0..1 across). Zero on
    every other face."""
    lay = bm.loops.layers.uv.get("Rune")
    if lay is None:
        lay = bm.loops.layers.uv.new("Rune")
    return lay


def set_uvs(face, uvl, uvs):
    for loop, uv in zip(face.loops, uvs):
        loop[uvl].uv = uv


def _centre(verts):
    return sum((v.co for v in verts), Vector()) / len(verts)


def grid_faces(bm, V, close_j=False, close_i=False):
    """Quads between the rows V[i] (lists of BMVerts, same length), with UVs by edge length: u runs along each
    row (centred, so a tapering tube becomes a trapezoid), v across the rows. Closed directions get one seam.
    Returns (faces, u per row, v per row)."""
    uvl = uv_layer(bm)
    I, J = len(V), len(V[0])
    U = []
    for row in V:
        d = [0.0]
        for k in range(1, J):
            d.append(d[-1] + (row[k].co - row[k - 1].co).length)
        if close_j:
            d.append(d[-1] + (row[0].co - row[-1].co).length)
        U.append([x - d[-1] / 2 for x in d])
    vv = [0.0]
    for i in range(I if close_i else I - 1):
        a, b = V[i], V[(i + 1) % I]
        vv.append(vv[-1] + sum((b[j].co - a[j].co).length for j in range(J)) / J)
    faces = []
    for i in range(I if close_i else I - 1):
        i1 = (i + 1) % I
        Ua, Ub = U[i], U[i1]
        for j in range(J if close_j else J - 1):
            j1 = (j + 1) % J
            f = bm.faces.new((V[i][j], V[i][j1], V[i1][j1], V[i1][j]))
            set_uvs(f, uvl, ((Ua[j], vv[i]), (Ua[j + 1], vv[i]), (Ub[j + 1], vv[i + 1]), (Ub[j], vv[i + 1])))
            faces.append(f)
    return faces, U, vv


def cap_face(bm, verts, normal_hint=None):
    """Flat ngon over a closed ring of verts, UVs = its projection on its own plane (true size)."""
    uvl = uv_layer(bm)
    f = bm.faces.new(verts)
    f.normal_update()
    n = f.normal if f.normal.length > 1e-8 else Vector((0, 0, 1))
    t = n.orthogonal().normalized()
    b = n.cross(t)
    c = _centre(verts)
    set_uvs(f, uvl, [((v.co - c).dot(t), (v.co - c).dot(b)) for v in verts])
    return f


def fill_gutters(img, mask=None):
    """Fill every texel outside the UV islands with the colour of the nearest island (push-pull), so mip-maps
    never mix the black background into the edges. The islands are `mask` (h x w bool) or, without one, the
    texels a plain bake left with alpha 1. Leaves alpha at 1."""
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)
    m = (np.asarray(mask) if mask is not None else a[..., 3] > 0.5).astype(np.float32)

    def pushpull(col, wt):
        hh, ww = wt.shape
        if hh <= 1 and ww <= 1:
            return col
        h2, w2 = (hh + 1) // 2, (ww + 1) // 2
        cp = np.zeros((h2 * 2, w2 * 2, 3), np.float32)
        wp = np.zeros((h2 * 2, w2 * 2), np.float32)
        cp[:hh, :ww] = col * wt[..., None]
        wp[:hh, :ww] = wt
        cs = cp.reshape(h2, 2, w2, 2, 3).sum((1, 3))
        ws = wp.reshape(h2, 2, w2, 2).sum((1, 3))
        coarse = np.where(ws[..., None] > 0, cs / np.maximum(ws, 1e-6)[..., None], 0.0)
        coarse = pushpull(coarse, np.minimum(ws, 1.0))
        up = np.repeat(np.repeat(coarse, 2, 0), 2, 1)[:hh, :ww]
        return np.where(wt[..., None] > 0.5, col, up)

    a[..., :3] = pushpull(a[..., :3], m)
    a[..., 3] = 1.0
    img.pixels.foreach_set(a.ravel())
    return float(m.mean())


# ----------------------------------------------------------------------------------------- primitives
def loft(bm, rows, up=(0, 0, 1), seg=12, per_seg=3, cap0=0.8, cap1=0.8, shape=1.0, twist=0.0):
    """Closed tube through control rows (x, y, z, a, b, c).

    a = radius along the side axis S, b = radius toward +N, c = radius toward -N,
    where N is `up` made perpendicular to the path and S = T x N. cap0/cap1 scale the rounded end caps
    (0 = flat end). shape > 1 sharpens the section toward a diamond, < 1 squares it.
    """
    rows = spline(rows, per_seg)
    P = rows[:, :3].copy()
    n = len(P)
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1)[:, None], 1e-12)
    U = np.array(up, float)
    rings = []
    for i in range(n):
        t = T[i]
        N = U - np.dot(U, t) * t
        N /= np.linalg.norm(N)
        S = np.cross(t, N)
        a, b, c = rows[i, 3], rows[i, 4], rows[i, 5]
        ring = []
        for j in range(seg):
            th = 2 * math.pi * j / seg + twist
            s, u = math.cos(th), math.sin(th)
            if shape != 1.0:
                s = math.copysign(abs(s) ** shape, s)
                u = math.copysign(abs(u) ** shape, u)
            ring.append(P[i] + S * a * s + N * (b if u >= 0 else c) * u)
        rings.append((np.array(ring), P[i], t, max(1e-5, min(a, b, c))))

    def cap_rings(ring, center, t, r, sign, f):
        out = []
        for k in range(1, CAPK):
            ph = (k / CAPK) * math.pi / 2
            out.append(center + (ring - center) * math.cos(ph) + sign * t * r * f * math.sin(ph))
        return out, center + sign * t * r * f

    all_rings = [r[0] for r in rings]
    if cap0 > 0:
        extra, pole0 = cap_rings(rings[0][0], rings[0][1], rings[0][2], rings[0][3], -1, cap0)
        all_rings = extra[::-1] + all_rings
    else:
        pole0 = rings[0][1]
    if cap1 > 0:
        extra, pole1 = cap_rings(rings[-1][0], rings[-1][1], rings[-1][2], rings[-1][3], 1, cap1)
        all_rings = all_rings + extra
    else:
        pole1 = rings[-1][1]
    vr = [[bm.verts.new(Vector(p)) for p in ring] for ring in all_rings]
    _, Uc, vv = grid_faces(bm, vr, close_j=True)
    uvl = uv_layer(bm)
    v0 = bm.verts.new(Vector(pole0))
    v1 = bm.verts.new(Vector(pole1))
    p0 = vv[0] - (Vector(pole0) - _centre(vr[0])).length
    p1 = vv[-1] + (Vector(pole1) - _centre(vr[-1])).length
    for j in range(seg):
        set_uvs(bm.faces.new((v0, vr[0][(j + 1) % seg], vr[0][j])), uvl, ((0.0, p0), (Uc[0][j + 1], vv[0]), (Uc[0][j], vv[0])))
        set_uvs(bm.faces.new((v1, vr[-1][j], vr[-1][(j + 1) % seg])), uvl,
                ((0.0, p1), (Uc[-1][j], vv[-1]), (Uc[-1][j + 1], vv[-1])))


def ellipsoid(bm, center, radii, rot=None, seg=12, rings=8):
    uv_layer(bm)
    m = Matrix.Diagonal((radii[0], radii[1], radii[2], 1.0))
    if rot is not None:
        m = rot.to_4x4() @ m
    m = Matrix.Translation(Vector(center)) @ m
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0, matrix=m, calc_uvs=True)


def cone(bm, base, tip, r0, r1=0.0, seg=8):
    uv_layer(bm)
    base, tip = Vector(base), Vector(tip)
    d = tip - base
    rot = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    m = Matrix.Translation(base + d / 2) @ rot
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r0, radius2=r1, depth=d.length, matrix=m,
                          calc_uvs=True)


def box(bm, center, size, rot=None):
    """Box with each face unwrapped flat at its true size (six islands)."""
    uvl = uv_layer(bm)
    R = rot.to_4x4() if rot is not None else Matrix.Identity(4)
    M = Matrix.Translation(Vector(center)) @ R
    V = {}
    for ix in (0, 1):
        for iy in (0, 1):
            for iz in (0, 1):
                V[ix, iy, iz] = bm.verts.new(M @ Vector(((ix - 0.5) * size[0], (iy - 0.5) * size[1], (iz - 0.5) * size[2])))
    for k in range(3):
        a, b = [x for x in range(3) if x != k]
        for s in (0, 1):
            quad, uvs = [], []
            for ca, cb in ((0, 0), (1, 0), (1, 1), (0, 1)):
                idx = [0, 0, 0]
                idx[k], idx[a], idx[b] = s, ca, cb
                quad.append(V[tuple(idx)])
                uvs.append((ca * size[a], cb * size[b]))
            set_uvs(bm.faces.new(quad), uvl, uvs)


def torus(bm, center, normal, R, r, seg=12, rseg=5):
    nrm = Vector(normal).normalized()
    t = nrm.orthogonal().normalized()
    b = nrm.cross(t)
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        d = t * math.cos(a) + b * math.sin(a)
        c = Vector(center) + d * R
        rings.append([bm.verts.new(c + d * r * math.cos(2 * math.pi * j / rseg) + nrm * r * math.sin(2 * math.pi * j / rseg))
                      for j in range(rseg)])
    grid_faces(bm, rings, close_j=True, close_i=True)


def slab(bm, outline, frame, z0, z1):
    """Closed slab from a 2D outline between z0 and z1 in `frame` (4x4 taking (x, y, z) to object space). UVs:
    the two flat faces as drawn, the rim as one strip."""
    uvl = uv_layer(bm)
    top = [bm.verts.new(frame @ Vector((x, y, z1))) for x, y in outline]
    bot = [bm.verts.new(frame @ Vector((x, y, z0))) for x, y in outline]
    set_uvs(bm.faces.new(top), uvl, [(x, y) for x, y in outline])
    set_uvs(bm.faces.new(bot[::-1]), uvl, [(-x, y) for x, y in outline[::-1]])
    grid_faces(bm, [top, bot], close_j=True)


def prism(bm, pts, z0, z1):
    slab(bm, pts, Matrix.Identity(4), z0, z1)


def closed_spline(pts, per_seg=4):
    c = np.asarray(pts, float)
    n = len(c)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = c[(i - 1) % n], c[i], c[(i + 1) % n], c[(i + 2) % n]
        for k in range(per_seg):
            out.append(_cr(p0, p1, p2, p3, k / per_seg))
    return np.array(out)


# ----------------------------------------------------------------------------------------- objects
def get_coll(name, parent=None, scene=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
    par = parent if parent is not None else (scene or bpy.context.scene).collection
    if c.name not in [x.name for x in par.children]:
        par.children.link(c)
    return c


def remove_obj(name):
    ob = bpy.data.objects.get(name)
    if ob is not None:
        me = ob.data if ob.type == 'MESH' else None
        bpy.data.objects.remove(ob, do_unlink=True)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t
