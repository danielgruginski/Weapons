"""The weapons: one builder per model, all in socket space (wpn_common). Tiers by material and make:
iron (plain smithing), steel (better steel, cleaner lines), fine (bright steel, gilt or silver fittings, stones).
A builder called with magic=True adds the rune inlays (and crystals) the enchanted copies glow through.

WEAPONS rows: (name, builder, hand, mode). hand: 'R' right fist, 'L' left fist (bows, crossbows), 'M' a missile;
mode: 'plain' (no enchanted copy), 'both', 'rune' (only the enchanted model).
"""
import math
from mathutils import Vector, Matrix
import numpy as np
from wpn_parts import (Builder, blade, crossguard, grip, collar, pommel, haft, rings, langets, butt_cap, flanges, spikes,
                       rounded_block, gem, crystal, sheet, sheet_runes, fuller_runes, shaft_runes, ribbon)
from wpn_common import loft, ellipsoid, cone, box, torus, slab, prism, lerp, smoothstep


# ----------------------------------------------------------------------------------------- one-handed swords
def arming_sword(magic=False):
    """Iron arming sword: straight double edge, short fuller, plain bar guard, wheel pommel."""
    b = Builder(magic)
    blade(b, 'iron', 0.72, 0.046, base=0.062, taper=0.6, tip=0.12, fuller=0.55, fw=0.0065, fd=0.0011)
    crossguard(b, 'iron', 0.058, 0.092, r=0.0065, thick=0.012, flare=1.15, block=1.4)
    grip(b, 'leather', -0.052, 0.052, r=0.0142, ridges=5)
    pommel(b, 'iron', -0.074, 'wheel', r=0.024)
    return b


def knight_sword(magic=False):
    """Steel knightly sword: longer, tapering to a keen point, a long fuller, arms curved toward the blade,
    wire-bound grip, pear pommel."""
    b = Builder(magic)
    blade(b, 'steel', 0.8, 0.05, base=0.066, taper=0.48, tip=0.16, fuller=0.66, fw=0.0075, fd=0.0013)
    crossguard(b, 'steel', 0.06, 0.112, r=0.0065, thick=0.012, curve=0.014, flare=1.35, block=1.5)
    grip(b, 'leather_dark', -0.06, 0.054, r=0.0142, ridges=6, wire=('wire', 2))
    pommel(b, 'steel', -0.086, 'pear', r=0.022, gem='crystal' if magic else None)
    return b


def falchion(magic=False):
    """Steel falchion: one edge (+X), the blade widening toward a clipped point, a short curved guard."""
    b = Builder(magic)
    R = blade(b, 'steel', 0.6, 0.044, base=0.06, taper=1.0, tip=0.13, fuller=0.0, fw=0.0, single=True, curve=0.02,
              belly=0.32, thick=0.0062, bev=0.009)
    crossguard(b, 'steel', 0.054, 0.075, r=0.0062, thick=0.011, curve=-0.012, flare=1.25, block=1.4)
    grip(b, 'leather', -0.05, 0.048, r=0.0142, ridges=5)
    pommel(b, 'steel', -0.07, 'cap', r=0.018)
    if magic:                                           # a band of runes along the flat, by the spine
        sheet_runes(b, R, [(0.11 + 0.4 * k / 8, 0.24) for k in range(9)], 0.0042)
    return b


def masterwork_sword(magic=False):
    """Fine sword: bright steel, a twin fuller look, gilt guard with ball finials, red grip bound in gilt wire,
    a gilt wheel pommel set with stones."""
    b = Builder(magic)
    blade(b, 'steel_fine', 0.82, 0.052, base=0.07, taper=0.5, tip=0.15, fuller=0.7, fw=0.009, fd=0.0014, ricasso=0.03)
    crossguard(b, 'gold', 0.062, 0.118, r=0.0068, thick=0.013, curve=0.02, flare=1.2, block=1.7, finial=('gold', 0.0085))
    collar(b, 'gold', 0.053, 0.0165, 0.007)
    grip(b, 'leather_red', -0.058, 0.05, r=0.0142, ridges=5, wire=('gold', 3))
    pommel(b, 'gold', -0.082, 'wheel', r=0.026, gem='crystal' if magic else 'gem_red')
    return b


def sabre(magic=False):
    """Red Garrick's sabre: a curved single-edged blade, a gilt knuckle bow sweeping from the guard to the pommel,
    red grip, a red stone in the pommel."""
    b = Builder(magic)
    blade(b, 'steel_fine', 0.7, 0.04, base=0.06, taper=0.7, tip=0.14, fuller=0.6, fw=0.005, fd=0.001, single=True,
          curve=0.075, thick=0.0058, bev=0.008)
    crossguard(b, 'gold', 0.056, 0.05, r=0.006, thick=0.011, curve=0.0, flare=1.0, block=1.6, finial=('gold', 0.007))
    grip(b, 'leather_red', -0.05, 0.048, r=0.0138, ridges=6, wire=('gold', 2))
    pommel(b, 'gold', -0.068, 'cap', r=0.018)
    # knuckle bow: from the guard's +X arm round in front of the fist to the pommel
    pts = []
    for k in range(9):
        t = k / 8
        y = lerp(0.056, -0.066, t)
        x = 0.05 + 0.03 * math.sin(math.pi * t)
        pts.append((x, y, 0.0, 0.0042, 0.0042, 0.0042))
    pts[-1] = (0.012, -0.068, 0.0, 0.004, 0.004, 0.004)
    b.part('gold', loft, pts, up=(0, 0, 1), seg=6, per_seg=1, cap0=0.4, cap1=0.4)
    gem(b, 'gem_red' if not magic else 'crystal', (0, -0.072, 0.0), 0.009, (0, -1, 0))
    return b


