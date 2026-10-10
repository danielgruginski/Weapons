"""FBX export for Unity:

    import wpn_export; wpn_export.export_all()            # the weapons
    wpn_export.export_all(kit="shields")                  # the shields: Shd_*.fbx, T_Shields*, shields.json

export/Models/Wpn_<Name>.fbx    each weapon alone, in socket space (parent it under the hand socket, identity pose;
                                the game turns goblin-frame props into the Humans sockets with its own rotation)
export/Textures/*.png           T_Weapons, T_Weapons_Glow, T_Weapons_MS
export/weapons.json             per weapon: hand, triangles, bounds, and the points the game needs (bow string tips,
                                crossbow bolt rest), in Unity's frame (Blender +X = Unity -X)
"""
import bpy, os, json, shutil
from mathutils import Vector
from wpn_common import ROOT
import wpn_roster, wpn_shields

EXPORT = os.path.join(ROOT, "export")
# collection, texture prefix, manifest (its list is named after the kit)
KITS = {"weapons": ("WPN_Export", "T_Weapons", "weapons.json"), "shields": ("WPN_Shields", "T_Shields", "shields.json")}
FBX = dict(apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', use_armature_deform_only=True,
           add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X', bake_anim=False,
           mesh_smooth_type='FACE', use_mesh_modifiers=True, use_custom_props=True, path_mode='STRIP',
           embed_textures=False)


def _unity(p):
    """A point in the prop's Blender space -> the imported prop's Unity local space."""
    return [-p[0], p[1], p[2]]


def export_all(kit="weapons"):
    coll_name, tex, manifest_file = KITS[kit]
    os.makedirs(os.path.join(EXPORT, "Models"), exist_ok=True)
    os.makedirs(os.path.join(EXPORT, "Textures"), exist_ok=True)
    exp = bpy.data.collections[coll_name]
    exp.hide_viewport = False
    vl = bpy.context.view_layer
    objs = sorted(exp.objects, key=lambda o: o.name)
    rune_only = {"Wpn_" + n for n, _, _, mode in wpn_roster.WEAPONS if mode == 'rune'}
    rune_only |= {"Shd_" + n for n, _, mode in wpn_shields.SHIELDS if mode == 'rune'}
    manifest = {}
    gm = bpy.data.materials.get("M_Weapons") or bpy.data.materials.new("M_Weapons")
    coll = bpy.context.scene.collection
    for o in objs:
        # one material over the whole mesh (the painted source materials are baked into the atlas): one submesh in Unity
        me = o.data.copy()
        me.materials.clear()
        me.materials.append(gm)
        for p in me.polygons:
            p.material_index = 0
        name = o.name
        o.name = name + "__src"
        tmp = bpy.data.objects.new(name, me)
        coll.objects.link(tmp)
        for s in bpy.context.selected_objects:
            s.select_set(False)
        tmp.select_set(True)
        vl.objects.active = tmp
        path = os.path.join(EXPORT, "Models", name + ".fbx")
        try:
            bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, **FBX)
        finally:
            bpy.data.objects.remove(tmp, do_unlink=True)
            bpy.data.meshes.remove(me)
            o.name = name
        bb = [Vector(c) for c in o.bound_box]
        lo = [min(v[k] for v in bb) for k in range(3)]
        hi = [max(v[k] for v in bb) for k in range(3)]
        e = {"hand": o.get("hand", "R"),
             "tris": sum(len(p.vertices) - 2 for p in o.data.polygons),
             "bounds_min": _unity((hi[0], lo[1], lo[2])), "bounds_max": _unity((lo[0], hi[1], hi[2])),
             "length": hi[1] - lo[1], "runed": o.name.endswith("_Rune") or o.name in rune_only}
        for k in ("string_top", "string_bottom", "bolt_rest"):
            if k in o:
                e[k] = _unity(tuple(o[k]))
        manifest[o.name] = e
    for fn in os.listdir(os.path.join(ROOT, "textures")):
        if fn.startswith(tex) and fn.endswith(".png"):
            shutil.copy2(os.path.join(ROOT, "textures", fn), os.path.join(EXPORT, "Textures", fn))
    with open(os.path.join(EXPORT, manifest_file), "w", encoding="utf-8") as f:
        json.dump({kit: [dict(name=k, **v) for k, v in manifest.items()]}, f, indent=1)
    for s in bpy.context.selected_objects:
        s.select_set(False)
    exp.hide_viewport = True
    return len(manifest)
