from app import app
import platform
import os

# This file imports the FastAPI app instance from app.py
# and exposes it for use with uvicorn.
# To run the application:
# uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

if __name__ == "__main__":
    import uvicorn
    
    # Check if running on Windows
    is_windows = platform.system() == "Windows"
    
    # On Windows, only use a single worker as Windows doesn't support
    # socket sharing between processes in the same way as Unix
    workers = 1 if is_windows else int(os.getenv("WORKERS", "2"))
    
    # This allows you to run the application directly with python main.py
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=workers
    )