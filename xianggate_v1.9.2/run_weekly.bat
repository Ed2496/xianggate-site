@echo off
chcp 65001 >nul
REM 相閘 週報單跑(單一資料夾版)。注意:此檔產出純週報index.html,不含分頁。
REM 若要分頁儀表板首頁,請改跑 run_all.bat。
set SITE=C:\Users\ed249\Downloads\xianggate-site
cd /d "%SITE%"
python xianggate_weekly.py
if errorlevel 1 (echo 週報失敗 & pause & exit /b 1)
git add -A
git commit -m "xianggate weekly %date%"
git push
if errorlevel 1 (echo [!] push失敗,檢查 git remote -v & pause)
echo 完成。
