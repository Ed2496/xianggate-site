@echo off
chcp 65001 >nul
set SITE=C:\Users\ed249\Downloads\xianggate-site
cd /d "%SITE%"
echo === 乾跑預覽 ===
python xianggate_backfill.py --dry
echo.
echo 確認週數/筆數無誤後按任意鍵開始回填,或關視窗中止
pause >nul
python xianggate_backfill.py
echo === 重出報告 ===
python xianggate_weekly.py --mainfile weekly.html
python xianggate_dashboard.py --out "%SITE%" --outfile index.html
pause