# ----------------------------------------------------------------------------------------- daggers
def iron_dagger(magic=False):
    b = Builder(magic)
    blade(b, 'iron', 0.22, 0.032, base=0.05, taper=0.55, tip=0.07, fuller=0.0, fw=0.0, thick=0.0055, bev=0.006)
    crossguard(b, 'iron', 0.046, 0.042, r=0.0055, thick=0.01, flare=1.2, block=1.3)
    grip(b, 'leather', -0.045, 0.042, r=0.0128, ridges=4)
    pommel(b, 'iron', -0.06, 'ball', r=0.014)
    return b


def rondel(magic=False):
    """Steel rondel dagger: a stiff triangular blade with a midrib, disc guard and disc pommel."""
    b = Builder(magic)
    R = blade(b, 'steel', 0.26, 0.026, base=0.052, taper=0.45, tip=0.1, fuller=0.8, fw=0.004, fd=-0.0012, thick=0.0075,
              bev=0.007, runes=False)
    b.part('steel', loft, [(0, y, 0, 0.032, 0.032, 0.032) for y in (0.044, 0.049, 0.054)], up=(0, 0, 1), seg=12,
           per_seg=1, cap0=0.2, cap1=0.2)
    grip(b, 'wood_dark', -0.046, 0.044, r=0.0125, ridges=3, wire=('wire', 3))
    b.part('steel', loft, [(0, y, 0, 0.026, 0.026, 0.026) for y in (-0.06, -0.055, -0.05)], up=(0, 0, 1), seg=12,
           per_seg=1, cap0=0.2, cap1=0.2)
    if magic:
        sheet_runes(b, R, [(0.07 + 0.15 * k / 5, 0.5) for k in range(6)], 0.0016)
        gem(b, 'crystal', (0, -0.064, 0), 0.008, (0, -1, 0))
    return b


def fine_dagger(magic=False):
    """Fine parrying dagger: bright double-edged blade, gilt quillons swept toward the blade, a side ring, a
    stone in the pommel."""
    b = Builder(magic)
    blade(b, 'steel_fine', 0.27, 0.036, base=0.052, taper=0.45, tip=0.09, fuller=0.6, fw=0.005, fd=0.001, thick=0.006)
    crossguard(b, 'gold', 0.048, 0.07, r=0.0052, thick=0.009, curve=0.03, flare=1.1, block=1.6, finial=('gold', 0.006))
    b.part('gold', torus, (0, 0.06, 0.0), (0, 0, 1), 0.02, 0.003, 12, 4)
    grip(b, 'leather_blue', -0.044, 0.042, r=0.0125, ridges=4, wire=('gold', 2))
    pommel(b, 'gold', -0.06, 'faceted', r=0.016, gem='crystal' if magic else 'gem_blue')
    return b


# ----------------------------------------------------------------------------------------- axes
def _axe_head(b, mat, top, rows, poll=None, eye_r=0.02, eye_h=0.06):
    """An axe head lofted along +X from the eye; rows (x, y_lo, y_hi, t) relative to `top` (the haft's head)."""
    rr = [(x, top + lo, top + hi, t) for x, lo, hi, t in rows]
    R = b.part(mat, sheet, rr, 'X', ('flat', 'flat'), 0.003, 2)
    b.part(mat, loft, [(0, top - eye_h / 2, 0, eye_r, eye_r * 0.95, eye_r * 0.95), (0, top + eye_h / 2, 0, eye_r, eye_r * 0.95, eye_r * 0.95)],
           up=(0, 0, 1), seg=8, per_seg=1, cap0=0.3, cap1=0.3)
    if poll == 'block':
        b.part(mat, box, (-eye_r - 0.01, top, 0), (0.026, eye_h * 0.75, eye_r * 1.6))
    elif poll == 'spike':
        b.part(mat, cone, (-eye_r * 0.6, top, 0), (-eye_r - 0.07, top - 0.015, 0), eye_r * 0.8, 0.0, 6)
    return R


def hand_axe(magic=False):
    b = Builder(magic)
    haft(b, 'wood_ash', -0.12, 0.47, r0=0.0155, r1=0.0145, seed=2, wobble=0.0015)
    grip(b, 'leather', -0.1, -0.0, r=0.0168, ridges=3)
    _axe_head(b, 'iron', 0.42, [(0.012, -0.026, 0.026, 0.02), (0.05, -0.02, 0.02, 0.014), (0.1, -0.05, 0.04, 0.008),
                                (0.138, -0.072, 0.052, 0.003)], poll='block')
    return b


def bearded_axe(magic=False):
    """Steel bearded axe: a long beard hooking down from a narrow neck, langets down the haft."""
    b = Builder(magic)
    haft(b, 'wood', -0.13, 0.52, r0=0.016, r1=0.0145, seed=5)
    grip(b, 'leather_dark', -0.11, 0.0, r=0.0172, ridges=4)
    top = 0.46
    R = _axe_head(b, 'steel', top, [(0.012, -0.028, 0.03, 0.022), (0.045, -0.018, 0.018, 0.014), (0.08, -0.06, 0.03, 0.008),
                                (0.12, -0.13, 0.05, 0.004), (0.135, -0.14, 0.056, 0.0025)], poll='block')
    langets(b, 'steel', top - 0.13, top - 0.03, 0.0145)
    if magic:
        sheet_runes(b, R, [(0.095, 0.1), (0.105, 0.35), (0.11, 0.62), (0.112, 0.85)], 0.0032, axis='X')
    return b


# ----------------------------------------------------------------------------------------- maces
def flanged_mace(magic=False):
    b = Builder(magic)
    haft(b, 'iron', -0.1, 0.4, r0=0.0125, r1=0.0115, seg=8)
    grip(b, 'leather', -0.09, 0.03, r=0.0158, ridges=4)
    pommel(b, 'iron', -0.11, 'ball', r=0.017)
    flanges(b, 'iron', 0.33, 0.49, 0.015, 0.05, n=6, t=0.0075, shape='square')
    b.part('iron', ellipsoid, (0, 0.492, 0), (0.017, 0.016, 0.017), None, 8, 5)
    collar(b, 'iron', 0.33, 0.017, 0.012)
    return b


