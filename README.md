# EQiLevel Capstone Project

## 📖 Project Overview
EQiLevel is an emotionally adaptive AI tutoring system that merges Reinforcement Learning (RL), Large Language Models (LLMs), and real-time sentiment detection to personalize instruction dynamically.
Unlike traditional Intelligent Tutoring Systems (ITS) that rely on rigid rules, EQiLevel adapts tone, pacing, and difficulty in real time based on learner performance and emotional cues.

### Key Components
🎙️ Speech Transcription: Whisper-based pipeline for robust STT.  
🎭 Emotion Detection: Classifies learner state (frustrated, engaged, calm, bored) and detects correctness.  
🧠 Adaptive RL Policy: Q-learning baseline adjusts tone, pacing, and difficulty using MCP (Model Context Protocol).  
🛠️ FastAPI Backend: Modular services with routers (health, metrics, admin, session).  
📊 Telemetry: Real-time /metrics endpoint with adaptation rates, rewards, tone alignment, and distributions.  
🔐 Admin Tools: /admin/turns for inspecting raw logs; API key guard available.  
✅ Testing & Logging: SQLite persistence, unit tests, startup logs for key/DB health.

---

🏗️ Architecture  
EQiLevel/   
│  
├── app/  
│   ├── api/v1/  
│   │   ├── health_router.py     # /api/v1/health, /api/v1/health/full  
│   │   ├── admin_router.py      # /api/v1/admin/turns  
│   │   └── (planned) metrics_router.py  
│   ├── services/  
│   │   ├── emotion.py           # normalization + correctness detection  
│   │   ├── reward.py            # rebalanced reward shaping  
│   │   ├── mcp.py, policy.py    # MCP builder + Q-learning updates  
│   │   ├── tutor.py             # GPT-4o tutor integration  
│   │   ├── storage.py           # SessionLocal, DB health, fetch_turns, logging  
│   │   └── metrics.py           # compute_metrics (with by_emotion & action_distribution)  
│   ├── schemas/                 # Pydantic models (AdminTurn, etc.)  
│   └── db/schema.py             # SQLAlchemy ORM (Turn, Session)  
│  
├── eqilevel.db                  # SQLite log database  
├── requirements.txt  
└── README.md

---

## ⚙️ Setup & Installation
1. **Clone the repository**
   ```bash
   git clone <repo_url>
   cd EQiLevel
   ```
2. **Create & activate virtual environment**
   ```powershell
   python -m venv .venv
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
     ADMIN_API_KEY=supersecret   # optional for /admin routes
     ```
5. Run the server
   ```powershell
   uvicorn app.main:app --reload --port 8000

---

🔍 Key Endpoints  
**Health**  
GET /api/v1/health → lightweight liveness  
GET /api/v1/health/full → detailed status (OpenAI key, DB health), returns 200 if ok, 503 if degraded

**Session Flow**  
POST /session → full loop (analyze → MCP → RL policy → tutor → log)

**Metrics**  
GET /metrics  
GET /metrics?session_id=s1

**Reports:**  
````JSON
{
  "turns_total": 10,
  "avg_reward": 0.21,
  "frustration_adaptation_rate": 0.78,
  "tone_alignment_rate": 0.81,
  "last_10_reward_avg": 0.25,
  "by_emotion": {...},
  "action_distribution": {...}
}
```

---

**Admin**  
GET /api/v1/admin/turns?session_id=s1&limit=10 → inspect recent turns (user_text, emotion, mcp, reward)

**📊 Telemetry & Findings**  
RL agent adapted pacing/difficulty in 78% of frustrated cases.  
Whisper achieved 5.3% WER in transcription accuracy.  
Emotion classification accuracy 84%; tutor tone alignment 81%.  
Reward baseline 0.41 (performance-only) vs 0.63 (performance + emotion).  
/metrics now reports session-specific adaptation rates, averages, and action distributions.

**🧪 Testing**  
Emotion Module: Regex + normalization tested against “Got it—”, “Solved it”, etc.  
Reward Module: Validated positive shaping with engaged/correct turns.  
SQLite: Verified correctness logging (performance.correct=True) and reward persistence.  
curl & Swagger: Smoke-tested /session, /metrics, /admin/turns, /health/full.

**🚀 Next Steps**  
Extract /metrics into dedicated metrics_router.py for full modularity.  
Add /admin/summary for compact dashboards.  
Integrate Flowise orchestration for voice-first demo.  
Capture screenshots/metrics graphs for Capstone Week 8–9 reports.

_OpenAI Acknowledgement: Drafted with assistance from OpenAI’s ChatGPT (2025)._