# Carved temple environment V2

This is an editable, original procedural environment study for the Lost Temple arena. It replaces the first environment's plain shapes with carved architecture and physically modeled masonry. It is development art, not a claim of production AAA visual quality. The generated PNG is an actual Blender render of the exported environment geometry, with a render-only camera, lights and atmospheric volume; it does not use a concept painting as a background.

## Rebuild

Run from the repository root with Blender 4.0 or newer and the texture files present:

```bash
blender --background --python tools/blender/build_temple_v2.py -- --materials art/textures/materials.json --render
```

Omit `--render` to rebuild the models and perform the import checks without rendering. `--samples 128` increases the EEVEE render samples above the default 64. Without `--materials`, geometry builds with plain materials for inspection. The script uses the seeded random generator for reproducible detail placement and preserves every original `temple.*` and `lost-temple.blend` asset.

Outputs:

- `art/source/lost-temple-v2.blend`: compressed, editable Blender scene with packed source textures and a non-destructive triangulation modifier.
- `art/exports/temple-v2.glb`: game environment with embedded PBR textures and explicit tangent vectors.
- `art/exports/temple-v2.fbx`: environment with embedded textures for a native import workflow.
- `art/exports/temple-v2-colliders.json`: 37 simplified AABBs for the third-person camera.
- `art/renders/temple-v2.png`: 1920 × 1080 low courtyard camera render.

## Geometry and material contract

The scene contains a four-storey carved shrine on each side, fluted pillars, layered capitals and dentil cornices, arched galleries, small recessed deity niches, a processional stair, a sculpted god head on a carved reliquary, a broken segmented halo, rock cliffs, restrained vegetation and staggered paving. Facial depth includes recessed eye sockets, brows, eyelids, a nasal bridge and wings, lips, ears and a layered crown. The court uses individual approximately one-metre chamfered paving stones; neither the floor nor the background is an image plane.

The central playable radius remains 16.5 metres. Paving top heights range from -0.014 to +0.004 metres to avoid perfectly coplanar overlaps while remaining visually compatible with the existing flat gameplay surface. Small peripheral inlays are only 0.023 metres high and lie outside the playable radius. Debris, grass, columns and raised buildings also stay outside that radius. The generated camera colliders exclude the ground and preserve the open gallery bays by representing columns and solid lintels separately.

Authoring coordinates use metres, Blender +Z up, and +Y toward the far shrine. glTF maps `(x, y, z)` to `(x, z, -y)`, so the far shrine lies along negative Z in the game. Collider bounds already use those glTF coordinates. This V2 FBX export specifies `axis_forward='-Z', axis_up='Y'`; both formats reimport into Blender with the same +Z-up authoring bounds. These FBX export settings differ from the original static-character settings and should not be copied into the rig pipeline without checking its contract.

Meshes are combined by material role, so detailed repeated carving does not cause thousands of draw calls. All mesh faces receive UVs; projection scale follows world size and is finer on the statue and cliffs. The script accepts the roles `stone`, `lightstone`, `floor`, `gold`, `bronze` and `rock` from the material mapping. The idol uses a dedicated cool-tinted stone material with the rock maps and a lower normal strength, avoiding the masonry brick pattern on the face. Gold and bronze tint their metal maps instead of losing their material identity. Texture source and license metadata live in `art/textures/sources.json`.

For runtime size, the GLB re-encodes embedded images at JPEG quality 82 while retaining their 2K dimensions. The original texture files are unchanged. The editable `.blend` retains packed textures. Exported models contain no cameras, lights, atmosphere volumes, heroes or bosses.

## Verified result

The textured September 9, 2026 build contains **397,851 triangles**, **10 meshes**, **10 materials/primitives**, **12 embedded images** and **37 camera collision boxes**. The GLB is **39,229,396 bytes**; the FBX is **48,295,276 bytes**. These meet the 600,000-triangle, fewer-than-25-draw-call and 40 MB GLB targets. Rebuilding with different texture files can change file size.

Every build reimports both GLB and FBX and checks that mesh bounds match the generated source within 0.005 metres, all imported meshes retain UVs, and neither format contains cameras or lights. The current Blender-space bounds are `[-76, -32, -2.2]` to `[76, 112, 49.50612]` metres, including the distant ground and cliffs. Khronos glTF Validator also reported **0 errors and 0 warnings**. Its six informational notices concern preserved UV/tangent attributes on the three plain-color materials; those attributes are intentional for later texture work.

The source render uses EEVEE because this Blender installation lacks OpenImageDenoiser. It has a warm side sun, broad cool sky fill, a subtle real volume over the distant cliffs, and a low camera at `(0, -20, 3.6)` looking toward `(0, 18, 8.5)`. Runtime lighting and atmospheric settings belong to the game renderer; the Blender preview is a geometry/material review, not a substitute for browser playtesting.
