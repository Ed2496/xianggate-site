@echo off
chcp 65001 >nul
REM 相閘 週報 v1.9 ｜ 四境→五境→報告→推 Pages ｜ Task Scheduler 週五觸發
REM 修正：git push 失敗時不再印 pushed（原 run_log 第12行 fatal 卻印 pushed）
set SITE=C:\Users\ed249\Downloads\xianggate-site
set PY=C:\Users\ed249\Downloads\xianggate
set LOG=%SITE%\run_log.txt

echo ============================================== >> "%LOG%"
echo [%date% %time%] START >> "%LOG%"

cd /d "%PY%"
python xianggate_weekly.py >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [%date% %time%] WEEKLY FAILED >> "%LOG%"
  goto :end
)
REM 第五境已由 weekly 內嵌呼叫；此行為保險：若需單獨重跑可取消註解
REM python xianggate_lambda.py >> "%LOG%" 2>&1

cd /d "%SITE%"
git add -A >> "%LOG%" 2>&1
git commit -m "xianggate weekly %date%" >> "%LOG%" 2>&1
git push >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [%date% %time%] PUSH FAILED ^(check: git remote -v^) >> "%LOG%"
) else (
  echo [%date% %time%] pushed >> "%LOG%"
)
:end
echo [%date% %time%] DONE >> "%LOG%"
