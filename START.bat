@echo off
chcp 65001 >nul
title ThinkCore - Avvio in corso...
echo.
echo  ================================================
echo    ThinkCore - Plan Intelligence - Gestione Turni Retail
echo  ================================================
echo.
echo  Installazione dipendenze (prima volta)...
pip install streamlit plotly pandas openpyxl -q
echo.
echo  Avvio applicazione...
echo  Il browser si aprira' automaticamente su http://localhost:8501
echo.
streamlit run app_lidl.py --server.headless false --browser.gatherUsageStats false
pause
