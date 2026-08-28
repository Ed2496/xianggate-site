@echo off
chcp 65001 >nul
cd /d "C:\Users\ed249\Downloads\xianggate-site"
echo === xianggate-site git push ===
echo.

REM 清除殘留 lock
if exist ".git\index.lock" (
    del ".git\index.lock"
    echo [!] 已清除殘留 index.lock
)

echo --- git status ---
git status --short
echo.
echo --- Committing ---
git add -A
git commit -m "fix index tab framework + run_weekly safe mode 2026-08-28"
echo.
echo --- Pushing ---
git push
echo.
echo === Done ===
pause
