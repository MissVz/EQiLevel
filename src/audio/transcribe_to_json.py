"""
EQiLevel: Whisper transcription helper
 - Uses GPU if available
 - Writes a structured JSON next to the audio file (in output_dir)
 - Optional language hint forwarded to Whisper
"""

import argparse
import json
import os
from datetime import datetime

import torch
import whisper


def detect_device() -> str:
    if torch.cuda.is_available():
        print("GPU detected - using CUDA")
        return "cuda"
    print("No GPU found - using CPU")
    return "cpu"


def transcribe_audio(audio_path: str, model_size: str = "base", output_dir: str = "transcripts", language: str | None = None) -> str:
    device = detect_device()
    model = whisper.load_model(model_size, device=device)

    print(f"Transcribing: {audio_path}")
    if language:
        result = model.transcribe(audio_path, language=language)
    else:
        result = model.transcribe(audio_path)

    output = {
        "timestamp": datetime.now().isoformat(),
        "audio_file": os.path.basename(audio_path),
        "language": result.get("language", "unknown"),
        "text": result.get("text", ""),
        "segments": result.get("segments", []),
    }

    os.makedirs(output_dir, exist_ok=True)
    json_filename = os.path.splitext(os.path.basename(audio_path))[0] + "_transcript.json"
    output_path = os.path.join(output_dir, json_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Transcript saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EQiLevel Whisper Transcriber")
    parser.add_argument("audio_path", help="Path to the input audio file")
    parser.add_argument("--model", default="base", help="Whisper model size: tiny, base, small, medium, large")
    parser.add_argument("--language", default=None, help="Optional language hint (e.g., en, es)")
    args = parser.parse_args()

    transcribe_audio(args.audio_path, model_size=args.model, language=args.language)