def morning_star(magic=False):
    b = Builder(magic)
    haft(b, 'wood_dark', -0.11, 0.42, r0=0.016, r1=0.015, seed=8)
    grip(b, 'leather_dark', -0.1, 0.02, r=0.0175, ridges=4)
    butt_cap(b, 'steel', -0.115, 0.016)
    langets(b, 'steel', 0.3, 0.41, 0.015, n=4)
    b.part('steel', ellipsoid, (0, 0.47, 0), (0.05, 0.052, 0.05), None, 12, 8)
    spikes(b, 'steel', (0, 0.47, 0), 0.05, n=16, length=0.032, base=0.0085)
    if magic:
        for a in (0.0, math.pi):
            shaft_runes(b, 0.13, 0.29, 0.0152, turns=0.0, half=0.0035, n=6, phase=a)
    return b


def knight_mace(magic=False):
    """Fine knight's mace: an all-steel gothic head of eight pointed flanges, gilt collars, red grip."""
    b = Builder(magic)
    haft(b, 'steel_fine', -0.1, 0.42, r0=0.0125, r1=0.0115, seg=8)
    grip(b, 'leather_red', -0.09, 0.04, r=0.0158, ridges=5, wire=('gold', 2))
    pommel(b, 'gold', -0.112, 'faceted', r=0.018, gem='crystal' if magic else 'gem_blue')
    flanges(b, 'steel_fine', 0.34, 0.5, 0.016, 0.046, n=8, t=0.0055, shape='gothic')
    if magic:
        crystal(b, 'crystal', (0, 0.5, 0), (0, 0.55, 0), 0.011)
    else:
        b.part('gold', cone, (0, 0.49, 0), (0, 0.54, 0), 0.014, 0.0, 8)
    rings(b, 'gold', (0.33, 0.06), 0.0168, 0.01)
    if magic:
        for a in (0.0, math.pi):
            shaft_runes(b, 0.1, 0.3, 0.0123, turns=0.5, half=0.003, n=12, phase=a)
    return b




# ----------------------------------------------------------------------------------------- two-handed (the 2H clips
# hold the right fist on top, the left 10-18 cm below it: grips run down to y = -0.24)
def two_hand_sword(magic=False):
    """Iron two-handed sword: a long plain blade, a straight wide guard, a long leather grip."""
    b = Builder(magic)
    blade(b, 'iron', 0.98, 0.05, base=0.072, taper=0.6, tip=0.15, fuller=0.5, fw=0.007, fd=0.0012, thick=0.0075)
    crossguard(b, 'iron', 0.066, 0.15, r=0.0075, thick=0.014, flare=1.15, block=1.4)
    grip(b, 'leather', -0.235, 0.058, r=0.0152, ridges=10)
    collar(b, 'iron', -0.09, 0.0165, 0.01)
    pommel(b, 'iron', -0.258, 'ball', r=0.022)
    return b


def greatsword(magic=False):
    """Steel greatsword: a leather-bound ricasso under parrying lugs, a long fuller, a wide guard with flared
    ends, a wire-bound grip and a pear pommel."""
    b = Builder(magic)
    R = blade(b, 'steel', 1.1, 0.056, base=0.078, taper=0.5, tip=0.18, fuller=0.62, fw=0.0085, fd=0.0014, thick=0.0078,
              ricasso=0.15, runes=False)
    if magic:
        fuller_runes(b, R, 0.25, 0.078 + 1.1 * 0.58)
    grip(b, 'leather_dark', 0.085, 0.2, r=0.0105, ridges=4, flat=0.55, swell=0.0)      # the ricasso's wrap
    for sg in (1, -1):                                                                     # parrying lugs
        b.part('steel', cone, (sg * 0.02, 0.215, 0), (sg * 0.05, 0.2, 0), 0.007, 0.0015, 6)
    crossguard(b, 'steel', 0.07, 0.18, r=0.0075, thick=0.014, curve=0.02, flare=1.4, block=1.5)
    grip(b, 'leather_dark', -0.24, 0.062, r=0.0152, ridges=10, wire=('wire', 3))
    pommel(b, 'steel', -0.27, 'pear', r=0.025, gem='crystal' if magic else None)
    return b


def flamberge(magic=False):
    """Fine flamberge: a snaking blade, gilt swept quillons with side rings, a black and gilt grip, a stone in a
    gilt wheel pommel."""
    b = Builder(magic)
    R = blade(b, 'steel_fine', 1.12, 0.054, base=0.08, taper=0.55, tip=0.17, fuller=0.0, fw=0.0, thick=0.0075,
              ricasso=0.14, wave=(0.0065, 5, 0.17), runes=False)
    grip(b, 'leather_red', 0.088, 0.21, r=0.0105, ridges=4, flat=0.55, swell=0.0)
    for sg in (1, -1):
        b.part('gold', cone, (sg * 0.02, 0.225, 0), (sg * 0.055, 0.21, 0), 0.0075, 0.0015, 6)
        b.part('gold', torus, (sg * 0.042, 0.1, 0), (0, 0, 1), 0.026, 0.0035, 12, 4)
    crossguard(b, 'gold', 0.072, 0.19, r=0.0075, thick=0.014, curve=0.05, flare=1.2, block=1.7, finial=('gold', 0.01))
    grip(b, 'leather_dark', -0.24, 0.064, r=0.0152, ridges=10, wire=('gold', 4))
    pommel(b, 'gold', -0.272, 'wheel', r=0.03, gem='crystal' if magic else 'gem_red')
    if magic:
        sheet_runes(b, R, [(0.25 + 0.6 * k / 24, 0.5) for k in range(25)], 0.0035)
    return b


