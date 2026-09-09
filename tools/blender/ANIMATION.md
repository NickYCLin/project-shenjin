# 骨架動畫與角色細節來源

這一輪加入可實際播放的骨架動畫，以及曲面胸腿甲、三層肩甲、金屬浮雕、分節手指、腳型戰靴、封閉面甲與折褶布裙。Hero 採黑鐵與古金、灰米白破布、深色長髮；Sentinel 採暗石灰岩與古銅、酒紅布、深凹斜眼面甲。這些都是 `.blend` 內可編輯的 3D 幾何；仍屬開發中的角色美術，尚未達到 `art/reference/visual-target.png` 的最終寫實品質。

## 重新產生與驗證

在 repository 根目錄，以 Blender 4.0.2 或相容版本執行：

```bash
blender --background --python tools/blender/build_animation.py -- --render
blender --background --python tools/blender/verify_animation.py
```

若使用 CLI / CI，建議加上 `--python-exit-code 1`，讓 Python assertion 失敗明確回傳非零狀態。

- 讀取原始 `art/source/lost-temple.blend`，不覆寫原始雕塑和 static GLB / FBX。
- 輸出 `art/source/animated-characters.blend`、`art/exports/hero-rigged.{glb,fbx}`、`art/exports/sentinel-rigged.{glb,fbx}`。
- `art/exports/animation-manifest.json` 包含骨骼、動畫、三角面數、檔案大小與驗證結果；`art/renders/animation-preview.png` 為 Blender 實際渲染。
- 若 `art/textures/metal_plate` 的法線與粗糙度貼圖存在，會使用並嵌入 CC0 金屬微細表面；保留各角色的黑鐵、古金、古銅基底色。來源與授權見 `art/textures/sources.json`。原創程式與模型為 MIT；第三方 PBR 貼圖為 CC0。
- GLB 匯出前明確三角化並輸出 tangents，供法線貼圖使用；skinned mesh 放在 glTF scene root，避免重複套用 skeleton transform。FBX 保留一般 armature parent。
- `.blend` 使用 Blender 內建壓縮保存；可正常開啟與重新產生，貼圖也已 packed。

## 座標與骨骼

| 契約 | 值 |
| --- | --- |
| 單位 | 公尺；hero 靜態全高 1.8 m，sentinel 靜態全高 6 m |
| Blender | +Z 向上，角色面朝 -Y，足底與 Root 在 z = 0 |
| glTF | +Y 向上，角色面朝 +Z |
| FBX | `axis_forward=-Y`、`axis_up=Z`，公尺單位、骨架動畫 |
| Armature | `HeroRig` / `SentinelRig` |
| Skin | 每個角色 1 skin、1 mesh，依材質分 primitives |
| 骨骼數 | Hero 22；Sentinel 28，包含 Root / WeaponSocket / WeaponTip |
| 移動 | 所有 clips 原地播放；角色前進、閃避位移由遊戲邏輯控制 |

骨架有 Pelvis、Spine、Neck、Head、左右 UpperArm / Forearm / Hand、Thigh / Shin / Foot、Tabard，以及 Cloak。Sentinel 額外有第二對 UpperArm2 / Forearm2 / Hand2。

模型按解剖與盔甲部件使用剛性頂點權重，每個頂點總權重為 1。步行以雙腿的髖、膝、踝關節與交替抬腳形成；手臂、脊椎與布片跟隨各自骨骼。不是將整個角色上下平移來代替走路。分析式雙骨 IK 在 Blender 產製時烘焙成關節資料，遊戲執行時不需要 Blender constraint。

`WeaponSocket` 為 `Hand.R` 的 child bone，local +Y 指向槍尖。現有 `spear.glb` 長軸為 +Y，可掛到該骨骼後設定 `position.y = -0.65`，使手握在槍底往上 65 cm。`WeaponTip` 是其 child，兩骨位置差提供跨引擎的朝向向量。UE 可以將長槍自身的長軸對齊該向量，不需猜測 FBX 匯入後的 bone 本地軸。

## 剪輯契約

| 角色 | Clip | 長度（秒） | 播放 |
| --- | --- | ---: | --- |
| Hero | Idle | 2.00 | 循環 |
| Hero | Walk | 0.80 | 循環 |
| Hero | Thrust | 0.55 | 一次；命中姿勢在 0.20 s |
| Hero | Dodge | 0.32 | 一次 |
| Hero | Hit | 0.35 | 一次 |
| Hero | Death | 1.40 | 一次；結束維持倒下姿勢 |
| Sentinel | Idle | 2.40 | 循環 |
| Sentinel | Walk | 1.20 | 循環 |
| Sentinel | Windup | 1.10 | 一次；末端抬手最高 |
| Sentinel | Slam | 0.30 | 一次；0.30 s 末端命中 |
| Sentinel | Recover | 1.05 | 一次；由 Slam 末端回到待機 |
| Sentinel | Hit | 0.40 | 一次 |
| Sentinel | Death | 1.80 | 一次；結束維持倒下姿勢 |

動畫以 100 fps 烘焙，因此攻擊、閃避與頭目階段時間皆為精確幀數。GLB animations 使用上表的純名稱，直接以 `THREE.AnimationClip.findByName(gltf.animations, 'Walk')` 查找。`AnimationMixer` 將 Idle / Walk 設 `LoopRepeat`，其他設 `LoopOnce`；Death 需 `clampWhenFinished=true`。持續型步行可以依速度調整 timeScale，但攻擊應保留契約時間。

`.blend` 的 source Actions 使用 `Hero_Idle`、`Sentinel_Idle` 等名稱。NLA track / strip 使用 `Idle` 等純名稱；每個角色在獨立 scene 匯出，並開啟 `use_active_scene`，防止另一角色的 Actions 被誤帶入。

實際 Blender 4.0.2 回匯名稱：GLB 為 `Idle_HeroRig` / `Idle_SentinelRig`；FBX AnimStack 為 `HeroRig|Idle` / `SentinelRig|Idle`，其他 clips 類推。這是 Blender 匯入器的 action 名稱，GLB 檔本身仍為純名稱。

## 編輯與驗證範圍

`.blend` 包含原始雕塑 scene、Hero / Sentinel 各自可編輯場景，以及 `Animation showcase` 實際渲染場景。選取 armature 後在 Action Editor 選擇對應 action；NLA tracks 預設 mute，方便一次預覽一支 action。所有 render / packed texture 路徑使用相對路徑。

`verify_animation.py` 會：

1. 直接讀 GLB buffer，檢查 skins、JOINTS_0 / WEIGHTS_0、精確剪輯名稱、非空 animation channels、實際變動骨骼、時間與循環首尾一致性。
2. 確認 Walk 確實包含雙側大腿、小腿與上臂的變化，且 Root 沒有水平或垂直位移。
3. 對 hero / sentinel 的 GLB / FBX 共做 4 次真實 Blender 回匯，檢查 armature、bone 清單、modifier、權重與靜態全高。
4. 對每支回匯動畫每 50 ms 及末幀採樣整個變形 mesh，檢查不穿地、Root 不移動及武器軸向；產製時另每 10 ms 檢查腿部幾何。

這些驗證證明 Blender / glTF / FBX 資料可讀且契約一致。UE Editor 匯入、C++ 編譯與打包仍需有 Unreal Engine 的機器執行原生驗證，不能用 Blender 回匯結果宣稱完成 UE 驗證。
