"""Painted source materials for the weapon kit, and the three bake passes they drive.

Every weapon part carries one of these materials while it is built. The bake renders them into three textures
over one packed UV layout:
    color   T_Weapons        painted colour: two-tone noise, stains, ambient occlusion, top light, worn edges
    glow    T_Weapons_Glow   what lights up on an enchanted weapon: runes (the glyph strip, through the "Rune" UV
                             layer of the rune inlays) and crystals; black everywhere else
    ms      T_Weapons_MS     metallic (R) and smoothness (A, from the bake's G) for URP Lit
`set_pass(name)` relinks every source material's emission to one of the three.
"""
import bpy, os, math
import numpy as np
from wpn_common import ROOT

TEX_DIR = os.path.join(ROOT, "textures")
RUNE_IMG = "T_RuneStrip"
RUNE_SPACING = 0.0115            # metres of inlay per glyph (the strip image holds RUNE_GLYPHS of them)
RUNE_GLYPHS = 32


def _hex(h, a=1.0):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*c, a)


# name: (dark, light, noise scale (x, y, z object space), stain (colour, scale, threshold) or None, edge wear,
#        stripes (direction, scale) or None, glow (0, 1 or 'rune'), metallic, smoothness)
PALETTE = {
    # metals
    'iron':        ('#45474d', '#6b6e75', (30, 30, 30), ('#6e3f24', 14, 0.60), 1.3, None, 0, 0.2, 0.3),
    'steel':       ('#80868f', '#b2b8c1', (40, 6, 40), ('#5d6067', 10, 0.66), 1.5, None, 0, 0.25, 0.48),
    'steel_fine':  ('#9aa4b0', '#d7dee6', (50, 5, 50), None, 1.6, None, 0, 0.3, 0.56),
    'steel_dark':  ('#2c2f36', '#4a4e57', (40, 6, 40), None, 1.4, None, 0, 0.25, 0.42),
    'gold':        ('#8c6421', '#e0b552', (25, 25, 25), ('#5e4316', 10, 0.66), 1.3, None, 0, 0.35, 0.5),
    'brass':       ('#6b4e1c', '#b8913e', (25, 25, 25), ('#3f4a2a', 10, 0.66), 1.2, None, 0, 0.3, 0.42),
    'silver':      ('#9ea2aa', '#e3e6ec', (30, 30, 30), ('#6d717a', 10, 0.68), 1.3, None, 0, 0.35, 0.55),
    'bronze':      ('#5e3b1c', '#9c6a36', (25, 25, 25), ('#3c4a35', 9, 0.64), 1.2, None, 0, 0.3, 0.4),
    # organics
    'leather':     ('#4d301b', '#7a5132', (35, 35, 35), ('#35200f', 9, 0.62), 0.7, None, 0, 0.0, 0.32),
    'leather_dark':('#24180f', '#3f2b1d', (35, 35, 35), None, 0.6, None, 0, 0.0, 0.3),
    'leather_red': ('#561a14', '#8c2d22', (35, 35, 35), ('#3a0f0b', 9, 0.62), 0.7, None, 0, 0.0, 0.34),
    'leather_blue':('#1c2a40', '#34496a', (35, 35, 35), None, 0.6, None, 0, 0.0, 0.34),
    'cord':        ('#3a2a1c', '#6e5438', (30, 30, 30), None, 0.5, ('DIAGONAL', 260), 0, 0.0, 0.25),
    'wire':        ('#6e7076', '#c4c7cd', (30, 30, 30), None, 0.8, ('DIAGONAL', 420), 0, 0.3, 0.42),
    'wood':        ('#5a3d25', '#8c6640', (45, 3, 45), ('#3e2918', 6, 0.64), 0.6, None, 0, 0.0, 0.3),
    'wood_ash':    ('#7a5c3c', '#b08c62', (50, 3, 50), ('#5c4129', 6, 0.66), 0.6, None, 0, 0.0, 0.32),
    'wood_dark':   ('#2e1f15', '#4f3624', (50, 3, 50), None, 0.6, None, 0, 0.0, 0.36),
    'yew':         ('#7a4422', '#c98d52', (40, 1.5, 40), ('#e1b98a', 4, 0.6), 0.6, None, 0, 0.0, 0.4),
    'horn':        ('#2a1f17', '#b5a07c', (12, 12, 12), None, 0.6, None, 0, 0.0, 0.55),
    'lacquer':     ('#2a0c0a', '#6e2219', (30, 4, 30), ('#140605', 7, 0.66), 0.7, None, 0, 0.0, 0.6),
    'bone':        ('#a59572', '#e0d4b0', (20, 20, 20), ('#7d6a48', 7, 0.62), 0.5, None, 0, 0.0, 0.4),
    'linen':       ('#8f8467', '#c4b994', (60, 60, 60), None, 0.3, ('Z', 240), 0, 0.0, 0.2),
    'string':      ('#bfb49a', '#e6dcc2', (20, 20, 20), None, 0.2, ('DIAGONAL', 900), 0, 0.0, 0.3),
    'fletch_white':('#c9c3b6', '#f0ece2', (40, 40, 40), None, 0.2, ('Z', 600), 0, 0.0, 0.2),
    'fletch_grey': ('#53545a', '#8e9098', (40, 40, 40), None, 0.2, ('Z', 600), 0, 0.0, 0.2),
    'fletch_red':  ('#6e1a14', '#b0362a', (40, 40, 40), None, 0.2, ('Z', 600), 0, 0.0, 0.2),
    # stones
    'gem_red':     ('#4a0a0e', '#e0303a', (60, 60, 60), None, 1.6, None, 0, 0.0, 0.9),
    'gem_blue':    ('#0a1a4a', '#3a7ae0', (60, 60, 60), None, 1.6, None, 0, 0.0, 0.9),
    'gem_green':   ('#0a3a1a', '#3ad070', (60, 60, 60), None, 1.6, None, 0, 0.0, 0.9),
    'crystal':     ('#7d97a8', '#e8f6ff', (60, 60, 60), None, 1.8, None, 1, 0.0, 0.92),
    # the inlay that carries an enchanted weapon's runes (engraved steel; the glyphs glow in the magic material)
    'rune':        ('#2d3036', '#41454d', (40, 40, 40), None, 0.4, None, 'rune', 0.25, 0.42),
}


