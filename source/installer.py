"""
Copyright (c) 2026 GVW - Questo file è protetto dalla licenza AGPL-3.0.

Author: Giulio Segre
Last modified date: 27-07-2026
www.giulio-virtual-world.com

Questo script crea un ambiente virtuale, installa le librerie necessarie
per il programma principale "core.py" e verifica che MediaPipe sia installato.

"""

from pathlib import Path
import subprocess

script_dir = Path(__file__).parent

# Crea il virtual environment
subprocess.run(
    ["python", "-m", "venv", "venv"],
    cwd=script_dir,
    check=True
)

python_venv = script_dir / "venv" / "Scripts" / "python.exe"

# Installa i pacchetti
subprocess.run(
    [str(python_venv), "-m", "pip", "install", "mediapipe", "opencv-python", "numpy"],
    check=True
)

# Verifica installazione
subprocess.run(
    [str(python_venv), "-m", "pip", "show", "mediapipe"],
    check=True
)
