# AI687 HOS04B – EQiLevel: Emotion Prompting via GPT-4o (v1.0+)
# Purpose: Send Whisper transcripts to GPT-4o and extract emotional tone
# Theme: Robotics tutor reading the room 🤖📚
# -------------------------------------------------------------

import os
import json
import argparse
import re
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env
load_dotenv()

# Initialize OpenAI client with API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_transcript(transcript_path: str) -> dict:
    """
    Load a Whisper transcript JSON file.
    Returns:
        dict: Parsed transcript data
    """
    with open(transcript_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(transcript_text: str) -> str:
    """
    Build a user-facing prompt for GPT-4o to analyze emotion.
    """
    return (
        "You are an emotion-aware AI tutor. Analyze the following student response "
        "and determine their overall emotional tone and reasoning behind it. Respond with raw JSON only, no markdown fences.\n\n"
        f"Transcript:\n\"{transcript_text}\"\n\n"
        "JSON format:\n"
        "{ \"emotion\": \"<emotion>\", \"confidence\": 0.00, \"explanation\": \"...\" }"
    )


def analyze_emotion(transcript_data: dict) -> dict:
    """
    Send the transcript text to GPT-4o and parse the JSON response.
    Returns:
        dict: Combined transcript and emotion analysis
    """
    prompt = build_prompt(transcript_data.get("text", ""))

    print("🧠 Sending to GPT-4o...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    # Extract content
    message = response.choices[0].message
    raw = message.content if hasattr(message, 'content') else message['content']

    # Remove markdown fences if present
    raw_clean = raw.strip()
    raw_clean = re.sub(r"^```[\w]*", "", raw_clean)
    raw_clean = re.sub(r"```$", "", raw_clean).strip()

    # Extract JSON object
    match = re.search(r"\{.*\}", raw_clean, re.DOTALL)
    json_str = match.group(0) if match else raw_clean

    # Parse JSON
    try:
        emotion_json = json.loads(json_str)
    except json.JSONDecodeError:
        emotion_json = {
            "emotion": "unknown",
            "confidence": 0.0,
            "explanation": "Could not parse JSON from GPT-4o. Raw response:\n" + raw_clean
        }

    return {
        "timestamp": datetime.now().isoformat(),
        "input_file": transcript_data.get("audio_file", ""),
        "transcript": transcript_data.get("text", ""),
        "emotion_analysis": emotion_json
    }


def save_output(data: dict, out_path: str = "outputs/emotion_results.json"):  
    """
    Save the emotion analysis result to a JSON file.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Emotion analysis saved to: {out_path}")
    # Print a concise summary for quick feedback
    emo = data.get("emotion_analysis", {})
    print(f"🔔 Summary → Emotion: {emo.get('emotion', 'N/A')}, Confidence: {emo.get('confidence', 0):.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EQiLevel Emotion Analyzer (v1.0+ OpenAI)")
    parser.add_argument(
        "transcript_path", help="Path to Whisper transcript JSON file"
    )
    parser.add_argument(
        "--output", default="outputs/emotion_results.json",
        help="Path to save emotion result JSON"
    )
    args = parser.parse_args()

    data = load_transcript(args.transcript_path)
    result = analyze_emotion(data)
    save_output(result, args.output)

# -------------------------------------------------------------
# REFERENCE:
# OpenAI. (2025). ChatGPT’s assistance with emotion-aware prompting [Large language model]. https://openai.com/chatgpt
