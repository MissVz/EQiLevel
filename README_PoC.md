# EQiLevel Capstone Project

## 📖 Project Overview
EQiLevel is an adaptive learning platform combining speech-based interaction and reinforcement learning to dynamically tailor question difficulty based on student performance and emotional cues.

### Key Components
1. **Audio Transcription (Whisper + CUDA)**
2. **Emotion Analysis (GPT-4o prompting)**
3. **Adaptive Q-Learning Agent**
4. **Comprehensive Unit Tests with Console Feedback**

---

## ⚙️ Setup & Installation
1. **Clone the repository**
   ```bash
   git clone <repo_url>
   cd EQiLevel
   ```
2. **Create & activate virtual environment**
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate    # PowerShell
   ```
3. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```
4. **Configure environment variables**
   - Create a `.env` file at project root:
     ```ini
     OPENAI_API_KEY=sk-your_actual_key_here
     ```

---

## 🎙️ Audio Transcription Pipeline
- **Script**: `src/audio/transcribe_to_json.py`
- Uses FFmpeg + Whisper (GPU auto-detect)
- Transcribes `.wav`, `.mp3`, `.m4a` to JSON with timestamps

**Usage:**
```bash
python src/audio/transcribe_to_json.py samples/your_audio.wav
```

---

## 🎭 Emotion Analysis Pipeline
- **Script**: `src/nlp/emotion_prompt.py`
- Reads transcript JSON, prompts GPT-4o, strips fences, parses JSON
- Logs each step and prints a summary

**Usage:**
```bash
python src/nlp/emotion_prompt.py transcripts/your_audio_transcript.json
```

---

## 🤖 Q-Learning Agent
- **Module**: `src/rl/q_learning_agent.py`
- Implements:
  - ε-greedy action selection
  - Temporal-Difference (TD) update rule
  - Console logs for init, state creation, action, and updates
  - Save/load persistence

---

## 🧪 Testing Strategy
### Emotion Module Tests
- **File**: `tests/test_emotion_prompt.py`
- Validates transcript loading, prompt creation, JSON parsing, output saving, with pass/fail prints

### Q-Learning Agent Tests
- **File**: `tests/test_q_learning_agent.py`
- Covers state init, explore/exploit, TD updates, save/load, with detailed console feedback

**Run all tests:**
```bash
pytest -q
```

---

## 📜 Requirements
- Python 3.10+
- CUDA Toolkit 12.1 & drivers
- FFmpeg in PATH
- Dependencies in `requirements.txt` (update via `pip freeze > requirements.txt`)

---

## 🚀 Next Steps
- Integrate pipelines into a CLI/web interface
- Enhance reward function with emotional feedback
- Develop front-end for student interaction
- Prepare Sprint 05: deployment & user study

---

*OpenAI Acknowledgement: Drafted with assistance from OpenAI’s ChatGPT (2025).*