def maul(magic=False):
    """Iron maul: a long haft, a heavy square head banded on."""
    b = Builder(magic)
    haft(b, 'wood', -0.56, 0.55, r0=0.018, r1=0.017, seed=11)
    grip(b, 'leather', -0.26, 0.04, r=0.0195, ridges=6)
    butt_cap(b, 'iron', -0.56, 0.018)
    rounded_block(b, 'iron', (0, 0.56, 0), (0.21, 0.09, 0.09), axis='X', shape=0.55, seg=8, bulge=0.05)
    langets(b, 'iron', 0.42, 0.53, 0.017)
    return b


def war_maul(magic=False):
    """Steel war maul: a striking head, a back spike, a top spike, steel langets, a ringed grip."""
    b = Builder(magic)
    haft(b, 'wood_dark', -0.56, 0.56, r0=0.018, r1=0.017, seed=12)
    grip(b, 'leather_dark', -0.26, 0.04, r=0.0195, ridges=6, wire=('steel', 2))
    butt_cap(b, 'steel', -0.56, 0.018, spike=True)
    rounded_block(b, 'steel', (0.045, 0.57, 0), (0.12, 0.085, 0.085), axis='X', shape=0.5, seg=8, bulge=0.08)
    b.part('steel', cone, (-0.01, 0.57, 0), (-0.13, 0.555, 0), 0.03, 0.0, 6)
    b.part('steel', cone, (0, 0.6, 0), (0, 0.69, 0), 0.016, 0.0, 6)
    langets(b, 'steel', 0.4, 0.54, 0.017, n=4)
    if magic:
        for a in (math.pi / 2, -math.pi / 2):
            shaft_runes(b, 0.08, 0.38, 0.0172, turns=0.0, half=0.004, n=6, phase=a)
    return b


def dane_axe(magic=False):
    """Steel great axe: a broad crescent bit on a long haft, langets, a pointed butt."""
    b = Builder(magic)
    haft(b, 'wood', -0.58, 0.64, r0=0.0175, r1=0.016, seed=13)
    grip(b, 'leather_dark', -0.26, 0.04, r=0.019, ridges=6)
    butt_cap(b, 'steel', -0.58, 0.0175, spike=True)
    top = 0.58
    R = _axe_head(b, 'steel', top, [(0.014, -0.035, 0.035, 0.026), (0.05, -0.022, 0.022, 0.016), (0.1, -0.08, 0.06, 0.009),
                                    (0.16, -0.15, 0.1, 0.0045), (0.19, -0.17, 0.115, 0.0025)], poll=None, eye_r=0.023, eye_h=0.075)
    langets(b, 'steel', top - 0.18, top - 0.04, 0.0165)
    if magic:
        sheet_runes(b, R, [(0.13, 0.12), (0.14, 0.35), (0.145, 0.6), (0.142, 0.85)], 0.0038, axis='X')
    return b


# ----------------------------------------------------------------------------------------- polearms and staves (the
# polearm clips hold the right fist low, the left 36 cm above it)
def iron_spear(magic=False):
    b = Builder(magic)
    haft(b, 'wood_ash', -0.6, 1.08, r0=0.0155, r1=0.0145, seed=21, wobble=0.001)
    b.part('iron', cone, (0, 1.02, 0), (0, 1.13, 0), 0.0165, 0.011, 8)
    blade(b, 'iron', 0.26, 0.042, base=1.12, taper=0.75, tip=0.12, fuller=0.8, fw=0.004, fd=-0.0015, thick=0.008, bev=0.008,
          runes=False)
    butt_cap(b, 'iron', -0.6, 0.0155)
    return b


def winged_spear(magic=False):
    """Steel winged spear: a long leaf head with a raised midrib, wings below it, a bound socket."""
    b = Builder(magic)
    haft(b, 'wood_dark', -0.6, 1.1, r0=0.016, r1=0.015, seed=22)
    b.part('steel', cone, (0, 1.03, 0), (0, 1.16, 0), 0.0175, 0.012, 8)
    rings(b, 'brass', (1.04, 1.075), 0.0185, 0.008)
    R = blade(b, 'steel', 0.32, 0.05, base=1.15, taper=0.62, tip=0.16, fuller=0.85, fw=0.006, fd=-0.0018, thick=0.0085,
              bev=0.009, runes=False)
    for sg in (1, -1):                                   # the wings: small flat lugs either side of the socket
        rows = [(1.07, 0.0, 0.012, 0.007), (1.095, 0.0, 0.058, 0.005), (1.115, 0.0, 0.05, 0.0025)]
        if sg < 0:
            rows = [(y, -hi, -lo, t) for y, lo, hi, t in rows]
        b.part('steel', sheet, rows, 'Y', ('flat', 'flat'), 0.004, 1)
    rings(b, 'leather_dark', (-0.05, 0.0, 0.32, 0.37), 0.0172, 0.03)
    butt_cap(b, 'steel', -0.6, 0.016, spike=True)
    if magic:
        sheet_runes(b, R, [(1.19 + 0.17 * k / 5, 0.5) for k in range(6)], 0.0022)
        shaft_runes(b, 0.55, 0.95, 0.0153, turns=1.0, half=0.0035, n=16)
    return b


