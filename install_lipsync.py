"""
╔══════════════════════════════════════════════════════════════╗
║          AUTO LIPSYNC v5.1 — INSTALLER                      ║
║          Устанавливает все зависимости в локальный venv      ║
╚══════════════════════════════════════════════════════════════╝

Использование:
  python install_lipsync.py

Что делает:
  1. Создаёт ./venv/ рядом с собой
  2. Устанавливает torch, torchaudio, whisperx, librosa и др.
  3. Сохраняет всё ЛОКАЛЬНО — ничего не меняет в системе

Требования:
  Python 3.9+ уже должен быть установлен.
"""

import sys
import os
import subprocess
import platform
import shutil
import time
import venv as venv_module

# ─────────────────────────────────────────────────────────────
# COLORS (Windows CMD / Unix terminal)
# ─────────────────────────────────────────────────────────────
if sys.platform == "win32":
    os.system("color")  # enable ANSI on Windows

C_RESET  = "\033[0m"
C_BOLD   = "\033[1m"
C_CYAN   = "\033[96m"
C_GREEN  = "\033[92m"
C_YELLOW = "\033[93m"
C_RED    = "\033[91m"
C_DIM    = "\033[2m"
C_BLUE   = "\033[94m"

def ok(msg):    print(f"  {C_GREEN}[OK] {msg}{C_RESET}")
def info(msg):  print(f"  {C_CYAN}[>>] {msg}{C_RESET}")
def warn(msg):  print(f"  {C_YELLOW}[!]  {msg}{C_RESET}")
def err(msg):   print(f"  {C_RED}[X]  {msg}{C_RESET}")
def dim(msg):   print(f"{C_DIM}       {msg}{C_RESET}")
def sep():      print(f"\n{C_DIM}{'─' * 62}{C_RESET}\n")
def head(msg):  print(f"\n{C_BOLD}{C_CYAN}  ▶  {msg}{C_RESET}")

# ─────────────────────────────────────────────────────────────
# ПУТИ
# ─────────────────────────────────────────────────────────────
INSTALLER_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR      = os.path.join(INSTALLER_DIR, "venv")

if sys.platform == "win32":
    VENV_PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
    VENV_PIP    = os.path.join(VENV_DIR, "Scripts", "pip.exe")
else:
    VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
    VENV_PIP    = os.path.join(VENV_DIR, "bin", "pip")

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def run_in_venv(*args, show_output=False):
    """Запускает pip-команду в локальном venv."""
    cmd = [VENV_PYTHON, "-m", "pip", "install", "--quiet"] + list(args)
    if show_output:
        result = subprocess.run(cmd, text=True)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, (result.stdout + result.stderr) if not show_output else ""