def rune_image():
    """The glyph strip: RUNE_GLYPHS runic marks (a stave and its branches), white on black, softly bloomed."""
    img = bpy.data.images.get(RUNE_IMG)
    path = os.path.join(TEX_DIR, RUNE_IMG + ".png")
    if img is not None:
        return img
    W, H = 48 * RUNE_GLYPHS, 64
    a = np.zeros((H, W), np.float32)
    rng = np.random.default_rng(1337)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    def seg(p, q, r=2.6):
        x0, x1 = int(max(0, min(p[0], q[0]) - 6)), int(min(W, max(p[0], q[0]) + 7))
        y0, y1 = int(max(0, min(p[1], q[1]) - 6)), int(min(H, max(p[1], q[1]) + 7))
        X, Y = xx[y0:y1, x0:x1], yy[y0:y1, x0:x1]
        dx, dy = q[0] - p[0], q[1] - p[1]
        L2 = max(dx * dx + dy * dy, 1e-6)
        t = np.clip(((X - p[0]) * dx + (Y - p[1]) * dy) / L2, 0, 1)
        d = np.hypot(X - (p[0] + t * dx), Y - (p[1] + t * dy))
        a[y0:y1, x0:x1] = np.maximum(a[y0:y1, x0:x1], np.clip(r + 0.8 - d, 0, 1))

    for g in range(RUNE_GLYPHS):
        cx = g * 48 + 24
        top, bot = 10, 54
        kind = rng.integers(0, 6)
        if kind == 0:                                   # stave with two branches up-right
            seg((cx - 4, bot), (cx - 4, top))
            seg((cx - 4, top + 4), (cx + 10, top + 14))
            seg((cx - 4, top + 16), (cx + 10, top + 26))
        elif kind == 1:                                 # two staves joined by a cross
            seg((cx - 9, bot), (cx - 9, top)); seg((cx + 9, bot), (cx + 9, top))
            seg((cx - 9, top + 10), (cx + 9, top + 26))
        elif kind == 2:                                 # diamond on a stave
            seg((cx, bot), (cx, top + 22))
            seg((cx, top), (cx + 10, top + 11)); seg((cx + 10, top + 11), (cx, top + 22))
            seg((cx, top + 22), (cx - 10, top + 11)); seg((cx - 10, top + 11), (cx, top))
        elif kind == 3:                                 # arrow
            seg((cx, bot), (cx, top))
            seg((cx, top), (cx - 11, top + 13)); seg((cx, top), (cx + 11, top + 13))
        elif kind == 4:                                 # crossed staves
            seg((cx - 10, bot), (cx + 10, top)); seg((cx + 10, bot), (cx - 10, top))
            seg((cx, top + 4), (cx, bot - 4))
        else:                                           # hooked stave
            seg((cx - 3, bot), (cx - 3, top))
            seg((cx - 3, top), (cx + 9, top + 10)); seg((cx + 9, top + 10), (cx - 3, top + 20))
            seg((cx - 3, top + 24), (cx + 9, bot))
    k = 5                                               # bloom: box blur by cumulative sums
    pad = np.pad(a, k, mode='wrap')
    c = pad.cumsum(0).cumsum(1)
    blur = (c[2 * k:, 2 * k:] - c[:-2 * k, 2 * k:] - c[2 * k:, :-2 * k] + c[:-2 * k, :-2 * k])[:H, :W] / (2 * k) ** 2
    v = np.clip(a + blur * 0.45, 0, 1)
    img = bpy.data.images.new(RUNE_IMG, W, H, alpha=False)
    px = np.ones((H, W, 4), np.float32)
    px[..., 0] = px[..., 1] = px[..., 2] = v[::-1]      # image rows go bottom-up
    img.pixels.foreach_set(px.ravel())
    os.makedirs(TEX_DIR, exist_ok=True)
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    return img


