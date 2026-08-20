# 相閘週報 · 部署指南（Cpk 段 · Cowork/本機執行）

> Ca 段（此文件＋兩支程式）已由 Claude.ai web 產出。
> 以下**一次性設定**與**每週自動執行**屬 Cpk 段，在 Edward 本機／Cowork 執行。
> 坍縮權：關鍵詞、命名、要不要上線，全屬 Edward。

## 檔案清單（放同一個資料夾＝GitHub repo 根）

```
C:\Users\ed249\Downloads\xianggate-site\
├─ xianggate_weekly.py     主程式（掃描→環次命中→HTML→history）
├─ run_weekly.bat          排程觸發（產報告→git push）
├─ README_部署.md          本文件
├─ index.html              產出：最新一週首頁（自動生成，勿手改）
├─ history.json            產出：每週趨勢快照（append-only，勿手刪）
└─ reports\                產出：每週封存 YYYY-Www.html
```

## 掃描/輸出路徑（已內建，如需改在 xianggate_weekly.py 檔頭改）

- 掃描：`C:\Users\ed249\Downloads\TXT2026`、`C:\Users\ed249\Downloads\Transcripts-20260120`
- 輸出：`C:\Users\ed249\Downloads\xianggate-site`（＝repo 根）
- 副檔名：`.txt`、`.md`
- 編碼：utf-8 / cp950(Big5) / big5 / gb18030 自動嘗試（台灣 Windows 混編已處理）

---

## 一、先手測（不推 git，只驗產出）

```bat
cd /d C:\Users\ed249\Downloads\xianggate-site
python xianggate_weekly.py
```

看終端印出「素材總數／本週新增／字元總量」，開 `index.html` 確認畫面。
若某掃描目錄不存在，報告頂端會紅框標示「掃描目錄缺失」，不會中斷。

> 前置：確認已裝 Python 3（`python --version`）。本程式**零第三方套件**，純標準庫。

---

## 二、GitHub Pages 架站（一次性）

1. 在 GitHub 新建 repo，例如 `xianggate-site`（Public；Pages 需 Public 或付費方案）。
2. 本機 repo 初始化並綁遠端：
   ```bat
   cd /d C:\Users\ed249\Downloads\xianggate-site
   git init
   git branch -M main
   git add -A
   git commit -m "相閘週報 init"
   git remote add origin https://github.com/<你的帳號>/xianggate-site.git
   git push -u origin main
   ```
3. GitHub → repo → **Settings → Pages** → Source 選 **Deploy from a branch** → Branch `main` `/ (root)` → Save。
4. 幾分鐘後網址：`https://<你的帳號>.github.io/xianggate-site/`

> 認證：首次 push 若跳登入，用 GitHub **Personal Access Token**（Settings→Developer settings→Tokens）當密碼，
> 或裝 GitHub CLI `gh auth login` 一次綁好，之後 `run_weekly.bat` 才能無人值守 push。

---

## 三、每週五自動執行（Windows Task Scheduler · OpenClaw 已廢）

系統管理員 cmd 貼一行（每週五 09:00 觸發）：

```bat
schtasks /Create /TN "XiangGate_Weekly" /TR "\"C:\Users\ed249\Downloads\xianggate-site\run_weekly.bat\"" /SC WEEKLY /D FRI /ST 09:00 /F
```

- 改時間：`/ST 14:00`
- 立即測一次：`schtasks /Run /TN "XiangGate_Weekly"`
- 看排程：`schtasks /Query /TN "XiangGate_Weekly"`
- 刪除：`schtasks /Delete /TN "XiangGate_Weekly" /F`

執行紀錄寫在 `run_log.txt`（含每次 import_ts 稽核）。

---

## 四、Cowork 接手檢查清單（無根動作防呆）

- [ ] Python 3 在 PATH（`python --version` 有回應）
- [ ] git 在 PATH，且 `git push` 認證已綁（token 或 gh），否則排程 push 會卡
- [ ] 兩個掃描目錄路徑正確存在（不存在會被報告標示，但無資料）
- [ ] 先手測 `python xianggate_weekly.py`，開 index.html 確認畫面無誤
- [ ] git init + 首推成功、Pages 網址開得出來
- [ ] schtasks 建立，`schtasks /Run` 手動觸發一次，run_log.txt 有「已 push」
- [ ] 確認 history.json、reports\ 有進 git（趨勢圖靠歷史累積，勿被 .gitignore 擋掉）

---

## 五、待坍縮項（回 Ca 段給 Edward）

1. **環次命中關鍵詞**：現為示範層啟發式（規格 §9）。RING_KEYWORDS 在 py 檔頭可編。
   正式版應由對撞引擎逐命題判定 —— 這是 Fork B（接後端）的活，本週報是 Fork A（先讓它轉）。
2. **週窗定義**：現用 ISO 週（週一起算），「本週新增」＝檔案 mtime ≥ 本週一。
   若要改「上次跑到這次跑之間」的增量窗，回報改。
3. **報告只給方位**：不做結論、不替你坍縮（守規格 §10）。要不要把某環升格、駁回，走週閘。