def check_import_in_venv(module):
    """Проверяет, установлен ли модуль в venv."""
    result = subprocess.run(
        [VENV_PYTHON, "-c",
         f"import {module}; print(getattr({module}, '__version__', 'ok'))"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, ""

def ffmpeg_found():
    return shutil.which("ffmpeg") is not None

def get_cuda_version():
    """Определяет версию CUDA через nvidia-smi."""
    nismi = shutil.which("nvidia-smi")
    if not nismi:
        return None

    cuda_ver = None
    gpu_name = None

    try:
        # Версия драйвера
        r = subprocess.run(
            [nismi, "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0 and r.stdout.strip():
            info(f"NVIDIA driver  : {r.stdout.strip()}")

        # GPU name
        r2 = subprocess.run(
            [nismi, "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if r2.returncode == 0 and r2.stdout.strip():
            gpu_name = r2.stdout.strip()
            info(f"GPU name       : {gpu_name}")

        # CUDA version из таблицы nvidia-smi
        r3 = subprocess.run([nismi], capture_output=True, text=True, timeout=5)
        for line in r3.stdout.splitlines():
            if "CUDA Version" in line:
                parts = line.split("CUDA Version:")
                if len(parts) > 1:
                    raw = parts[1].strip().split()[0].strip("|").strip()
                    if raw and raw[0].isdigit():
                        cuda_ver = raw
                        info(f"CUDA version   : {cuda_ver}")
                break
    except Exception:
        pass

    # nvcc как запасной вариант
    nvcc = shutil.which("nvcc")
    if nvcc and not cuda_ver:
        try:
            r = subprocess.run([nvcc, "--version"], capture_output=True, text=True, timeout=5)
            for line in r.stdout.splitlines():
                if "release" in line.lower():
                    parts = line.split("release ")
                    if len(parts) > 1:
                        cuda_ver = parts[1].split(",")[0].strip()
                        info(f"CUDA toolkit   : {cuda_ver}  (nvcc)")
        except Exception:
            pass

    return cuda_ver


def cuda_tag_from_ver(ver):
    """Переводит версию CUDA в тег для PyTorch index."""
    if not ver:
        return None
    mapping = {
        "12.8": "cu128", "12.7": "cu126", "12.6": "cu126",
        "12.5": "cu124", "12.4": "cu124", "12.3": "cu121",
        "12.2": "cu121", "12.1": "cu121", "12.0": "cu121",
        "11.8": "cu118", "11.7": "cu118", "11.6": "cu118",
    }
    if ver in mapping:
        return mapping[ver]
    for key, tag in mapping.items():
        if ver.startswith(key):
            return tag
    major = ver.split(".")[0]
    return "cu126" if major == "12" else ("cu118" if major == "11" else None)


# ─────────────────────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────────────────────
def print_banner():
    print(f"""
{C_BOLD}{C_CYAN}
  ╔══════════════════════════════════════════════════════════╗
  ║                                                          ║
  ║       AUTO LIPSYNC v5.1  —  УСТАНОВЩИК ЗАВИСИМОСТЕЙ     ║
  ║       WhisperX · PyTorch · Librosa · NumPy               ║
  ║       Устанавливает в локальный ./venv/                  ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝
{C_RESET}""")


# ─────────────────────────────────────────────────────────────
# ШАГ 1 — Проверка Python
# ─────────────────────────────────────────────────────────────
def step_check_python():
    head("ШАГ 1 / 6  — Проверка версии Python")
    sep()
    v = sys.version_info
    info(f"Python version : {v.major}.{v.minor}.{v.micro}")
    info(f"Executable     : {sys.executable}")
    info(f"Platform       : {platform.platform()}")
    info(f"Папка venv     : {VENV_DIR}")

    if v.major < 3 or (v.major == 3 and v.minor < 9):
        err("Требуется Python 3.9+!")
        err(f"У тебя Python {v.major}.{v.minor}. Обнови: https://python.org/downloads")
        sys.exit(1)

    if v.major == 3 and v.minor >= 14:
        warn(f"Python {v.major}.{v.minor} — WhisperX официально тестируется на 3.10–3.13.")
        warn("Будет использован --ignore-requires-python.")
    else:
        ok(f"Python {v.major}.{v.minor} — OK")


# ─────────────────────────────────────────────────────────────
# ШАГ 2 — Создание venv
# ─────────────────────────────────────────────────────────────
def step_create_venv():
    head("ШАГ 2 / 6  — Создание локального venv")
    sep()

    if os.path.isfile(VENV_PYTHON):
        ok(f"venv уже существует: {VENV_DIR}")
        ans = input(f"  {C_YELLOW}Пересоздать venv? [y/N]: {C_RESET}").strip().lower()
        if ans == "y":
            info("Удаляю старый venv...")
            shutil.rmtree(VENV_DIR, ignore_errors=True)
        else:
            ok("Используем существующий venv.")
            return

    info(f"Создаю venv в {VENV_DIR} ...")
    try:
        venv_module.create(VENV_DIR, with_pip=True)
    except Exception as e:
        err(f"Не удалось создать venv: {e}")
        sys.exit(1)

    if not os.path.isfile(VENV_PYTHON):
        err("venv создан, но python не найден — что-то пошло не так.")
        sys.exit(1)

    # Обновить pip внутри venv
    info("Обновляю pip в venv...")
    subprocess.run([VENV_PYTHON, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    ok("venv создан и pip обновлён.")


# ─────────────────────────────────────────────────────────────
# ШАГ 3 — Определить GPU / CUDA
# ─────────────────────────────────────────────────────────────
def step_detect_gpu():
    head("ШАГ 3 / 6  — Определение GPU / CUDA")
    sep()

    cuda_ver = get_cuda_version()

    if cuda_ver:
        ok(f"NVIDIA GPU + CUDA {cuda_ver} — установим GPU-версию PyTorch")
    elif shutil.which("nvidia-smi"):
        cuda_ver = "12.6"
        warn(f"GPU найден, но версия CUDA не определена — используем CUDA {cuda_ver}")
    else:
        warn("NVIDIA GPU не найден — установим CPU-версию PyTorch (медленнее, но работает)")

    return cuda_ver


# ─────────────────────────────────────────────────────────────
# ШАГ 4 — Установить PyTorch
# ─────────────────────────────────────────────────────────────
def step_install_torch(cuda_ver):
    head("ШАГ 4 / 6  — Установка PyTorch + TorchAudio")
    sep()

    cuda_tag  = cuda_tag_from_ver(cuda_ver)
    index_url = f"https://download.pytorch.org/whl/{cuda_tag}" if cuda_tag else None

    # Проверить, уже установлен ли torch в venv
    found, ver = check_import_in_venv("torch")
    found2, _  = check_import_in_venv("torchaudio")

    if found:
        is_cpu_only = "+cpu" in ver
        if is_cpu_only and cuda_tag:
            warn(f"Установлен CPU-only torch v{ver}, но GPU доступен — переустанавливаю с CUDA...")
        elif found2:
            ok(f"PyTorch v{ver} уже установлен в venv")
            ok("TorchAudio уже установлен в venv")
            return
        else:
            ok(f"PyTorch v{ver} уже установлен — устанавливаю torchaudio...")

    if index_url:
        info(f"Index URL: {index_url}")
        info("Установка torch + torchaudio (GPU)... [5–15 минут, зависит от скорости]")
        cmd = [VENV_PYTHON, "-m", "pip", "install",
               "torch", "torchaudio",
               "--index-url", index_url, "--quiet"]
    else:
        info("Установка torch + torchaudio (CPU)... [3–8 минут]")
        cmd = [VENV_PYTHON, "-m", "pip", "install",
               "torch", "torchaudio", "--quiet"]

    result = subprocess.run(cmd, text=True)
    if result.returncode == 0:
        _, new_ver = check_import_in_venv("torch")
        ok(f"PyTorch установлен  (v{new_ver})")
    else:
        err("Установка PyTorch не удалась!")
        err(f"Попробуй вручную в venv:\n  {VENV_PIP} install torch torchaudio")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# ШАГ 5 — Установить WhisperX и зависимости
# ─────────────────────────────────────────────────────────────
def step_install_whisperx():
    head("ШАГ 5 / 6  — Установка WhisperX + зависимостей")
    sep()

    v = sys.version_info
    needs_ignore_python = (v.major == 3 and v.minor >= 14)

    packages = [
        ("whisperx",       "whisperx",        "WhisperX"),
        ("numpy",          "numpy",            "NumPy"),
        ("librosa",        "librosa",          "Librosa"),
        ("ctranslate2",    "ctranslate2",      "CTranslate2"),
        ("faster_whisper", "faster-whisper",   "Faster-Whisper"),
    ]

    for module, pkg, label in packages:
        found, ver = check_import_in_venv(module)
        if found:
            ok(f"{label:<20} уже установлен  (v{ver})")
            continue

        info(f"Установка {label}...")
        cmd = [VENV_PYTHON, "-m", "pip", "install", pkg, "--quiet"]
        if needs_ignore_python:
            cmd.append("--ignore-requires-python")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            found2, ver2 = check_import_in_venv(module)
            ok(f"{label:<20} установлен" + (f"  (v{ver2})" if found2 else ""))
        else:
            if "whisperx" in pkg.lower():
                warn("PyPI не сработал — пробуем GitHub...")
                cmd2 = [VENV_PYTHON, "-m", "pip", "install",
                        "git+https://github.com/m-bain/whisperX.git", "--quiet"]
                if needs_ignore_python:
                    cmd2.append("--ignore-requires-python")
                r2 = subprocess.run(cmd2, text=True)
                if r2.returncode == 0:
                    ok(f"{label:<20} установлен с GitHub")
                else:
                    err(f"{label} — установка НЕУДАЧНА!")
                    err(f"Вручную: {VENV_PIP} install git+https://github.com/m-bain/whisperX.git")
            else:
                err(f"{label} — НЕУДАЧА. Вручную: {VENV_PIP} install {pkg}")


# ─────────────────────────────────────────────────────────────
# ШАГ 6 — Проверить FFmpeg + итоговая проверка
# ─────────────────────────────────────────────────────────────
def step_final():
    head("ШАГ 6 / 6  — Проверка FFmpeg и итоговый тест")
    sep()

    # FFmpeg
    if ffmpeg_found():
        try:
            r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
            ver_line = r.stdout.splitlines()[0][:60] if r.stdout else "ok"
            ok(f"FFmpeg: {ver_line}")
        except Exception:
            ok("FFmpeg найден в PATH")
    else:
        err("FFmpeg НЕ найден в PATH!")
        print()
        if sys.platform == "win32":
            info("Windows — установи FFmpeg:")
            print(f"    {C_BOLD}winget install ffmpeg{C_RESET}   (рекомендуется)")
            print(f"    или скачай: {C_BLUE}https://www.gyan.dev/ffmpeg/builds/{C_RESET}")
            print(f"    Добавь C:\\ffmpeg\\bin в PATH и перезапусти терминал.")

            if shutil.which("winget"):
                ans = input(f"\n  {C_YELLOW}Установить FFmpeg через winget сейчас? [y/N]: {C_RESET}").strip().lower()
                if ans == "y":
                    r = subprocess.run(["winget", "install", "ffmpeg"], text=True)
                    if r.returncode == 0 and ffmpeg_found():
                        ok("FFmpeg установлен!")
                    else:
                        warn("Перезапусти терминал и запусти LipSync снова.")

    # Итоговая проверка пакетов
    print()
    all_good = True
    checks = [
        ("torch",        "PyTorch"),
        ("torchaudio",   "TorchAudio"),
        ("whisperx",     "WhisperX"),
        ("numpy",        "NumPy"),
        ("librosa",      "Librosa"),
        ("ctranslate2",  "CTranslate2"),
        ("faster_whisper","Faster-Whisper"),
    ]

    for module, label in checks:
        found, ver = check_import_in_venv(module)
        if found:
            ok(f"{label:<20} v{ver}")
        else:
            err(f"{label:<20} ОТСУТСТВУЕТ!")
            all_good = False

    # CUDA проверка
    print()
    try:
        r = subprocess.run(
            [VENV_PYTHON, "-c", "import torch; print(torch.cuda.is_available())"],
            capture_output=True, text=True, timeout=30
        )
        if r.stdout.strip() == "True":
            ok("CUDA (GPU)  — доступна! Быстрый режим включён.")
        else:
            warn("CUDA не доступна — работаем на CPU (медленнее, но работает)")
    except Exception:
        warn("Не удалось проверить CUDA")

    print()
    if all_good:
        print(f"{C_BOLD}{C_GREEN}  [OK] ВСЕ ЗАВИСИМОСТИ УСТАНОВЛЕНЫ УСПЕШНО!{C_RESET}")
        print(f"\n  {C_CYAN}Теперь запусти:{C_RESET}")
        print(f"    {C_BOLD}run_lipsync.bat{C_RESET}")
        print(f"\n  Или напрямую через Python:")
        print(f"    {C_BOLD}{VENV_PYTHON} lipsync_v5_1.py{C_RESET}")
    else:
        print(f"{C_BOLD}{C_RED}  [X] ЧАСТЬ ПАКЕТОВ НЕ УСТАНОВЛЕНА — смотри ошибки выше{C_RESET}")
        print(f"\n  Попробуй запустить установщик снова.")

    return all_good


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    print_banner()

    print(f"  {C_DIM}Устанавливает зависимости для Auto LipSync v5.1{C_RESET}")
    print(f"  {C_DIM}в локальный venv (НЕ трогает системный Python).{C_RESET}")
    print()
    print(f"  {C_YELLOW}Размер загрузки: 2–8 GB (зависит от GPU).{C_RESET}")
    print(f"  {C_YELLOW}Нужно стабильное интернет-соединение.{C_RESET}")
    print(f"  {C_DIM}Папка установки: {VENV_DIR}{C_RESET}")
    print()

    ans = input(f"  {C_CYAN}Начать установку? [Y/n]: {C_RESET}").strip().lower()
    if ans == "n":
        print("  Отмена.")
        sys.exit(0)

    t_start = time.time()

    step_check_python()
    step_create_venv()
    cuda_ver = step_detect_gpu()
    step_install_torch(cuda_ver)
    step_install_whisperx()
    all_ok = step_final()

    elapsed = time.time() - t_start
    print()
    print(f"{C_DIM}  Общее время: {elapsed/60:.1f} мин{C_RESET}")
    print()

    if sys.platform == "win32":
        input("  Нажми Enter для закрытия...")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
