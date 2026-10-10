"""Pack every weapon's construction UVs into one atlas and bake the three textures (see wpn_mats):

    import wpn_bake; wpn_bake.bake_all()                  # the weapons (WPN_Export -> T_Weapons*)
    wpn_bake.bake_all(kit="shields")                      # the shields (WPN_Shields -> T_Shields*), an atlas of their own

textures/T_Weapons.png (colour), T_Weapons_Glow.png (rune and crystal mask), T_Weapons_MS.png (metallic in R,
smoothness in A); the same three for T_Shields. The painted source materials stay on the weapons (a later pass can be baked again without a
rebuild); game_material() puts the colour atlas on them instead, for a look at the baked result.
"""
import bpy, os
import numpy as np
from wpn_common import fill_gutters
import wpn_mats

TEX_DIR = wpn_mats.TEX_DIR
KITS = {"weapons": ("WPN_Export", "T_Weapons"), "shields": ("WPN_Shields", "T_Shields")}   # collection, texture prefix
PASSES = (("color", ""), ("glow", "_Glow"), ("ms", "_MS"))


def objects(kit="weapons"):
    return sorted(bpy.data.collections[KITS[kit][0]].objects, key=lambda o: o.name)


def uv_report(objs):
    """Faces left without UVs (all loops at 0,0) per object: should be none."""
    out = {}
    for o in objs:
        me = o.data
        uv = me.uv_layers.get("UVMap") or me.uv_layers[0]
        co = np.empty(len(me.loops) * 2, dtype=np.float32)
        uv.data.foreach_get("uv", co)
        co = co.reshape(-1, 2)
        bad = sum(1 for p in me.polygons if not np.any(co[p.loop_start:p.loop_start + p.loop_total]))
        if bad:
            out[o.name] = bad
    return out


def _select(objs):
    vl = bpy.context.view_layer
    exp = objs[0].users_collection[0]
    exp.hide_viewport = False
    for lc in vl.layer_collection.children:
        if lc.collection == exp:
            lc.exclude = False
            lc.hide_viewport = False
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    vl.objects.active = objs[0]


def pack(objs, margin=0.003):
    for o in objs:
        o.data.uv_layers.active = o.data.uv_layers["UVMap"]
    _select(objs)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(margin=margin, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake_all(size=2048, samples=24, margin=0.003, passes=("color", "glow", "ms"), pack_uvs=True, kit="weapons"):
    """Pack (unless pack_uvs is False: a later pass of the same layout) and bake the given passes of one kit."""
    objs = objects(kit)
    missing = uv_report(objs)
    if missing:
        print("faces without UVs:", missing)
    if pack_uvs:
        pack(objs, margin)
    os.makedirs(TEX_DIR, exist_ok=True)
    scn = bpy.context.scene
    prev = scn.render.engine
    scn.render.engine = 'CYCLES'
    scn.cycles.samples = samples
    mats = {m for o in objs for m in o.data.materials if m is not None}
    paths = {}
    for pas, suffix in PASSES:
        name = KITS[kit][1] + suffix
        if pas not in passes:
            continue
        img = bpy.data.images.get(name)
        if img is not None:
            bpy.data.images.remove(img)
        img = bpy.data.images.new(name, size, size, alpha=True, float_buffer=False)
        img.colorspace_settings.name = 'sRGB' if pas == "color" else 'Non-Color'
        wpn_mats.set_pass(pas)
        for m in mats:
            nt = m.node_tree
            node = nt.nodes.get("BAKE_TARGET") or nt.nodes.new('ShaderNodeTexImage')
            node.name = "BAKE_TARGET"
            node.image = img
            nt.nodes.active = node
        _select(objs)
        bpy.ops.object.bake(type='EMIT', margin=4, use_clear=True)
        if pas != "glow":                               # the glow map keeps black gutters
            fill_gutters(img)
        if pas == "ms":                                  # URP: metallic in R, smoothness in A
            a = np.empty(size * size * 4, np.float32)
            img.pixels.foreach_get(a)
            a = a.reshape(-1, 4)
            a[:, 3] = a[:, 1]
            a[:, 1] = a[:, 0]
            a[:, 2] = a[:, 0]
            img.pixels.foreach_set(a.ravel())
        img.filepath_raw = os.path.join(TEX_DIR, name + ".png")
        img.file_format = 'PNG'
        img.save()
        paths[pas] = img.filepath_raw
    wpn_mats.set_pass("color")
    scn.render.engine = prev
    return paths


def game_material(objs):
    """Swap the painted source materials for the one game material (the colour atlas), for the Blender preview."""
    gm = bpy.data.materials.get("M_Weapons") or bpy.data.materials.new("M_Weapons")
    gm.use_nodes = True
    nt = gm.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.5
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images["T_Weapons"]
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(gm)
        for p in o.data.polygons:
            p.material_index = 0
