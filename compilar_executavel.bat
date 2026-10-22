@echo off
title Compilador do Executavel EPI Master Pro
cd /d "%~dp0"
echo ======================================================
echo    COMPILANDO APLICATIVO DESKTOP PARA EXECUTAVEL (.EXE)
echo ======================================================
echo.
echo Aguarde... O PyInstaller esta criando o executavel independente.
echo Isso pode levar de 1 a 2 minutos.
echo.

pyinstaller --noconfirm --onedir --windowed --name "EPI_Master_Pro" ^
    --add-data "data;data" ^
    --hidden-import "customtkinter" ^
    --hidden-import "reportlab" ^
    --hidden-import "openpyxl" ^
    --hidden-import "pandas" ^
    main.py

echo.
echo ======================================================
if exist "dist\EPI_Master_Pro\EPI_Master_Pro.exe" (
    echo COMPILACAO CONCLUIDA COM SUCESSO!
    echo O executavel foi criado em: dist\EPI_Master_Pro\EPI_Master_Pro.exe
) else (
    echo Houve uma falha na compilacao. Verifique as mensagens acima.
)
echo ======================================================
pause
