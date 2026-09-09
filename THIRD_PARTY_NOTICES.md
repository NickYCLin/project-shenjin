# Source and asset provenance

The repository's original code, documentation, Blender generation scripts,
original meshes, materials, and renders are provided under the root MIT license.
The project is developed with AI assistance. No game assets from Tantra,
commercial asset stores, or other games are included. Models are built locally
from original procedural geometry; there are no downloaded texture libraries.
Audio in the browser study is synthesized at runtime.

| Component | License / source | How used |
| --- | --- | --- |
| Three.js | MIT — https://github.com/mrdoob/three.js/blob/dev/LICENSE | Browser renderer and official example modules, installed through npm |
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
