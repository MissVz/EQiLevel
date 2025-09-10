# app/services/emotion.py
import re, unicodedata
from app.models import EmotionSignals, PerformanceSignals
import torch
import torchaudio
# SpeechBrain v1.0 moved EncoderClassifier to speechbrain.inference
try:
    from speechbrain.inference import EncoderClassifier  # >=1.0
except Exception:  # pragma: no cover
    from speechbrain.pretrained import EncoderClassifier  # <1.0 (deprecated)

# Allow multiple variants, case insensitive
_CORRECT_RE = re.compile(r"\b(got\s*it|i\s*solved|solved\s*it|worked)\b", re.I)

NEG_WORDS = {"stuck","confused","lost","hard","difficult","messing up","frustrated"}
POS_WORDS = {"great","got it","clear","easy","makes sense","understand"}

def _normalize(text: str) -> str:
    # Fold Unicode characters (like em dashes, curly quotes) into simpler ASCII
    t = unicodedata.normalize("NFKD", text)
    return (
        t.replace("—", "-")   # em dash → hyphen
         .replace("–", "-")   # en dash → hyphen
         .replace("’", "'")   # curly apostrophe → straight
         .replace("“", '"')   # left double quote → straight
         .replace("”", '"')   # right double quote → straight
         .lower().strip()
    )

def classify(text: str) -> EmotionSignals:
    t = _normalize(text)
    if any(w in t for w in NEG_WORDS):
        return EmotionSignals(label="frustrated", sentiment=-0.4)
    if any(w in t for w in POS_WORDS):
        return EmotionSignals(label="engaged", sentiment=0.5)
    # neutral fallback
    return EmotionSignals(label="calm", sentiment=0.0)

def estimate_perf(text: str) -> PerformanceSignals:
    # very rough heuristic: “I got it / I solved it” -> correct
    t1 = _normalize(text)
    perf = PerformanceSignals()
    if _CORRECT_RE.search(t1):
        perf.correct = True
        perf.accuracy_pct = 1.0
        perf.attempts = 1
    return perf

# Audio-based emotion analysis (SpeechBrain)
# Load SpeechBrain emotion recognition model (only load once)
_sb_emotion_model = None
_sb_emotion_device = None
def get_sb_emotion_model():
    """Load SpeechBrain emotion model on GPU if available."""
    global _sb_emotion_model, _sb_emotion_device
    if _sb_emotion_model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _sb_emotion_model = EncoderClassifier.from_hparams(
            source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
            savedir="pretrained_models/speechbrain_emotion",
            run_opts={"device": device},
        )
        _sb_emotion_device = torch.device(device)
    return _sb_emotion_model

def get_emotion_model_device() -> str:
    """
    Returns the device string ("cuda" or "cpu") the SpeechBrain
    emotion model intends to use. If the model has already been loaded,
    returns the actual device; otherwise infers from CUDA availability.
    """
    global _sb_emotion_device
    if _sb_emotion_device is not None:
        try:
            return str(_sb_emotion_device)
        except Exception:
            pass
    return "cuda" if torch.cuda.is_available() else "cpu"

def torch_runtime_info() -> dict:
    """Return a small dict with Torch/audio/SpeechBrain + CUDA status."""
    info = {
        "torch": getattr(torch, "__version__", "unknown"),
        "torchaudio": getattr(torchaudio, "__version__", "unknown"),
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
    }
    try:
        import speechbrain  # type: ignore
        info["speechbrain"] = getattr(speechbrain, "__version__", "unknown")
    except Exception:
        info["speechbrain"] = "unknown"
    if info["cuda_available"] and info["cuda_device_count"] > 0:
        try:
            info["device_name"] = torch.cuda.get_device_name(0)
        except Exception:
            info["device_name"] = None
    else:
        info["device_name"] = None
    return info

def detect_audio_emotion(file_path: str):
    """
    Classify emotion from an audio file using SpeechBrain's
    wav2vec2 IEMOCAP model.

    GPU acceleration is used when available.

    Returns: (top_label: str, scores: dict[label -> score])
    """
    model = get_sb_emotion_model()
    signal, fs = torchaudio.load(file_path)  # shape: [channels, time]
    # Convert to mono if multi-channel
    if signal.shape[0] > 1:
        signal = torch.mean(signal, dim=0, keepdim=True)  # [1, time]
    # Ensure 16 kHz sample rate for wav2vec2
    target_sr = 16000
    if fs != target_sr:
        signal = torchaudio.functional.resample(signal, fs, target_sr)
    # Move to model device
    device = getattr(model, "device", torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    signal = signal.to(device)
    # Inference
    model.eval()
    with torch.no_grad():
        prediction = model.classify_batch(signal)
    # Extract top label and per-class scores
    emotion_label = prediction[3][0]
    scores = {lbl: float(score) for lbl, score in zip(prediction[2][0], prediction[1][0])}
    return emotion_label, scores

def extract_opensmile_features_from_file(file_path: str) -> dict:
    """
    Extract eGeMAPSv02 Functionals features from a WAV file using openSMILE.
    Returns a flat dict of feature_name -> value.

    Note: This is provided for experimentation; the active classifier uses
    SpeechBrain. If you want to swap to an openSMILE-based classifier, you can
    load a trained model and consume these features.
    """
    try:
        import opensmile
        import soundfile as sf
        import numpy as np
    except Exception as e:
        raise RuntimeError(
            "openSMILE feature extraction unavailable; install 'opensmile' and 'soundfile'"
        ) from e
    audio, sr = sf.read(file_path)
    if hasattr(audio, "ndim") and getattr(audio, "ndim", 1) > 1:
        audio = np.mean(audio, axis=1)
    smile = opensmile.Smile(
        feature_set=opensmile.FeatureSet.eGeMAPSv02,
        feature_level=opensmile.FeatureLevel.Functionals,
    )
    df = smile.process_signal(audio, sr)
    return df.iloc[0].to_dict()
