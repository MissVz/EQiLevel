# AI687 HOS04A – EQiLevel: GPU Whisper Transcription Script
# Purpose: Transcribe audio with Whisper using GPU (if available) and output structured JSON
# Theme: Robotics headset-to-classroom interface
# -------------------------------------------------------------

import whisper
import torch
import argparse
import json
import os
from datetime import datetime

def detect_device():
    if torch.cuda.is_available():
        print("🚀 GPU detected — running Whisper with CUDA.")
        return "cuda"
    else:
        print("🐢 No GPU found — defaulting to CPU.")
        return "cpu"

def transcribe_audio(audio_path, model_size="base", output_dir="transcripts"):
    device = detect_device()

    # Load Whisper model
    model = whisper.load_model(model_size, device=device)

    # Run transcription
    print(f"🔍 Transcribing: {audio_path}")
    result = model.transcribe(audio_path)

    # Prepare output structure
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "audio_file": os.path.basename(audio_path),
        "language": result.get("language", "unknown"),
        "text": result["text"],
        "segments": result["segments"]
    }

    # Save to JSON
    os.makedirs(output_dir, exist_ok=True)
    json_filename = os.path.splitext(os.path.basename(audio_path))[0] + "_transcript.json"
    output_path = os.path.join(output_dir, json_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"✅ Transcript saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EQiLevel GPU Whisper Transcriber")
    parser.add_argument("audio_path", help="Path to the input .wav or .mp3 file")
    parser.add_argument("--model", default="base", help="Whisper model size: tiny, base, small, medium, large")
    args = parser.parse_args()

    transcribe_audio(args.audio_path, model_size=args.model)

# -------------------------------------------------------------
# REFERENCE:
# OpenAI. (2025). ChatGPT’s assistance with GPU-based Whisper transcription [Large language model]. https://openai.com/chatgpt
