"""
CRM Excel Export Service
Generates professional, styled, Persian RTL Excel files (.xlsx)
for individual CRM entities (Leads, Opportunities, Contacts, Companies)
as well as a consolidated multi-sheet workbook.
"""

import io
import urllib.parse
from typing import List
from datetime import datetime, timezone, timedelta
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from sqlalchemy.orm import Session
from ghofreyar.crm_models import Lead, Opportunity, Contact, Company

try:
    import zoneinfo
    TEHRAN_TZ = zoneinfo.ZoneInfo("Asia/Tehran")
except Exception:
    TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))


def format_crm_datetime(dt: datetime) -> str:
    """
    تبدیل تاریخ و زمان دیتابیس (UTC) به ساعت رسمی ایران (تهران)
    و نمایش با تقویم شمسی و ساعت و دقیقه دقیق.
    مثال: 1405/08/05 10:45
    """
    if not dt:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone(TEHRAN_TZ)
    try:
        import jdatetime
        jdt = jdatetime.datetime.fromgregorian(datetime=local_dt)
        return jdt.strftime("%Y/%m/%d %H:%M")
    except Exception:
        return local_dt.strftime("%Y/%m/%d %H:%M")


# Standard Persian Status Translations
STATUS_FA = {
    "New": "جدید (New)",
    "In_Progress": "در حال پیگیری",
    "Contacted": "تماس حاصل شده",
    "Qualified": "واجد شرایط (Qualified)",
    "Won": "موفق / برنده (Won)",
    "Lost": "ناموفق (Lost)",
}

TEMP_FA = {
    "Hot": "🔥 داغ (Hot)",
    "Warm": "⚡ گرم (Warm)",
    "Cold": "❄️ سرد (Cold)",
}

STAGE_FA = {
    "Prospecting": "🔍 کشف اولیه (Prospecting)",
    "Qualification": "🎯 واجد شرایط (Qualification)",
    "Proposal": "📑 ارائه پروپوزال (Proposal)",
    "Negotiation": "🤝 مذاکره نهایی (Negotiation)",
    "Closed_Won": "🏆 قرارداد موفق (Closed Won)",
    "Closed_Lost": "❌ از دست رفته (Closed Lost)",
}

PRIORITY_FA = {
    "High": "🔴 بالا (High)",
    "Medium": "🟡 متوسط (Medium)",
    "Low": "🟢 پایین (Low)",
}

DEAL_TYPE_FA = {
    "New Business": "مشتری جدید",
    "Existing Business": "مشتری فعلی",
    "Upgrade": "ارتقای سرویس",
    "Partner": "همکاری شرکتی",
}


def _create_styles():
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Tahoma", size=10, bold=True, color="FFFFFF")
    data_font = Font(name="Tahoma", size=10)
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    return header_fill, header_font, data_font, thin_border, center_align, right_align


def _auto_fit_columns(ws):
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            # Approximate width accounting for Persian characters
            cell_len = len(val_str)
            if cell_len > max_len:
                max_len = cell_len
        ws.column_dimensions[col_letter].width = max(max_len + 5, 14)


def build_leads_sheet(ws, leads: List[Lead]):
    ws.sheet_view.rightToLeft = True
    header_fill, header_font, data_font, thin_border, center_align, right_align = _create_styles()

    headers = [
        "ردیف",
        "کد لید",
        "نام مخاطب",
        "شماره تماس",
        "نام شرکت / سازمان",
        "عنوان نیاز / پروژه",
        "بودجه برآوردی",
        "اولویت (حرارت)",
        "وضعیت پیگیری",
        "حوزه علاقه‌مندی",
        "بازه زمانی اجرا",
        "یادداشت‌های پیگیری",
        "تاریخ ثبت"
    ]
    ws.append(headers)

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    for idx, lead in enumerate(leads, 1):
        contact_name = lead.contact.full_name if lead.contact else "—"
        contact_phone = lead.contact.phone_number if lead.contact else "—"
        company_name = lead.company.name if lead.company else (lead.contact.company.name if (lead.contact and lead.contact.company) else "—")
        created_str = format_crm_datetime(lead.created_at)

        row = [
            idx,
            lead.id,
            contact_name,
            contact_phone,
            company_name,
            lead.title or "—",
            lead.estimated_budget or "—",
            TEMP_FA.get(lead.temperature, lead.temperature or "—"),
            STATUS_FA.get(lead.status, lead.status or "—"),
            lead.field_of_interest or "—",
            lead.timeline or "—",
            lead.notes or "—",
            created_str
        ]
        ws.append(row)

    # Style data rows
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.font = data_font
            cell.border = thin_border
            cell.alignment = right_align

    _auto_fit_columns(ws)


