"""
LipSync Analyzer v5.1 — With WhisperX Phoneme Alignment
Install: pip install whisperx torch torchaudio

CHANGES IN v5.0:
  + WhisperX instead of standard Whisper
  + Forced phoneme alignment for precise timestamps
  + Character-level timestamps (not just word-level)
  + Much more accurate lip-sync
  + Ukrainian language support via wav2vec2

ADVANTAGES:
  -> Precise timestamps for EACH character (not uniform distribution)
  -> Accounts for real pronunciation
  -> 70x faster than real-time
  -> Automatic alignment model selection
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import shutil
import tempfile
import json
import os
import sys
import webbrowser
import numpy as np
import warnings

DISCORD_URL = "https://discord.gg/czxF7hmZ"

warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")

# --- WhisperX Check -----------------------------------------------------------
def check_whisperx():
    try:
        import whisperx
        return True
    except ImportError:
        return False

# --- Volume Analysis ----------------------------------------------------------
def analyze_audio_volume(audio_path: str, segments: list, fps: int):
    try:
        import librosa
    except ImportError:
        return [{"volume": "normal", "db": 0.0} for _ in segments]

    y, sr = librosa.load(audio_path, sr=16000)
    results = []
    for seg in segments:
        start = seg.get("start", 0.0)
        end   = seg.get("end", start + 0.1)
        s0, s1 = int(start * sr), int(end * sr)
        chunk  = y[s0:s1]
        if len(chunk) == 0:
            results.append({"volume": "normal", "db": 0.0})
            continue
        rms = np.sqrt(np.mean(chunk**2))
        db  = 20 * np.log10(rms + 1e-10)
        volume = "quiet" if db < -35 else ("loud" if db >= -20 else "normal")
        results.append({"volume": volume, "db": float(db)})
    return results

# --- Viseme Mapping -----------------------------------------------------------
SILENCE_HOLD_SEC = 0.08

def char_to_viseme(ch):
    ch = ch.lower()
    vowels_a = set("aая")
    vowels_e = set("eеє")
    vowels_i = set("iіиї")
    vowels_o = set("oо")
    vowels_u = set("uую")
    bilabial  = set("mpbмпб")
    labio     = set("fvфв")
    sibilant  = set("szшщцчсз")
    liquid    = set("lrлр")

    if ch in vowels_a: return "A"
    if ch in vowels_e: return "E"
    if ch in vowels_i: return "I"
    if ch in vowels_o: return "O"
    if ch in vowels_u: return "U"
    if ch in bilabial: return "M"
    if ch in labio:    return "F"
    if ch in sibilant: return "S"
    if ch in liquid:   return "L"
    if ch in " \t\n":  return "CLOSED"
    return "T"

# --- File Types ---------------------------------------------------------------
AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".aac", ".wma", ".opus", ".aiff"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv", ".ts",
              ".m4v", ".3gp", ".mpeg", ".mpg", ".mts", ".vob"}

def is_video(path):  return os.path.splitext(path)[1].lower() in VIDEO_EXTS
def is_audio(path):  return os.path.splitext(path)[1].lower() in AUDIO_EXTS
def ffmpeg_available(): return shutil.which("ffmpeg") is not None

def extract_audio_from_video(video_path: str, log_fn=None) -> str:
    if not ffmpeg_available():
        raise RuntimeError("FFmpeg not found! Download: https://ffmpeg.org/download.html")

    import hashlib
    hash_name = hashlib.md5(video_path.encode()).hexdigest()[:12]
    out_wav = os.path.join(tempfile.gettempdir(), f"lipsync_{hash_name}.wav")

    if log_fn:
        log_fn("[VIDEO] Extracting audio from video...\n", "info")

    cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
           "-ar", "16000", "-ac", "1", out_wav]
    try:
        kw = {}
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kw["startupinfo"] = si
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=300, encoding="utf-8", errors="replace", **kw)
    except Exception as e:
        raise RuntimeError(f"FFmpeg error: {e}")

    if proc.returncode != 0 or not os.path.exists(out_wav):
        raise RuntimeError("FFmpeg did not create the output file")

    if log_fn:
        mb = os.path.getsize(out_wav) / 1024 / 1024
        log_fn(f"[OK] Audio extracted ({mb:.1f} MB)\n", "ok")
    return out_wav

# --- Diagnostics --------------------------------------------------------------
def get_diagnostics() -> str:
    import platform, importlib
    lines = [
        f"Python:    {sys.version.split()[0]}",
        f"OS:        {platform.platform()}",
        f"FFmpeg:    {'[OK]' if ffmpeg_available() else '[X] NOT FOUND'}",
        f"WhisperX:  {'[OK]' if check_whisperx() else '[X] NOT INSTALLED'}",
    ]
    for pkg in ("whisperx", "torch", "torchaudio", "librosa", "numpy"):
        try:
            m   = importlib.import_module(pkg)
            ver = getattr(m, "__version__", "?")
            lines.append(f"  {pkg:<12} v{ver}")
        except Exception as e:
            lines.append(f"  {pkg:<12} [X]  {str(e)[:40]}")
    return "\n".join(lines)

# --- Stop Exception -----------------------------------------------------------
class StopAnalysis(Exception):
    pass

# --- MAIN ANALYSIS WITH WHISPERX ----------------------------------------------
def run_analysis_whisperx(audio_path: str, fps: int, language, model_name: str,
                          log_fn=None, stop_flag=None) -> dict:
    if not ffmpeg_available():
        raise RuntimeError("FFmpeg not found! Install: https://ffmpeg.org/download.html")
    if not check_whisperx():
        raise RuntimeError(
            "WhisperX is not installed!\n\n"
            "Install with:\n"
            "pip install whisperx\n\n"
            "Or:\n"
            "pip install git+https://github.com/m-bain/whisperX.git"
        )
    if not os.path.exists(audio_path):
        raise RuntimeError(f"File not found: {audio_path}")

    if log_fn:
        log_fn(f"[FILE] Audio: {os.path.basename(audio_path)}\n", "info")
        log_fn(f"       Size:  {os.path.getsize(audio_path) / 1024 / 1024:.1f} MB\n", "dim")

    try:
        import whisperx
        import torch
    except Exception as e:
        raise RuntimeError(f"WhisperX import error: {e}")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    if device == "cuda":
        try:
            import ctranslate2
            supported = ctranslate2.get_supported_compute_types("cuda")
            compute_type = "float16" if "float16" in supported else "float32"
        except Exception:
            compute_type = "float32"
    else:
        compute_type = "float32"

    batch_size = 16 if device == "cuda" else 4

    if stop_flag and stop_flag.is_set():
        raise StopAnalysis("Stopped")

    if log_fn:
        log_fn(f"[WhisperX] Device: {device.upper()} | compute: {compute_type}\n", "info")
        log_fn(f"[WhisperX] Loading model '{model_name}'...\n", "dim")

    model = None
    model_a = None
    try:
        model = whisperx.load_model(model_name, device, compute_type=compute_type)
    except Exception as e:
        raise RuntimeError(f"Model load error: {e}")

    if stop_flag and stop_flag.is_set():
        del model
        if device == "cuda":
            torch.cuda.empty_cache()
        raise StopAnalysis("Stopped")

    if log_fn:
        log_fn("[WhisperX] Transcribing...\n", "dim")

    try:
        audio  = whisperx.load_audio(audio_path)
        result = model.transcribe(audio, batch_size=batch_size, language=language)
    except Exception as e:
        del model
        raise RuntimeError(f"Transcription error: {e}")

    del model
    if device == "cuda":
        torch.cuda.empty_cache()

    if stop_flag and stop_flag.is_set():
        raise StopAnalysis("Stopped")

    detected_lang = result.get("language", language or "uk")
    if log_fn:
        log_fn(f"[OK] Language: {detected_lang}\n", "ok")
        log_fn("[WhisperX] Forced alignment (phoneme-level)...\n", "dim")

    result_aligned = None
    try:
        model_a, metadata = whisperx.load_align_model(
            language_code=detected_lang,
            device=device
        )
        result_aligned = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio,
            device,
            return_char_alignments=True
        )
    except Exception as e:
        if log_fn:
            log_fn(f"[!] Alignment unavailable for language {detected_lang}: {e}\n", "warn")
            log_fn("    Using basic Whisper without alignment\n", "warn")
        result_aligned = {"segments": result["segments"], "word_segments": []}
    finally:
        if model_a is not None:
            del model_a
        if device == "cuda":
            torch.cuda.empty_cache()

    if stop_flag and stop_flag.is_set():
        raise StopAnalysis("Stopped")

    if log_fn:
        log_fn("[Volume] Analyzing volume...\n", "dim")

    segment_list = []
    for segment in result_aligned.get("segments", []):
        words = segment.get("words", [])
        if words:
            for word in words:
                segment_list.append({
                    "start": word.get("start", segment.get("start", 0.0)),
                    "end":   word.get("end",   segment.get("end",   0.0)),
                    "word":  word.get("word", "")
                })
        else:
            segment_list.append({
                "start": segment.get("start", 0.0),
                "end":   segment.get("end",   0.0),
                "word":  segment.get("text", "").strip()
            })

    try:
        volume_data = analyze_audio_volume(audio_path, segment_list, fps)
    except Exception:
        volume_data = [{"volume": "normal", "db": 0.0} for _ in segment_list]

    if stop_flag and stop_flag.is_set():
        raise StopAnalysis("Stopped")

    keyframes = []
    last_end  = 0.0
    vol_idx   = 0

    for segment in result_aligned.get("segments", []):
        if stop_flag and stop_flag.is_set():
            raise StopAnalysis("Stopped")

        words = segment.get("words", [])

        if not words:
            seg_start = segment.get("start", 0.0)
            seg_end   = segment.get("end",   seg_start + 0.1)
            seg_text  = segment.get("text", "").strip()
            vol_info  = volume_data[vol_idx] if vol_idx < len(volume_data) else {"volume": "normal", "db": 0.0}
            vol_idx  += 1

            if seg_start > last_end + 0.05:
                keyframes.append({"time_sec": round(last_end, 4), "frame": int(last_end * fps),
                                  "viseme": "CLOSED", "word": "", "volume": "quiet", "db": -50.0})

            clean   = "".join(c for c in seg_text if c.isalpha())
            if clean:
                char_dur = (seg_end - seg_start) / max(len(clean), 1)
                prev_vis = None
                for i, ch in enumerate(clean):
                    vis = char_to_viseme(ch)
                    t   = seg_start + i * char_dur
                    if vis != prev_vis:
                        keyframes.append({"time_sec": round(t, 4), "frame": int(t * fps),
                                          "viseme": vis, "word": seg_text,
                                          "volume": vol_info["volume"], "db": vol_info["db"]})
                        prev_vis = vis

            close_t  = seg_end + SILENCE_HOLD_SEC
            keyframes.append({"time_sec": round(close_t, 4), "frame": int(close_t * fps),
                              "viseme": "CLOSED", "word": "", "volume": "quiet", "db": -50.0})
            last_end = close_t
            continue

        for word_info in words:
            word       = word_info.get("word", "").strip()
            word_start = word_info.get("start", 0.0)
            word_end   = word_info.get("end",   0.0)

            vol_info  = volume_data[vol_idx] if vol_idx < len(volume_data) else {"volume": "normal", "db": 0.0}
            vol_idx  += 1

            if word_start > last_end + 0.05:
                keyframes.append({"time_sec": round(last_end, 4), "frame": int(last_end * fps),
                                  "viseme": "CLOSED", "word": "", "volume": "quiet", "db": -50.0})

            if "chars" in word_info and word_info["chars"]:
                prev_vis = None
                for char_info in word_info["chars"]:
                    ch         = char_info.get("char", "")
                    char_start = char_info.get("start", word_start)
                    if ch.strip():
                        vis = char_to_viseme(ch)
                        if vis != prev_vis:
                            keyframes.append({"time_sec": round(char_start, 4),
                                              "frame": int(char_start * fps),
                                              "viseme": vis, "word": word,
                                              "volume": vol_info["volume"], "db": vol_info["db"]})
                            prev_vis = vis
            else:
                clean    = "".join(c for c in word if c.isalpha())
                if clean:
                    char_dur = (word_end - word_start) / max(len(clean), 1)
                    prev_vis = None
                    for i, ch in enumerate(clean):
                        vis = char_to_viseme(ch)
                        t   = word_start + i * char_dur
                        if vis != prev_vis:
                            keyframes.append({"time_sec": round(t, 4), "frame": int(t * fps),
                                              "viseme": vis, "word": word,
                                              "volume": vol_info["volume"], "db": vol_info["db"]})
                            prev_vis = vis

            close_t  = word_end + SILENCE_HOLD_SEC
            keyframes.append({"time_sec": round(close_t, 4), "frame": int(close_t * fps),
                              "viseme": "CLOSED", "word": "", "volume": "quiet", "db": -50.0})
            last_end = close_t

    keyframes.sort(key=lambda x: x["time_sec"])
    deduped = []
    for kf in keyframes:
        if not deduped or kf["frame"] != deduped[-1]["frame"]:
            deduped.append(kf)

    segments_list = result_aligned.get("segments", [])
    if segments_list:
        last_seg = segments_list[-1]
        total = float(last_seg.get("end", last_seg.get("start", 0.0)))
    else:
        total = 0.0

    vol_stats = {"quiet": 0, "normal": 0, "loud": 0}
    for kf in deduped:
        vol_stats[kf.get("volume", "normal")] += 1

    transcript = " ".join(seg.get("text", "") for seg in result.get("segments", []))

    return {
        "meta": {
            "audio_file":    os.path.basename(audio_path),
            "fps":           fps,
            "total_frames":  int(total * fps),
            "total_seconds": round(total, 4),
            "language":      detected_lang,
            "transcript":    transcript,
            "volume_stats":  vol_stats,
            "engine":        "WhisperX",
            "alignment":     "character-level (forced phoneme alignment)"
        },
        "viseme_groups":  ["CLOSED","A","E","I","O","U","M","F","S","L","T"],
        "volume_levels":  ["quiet", "normal", "loud"],
        "keyframes":      deduped,
    }

# --- UI Colors ----------------------------------------------------------------
BG       = "#1e1e23"
PANEL    = "#2a2a32"
ACCENT   = "#64b4ff"
GREEN    = "#64dc82"
RED      = "#ff5a5a"
YELLOW   = "#ffc832"
ORANGE   = "#ff9a3c"
TEXT     = "#e6e6e6"
DIMTEXT  = "#96969f"
BORDER   = "#3c3c46"
BTN_BG   = "#3a3a50"
DISCORD  = "#5865F2"
ENTRY_BG = "#111115"

FONT      = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_MONO = ("Consolas", 9)

# --- GUI Application ----------------------------------------------------------
class LipSyncApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto LipSync v5.1 (WhisperX)")
        self.geometry("530x750")
        self.minsize(460, 600)
        self.configure(bg=BG)

        # ── FIX: Style the Combobox dropdown Listbox BEFORE any widgets exist ──
        # ttk.Combobox dropdown is a plain tk.Listbox — needs option_add to style
        self.option_add("*TCombobox*Listbox.background",       BG)
        self.option_add("*TCombobox*Listbox.foreground",       TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.option_add("*TCombobox*Listbox.selectForeground", "#0a0a14")
        self.option_add("*TCombobox*Listbox.font",             FONT_MONO)

        # Set window icon if available
        try:
            icon_path = self._get_resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        self.input_path  = tk.StringVar()
        self.output_path = tk.StringVar()
        self.fps_var     = tk.StringVar(value="24")
        self.lang_var    = tk.StringVar(value="auto")
        self.model_var   = tk.StringVar(value="base")
        self.running     = False
        self._result_path = None
        self._result_data = None
        self._tmp_wav     = None
        self._stop_flag   = None
        self._ffmpeg_ok   = ffmpeg_available()
        self._whisperx_ok = check_whisperx()

        self._build_ui()
        self._center()
        self._check_deps()

    def _get_resource_path(self, relative_path):
        """Get absolute path to resource — works for dev and PyInstaller."""
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"{w}x{h}+"
                      f"{(self.winfo_screenwidth()-w)//2}+"
                      f"{(self.winfo_screenheight()-h)//2}")

    def _check_deps(self):
        issues = []
        if not self._ffmpeg_ok:
            issues.append("[X] FFmpeg not found!")
        if not self._whisperx_ok:
            issues.append("[X] WhisperX not installed!")
            issues.append("    Install: pip install whisperx")
        if issues:
            self._log("\n".join(issues) + "\n\n", "err")
            missing = []
            if not self._ffmpeg_ok:
                missing.append("FFmpeg")
            if not self._whisperx_ok:
                missing.append("WhisperX")
            self._run_btn.configure(state="disabled",
                                    text="[X] Missing: " + " + ".join(missing))
        else:
            self._log("[OK] v5.1 - WhisperX ready!\n", "ok")
            self._log("[>>] Character-level phoneme alignment\n", "ok")
            self._log("Select a file and press Run\n\n", "dim")

    def _build_ui(self):
        hdr = tk.Frame(self, bg="#14141c", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="LIPSYNC v5.1  (WhisperX)",
                 font=("Segoe UI", 15, "bold"), bg="#14141c", fg=ACCENT).pack()
        tk.Label(hdr, text="Phoneme Alignment  |  Character-Level Timestamps",
                 font=("Segoe UI", 9), bg="#14141c", fg=GREEN).pack()
        discord_btn = tk.Button(
            hdr, text="Discord", command=self._open_discord,
            bg=DISCORD, fg="#ffffff", font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2",
            activebackground="#4752c4", padx=12, pady=3
        )
        discord_btn.pack(pady=(6, 2))

        outer  = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        sb     = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._content = tk.Frame(canvas, bg=BG)
        cid = canvas.create_window((0, 0), window=self._content, anchor="nw")
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(cid, width=e.width))
        self._content.bind("<Configure>",
                           lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self._fill_ui(self._content)

    def _sep(self, parent, title):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", padx=14, pady=(12, 4))
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x", pady=(0, 4))
        tk.Label(f, text=title, font=FONT_BOLD, bg=BG, fg=ACCENT).pack(anchor="w")

    def _panel(self, parent):
        p = tk.Frame(parent, bg=PANEL, padx=12, pady=10)
        p.pack(fill="x", padx=14, pady=3)
        return p

    def _btn(self, parent, text, cmd, bg=ACCENT, fg="#0a0a14", **kw):
        return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                         font=FONT_BOLD, relief="flat", cursor="hand2",
                         activebackground=bg, padx=10, pady=6, **kw)

    def _fill_ui(self, root):
        # ── FIX: Configure ttk styles with full dark-theme colors ──
        sty = ttk.Style()
        sty.theme_use("clam")
        sty.configure("TCombobox",
                      fieldbackground=ENTRY_BG,
                      background=BTN_BG,
                      foreground=TEXT,
                      arrowcolor=ACCENT,
                      borderwidth=0,
                      selectbackground=ENTRY_BG,
                      selectforeground=TEXT)
        sty.map("TCombobox",
                fieldbackground=[("readonly", ENTRY_BG), ("disabled", PANEL)],
                foreground=[("readonly", TEXT), ("disabled", DIMTEXT)],
                selectbackground=[("readonly", ENTRY_BG)],
                selectforeground=[("readonly", TEXT)],
                background=[("readonly", BTN_BG)])
        sty.configure("Accent.Horizontal.TProgressbar",
                      troughcolor=BG, background=ACCENT, thickness=4)
        # Style scrollbars
        sty.configure("TScrollbar",
                      background=BTN_BG, troughcolor=PANEL,
                      arrowcolor=ACCENT, borderwidth=0)

        # (1) File
        self._sep(root, "(1)  Audio or Video")
        p1 = self._panel(root)
        row = tk.Frame(p1, bg=PANEL)
        row.pack(fill="x")
        tk.Entry(row, textvariable=self.input_path, font=FONT_MONO,
                 bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT, relief="flat",
                 readonlybackground=ENTRY_BG, disabledforeground=TEXT,
                 state="readonly").pack(side="left", fill="x", expand=True, ipady=5, padx=(0,8))
        self._btn(row, "Browse...", self._pick, bg=BTN_BG, fg=TEXT).pack(side="right")
        self._badge = tk.Label(p1, text="", font=("Segoe UI", 8, "bold"),
                               bg=PANEL, fg=DIMTEXT)
        self._badge.pack(anchor="w", pady=(5, 0))

        # (2) Output
        self._sep(root, "(2)  Save JSON")
        p2 = self._panel(root)
        row2 = tk.Frame(p2, bg=PANEL)
        row2.pack(fill="x")
        tk.Entry(row2, textvariable=self.output_path, font=FONT_MONO,
                 bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT, relief="flat",
                 readonlybackground=ENTRY_BG, disabledforeground=TEXT,
                 state="readonly").pack(side="left", fill="x", expand=True, ipady=5, padx=(0,8))
        self._btn(row2, "Save As...", self._pick_out, bg=BTN_BG, fg=TEXT).pack(side="right")

        # (3) Settings
        self._sep(root, "(3)  Settings")
        p3 = self._panel(root)
        g = tk.Frame(p3, bg=PANEL)
        g.pack(fill="x")
        g.columnconfigure(1, weight=1)
        tk.Label(g, text="FPS:", font=FONT, bg=PANEL, fg=TEXT
                 ).grid(row=0, column=0, sticky="w", pady=4, padx=(0,8))
        ttk.Combobox(g, textvariable=self.fps_var, values=["24","30","60"],
                     width=6, state="readonly").grid(row=0, column=1, sticky="w")
        tk.Label(g, text="Language:", font=FONT, bg=PANEL, fg=TEXT
                 ).grid(row=0, column=2, sticky="w", pady=4, padx=(20,8))
        ttk.Combobox(g, textvariable=self.lang_var,
                     values=["auto","uk","ru","en","de","fr","ja","zh"],
                     width=8, state="readonly").grid(row=0, column=3, sticky="w")
        tk.Label(g, text="Model:", font=FONT, bg=PANEL, fg=TEXT
                 ).grid(row=1, column=0, sticky="w", pady=(8,0), padx=(0,8))
        ttk.Combobox(g, textvariable=self.model_var,
                     values=["tiny","base","small","medium","large","large-v2","large-v3"],
                     width=10, state="readonly").grid(row=1, column=1, sticky="w", pady=(8,0))

        # (4) Run
        self._sep(root, "(4)  Analysis")
        p4 = self._panel(root)
        run_row = tk.Frame(p4, bg=PANEL)
        run_row.pack(fill="x")
        self._run_btn = self._btn(run_row, "[ > ] Run", self._run)
        self._run_btn.pack(side="left", fill="x", expand=True, ipady=8, padx=(0,8))
        self._stop_btn = self._btn(run_row, "[ STOP ]", self._stop, bg=RED, fg="#fff")
        self._stop_btn.pack(side="left", ipady=8, padx=(0,8))
        self._stop_btn.configure(state="disabled")
        self._btn(run_row, "Diagnostics", self._show_diag,
                  bg=BTN_BG, fg=TEXT).pack(side="right", ipady=8)
        self._progress = ttk.Progressbar(p4, mode="indeterminate",
                                         style="Accent.Horizontal.TProgressbar")
        self._progress.pack(fill="x", pady=(8, 0))
        self._status_var = tk.StringVar(value="Waiting...")
        self._status_lbl = tk.Label(p4, textvariable=self._status_var,
                                    font=FONT, bg=PANEL, fg=DIMTEXT,
                                    wraplength=440, justify="left")
        self._status_lbl.pack(anchor="w", pady=(6, 0))

        # (5) Log
        self._sep(root, "(5)  Log")
        p5 = tk.Frame(root, bg=BG)
        p5.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        wrap = tk.Frame(p5, bg=PANEL)
        wrap.pack(fill="both", expand=True)
        self._log_box = tk.Text(wrap, font=FONT_MONO, bg=PANEL, fg=TEXT,
                                insertbackground=TEXT, relief="flat",
                                state="disabled", wrap="word", height=10)
        lsb = ttk.Scrollbar(wrap, command=self._log_box.yview)
        self._log_box.configure(yscrollcommand=lsb.set)
        lsb.pack(side="right", fill="y")
        self._log_box.pack(fill="both", expand=True, padx=6, pady=6)
        for tag, color in [("ok",GREEN),("err",RED),("info",ACCENT),
                            ("dim",DIMTEXT),("warn",ORANGE)]:
            self._log_box.tag_config(tag, foreground=color)
        br = tk.Frame(p5, bg=BG)
        br.pack(fill="x", pady=(6, 0))
        self._open_btn = self._btn(br, "Open File", self._open_result, bg=BTN_BG, fg=TEXT)
        self._open_btn.pack(side="left", padx=(0, 8))
        self._open_btn.configure(state="disabled")
        self._copy_btn = self._btn(br, "Copy JSON", self._copy_json, bg=BTN_BG, fg=TEXT)
        self._copy_btn.pack(side="left")
        self._copy_btn.configure(state="disabled")

    def _pick(self):
        audio_pat = " ".join(f"*{e}" for e in sorted(AUDIO_EXTS))
        video_pat = " ".join(f"*{e}" for e in sorted(VIDEO_EXTS))
        path = filedialog.askopenfilename(
            title="Select audio or video file",
            filetypes=[("All media", audio_pat + " " + video_pat),
                       ("Audio", audio_pat), ("Video", video_pat)])
        if not path:
            return
        self.input_path.set(path)
        if not self.output_path.get():
            self.output_path.set(os.path.splitext(path)[0] + "_lipsync.json")
        ext = os.path.splitext(path)[1].lower()
        if is_video(path):
            self._badge.configure(text=f"[VIDEO] {ext}", fg=ORANGE)
        else:
            self._badge.configure(text=f"[AUDIO] {ext}", fg=GREEN)
        self._log(f"[OK] File: {os.path.basename(path)}\n\n", "info")

    def _pick_out(self):
        cur  = self.output_path.get() or os.path.expanduser("~")
        path = filedialog.asksaveasfilename(
            title="Save JSON", initialfile="lipsync.json",
            initialdir=os.path.dirname(cur),
            defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            self.output_path.set(path)

    def _stop(self):
        if self._stop_flag:
            self._stop_flag.set()
            self._log("\n[STOP] Stopping...\n", "warn")

    def _run(self):
        if self.running:
            return
        if not self._ffmpeg_ok or not self._whisperx_ok:
            messagebox.showerror("Error",
                "WhisperX or FFmpeg is not installed!\n\n"
                "Install:\n"
                "pip install whisperx\n"
                "and FFmpeg from https://ffmpeg.org")
            return
        src = self.input_path.get()
        if not src or not os.path.exists(src):
            messagebox.showwarning("Error", "Please select a file!")
            return
        out = self.output_path.get() or (os.path.splitext(src)[0] + "_lipsync.json")
        self.output_path.set(out)
        fps   = int(self.fps_var.get() or 24)
        lang  = self.lang_var.get()
        lang  = None if lang == "auto" else lang
        model = self.model_var.get()

        self._set_busy(True)
        self._open_btn.configure(state="disabled")
        self._copy_btn.configure(state="disabled")
        self._clear_log()
        self._log("[ > ] START (WhisperX + Phoneme Alignment)\n", "info")
        self._log(f"{'=' * 50}\n", "dim")
        self._stop_flag = threading.Event()

        def worker():
            try:
                audio = src
                if is_video(src):
                    self.after(0, lambda: self._log("[VIDEO] Extracting audio...\n", "info"))
                    audio = extract_audio_from_video(src,
                        log_fn=lambda m, t="dim": self.after(0, self._log, m, t))
                    self._tmp_wav = audio

                data = run_analysis_whisperx(audio, fps, lang, model,
                    log_fn=lambda m, t="dim": self.after(0, self._log, m, t),
                    stop_flag=self._stop_flag)

                with open(out, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                if self._tmp_wav:
                    try: os.remove(self._tmp_wav)
                    except: pass
                    self._tmp_wav = None

                self.after(0, self._done, data, out)

            except StopAnalysis:
                if self._tmp_wav:
                    try: os.remove(self._tmp_wav)
                    except: pass
                self.after(0, self._stopped)

            except Exception as e:
                import traceback as _tb
                if self._tmp_wav:
                    try: os.remove(self._tmp_wav)
                    except: pass
                self.after(0, self._error, str(e), _tb.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def _stopped(self):
        self._set_busy(False)
        self._log("\n[STOP] Analysis stopped\n", "warn")
        self._stop_flag = None

    def _done(self, data, out):
        self._set_busy(False)
        kf  = len(data["keyframes"])
        dur = data["meta"]["total_seconds"]
        lng = data["meta"]["language"]
        vol = data["meta"].get("volume_stats", {})
        self._log(f"\n{'=' * 50}\n", "dim")
        self._log("[DONE] COMPLETE!\n", "ok")
        self._log(f"{'=' * 50}\n", "dim")
        self._log(f"Keyframes:   {kf}\n", "ok")
        self._log(f"Duration:    {dur:.2f}s\n", "ok")
        self._log(f"Language:    {lng}\n", "ok")
        self._log(f"Volume:      Q:{vol.get('quiet',0)}  N:{vol.get('normal',0)}  L:{vol.get('loud',0)}\n", "ok")
        self._log(f"Engine:      {data['meta'].get('engine','?')}\n", "ok")
        self._log(f"Alignment:   {data['meta'].get('alignment','?')}\n", "ok")
        self._log(f"\n[SAVED] {out}\n", "info")
        self._result_path = out
        self._result_data = data
        self._open_btn.configure(state="normal")
        self._copy_btn.configure(state="normal")
        self._stop_flag = None

    def _error(self, msg, full=""):
        self._set_busy(False)
        self._log(f"\n{'=' * 50}\n", "err")
        self._log("[X] ERROR\n", "err")
        self._log(f"{'=' * 50}\n", "err")
        self._log(f"{msg}\n\n", "err")
        self._log("Details:\n", "dim")
        self._log(full, "dim")
        self._stop_flag = None

    def _open_discord(self):
        webbrowser.open(DISCORD_URL)

    def _show_diag(self):
        info = get_diagnostics()
        win  = tk.Toplevel(self)
        win.title("Diagnostics")
        win.configure(bg=BG)
        win.geometry("500x300")
        try:
            icon_path = self._get_resource_path("icon.ico")
            if os.path.exists(icon_path):
                win.iconbitmap(icon_path)
        except Exception:
            pass
        tk.Label(win, text="Diagnostics",
                 font=("Segoe UI", 12, "bold"), bg=BG, fg=ACCENT, pady=10).pack()
        txt = tk.Text(win, font=FONT_MONO, bg=PANEL, fg=TEXT,
                      relief="flat", wrap="word", padx=10, pady=8)
        txt.pack(fill="both", expand=True, padx=12, pady=(0,8))
        txt.insert("end", info)
        txt.configure(state="disabled")
        self._btn(win, "Close", win.destroy, bg=BTN_BG, fg=TEXT).pack(pady=(0,10))

    def _set_busy(self, val):
        self.running = val
        if val:
            self._run_btn.configure(text="[ ... ] Processing...", state="disabled")
            self._stop_btn.configure(state="normal")
            self._progress.start(12)
        else:
            self._run_btn.configure(text="[ > ] Run", state="normal")
            self._stop_btn.configure(state="disabled")
            self._progress.stop()

    def _open_result(self):
        p = self._result_path
        if p and os.path.exists(p):
            if sys.platform == "win32":  os.startfile(p)
            elif sys.platform == "darwin": subprocess.run(["open", p])
            else: subprocess.run(["xdg-open", p])

    def _copy_json(self):
        if self._result_data:
            self.clipboard_clear()
            self.clipboard_append(json.dumps(self._result_data, ensure_ascii=False, indent=2))
            self._copy_btn.configure(text="[OK] Copied!", bg=GREEN)
            self.after(2000, lambda: self._copy_btn.configure(
                text="Copy JSON", bg=BTN_BG))

    def _log(self, msg, tag=None):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg, tag or "")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")


if __name__ == "__main__":
    try:
        app = LipSyncApp()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter...")
        sys.exit(1)