def halberd(magic=False):
    """Steel halberd: an axe blade, a back hook and a long top spike on a two-metre pole with langets."""
    b = Builder(magic)
    haft(b, 'wood', -0.62, 1.2, r0=0.017, r1=0.0155, seed=23)
    top = 1.08
    R = _axe_head(b, 'steel', top, [(0.014, -0.06, 0.06, 0.018), (0.04, -0.07, 0.05, 0.012), (0.11, -0.09, 0.05, 0.007),
                                    (0.16, -0.1, 0.075, 0.003)], poll=None, eye_r=0.0185, eye_h=0.12)
    hook = [(-0.12, top + 0.06, top + 0.064, 0.003), (-0.1, top + 0.03, top + 0.05, 0.006), (-0.06, top, top + 0.03, 0.009),
            (-0.014, top - 0.01, top + 0.03, 0.012)]
    b.part('steel', sheet, hook, 'X', ('flat', 'flat'), 0.003, 2)                       # the back hook
    blade(b, 'steel', 0.32, 0.034, base=top + 0.06, taper=0.7, tip=0.12, fuller=0.8, fw=0.004, fd=-0.0014, thick=0.009,
          bev=0.008, runes=False)
    langets(b, 'steel', top - 0.3, top - 0.06, 0.0158)
    rings(b, 'leather_dark', (-0.02, 0.36), 0.0178, 0.05)
    butt_cap(b, 'steel', -0.62, 0.017)
    if magic:
        sheet_runes(b, R, [(0.125, 0.12), (0.13, 0.4), (0.132, 0.65), (0.13, 0.88)], 0.0035, axis='X')
    return b


def quarterstaff(magic=False):
    b = Builder(magic)
    haft(b, 'wood_ash', -0.62, 1.12, r0=0.0165, r1=0.0165, seed=31, wobble=0.0012)
    butt_cap(b, 'iron', -0.62, 0.0165, 0.06)
    b.part('iron', loft, [(0, 1.06, 0, 0.0178, 0.0178, 0.0178), (0, 1.13, 0, 0.0185, 0.0185, 0.0185)], up=(0, 0, 1), seg=8,
           per_seg=1, cap0=0.2, cap1=0.6)
    rings(b, 'leather', (0.0, 0.36), 0.0178, 0.09)
    return b


def wizard_staff(magic=False):
    """Gnarled oak staff: three roots twisting up round a stone at the head."""
    b = Builder(magic)
    rng = np.random.default_rng(41)
    ys = np.linspace(-0.62, 1.0, 9)
    rows = [(0.012 * math.sin(y * 4.3) + rng.uniform(-0.004, 0.004), y, 0.008 * math.cos(y * 3.1),
             0.0175 + rng.uniform(-0.002, 0.002) + 0.004 * smoothstep(0.85, 1.0, y), 0.017, 0.017) for y in ys]
    b.part('wood', loft, rows, up=(0, 0, 1), seg=8, per_seg=2, cap0=0.4, cap1=0.3)
    top = Vector((rows[-1][0], 1.0, rows[-1][2]))
    stone = top + Vector((0, 0.1, 0))
    for k in range(3):                                   # three prongs cupping the stone
        a = k * 2 * math.pi / 3 + 0.4
        pts = []
        for t in np.linspace(0, 1, 5):
            r = 0.012 + 0.036 * math.sin(math.pi * min(1.0, t * 1.1))
            aa = a + t * 0.9
            w = 0.006 * (1 - 0.6 * t)
            pts.append((top.x + math.cos(aa) * r, top.y + t * 0.15, top.z + math.sin(aa) * r, w, w, w))
        b.part('wood', loft, pts, up=(0, 0, 1), seg=5, per_seg=2, cap0=0.4, cap1=0.6)
    crystal(b, 'crystal' if magic else 'gem_blue', stone - Vector((0, 0.045, 0)), stone + Vector((0, 0.065, 0)), 0.026)
    rings(b, 'leather', (0.0, 0.36), 0.019, 0.08)
    if magic:
        for ph in (0.0, math.pi):
            shaft_runes(b, 0.45, 0.92, 0.0182, turns=1.2, half=0.0032, n=18, phase=ph)
    return b


def arcane_staff(magic=False):
    """Fine arcane staff: straight black wood bound in silver, a silver crescent holding a large stone."""
    b = Builder(magic)
    haft(b, 'wood_dark', -0.62, 1.04, r0=0.0155, r1=0.0165, seed=42)
    butt_cap(b, 'silver', -0.62, 0.0155, 0.05)
    rings(b, 'silver', (-0.1, 0.18, 0.55, 0.9, 1.0), 0.0178, 0.012)
    rings(b, 'leather_blue', (0.0, 0.36), 0.0172, 0.09)
    stone = Vector((0, 1.17, 0))
    pts = []                                             # the crescent: a ring open at the top, in the XY plane
    for a in np.linspace(math.radians(-50), math.radians(230), 11):
        pts.append((math.cos(a) * 0.062, stone.y - 0.02 + math.sin(a) * 0.07, 0, 0.0065, 0.0065, 0.0065))
    b.part('silver', loft, [(0, 1.03, 0, 0.012, 0.012, 0.012), (0, stone.y - 0.09, 0, 0.008, 0.008, 0.008)], up=(0, 0, 1),
           seg=6, per_seg=1, cap0=0.3, cap1=0.3)
    b.part('silver', loft, pts, up=(0, 0, 1), seg=6, per_seg=2, cap0=0.5, cap1=0.5)
    crystal(b, 'crystal' if magic else 'gem_blue', stone - Vector((0, 0.05, 0)), stone + Vector((0, 0.06, 0)), 0.028)
    if magic:
        for ph in (0.0, math.pi):
            shaft_runes(b, 0.62, 0.86, 0.0167, turns=0.0, half=0.0032, n=6, phase=ph)
    return b


# ----------------------------------------------------------------------------------------- bows (left fist; the
# stave bows toward +X, the archer; the string runs between the tips: meta string_top / string_bottom)
def _bow_x(u, bend, recurve):
    return bend * u ** 1.8 - recurve * smoothstep(0.72, 1.0, u) ** 1.5


def _stave(b, mat, half, bend, r0=0.016, r1=0.007, recurve=0.0, n=15, flat=0.75):
    rows = []
    for y in np.linspace(-half, half, n):
        u = abs(y) / half
        r = lerp(r0, r1, u)
        rows.append((_bow_x(u, bend, recurve), y, 0.0, r * 1.25, r * flat, r * flat))
    b.part(mat, loft, rows, up=(1, 0, 0), seg=8, per_seg=2, cap0=0.3, cap1=0.3)
    return bend - recurve