def build_opportunities_sheet(ws, opps: List[Opportunity]):
    ws.sheet_view.rightToLeft = True
    header_fill, header_font, data_font, thin_border, center_align, right_align = _create_styles()
    opp_header_fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")

    headers = [
        "ردیف",
        "کد معامله",
        "عنوان فرصت تجاری",
        "شرکت / سازمان",
        "شخص مخاطب",
        "ارزش معامله (تومان)",
        "مرحله فروش (Stage)",
        "درصد احتمال موفقیت",
        "تاریخ پیش‌بینی توافق",
        "اولویت معامله",
        "نوع قرارداد",
        "سرنخ مبدا",
        "یادداشت‌ها و استراتژی",
        "تاریخ ایجاد"
    ]
    ws.append(headers)

    for cell in ws[1]:
        cell.fill = opp_header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    for idx, opp in enumerate(opps, 1):
        company_name = opp.company.name if opp.company else "—"
        contact_name = opp.contact.full_name if opp.contact else "—"
        origin_lead = f"لید شماره {opp.lead.id} ({opp.lead.title})" if opp.lead else "مستقیم"
        created_str = format_crm_datetime(opp.created_at)

        row = [
            idx,
            opp.id,
            opp.title,
            company_name,
            contact_name,
            opp.amount if opp.amount is not None else 0,
            STAGE_FA.get(opp.stage, opp.stage or "—"),
            f"{opp.probability or 0}٪",
            opp.expected_close_date or "—",
            PRIORITY_FA.get(opp.priority, opp.priority or "—"),
            DEAL_TYPE_FA.get(opp.deal_type, opp.deal_type or "—"),
            origin_lead,
            opp.notes or "—",
            created_str
        ]
        ws.append(row)

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.font = data_font
            cell.border = thin_border
            cell.alignment = right_align

    _auto_fit_columns(ws)


def build_contacts_sheet(ws, contacts: List[Contact]):
    ws.sheet_view.rightToLeft = True
    header_fill, header_font, data_font, thin_border, center_align, right_align = _create_styles()
    contact_header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")

    headers = [
        "ردیف",
        "کد مخاطب",
        "نام و نام خانوادگی",
        "سمت سازمانی / عنوان شغلی",
        "شرکت متصل",
        "شماره تماس / همراه",
        "آدرس ایمیل",
        "تاریخ ثبت"
    ]
    ws.append(headers)

    for cell in ws[1]:
        cell.fill = contact_header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    for idx, c in enumerate(contacts, 1):
        company_name = c.company.name if c.company else "—"
        created_str = format_crm_datetime(c.created_at)

        row = [
            idx,
            c.id,
            c.full_name,
            c.job_title or "—",
            company_name,
            c.phone_number or "—",
            c.email or "—",
            created_str
        ]
        ws.append(row)

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.font = data_font
            cell.border = thin_border
            cell.alignment = right_align

    _auto_fit_columns(ws)


def build_companies_sheet(ws, companies: List[Company]):
    ws.sheet_view.rightToLeft = True
    header_fill, header_font, data_font, thin_border, center_align, right_align = _create_styles()
    comp_header_fill = PatternFill(start_color="4C1D95", end_color="4C1D95", fill_type="solid")

    headers = [
        "ردیف",
        "کد شرکت",
        "نام شرکت / برند",
        "حوزه فعالیت / صنعت",
        "تلفن تماس",
        "وب‌سایت",
        "آدرس و توضیحات",
        "تاریخ ایجاد"
    ]
    ws.append(headers)

    for cell in ws[1]:
        cell.fill = comp_header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    for idx, comp in enumerate(companies, 1):
        created_str = format_crm_datetime(comp.created_at)

        row = [
            idx,
            comp.id,
            comp.name,
            comp.industry or "—",
            comp.phone or "—",
            comp.website or "—",
            comp.address or "—",
            created_str
        ]
        ws.append(row)

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.font = data_font
            cell.border = thin_border
            cell.alignment = right_align

    _auto_fit_columns(ws)


def export_single_entity_to_excel(entity_type: str, db: Session) -> io.BytesIO:
    """Exports a single entity table to an Excel file buffer."""
    wb = openpyxl.Workbook()
    ws = wb.active

    if entity_type == "leads":
        ws.title = "سرنخ‌های فروش"
        leads = db.query(Lead).order_by(Lead.id.desc()).all()
        build_leads_sheet(ws, leads)
    elif entity_type == "opportunities":
        ws.title = "فرصت‌های تجاری"
        opps = db.query(Opportunity).order_by(Opportunity.id.desc()).all()
        build_opportunities_sheet(ws, opps)
    elif entity_type == "contacts":
        ws.title = "مخاطبان و اشخاص"
        contacts = db.query(Contact).order_by(Contact.id.desc()).all()
        build_contacts_sheet(ws, contacts)
    elif entity_type == "companies":
        ws.title = "شرکت‌ها و سازمان‌ها"
        companies = db.query(Company).order_by(Company.id.desc()).all()
        build_companies_sheet(ws, companies)
    else:
        raise ValueError(f"Unknown entity type: {entity_type}")

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def export_all_crm_to_excel(db: Session) -> io.BytesIO:
    """Exports all 4 CRM tables into a single consolidated multi-sheet Excel workbook."""
    wb = openpyxl.Workbook()

    # Sheet 1: Leads
    ws_leads = wb.active
    ws_leads.title = "سرنخ‌ها (Leads)"
    leads = db.query(Lead).order_by(Lead.id.desc()).all()
    build_leads_sheet(ws_leads, leads)

    # Sheet 2: Opportunities
    ws_opps = wb.create_sheet(title="فرصت‌های فروش (Opportunities)")
    opps = db.query(Opportunity).order_by(Opportunity.id.desc()).all()
    build_opportunities_sheet(ws_opps, opps)

    # Sheet 3: Contacts
    ws_contacts = wb.create_sheet(title="مخاطبان (Contacts)")
    contacts = db.query(Contact).order_by(Contact.id.desc()).all()
    build_contacts_sheet(ws_contacts, contacts)

    # Sheet 4: Companies
    ws_companies = wb.create_sheet(title="شرکت‌ها (Companies)")
    companies = db.query(Company).order_by(Company.id.desc()).all()
    build_companies_sheet(ws_companies, companies)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
