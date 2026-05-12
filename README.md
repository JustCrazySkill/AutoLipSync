# AutoLipSync

Automated lip sync pipeline for Roblox Moon Animator 2.
Consists of two parts: a Python audio analyzer and a Roblox Studio plugin.

---

## How it works

1. You run the analyzer on a voice line (audio or video file).
2. The analyzer transcribes speech using WhisperX, maps each character to a viseme,
   and measures volume level at each timestamp.
3. It outputs a JSON file with frame-by-frame viseme and volume data.
4. You paste that JSON into the Roblox Studio plugin.
5. The plugin creates all Texture keyframes in your Moon Animator 2 save folder automatically.

---

## Parts

### Analyzer (lipsync\_v5\_1.py / LipSync\_v5.1.exe)

A desktop application with a GUI. Powered by WhisperX with forced phoneme alignment,
which gives precise per-character timestamps instead of estimated ones.

Supported input formats:
- Audio: wav, mp3, ogg, m4a, flac, aac, wma, opus, aiff
- Video: mp4, mkv, avi, mov, wmv, webm, flv and others (requires FFmpeg)

Supported languages: English, Ukrainian, Russian (auto-detected)

Volume detection: each keyframe is tagged as quiet, normal, or loud
based on RMS amplitude at that timestamp.

Output: a JSON file used directly by the plugin.

### Plugin (AutoLipSync\_v4.1.lua)

A Roblox Studio plugin for Moon Animator 2.
Takes the JSON from the analyzer and generates Texture keyframes automatically.

Supported visemes: CLOSED, A, E, I, O, U, M, F, S, L, T

Two modes:
- Simple — one texture per viseme regardless of volume
- Volume — separate textures for quiet, normal, and loud per viseme

Mode is selected automatically based on your config.

---

## Requirements

### Analyzer
- Python 3.9 or newer
- FFmpeg (only required for video input) — https://ffmpeg.org/download.html

All Python dependencies (whisperx, torch, torchaudio, librosa, etc.) are installed automatically into a local virtual environment by the installer. Nothing is changed system-wide.

### Plugin
- Roblox Studio with plugin execution enabled
- Moon Animator 2

---

## Installation

### Analyzer (Python version)
1. Install Python 3.9+ from https://python.org
   - During installation, check **"Add Python to PATH"**
2. Place all files from the release in the same folder
3. Run `install_lipsync.bat` — it will find your Python, create a local `venv`, and install all dependencies automatically
4. Once the installer finishes, launch the app with `launcher.py` (or double-click it)

> All dependencies are installed into a `venv` folder next to the scripts. Nothing is modified in your system Python.

### Analyzer (compiled .exe)
1. Download `LipSync_v5.1.exe` from the Releases page
2. Run it directly — no Python installation needed

### Plugin
1. Download `AutoLipSync_v4.1.lua` from the Releases page
2. Place it in your Roblox Plugins folder:
   - Windows: `%LOCALAPPDATA%\Roblox\Plugins\`
   - Mac: `~/Documents/Roblox/Plugins/`
3. Restart Roblox Studio
4. The plugin appears in the Plugins toolbar as "LipSync v4.1"

---

## Usage

1. Open the analyzer via `launcher.py` (Python version) or `LipSync_v5.1.exe`
2. Select your audio or video file
3. Set FPS to match your Moon Animator 2 animation (default: 24)
4. Choose a Whisper model size:
   - `base` — fast, good for clear recordings
   - `small` or `medium` — more accurate, slower
5. Click Analyze and wait for the JSON file to be saved
6. Open Roblox Studio and click the LipSync v4.1 button in the Plugins toolbar
7. Paste the JSON content into the JSON field and click Load JSON
8. Select your face folder in Explorer:
   `ServerStorage/MoonAnimator2Saves/[AnimName]/[N]`
9. Fill in the texture config with your asset IDs and click Apply Config
10. Click APPLY
11. Open Moon Animator 2 → File → Open to load the result

---

## Texture config format

```
CLOSED: 6550795382
A,E,I quiet: 2840140471
A,E,I loud: 6107690672
O,U quiet: 5998754410
O,U loud: 5921729062
M: 6550795382
F,S,L,T quiet: 2840140471
F,S,L,T loud: 6107690672
```

You can group multiple visemes on one line separated by commas.
The same asset ID can be used for multiple visemes.
If quiet/loud keywords are present the plugin uses Volume mode automatically.

---

## JSON output format

```json
{
  "meta": {
    "fps": 24,
    "total_frames": 312,
    "duration_sec": 13.0,
    "language": "en",
    "model": "base"
  },
  "keyframes": [
    { "time_sec": 0.0,  "frame": 0,  "viseme": "CLOSED", "volume": "normal" },
    { "time_sec": 0.12, "frame": 3,  "viseme": "A",      "volume": "loud"   },
    { "time_sec": 0.25, "frame": 6,  "viseme": "CLOSED", "volume": "normal" }
  ],
  "volume_levels": ["quiet", "normal", "loud"]
}
```

---

## Notes

- The `TH` viseme is not included. The analyzer never emits it.
- This pipeline works with texture-based face rigs only.
  It does not support Dynamic Heads or FaceControls.
- The `.exe` build does not require Python but is larger in file size.
- For video input, FFmpeg must be installed and available in PATH.

---

## Downloads

Go to the Releases page for the latest builds:
- `AutoLipSync_v4.1.lua` — Roblox Studio plugin
- `LipSync_v5.1.exe` — compiled analyzer for Windows (no Python needed)

---

## Community

Questions, bug reports, and feedback: [Discord](https://discord.gg/m75dmfyHKS)

---

The main changes from the old version:

- **Requirements** — removed the manual `pip install` command; the installer handles everything
- **Installation (Python version)** — replaced the old 3-step manual setup with the new `install_lipsync.bat` → `launcher.py` flow, plus a note that deps go into a local `venv`
- **Usage** — updated step 1 to mention `launcher.py` alongside the `.exe`
- **File names** — updated from `Lipsync4.py` / `Lipsync4.exe` to `lipsync_v5_1.py` / `LipSync_v5.1.exe` throughout
