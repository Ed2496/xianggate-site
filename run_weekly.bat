@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
REM ============================================================
REM 相閘週報 · 每週五自動執行
REM 觸發：Windows Task Scheduler（OpenClaw 已廢，不假設常駐服務）
REM 動作：產報告(Cpk 寫檔) → git add/commit/push(Cpk 版本/上傳)
REM ============================================================

set "REPO=C:\Users\ed249\Downloads\xianggate-site"
set "LOG=%REPO%\run_log.txt"

cd /d "%REPO%" 2>nul
if errorlevel 1 (
  echo [%date% %time%] [ERROR] repo 不存在: %REPO%
  exit /b 1
)

echo ============================================== >> "%LOG%"
echo [%date% %time%] 開始執行相閘週報 >> "%LOG%"

REM 1) 產報告（掃描 → 環次命中 → HTML → history append）
REM    --mainfile weekly.html 避免覆蓋儀表板首頁 index.html
python "%REPO%\xianggate_weekly.py" --mainfile weekly.html >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [%date% %time%] [ERROR] 產報告失敗，中止（未 push） >> "%LOG%"
  exit /b 1
)

REM 1.5) 重建儀表板首頁（合併 weekly.html + concept_analysis.html → index.html）
python "%REPO%\xianggate_dashboard.py" --out "%REPO%" --outfile index.html >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [%date% %time%] [WARN] 儀表板合併失敗，weekly.html 已更新但 index.html 未刷新 >> "%LOG%"
)

REM 2) git 推送
git add -A >> "%LOG%" 2>&1
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "相閘週報 %date%" >> "%LOG%" 2>&1
  git push >> "%LOG%" 2>&1
  if errorlevel 1 (
    echo [%date% %time%] [ERROR] git push 失敗（檢查認證/網路） >> "%LOG%"
    exit /b 1
  )
  echo [%date% %time%] 已 push 到 GitHub Pages >> "%LOG%"
) else (
  echo [%date% %time%] 無變更，跳過 commit/push >> "%LOG%"
)

echo [%date% %time%] 完成 >> "%LOG%"
endlocal
