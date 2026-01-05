@echo off
cd /d "%~dp0"
echo TESTANDO O SISTEMA SEM INTERNET...
echo.

python -m streamlit run app.py

pause