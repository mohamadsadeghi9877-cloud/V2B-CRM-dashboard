import os
import io
import sys
import logging
from pathlib import Path
from typing import Optional
import numpy as np
import av
import sherpa_onnx

logger = logging.getLogger(__name__)

# مسیر مدل شنوا
SHENAVA_DIR = Path(__file__).parent / "models" / "shenava"
MODEL_PATH = SHENAVA_DIR / "model.onnx"
TOKENS_PATH = SHENAVA_DIR / "tokens.txt"

# افزودن ماژول itn برای تبدیل اعداد و کلمات فارسی
try:
    from ghofreyar.persian_itn import itn
except ImportError:
    if str(SHENAVA_DIR) not in sys.path:
        sys.path.append(str(SHENAVA_DIR))
    try:
        from persian_itn import itn
    except ImportError:
        itn = lambda x: x


class STTService:
    """High-speed Offline Persian Speech-to-Text powered by Shenava-Koochik and Sherpa-ONNX."""

    def __init__(self, num_threads: int = 4, lazy_load: bool = False, **kwargs):
        self.num_threads = num_threads
        self.model_name = kwargs.get("model_name", "shenava-koochik")
        self.sample_rate = kwargs.get("sample_rate", 16000)
        self._recognizer: Optional[sherpa_onnx.OfflineRecognizer] = None

        if not lazy_load:
            self._load_engine()

    @property
    def is_loaded(self) -> bool:
        return self._recognizer is not None

    def _load_engine(self):
        if self._recognizer is None:
            logger.info("Initializing offline Persian Shenava-Koochik STT engine (Sherpa-ONNX)...")
            try:
                if not MODEL_PATH.exists() or not TOKENS_PATH.exists():
                    raise FileNotFoundError(
                        f"Shenava model files not found in {SHENAVA_DIR}. Model: {MODEL_PATH.exists()}, Tokens: {TOKENS_PATH.exists()}"
                    )

                self._recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
                    model=str(MODEL_PATH),
                    tokens=str(TOKENS_PATH),
                    num_threads=self.num_threads,
                )
                logger.info("Persian Shenava-Koochik STT engine initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to load Shenava-Koochik STT: {e}")
                raise

    def _convert_audio_to_16k_mono(self, audio_bytes: bytes) -> np.ndarray:
        """Decode any audio format (WebM, Opus, WAV, MP3) in-memory to 16kHz mono float32 numpy array using PyAV."""
        if not audio_bytes:
            return np.array([], dtype=np.float32)

        input_container = av.open(io.BytesIO(audio_bytes))
        audio_stream = next((s for s in input_container.streams if s.type == "audio"), None)
        if not audio_stream:
            raise ValueError("No audio stream found in input bytes.")

        resampler = av.AudioResampler(
            format="flt",  # float32
            layout="mono",
            rate=16000
        )

        frames = []
        for frame in input_container.decode(audio_stream):
            frame.pts = None
            resampled_frames = resampler.resample(frame)
            for rf in resampled_frames:
                arr = rf.to_ndarray()  # shape: (channels, samples)
                frames.append(arr.flatten())

        input_container.close()

        if not frames:
            return np.array([], dtype=np.float32)

        audio_data = np.concatenate(frames).astype(np.float32)
        return audio_data

    def transcribe_bytes(self, audio_bytes: bytes) -> str:
        """Transcribe in-memory audio bytes (WebM, WAV, etc.) to clean Persian text."""
        if not audio_bytes:
            return ""

        if not self.is_loaded:
            self._load_engine()

        try:
            samples = self._convert_audio_to_16k_mono(audio_bytes)
            if len(samples) < 1600:  # کمتر از 0.1 ثانیه
                return ""

            stream = self._recognizer.create_stream()
            stream.accept_waveform(16000, samples)
            self._recognizer.decode_stream(stream)
            raw_text = stream.result.text.strip()
            if not raw_text:
                return ""

            final_text = itn(raw_text)
            logger.info(f"Shenava STT Transcribed: '{final_text}'")
            return final_text
        except Exception as e:
            logger.error(f"Error during Shenava audio transcription: {e}")
            raise

    def transcribe_file(self, file_path: str) -> str:
        """Transcribe an audio file from disk."""
        with open(file_path, "rb") as f:
            return self.transcribe_bytes(f.read())
