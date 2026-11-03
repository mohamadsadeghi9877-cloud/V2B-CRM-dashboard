import logging
import base64
import re
from typing import Dict, Any, List, Optional
from ghofreyar.models import LLMResponse, ExtractedData
from ghofreyar.form_service import FormManager
from ghofreyar.llm_service import LLMService
from ghofreyar.stt_service import STTService
from ghofreyar.tts_service import TTSService
from ghofreyar.gemini_service import GeminiService

logger = logging.getLogger(__name__)

INITIAL_GREETING = "سلام! به سامانه هوشمند مدیریت ارتباط با مشتریان خوش آمدید. خوشحالم که شما رو می‌بینم. ممکنه لطفاً خودتون و شرکتتون رو معرفی بفرمایید؟"


class BoothAgent:
    """Core Exhibition Booth Voice Agent orchestrating Gemini Multimodal, TTS and Form state."""

    def __init__(
        self,
        stt_service: Optional[STTService] = None,
        tts_service: Optional[TTSService] = None,
        llm_service: Optional[LLMService] = None,
        gemini_service: Optional[GeminiService] = None
    ):
        self.stt = stt_service or STTService(lazy_load=True)
        self.tts = tts_service or TTSService(lazy_load=True)
        self.llm = llm_service or LLMService()
        self.gemini = gemini_service or GeminiService()
        self.form_manager = FormManager()
        self.history: List[Dict[str, str]] = []
        self._initialize_history()

    def _initialize_history(self):
        self.history = [
            {"role": "assistant", "content": INITIAL_GREETING}
        ]

    def get_initial_greeting(self) -> str:
        return INITIAL_GREETING

    def _complete_turn(self, transcript: str, llm_response: LLMResponse) -> Dict[str, Any]:
        """Apply LLM response, update form state, synthesize speech and return turn payload."""
        # Add user text and assistant response to history
        self.history.append({"role": "user", "content": transcript})
        self.history.append({"role": "assistant", "content": llm_response.spoken_response})

        # Smart Phone Number extraction & normalization safeguard
        phone = llm_response.extracted_data.phone_number
        if phone:
            phone_clean = re.sub(r'[\s\-]+', '', str(phone))
            if phone_clean.startswith("9") and len(phone_clean) == 10:
                phone_clean = "0" + phone_clean
            elif phone_clean.startswith("+98") and len(phone_clean) == 13:
                phone_clean = "0" + phone_clean[3:]
            llm_response.extracted_data.phone_number = phone_clean
        else:
            # Fallback regex search on user transcript
            m = re.search(r'(09\d{9}|0[1-8]\d{8,9})', transcript)
            if m:
                llm_response.extracted_data.phone_number = m.group(1)

        # Update form state
        updated_fields = self.form_manager.update_with_extracted(llm_response.extracted_data)
        self.form_manager.record_turn(llm_response.is_off_topic)
        if llm_response.conversation_complete:
            self.form_manager.set_complete(True)

        # Synthesize speech
        audio_bytes = b""
        audio_base64 = ""
        try:
            audio_bytes = self.tts.synthesize_to_bytes(llm_response.spoken_response)
            if audio_bytes:
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")

        return {
            "transcript": transcript,
            "spoken_response": llm_response.spoken_response,
            "extracted_data": llm_response.extracted_data.model_dump(),
            "updated_fields": updated_fields,
            "form_data": self.form_manager.get_form_dict(),
            "is_off_topic": llm_response.is_off_topic,
            "conversation_complete": self.form_manager.is_complete,
            "audio_bytes": audio_bytes,
            "audio_base64": audio_base64
        }

    def process_text(self, user_text: str) -> Dict[str, Any]:
        """Process a text turn from visitor using local Qwen LLM."""
        clean_user_text = (user_text or "").strip()
        if not clean_user_text:
            return {
                "transcript": "",
                "spoken_response": "صداتون رو به درستی نشنیدم، ممکنه لطفاً دوباره بفرمایید؟",
                "extracted_data": {},
                "form_data": self.form_manager.get_form_dict(),
                "is_off_topic": False,
                "conversation_complete": self.form_manager.is_complete,
                "audio_bytes": None,
                "audio_base64": None
            }

        # Normalize spoken Persian numbers and format phone numbers in transcript
        try:
            from ghofreyar.persian_itn import itn
            clean_user_text = itn(clean_user_text)
        except Exception as e:
            logger.debug(f"ITN error: {e}")

        # 100% Local Qwen LLM dialog and structured extraction
        llm_response = self.llm.generate_response(self.history + [{"role": "user", "content": clean_user_text}])
        return self._complete_turn(clean_user_text, llm_response)

    def process_audio(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> Dict[str, Any]:
        """Process visitor audio 100% locally and exclusively using Shenava-Koochik STT."""
        transcript = self.stt.transcribe_bytes(audio_bytes)
        logger.info(f"Shenava STT successfully transcribed: '{transcript}'")
        return self.process_text(transcript)

    def get_summary(self) -> Dict[str, Any]:
        return self.form_manager.get_confirmation_summary()

    def reset(self):
        """Reset conversation and form for the next visitor."""
        self.form_manager.reset()
        self._initialize_history()
