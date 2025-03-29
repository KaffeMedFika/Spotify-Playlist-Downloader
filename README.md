Spotify Playlist Downloader
==========================

What It Does
------------
This program lets you download songs from a Spotify playlist as MP3 files using YouTube. Just paste a Spotify playlist URL, and it will fetch the songs and save them to your computer in a folder called "Spotify_Downloads". It has a simple graphical interface (GUI) to make it easy to use.

Requirements
------------
To run this program, you need:
1. Python 3.x (download from https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH".
2. Two tools: yt-dlp.exe and ffmpeg.exe (included in setup instructions below).
3. A Spotify Developer account to get your Client ID and Secret (free at https://developer.spotify.com/dashboard/).

Setup Instructions
------------------
1. Download and unzip this folder to your computer.
2. Double-click "setup.bat" to automatically install the required Python libraries and download yt-dlp.exe and ffmpeg.exe.
   - If it asks for permission, allow it to run.
   - This may take a minute depending on your internet speed.
3. Open a command prompt in this folder:
   - Right-click inside the folder, hold Shift, and select "Open command window here" (or "PowerShell" on newer Windows).
4. Run the program by typing:
   python spotify_to_youtube_gui.py
   and press Enter.

Using the Program
-----------------
1. The first time you run it, a window will ask for your Spotify Client ID and Secret.
   - Go to https://developer.spotify.com/dashboard/, log in, create an app, and copy these keys.
   - Paste them into the fields and click "Submit".
   - They’ll be saved to a file called ".env" so you won’t need to enter them again.
2. In the main window, paste your Spotify playlist URL (e.g., https://open.spotify.com/playlist/xyz).
3. Choose "Lyrics" or "Instrumental" for the download type.
4. Click "Start Download" to begin. Songs will save to "Spotify_Downloads/[Playlist Name]".
5. Use "Open Last Download Folder" to see your downloaded files.

Notes
-----
- Keep yt-dlp.exe and ffmpeg.exe in this folder for the program to work.
- If you get errors, check the command prompt for messages and ensure all steps were followed.
- This program is for personal use only, respecting Spotify and YouTube’s terms of service.

License
-------
This program is licensed under the MIT License - see the LICENSE file for details.

Support
-------
If you have issues, feel free to open an issue on GitHub at https://github.com/KaffeMedFika/Spotify-Playlist-Downloader.
