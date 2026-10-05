"""Review renders of the weapon catalog: an orthographic front camera per catalog row, close-ups of single weapons."""
import bpy, math, os
from mathutils import Vector
from wpn_common import ROOT

RENDERS = os.path.join(ROOT, "renders")


def _world(scn):
    w = bpy.data.worlds.get("WPN_World") or bpy.data.worlds.new("WPN_World")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.2, 0.21, 0.23, 1)
    bg.inputs['Strength'].default_value = 1.0
    scn.world = w


def camera(scn, name="CAM_Review"):
    cam = bpy.data.objects.get(name)
    if cam is None:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        scn.collection.objects.link(cam)
    cam.data.type = 'ORTHO'
    cam.rotation_euler = (math.radians(90), 0, 0)
    scn.camera = cam
    return cam


def render(path, objs, res=(1800, 900), pad=1.06, scene="Weapons", lineup=True, gap=0.06, turn=0.0):
    """Frame the given catalog objects from the front and render them to renders/<path>.png. lineup: stand them
    side by side for the shot (their catalog places come back after); turn: degrees about the vertical."""
    scn = bpy.data.scenes[scene]
    _world(scn)
    cam = camera(scn)
    saved = [(o, o.location.copy(), o.rotation_euler.copy()) for o in objs]
    if lineup:
        x = 0.0
        for o in objs:
            o.rotation_euler = (math.radians(90), 0, math.radians(turn))
            bpy.context.view_layer.update()
            o.location = (0, 0, 0)
            bpy.context.view_layer.update()
            pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
            x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
            o.location = (x - x0, 0, 100.0)
            x += (x1 - x0) + gap
        bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
    z0, z1 = min(p.z for p in pts), max(p.z for p in pts)
    cam.location = ((x0 + x1) / 2, -5.0, (z0 + z1) / 2)
    aspect = res[0] / res[1]
    cam.data.ortho_scale = max(x1 - x0, (z1 - z0) * aspect) * pad
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.resolution_percentage = 100
    try:
        scn.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        scn.render.engine = 'BLENDER_EEVEE'
    hidden = []
    for o in scn.objects:
        if o.type in ('MESH', 'FONT') and o not in objs and not o.hide_render:
            if lineup or not any(o.name == "LBL_" + x.name[4:] for x in objs):
                o.hide_render = True
                hidden.append(o)
    os.makedirs(RENDERS, exist_ok=True)
    scn.render.filepath = os.path.join(RENDERS, path + ".png")
    bpy.ops.render.render(write_still=True, scene=scn.name)
    for o in hidden:
        o.hide_render = False
    for o, loc, rot in saved:
        o.location, o.rotation_euler = loc, rot
    return scn.render.filepath


def cat(names, scene="Weapons"):
    S = bpy.data.scenes[scene]
    return [S.objects["CAT_Wpn_" + n] for n in names]


def row_objects(row, scene="Weapons", row_gap=1.9):
    scn = bpy.data.scenes[scene]
    z = -row * row_gap
    return [o for o in scn.objects if o.name.startswith("CAT_") and abs(o.location.z - z) < 0.01]
