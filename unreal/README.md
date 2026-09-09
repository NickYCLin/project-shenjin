# Shenjin — Unreal 原生戰鬥原型

**目標版本：Unreal Engine 5.6。這個目錄仍未經 Unreal 編譯、Editor 匯入、PIE 或封裝驗證。** 開發環境沒有 UE；Python 語法檢查、設定檢查與 C++ 人工檢閱不能取代引擎實測。瀏覽器 companion 的執行結果也不能視為 UE 通過。

本次新增原生骨架動畫匯入與播放管線。原生 C++ 單人遭遇戰包含：第三人稱移動與攝影機、長槍攻擊、閃避無敵窗口、三種神誓、8 秒神相、兩階段神殿守衛、血條、勝敗與重開。場景在 GameMode `StartPlay` 建立，因此 Editor 的空白地圖要按 **Play** 才會看到場景。

Unreal 原型與 browser companion 是共用原創美術、各自實作戰鬥的獨立實驗。目前 native 有三誓、browser 有兩種配置，攻速、範圍、傷害等數值也還未統一；browser 試玩只能驗證 browser 的操作與邏輯。

## 安裝與啟動

需自行安裝 UE 5.6 與其平台 C++ toolchain。引擎程式碼、安裝包與引擎資產不在本 repository；本 repository 的開源授權不會重新授權 Unreal Engine。版本升級需重新編譯與驗證，請勿把 `EngineAssociation` 換掉就當作相容性已確認。

先依根目錄美術流程產生 `art/exports/{temple,hero,sentinel,spear}.fbx`；缺少 FBX 時仍可建立地圖並使用引擎內建幾何體。

Linux，從 repository 根目錄執行：

```bash
export SHENJIN_UE_ROOT=/absolute/path/to/UnrealEngine
bash unreal/Scripts/run_linux.sh build
bash unreal/Scripts/run_linux.sh prepare
bash unreal/Scripts/run_linux.sh prepare-animation
bash unreal/Scripts/run_linux.sh editor
```

Windows PowerShell，從 repository 根目錄執行：

```powershell
$env:SHENJIN_UE_ROOT = 'C:\Program Files\Epic Games\UE_5.6'
$project = (Resolve-Path 'unreal\Shenjin.uproject').Path
$prepare = (Resolve-Path 'unreal\Scripts\prepare_project.py').Path
$animations = (Resolve-Path 'unreal\Scripts\prepare_animation.py').Path
if (!(Test-Path "$env:SHENJIN_UE_ROOT\Engine\Binaries\Win64\UnrealEditor.exe")) { throw "UE 5.6 安裝路徑不存在" }
& "$env:SHENJIN_UE_ROOT\Engine\Build\BatchFiles\Build.bat" ShenjinEditor Win64 Development $project -WaitMutex -NoHotReloadFromIDE
& "$env:SHENJIN_UE_ROOT\Engine\Binaries\Win64\UnrealEditor.exe" $project "-ExecutePythonScript=$prepare" -unattended -nop4
& "$env:SHENJIN_UE_ROOT\Engine\Binaries\Win64\UnrealEditor.exe" $project "-ExecutePythonScript=$animations" -unattended -nop4
& "$env:SHENJIN_UE_ROOT\Engine\Binaries\Win64\UnrealEditor.exe" $project
```

Linux 腳本會先檢查引擎路徑及可執行檔，缺少時立即以 exit 3 停止，不會啟動假建置。每一步成功後再執行下一步。首次 C++ 編譯與 shader 編譯可能需要較長時間。`prepare` 成功時 Output Log 會出現 `SHENJIN_PREPARE_OK`，並產生 `unreal/Saved/prepare-report.json`；不要只用 Editor 程序退出碼判斷 Python 匯入成功。

也可在已編譯完成的 Editor 執行 `Tools → Execute Python Script`，選擇 `Scripts/prepare_project.py`。執行前先存檔；腳本發現未存的地圖會停止。腳本建立或載入 `/Game/Shenjin/Maps/LostTemple`，指定 `ShenjinGameMode`。開啟地圖，選擇 **Selected Viewport / Play**（不是 Simulate），點進視窗捕捉滑鼠；Shift+F1 釋放滑鼠，Esc 結束 PIE。

## 操作與戰鬥

| 按鍵 | 動作 |
| --- | --- |
| WASD / 滑鼠 | 相對攝影機方向移動 / 環繞視角 |
| 左鍵或 J | 長槍攻擊；前搖後以朝向及距離判定命中 |
| Space | 沿移動方向閃避；沒有方向輸入時向前；0.32 秒無敵，可取消攻擊 |
| Q | 神力滿 100 後啟動 8 秒神相，增加攻速、傷害與距離 |
| E | 循環切換 Ember / Aegis / Gale；1 秒切換冷卻 |
| R | 隨時重開這場遭遇戰 |

