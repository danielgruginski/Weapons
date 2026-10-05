# Handoff

Where the weapon kit stands and how to pick it up. The README is the reference (rebuild, roster, socket frame,
Unity); this file holds the agreements, the conventions that bite, the open issues and the checks.

## Working agreements

- Daniel asked (2026-10-04) for "a number of weapons proper to an RPG": long bows, crossbows, maces, greatswords,
  magical versions, better versions, variety; the roster and the numbers were left to me. He reviews in Unity.
- Keep Blender work visible: the **Weapons** scene in `blender/weapons.blend` shows the catalog.
- Report triangle counts when adding models. The game camera is 22 m away at 30 degrees FOV: a sword is a few dozen
  pixels long; silhouette and colour matter more than modelled detail.
- Commits in batches when he asks ("commit" = commit and push). Repository: github.com/danielgruginski/Weapons
  (private, branch main): scripts and docs only; the blend file, exports, textures and renders are regenerated.

## Conventions that bite

- **Socket frame** (README): edges and bits on +X (Blender), two-handed grips below the origin, polearm heads high,
  bows and crossbows in the LEFT hand. In a Humans socket: right (0, 90, 0), left (0, -90, 0).
- **UVs are never automatic**: every part lays out its own (`grid_faces`, `cap_face`, `slab`, `box`); `wpn_bake.uv_report`
  lists faces left without UVs (none so far). bmesh names the first UV layer "Float2": `finish` renames it "UVMap".
- **One material on export** (`wpn_export`): the FBX must have one submesh, or Unity draws only the first (grips and
  heads vanished once).
- **Bake**: three passes over one packed layout; the source materials stay on the objects. Re-pack only with the
  colour pass (`pack_uvs=True`), never between passes.
- **Rune inlays** sit on the surface they decorate through `sheet_runes` (reads the sheet's rows: a fuller's floor, a
  midrib's top) or `shaft_runes` / `ribbon`; a fixed height leaves them floating or buried as blades taper.
- **Crossbow** points (`wpn_roster` crossbow rows) are mirrored in `Goblins/src/gob_crossbow.py` (`GRIP_R`, `NUT`,
  `STRING_FRONT`, `GROOVE`, `CHEEK`): change both together, then rebuild the clips.

## State (2026-10-04)

Done: 35 models, 20 enchanted copies, atlas + glow + metallic/smoothness, Unity setup and showcase, 54 items in the
game (stats, prices, shops, loot, enchant effects, armour piercing), crossbow clips, glow checked in play mode.

## Open / next

- Glow is subtle from the game camera in daylight (MedievalSetting `Assets/Game/POLISH.md`): a swing trail or bloom.
- No item icons (the game shows glyphs). The catalog renders could be cut into icons.
- The crossbow string is modelled spanned; no bolt in the groove; enchanted missiles fly plain.
- Goblins could carry the iron weapons (`GoblinAppearance` slots take any prop prefab: the kit is in their socket frame,
  but human-sized: scale ~0.6).
- The flamberge is heavy (2,640 triangles): fewer rows in its waves if budget matters.

## Checks

- Blender: `wpn_scene.render("name", wpn_scene.cat([...]))` renders catalog models side by side; look at the atlas and
  the glow mask PNGs themselves.
- Unity: the showcase renders in `Logs/WeaponsSetup`; in play mode ("Game > Play This Level" loads and writes no save),
  equip with `Equipment.Instance.Remove(slot)` then `Wear(item)`; the game pauses itself on a new character
  (`Time.timeScale` 0) -- set it to 1 for a test. Never add or change scripts while in play mode (the domain reload
  loses the game's statics).
