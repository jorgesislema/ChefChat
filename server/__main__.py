"""Arranque local:  python -m server   ->  http://127.0.0.1:8765"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("server.app:app", host="127.0.0.1", port=int(os.environ.get("CHEFCHAT_PORT", "8765")))
