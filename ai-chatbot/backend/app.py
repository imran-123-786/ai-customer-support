from __future__ import annotations

import runpy
from pathlib import Path


HERE = Path(__file__).resolve().parent
TARGET = HERE / "streamlit_app.py"

if not TARGET.exists():
    raise FileNotFoundError(f"Could not find Streamlit app at: {TARGET}")

runpy.run_path(str(TARGET), run_name="__main__")
