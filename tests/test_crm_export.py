"""
Tests for CRM Excel Export endpoints.
Verifies that individual sheet exports and the consolidated all-in-one export work
and return valid Excel (.xlsx) file bytes.
"""

import io
import openpyxl
from fastapi.testclient import TestClient
from ghofreyar.app import app

client = TestClient(app)


def test_export_leads_excel():
    response = client.get("/api/crm/export/leads")
    assert response.status_code == 200
    assert "spreadsheetml.sheet" in response.headers.get("content-type", "")
    assert "attachment" in response.headers.get("content-disposition", "")

    # Load in openpyxl to verify valid xlsx structure
    wb = openpyxl.load_workbook(io.BytesIO(response.content))
    assert "سرنخ‌های فروش" in wb.sheetnames or len(wb.sheetnames) >= 1
    ws = wb.active
    assert ws.sheet_view.rightToLeft is True


def test_export_opportunities_excel():
    response = client.get("/api/crm/export/opportunities")
    assert response.status_code == 200
    assert "spreadsheetml.sheet" in response.headers.get("content-type", "")

    wb = openpyxl.load_workbook(io.BytesIO(response.content))
    assert len(wb.sheetnames) >= 1
    ws = wb.active
    assert ws.sheet_view.rightToLeft is True


def test_export_contacts_excel():
    response = client.get("/api/crm/export/contacts")
    assert response.status_code == 200
    assert "spreadsheetml.sheet" in response.headers.get("content-type", "")

    wb = openpyxl.load_workbook(io.BytesIO(response.content))
    assert len(wb.sheetnames) >= 1
    ws = wb.active
    assert ws.sheet_view.rightToLeft is True


def test_export_companies_excel():
    response = client.get("/api/crm/export/companies")
    assert response.status_code == 200
    assert "spreadsheetml.sheet" in response.headers.get("content-type", "")

    wb = openpyxl.load_workbook(io.BytesIO(response.content))
    assert len(wb.sheetnames) >= 1
    ws = wb.active
    assert ws.sheet_view.rightToLeft is True


def test_export_all_crm_excel():
    response = client.get("/api/crm/export/all")
    assert response.status_code == 200
    assert "spreadsheetml.sheet" in response.headers.get("content-type", "")

    wb = openpyxl.load_workbook(io.BytesIO(response.content))
    # Should contain all 4 sheets
    sheet_names = wb.sheetnames
    assert len(sheet_names) == 4
    for sheet in wb.worksheets:
        assert sheet.sheet_view.rightToLeft is True
