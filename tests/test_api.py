import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from ghofreyar.app import app, get_agent
from ghofreyar.models import LLMResponse, ExtractedData


@pytest.fixture
def client_with_mock_agent():
    mock_agent = MagicMock()
    mock_agent.get_initial_greeting.return_value = "سلام! به غرفه ما خوش آمدید!"
    mock_agent.history = [{"role": "assistant", "content": "سلام! به غرفه ما خوش آمدید!"}]
    mock_agent.form_manager.get_form_dict.return_value = {
        "full_name": None,
        "phone_number": None,
        "email": None,
        "company_name": None,
        "job_title": None,
        "field_of_interest": None,
        "notes": None
    }
    mock_agent.form_manager.is_complete = False
    mock_agent.form_manager.off_topic_count = 0
    mock_agent.process_text.return_value = {
        "transcript": "علی رضایی هستم",
        "spoken_response": "خوش آمدید آقای رضایی!",
        "extracted_data": {"full_name": "علی رضایی"},
        "updated_fields": {"full_name": "علی رضایی"},
        "form_data": {"full_name": "علی رضایی", "phone_number": None},
        "is_off_topic": False,
        "conversation_complete": False,
        "audio_base64": "fake_base64"
    }
    mock_agent.get_summary.return_value = {
        "full_name": "علی رضایی",
        "phone_number": "09121234567",
        "email": None,
        "company_name": None,
        "job_title": None,
        "field_of_interest": None,
        "notes": None,
        "is_required_complete": True,
        "is_conversation_complete": True
    }

    app.dependency_overrides[get_agent] = lambda: mock_agent
    client = TestClient(app)
    yield client, mock_agent
    app.dependency_overrides.clear()


def test_api_state(client_with_mock_agent):
    client, mock_agent = client_with_mock_agent
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.json()
    assert "form_data" in data
    assert "history" in data


def test_api_chat_text(client_with_mock_agent):
    client, mock_agent = client_with_mock_agent
    response = client.post("/api/chat", json={"text": "علی رضایی هستم"})
    assert response.status_code == 200
    data = response.json()
    assert data["spoken_response"] == "خوش آمدید آقای رضایی!"
    assert data["form_data"]["full_name"] == "علی رضایی"
    assert data["audio_base64"] == "fake_base64"


def test_api_reset(client_with_mock_agent):
    client, mock_agent = client_with_mock_agent
    response = client.post("/api/reset")
    assert response.status_code == 200
    assert mock_agent.reset.called


def test_api_summary(client_with_mock_agent):
    client, mock_agent = client_with_mock_agent
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "علی رضایی"
    assert data["is_required_complete"] is True