def _nocks(b, mat, half, xt, bend, recurve=0.0):
    for sg in (1, -1):
        u0 = 0.93
        base = Vector((_bow_x(u0, bend, recurve), sg * half * u0, 0))
        tip = Vector((xt, sg * half, 0))
        b.part(mat, cone, base, tip + (tip - base).normalized() * 0.014, 0.0085, 0.003, 6)


def _belly_runes(b, half, bend, r0, r1, y0, y1, recurve=0.0):
    """Rune inlays down the back of both limbs (the side away from the archer, -X)."""
    for sg in (1, -1):
        P, A, N = [], [], []
        for k in range(9):
            y = sg * lerp(y0, y1, k / 8)
            u = abs(y) / half
            r = lerp(r0, r1, u)
            P.append((_bow_x(u, bend, recurve) - r * 0.75, y, 0.0)); A.append((0, 0, r * 0.55)); N.append((-1, 0, 0))
        b.part('rune', ribbon, P, A, N)


def hunting_bow(magic=False):
    b = Builder(magic)
    half, bend = 0.56, 0.13
    xt = _stave(b, 'wood', half, bend, r0=0.015, r1=0.0075)
    grip(b, 'leather', -0.055, 0.055, r=0.018, ridges=4, flat=0.85)
    _nocks(b, 'horn', half, xt, bend)
    b.meta.update(string_top=(xt, half, 0.0), string_bottom=(xt, -half, 0.0))
    return b


def longbow(magic=False):
    """Yew longbow, a man's height: pale sapwood and red heartwood, horn nocks, a leather grip."""
    b = Builder(magic)
    half, bend = 0.8, 0.155
    xt = _stave(b, 'yew', half, bend, r0=0.0175, r1=0.008, n=17)
    grip(b, 'leather_dark', -0.06, 0.06, r=0.0195, ridges=4, flat=0.85)
    _nocks(b, 'horn', half, xt, bend)
    if magic:
        _belly_runes(b, half, bend, 0.0175, 0.008, 0.1, 0.62)
    b.meta.update(string_top=(xt, half, 0.0), string_bottom=(xt, -half, 0.0))
    return b


def recurve_bow(magic=False):
    """Fine composite bow: horn and sinew limbs that sweep back at the tips, bone ears, a gilt-bound grip."""
    b = Builder(magic)
    half, bend, rc = 0.6, 0.2, 0.06
    xt = _stave(b, 'lacquer', half, bend, r0=0.016, r1=0.0075, recurve=rc, n=19, flat=0.7)
    grip(b, 'leather_red', -0.055, 0.055, r=0.019, ridges=4, flat=0.85, wire=('gold', 2))
    _nocks(b, 'bone', half, xt, bend, rc)
    if magic:
        for sg in (1, -1):
            b.part('crystal', ellipsoid, (-0.014, sg * 0.075, 0.0), (0.008, 0.012, 0.008), None, 6, 4)
        _belly_runes(b, half, bend, 0.016, 0.0075, 0.1, 0.42, rc)
    b.meta.update(string_top=(xt, half, 0.0), string_bottom=(xt, -half, 0.0))
    return b


# ----------------------------------------------------------------------------------------- crossbows (left fist on the
# fore-stock; built shooting along +Y with the top +Z, then turned into the hand by CROSSBOW_GRIP: the palm cradles the
# stock from below, the stock running through the fist toward the index finger, the knuckles to the crossbow's right.
# In the left hand's socket the knuckles face -X, so the crossbow's +X goes to -X and its top to -Z: half a turn about Y.)
CROSSBOW_GRIP = Matrix.Rotation(math.pi, 4, 'Y')


def _crossbow(b, wood, prod_mat, half, depth, back, front, heavy):
    rows = [(0, -back, -0.04, 0.022, 0.03, 0.045), (0, -back + 0.1, -0.022, 0.02, 0.026, 0.032),
            (0, -0.16, -0.004, 0.0165, 0.021, 0.024), (0, -0.02, 0.0, 0.017, 0.02, 0.022),
            (0, front - 0.06, 0.002, 0.02, 0.021, 0.024), (0, front, 0.004, 0.022, 0.022, 0.026)]
    b.part(wood, loft, rows, up=(0, 0, 1), seg=8, per_seg=2, cap0=0.25, cap1=0.2, shape=0.62)
    py = front - 0.035
    pz = 0.026
    prow = []
    for x in np.linspace(-half, half, 9):
        u = abs(x) / half
        th = lerp(0.011, 0.006, u)
        prow.append((x, py - depth * u ** 1.8, pz, lerp(0.017 if heavy else 0.019, 0.01, u), th, th))
    b.part(prod_mat, loft, prow, up=(0, 0, 1), seg=6, per_seg=2, cap0=0.3, cap1=0.3, shape=0.75)
    nut = Vector((0, -0.11, 0.027))
    for sg in (1, -1):                                   # the string, spanned back to the nut
        tip = Vector((sg * half * 0.985, py - depth, pz))
        b.part('string', loft, [tuple(tip) + (0.0022,) * 3, tuple(nut + Vector((sg * 0.006, 0, 0))) + (0.0022,) * 3],
               up=(0, 0, 1), seg=4, per_seg=1, cap0=0.3, cap1=0.3)
    b.part('bone', loft, [(0, -0.11, 0.019, 0.009, 0.009, 0.009), (0, -0.11, 0.031, 0.009, 0.009, 0.009)], up=(0, 1, 0),
           seg=8, per_seg=1, cap0=0.3, cap1=0.3)
    b.part('iron', loft, [(0, -0.13, -0.02, 0.0035, 0.0035, 0.0035), (0, -0.22, -0.04, 0.004, 0.004, 0.004),
                          (0, -0.33, -0.048, 0.0035, 0.0035, 0.0035)], up=(0, 0, 1), seg=5, per_seg=2, cap0=0.4, cap1=0.6)
    b.part('cord', torus, (0, py, 0.012), (0, 1, 0), 0.026, 0.006, 10, 4)          # the prod lashed to the stock
    return py, pz


