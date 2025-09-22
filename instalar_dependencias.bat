@echo off
title Instalar Dependencias - Transcritor Universal
color 0A

echo ================================================
echo   Instalador de Dependencias - Transcritor App
echo ================================================
echo.

:: Verifica se o Python esta no PATH
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    echo Baixe e instale em: https://www.python.org/downloads/
    pause
    exit /b
)

echo [OK] Python detectado.
echo.

:: Cria ambiente virtual (opcional)
if not exist venv (
    echo Criando ambiente virtual...
    python -m venv venv
)

echo Ativando ambiente virtual...
call venv\Scripts\activate

:: Atualiza pip
echo Atualizando pip...
python -m pip install --upgrade pip

:: Instala dependencias do requirements.txt
if exist requirements.txt (
    echo Instalando pacotes Python...
    pip install -r requirements.txt
) else (
    echo requirements.txt nao encontrado, instalando manualmente...
    pip install tkinterdnd2 customtkinter openai-whisper pdfplumber python-docx openpyxl pillow pytesseract
)

echo.
echo ================================================
echo   Dependencias Python instaladas!
echo ================================================

:: Instalar FFmpeg automaticamente
set FFMPEG_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
set FFMPEG_ZIP=ffmpeg-release-essentials.zip
set FFMPEG_DIR=C:\ffmpeg

echo.
echo Baixando FFmpeg...
bitsadmin /transfer ffmpegDownload /priority high %FFMPEG_URL% %FFMPEG_ZIP%

if exist %FFMPEG_ZIP% (
    echo Extraindo FFmpeg para %FFMPEG_DIR% ...
    powershell -Command "Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath '%FFMPEG_DIR%' -Force"
    del %FFMPEG_ZIP%
    
    :: Acha subpasta "ffmpeg-xxxx" e move o conteudo para C:\ffmpeg
    for /d %%i in ("%FFMPEG_DIR%\ffmpeg-*") do (
        xcopy "%%i\bin" "%FFMPEG_DIR%\bin" /E /I /Y
        rmdir /S /Q "%%i"
    )

    echo Adicionando %FFMPEG_DIR%\bin ao PATH...
    setx PATH "%PATH%;%FFMPEG_DIR%\bin"
    echo [OK] FFmpeg instalado em %FFMPEG_DIR%
) else (
    echo [ERRO] Nao foi possivel baixar FFmpeg automaticamente.
    echo Baixe manualmente em: https://www.gyan.dev/ffmpeg/builds/
)

:: Aviso sobre Tesseract
echo.
echo ================================================
echo   ATENCAO: Tesseract OCR precisa estar instalado
echo - Baixar: https://github.com/UB-Mannheim/tesseract/wiki
echo - Normalmente instala em: C:\Program Files\Tesseract-OCR\
echo - Adicione este caminho ao PATH
echo ================================================

echo.
echo ================================================
echo   Instalacao concluida!
echo   Agora rode: python app_transcricao.py
echo ================================================
pause
