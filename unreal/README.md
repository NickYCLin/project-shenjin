# Shenjin — Unreal 原生戰鬥原型

**目標版本：Unreal Engine 5.6。這個目錄的初版尚未經 Unreal 編譯、Editor 匯入、PIE 或封裝驗證。** 開發環境沒有 UE；Python 語法檢查、設定檢查與 C++ 人工檢閱不能取代引擎實測。瀏覽器 companion 的執行結果也不能視為 UE 通過。

本次實作一個原生 C++ 單人遭遇戰：第三人稱移動與攝影機、長槍攻擊、閃避無敵窗口、三種神誓、8 秒神相、兩階段神殿守衛、血條、勝敗與重開。場景在 GameMode `StartPlay` 建立，因此 Editor 的空白地圖要按 **Play** 才會看到場景。

Unreal 原型與 browser companion 是共用原創美術、各自實作戰鬥的獨立實驗。目前 native 有三誓、browser 有兩種配置，攻速、範圍、傷害等數值也還未統一；browser 試玩只能驗證 browser 的操作與邏輯。

## 安裝與啟動

需自行安裝 UE 5.6 與其平台 C++ toolchain。引擎程式碼、安裝包與引擎資產不在本 repository；本 repository 的開源授權不會重新授權 Unreal Engine。版本升級需重新編譯與驗證，請勿把 `EngineAssociation` 換掉就當作相容性已確認。

先依根目錄美術流程產生 `art/exports/{temple,hero,sentinel,spear}.fbx`；缺少 FBX 時仍可建立地圖並使用引擎內建幾何體。

Linux，從 repository 根目錄執行：

```bash
export SHENJIN_UE_ROOT=/absolute/path/to/UnrealEngine
bash unreal/Scripts/run_linux.sh build
bash unreal/Scripts/run_linux.sh prepare
bash unreal/Scripts/run_linux.sh editor
```

Windows PowerShell，從 repository 根目錄執行：

```powershell
$env:SHENJIN_UE_ROOT = 'C:\Program Files\Epic Games\UE_5.6'
$project = (Resolve-Path 'unreal\Shenjin.uproject').Path
$prepare = (Resolve-Path 'unreal\Scripts\prepare_project.py').Path
& "$env:SHENJIN_UE_ROOT\Engine\Build\BatchFiles\Build.bat" ShenjinEditor Win64 Development $project -WaitMutex -NoHotReloadFromIDE
& "$env:SHENJIN_UE_ROOT\Engine\Binaries\Win64\UnrealEditor.exe" $project "-ExecutePythonScript=$prepare" -unattended -nop4
& "$env:SHENJIN_UE_ROOT\Engine\Binaries\Win64\UnrealEditor.exe" $project
```

每一步成功後再執行下一步。首次 C++ 編譯與 shader 編譯可能需要較長時間。`prepare` 成功時 Output Log 會出現 `SHENJIN_PREPARE_OK`，並產生 `unreal/Saved/prepare-report.json`；不要只用 Editor 程序退出碼判斷 Python 匯入成功。

也可在已編譯完成的 Editor 執行 `Tools → Execute Python Script`，選擇 `Scripts/prepare_project.py`。執行前先存檔；腳本發現未存的地圖會停止。腳本建立或載入 `/Game/Shenjin/Maps/LostTemple`，指定 `ShenjinGameMode`。開啟地圖，選擇 **Selected Viewport / Play**（不是 Simulate），點進視窗捕捉滑鼠；Shift+F1 釋放滑鼠，Esc 結束 PIE。

## 操作與戰鬥

| 按鍵 | 動作 |
| --- | --- |
| WASD / 滑鼠 | 相對攝影機方向移動 / 環繞視角 |
| 左鍵或 J | 長槍攻擊；前搖後以朝向及距離判定命中 |
| Space | 沿移動方向閃避；沒有方向輸入時向前；0.25 秒無敵，可取消攻擊 |
| Q | 神力滿 100 後啟動 8 秒神相，增加攻速、傷害與距離 |
| E | 循環切換 Ember / Aegis / Gale；1 秒切換冷卻 |
| R | 隨時重開這場遭遇戰 |