def light_crossbow(magic=False):
    b = Builder(magic)
    _crossbow(b, 'wood', 'wood_dark', 0.28, 0.05, 0.42, 0.26, False)
    b.part('iron', box, (0, 0.24, -0.02), (0.03, 0.012, 0.012))
    b.meta.update(bolt_rest=(0.0, 0.16, 0.03))
    b.transform(CROSSBOW_GRIP)
    return b


def heavy_crossbow(magic=False):
    """Steel-prodded arbalest: a deeper stock with iron cheek plates, a stirrup at the front for spanning."""
    b = Builder(magic)
    py, pz = _crossbow(b, 'wood_dark', 'steel', 0.33, 0.06, 0.48, 0.3, True)
    for sg in (1, -1):
        b.part('iron', box, (sg * 0.0185, -0.12, 0.004), (0.003, 0.14, 0.03))
    pts = []                                             # the stirrup: a U of iron in front of the prod
    for a in np.linspace(0, math.pi, 9):
        pts.append((math.cos(a) * 0.05, py + 0.07 + math.sin(a) * 0.06, 0.004, 0.0055, 0.0055, 0.0055))
    b.part('iron', loft, pts, up=(0, 0, 1), seg=5, per_seg=2, cap0=0.5, cap1=0.5)
    if magic:
        for sg in (1, -1):                               # along the cheek plates
            b.part('rune', ribbon, [(sg * 0.0205, y, 0.004) for y in np.linspace(-0.18, -0.06, 5)],
                   [(0, 0, 0.007)] * 5, [(sg, 0, 0)] * 5)
        b.part('crystal', ellipsoid, (0, -0.36, -0.02), (0.012, 0.016, 0.012), None, 6, 4)
    b.meta.update(bolt_rest=(0.0, 0.18, 0.032))
    b.transform(CROSSBOW_GRIP)
    return b


# ----------------------------------------------------------------------------------------- missiles (+Y along the
# flight, the nock at the origin)
def arrow(magic=False):
    b = Builder(magic)
    b.part('wood_ash', loft, [(0, y, 0, 0.0042, 0.0042, 0.0042) for y in (0.0, 0.35, 0.7)], up=(0, 0, 1), seg=5, per_seg=1,
           cap0=0.2, cap1=0.2)
    b.part('steel', cone, (0, 0.69, 0), (0, 0.76, 0), 0.0065, 0.0, 4)
    for k in range(3):
        rot = Matrix.Rotation(k * 2 * math.pi / 3, 3, 'Y')
        b.part('fletch_grey', box, tuple(Vector((0, 0.06, 0)) + rot @ Vector((0.0, 0.0, 0.0085))), (0.0012, 0.085, 0.011), rot)
    return b


def bolt(magic=False):
    b = Builder(magic)
    b.part('wood', loft, [(0, y, 0, 0.0058, 0.0058, 0.0058) for y in (0.0, 0.16, 0.3)], up=(0, 0, 1), seg=6, per_seg=1,
           cap0=0.2, cap1=0.2)
    b.part('iron', cone, (0, 0.29, 0), (0, 0.345, 0), 0.0085, 0.0, 4)
    for k in range(2):
        rot = Matrix.Rotation(k * math.pi / 2, 3, 'Y')
        b.part('leather', box, (0, 0.035, 0), (0.0015, 0.05, 0.026), rot)
    return b


# ----------------------------------------------------------------------------------------- named weapons (enchanted only)
def sunwarden(magic=True):
    """Sunwarden, a blessed mace: a gilt head of six pointed flanges crowned by a sun disc with a crystal heart,
    a linen-bound grip."""
    b = Builder(True)
    haft(b, 'silver', -0.1, 0.42, r0=0.0125, r1=0.0115, seg=8)
    grip(b, 'linen', -0.09, 0.04, r=0.0158, ridges=5, wire=('gold', 2))
    pommel(b, 'gold', -0.112, 'faceted', r=0.019, gem='crystal')
    flanges(b, 'gold', 0.33, 0.47, 0.015, 0.044, n=6, t=0.0055, shape='gothic')
    sun = Vector((0, 0.53, 0))
    b.part('gold', loft, [(0, 0.455, 0, 0.012, 0.012, 0.012), (0, 0.495, 0, 0.008, 0.008, 0.008)], up=(0, 0, 1), seg=8,
           per_seg=1, cap0=0.3, cap1=0.3)
    b.part('gold', torus, tuple(sun), (0, 0, 1), 0.04, 0.0055, 16, 5)
    for k in range(12):
        a = k * 2 * math.pi / 12
        d = Vector((math.cos(a), math.sin(a), 0))
        if d.y < -0.8:
            continue
        ln = 0.03 if k % 2 == 0 else 0.018
        b.part('gold', cone, sun + d * 0.042, sun + d * (0.045 + ln), 0.0055, 0.0, 4)
    b.part('crystal', ellipsoid, tuple(sun), (0.024, 0.024, 0.012), None, 8, 5)
    rings(b, 'gold', (0.32, 0.06), 0.017, 0.012)
    for ph in (0.0, math.pi):
        shaft_runes(b, 0.1, 0.3, 0.0123, turns=0.5, half=0.003, n=12, phase=ph)
    return b


