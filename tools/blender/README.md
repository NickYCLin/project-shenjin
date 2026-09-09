# Shenjin original Blender art

These assets were authored specifically for this project with procedural Blender
geometry. No downloaded models, textures, characters, or engine content are used.
This first art study deliberately uses a stylized polygonal treatment; it is not a
finished AAA character set. Characters are static sculptural meshes without
skeletal rigs or animation clips yet.

## Rebuild and verify

Tested with **Blender 4.0.2** on Linux. From the repository root:

```sh
blender --background --python tools/blender/build_assets.py -- --render
blender --background --python tools/blender/verify_assets.py
```

Omit `-- --render` for geometry exports only. Rendering uses Eevee, 128 samples,
1600 × 900 pixels, with an AgX color transform. The `.blend` contains the complete
editable model objects, original materials, camera, and lighting. The exported
GLB/FBX files contain meshes, materials, root empties, and a facing marker only.
Meshes are merged by material on temporary export copies to reduce draw calls;
the source collection objects remain separately editable.

## Files

| File | Contents |
| --- | --- |
| `art/source/lost-temple.blend` | Complete editable presentation scene |
| `art/renders/preview.png` | Actual Blender render of the source scene |
| `art/exports/temple.glb` / `.fbx` | Battle arena, temple, stairs, columns, original giant god head, distant rocks |
| `art/exports/hero.glb` / `.fbx` | 1.8 m armored oath bearer |
| `art/exports/sentinel.glb` / `.fbx` | 6.0 m four-armed guardian including the raised flame tips |
| `art/exports/spear.glb` / `.fbx` | 2.4 m spear, root at shaft bottom |
| `art/exports/manifest.json` | Actual mesh counts, byte sizes, bounds, and glTF facing probe |
| `art/exports/verification.json` | Results of eight actual GLB/FBX round-trip imports |

## Coordinate and placement contract

- **Units:** meters in Blender and glTF. FBX includes Blender's metric unit metadata.
- **Blender source:** +Z up; both characters look toward **−Y**. Feet/root at `(0,0,0)`.
- **glTF:** +Y up; both characters look toward **+Z**. Feet/root at `(0,0,0)`.
- The export marker `Facing_reference__source_minusY__gltf_plusZ` is an empty at
  Blender `(0,−1,0)`. The generator inspects the actual GLB JSON and verifies its
  translated location is glTF `(0,0,+1)`; the round-trip verifier checks the
  imported location is again Blender `(0,−1,0)`.
- The temple's unobstructed battle disk is centered at the origin with an 18 m
  playable radius. Its top is exactly Blender Z = 0 / glTF Y = 0. The dark lower
  foundation ends at Z = −0.25 m, avoiding coplanar surface artifacts.
- Suggested Blender placements: hero `(0,−8,0)` with Z rotation π, sentinel
  `(0,5,0)` with rotation 0. The source `.blend` uses these placements.
- Equivalent glTF placements: hero `(0,0,+8)` facing −Z (Y rotation π), sentinel
  `(0,0,−5)` facing +Z. Temple structures extend into negative glTF Z.
- Exported hero and sentinel do **not** include a separate weapon. The spear root
  is at its bottom, so a hand socket must account for the grip's height on the shaft.
- Blender scene camera: `(25,−33,23)`, looking toward `(0,15,8)` with a 27 mm lens.

## Mesh budgets and current limitations

| Asset | Triangles | Material batches |
| --- | ---: | ---: |
| Temple | 54,532 | 11 |
| Hero | 10,191 | 7 |
| Sentinel | 20,095 | 7 |
| Spear | 2,516 | 3 |

Every exported binary is below 4 MB and the complete source `.blend` is below
20 MB. Counts are rechecked by the generator; the machine-readable manifest is
the source of truth after regeneration. There are no image textures or external
file dependencies. Cloth uses an original static wind silhouette and emissive
surfaces use material emission, so a realtime engine must supply its own bloom
and scene lighting. Imported meshes do not include collision meshes, LODs,
navigation, sockets, skeletal animation, or production retopology.

FBX uses `axis_forward='-Y'`, `axis_up='Z'`, and `FBX_SCALE_UNITS`. Blender round-trip
imports confirm scale and forward direction. Actual Unreal import still needs to
be checked in Unreal: use its automatic FBX unit conversion (1 m should become
100 Unreal units) and confirm the character's forward axis before adding a
Character Blueprint. No Unreal installation or Unreal import success is claimed.
