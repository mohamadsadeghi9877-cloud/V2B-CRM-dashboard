import time
import pytest
from fastapi.testclient import TestClient
from ghofreyar.app import app
from ghofreyar.crm_database import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_create_and_list_opportunity():
    ts = int(time.time() * 1000)
    # 1. Create company and contact
    comp_res = client.post("/api/crm/companies", json={"name": f"شرکت افق {ts}"})
    assert comp_res.status_code == 201
    comp_id = comp_res.json()["id"]

    cont_res = client.post("/api/crm/contacts", json={
        "full_name": f"مخاطب {ts}",
        "phone_number": f"0912{ts % 10000000:07d}",
        "company_id": comp_id
    })
    assert cont_res.status_code == 201
    cont_id = cont_res.json()["id"]

    # 2. Create opportunity
    opp_res = client.post("/api/crm/opportunities", json={
        "title": "پروژه طراحی پلتفرم سازمانی",
        "company_id": comp_id,
        "contact_id": cont_id,
        "amount": 150000000.0,
        "stage": "Proposal",
        "expected_close_date": "1405/09/30",
        "notes": "ارائه پروپوزال فنی انجام شد"
    })
    assert opp_res.status_code == 201
    opp_data = opp_res.json()
    assert opp_data["title"] == "پروژه طراحی پلتفرم سازمانی"
    assert opp_data["amount"] == 150000000.0
    assert opp_data["stage"] == "Proposal"
    assert opp_data["probability"] == 60  # Auto probability for Proposal

    opp_id = opp_data["id"]

    # 3. List opportunities
    list_res = client.get("/api/crm/opportunities")
    assert list_res.status_code == 200
    opps = list_res.json()
    assert any(o["id"] == opp_id for o in opps)

    # 4. Filter by stage
    filter_res = client.get("/api/crm/opportunities?stage=Proposal")
    assert filter_res.status_code == 200
    assert all(o["stage"] == "Proposal" for o in filter_res.json())


def test_convert_lead_to_opportunity():
    ts = int(time.time() * 1000)
    # 1. Quick capture a lead
    capture_res = client.post("/api/crm/quick-capture", json={
        "full_name": f"نیما {ts}",
        "phone_number": f"0913{ts % 10000000:07d}",
        "company_name": f"شرکت خزر {ts}",
        "project_title": "توسعه نرم‌افزار ابری",
        "estimated_budget": "۸۰ میلیون تومان"
    })
    assert capture_res.status_code == 201
    lead_id = capture_res.json()["id"]

    # 2. Convert lead to opportunity
    convert_res = client.post(f"/api/crm/leads/{lead_id}/convert", json={
        "opportunity_title": "قرارداد نرم‌افزار ابری خزر",
        "stage": "Negotiation",
        "expected_close_date": "1405/10/15"
    })
    assert convert_res.status_code == 201
    opp = convert_res.json()
    assert opp["title"] == "قرارداد نرم‌افزار ابری خزر"
    assert opp["amount"] == 80000000.0  # Parsed from "۸۰ میلیون تومان"
    assert opp["stage"] == "Negotiation"
    assert opp["probability"] == 80
    assert opp["lead_id"] == lead_id

    # 3. Verify lead status updated to Converted / Qualified
    lead_res = client.get(f"/api/crm/leads/{lead_id}")
    assert lead_res.status_code == 200
    assert lead_res.json()["status"] in ("Converted", "Qualified")


def test_opportunity_stage_update_and_stats():
    # 1. Create an opportunity
    opp_res = client.post("/api/crm/opportunities", json={
        "title": "معامله تجهیزات هوشمند",
        "amount": 200000000.0,
        "stage": "Prospecting"
    })
    assert opp_res.status_code == 201
    opp_id = opp_res.json()["id"]

    # 2. Update stage to Closed_Won
    stage_res = client.patch(f"/api/crm/opportunities/{opp_id}/stage", json={
        "stage": "Closed_Won",
        "notes": "قرارداد نهایی امضا و پیش‌پرداخت واریز شد"
    })
    assert stage_res.status_code == 200
    assert stage_res.json()["stage"] == "Closed_Won"
    assert stage_res.json()["probability"] == 100

    # 3. Verify stats
    stats_res = client.get("/api/crm/opportunities/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["won_count"] >= 1
    assert stats["won_value"] >= 200000000.0
    assert "Closed_Won" in stats["by_stage"]


def test_lead_status_change_to_converted_auto_creates_opportunity():
    """تغییر وضعیت سرنخ به Converted به‌صورت خودکار رکورد فرصت فروش ایجاد می‌کند."""
    ts = int(time.time() * 1000)
    # 1. Create a lead without specific project request
    capture_res = client.post("/api/crm/quick-capture", json={
        "full_name": f"سینا {ts}",
        "phone_number": f"0919{ts % 10000000:07d}",
        "company_name": f"شرکت آریا {ts}",
        "notes": "آشنایی اولیه در غرفه"
    })
    assert capture_res.status_code == 201
    lead_id = capture_res.json()["id"]

    # Check that currently no opportunity is linked
    opps_before = [o for o in client.get("/api/crm/opportunities").json() if o.get("lead_id") == lead_id]
    assert len(opps_before) == 0

    # 2. Patch status to Converted (as user does via dropdown)
    patch_res = client.patch(f"/api/crm/leads/{lead_id}/status", json={"status": "Converted"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "Converted"

    # 3. Verify opportunity was automatically created
    opps_after = [o for o in client.get("/api/crm/opportunities").json() if o.get("lead_id") == lead_id]
    assert len(opps_after) == 1
    opp = opps_after[0]
    assert opp["stage"] == "Requirement_Analysis"
    assert opp["probability"] == 20

    # 4. Patching again to Converted does not create duplicate
    client.patch(f"/api/crm/leads/{lead_id}/status", json={"status": "Converted"})
    opps_duplicate_check = [o for o in client.get("/api/crm/opportunities").json() if o.get("lead_id") == lead_id]
    assert len(opps_duplicate_check) == 1
