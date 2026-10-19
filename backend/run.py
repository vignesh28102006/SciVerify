"""
Entrypoint script to launch the SciVerify FastAPI backend server.
Usage:
    python run.py
"""

import uvicorn
import os
import sys

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    print("[STARTING] SciVerify NLP Backend on http://localhost:8001 ...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
