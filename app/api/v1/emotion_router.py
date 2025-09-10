# app/api/v1/emotion_router.py
from fastapi import APIRouter, UploadFile, File
from app.services import emotion
import tempfile, os

router = APIRouter(prefix="/emotion", tags=["emotion"])

@router.post("/detect_audio")
async def detect_audio_emotion(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        emotion_label, scores = emotion.detect_audio_emotion(tmp_path)
        return {"emotion": emotion_label, "scores": scores}
    finally:
        os.remove(tmp_path)

@router.post("/detect_text")
async def detect_text_emotion(text: str):
    em = emotion.classify(text)
    return {"emotion": em.label, "sentiment": em.sentiment}
