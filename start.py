import subprocess
import os
import sys
import time
import signal


def run_services():
    """
    Launch both FastAPI backend and Next.js frontend concurrently.
    """
    root_dir = os.path.dirname(os.path.abspath(__file__))
    ui_dir = os.path.join(root_dir, "ui")

    print("🚀 Starting Investment-X Unified Server...")

    # 1. Start FastAPI Backend
    print("📦 Starting FastAPI Backend on http://localhost:8000")
    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "ix.api.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        cwd=root_dir,
    )

    # 2. Wait a moment for backend to initialize
    time.sleep(2)

    # 3. Start Next.js Frontend
    print("🎨 Starting Next.js Frontend on http://localhost:3000")
    # Use shell=True for npm/npx on Windows
    frontend = subprocess.Popen(["npm", "run", "dev"], cwd=ui_dir, shell=True)

    print("\n✅ Both services are running!")
    print("👉 View Dashboard: http://localhost:3000")
    print("👉 API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop both services.\n")

    try:
        # Keep the script running
        while True:
            time.sleep(1)
            # Check if either process failed
            if backend.poll() is not None:
                print("❌ Backend stopped unexpectedly.")
                break
            if frontend.poll() is not None:
                print("❌ Frontend stopped unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        # Clean shutdown
        backend.terminate()
        # On Windows, terminate() might not kill the whole npm tree, but it's a start
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(frontend.pid)], capture_output=True
            )
        else:
            frontend.terminate()

        print("👋 Services stopped.")


if __name__ == "__main__":
    run_services()
