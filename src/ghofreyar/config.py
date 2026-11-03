import os
from pydantic import BaseModel


class Settings(BaseModel):
    # LLM & Local Server Settings (Unsloth Desktop / LM Studio / Ollama / llama.cpp)
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8888")
    llm_model: str = os.getenv("LLM_MODEL", "unsloth/Qwen3.5-4B-MTP-GGUF")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")

    # Backward compatibility aliases
    @property
    def ollama_base_url(self) -> str:
        return self.llm_base_url

    @property
    def ollama_model(self) -> str:
        return self.llm_model

    # Speech settings (Whisper STT: small, base, tiny)
    stt_model: str = os.getenv("STT_MODEL", "small")
    sample_rate: int = int(os.getenv("SAMPLE_RATE", "16000"))
    port: int = int(os.getenv("PORT", "8090"))
    host: str = os.getenv("HOST", "0.0.0.0")


settings = Settings()