def paint_group():
    """AO x top light + worn-edge highlight over a base colour (the goblins' painted look)."""
    g = bpy.data.node_groups.get("WPN_PaintLight")
    if g is not None:
        return g
    g = bpy.data.node_groups.new("WPN_PaintLight", 'ShaderNodeTree')
    g.interface.new_socket("Color", in_out='INPUT', socket_type='NodeSocketColor')
    g.interface.new_socket("Edge", in_out='INPUT', socket_type='NodeSocketFloat')
    g.interface.new_socket("Color", in_out='OUTPUT', socket_type='NodeSocketColor')
    N, L = g.nodes, g.links
    gi, go = N.new('NodeGroupInput'), N.new('NodeGroupOutput')
    ao = N.new('ShaderNodeAmbientOcclusion')
    ao.samples = 12
    ao.inputs['Distance'].default_value = 0.03
    bev = N.new('ShaderNodeBevel')
    bev.samples = 8
    bev.inputs['Radius'].default_value = 0.0025
    geo = N.new('ShaderNodeNewGeometry')
    dot = N.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    L.new(bev.outputs['Normal'], dot.inputs[0])
    L.new(geo.outputs['Normal'], dot.inputs[1])
    edge = N.new('ShaderNodeMapRange')
    edge.inputs['From Min'].default_value = 0.999
    edge.inputs['From Max'].default_value = 0.93
    L.new(dot.outputs['Value'], edge.inputs['Value'])
    sep = N.new('ShaderNodeSeparateXYZ')
    L.new(geo.outputs['Normal'], sep.inputs[0])
    top = N.new('ShaderNodeMapRange')            # socket +Y is "up" when the weapon is held raised: light from +Y/+Z
    top.inputs['From Min'].default_value = -1
    top.inputs['To Min'].default_value = 0.86
    top.inputs['To Max'].default_value = 1.08
    L.new(sep.outputs['Z'], top.inputs['Value'])
    aot = N.new('ShaderNodeMapRange')
    aot.inputs['To Min'].default_value = 0.5
    L.new(ao.outputs['AO'], aot.inputs['Value'])
    m1 = N.new('ShaderNodeMix')
    m1.data_type, m1.blend_type = 'RGBA', 'MULTIPLY'
    m1.inputs['Factor'].default_value = 1
    L.new(gi.outputs['Color'], m1.inputs['A'])
    L.new(aot.outputs['Result'], m1.inputs['B'])
    m2 = N.new('ShaderNodeMix')
    m2.data_type, m2.blend_type = 'RGBA', 'MULTIPLY'
    m2.inputs['Factor'].default_value = 1
    L.new(m1.outputs['Result'], m2.inputs['A'])
    L.new(top.outputs['Result'], m2.inputs['B'])
    ef = N.new('ShaderNodeMath')
    ef.operation = 'MULTIPLY'
    L.new(edge.outputs['Result'], ef.inputs[0])
    L.new(gi.outputs['Edge'], ef.inputs[1])
    m3 = N.new('ShaderNodeMix')
    m3.data_type, m3.blend_type = 'RGBA', 'ADD'
    m3.inputs['B'].default_value = (0.28, 0.27, 0.24, 1)
    L.new(ef.outputs['Value'], m3.inputs['Factor'])
    L.new(m2.outputs['Result'], m3.inputs['A'])
    L.new(m3.outputs['Result'], go.inputs['Color'])
    return g


