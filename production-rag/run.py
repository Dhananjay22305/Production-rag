import sys
import os
import uvicorn

# Force Python to recognize the current directory as root
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=True)