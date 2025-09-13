# EQiLevel PoC - Pipelines and Tests

This Proof-of-Concept demonstrates audio transcription, emotion analysis, and a Q-learning agent with concise unit tests and console feedback.

---

## Table of Contents

- [Setup](#setup)
- [Audio Transcription](#audio-transcription)
- [Emotion Analysis](#emotion-analysis)
- [Q-Learning Agent](#q-learning-agent)
- [Tests](#tests)
- [Next Steps](#next-steps)

---

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # PowerShell
pip install -r requirements.txt

# .env
echo OPENAI_API_KEY=sk-...> .env
```

Requirements
- Python 3.10+
- FFmpeg in PATH
- CUDA (optional) for Whisper and Torch GPU acceleration

---

## Audio Transcription

- Script: `src/audio/transcribe_to_json.py`
- Uses FFmpeg + Whisper; auto-detects GPU
- Transcribes `.wav`, `.mp3`, `.m4a` to JSON with timestamps

Usage

```bash
python src/audio/transcribe_to_json.py samples/your_audio.wav
```

---

## Emotion Analysis

- Script: `src/nlp/emotion_prompt.py`
- Reads transcript JSON, prompts GPT, strips fences, parses JSON
- Logs each step and prints a summary

Usage

```bash
python src/nlp/emotion_prompt.py transcripts/your_audio_transcript.json
```

---

## Q-Learning Agent

- Module: `src/rl/q_learning_agent.py`
- Implements:
  - epsilon-greedy action selection
  - temporal-difference (TD) update
  - structured logging for init/state/action/updates
  - save/load of Q-table

---

## Tests

Emotion module
- File: `tests/test_emotion_prompt.py`
- Validates transcript loading, prompt, JSON parsing, output saving

Q-learning agent
- File: `tests/test_q_learning_agent.py`
- Covers state init, explore/exploit, TD updates, save/load

Run all tests

```bash
pytest -q
```

---

## Next Steps

- Integrate pipelines into CLI/UI
- Incorporate emotional feedback into reward shaping
- Frontend for student interaction
- Prep deployment & user study

---

OpenAI acknowledgement: drafted with assistance from ChatGPT (2025).