Ember 提高每擊傷害，Aegis 減少 40% 所受傷害，Gale 增加移速並縮短攻擊與閃避冷卻。成功命中補充神力，神相期間不再補充。守衛落下血量 50% 後開始更快、更大的砸擊；每次攻擊的範圍在預警開始時鎖定。離開地面預警圓或使用閃避窗口躲開，趁恢復期間攻擊可得到 35% 傷害加成。

## 美術匯入契約

`prepare_project.py` 使用 `FbxImportUI`，每個 FBX 以 `combine_meshes=True` 匯成一個 static mesh，保留材質槽。角色骨架由獨立的 `prepare_animation.py` 匯入；未完成骨架匯入時使用 static mesh，連 static mesh 也缺少時使用 `/Engine/BasicShapes`。這些引擎資產只由本機引擎引用，不複製進 repository。

| FBX / Unreal asset | 單位與原點 |
| --- | --- |
| `temple.fbx` → `/Game/Shenjin/Meshes/temple` | 中央地面 Z=0，戰鬥半徑 18m；背景朝 +Y |
| `hero.fbx` → `/Game/Shenjin/Meshes/hero` | 約 1.8m，腳底原點，正面 -Y |
| `sentinel.fbx` → `/Game/Shenjin/Meshes/sentinel` | 約 6m，腳底原點，正面 -Y |
| `spear.fbx` → `/Game/Shenjin/Meshes/spear` | 約 2.4m，槍底原點，長軸 Z |

FBX 帶公尺單位資訊，Editor 以 `convert_scene_unit=True` 自動轉為公分；`import_uniform_scale=1`，不再乘 100。`force_front_x_axis=False`，角色元件在 C++ 用 +90° yaw 把 -Y 轉到 +X。腳本檢查匯入尺寸並停止異常比例匯入，不會悄悄補比例。首次實機仍需檢查人物朝向、腳底、槍持握與材質。

腳本也建立可染色的原創 `M_Prototype` 材質，供預警範圍與神相幾何使用。未執行腳本時預警仍有可見形狀和 HUD 提示，但 engine fallback 材質可能只顯示白色。

現有 mesh/material 預設保留。如需依新 FBX 重匯，先確保可還原，再設定 `SHENJIN_REIMPORT=1` 執行 `prepare`。已有地圖會保留並更新 GameMode。環境模型目前只作視覺，角色實際踩在 runtime 圓形碰撞地板上；不要把整個神殿匯入為一顆阻擋內部移動的 convex collision。

## 骨架與動畫流程

先依根目錄 Blender 流程產生 `art/exports/hero-rigged.fbx` 及 `sentinel-rigged.fbx`。執行 `prepare-animation`，或在 Editor 的 `Tools → Execute Python Script` 選 `Scripts/prepare_animation.py`。匯入前先存所有 Content 資產；有未存的內容時腳本停止。

| 來源 | 固定 Unreal 路徑 |
| --- | --- |
| `hero-rigged.fbx` | `/Game/Shenjin/Characters/Hero/Hero_SK`、`Hero_Skeleton` |
| 主角 clips | 同目錄 `Hero_Idle`、`Hero_Walk`、`Hero_Thrust`、`Hero_Dodge`、`Hero_Hit`、`Hero_Death` |
| `sentinel-rigged.fbx` | `/Game/Shenjin/Characters/Sentinel/Sentinel_SK`、`Sentinel_Skeleton` |
| 守衛 clips | 同目錄 `Sentinel_Idle`、`Sentinel_Walk`、`Sentinel_Windup`、`Sentinel_Slam`、`Sentinel_Recover`、`Sentinel_Hit`、`Sentinel_Death` |

Importer 會在各角色 `_Import/<唯一識別碼>` 匯入，按明確的 clip token 與已知 FBX 前後綴辨認 take，再整理到固定路徑。不會任選第一個 animation；重複、未知或缺少 clip 都會停止。檢查 mesh 尺寸、Skeleton 相容性與全部 clip 長度後才完成。匯入來源材質留在 `_Import`，供 Editor 人工整理；不會自動刪除資產。

**骨架 importer 永遠保留現有固定路徑資產**；整套資產已存在時只檢查，部分存在時停止並要求在 Editor 檢查，不會重新匯入到既有 Skeleton 上；`SHENJIN_REIMPORT` 僅適用舊 static importer。既有資產型別錯誤或骨架不一致時停止，應先備份並在 Editor 檢查。成功須同時看到 `SHENJIN_ANIMATION_PREPARE_OK` 和 `unreal/Saved/prepare-animation-report.json` 的 `ok: true`；Editor 程序 exit 0 本身不足以證明 Python 匯入成功。

