# app/services/tutor.py
import os
from openai import OpenAI
from app.models import MCP  # Pydantic model

SYSTEM_TMPL = """You are an emotionally-aware tutor.
- Tone: {tone}
- Pacing: {pacing}
- Difficulty: {difficulty}
- Style: {style}
- Next Step: {next_step}
Respond with clear, supportive instruction; keep 3–5 sentences.
"""

def generate(user_text: str, mcp: MCP) -> str:
    """Return a non-empty tutor reply; never None."""
    try:
        system = SYSTEM_TMPL.format(**mcp.model_dump())

        # New OpenAI SDK (v1.x) usage
        client = OpenAI()  # reads OPENAI_API_KEY from env

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_text}
            ],
            temperature=0.3,
            max_tokens=220,
        )
        text = resp.choices[0].message.content or ""
        return text.strip() or "[Tutor] Let’s try a smaller step together."
    except Exception as e:
        # Log and return fallback so DB insert never breaks
        print(f"[tutor.generate] ERROR: {e}")
        return "[Tutor] I hit a snag generating a reply. Try a smaller step: combine like terms on one side, then simplify."