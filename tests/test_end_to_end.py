# tests/test_end_to_end.py
"""
End-to-end test for EQiLevel pipeline:
- Starts a session
- Sends a text turn
- Sends an audio turn (if sample audio exists)
- Checks for expected keys in responses
- Prints PASS/FAIL for each step
"""
import requests
import os
import json

API = "http://127.0.0.1:8000"
SAMPLE_AUDIO = os.path.join("samples", "easy.m4a")


def print_result(name, cond, detail=None):
    if cond:
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name}" + (f": {detail}" if detail else ""))


def test_end_to_end():
    # 1. Start session
    try:
        r = requests.post(f"{API}/session/start", timeout=10)
        r.raise_for_status()
        sid = r.json()["session_id"]
        print_result("Session start", True)
    except Exception as e:
        print_result("Session start", False, e)
        return

    # 2. Send text turn
    try:
        payload = {"session_id": sid, "user_text": "I solved it!"}
        r = requests.post(f"{API}/session", json=payload, timeout=20)
        r.raise_for_status()
        data = r.json()
        cond = "text" in data and "mcp" in data and "reward" in data
        print_result("Text turn", cond, data)
    except Exception as e:
        print_result("Text turn", False, e)

    # 3. Send audio turn (if sample audio exists)
    if os.path.exists(SAMPLE_AUDIO):
        try:
            import soundfile as sf
            import numpy as np
            import tempfile
            # Convert m4a to wav if needed (Gradio expects wav)
            # For this test, just send the m4a as is
            with open(SAMPLE_AUDIO, "rb") as f:
                files = {"file": ("easy.m4a", f, "audio/mp4")}
                data = {"session_id": str(sid), "user_text": ""}
                r = requests.post(f"{API}/session", files=files, data=data, timeout=60)
            r.raise_for_status()
            data = r.json()
            cond = "text" in data and "mcp" in data and "reward" in data
            print_result("Audio turn", cond, data)
        except Exception as e:
            print_result("Audio turn", False, e)
    else:
        print("[SKIP] Audio turn: sample audio not found.")

if __name__ == "__main__":
    test_end_to_end()
