@echo off
chcp 65001 >nul
set SITE=C:\Users\ed249\Downloads\xianggate-site
cd /d "%SITE%"
if not exist "csv_concept_engine.py" (echo [X] 找不到 csv_concept_engine.py 於 %SITE% & pause & exit /b 1)
python csv_concept_engine.py --dir "C:\Users\ed249\OneDrive\Documents" --out "%SITE%"
if errorlevel 1 (echo [X] 失敗；若中文亂碼被當命令,表py檔編碼被改壞,用VS Code存成UTF-8 with BOM & pause & exit /b 1)
if exist "%SITE%\concept_analysis.html" (start "" "%SITE%\concept_analysis.html") else (echo [X] 報告未產生 & pause)
