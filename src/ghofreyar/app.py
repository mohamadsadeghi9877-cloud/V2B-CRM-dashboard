import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ghofreyar.config import settings
from ghofreyar.crm_database import init_db
from ghofreyar.crm_routes import router as crm_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ghofreyar")

# Initialize SQLite CRM Database Tables
init_db()

app = FastAPI(title="Ghofreyar Voice Agent", description="Intelligent Persian Exhibition Booth Assistant")

# Register CRM Router
app.include_router(crm_router)

# Global singleton booth agent instance
_booth_agent: Optional[Any] = None


def get_agent() -> Any:
    global _booth_agent
    if _booth_agent is None:
        try:
            from ghofreyar.agent import BoothAgent
            from ghofreyar.stt_service import STTService
            from ghofreyar.tts_service import TTSService
            from ghofreyar.llm_service import LLMService
            from ghofreyar.gemini_service import GeminiService
            stt = STTService(lazy_load=True)
            tts = TTSService(lazy_load=False)
            llm = LLMService(
                base_url=settings.llm_base_url,
                model=settings.llm_model,
                api_key=settings.llm_api_key
            )
            gemini = GeminiService()
            _booth_agent = BoothAgent(stt_service=stt, tts_service=tts, llm_service=llm, gemini_service=gemini)
        except Exception as e:
            logger.warning(f"Voice agent dependencies not available: {e}")
            return None
    return _booth_agent


class TextChatRequest(BaseModel):
    text: str


class TTSRequest(BaseModel):
    text: str


# Static frontend path
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/api/state")
def get_state(agent: Any = Depends(get_agent)):
    """Return the current conversation state and form data."""
    if not agent:
        return {"greeting": "", "greeting_audio": "", "history": [], "form_data": {}, "is_complete": False}
    greeting = agent.get_initial_greeting()
    try:
        greeting_audio = agent.tts.synthesize_to_base64(greeting)
    except Exception:
        greeting_audio = ""
    return {
        "greeting": greeting,
        "greeting_audio": greeting_audio,
        "history": agent.history,
        "form_data": agent.form_manager.get_form_dict(),
        "is_complete": agent.form_manager.is_complete,
        "is_required_complete": agent.form_manager.is_required_data_complete(),
        "off_topic_count": agent.form_manager.off_topic_count,
        "is_off_topic": agent.form_manager.is_current_turn_off_topic
    }


@app.post("/api/chat")
def chat_text(req: TextChatRequest, agent: Any = Depends(get_agent)):
    """Process visitor text message."""
    if not agent:
        raise HTTPException(status_code=503, detail="Voice agent service offline")
    result = agent.process_text(req.text)
    result.pop("audio_bytes", None)
    return result


@app.post("/api/chat/audio")
async def chat_audio(file: UploadFile = File(...), agent: Any = Depends(get_agent)):
    """Process visitor audio recording from microphone."""
    if not agent:
        raise HTTPException(status_code=503, detail="Voice agent service offline")
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file uploaded")
        content_type = file.content_type or ("audio/webm" if file.filename.endswith(".webm") else "audio/wav")
        result = agent.process_audio(audio_bytes, mime_type=content_type)
        result.pop("audio_bytes", None)
        return result
    except Exception as e:
        logger.error(f"Error processing audio upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts")
def synthesize_tts(req: TTSRequest, agent: Any = Depends(get_agent)):
    """Synthesize text to speech and return base64 encoded audio."""
    if not agent:
        return {"audio_base64": ""}
    clean_text = (req.text or "").strip()
    if not clean_text:
        return {"audio_base64": ""}
    audio_base64 = agent.tts.synthesize_to_base64(clean_text)
    return {"audio_base64": audio_base64}


@app.get("/api/summary")
def get_summary(agent: Any = Depends(get_agent)):
    """Get final confirmation summary of extracted lead data."""
    if not agent:
        return {}
    return agent.get_summary()


@app.post("/api/reset")
def reset_conversation(agent: Any = Depends(get_agent)):
    """Reset the assistant for a new booth visitor."""
    if not agent:
        return {"status": "reset", "greeting": "", "form_data": {}}
    agent.reset()
    return {
        "status": "reset",
        "greeting": agent.get_initial_greeting(),
        "form_data": agent.form_manager.get_form_dict()
    }


# Mount static assets
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Ghofreyar Voice Agent Backend Running. Visit /docs for API."}


@app.get("/style.css")
def serve_css():
    css_file = STATIC_DIR / "style.css"
    if css_file.exists():
        return FileResponse(css_file, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS not found")


@app.get("/app.js")
def serve_js():
    js_file = STATIC_DIR / "app.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JS not found")


def main():
    import uvicorn
    uvicorn.run("ghofreyar.app:app", host=settings.host, port=settings.port, reload=True)


if __name__ == "__main__":
    main()
