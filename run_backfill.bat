@echo off
chcp 65001 >nul
REM 相閘 全庫標記回填（一次性；補齊歷史週讓 σ 線/深度熱圖有多週資料）
REM 先 --dry 看會標幾筆幾週，確認無誤再拿掉 --dry 實跑
set PY=C:\Users\ed249\Downloads\xianggate
cd /d "%PY%"
echo === 乾跑預覽 ===
python xianggate_backfill.py --dry
echo.
echo 確認上面週數/筆數無誤後，按任意鍵開始實際回填，或關視窗中止
pause >nul
python xianggate_backfill.py
echo.
echo === 重出報告 ===
python xianggate_weekly.py
pause
