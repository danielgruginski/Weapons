"""Orc-made weapons and the war horn (2026-10-10, Daniel: "go ahead with the orc weapons and the horn"). Crude: rust-
pitted iron hammered thick, rough hafts bound in cord, bone; plain models (no enchanted copies). Same socket frame as
every model (wpn_common): origin where the fist closes, +Y along the handle toward the business end, the edge or the
bit toward +X, the flats +-Z.

OrcCleaver    a broad, heavy single-edged blade squared at the end, its spine toothed, rivets by the hilt, a crude bar
              guard, a cord grip, an iron ball pommel (one hand)
OrcAxe        a big moon-shaped iron head with a long lower horn, a hooked back spike, cord bindings (one hand)
SpikedClub    a thick club of dark wood swelling to the head, iron-banded and studded with nails (one hand)
OrcWarAxe     a double-bitted war axe on a long haft, a spike on top, cord and a bone ring on the grip (two hands)
WarHorn       a curved aurochs horn with iron bands and a brass mouthpiece; held in the LEFT fist, the bell up and out
              (the horn-blower's)
"""
import math
from mathutils import Vector, Matrix
import numpy as np
from wpn_parts import Builder, crossguard, grip, collar, pommel, haft, rings, langets, butt_cap, sheet
from wpn_common import loft, ellipsoid, cone, box, torus, lerp, smoothstep


def _head(b, mat, top, rows, side=1.0):
    """An axe bit lofted along +-X from the eye (rows (x, y_lo, y_hi, t) relative to `top`); side -1 = the back bit."""
    rr = [(side * x, top + lo, top + hi, t) for x, lo, hi, t in rows]
    if side < 0:
        rr = rr[::-1]
    return b.part(mat, sheet, rr, 'X', ('flat', 'flat'), 0.003, 2)


def _eye(b, mat, top, r=0.022, h=0.07):
    b.part(mat, loft, [(0, top - h / 2, 0, r, r * 0.95, r * 0.95), (0, top + h / 2, 0, r, r * 0.95, r * 0.95)],
           up=(0, 0, 1), seg=8, per_seg=1, cap0=0.3, cap1=0.3)


def _rivets(b, mat, pts, r=0.0042):
    for x, y, z in pts:
        b.part(mat, ellipsoid, (x, y, z), (r, r, r * 0.7), None, 6, 3)


def _bindings(b, ys, r):
    """Cord lashed round a haft in short bands."""
    for y in ys:
        collar(b, 'cord', y, r * 1.12, 0.022, 8, 1.0)


def orc_cleaver(magic=False):
    b = Builder(magic)
    base, L = 0.055, 0.45
    rows = []
    for k, u in enumerate(np.linspace(0.0, 1.0, 19)):
        y = base + L * u
        edge = 0.034 + 0.05 * smoothstep(0.0, 0.85, u)              # widening toward the end
        spine = -0.026 - 0.006 * u
        if 0.15 < u < 0.9 and k % 2:                                  # a toothed spine
            spine -= 0.011
        t = lerp(0.0085, 0.005, u)
        rows.append((y, spine, edge, t))
    rows.append((base + L + 0.004, -0.024, 0.07, 0.004))               # squared, a little clipped at the edge
    b.part('iron', sheet, rows, 'Y', ('spine', 'edge'), 0.008, 1)
    _rivets(b, 'iron', [(x, base + 0.03, s * 0.0052) for x in (-0.008, 0.016) for s in (1, -1)])
    b.part('iron', box, (0.004, base - 0.006, 0), (0.1, 0.016, 0.022))          # a bar of a guard
    grip(b, 'cord', -0.09, base - 0.014, r=0.0165, ridges=6)
    pommel(b, 'iron', -0.105, 'ball', r=0.021)
    return b


def orc_axe(magic=False):
    b = Builder(magic)
    haft(b, 'wood_dark', -0.12, 0.54, r0=0.0175, r1=0.016, seed=21, wobble=0.002)
    grip(b, 'leather_dark', -0.11, 0.02, r=0.0185, ridges=4)
    _bindings(b, (0.12, 0.3), 0.0168)
    top = 0.47
    _eye(b, 'iron', top, 0.023, 0.08)
    _head(b, 'iron', top, [(0.014, -0.034, 0.034, 0.028), (0.045, -0.026, 0.024, 0.018), (0.085, -0.075, 0.04, 0.01),
                           (0.13, -0.16, 0.075, 0.006), (0.158, -0.19, 0.088, 0.0035)])
    b.part('iron', cone, (-0.016, top + 0.01, 0), (-0.1, top - 0.03, 0), 0.016, 0.0, 6)          # the back hook
    b.part('iron', cone, (0, top + 0.035, 0), (0, top + 0.1, 0), 0.012, 0.0, 6)                 # a short top spike
    _rivets(b, 'iron', [(0.03, top + y, s * 0.012) for y in (-0.02, 0.02) for s in (1, -1)])
    return b


