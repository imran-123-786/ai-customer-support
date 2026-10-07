from __future__ import annotations

import runpy
from pathlib import Path
import os
import sys


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "ai-chatbot" / "backend"
TARGET = BACKEND_DIR / "streamlit_app.py"

if not TARGET.exists():
    raise FileNotFoundError(f"Could not find Streamlit app at: {TARGET}")

# Ensure both project root and backend dir are in sys.path
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.chdir(ROOT)
runpy.run_path(str(TARGET), run_name="__main__")
