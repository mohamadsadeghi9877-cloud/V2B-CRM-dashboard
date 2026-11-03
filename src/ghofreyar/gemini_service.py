import os
import json
import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from ghofreyar.models import LLMResponse, ExtractedData
from ghofreyar.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


class GeminiService:
    """Multimodal Gemini 3.8 Service for high-precision Persian audio STT, dialog and lead extraction."""

    def __init__(self, api_key: str = GEMINI_API_KEY, model: str = GEMINI_MODEL):
        self.api_key = api_key
        self.model = model
        self.client = genai.Client(api_key=self.api_key)

    def process_turn(
        self,
        conversation_history: List[Dict[str, str]],
        audio_bytes: Optional[bytes] = None,
        mime_type: str = "audio/webm",
        user_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user turn via Gemini.
        Accepts raw audio bytes (native multimodal WebM/WAV) OR text.
        Returns transcript, LLMResponse (spoken response + extracted fields).
        """
        # Construct contents
        prompt_instruction = f"""{SYSTEM_PROMPT}

IMPORTANT ADDITIONAL INSTRUCTIONS FOR AUDIO/MULTIMODAL:
If audio is provided:
1. Transcribe the user's Persian speech accurately into a 'transcript' field.
2. Formulate your polite Persian spoken response in 'spoken_response'.
3. Extract any lead data or project inquiries in 'extracted_data'.
4. Indicate 'is_off_topic' (true/false) and 'conversation_complete' (true/false).

Return JSON only conforming strictly to this format:
{{
  "transcript": "متن دقیق کلماتی که کاربر به فارسی گفت",
  "spoken_response": "پاسخ گفتاری غرفه‌یار",
  "extracted_data": {{
    "full_name": null or "string",
    "phone_number": null or "string",
    "email": null or "string",
    "company_name": null or "string",
    "job_title": null or "string",
    "project_description": null or "string",
    "field_of_interest": null or "string",
    "estimated_budget": null or "string",
    "timeline": null or "string",
    "notes": null or "string"
  }},
  "is_off_topic": false or true,
  "conversation_complete": false or true
}}
"""
        contents = [prompt_instruction]

        # Add history
        history_summary = "Previous Conversation History:\n"
        for msg in conversation_history:
            history_summary += f"- {msg['role']}: {msg['content']}\n"
        contents.append(history_summary)

        # Attach Audio or Text
        if audio_bytes and len(audio_bytes) > 0:
            part_audio = types.Part.from_bytes(
                data=audio_bytes,
                mime_type=mime_type
            )
            contents.append(part_audio)
            contents.append("Please listen to the attached audio, transcribe it, respond warmly, and extract all lead/project details.")
        elif user_text:
            contents.append(f"Current User Text: {user_text}")

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )

            raw_text = response.text or "{}"
            data = json.loads(raw_text)

            transcript = data.get("transcript", user_text or "")
            spoken_response = data.get("spoken_response", "متشکرم، اطلاعات شما ثبت شد.")
            raw_extracted = data.get("extracted_data", {})
            extracted = ExtractedData.model_validate(raw_extracted)
            is_off_topic = bool(data.get("is_off_topic", False))
            conv_complete = bool(data.get("conversation_complete", False))

            return {
                "transcript": transcript,
                "llm_response": LLMResponse(
                    spoken_response=spoken_response,
                    extracted_data=extracted,
                    is_off_topic=is_off_topic,
                    conversation_complete=conv_complete
                )
            }

        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            raise
