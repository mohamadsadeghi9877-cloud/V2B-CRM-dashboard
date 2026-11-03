import pytest
from fastapi.testclient import TestClient
from ghofreyar.app import app
from ghofreyar.persian_itn import itn
from ghofreyar.llm_service import LLMService

client = TestClient(app)


def test_persian_itn_and_domain_correction():
    raw_speech = (
        "محمد صادقی از شرکت تییتان صنعت شماره همراه 0900ودوازده،0دوازده،6681 سمت کارشناس فروش "
        "برای ایجنت منافات درخواست داشتیم که حالا هنوز فعلا بودجه تقلبی و مشخص نیست و "
        "باز زمانی اجرا هم همین طور در کل به بحث ایجنتس در مناقاسات علاقه داریم."
    )
    cleaned = itn(raw_speech)
    assert "09120126681" in cleaned
    assert "تیتان صنعت" in cleaned
    assert "ایجنت مناقصات" in cleaned
    assert "بودجه تقریبی" in cleaned
    assert "بازه زمانی" in cleaned
    assert "ایجنت‌ها در مناقصات" in cleaned


def test_quick_capture_populates_all_four_sheets():
    payload = {
        "full_name": "محمد صادقی",
        "phone_number": "09120126681",
        "email": "m.sadeghi@titansanat.ir",
        "company_name": "تیتان صنعت",
        "job_title": "کارشناس فروش",
        "project_title": "درخواست برای ایجنت مناقصات",
        "field_of_interest": "ایجنت‌ها در مناقصات",
        "estimated_budget": "۱۰۰ میلیون تومان",
        "timeline": "۲ ماه آینده",
        "notes": "مشتری غرفه نمایشگاه، علاقه‌مند به هوش مصنوعی",
        "temperature": "Hot"
    }

    # 1. Quick capture call
    resp = client.post("/api/crm/quick-capture", json=payload)
    assert resp.status_code == 201
    lead_data = resp.json()
    assert lead_data["title"] == "درخواست برای ایجنت مناقصات"

    # 2. Check Companies sheet
    comp_resp = client.get("/api/crm/companies")
    assert comp_resp.status_code == 200
    companies = comp_resp.json()
    assert any(c["name"] == "تیتان صنعت" for c in companies)

    # 3. Check Contacts sheet
    contact_resp = client.get("/api/crm/contacts")
    assert contact_resp.status_code == 200
    contacts = contact_resp.json()
    assert any(c["full_name"] == "محمد صادقی" and c["phone_number"] == "09120126681" for c in contacts)

    # 4. Check Leads sheet
    leads_resp = client.get("/api/crm/leads")
    assert leads_resp.status_code == 200
    leads = leads_resp.json()
    assert any(l["title"] == "درخواست برای ایجنت مناقصات" for l in leads)

    # 5. Check Opportunities sheet
    opps_resp = client.get("/api/crm/opportunities")
    assert opps_resp.status_code == 200
    opps = opps_resp.json()
    assert any("محمد صادقی" in o["title"] and o["amount"] == 100_000_000.0 for o in opps)


def test_quick_capture_introduction_only_fills_three_sheets_no_opportunity():
    """
    وقتی بازدیدکننده صرفاً خود را معرفی می‌کند یا کارت ویزیت می‌دهد و درخواستی ندارد:
    تنها ۳ شیت (مخاطبان، شرکت‌ها و سرنخ‌ها) پر می‌شوند و فرصت فروش (Opportunity) ایجاد نمی‌شود.
    """
    payload = {
        "full_name": "سارا باقری",
        "phone_number": "09351112233",
        "email": "sara.bagheri@novin.com",
        "company_name": "شرکت داده‌پردازی نوین",
        "job_title": "مدیر منابع انسانی",
        "project_title": None,
        "field_of_interest": None,
        "estimated_budget": None,
        "timeline": None,
        "notes": "صرفاً جهت احوالپرسی و دریافت بروشور به غرفه آمدند",
        "temperature": "Cold"
    }

    # Count opportunities before
    opps_before = len(client.get("/api/crm/opportunities").json())

    # 1. Quick capture call
    resp = client.post("/api/crm/quick-capture", json=payload)
    assert resp.status_code == 201

    # 2. Check Companies sheet (must exist)
    comp_resp = client.get("/api/crm/companies")
    assert comp_resp.status_code == 200
    assert any(c["name"] == "شرکت داده‌پردازی نوین" for c in comp_resp.json())

    # 3. Check Contacts sheet (must exist)
    contact_resp = client.get("/api/crm/contacts")
    assert contact_resp.status_code == 200
    assert any(c["full_name"] == "سارا باقری" for c in contact_resp.json())

    # 4. Check Leads sheet (must exist with empty/null title when no project title was given)
    leads_resp = client.get("/api/crm/leads")
    assert leads_resp.status_code == 200
    assert any((l["title"] is None or l["title"] == "" or l["title"] == "—") and l["contact"]["full_name"] == "سارا باقری" for l in leads_resp.json())

    # 5. Check Opportunities sheet (MUST NOT INCREASE)
    opps_after = len(client.get("/api/crm/opportunities").json())
    assert opps_after == opps_before, "در صورت نبود درخواست نباید رکورد فرصت فروش (Opportunity) اضافه شود"


def test_llm_fallback_heuristic_extracts_all_fields():
    svc = LLMService(base_url="http://127.0.0.1:9999")  # unreachable to force fallback
    msg = (
        "محمد صادقی از شرکت تیتان صنعت شماره همراه 09120126681 سمت کارشناس فروش "
        "برای ایجنت مناقصات درخواست داشتیم که حالا هنوز فعلا بودجه مشخص نیست و "
        "بازه زمانی اجرا هم همین طور در کل به بحث ایجنت‌ها در مناقصات علاقه داریم."
    )
    res = svc._fallback_heuristic_response([{"role": "user", "content": msg}])
    data = res.extracted_data
    assert data.full_name == "محمد صادقی"
    assert data.company_name == "تیتان صنعت"
    assert data.phone_number == "09120126681"
    assert data.job_title == "کارشناس فروش"
    assert "ایجنت مناقصات" in (data.project_description or "")
    assert data.estimated_budget == "نامشخص / در حال برآورد"
    assert data.timeline == "نامشخص"
