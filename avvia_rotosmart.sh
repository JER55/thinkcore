#!/bin/bash
echo "📦 Installazione dipendenze..."
pip install streamlit plotly pandas openpyxl -q
echo "🚀 Avvio RotoSmart su http://localhost:8501"
streamlit run app_lidl.py --server.headless false --browser.gatherUsageStats false
