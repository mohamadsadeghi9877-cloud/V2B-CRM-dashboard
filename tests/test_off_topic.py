import pytest
from ghofreyar.form_service import FormManager
from ghofreyar.models import ExtractedData, LLMResponse


def test_off_topic_flag_tracking():
    manager = FormManager()
    assert manager.off_topic_count == 0
    assert not manager.is_current_turn_off_topic

    # First off-topic turn
    manager.record_turn(is_off_topic=True)
    assert manager.off_topic_count == 1
    assert manager.is_current_turn_off_topic is True
    assert not manager.should_force_steer_back()

    # Second off-topic turn
    manager.record_turn(is_off_topic=True)
    assert manager.off_topic_count == 2
    assert manager.is_current_turn_off_topic is True
    # At 2 consecutive off-topic turns, we must steer back!
    assert manager.should_force_steer_back() is True

    # User returns on-topic
    manager.record_turn(is_off_topic=False)
    assert manager.off_topic_count == 0
    assert manager.is_current_turn_off_topic is False
    assert not manager.should_force_steer_back()


def test_off_topic_steering_instruction():
    manager = FormManager()
    manager.record_turn(is_off_topic=True)
    manager.record_turn(is_off_topic=True)

    steering_note = manager.get_steering_instruction_if_needed()
    assert steering_note is not None
    assert "بازگرداندن" in steering_note or "فرم" in steering_note