def thornwood_bow(magic=True):
    """Thornwood, a venomous longbow: a dark gnarled stave grown with thorns, green stones at the grip and tips."""
    b = Builder(True)
    half, bend = 0.78, 0.16
    rng = np.random.default_rng(51)
    rows = []
    for y in np.linspace(-half, half, 19):
        u = abs(y) / half
        r = lerp(0.018, 0.0085, u) * rng.uniform(0.92, 1.08)
        rows.append((bend * u ** 1.8 + 0.004 * math.sin(y * 23), y, 0.003 * math.cos(y * 17), r * 1.2, r * 0.8, r * 0.8))
    b.part('wood_dark', loft, rows, up=(1, 0, 0), seg=7, per_seg=2, cap0=0.3, cap1=0.3)
    for k in range(14):                                  # thorns on the back and the sides
        y = rng.uniform(0.12, 0.7) * (1 if k % 2 else -1)
        u = abs(y) / half
        r = lerp(0.018, 0.0085, u)
        a = rng.uniform(math.radians(100), math.radians(260))
        d = Vector((math.cos(a), rng.uniform(-0.3, 0.3), math.sin(a))).normalized()
        base = Vector((bend * u ** 1.8, y, 0)) + Vector((math.cos(a), 0, math.sin(a))) * r * 0.8
        b.part('bone', cone, base, base + d * rng.uniform(0.018, 0.03), 0.004, 0.0, 4)
    grip(b, 'leather_dark', -0.06, 0.06, r=0.0205, ridges=3, flat=0.85)
    for y in (0.085, -0.085):
        b.part('crystal', ellipsoid, (-0.004, y, 0.0), (0.011, 0.016, 0.011), None, 6, 4)
    for sg in (1, -1):
        b.part('crystal', ellipsoid, (bend - 0.004, sg * half * 0.97, 0), (0.008, 0.014, 0.008), None, 6, 4)
    _belly_runes(b, half, bend, 0.018, 0.0085, 0.11, 0.6)
    b.meta.update(string_top=(bend, half, 0.0), string_bottom=(bend, -half, 0.0))
    return b


def stormcaller(magic=True):
    """Stormcaller, a storm staff: black wood banded in iron, a forked head holding a crystal, copper wire coiled
    under the fork."""
    b = Builder(True)
    haft(b, 'wood_dark', -0.62, 1.0, r0=0.0155, r1=0.017, seed=61)
    butt_cap(b, 'iron', -0.62, 0.0155, 0.05)
    rings(b, 'iron', (-0.2, 0.5, 0.97), 0.0182, 0.014)
    rings(b, 'leather', (0.0, 0.36), 0.0178, 0.09)
    for y in np.linspace(0.8, 0.94, 8):                  # the copper coil
        collar(b, 'bronze', y, 0.0195, 0.006, 8, 1.0)
    stone = Vector((0, 1.13, 0))
    for sg in (1, -1):                                   # the fork's two tines
        pts = [(sg * 0.006, 0.99, 0, 0.011, 0.011, 0.011), (sg * 0.035, 1.06, 0, 0.009, 0.009, 0.009),
               (sg * 0.042, 1.14, 0, 0.007, 0.007, 0.007), (sg * 0.025, 1.21, 0, 0.004, 0.004, 0.004)]
        b.part('wood_dark', loft, pts, up=(0, 0, 1), seg=6, per_seg=2, cap0=0.4, cap1=0.8)
        b.part('iron', torus, (sg * 0.04, 1.12, 0), (0, 1, 0), 0.0095, 0.0025, 8, 4)
    crystal(b, 'crystal', stone - Vector((0, 0.05, 0)), stone + Vector((0, 0.06, 0)), 0.022)
    for ph in (0.0, math.pi):
        shaft_runes(b, 0.55, 0.78, 0.0168, turns=0.0, half=0.0035, n=6, phase=ph)
    return b


# ----------------------------------------------------------------------------------------- the list
WEAPONS = [
    ("ArmingSword", arming_sword, 'R', 'plain'),
    ("KnightSword", knight_sword, 'R', 'both'),
    ("Falchion", falchion, 'R', 'both'),
    ("MasterworkSword", masterwork_sword, 'R', 'both'),
    ("Sabre", sabre, 'R', 'both'),
    ("IronDagger", iron_dagger, 'R', 'plain'),
    ("Rondel", rondel, 'R', 'both'),
    ("FineDagger", fine_dagger, 'R', 'both'),
    ("HandAxe", hand_axe, 'R', 'plain'),
    ("BeardedAxe", bearded_axe, 'R', 'both'),
    ("FlangedMace", flanged_mace, 'R', 'plain'),
    ("MorningStar", morning_star, 'R', 'both'),
    ("KnightMace", knight_mace, 'R', 'both'),
    ("Sunwarden", sunwarden, 'R', 'rune'),
    ("TwoHandSword", two_hand_sword, 'R', 'plain'),
    ("Greatsword", greatsword, 'R', 'both'),
    ("Flamberge", flamberge, 'R', 'both'),
    ("Maul", maul, 'R', 'plain'),
    ("WarMaul", war_maul, 'R', 'both'),
    ("DaneAxe", dane_axe, 'R', 'both'),
    ("IronSpear", iron_spear, 'R', 'plain'),
    ("WingedSpear", winged_spear, 'R', 'both'),
    ("Halberd", halberd, 'R', 'both'),
    ("Quarterstaff", quarterstaff, 'R', 'plain'),
    ("WizardStaff", wizard_staff, 'R', 'both'),
    ("ArcaneStaff", arcane_staff, 'R', 'both'),
    ("Stormcaller", stormcaller, 'R', 'rune'),
    ("HuntingBow", hunting_bow, 'L', 'plain'),
    ("Longbow", longbow, 'L', 'both'),
    ("RecurveBow", recurve_bow, 'L', 'both'),
    ("Thornwood", thornwood_bow, 'L', 'rune'),
    ("LightCrossbow", light_crossbow, 'L', 'plain'),
    ("HeavyCrossbow", heavy_crossbow, 'L', 'both'),
    ("Arrow", arrow, 'M', 'plain'),
    ("Bolt", bolt, 'M', 'plain'),
]
