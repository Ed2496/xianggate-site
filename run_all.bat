@echo off
chcp 65001 >nul
REM 相閘 一鍵全流程(單一資料夾版：py與網站同在 xianggate-site)
REM   weekly    -> weekly.html          (週報分頁源)
REM   concept   -> concept_analysis.html (概念分頁源)
REM   dashboard -> index.html           (首頁=分頁儀表板)
REM   -> git push
set SITE=C:\Users\ed249\Downloads\xianggate-site
cd /d "%SITE%"

echo [1/4] 素材週報 -^> weekly.html ...
python xianggate_weekly.py --mainfile weekly.html
if errorlevel 1 (echo 週報失敗 & pause & exit /b 1)

echo [2/4] 概念/結論歸位分析 ...
python csv_concept_engine.py --dir "C:\Users\ed249\OneDrive\Documents" --out "%SITE%"
if errorlevel 1 (echo 概念分析失敗，略過此分頁 & echo.)

echo [3/4] 整合儀表板 -^> index.html(首頁) ...
python xianggate_dashboard.py --out "%SITE%" --outfile index.html
if errorlevel 1 (echo 儀表板失敗 & pause & exit /b 1)

echo [4/4] 推 GitHub ...
git add -A
git commit -m "xianggate dashboard %date%"
git push
if errorlevel 1 (echo 推送失敗，檢查 git remote -v & pause & exit /b 1)

echo.
echo 完成！首頁 index.html 現在是分頁儀表板(週報+概念)。
start "" "%SITE%\index.html"
