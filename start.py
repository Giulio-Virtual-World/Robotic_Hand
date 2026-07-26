'''

Author: Giulio Segre
Last modified date: 26-07-2026
www.giulio-virtual-world.com

________________________________

Questo script avvia il programa principale "core.py" in un ambiente virtuale

'''

from pathlib import Path
import subprocess

script_dir = Path(__file__).parent

python_venv = script_dir / "venv" / "Scripts" / "python.exe"

subprocess.Popen(
    ["cmd", "/k", str(python_venv), "core.py"],
    cwd=script_dir
)
