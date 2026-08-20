@echo off
chcp 65001 >nul
set "REPO=C:\Users\ed249\Downloads\xianggate-site"
set "LOG=%REPO%\run_log.txt"
cd /d "%REPO%"
echo ============================================== >> "%LOG%"
echo [%date% %time%] START >> "%LOG%"
python "%REPO%\xianggate_weekly.py" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [%date% %time%] ERROR report generation failed >> "%LOG%"
  exit /b 1
)
git add -A >> "%LOG%" 2>&1
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "xianggate weekly %date%" >> "%LOG%" 2>&1
  git push >> "%LOG%" 2>&1
  echo [%date% %time%] pushed >> "%LOG%"
) else (
  echo [%date% %time%] no change, skip >> "%LOG%"
)
echo [%date% %time%] DONE >> "%LOG%"
