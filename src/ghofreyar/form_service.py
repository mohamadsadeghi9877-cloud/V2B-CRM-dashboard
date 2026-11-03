from typing import Dict, Any, Optional
from ghofreyar.models import ExtractedData


class FormManager:
    """Manages form state, progressive field updating, validation, and off-topic tracking."""

    def __init__(self):
        self.data = ExtractedData()
        self.is_complete: bool = False
        self.off_topic_count: int = 0
        self.is_current_turn_off_topic: bool = False

    def update_with_extracted(self, extracted: ExtractedData) -> Dict[str, Any]:
        """Progressively merge non-null extracted fields into the persistent form state.
        Returns a dict of fields that were updated in this step.
        """
        updated_fields = {}
        for field_name, value in extracted.model_dump().items():
            if value is not None and str(value).strip():
                # Update or correct existing field value
                setattr(self.data, field_name, str(value).strip())
                updated_fields[field_name] = str(value).strip()

        return updated_fields

    def record_turn(self, is_off_topic: bool):
        """Track turn topic adherence and off-topic streaks."""
        self.is_current_turn_off_topic = is_off_topic
        if is_off_topic:
            self.off_topic_count += 1
        else:
            self.off_topic_count = 0

    def should_force_steer_back(self) -> bool:
        """Rule: After at most 2 off-topic turns, must steer conversation back to the form."""
        return self.off_topic_count >= 2

    def get_steering_instruction_if_needed(self) -> Optional[str]:
        if self.should_force_steer_back():
            return "تذکر مهم: کاربر ۲ نوبت متوالی خارج از موضوع گفتگو کرده است. فوراً و مؤدبانه گفتگو را برای بازگرداندن به فرم هدایت کن."
        return None

    def is_required_data_complete(self) -> bool:
        """Checks if all mandatory fields (full_name and phone_number) are filled."""
        has_name = bool(self.data.full_name and self.data.full_name.strip())
        has_phone = bool(self.data.phone_number and self.data.phone_number.strip())
        return has_name and has_phone

    def set_complete(self, complete: bool = True):
        self.is_complete = complete

    def get_form_dict(self) -> Dict[str, Any]:
        return self.data.model_dump()

    def get_confirmation_summary(self) -> Dict[str, Any]:
        """Summary formatted for final review and confirmation."""
        return {
            "full_name": self.data.full_name,
            "phone_number": self.data.phone_number,
            "email": self.data.email,
            "company_name": self.data.company_name,
            "job_title": self.data.job_title,
            "project_description": self.data.project_description,
            "field_of_interest": self.data.field_of_interest,
            "estimated_budget": self.data.estimated_budget,
            "timeline": self.data.timeline,
            "notes": self.data.notes,
            "is_required_complete": self.is_required_data_complete(),
            "is_conversation_complete": self.is_complete
        }

    def reset(self):
        """Reset form state for a new visitor."""
        self.data = ExtractedData()
        self.is_complete = False
        self.off_topic_count = 0
        self.is_current_turn_off_topic = False
