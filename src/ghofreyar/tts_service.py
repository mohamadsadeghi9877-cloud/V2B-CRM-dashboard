import os
import io
import wave
import base64
import logging
from pathlib import Path
from typing import Optional
from piper import PiperVoice

logger = logging.getLogger(__name__)

# مسیر پیش‌فرض مدل‌های پایپر
PIPER_DIR = Path(__file__).parent / "models" / "piper"
DEFAULT_MODEL = PIPER_DIR / "fa_IR-amir-medium.onnx"
DEFAULT_CONFIG = PIPER_DIR / "fa_IR-amir-medium.onnx.json"


class TTSService:
    """High-performance Offline Persian Text-to-Speech powered by Piper TTS."""

    def __init__(self, lazy_load: bool = False):
        self._voice: Optional[PiperVoice] = None

        if not lazy_load:
            self._load_engine()

    @property
    def is_loaded(self) -> bool:
        return self._voice is not None

    def _load_engine(self):
        if self._voice is None:
            logger.info("Initializing offline Persian Piper TTS engine...")
            try:
                if not DEFAULT_MODEL.exists() or not DEFAULT_CONFIG.exists():
                    raise FileNotFoundError(
                        f"Piper model files not found in {PIPER_DIR}. Model: {DEFAULT_MODEL.exists()}, Config: {DEFAULT_CONFIG.exists()}"
                    )

                self._voice = PiperVoice.load(str(DEFAULT_MODEL), config_path=str(DEFAULT_CONFIG))
                logger.info("Persian Piper TTS engine initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Piper TTS: {e}")
                raise

    def synthesize_to_bytes(self, text: str) -> bytes:
        """Synthesize Persian text to WAV audio bytes offline using Piper."""
        clean_text = (text or "").strip()
        if not clean_text:
            return b""

        if not self.is_loaded:
            self._load_engine()

        try:
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav_file:
                self._voice.synthesize_wav(clean_text, wav_file)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Error synthesizing speech for text '{clean_text}': {e}")
            raise

    def synthesize_to_base64(self, text: str) -> str:
        """Synthesize Persian text to base64 encoded audio string for web streaming."""
        audio_bytes = self.synthesize_to_bytes(text)
        if not audio_bytes:
            return ""
        return base64.b64encode(audio_bytes).decode("utf-8")

    def save_to_file(self, text: str, output_path: str) -> str:
        """Synthesize speech and save directly to WAV file."""
        audio_bytes = self.synthesize_to_bytes(text)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        return output_path
