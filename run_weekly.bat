@echo off
chcp 65001 >nul
REM 相閘 週報更新(安全版)：週報→weekly.html，再合併→index.html（保留分頁框架）
REM 2026-08-28 修正：不再直接覆蓋 index.html，改走 run_all 同路徑
set SITE=C:\Users\ed249\Downloads\xianggate-site
cd /d "%SITE%"

echo [1/3] 素材週報 -^> weekly.html ...
python xianggate_weekly.py --mainfile weekly.html
if errorlevel 1 (echo 週報失敗 & pause & exit /b 1)

echo [2/3] 整合儀表板 -^> index.html（週報+概念分頁） ...
python xianggate_dashboard.py --out "%SITE%" --outfile index.html
if errorlevel 1 (echo 儀表板合併失敗 & pause & exit /b 1)

echo [3/3] 推 GitHub ...
git add -A
git commit -m "xianggate weekly %date%"
git push
if errorlevel 1 (echo [!] push失敗,檢查 git remote -v & pause)
echo 完成。週報已更新，index.html 分頁框架完整。