def _material(name, spec):
    dark, light, scale, stain, edge, stripes, glow, metal, smooth = spec
    m = bpy.data.materials.get("WS_" + name) or bpy.data.materials.new("WS_" + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial')
    em = N.new('ShaderNodeEmission')
    em.name = "EMIT"
    L.new(em.outputs['Emission'], out.inputs['Surface'])
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = scale
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 1.0
    nz.inputs['Detail'].default_value = 4
    nz.inputs['Roughness'].default_value = 0.6
    L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = _hex(dark)
    ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[1].color = _hex(light)
    L.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    col = ramp.outputs['Color']
    if stripes is not None:
        wv = N.new('ShaderNodeTexWave')
        wv.wave_type = 'BANDS'
        wv.bands_direction = stripes[0]
        wv.inputs['Scale'].default_value = stripes[1]
        wv.inputs['Distortion'].default_value = 1.5
        L.new(tc.outputs['Object'], wv.inputs['Vector'])
        mr = N.new('ShaderNodeMapRange')
        mr.inputs['To Min'].default_value = 0.72
        L.new(wv.outputs['Fac'], mr.inputs['Value'])
        mx = N.new('ShaderNodeMix')
        mx.data_type, mx.blend_type = 'RGBA', 'MULTIPLY'
        mx.inputs['Factor'].default_value = 1
        L.new(col, mx.inputs['A'])
        L.new(mr.outputs['Result'], mx.inputs['B'])
        col = mx.outputs['Result']
    if stain is not None:
        sn = N.new('ShaderNodeTexNoise')
        sn.inputs['Scale'].default_value = stain[1]
        sn.inputs['Detail'].default_value = 6
        L.new(tc.outputs['Object'], sn.inputs['Vector'])
        sr = N.new('ShaderNodeMapRange')
        sr.inputs['From Min'].default_value = stain[2]
        sr.inputs['From Max'].default_value = stain[2] + 0.08
        L.new(sn.outputs['Fac'], sr.inputs['Value'])
        mx = N.new('ShaderNodeMix')
        mx.data_type = 'RGBA'
        mx.inputs['B'].default_value = _hex(stain[0])
        L.new(sr.outputs['Result'], mx.inputs['Factor'])
        L.new(col, mx.inputs['A'])
        col = mx.outputs['Result']
    if metal >= 0.5:                                     # bevels and sides turned to the knuckles' way catch the light
        sx = N.new('ShaderNodeSeparateXYZ')
        L.new(tc.outputs['Normal'], sx.inputs[0])
        ab = N.new('ShaderNodeMath')
        ab.operation = 'ABSOLUTE'
        L.new(sx.outputs['X'], ab.inputs[0])
        sh = N.new('ShaderNodeMapRange')
        sh.inputs['From Min'].default_value = 0.12
        sh.inputs['From Max'].default_value = 0.6
        sh.inputs['To Max'].default_value = 0.22
        L.new(ab.outputs['Value'], sh.inputs['Value'])
        mx = N.new('ShaderNodeMix')
        mx.data_type, mx.blend_type = 'RGBA', 'SCREEN'
        mx.inputs['B'].default_value = (1, 1, 1, 1)
        L.new(sh.outputs['Result'], mx.inputs['Factor'])
        L.new(col, mx.inputs['A'])
        col = mx.outputs['Result']
    glow_out = None
    if glow == 'rune':                                   # the glyphs, through the inlay's own UV layer
        uvn = N.new('ShaderNodeUVMap')
        uvn.uv_map = "Rune"
        mp2 = N.new('ShaderNodeMapping')
        mp2.inputs['Scale'].default_value = (1.0 / (RUNE_SPACING * RUNE_GLYPHS), 1.0, 1.0)
        L.new(uvn.outputs['UV'], mp2.inputs['Vector'])
        it = N.new('ShaderNodeTexImage')
        it.name = "RUNE_TEX"
        it.image = rune_image()
        it.extension = 'REPEAT'
        it.interpolation = 'Linear'
        L.new(mp2.outputs['Vector'], it.inputs['Vector'])
        mx = N.new('ShaderNodeMix')                      # engraved glyphs catch the light a little
        mx.data_type = 'RGBA'
        mx.inputs['B'].default_value = _hex('#8d939e')
        f = N.new('ShaderNodeMath')
        f.operation = 'MULTIPLY'
        f.inputs[1].default_value = 0.55
        L.new(it.outputs['Color'], f.inputs[0])
        L.new(f.outputs['Value'], mx.inputs['Factor'])
        L.new(col, mx.inputs['A'])
        col = mx.outputs['Result']
        glow_out = it.outputs['Color']
    grp = N.new('ShaderNodeGroup')
    grp.node_tree = paint_group()
    grp.inputs['Edge'].default_value = edge
    L.new(col, grp.inputs['Color'])
    reroute = N.new('NodeReroute')                       # the pass outputs, picked by set_pass
    reroute.name = "OUT_color"
    L.new(grp.outputs['Color'], reroute.inputs[0])
    g = N.new('NodeReroute')
    g.name = "OUT_glow"
    if glow_out is not None:
        L.new(glow_out, g.inputs[0])
    elif glow == 0 and metal >= 0.2:                    # metal: its worn edges glow faintly on an enchanted model (only
        bev = N.new('ShaderNodeBevel')                   # the "_Rune" models use this map, so the plain ones are unaffected)
        bev.samples = 8
        bev.inputs['Radius'].default_value = 0.003
        geo = N.new('ShaderNodeNewGeometry')
        dot = N.new('ShaderNodeVectorMath')
        dot.operation = 'DOT_PRODUCT'
        L.new(bev.outputs['Normal'], dot.inputs[0])
        L.new(geo.outputs['Normal'], dot.inputs[1])
        e = N.new('ShaderNodeMapRange')
        e.inputs['From Min'].default_value = 0.999
        e.inputs['From Max'].default_value = 0.94
        e.inputs['To Min'].default_value = 0.0
        e.inputs['To Max'].default_value = 0.4
        L.new(dot.outputs['Value'], e.inputs['Value'])
        L.new(e.outputs['Result'], g.inputs[0])
    else:
        c = N.new('ShaderNodeRGB')
        c.outputs[0].default_value = (1, 1, 1, 1) if glow == 1 else (0, 0, 0, 1)
        L.new(c.outputs[0], g.inputs[0])
    ms = N.new('ShaderNodeRGB')
    ms.outputs[0].default_value = (metal, smooth, 0.0, 1.0)
    r2 = N.new('NodeReroute')
    r2.name = "OUT_ms"
    L.new(ms.outputs[0], r2.inputs[0])
    _route(m, "color")
    m["wpn_glow"] = str(glow)
    m["wpn_ms"] = (metal, smooth)
    m.diffuse_color = _hex(light)
    return m


def _route(m, pas):
    nt = m.node_tree
    em = nt.nodes["EMIT"]
    src = nt.nodes["OUT_" + pas]
    for l in list(em.inputs['Color'].links):
        nt.links.remove(l)
    nt.links.new(src.outputs[0], em.inputs['Color'])


def build_materials():
    return {k: _material(k, v) for k, v in PALETTE.items()}


def set_pass(pas):
    """Relink every source material's emission to its colour, glow or metallic/smoothness output."""
    for m in bpy.data.materials:
        if m.name.startswith("WS_") and m.node_tree and "EMIT" in m.node_tree.nodes:
            _route(m, pas)