角色有完整且相容的骨架和全部動畫時才啟用 skeletal visual，否則保留 static fallback。主角使用 `ACharacter` 的 `GetMesh()`；守衛有獨立 `USkeletalMeshComponent`。目前用 Single Node 播放，不需要 AnimBP；同一狀態不會每幀重啟 `PlayAnimation`。走路播放速度隨實際移速改變，單次動作的進度對齊戰鬥計時：

- 主角普通突刺 0.55 秒，0.20 秒命中；Gale / 神相縮短整段動作，命中點按同樣比例縮短。閃避 0.32 秒，取消突刺後不保留待命中事件。
- 守衛 Windup 原始 1.10 秒，依本次預警 1.20 / 0.90 秒縮放；Slam 0.30 秒、末端命中；Recover 原始 1.05 秒，依破綻 1.55 / 1.00 秒縮放。預警、砸擊或恢復期間受擊只閃爍，不打斷招式動畫。
- 主角 Hit 0.35 秒、Death 1.40 秒；守衛 Hit 0.40 秒、Death 1.80 秒。死亡動畫停在最後一幀；不是 ragdoll。

`WeaponSocket` 與它的子骨 `WeaponTip` 定義持握點和槍軸向；C++ 用兩個骨骼位置的向量讓槍的 +Z 長軸對齊，避免猜測 FBX bone roll。槍底到持握點 65cm。缺少任一骨時回到原有程序化 WeaponPivot；實際持握、朝向與動畫銜接仍需 PIE 驗收。骨架不使用 root motion，位移由 C++ 控制。

動態載入的 mesh、Skeleton、AnimSequence 由 `UPROPERTY` 或 skeletal component 保持引用；封裝設定明確包含 `/Game/Shenjin` 及 `/Engine/BasicShapes`。這是來源設定，仍須實際 cook 驗證封裝內容。

## 不需引擎的來源檢查

```bash
python3 unreal/Scripts/validate_source.py
# 或 bash unreal/Scripts/run_linux.sh validate
```

標準庫腳本輸出機器可讀 JSON，檢查 Python 語法、generated header 次序、必要 clip 名稱、模糊名稱拒絕、FBX 檔案存在、資產路徑、計時常數與 cook 設定。`ok: true` 僅指這些來源契約通過；JSON 會始終將 `cpp_compile`、`uht`、`editor_import`、`pie`、`packaged_build` 標為 `not_run`。這不是 C++ 測試，不能證明 API 或引擎行為正確。

## 引擎端驗收清單（尚待執行）

- [ ] UE 5.6 編譯 `ShenjinEditor`，沒有 UHT/C++ 錯誤。
- [ ] Python 成功標記與 report；hero 高度約 180cm、守衛約 600cm，沒有 100 倍比例問題。
- [ ] 骨架 importer 成功標記、`ok: true` report、2 meshes / 2 skeletons / 13 clips；尺寸、骨名、腳底與材質正確。
- [ ] Idle/Walk 切換連續；突刺接觸與傷害同時、閃避不重啟、兩階段守衛動作縮放正確、死亡停在末幀。
- [ ] WeaponSocket/WeaponTip 持握正確；移除骨架資產時 static fallback 仍可玩。
- [ ] PIE 有地面、燈光、正確攝影機與 HUD；WASD 方向正確，角色不掉出邊界。
- [ ] 攻擊須在範圍內且出招後才命中，空揮不增加神力；閃避取消攻擊不額外命中。
- [ ] 砸擊預警、命中、無敵窗口與破綻提示一致；預警途中進第二階段不改變當次範圍。
- [ ] Q 滿條才可使用；三誓與切換冷卻可辨認；死亡後不能繼續傷害頭目。
- [ ] 勝利、死亡與 R 重開都恢復乾淨狀態；30/60/120 FPS 閃避距離一致。
- [ ] Development 封裝包含地圖、動態載入 mesh/material 與 engine fallback shapes；在非 Editor 執行。

目前沒有音效、AnimBP 混合與 IK、技能樹、持久存檔、物品掉落、多人複寫、伺服器、反作弊或上架建置。守衛是適合這座空曠圓場的簡單 kinematic AI，沒有尋路；神相是程序化靜態幾何。這是驗證戰鬥流程的原型程式，不代表 3A 成品質量或多人架構已就緒。

## 官方 API 參考

- [Character movement input](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/APawn/AddMovementInput)
- [HUD drawing](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/AHUD)
- [FBX import options / UE 5.6](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxStaticMeshImportData?application_version=5.6)
- [Editor level creation / UE 5.6](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/LevelEditorSubsystem?application_version=5.6)
- [Interchange FBX switch](https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-using-interchange-in-unreal-engine)

- [Single Node skeletal animation playback](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/USkeletalMeshComponent/PlayAnimation)
- [Skeletal / animation import options / UE 5.6](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxImportUI?application_version=5.6)
- [SkeletalMesh bounds / UE 5.6](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/SkeletalMesh?application_version=5.6)
