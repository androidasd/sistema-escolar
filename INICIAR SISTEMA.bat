@echo off
cd /d "%~dp0"
title SISTEMA ESCOLAR - ONLINE (SINCRONIZADO)

:: Cor Azul Profissional
color 0B

echo ==================================================
echo   INICIANDO O SISTEMA...
echo ==================================================
echo.

:: 1. Liga o sistema forçando o endereço 'localhost' (para o túnel achar)
start /B python -m streamlit run app.py --server.port 8501 --server.address localhost

:: 2. Espera 10 segundos (Tempo extra para garantir que ligou)
echo   Aguardando o sistema carregar (10s)...
timeout /t 10 /nobreak >nul

:: 3. Liga o Túnel Cloudflare
echo.
echo   ------------------------------------------------
echo   GERANDO LINK ONLINE...
echo   ------------------------------------------------
echo.
cloudflared.exe tunnel --url http://localhost:8501