# spotify_to_youtube_gui.py
# Description: Downloads songs from a Spotify playlist using YouTube and yt-dlp, with a Tkinter GUI.
# Requirements:
#   - Python 3.x
#   - spotipy library (install using: pip install spotipy)
#   - python-dotenv library (install using: pip install python-dotenv)
#   - yt-dlp.exe (should be in the system PATH or the same directory as this script)
#   - ffmpeg (required by yt-dlp for audio conversion, should be in PATH or same directory)

import os
import subprocess
import time
import re
import threading
import queue
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font, Toplevel
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration ---
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
BASE_OUTPUT_DIR = "Spotify_Downloads"
ENV_FILE = ".env"
PLACEHOLDER_VALUES = {None, "", "YOUR_SPOTIFY_CLIENT_ID_HERE", "YOUR_SPOTIFY_CLIENT_SECRET_HERE", "your_key_here"}

# --- Global Spotify Client ---
sp = None

# --- Helper Functions ---
def extract_playlist_id(url):
    """Extracts the playlist ID from various Spotify URL formats."""
    match = re.search(r'playlist/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None

def sanitize_filename(name):
    """Removes characters that are invalid for Windows filenames."""
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized

def is_valid_credential(value):
    """Checks if a credential value is present and not a placeholder."""
    return value not in PLACEHOLDER_VALUES

def save_credentials_to_env(client_id, client_secret):
    """Saves the provided credentials to the .env file."""
    try:
        with open(ENV_FILE, "w") as f:
            f.write(f"CLIENT_ID={client_id}\n")
            f.write(f"CLIENT_SECRET={client_secret}\n")
        print(f"Credentials saved to {ENV_FILE}")
        return True
    except IOError as e:
        messagebox.showerror("File Error", f"Could not write to {ENV_FILE}: {e}")
        return False

def prompt_credentials_gui():
    """Creates a standalone Tkinter window to get Client ID and Secret from the user."""
    print("Entering prompt_credentials_gui...")
    try:
        # Create a new root window specifically for the prompt
        prompt_root = tk.Tk()
        print("Prompt root window created.")
        prompt_root.title("Enter Spotify Credentials")
        prompt_root.geometry("400x150")
        prompt_root.resizable(False, False)
        prompt_root.protocol("WM_DELETE_WINDOW", lambda: on_close(prompt_root, False))  # Handle window close

        id_var = tk.StringVar()
        secret_var = tk.StringVar()
        success = tk.BooleanVar(value=False)

        def submit_credentials():
            print("Submit button clicked.")
            client_id = id_var.get().strip()
            client_secret = secret_var.get().strip()

            if not is_valid_credential(client_id):
                messagebox.showwarning("Invalid Input", "Please enter a valid Client ID.", parent=prompt_root)
                return
            if not is_valid_credential(client_secret):
                messagebox.showwarning("Invalid Input", "Please enter a valid Client Secret.", parent=prompt_root)
                return

            if save_credentials_to_env(client_id, client_secret):
                success.set(True)
                prompt_root.quit()  # Exit the event loop cleanly
                print("Credentials submitted successfully.")

        def on_close(window, success_value):
            """Handle window close by setting success and quitting the event loop."""
            success.set(success_value)
            window.quit()
            print("Prompt window closed by user.")

        frame = ttk.Frame(prompt_root, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(frame, text="Spotify Client ID:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        id_entry = ttk.Entry(frame, textvariable=id_var, width=40)
        id_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Spotify Client Secret:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        secret_entry = ttk.Entry(frame, textvariable=secret_var, width=40, show="*")
        secret_entry.grid(row=1, column=1, padx=5, pady=5)

        submit_button = ttk.Button(frame, text="Submit", command=submit_credentials)
        submit_button.grid(row=2, column=0, columnspan=2, pady=10)

        id_entry.focus_set()
        print("GUI elements added to prompt window.")

        # Center the window
        prompt_root.update_idletasks()
        screen_width = prompt_root.winfo_screenwidth()
        screen_height = prompt_root.winfo_screenheight()
        size = tuple(int(_) for _ in prompt_root.geometry().split('+')[0].split('x'))
        x = screen_width / 2 - size[0] / 2
        y = screen_height / 2 - size[1] / 2
        prompt_root.geometry("+%d+%d" % (x, y))
        print("Prompt window centered.")

        print("Starting prompt event loop...")
        prompt_root.mainloop()  # Run the event loop for this window
        print("Prompt event loop ended.")
        
        result = success.get()
        prompt_root.destroy()  # Clean up the prompt window
        print(f"Prompt returning: {result}")
        return result

    except Exception as e:
        print(f"Error in prompt_credentials_gui: {e}")
        return False

# --- GUI Application Class ---
class SpotifyDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Spotify Playlist Downloader")
        self.root.minsize(600, 400)

        global CLIENT_ID, CLIENT_SECRET
        CLIENT_ID = os.getenv("CLIENT_ID")
        CLIENT_SECRET = os.getenv("CLIENT_SECRET")

        if not is_valid_credential(CLIENT_ID) or not is_valid_credential(CLIENT_SECRET):
            messagebox.showerror("Configuration Error",
                                 "Spotify Client ID or Secret is still invalid after check/prompt.\n"
                                 "Please check the .env file or restart the application.")
            self.root.quit()
            return

        self.sp = self.authenticate_spotify()
        if not self.sp:
            self.root.quit()
            return

        self.download_queue = queue.Queue()
        self.download_thread = None
        self.last_download_path = None

        self.playlist_url_var = tk.StringVar()
        self.search_suffix_var = tk.StringVar(value=" lyrics")
        self.status_var = tk.StringVar(value="Status: Idle")

        self.setup_gui()
        self.check_queue()

    def authenticate_spotify(self):
        global sp, CLIENT_ID, CLIENT_SECRET
        try:
            current_client_id = os.getenv("CLIENT_ID")
            current_client_secret = os.getenv("CLIENT_SECRET")
            if not is_valid_credential(current_client_id) or not is_valid_credential(current_client_secret):
                messagebox.showerror("Authentication Error", "Credentials became invalid before authentication.")
                return None

            client_credentials_manager = SpotifyClientCredentials(client_id=current_client_id, client_secret=current_client_secret)
            sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            sp.categories(limit=1)
            print("Successfully authenticated with Spotify API (using public endpoint check).")
            return sp
        except Exception as e:
            error_detail = str(e)
            if "invalid client" in error_detail.lower() or "client id" in error_detail.lower():
                error_message = f"Spotify Authentication Failed: Invalid Client ID or Secret.\nPlease verify the credentials in your .env file or re-enter them."
            elif "HTTP Error 401" in error_detail:
                error_message = f"Spotify Authentication Failed (401 Unauthorized): Invalid Client ID or Secret.\nPlease verify the credentials in your .env file or re-enter them."
            else:
                error_message = f"Error authenticating with Spotify: {e}\nCheck your CLIENT_ID, CLIENT_SECRET in .env, and network connection."
            messagebox.showerror("Spotify Authentication Failed", error_message)
            return None

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

        url_label = ttk.Label(main_frame, text="Spotify Playlist URL:")
        url_label.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        url_entry = ttk.Entry(main_frame, textvariable=self.playlist_url_var, width=60)
        url_entry.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="ew")

        radio_frame = ttk.Frame(main_frame)
        radio_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky="w")

        lyrics_radio = ttk.Radiobutton(radio_frame, text="Lyrics (Appends 'lyrics' to search)", variable=self.search_suffix_var, value=" lyrics")
        lyrics_radio.pack(side=tk.LEFT, padx=(0, 10))
        instrumental_radio = ttk.Radiobutton(radio_frame, text="Instrumental (Non lyrics search)", variable=self.search_suffix_var, value="")
        instrumental_radio.pack(side=tk.LEFT)

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)

        self.download_button = ttk.Button(buttons_frame, text="Start Download", command=self.start_download_thread)
        self.download_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.open_folder_button = ttk.Button(buttons_frame, text="Open Last Download Folder", command=self.open_last_download_folder, state=tk.DISABLED)
        self.open_folder_button.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        log_label = ttk.Label(main_frame, text="Log:")
        log_label.grid(row=3, column=0, sticky="nw", pady=(5, 0))

        self.log_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, width=80, state=tk.DISABLED)
        log_font = font.Font(family="Consolas", size=9)
        self.log_area.configure(font=log_font)
        self.log_area.grid(row=4, column=0, columnspan=2, padx=0, pady=(0, 5), sticky="nsew")

        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(5, 0))

    def log_message(self, message):
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.configure(state=tk.DISABLED)
        self.log_area.see(tk.END)

    def update_status(self, status_text):
        self.status_var.set(f"Status: {status_text}")

    def check_queue(self):
        try:
            while True:
                message_type, data = self.download_queue.get_nowait()
                if message_type == "log":
                    self.log_message(data)
                elif message_type == "status":
                    self.update_status(data)
                elif message_type == "finished":
                    self.download_button.config(state=tk.NORMAL)
                    if self.last_download_path and data:
                        self.open_folder_button.config(state=tk.NORMAL)
                    else:
                        self.open_folder_button.config(state=tk.DISABLED)
                    self.update_status("Finished" if data else "Finished with errors")
                    return
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

    def start_download_thread(self):
        playlist_url = self.playlist_url_var.get().strip()
        playlist_id = extract_playlist_id(playlist_url)

        if not playlist_id:
            messagebox.showerror("Invalid Input", "Please enter a valid Spotify playlist URL.")
            return

        if not self.sp:
            messagebox.showerror("Error", "Spotify client not initialized. Please restart the application.")
            return

        self.download_button.config(state=tk.DISABLED)
        self.open_folder_button.config(state=tk.DISABLED)
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete('1.0', tk.END)
        self.log_area.configure(state=tk.DISABLED)
        self.update_status("Starting...")
        self.log_message(f"Processing playlist URL: {playlist_url}")

        self.download_thread = threading.Thread(target=self.run_download_process, args=(playlist_id,), daemon=True)
        self.download_thread.start()
        self.root.after(100, self.check_queue)

    def run_download_process(self, playlist_id):
        try:
            self.download_queue.put(("status", "Fetching playlist name..."))
            playlist_name = self.fetch_playlist_name(playlist_id)
            sanitized_playlist_name = sanitize_filename(playlist_name)
            specific_output_dir = os.path.join(BASE_OUTPUT_DIR, sanitized_playlist_name)
            self.last_download_path = specific_output_dir

            self.create_output_directory(specific_output_dir)

            self.download_queue.put(("log", f"Fetching tracks for playlist ID: {playlist_id} ('{playlist_name}')"))
            self.download_queue.put(("status", f"Fetching tracks..."))
            tracks = self.get_playlist_tracks(playlist_id)

            if not tracks:
                self.download_queue.put(("log", "No tracks found or unable to fetch playlist details."))
                self.download_queue.put(("finished", False))
                return

            self.download_queue.put(("log", f"Found {len(tracks)} tracks. Starting download process into '{specific_output_dir}'..."))
            download_count = 0
            failed_count = 0
            search_suffix = self.search_suffix_var.get()

            for i, track in enumerate(tracks, 1):
                self.download_queue.put(("status", f"Downloading {i}/{len(tracks)}: {track['artist']} - {track['name']}"))
                self.download_queue.put(("log", f"\n--- Track {i}/{len(tracks)} ---"))
                success = self.download_track(track['artist'], track['name'], specific_output_dir, search_suffix, self.download_queue)
                if success:
                    download_count += 1
                else:
                    failed_count += 1
                self.download_queue.put(("log", "Waiting 1 second..."))
                time.sleep(1)

            self.download_queue.put(("log", "\n--- Download Summary ---"))
            self.download_queue.put(("log", f"Successfully downloaded/skipped: {download_count} tracks"))
            self.download_queue.put(("log", f"Failed: {failed_count} tracks"))
            self.download_queue.put(("log", "Download process finished."))
            self.download_queue.put(("finished", failed_count == 0))

        except Exception as e:
            self.download_queue.put(("log", f"An unexpected error occurred: {e}"))
            self.download_queue.put(("status", "Error occurred"))
            self.download_queue.put(("finished", False))
            if not os.path.exists(getattr(self, 'last_download_path', '')):
                self.last_download_path = None

    def fetch_playlist_name(self, playlist_id):
        try:
            playlist_info = self.sp.playlist(playlist_id, fields='name')
            playlist_name = playlist_info.get('name', playlist_id)
            self.download_queue.put(("log", f"Found playlist: '{playlist_name}'"))
            return playlist_name
        except Exception as e:
            self.download_queue.put(("log", f"Error fetching playlist name: {e}. Using Playlist ID instead."))
            return playlist_id

    def create_output_directory(self, directory_path):
        try:
            os.makedirs(directory_path, exist_ok=True)
            self.download_queue.put(("log", f"Downloads will be saved to: '{directory_path}'"))
        except OSError as e:
            self.download_queue.put(("log", f"Error creating directory '{directory_path}': {e}. Downloads might fail or save elsewhere."))

    def get_playlist_tracks(self, playlist_id):
        tracks = []
        try:
            results = self.sp.playlist_items(playlist_id, fields='items(track(name, artists(name))), next')
            items = results['items']
            while items:
                for item in items:
                    track = item.get('track')
                    if track and track.get('name') and track.get('artists'):
                        track_name = track['name']
                        artist_name = track['artists'][0]['name']
                        tracks.append({'artist': artist_name, 'name': track_name})
                if results['next']:
                    self.download_queue.put(("status", f"Fetching tracks... (Loaded {len(tracks)})"))
                    results = self.sp.next(results)
                    items = results['items']
                else:
                    items = None
        except Exception as e:
            self.download_queue.put(("log", f"Error fetching playlist tracks: {e}"))
        return tracks

    def download_track(self, artist, name, output_directory, search_suffix, msg_queue):
        search_query = f"{artist} - {name}{search_suffix}"
        output_filename_base = sanitize_filename(f"{artist} - {name}")
        output_filename = os.path.join(output_directory, f"{output_filename_base}.mp3")
        output_path_template = os.path.join(output_directory, f"{output_filename_base}.%(ext)s")

        if os.path.exists(output_filename):
            msg_queue.put(("log", f"Skipped: '{output_filename_base}.mp3' already exists."))
            return True

        msg_queue.put(("log", f"Searching and downloading: {artist} - {name}"))

        command = [
            "yt-dlp.exe",
            f"ytsearch1:{search_query}",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", output_path_template,
            "--no-playlist",
            "--encoding", "utf-8"
        ]

        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
            if "has already been downloaded" in result.stdout or "Destination:" in result.stdout or os.path.exists(output_filename):
                msg_queue.put(("log", f"Downloaded: '{output_filename_base}.mp3'"))
                return True
            else:
                msg_queue.put(("log", f"Warning: yt-dlp finished for '{artist} - {name}' but output file not confirmed."))
                if result.stdout: msg_queue.put(("log", f"yt-dlp stdout:\n{result.stdout}"))
                if result.stderr: msg_queue.put(("log", f"yt-dlp stderr:\n{result.stderr}"))
                return False

        except FileNotFoundError:
            msg_queue.put(("log", f"Error: 'yt-dlp.exe' not found. Make sure it's in your PATH or the script's directory."))
            raise RuntimeError("yt-dlp not found")
        except subprocess.CalledProcessError as e:
            msg_queue.put(("log", f"Error downloading '{artist} - {name}'. yt-dlp failed."))
            stderr_output = e.stderr if e.stderr else "No stderr output."
            msg_queue.put(("log", f"Error message (yt-dlp):\n{stderr_output[:500]}..."))
            return False
        except Exception as e:
            msg_queue.put(("log", f"An unexpected error occurred while downloading '{artist} - {name}': {e}"))
            return False

    def open_last_download_folder(self):
        if self.last_download_path and os.path.isdir(self.last_download_path):
            try:
                if os.name == 'nt':
                    os.startfile(self.last_download_path)
                    self.log_message(f"Opened folder: {self.last_download_path}")
                else:
                    messagebox.showinfo("Not Supported", "Opening folders is currently only supported on Windows.")
            except Exception as e:
                messagebox.showerror("Error Opening Folder", f"Could not open folder:\n{self.last_download_path}\nError: {e}")
                self.log_message(f"Error opening folder: {e}")
        elif self.last_download_path:
            messagebox.showwarning("Folder Not Found", f"The directory does not exist:\n{self.last_download_path}")
            self.log_message(f"Attempted to open non-existent folder: {self.last_download_path}")
        else:
            messagebox.showinfo("No Folder", "No download folder has been recorded yet. Please run a download first.")
            self.log_message("Attempted to open folder, but no path recorded yet.")

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting script...")

    # Load existing .env if present
    load_dotenv(dotenv_path=ENV_FILE)
    print("Environment variables loaded.")

    # Check credentials
    initial_client_id = os.getenv("CLIENT_ID")
    initial_client_secret = os.getenv("CLIENT_SECRET")
    credentials_valid = is_valid_credential(initial_client_id) and is_valid_credential(initial_client_secret)
    print(f"Credentials valid: {credentials_valid} (ID: {initial_client_id}, Secret: {initial_client_secret})")

    # Prompt if invalid or missing
    if not credentials_valid:
        print("Spotify credentials missing, invalid, or placeholders found. Prompting user.")
        if not prompt_credentials_gui():  # Run the standalone prompt
            print("User did not provide valid credentials or closed the prompt. Exiting.")
            exit(1)
        print("Credentials saved. Reloading environment variables.")
        load_dotenv(dotenv_path=ENV_FILE, override=True)
        final_client_id = os.getenv("CLIENT_ID")
        final_client_secret = os.getenv("CLIENT_SECRET")
        if not is_valid_credential(final_client_id) or not is_valid_credential(final_client_secret):
            print("Error: Credentials still invalid after saving.")
            messagebox.showerror("Credential Error", "Failed to verify credentials after saving. Please check the .env file.")
            exit(1)
    else:
        print("Existing credentials verified.")

    # Proceed to main application
    print("Starting main application...")
    root = tk.Tk()  # Create the main app root window only now
    app = SpotifyDownloaderGUI(root)
    if hasattr(app, 'sp') and app.sp:
        root.mainloop()
    else:
        print("Application initialization failed (likely Spotify auth). Exiting.")
        root.destroy()