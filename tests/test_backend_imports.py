import pytest


def test_backend_module_imports():
    import backend
    from backend import (
        agent,
        app,
        config,
        form_service,
        llm_service,
        models,
        prompt,
        stt_service,
        tts_service,
    )
    assert backend.BoothAgent is not None or agent.BoothAgent is not None
    assert app.app is not None
    assert models.LLMResponse is not None
    assert prompt.SYSTEM_PROMPT is not None
