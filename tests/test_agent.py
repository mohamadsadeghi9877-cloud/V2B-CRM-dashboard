import pytest
from unittest.mock import MagicMock
from ghofreyar.agent import BoothAgent
from ghofreyar.models import LLMResponse, ExtractedData


def test_agent_greeting():
    agent = BoothAgent(stt_service=MagicMock(), tts_service=MagicMock(), llm_service=MagicMock())
    greeting = agent.get_initial_greeting()
    assert "مدیریت ارتباط با مشتریان" in greeting or "CRM" in greeting
    assert "خوش آمدید" in greeting or "خوش اومدید" in greeting


def test_agent_process_text_turn():
    mock_llm = MagicMock()
    mock_llm.generate_response.return_value = LLMResponse(
        spoken_response="از آشنایی با شما خوشحالم آقای رضایی! لطفاً شماره تماس یا ایمیلتون رو بفرمایید.",
        extracted_data=ExtractedData(full_name="علی رضایی"),
        is_off_topic=False,
        conversation_complete=False
    )
    mock_tts = MagicMock()
    mock_tts.synthesize_to_bytes.return_value = b"fake_wav_bytes"

    agent = BoothAgent(stt_service=MagicMock(), tts_service=mock_tts, llm_service=mock_llm)
    result = agent.process_text("علی رضایی هستم")

    assert result["spoken_response"] == "از آشنایی با شما خوشحالم آقای رضایی! لطفاً شماره تماس یا ایمیلتون رو بفرمایید."
    assert result["form_data"]["full_name"] == "علی رضایی"
    assert result["is_off_topic"] is False
    assert result["audio_bytes"] == b"fake_wav_bytes"


def test_agent_process_audio_turn():
    mock_stt = MagicMock()
    mock_stt.transcribe_bytes.return_value = "علی رضایی هستم"

    mock_llm = MagicMock()
    mock_llm.generate_response.return_value = LLMResponse(
        spoken_response="خوش آمدید آقای رضایی!",
        extracted_data=ExtractedData(full_name="علی رضایی"),
        is_off_topic=False,
        conversation_complete=False
    )
    mock_tts = MagicMock()
    mock_tts.synthesize_to_bytes.return_value = b"fake_audio"

    agent = BoothAgent(stt_service=mock_stt, tts_service=mock_tts, llm_service=mock_llm)
    result = agent.process_audio(b"some_audio_bytes")

    assert result["transcript"] == "علی رضایی هستم"
    assert result["form_data"]["full_name"] == "علی رضایی"
    assert mock_stt.transcribe_bytes.called
    assert mock_llm.generate_response.called
    assert mock_tts.synthesize_to_bytes.called
