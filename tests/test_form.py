import pytest
from ghofreyar.form_service import FormManager
from ghofreyar.models import ExtractedData, LLMResponse


def test_form_initial_empty_state():
    manager = FormManager()
    assert manager.data.full_name is None
    assert manager.data.phone_number is None
    assert not manager.is_required_data_complete()
    assert not manager.is_complete


def test_form_progressive_data_filling():
    manager = FormManager()

    # Step 1: User provides name
    step1_data = ExtractedData(
        full_name="علی رضایی",
        phone_number=None,
        email=None,
        company_name=None,
        job_title=None,
        field_of_interest=None,
        notes=None
    )
    manager.update_with_extracted(step1_data)
    assert manager.data.full_name == "علی رضایی"
    assert manager.data.phone_number is None
    assert not manager.is_required_data_complete()

    # Step 2: User provides phone number (full_name is null in this step's delta)
    step2_data = ExtractedData(
        full_name=None,
        phone_number="09123456789",
        email=None,
        company_name=None,
        job_title=None,
        field_of_interest=None,
        notes=None
    )
    manager.update_with_extracted(step2_data)
    # full_name must be preserved!
    assert manager.data.full_name == "علی رضایی"
    assert manager.data.phone_number == "09123456789"
    assert manager.is_required_data_complete()


def test_form_field_correction():
    manager = FormManager()
    manager.update_with_extracted(ExtractedData(
        full_name="علی",
        phone_number="09120000000"
    ))
    assert manager.data.full_name == "علی"
    assert manager.data.phone_number == "09120000000"

    # User corrects full name to "علی حسینی" and company to "ابرآوران"
    manager.update_with_extracted(ExtractedData(
        full_name="علی حسینی",
        company_name="ابرآوران"
    ))
    assert manager.data.full_name == "علی حسینی"
    assert manager.data.company_name == "ابرآوران"
    # phone_number remains intact
    assert manager.data.phone_number == "09120000000"


def test_form_completion_and_summary():
    manager = FormManager()
    manager.update_with_extracted(ExtractedData(
        full_name="مریم دانش",
        phone_number="09191234567",
        email="maryam@example.com",
        company_name="فناوران نوین",
        job_title="مدیر محصول",
        field_of_interest="بینایی ماشین",
        notes="جلسه دوشنبه"
    ))
    manager.set_complete(True)
    assert manager.is_complete is True
    assert manager.is_required_data_complete() is True

    summary = manager.get_confirmation_summary()
    assert summary["full_name"] == "مریم دانش"
    assert summary["phone_number"] == "09191234567"
    assert summary["email"] == "maryam@example.com"
    assert summary["company_name"] == "فناوران نوین"
    assert summary["job_title"] == "مدیر محصول"
    assert summary["field_of_interest"] == "بینایی ماشین"
    assert summary["notes"] == "جلسه دوشنبه"


def test_form_project_inquiries_and_leads():
    manager = FormManager()
    manager.update_with_extracted(ExtractedData(
        full_name="رضا علوی",
        phone_number="09351112233",
        project_description="طراحی سیستم اتوماسیون انبار با هوش مصنوعی",
        estimated_budget="۵۰۰ میلیون تومان",
        timeline="۳ ماه آینده"
    ))
    summary = manager.get_confirmation_summary()
    assert summary["full_name"] == "رضا علوی"
    assert summary["project_description"] == "طراحی سیستم اتوماسیون انبار با هوش مصنوعی"
    assert summary["estimated_budget"] == "۵۰۰ میلیون تومان"
    assert summary["timeline"] == "۳ ماه آینده"

