# src/cli/interaction.py
# AI687 HOS06A – EQiLevel: CLI Interaction Loop
# Purpose: Tie together transcription, emotion analysis, and Q-learning into a conversational REPL
# Theme: AI tutor that listens, analyzes emotion, and adapts difficulty on the fly

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
import sys
from pathlib import Path


# We'll persist our Q-table here.
DATA_DIR = Path(__file__).parents[2] / "data" # Ensure data folder exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ensure project root is on PYTHONPATH so "src.*" imports work
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

# Load Whisper transcription
from src.audio.transcribe_to_json import transcribe_audio
# Emotion prompt utilities
from src.nlp.emotion_prompt import load_transcript, analyze_emotion, save_output as save_emotion
# Q-learning agent
from src.rl.q_learning_agent import QLearningAgent

# Initialize environment
load_dotenv()

def main(audio_dir: str, transcripts_dir: str, emotion_out_dir: str, qtable_path: str):
    # Setup directories
    os.makedirs(transcripts_dir, exist_ok=True)
    os.makedirs(emotion_out_dir, exist_ok=True)

    # Initialize or load agent
    if os.path.exists(qtable_path):
        agent = QLearningAgent.load(
            qtable_path,
            state_space_size=5,
            action_space_size=3
        )
    else:
        agent = QLearningAgent(
            state_space_size=5,
            action_space_size=3,
            alpha=0.2, gamma=0.99, epsilon=0.1
        )

    print("🤖 Welcome to EQiLevel CLI! Type 'exit' to quit.")

    while True:
        # 1. Record or provide audio
        audio_input = input("🎙️  Enter path to audio file: ").strip()
        if audio_input.lower() in ("exit", "quit"):
            break
        audio_path = Path(audio_input)
        if not audio_path.exists():
            print(f"⚠️  Audio file not found: {audio_input}")
            continue

        # 2. Transcribe
        print("🔄 Transcribing audio...")
        try:
            transcribe_audio(str(audio_path), output_dir=transcripts_dir)
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            continue

        # Derive transcript path
        transcript_file = Path(transcripts_dir) / f"{audio_path.stem}_transcript.json"

        # 3. Emotion analysis
        print("🔄 Analyzing emotion...")
        try:
            transcript_data = load_transcript(str(transcript_file))
            emo_result = analyze_emotion(transcript_data)
            save_emotion(emo_result, str(Path(emotion_out_dir) / f"{audio_path.stem}_emotion.json"))
        except Exception as e:
            print(f"❌ Emotion analysis error: {e}")
            continue

        # 4. Q-Learning decision
        state = emo_result.get("emotion_analysis", {}).get("emotion", "unknown")
        print(f"🎯 Mapping emotion '{state}' to learner state...")
        action = agent.choose_action(state)
        print(f"🔢 Next question difficulty level (action): {action}")

        # 5. Simulate reward collection
        try:
            reward = float(input("🏆 Enter reward (e.g., 1 for correct, 0 for wrong): "))
            next_state = input("📊 Enter next state label: ").strip() or state
            done_flag = input("✅ Done? (y/n): ").lower().startswith("y")
            agent.update(state, action, reward, next_state, done_flag)
        except Exception as e:
            print(f"⚠️  Update error: {e}")
            continue

        # 6. Persist Q-table
        # Save Q-table into our data folder so it's versioned alongside code.
        qtable_path = DATA_DIR / "q_table.json"
        try:
            agent.save(str(qtable_path))
        except Exception as e:
            print(f"⚠️ Failed to save Q-table to {qtable_path}: {e}")

        # Blank line for readability between interactions
        print()

    print("👋 Goodbye from EQiLevel CLI!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EQiLevel CLI Interaction Loop")
    parser.add_argument("--audio-dir", default="samples", help="Directory for input audio files")
    parser.add_argument("--transcripts-dir", default="transcripts", help="Directory to save Whisper transcripts")
    parser.add_argument("--emotion-out-dir", default="outputs", help="Directory to save emotion analysis JSON")
    parser.add_argument("--qtable", default="q_table.json", help="Path to Q-table JSON file")
    args = parser.parse_args()
    main(args.audio_dir, args.transcripts_dir, args.emotion_out_dir, args.qtable)

# -------------------------------------------------------------
# OpenAI Acknowledgement:
# This CLI loop was built with assistance from OpenAI’s ChatGPT o4-mini-high (2025) [Large Language Model].
