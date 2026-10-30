import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.app.api.main import app

# Verify app instance is loaded
if __name__ == "__main__":
    print("FastAPI app instance successfully imported for Vercel:", app.title)
