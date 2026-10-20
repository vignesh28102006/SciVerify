#!/usr/bin/env python3
"""
SciVerify Unified Launcher
Launches the FastAPI NLP Backend and Vite React Frontend.

Usage:
    python run.py             # Launches both Backend & Frontend simultaneously
    python run.py backend     # Launches only the FastAPI Backend
    python run.py frontend    # Launches only the Vite Frontend
"""

import os
import sys
import subprocess
import time

def find_project_dirs():
    current = os.path.dirname(os.path.abspath(__file__))
    # Case 1: current directory is the project root containing backend/ and src/
    if os.path.isdir(os.path.join(current, "backend")) and os.path.isdir(os.path.join(current, "src")):
        return current, os.path.join(current, "backend")
    # Case 2: nested under SciVerify-main
    nested = os.path.join(current, "SciVerify-main")
    if os.path.isdir(nested) and os.path.isdir(os.path.join(nested, "backend")):
        return nested, os.path.join(nested, "backend")
    return current, os.path.join(current, "backend")

def main():
    root_dir, backend_dir = find_project_dirs()
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    print("=" * 68)
    print("      SCIVERIFY - BIOMEDICAL SCIENTIFIC CLAIM VERIFICATION INSTRUMENT     ")
    print("=" * 68)
    print(f"[*] Project Root : {root_dir}")
    print(f"[*] Backend Dir  : {backend_dir}")
    print(f"[*] Mode         : {mode.upper()}")
    print("=" * 68)

    processes = []

    try:
        # Start Backend (FastAPI on Port 8001)
        if mode in ("all", "backend"):
            print("\n[>>] Starting FastAPI NLP Backend Server on http://localhost:8001 ...")
            backend_cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
            p_backend = subprocess.Popen(
                backend_cmd,
                cwd=backend_dir,
                shell=(os.name == "nt")
            )
            processes.append(("Backend", p_backend))

        # Start Frontend (Vite on Port 5173)
        if mode in ("all", "frontend"):
            print("[>>] Starting Vite React Frontend Server on http://localhost:5173 ...")
            npm_cmd = "npm run dev"
            p_frontend = subprocess.Popen(
                npm_cmd,
                cwd=root_dir,
                shell=True
            )
            processes.append(("Frontend", p_frontend))

        print("\n" + "=" * 68)
        print("  APPLICATION ACTIVE & READY FOR EVALUATION")
        print("  - Frontend UI    : http://localhost:5173")
        print("  - Backend API   : http://localhost:8001")
        print("  - Swagger Docs  : http://localhost:8001/docs")
        print("  Press Ctrl+C to terminate all services safely.")
        print("=" * 68 + "\n")

        # Keep alive and monitor child processes
        while True:
            time.sleep(1)
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"[!] {name} process terminated with exit code {proc.returncode}.")
                    return

    except KeyboardInterrupt:
        print("\n[*] Shutting down SciVerify services...")
    finally:
        for name, proc in processes:
            try:
                proc.terminate()
            except Exception:
                pass
        print("[*] All services stopped.")

if __name__ == "__main__":
    main()
