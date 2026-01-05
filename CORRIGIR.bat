@echo off
cd /d "%~dp0"
title CORRIGINDO INSTALACAO
color 0E

echo ==================================================
echo   CORRIGINDO BIBLIOTECAS (AGUARDE...)
echo ==================================================
echo.

:: 1. Tenta instalar/atualizar o pip
python -m pip install --upgrade pip

:: 2. Instala o Streamlit e as outras ferramentas
python -m pip install streamlit pandas python-docx

echo.
echo ==================================================
echo   CONCLUIDO!
echo ==================================================
echo   Agora feche esta janela e tente usar o 
echo   "INICIAR SISTEMA.bat" novamente.
pause