def spiked_club(magic=False):
    b = Builder(magic)
    y0, y1, r0, r1 = -0.12, 0.5, 0.017, 0.046
    haft(b, 'wood_dark', y0, y1, r0=r0, r1=r1, seg=10, wobble=0.003, seed=23)
    grip(b, 'leather', -0.11, 0.03, r=0.0185, ridges=4)
    r_at = lambda y: lerp(r0, r1, (y - y0) / (y1 - y0))
    for y in (0.27, 0.47):
        collar(b, 'iron', y, r_at(y) * 1.06, 0.018, 10, 1.0)
    rng = np.random.default_rng(4)
    k = 0
    for y in np.linspace(0.31, 0.44, 4):                             # nails driven through the head, staggered rows
        for j in range(6):
            a = 2 * math.pi * (j + 0.5 * (k % 2)) / 6 + rng.uniform(-0.15, 0.15)
            d = Vector((math.cos(a), 0.18, math.sin(a))).normalized()
            p = Vector((0, y, 0)) + Vector((math.cos(a), 0, math.sin(a))) * r_at(y) * 0.9
            b.part('iron', cone, p, p + d * (0.03 + rng.uniform(0, 0.01)), 0.0055, 0.0, 5)
        k += 1
    b.part('iron', cone, (0, y1 - 0.01, 0), (0, y1 + 0.05, 0), 0.008, 0.0, 6)                    # one on top
    return b


def orc_war_axe(magic=False):
    b = Builder(magic)
    haft(b, 'wood', -0.58, 0.66, r0=0.019, r1=0.0175, seed=25, wobble=0.0025)
    grip(b, 'cord', -0.27, 0.04, r=0.0205, ridges=7)
    collar(b, 'bone', 0.06, 0.024, 0.02, 8, 1.0)                     # a bone ring above the grip
    butt_cap(b, 'iron', -0.58, 0.019, spike=True)
    top = 0.58
    _eye(b, 'iron', top, 0.026, 0.1)
    for side in (1.0, -1.0):                                         # two moon-shaped bits, the front one bigger
        k = 1.0 if side > 0 else 0.82
        _head(b, 'iron', top, [(0.016, -0.04 * k, 0.04 * k, 0.03), (0.055, -0.03 * k, 0.03 * k, 0.018),
                               (0.11 * k, -0.11 * k, 0.09 * k, 0.009), (0.17 * k, -0.19 * k, 0.15 * k, 0.005),
                               (0.2 * k, -0.2 * k, 0.16 * k, 0.003)], side)
    b.part('iron', cone, (0, top + 0.045, 0), (0, top + 0.16, 0), 0.016, 0.0, 6)                 # the top spike
    langets(b, 'iron', top - 0.2, top - 0.05, 0.018)
    _bindings(b, (top - 0.24,), 0.0182)
    return b


def war_horn(magic=False):
    """A curved horn held in the left fist: the mouthpiece just below the fist, the bell up and out toward +X."""
    b = Builder(magic)
    P = [(0.0, -0.13), (0.0, -0.05), (0.006, 0.04), (0.025, 0.13), (0.06, 0.2), (0.11, 0.25), (0.165, 0.27)]
    R = [0.009, 0.013, 0.018, 0.026, 0.035, 0.044, 0.052]
    rows = [(x, y, 0.0, r, r, r) for (x, y), r in zip(P, R)]
    b.part('horn', loft, rows, up=(0, 0, 1), seg=12, per_seg=3, cap0=0.3, cap1=0.0)
    b.part('leather_dark', loft, [(0.162, 0.268, 0, 0.044, 0.044, 0.044), (0.166, 0.272, 0, 0.044, 0.044, 0.044)],
           up=(0, 0, 1), seg=12, per_seg=1, cap0=0.0, cap1=0.0)                                     # the dark inside
    # iron bands round the horn (short lofts on its own path, a little proud of it), a brass mouthpiece and bell rim
    path = np.array(P)
    for f in (0.3, 0.55, 0.8):
        i = f * (len(P) - 1)
        i0 = int(i)
        t = i - i0
        p = path[i0] * (1 - t) + path[i0 + 1] * t
        d = path[i0 + 1] - path[i0]
        d = d / np.linalg.norm(d)
        r = R[i0] * (1 - t) + R[i0 + 1] * t + 0.0035
        a, c = p - d * 0.008, p + d * 0.008
        b.part('iron', loft, [(a[0], a[1], 0, r, r, r), (c[0], c[1], 0, r, r, r)], up=(0, 0, 1), seg=12, per_seg=1,
               cap0=0.2, cap1=0.2)
    b.part('brass', loft, [(0, -0.155, 0, 0.0105, 0.0105, 0.0105), (0, -0.125, 0, 0.0095, 0.0095, 0.0095)],
           up=(0, 0, 1), seg=10, per_seg=1, cap0=0.4, cap1=0.2)
    d = np.array([0.055, 0.02]) / np.linalg.norm([0.055, 0.02])
    b.part('brass', torus, (0.165, 0.27, 0.0), (d[0], d[1], 0.0), 0.052, 0.005, 14, 5)
    return b


ORC_WEAPONS = [
    ("OrcCleaver", orc_cleaver, 'R', 'plain'),
    ("OrcAxe", orc_axe, 'R', 'plain'),
    ("SpikedClub", spiked_club, 'R', 'plain'),
    ("OrcWarAxe", orc_war_axe, 'R', 'plain'),
    ("WarHorn", war_horn, 'L', 'plain'),
]
