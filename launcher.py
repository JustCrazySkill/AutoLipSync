# launcher.py
import os, sys, subprocess, ctypes

BASE        = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
VENV_PYTHON = os.path.join(BASE, "venv", "Scripts", "python.exe")
SCRIPT      = os.path.join(BASE, "lipsync_v5_1.py")

def alert(msg):
    ctypes.windll.user32.MessageBoxW(0, msg, "LipSync v5.1", 0x10)

if not os.path.exists(VENV_PYTHON):
    alert("venv не найден!\n\nСначала запустите install_lipsync.bat")
    sys.exit(1)

if not os.path.exists(SCRIPT):
    alert("lipsync_v5_1.py не найден!\nВсе файлы должны быть в одной папке.")
    sys.exit(1)

subprocess.Popen([VENV_PYTHON, SCRIPT], cwd=BASE)