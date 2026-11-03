import json
import pytest
from unittest.mock import MagicMock, patch
from ghofreyar.llm_service import LLMService, LLMResponseError
from ghofreyar.models import LLMResponse, ExtractedData


def test_llm_parse_valid_json():
    llm = LLMService(base_url="http://mock-ollama:11434", model="llama3:8b")
    raw_json = json.dumps({
        "spoken_response": "سلام! خوش آمدید.",
        "extracted_data": {
            "full_name": "علی رضایی",
            "phone_number": "09121111111",
            "email": "ali@example.com",
            "company_name": "دیجی‌تک",
            "job_title": "مدیر فنی",
            "field_of_interest": "هوش مصنوعی",
            "notes": "علاقه‌مند به همکاری"
        },
        "is_off_topic": False,
        "conversation_complete": False
    })

    parsed = llm.parse_response(raw_json)
    assert isinstance(parsed, LLMResponse)
    assert parsed.spoken_response == "سلام! خوش آمدید."
    assert parsed.extracted_data.full_name == "علی رضایی"
    assert parsed.extracted_data.phone_number == "09121111111"
    assert parsed.extracted_data.email == "ali@example.com"
    assert parsed.is_off_topic is False
    assert parsed.conversation_complete is False


def test_llm_parse_markdown_wrapped_json():
    llm = LLMService(base_url="http://mock-ollama:11434", model="llama3:8b")
    markdown_payload = """
    مطابق درخواست شما خروجی به شکل زیر است:
    ```json
    {
      "spoken_response": "ممنون، نام شما ثبت شد.",
      "extracted_data": {
        "full_name": "سارا محمدی",
        "phone_number": null,
        "email": null,
        "company_name": null,
        "job_title": null,
        "field_of_interest": null,
        "notes": null
      },
      "is_off_topic": false,
      "conversation_complete": false
    }
    ```
    """
    parsed = llm.parse_response(markdown_payload)
    assert isinstance(parsed, LLMResponse)
    assert parsed.spoken_response == "ممنون، نام شما ثبت شد."
    assert parsed.extracted_data.full_name == "سارا محمدی"
    assert parsed.extracted_data.phone_number is None


def test_llm_call_mocked_ollama_api():
    llm = LLMService(base_url="http://mock-ollama:11434", model="qwen2:7b")
    
    expected_response_json = {
        "spoken_response": "سلام! من غرفه‌یار هستم.",
        "extracted_data": {
            "full_name": None,
            "phone_number": None,
            "email": None,
            "company_name": None,
            "job_title": None,
            "field_of_interest": None,
            "notes": None
        },
        "is_off_topic": False,
        "conversation_complete": False
    }

    mock_ollama_output = {
        "message": {
            "role": "assistant",
            "content": json.dumps(expected_response_json)
        }
    }

    with patch("httpx.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_ollama_output
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "سلام"}]
        result = llm.generate_response(messages)

        assert isinstance(result, LLMResponse)
        assert result.spoken_response == "سلام! من غرفه‌یار هستم."
        assert result.extracted_data.full_name is None
        assert mock_post.called

        # Check that the system prompt was sent
        sent_payload = mock_post.call_args[1]["json"]
        assert sent_payload["model"] == "qwen2:7b"
        assert any("CRM" in m.get("content", "") or "مدیریت ارتباط" in m.get("content", "") for m in sent_payload["messages"])


def test_llm_invalid_json_raises_or_recovers():
    llm = LLMService(base_url="http://mock-ollama:11434", model="qwen2:7b")
    with pytest.raises(LLMResponseError):
        llm.parse_response("این یک متن تصادفی بدون ساختار جی‌سان است.")
