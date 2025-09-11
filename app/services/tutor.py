# app/services/tutor.py
import os
from openai import OpenAI
import json as _json
from app.models import MCP  # Pydantic model
from app.services.storage import get_system_prompt
from app.services.objectives import format_for_prompt

SYSTEM_TMPL = """You are an emotionally-aware tutor.
- Tone: {tone}
- Pacing: {pacing}
- Difficulty: {difficulty}
- Style: {style}
- Next Step: {next_step}

Rules for this turn:
- End with exactly one question for the learner when appropriate.
- Use at most one question mark (?) in the entire reply.
- If you need to offer choices, present them as bullets, then ask ONE concise question that invites a single response.
- Keep it clear and supportive (about 3–5 sentences total).
"""

def _compose_text_from_json(j: dict) -> str:
    support = str(j.get("support", "")).strip()
    question = str(j.get("question", "")).strip()
    # sanitizer: ensure at most one question mark and concise question
    if question:
        if question.count("?") >= 1:
            # keep content up to first '?'
            idx = question.find("?")
            question = question[: idx + 1]
        else:
            # if author forgot '?', append one for clarity (optional)
            question = question.rstrip(".") + "?"
    if support and question:
        return f"{support} {question}".strip()
    return (support or question or "").strip()


def generate(user_text: str, mcp: MCP, history: list[dict] | None = None, objectives: list[dict] | None = None) -> str:
    """Return a non-empty tutor reply; never None."""
    try:
        # Load DB override (if any); fall back to code template
        tmpl = get_system_prompt() or SYSTEM_TMPL
        try:
            system = tmpl.format(**mcp.model_dump())
        except Exception:
            # If formatting fails due to placeholders, use as-is
            system = tmpl
        if objectives:
            system += "\n" + format_for_prompt(objectives)

        # New OpenAI SDK (v1.x) usage
        client = OpenAI()  # reads OPENAI_API_KEY from env

        # Prefer JSON envelope for predictable rendering
        messages = [
            {"role": "system", "content": system + "\nReturn JSON with keys: support (string, optional), question (string, required), next_step (one of: explain, example, prompt, quiz, review)."},
        ]
        # include recent dialogue to preserve short-term memory
        if history:
            # Clamp to a reasonable window so we don't blow the context
            for m in history[-16:]:
                if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
                    content = str(m.get("content", ""))[:1200]
                    if content:
                        messages.append({"role": m["role"], "content": content})
        # Current user turn last
        messages.append({"role": "user", "content": user_text})

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            max_tokens=260,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or ""
        try:
            j = _json.loads(content)
            txt = _compose_text_from_json(j)
            if txt:
                return txt
        except Exception:
            pass
        # Fallback: plain text generation
        resp2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                *([m for m in (history or []) if m.get("role") in ("user","assistant")] if history else []),
                {"role": "user", "content": user_text}
            ],
            temperature=0.3,
            max_tokens=220,
        )
        text = resp2.choices[0].message.content or ""
        return text.strip() or "[Tutor] Let’s try a smaller step together."
    except Exception as e:
        # Log and return fallback so DB insert never breaks
        print(f"[tutor.generate] ERROR: {e}")
        return "[Tutor] I hit a snag generating a reply. Try a smaller step: combine like terms on one side, then simplify."
