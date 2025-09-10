"""
Deprecated GUI.

The previous GUI had reliability issues with audio collection
and has been removed. Use the FastAPI endpoints directly instead:

- POST /session/start         -> get a session id
- POST /session               -> send text or (multipart) audio + text
- POST /transcribe            -> transcribe an uploaded audio file

Quick examples:

  python - << 'PY'
import requests
API = "http://127.0.0.1:8000"
sid = requests.post(f"{API}/session/start").json()["session_id"]
resp = requests.post(f"{API}/session", json={"session_id": sid, "user_text": "Hello!"}).json()
print(resp)
PY
"""

import sys
if __name__ == "__main__":
    sys.exit("Gradio UI removed. Use the API endpoints instead.")
