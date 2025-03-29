@echo off
title Spotify Downloader Setup
echo Setting up Spotify Playlist Downloader...

echo Checking for Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH.
    echo Please download and install Python 3.x from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found. Installing required libraries...
python -m pip install spotipy python-dotenv
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to install libraries. Ensure you have internet and pip is working.
    pause
    exit /b 1
)
echo Libraries installed successfully.

echo Checking for yt-dlp.exe...
if not exist "yt-dlp.exe" (
    echo Downloading yt-dlp.exe...
    curl -L "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -o "yt-dlp.exe"
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to download yt-dlp.exe. Please download it manually from:
        echo https://github.com/yt-dlp/yt-dlp/releases/latest
        pause
        exit /b 1
    )
    echo yt-dlp.exe downloaded.
) else (
    echo yt-dlp.exe already exists.
)

echo Checking for ffmpeg.exe...
if not exist "ffmpeg.exe" (
    echo Downloading ffmpeg.exe...
    curl -L "https://github.com/GyanD/codexffmpeg/releases/latest/download/ffmpeg-release-essentials.zip" -o "ffmpeg.zip"
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to download ffmpeg. Please download it manually from:
        echo https://ffmpeg.org/download.html (Windows builds)
        pause
        exit /b 1
    )
    echo Extracting ffmpeg.exe...
    powershell -command "Expand-Archive -Path ffmpeg.zip -DestinationPath .; Move-Item -Path .\ffmpeg-*-essentials_build\bin\ffmpeg.exe -Destination .; Remove-Item -Path ffmpeg.zip; Remove-Item -Recurse -Path ffmpeg-*-essentials_build"
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to extract ffmpeg.exe. Please extract it manually from ffmpeg.zip.
        pause
        exit /b 1
    )
    echo ffmpeg.exe downloaded and extracted.
) else (
    echo ffmpeg.exe already exists.
)

echo Setup complete! You can now run the program with:
echo python spotify_to_youtube_gui.py
echo (Open a command prompt here and type the above command.)
pause