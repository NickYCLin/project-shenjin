# Source and asset provenance

The repository's original code, documentation, Blender generation scripts,
original meshes, material graphs, and renders are provided under the root MIT license.
The project is developed with AI assistance. No game assets from Tantra,
commercial asset stores, or other games are included. Models are built locally
from original procedural geometry. The v0.2 PBR surfaces incorporate the CC0
texture assets listed below, embedded in the exported models and Blender scenes.
Audio in the browser study is synthesized at runtime.

| Component | License / source | How used |
| --- | --- | --- |
| Three.js | MIT — https://github.com/mrdoob/three.js/blob/dev/LICENSE | Browser renderer and official example modules, installed through npm |
| ws | MIT — https://github.com/websockets/ws | Multiplayer WebSocket transport |
| sirv | MIT — https://github.com/lukeed/sirv | Serving the built game from the multiplayer host |
| Vite | MIT — https://github.com/vitejs/vite/blob/main/LICENSE | Development/build tooling, installed through npm |
| Prettier | MIT — https://github.com/prettier/prettier/blob/main/LICENSE | Development-time source formatting, installed through npm |
| Khronos glTF Validator | Apache-2.0 — https://github.com/KhronosGroup/glTF-Validator | Development-time asset validation, installed through npm |
| Blender | GPL — https://www.blender.org/about/license/ | External creation tool; not redistributed in this repository |
| Unreal Engine | Epic's own license — https://www.unrealengine.com/license | External engine; no Engine source or binary assets are redistributed |

Dependencies retain their own licenses. The repository's MIT license does not
relicense Unreal Engine or imply any rights to third-party names or assets.
Future asset contributions must include source, authorship and redistribution
permission. Do not commit marketplace assets, engine binaries, secrets or
machine-specific credentials.

## CC0 texture sources

Poly Haven releases its asset files under [CC0](https://polyhaven.com/license).
The asset pages are linked for attribution; no website preview images or logos
are redistributed. Source 2K JPEGs are in `art/textures/`, and the exact download
URLs, upstream MD5 values, byte counts and SHA-256 checksums are recorded in
[`art/textures/sources.json`](art/textures/sources.json). Restore them with
`python3 tools/fetch-materials.py`. Runtime uses local, embedded texture data.

| Asset | Author | Usage |
| --- | --- | --- |
| [Old Sandstone 02](https://polyhaven.com/a/old_sandstone_02) | Dimitrios Savva | Weathered temple masonry |
| [Monastery Stone Floor](https://polyhaven.com/a/monastery_stone_floor) | Amal Kumar | Courtyard paving |
| [Metal Plate](https://polyhaven.com/a/metal_plate) | Rob Tuytel | Metal surface detail |
| [Rock Face 03](https://polyhaven.com/a/rock_face_03) | Dario Barresi (photography), Rico Cilliers (processing) | Cliffs and stone sculpture |

Blender material graphs tint and combine these maps; GLB export may recompress
them at the same resolution to keep downloads practical. CC0 source textures
retain their CC0 dedication independently of the original MIT code and meshes.