Ember 提高每擊傷害，Aegis 減少 40% 所受傷害，Gale 增加移速並縮短攻擊與閃避冷卻。成功命中補充神力，神相期間不再補充。守衛落下血量 50% 後開始更快、更大的砸擊；每次攻擊的範圍在預警開始時鎖定。離開地面預警圓或使用閃避窗口躲開，趁恢復期間攻擊可得到 35% 傷害加成。

## 美術匯入契約

腳本使用 `FbxImportUI`，每個 FBX 以 `combine_meshes=True` 匯成一個 static mesh，保留材質槽；不使用 skeletal mesh 或骨架動畫。缺少或尚未匯入模型時，C++ 使用 `/Engine/BasicShapes`。這些引擎資產只由本機引擎引用，不複製進 repository。

| FBX / Unreal asset | 單位與原點 |
| --- | --- |
| `temple.fbx` → `/Game/Shenjin/Meshes/temple` | 中央地面 Z=0，戰鬥半徑 18m；背景朝 +Y |
| `hero.fbx` → `/Game/Shenjin/Meshes/hero` | 約 1.8m，腳底原點，正面 -Y |
| `sentinel.fbx` → `/Game/Shenjin/Meshes/sentinel` | 約 6m，腳底原點，正面 -Y |
| `spear.fbx` → `/Game/Shenjin/Meshes/spear` | 約 2.4m，槍底原點，長軸 Z |

FBX 帶公尺單位資訊，Editor 以 `convert_scene_unit=True` 自動轉為公分；`import_uniform_scale=1`，不再乘 100。`force_front_x_axis=False`，角色元件在 C++ 用 +90° yaw 把 -Y 轉到 +X。腳本檢查匯入尺寸並停止異常比例匯入，不會悄悄補比例。首次實機仍需檢查人物朝向、腳底、槍持握與材質。

腳本也建立可染色的原創 `M_Prototype` 材質，供預警範圍與神相幾何使用。未執行腳本時預警仍有可見形狀和 HUD 提示，但 engine fallback 材質可能只顯示白色。

現有 mesh/material 預設保留。如需依新 FBX 重匯，先確保可還原，再設定 `SHENJIN_REIMPORT=1` 執行 `prepare`。已有地圖會保留並更新 GameMode。環境模型目前只作視覺，角色實際踩在 runtime 圓形碰撞地板上；不要把整個神殿匯入為一顆阻擋內部移動的 convex collision。

## 引擎端驗收清單（尚待執行）

- [ ] UE 5.6 編譯 `ShenjinEditor`，沒有 UHT/C++ 錯誤。
- [ ] Python 成功標記與 report；hero 高度約 180cm、守衛約 600cm，沒有 100 倍比例問題。
- [ ] PIE 有地面、燈光、正確攝影機與 HUD；WASD 方向正確，角色不掉出邊界。
- [ ] 攻擊須在範圍內且出招後才命中，空揮不增加神力；閃避取消攻擊不額外命中。
- [ ] 砸擊預警、命中、無敵窗口與破綻提示一致；預警途中進第二階段不改變當次範圍。
- [ ] Q 滿條才可使用；三誓與切換冷卻可辨認；死亡後不能繼續傷害頭目。
- [ ] 勝利、死亡與 R 重開都恢復乾淨狀態；30/60/120 FPS 閃避距離一致。
- [ ] Development 封裝包含地圖、動態載入 mesh/material 與 engine fallback shapes；在非 Editor 執行。

目前沒有音效、骨架動畫、技能樹、持久存檔、物品掉落、多人複寫、伺服器、反作弊或上架建置。守衛是適合這座空曠圓場的簡單 kinematic AI，沒有尋路；神相是程序化靜態幾何。這是驗證戰鬥流程的原型程式，不代表 3A 成品質量或多人架構已就緒。

## 官方 API 參考

- [Character movement input](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/APawn/AddMovementInput)
- [HUD drawing](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/AHUD)
- [FBX import options / UE 5.6](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxStaticMeshImportData?application_version=5.6)
- [Editor level creation / UE 5.6](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/LevelEditorSubsystem?application_version=5.6)
- [Interchange FBX switch](https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-using-interchange-in-unreal-engine)
