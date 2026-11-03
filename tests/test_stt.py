import io
import wave
import pytest
from unittest.mock import MagicMock, patch
from ghofreyar.stt_service import STTService


def _create_dummy_wav_bytes(duration_ms=100, sample_rate=16000) -> bytes:
    """Create a valid in-memory mono 16-bit 16kHz PCM WAV."""
    buf = io.BytesIO()
    num_frames = int(sample_rate * (duration_ms / 1000.0))
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


def test_stt_initialization_defaults():
    stt = STTService(model_name="fa", sample_rate=16000, lazy_load=True)
    assert stt.model_name == "fa"
    assert stt.sample_rate == 16000
    assert not stt.is_loaded


def test_stt_transcribe_file_mocked(tmp_path):
    stt = STTService(model_name="fa", lazy_load=True)
    with patch.object(stt, "transcribe_bytes", return_value="علی رضایی هستم") as mock_tb:
        dummy_file = tmp_path / "audio.wav"
        dummy_file.write_bytes(b"dummy_wav_content")

        result = stt.transcribe_file(str(dummy_file))
        assert result == "علی رضایی هستم"
        mock_tb.assert_called_once_with(b"dummy_wav_content")


def test_stt_transcribe_bytes_mocked(tmp_path):
    stt = STTService(model_name="fa", lazy_load=True)
    mock_recognizer = MagicMock()
    mock_stream = MagicMock()
    mock_stream.result.text = "سلام روزتون بخیر"
    mock_recognizer.create_stream.return_value = mock_stream
    stt._recognizer = mock_recognizer

    with patch.object(stt, "_convert_audio_to_16k_mono", return_value=[0.0] * 1600):
        wav_bytes = _create_dummy_wav_bytes()
        result = stt.transcribe_bytes(wav_bytes)

        assert "سلام روزتون بخیر" in result
        assert mock_recognizer.decode_stream.called


def test_stt_transcribe_empty_or_whitespace_handling(tmp_path):
    stt = STTService(model_name="fa", lazy_load=True)
    with patch.object(stt, "transcribe_bytes", return_value="") as mock_tb:
        dummy_file = tmp_path / "audio.wav"
        dummy_file.write_bytes(b"dummy_wav_content")

        result = stt.transcribe_file(str(dummy_file))
        assert result == ""
