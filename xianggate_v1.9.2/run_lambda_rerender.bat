@echo off
chcp 65001 >nul
set SITE=C:\Users\ed249\Downloads\xianggate-site
cd /d "%SITE%"
python xianggate_lambda.py --rerender
if errorlevel 1 exit /b 1
python xianggate_dashboard.py --out "%SITE%" --outfile index.html
git add -A && git commit -m "xianggate lambda finalize %date%" && git push
