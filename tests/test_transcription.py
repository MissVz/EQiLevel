# tests/test_transcription.py
import pytest
from src.audio.transcribe_to_json import transcribe_audio
import os

def test_transcribe_audio_runs(tmp_path):
    # Use a sample audio file from samples/
    sample_audio = os.path.join('samples', 'easy.m4a')
    output_dir = tmp_path
    # Should not raise exception
    try:
        transcribe_audio(sample_audio, model_size="tiny", output_dir=output_dir)
    except Exception as e:
        pytest.fail(f"transcribe_audio raised an exception: {e}")
    # Check output file exists
    output_files = list(output_dir.iterdir())
    assert any(f.suffix == '.json' for f in output_files)
