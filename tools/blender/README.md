# 神燼 Blender 美術來源與重建

模型、骨架與生成程式是本專案製作的原創內容，採 MIT。v0.2 另外使用 Poly Haven 的 CC0 PBR 貼圖，來源、作者、下載 URL 與校驗值保留在 [sources.json](../../art/textures/sources.json)；不要把這些貼圖描述成自行拍攝的素材。

目前包含可編輯神殿、持槍主角、四臂守衛、長槍、13 支骨架動畫與材質。這些是持續打磨的遊戲美術；[目標概念圖](../../art/reference/visual-target.png) 仍是美術方向，不是實機品質承諾。

## 重建順序

已使用 Blender 4.0.2 產製；其他 Blender 版本需重新驗證匯出器差異。從 repository 根目錄執行：

```bash
# 恢復或校驗 12 份固定的 CC0 原始貼圖；缺檔時需要網路。
python3 tools/fetch-materials.py

# 原始模型來源與 static fallback；動畫生成器會讀取此 .blend。
blender --background --python-exit-code 1 --python tools/blender/build_assets.py -- --render
blender --background --python-exit-code 1 --python tools/blender/verify_assets.py

# 角色骨架、細節與金屬表面；保留原始 static 來源。
blender --background --python-exit-code 1 --python tools/blender/build_animation.py -- --render
blender --background --python-exit-code 1 --python tools/blender/verify_animation.py

# 新場景；保留 temple.glb/.fbx 與 lost-temple.blend。
blender --background --python-exit-code 1 --python tools/blender/build_temple_v2.py -- --materials art/textures/materials.json --render

# Khronos glTF 結構檢查與 browser 資產同步／建置。
npm run validate:assets
npm run build
```

`--render` 可省略，僅生成模型輸出；以 `--python-exit-code 1` 讓 assertion 明確回傳非零狀態。重建會更新對應生成檔案，先提交或備份手動美術修改。角色產製會在可用時讀取本機金屬法線與粗糙度，因此要重現 v0.2 材質，需先完成貼圖步驟。

- [角色細節、骨架、剪輯、回匯驗證](ANIMATION.md)
- [神殿 v2 結構、材質、鏡頭碰撞與驗證](TEMPLE_V2.md)
- [UE 編譯與 static / skeletal 匯入流程](../../unreal/README.md)
- [目前遊戲範圍與驗證邊界](../../docs/STATUS.md)

## 輸出檔案

| 檔案                                                    | 用途                                                           |
| ------------------------------------------------------- | -------------------------------------------------------------- |
| `art/source/lost-temple.blend`                          | 原始可編輯場景與角色雕塑；角色生成器的輸入                     |
| `art/source/animated-characters.blend`                  | 角色細節、骨架、Actions、材質與展示場景                        |
| `art/source/lost-temple-v2.blend`                       | 雕刻神殿 v2、PBR 材質、渲染攝影機與燈光                        |
| `art/exports/temple-v2.glb` / `.fbx`                    | 新神殿環境；Browser 使用 GLB                                   |
| `art/exports/temple-v2-colliders.json`                  | glTF 座標的簡化鏡頭碰撞盒；不包含角色碰撞或尋路                |
| `art/exports/hero-rigged.glb` / `.fbx`                  | 1.8 m 主角，skin、22 bones、6 clips                            |
| `art/exports/sentinel-rigged.glb` / `.fbx`              | 6.0 m 四臂守衛，skin、28 bones、7 clips                        |
| `art/exports/spear.glb` / `.fbx`                        | 2.4 m 長槍，槍底原點，另行掛到武器骨骼                         |
| `art/exports/{temple,hero,sentinel}.glb` / `.fbx`       | 原始 static 輸出；保留作來源與 fallback                        |
| `art/exports/animation-manifest.json`                   | 角色骨骼、clips、面數、大小及動畫回匯報告                      |
| `art/exports/manifest.json`、`verification.json`        | 原始 static 資產數據及 8 份 GLB / FBX 回匯報告；不代表 v2 場景 |
| `art/renders/{preview,animation-preview,temple-v2}.png` | 各 Blender 來源場景的實際渲染；不是遊戲畫面                    |
| `art/textures/sources.json`、`materials.json`           | CC0 來源校驗與神殿材質角色映射                                 |

執行 `npm run build` 或 `npm run dev` 時，`sync-preview-assets.mjs` 會把新神殿、兩個骨架角色、長槍及鏡頭碰撞 JSON 複製到 `preview/public/models/`。材質與貼圖檔案大小已超出第一版的 4 MB 模型目標；實際數據以生成報告及 `validate-assets.mjs` 的當前預算檢查為準，不把 static manifest 的舊面數當作 v2 數據。

## 座標與持握契約

- Blender 使用公尺、+Z 向上；角色面朝 −Y，足底及 Root 在 `(0,0,0)`。glTF 使用 +Y 向上、角色面朝 +Z；角色高度分別 1.8 m 與 6.0 m。
- 所有骨架 clips 原地播放，Root 不位移；前進及閃避位移由遊戲邏輯負責。`WeaponSocket` 跟隨右手，`WeaponTip` 與它的位置差提供槍尖方向。glTF 長槍沿 +Y，持握點距槍底 0.65 m，詳細設定見 [ANIMATION.md](ANIMATION.md)。
- 原始 static 與角色骨架 FBX 使用 `axis_forward=-Y`、`axis_up=Z`；神殿 v2 使用 `axis_forward=-Z`、`axis_up=Y`。不要把不同匯出設定混成一個假設；兩套都必須檢查實際匯入尺寸與朝向。
- 神殿的 Blender 背景位於 +Y；glTF 映射為 `(x,z,-y)`，背景位於 −Z，地面 glTF Y=0。Browser 的戰鬥半徑維持 16.5 m。
- Browser 初始主角在 `(0,0,8)`、Y 旋轉 π，守衛在 `(0,0,-5)`。模型自身沒有另外內嵌長槍；武器應由遊戲端掛載。

## 材質與驗證邊界

神殿使用石材、地板、岩壁、金屬等材質角色；角色以自訂基底色搭配金屬法線／粗糙度。Blender 來源保留打包貼圖，GLB 嵌入影像；Eevee 的燈光、AgX 與遊戲的即時渲染不同，仍須在瀏覽器或引擎實際調整曝光、法線強度與貼圖取樣。

`verify_assets.py` 驗證原始 static set；`verify_animation.py` 檢查 skins、權重、變動骨骼、clip 長度、循環、原地 Root、武器軸向及 4 次動畫 GLB / FBX 回匯。神殿 v2 生成腳本另會直接回匯兩個輸出，檢查 bounds、UV、mesh 數，以及匯出不包含 camera / light。完整範圍及本輪結果見各專用文件；只有指令存在不代表已執行成功。

目前沒有正式 LOD、production retopology、完整角色 IK、布料物理、臉部表情系統或動畫藍圖。簡化碰撞 JSON 僅供鏡頭使用。UE 仍須在真正安裝引擎的機器上確認匯入、骨架、材質、C++ 編譯、PIE 及封裝；Blender 回匯和 Browser 測試都不能替代這些步驟。
