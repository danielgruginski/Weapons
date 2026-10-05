"""Build every weapon of the roster into the blend file.

    import sys; sys.path.insert(0, r"E:\\Unity\\Projects\\GameArtGeneration\\Weapons\\src")
    import wpn_build; wpn_build.build_all()

Objects: Wpn_<Name> (and Wpn_<Name>_Rune, the enchanted copy) in collection WPN_Export, in socket space at the
origin; the scene "Weapons" shows them as a catalog (linked copies stood upright in rows, labelled).
"""
import bpy, bmesh, math, importlib
from mathutils import Vector, Matrix
import wpn_common, wpn_mats, wpn_parts, wpn_roster
from wpn_common import get_coll, remove_obj

SCENE = "Weapons"
SHARP = math.radians(75)                   # blade edges and box corners; 5- to 8-sided tubes stay smooth


def reload():
    for m in (wpn_common, wpn_mats, wpn_parts, wpn_roster):
        importlib.reload(m)


def finish(name, b, coll, mats, hand):
    remove_obj(name)
    bm = b.bm
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons, quad_method='BEAUTY', ngon_method='BEAUTY')
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    for mn in b.mats:
        me.materials.append(mats[mn])
    for p in me.polygons:
        p.use_smooth = True
    me.set_sharp_from_angle(angle=SHARP)
    for uv in me.uv_layers:                              # bmesh names its first layer "Float2"
        if uv.name != "Rune":
            uv.name = "UVMap"
            break
    me.uv_layers.active = me.uv_layers["UVMap"]
    me.uv_layers["UVMap"].active_render = True
    ob["hand"] = hand
    for k, v in b.meta.items():
        ob[k] = v
    return ob


def scene():
    scn = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    scn.view_settings.view_transform = 'Standard'
    scn.unit_settings.system = 'METRIC'
    return scn


def build_all(names=None):
    reload()
    scn = scene()
    if bpy.context.window.scene != scn:
        bpy.context.window.scene = scn
    mats = wpn_mats.build_materials()
    coll = get_coll("WPN_Export", scene=scn)
    built = []
    for name, fn, hand, mode in wpn_roster.WEAPONS:
        if names and name not in names:
            continue
        if mode in ('plain', 'both'):
            built.append(finish("Wpn_" + name, fn(False), coll, mats, hand))
        if mode in ('both', 'rune'):
            built.append(finish("Wpn_" + name + ("_Rune" if mode == 'both' else ""), fn(True), coll, mats, hand))
    coll.hide_viewport = False
    catalog(scn)
    return {o.name: len(o.data.polygons) for o in built}


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# ----------------------------------------------------------------------------------------- catalog
def catalog(scn, dx=0.32, row_gap=1.9, per_row=16):
    """Linked copies of every weapon stood upright (+Y socket = up), mundane and enchanted side by side, labelled."""
    cat = get_coll("WPN_Catalog", scene=scn)
    for o in list(cat.objects):
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if isinstance(data, bpy.types.Curve) and data.users == 0:
            bpy.data.curves.remove(data)
    exp = bpy.data.collections["WPN_Export"]
    objs = []
    for n, _, h, m in wpn_roster.WEAPONS:
        for nm in ("Wpn_" + n, "Wpn_" + n + "_Rune"):
            if nm in exp.objects:
                objs.append(exp.objects[nm])
    x = 0.0
    row = 0
    col = 0
    for o in objs:
        if col >= per_row:
            row += 1
            col = 0
            x = 0.0
        bb = [Vector(v) for v in o.bound_box]
        x0, x1 = min(v.x for v in bb), max(v.x for v in bb)
        w = x1 - x0
        c = bpy.data.objects.new("CAT_" + o.name, o.data)
        cat.objects.link(c)
        c.rotation_euler = (math.radians(90), 0, 0)           # socket +Y -> world +Z, +Z toward -Y (the camera)
        c.location = (x - x0, 0, -row * row_gap)
        cu = bpy.data.curves.new("LBL_" + o.name, 'FONT')
        cu.body = o.name.replace("Wpn_", "").replace("_Rune", "\n(rune)")
        cu.size = 0.035
        cu.align_x = 'CENTER'
        lbl = bpy.data.objects.new("LBL_" + o.name, cu)
        lbl.location = (x + w / 2, 0, -row * row_gap - 0.42)
        lbl.rotation_euler = (math.radians(90), 0, 0)
        cat.objects.link(lbl)
        x += max(w, 0.14) + 0.12
        col += 1
    exp.hide_viewport = True
    return len(objs)
