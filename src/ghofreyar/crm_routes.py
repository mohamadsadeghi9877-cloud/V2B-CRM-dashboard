"""
CRM REST API Endpoints (FastAPI Router)
Full CRUD operations for Leads, Contacts, Companies, Opportunities,
and Excel exports.
"""

from typing import List, Optional
import re
import urllib.parse
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ghofreyar.crm_database import get_db
from ghofreyar.crm_models import Company, Contact, Lead, Opportunity
from ghofreyar.crm_schemas import (
    CompanyCreate, CompanyUpdate, CompanyOut,
    ContactCreate, ContactUpdate, ContactOut,
    LeadCreate, LeadUpdate, LeadOut, LeadUpdateStatus,
    OpportunityCreate, OpportunityUpdate, OpportunityUpdateStage, OpportunityOut, LeadConvertRequest,
    QuickLeadCaptureRequest
)
from ghofreyar.crm_export import export_single_entity_to_excel, export_all_crm_to_excel

router = APIRouter(prefix="/api/crm", tags=["CRM"])


# Pipeline stage to probability mapping (استاندارد بین‌المللی پایپ‌لاین معامله)
STAGE_PROBABILITIES = {
    "Requirement_Analysis": 20,
    "Proposal": 60,
    "Negotiation": 80,
    "Closed_Won": 100,
    "Closed_Lost": 0,
    # سازگاری با مراحل قبلی
    "Prospecting": 20,
    "Qualification": 30
}


# ==========================================
# 1. Quick Capture (ثبت جامع در یک مرحله)
# ==========================================

@router.post("/quick-capture", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def quick_lead_capture(req: QuickLeadCaptureRequest, db: Session = Depends(get_db)):
    """
    ثبت همزمان شرکت، مخاطب و لید در یک مرحله.
    ایده‌آل برای ذخیره مستقیم لیدهای نمایشگاهی یا ورودی ایجنت هوش مصنوعی.
    """
    # 1. مدیریت یا ایجاد شرکت
    company = None
    if req.company_name and req.company_name.strip():
        comp_name = req.company_name.strip()
        company = db.query(Company).filter(Company.name == comp_name).first()
        if not company:
            company = Company(name=comp_name)
            db.add(company)
            db.flush()

    # 2. مدیریت یا ایجاد مخاطب (جستجو بر اساس شماره همراه برای جلوگیری از مخاطب تکراری در صورت معتبر بودن شماره)
    phone = req.phone_number.strip() if req.phone_number else ""
    is_valid_phone = bool(phone and phone not in ["ثبت‌نشده", "نامشخص", "-", "—"])

    contact = None
    if is_valid_phone:
        contact = db.query(Contact).filter(Contact.phone_number == phone).first()

    if not contact:
        contact = Contact(
            full_name=req.full_name.strip() if req.full_name else "بازدیدکننده بدون نام",
            phone_number=phone if is_valid_phone else "ثبت‌نشده",
            email=req.email.strip() if req.email else None,
            job_title=req.job_title.strip() if req.job_title else None,
            company_id=company.id if company else None
        )
        db.add(contact)
        db.flush()
    else:
        # به‌روزرسانی سمت، ایمیل یا شرکت در صورت نیاز
        if company and not contact.company_id:
            contact.company_id = company.id
        if req.job_title and not contact.job_title:
            contact.job_title = req.job_title.strip()
        if req.email and not contact.email:
            contact.email = req.email.strip()
        if req.full_name and (contact.full_name in ["بازدیدکننده ناشناس", "بازدیدکننده بدون نام"] or not contact.full_name):
            contact.full_name = req.full_name.strip()

    # 3. بررسی وجود درخواست تجاری مشخص
    # طبق منطق استاندارد فروش، تنها در صورتی فرصت تجاری (Opportunity) ایجاد می‌شود که
    # بازدیدکننده یک درخواست، پروژه، حوزه علاقه‌مندی یا بودجه مطرح کرده باشد.
    # در غیر این صورت (صرفاً معرفی، تبادل شماره یا کارت ویزیت)، فقط ۳ شیت اول پر می‌شوند.
    has_specific_request = bool(
        (req.project_title and req.project_title.strip() and req.project_title.strip() not in [
            "درخواست عمومی بازدیدکننده غرفه", "ارتباط و مذاکره تجاری", "ارتباط و مذاکره اولیه", "آشنایی اولیه", "بازدید از غرفه", "معرفی", "کارت ویزیت", "—", "-"
        ])
        or (req.field_of_interest and req.field_of_interest.strip())
        or (req.estimated_budget and req.estimated_budget.strip())
    )

    lead_title = req.project_title.strip() if (req.project_title and req.project_title.strip()) else ""
    lead = Lead(
        title=lead_title,
        field_of_interest=req.field_of_interest.strip() if req.field_of_interest else None,
        estimated_budget=req.estimated_budget.strip() if req.estimated_budget else None,
        timeline=req.timeline.strip() if req.timeline else None,
        notes=req.notes.strip() if req.notes else None,
        temperature=req.temperature or ("Warm" if has_specific_request else "Cold"),
        status="New",
        contact_id=contact.id,
        company_id=company.id if company else None
    )
    db.add(lead)
    db.flush()

    # 4. ایجاد فرصت تجاری (Opportunity) صرفاً در صورت وجود درخواست مشخص
    if has_specific_request:
        opp_amount = 0.0
        if req.estimated_budget:
            digits = re.findall(r"\d+", req.estimated_budget)
            if digits:
                try:
                    raw_num = float(digits[0])
                    if "میلیارد" in req.estimated_budget:
                        opp_amount = raw_num * 1_000_000_000
                    elif "میلیون" in req.estimated_budget:
                        opp_amount = raw_num * 1_000_000
                    else:
                        opp_amount = raw_num
                except Exception:
                    opp_amount = 0.0

        opp = Opportunity(
            title=f"معامله {lead_title or req.field_of_interest or 'درخواست مشتری'} - {contact.full_name}",
            company_id=company.id if company else None,
            contact_id=contact.id,
            lead_id=lead.id,
            amount=opp_amount,
            stage="Requirement_Analysis",
            probability=20,
            expected_close_date=req.timeline,
            priority="High" if req.temperature == "Hot" else "Medium",
            deal_type="مشتری جدید",
            notes=f"ثبت خودکار از سامانه CRM پیرو درخواست مشتری. شرح: {req.project_title or req.field_of_interest or 'مذاکره اولیه'} | بودجه: {req.estimated_budget or 'نامشخص'}"
        )
        db.add(opp)

    db.commit()
    db.refresh(lead)

    return lead


# ==========================================
# 2. Leads Endpoints (مدیریت سرنخ‌ها)
# ==========================================

@router.get("/leads", response_model=List[LeadOut])
def list_leads(
    status_filter: Optional[str] = Query(None, alias="status", description="فیلتر بر اساس وضعیت"),
    temperature_filter: Optional[str] = Query(None, alias="temperature", description="فیلتر بر اساس داغ/گرم/سرد بودن"),
    db: Session = Depends(get_db)
):
    """لیست تمامی سرنخ‌های ثبت‌شده با قابلیت فیلتر بر اساس وضعیت و درجه حرارت"""
    query = db.query(Lead)
    if status_filter:
        query = query.filter(Lead.status == status_filter)
    if temperature_filter:
        query = query.filter(Lead.temperature == temperature_filter)
    
    return query.order_by(Lead.created_at.desc()).all()


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """دریافت جزئیات کامل یک لید به همراه اطلاعات مخاطب و شرکت"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="لید مورد نظر یافت نشد")
    return lead


@router.patch("/leads/{lead_id}/status", response_model=LeadOut)
def update_lead_status(lead_id: int, update_data: LeadUpdateStatus, db: Session = Depends(get_db)):
    """به‌روزرسانی وضعیت پیگیری یا یادداشت‌های لید همراه با تبدیل خودکار به فرصت"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="لید مورد نظر یافت نشد")

    lead.status = update_data.status
    if update_data.notes:
        existing = lead.notes or ""
        lead.notes = f"{existing}\n[پیگیری]: {update_data.notes}".strip()

    # در صورت تغییر وضعیت به «تبدیل شده به فرصت»، خودکار به شیت فرصت اضافه شود
    if update_data.status in ("Converted", "Qualified"):
        existing_opp = db.query(Opportunity).filter(Opportunity.lead_id == lead.id).first()
        if not existing_opp:
            amount = 0.0
            if lead.estimated_budget:
                norm_budget = lead.estimated_budget.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
                num_match = re.search(r"(\d+(?:\.\d+)?)", norm_budget.replace(",", ""))
                if num_match:
                    val = float(num_match.group(1))
                    if "میلیون" in norm_budget:
                        val *= 1_000_000
                    elif "میلیارد" in norm_budget:
                        val *= 1_000_000_000
                    amount = val

            contact_name = lead.contact.full_name if lead.contact else "مخاطب"
            opp = Opportunity(
                title=f"معامله {lead.title} - {contact_name}",
                company_id=lead.company_id,
                contact_id=lead.contact_id,
                lead_id=lead.id,
                amount=amount,
                stage="Requirement_Analysis",
                probability=20,
                expected_close_date=lead.timeline,
                priority="High" if lead.temperature == "Hot" else "Medium",
                deal_type="مشتری جدید",
                notes=f"تبدیل خودکار از سرنخ. نیازمندی: {lead.title} | {lead.notes or ''}"
            )
            db.add(opp)

    db.commit()
    db.refresh(lead)
    return lead


@router.post("/leads", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead(lead_in: LeadCreate, db: Session = Depends(get_db)):
    """ایجاد یک لید مستقیم متصل به مخاطب موجود"""
    contact = db.query(Contact).filter(Contact.id == lead_in.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="مخاطب انتخاب‌شده یافت نشد")

    lead = Lead(
        contact_id=lead_in.contact_id,
        company_id=contact.company_id,
        title=lead_in.title.strip() if (lead_in.title and lead_in.title.strip()) else "",
        field_of_interest=lead_in.field_of_interest,
        estimated_budget=lead_in.estimated_budget,
        timeline=lead_in.timeline,
        notes=lead_in.notes,
        temperature=lead_in.temperature,
        status="New"
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.put("/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, lead_in: LeadUpdate, db: Session = Depends(get_db)):
    """ویرایش کامل مشخصات یک سرنخ"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="لید مورد نظر یافت نشد")

    data = lead_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(lead, key, value)

    # تبدیل خودکار در صورت تغییر وضعیت به Converted یا Qualified
    if lead.status in ("Converted", "Qualified"):
        existing_opp = db.query(Opportunity).filter(Opportunity.lead_id == lead.id).first()
        if not existing_opp:
            amount = 0.0
            if lead.estimated_budget:
                norm_budget = lead.estimated_budget.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
                num_match = re.search(r"(\d+(?:\.\d+)?)", norm_budget.replace(",", ""))
                if num_match:
                    val = float(num_match.group(1))
                    if "میلیون" in norm_budget:
                        val *= 1_000_000
                    elif "میلیارد" in norm_budget:
                        val *= 1_000_000_000
                    amount = val

            contact_name = lead.contact.full_name if lead.contact else "مخاطب"
            opp = Opportunity(
                title=f"معامله {lead.title} - {contact_name}",
                company_id=lead.company_id,
                contact_id=lead.contact_id,
                lead_id=lead.id,
                amount=amount,
                stage="Requirement_Analysis",
                probability=20,
                expected_close_date=lead.timeline,
                priority="High" if lead.temperature == "Hot" else "Medium",
                deal_type="مشتری جدید",
                notes=f"تبدیل خودکار از سرنخ. نیازمندی: {lead.title} | {lead.notes or ''}"
            )
            db.add(opp)

    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    """حذف یک لید از سیستم"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="لید مورد نظر یافت نشد")
    db.delete(lead)
    db.commit()
    return None


# ==========================================
# 3. Contacts Endpoints (مدیریت مخاطبان)
# ==========================================

@router.get("/contacts", response_model=List[ContactOut])
def list_contacts(db: Session = Depends(get_db)):
    """لیست تمامی مخاطبان ثبت‌شده"""
    return db.query(Contact).order_by(Contact.created_at.desc()).all()


@router.get("/contacts/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """دریافت مشخصات یک مخاطب خاص"""
    c = db.query(Contact).filter(Contact.id == contact_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="مخاطب یافت نشد")
    return c


@router.post("/contacts", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(contact_in: ContactCreate, db: Session = Depends(get_db)):
    """ثبت مخاطب و شخص حقیقی جدید"""
    existing = db.query(Contact).filter(Contact.phone_number == contact_in.phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="مخاطبی با این شماره تماس قبلاً ثبت شده است")

    contact = Contact(**contact_in.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.put("/contacts/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, contact_in: ContactUpdate, db: Session = Depends(get_db)):
    """ویرایش اطلاعات مخاطب"""
    c = db.query(Contact).filter(Contact.id == contact_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="مخاطب یافت نشد")

    data = contact_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(c, key, value)

    db.commit()
    db.refresh(c)
    return c


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    """حذف مخاطب"""
    c = db.query(Contact).filter(Contact.id == contact_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="مخاطب یافت نشد")
    db.delete(c)
    db.commit()
    return None


# ==========================================
# 4. Companies Endpoints (مدیریت شرکت‌ها)
# ==========================================

@router.get("/companies", response_model=List[CompanyOut])
def list_companies(db: Session = Depends(get_db)):
    """لیست تمامی شرکت‌های ثبت‌شده"""
    return db.query(Company).order_by(Company.created_at.desc()).all()


@router.get("/companies/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, db: Session = Depends(get_db)):
    """دریافت اطلاعات شرکت خاص"""
    comp = db.query(Company).filter(Company.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="شرکت یافت نشد")
    return comp


@router.post("/companies", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(comp_in: CompanyCreate, db: Session = Depends(get_db)):
    """افزودن شرکت یا برند تجاری جدید"""
    existing = db.query(Company).filter(Company.name == comp_in.name.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="شرکتی با این نام قبلاً ثبت شده است")

    company = Company(**comp_in.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.put("/companies/{company_id}", response_model=CompanyOut)
def update_company(company_id: int, comp_in: CompanyUpdate, db: Session = Depends(get_db)):
    """ویرایش مشخصات شرکت"""
    comp = db.query(Company).filter(Company.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="شرکت یافت نشد")

    data = comp_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(comp, key, value)

    db.commit()
    db.refresh(comp)
    return comp


@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company_id: int, db: Session = Depends(get_db)):
    """حذف شرکت"""
    comp = db.query(Company).filter(Company.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="شرکت یافت نشد")
    db.delete(comp)
    db.commit()
    return None


# ==========================================
# 5. Opportunities Endpoints (مدیریت پایپ‌لاین و فرصت‌های فروش)
# ==========================================

@router.get("/opportunities", response_model=List[OpportunityOut])
def list_opportunities(
    stage_filter: Optional[str] = Query(None, alias="stage", description="فیلتر بر اساس مرحله فروش"),
    company_id: Optional[int] = Query(None, description="فیلتر بر اساس شرکت"),
    contact_id: Optional[int] = Query(None, description="فیلتر بر اساس مخاطب"),
    db: Session = Depends(get_db)
):
    """لیست فرصت‌های تجاری و فروش با امکان فیلتر مرحله، شرکت یا مخاطب"""
    query = db.query(Opportunity)
    if stage_filter:
        query = query.filter(Opportunity.stage == stage_filter)
    if company_id:
        query = query.filter(Opportunity.company_id == company_id)
    if contact_id:
        query = query.filter(Opportunity.contact_id == contact_id)
    return query.order_by(Opportunity.created_at.desc()).all()


@router.get("/opportunities/stats")
def get_opportunity_stats(db: Session = Depends(get_db)):
    """آمار و شاخص‌های کلیدی پایپ‌لاین فروش (KPIs)"""
    all_opps = db.query(Opportunity).all()
    total_count = len(all_opps)
    total_value = sum(o.amount or 0.0 for o in all_opps)

    open_opps = [o for o in all_opps if o.stage not in ("Closed_Won", "Closed_Lost")]
    open_count = len(open_opps)
    open_value = sum(o.amount or 0.0 for o in open_opps)

    won_opps = [o for o in all_opps if o.stage == "Closed_Won"]
    won_count = len(won_opps)
    won_value = sum(o.amount or 0.0 for o in won_opps)

    closed_opps = [o for o in all_opps if o.stage in ("Closed_Won", "Closed_Lost")]
    win_rate = round((won_count / len(closed_opps)) * 100, 1) if closed_opps else 0.0

    by_stage = {}
    for stage_key in ("Requirement_Analysis", "Proposal", "Negotiation", "Closed_Won", "Closed_Lost"):
        stage_list = [o for o in all_opps if o.stage == stage_key]
        if stage_key == "Requirement_Analysis":
            stage_list += [o for o in all_opps if o.stage in ("Prospecting", "Qualification")]
        by_stage[stage_key] = {
            "count": len(stage_list),
            "total_amount": sum(o.amount or 0.0 for o in stage_list)
        }

    return {
        "total_count": total_count,
        "total_value": total_value,
        "open_count": open_count,
        "open_value": open_value,
        "won_count": won_count,
        "won_value": won_value,
        "win_rate": win_rate,
        "by_stage": by_stage
    }


@router.get("/opportunities/{opp_id}", response_model=OpportunityOut)
def get_opportunity(opp_id: int, db: Session = Depends(get_db)):
    """دریافت جزئیات کامل یک فرصت تجاری"""
    opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="فرصت تجاری مورد نظر یافت نشد")
    return opp


@router.post("/opportunities", response_model=OpportunityOut, status_code=status.HTTP_201_CREATED)
def create_opportunity(opp_in: OpportunityCreate, db: Session = Depends(get_db)):
    """ایجاد دستی فرصت تجاری جدید"""
    data = opp_in.model_dump()
    if data.get("probability") is None:
        data["probability"] = STAGE_PROBABILITIES.get(data.get("stage", "Prospecting"), 10)
    opp = Opportunity(**data)
    db.add(opp)
    db.commit()
    db.refresh(opp)
    return opp


@router.put("/opportunities/{opp_id}", response_model=OpportunityOut)
def update_opportunity(opp_id: int, update_in: OpportunityUpdate, db: Session = Depends(get_db)):
    """ویرایش کامل اطلاعات یک فرصت تجاری"""
    opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="فرصت تجاری مورد نظر یافت نشد")

    data = update_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        if value is not None or key in ("company_id", "contact_id", "lead_id", "expected_close_date", "notes"):
            setattr(opp, key, value)

    if "stage" in data and ("probability" not in data or data["probability"] is None):
        opp.probability = STAGE_PROBABILITIES.get(opp.stage, opp.probability)

    db.commit()
    db.refresh(opp)
    return opp


@router.patch("/opportunities/{opp_id}/stage", response_model=OpportunityOut)
def update_opportunity_stage(opp_id: int, stage_in: OpportunityUpdateStage, db: Session = Depends(get_db)):
    """تغییر سریع مرحله پایپ‌لاین فرصت فروش"""
    opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="فرصت تجاری مورد نظر یافت نشد")

    opp.stage = stage_in.stage
    if stage_in.probability is not None:
        opp.probability = stage_in.probability
    else:
        opp.probability = STAGE_PROBABILITIES.get(stage_in.stage, opp.probability)

    if stage_in.notes:
        existing = opp.notes or ""
        opp.notes = f"{existing}\n[تغییر مرحله]: {stage_in.notes}".strip()

    db.commit()
    db.refresh(opp)
    return opp


@router.delete("/opportunities/{opp_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opportunity(opp_id: int, db: Session = Depends(get_db)):
    """حذف یک فرصت تجاری"""
    opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="فرصت تجاری مورد نظر یافت نشد")
    db.delete(opp)
    db.commit()
    return None


# ==========================================
# 6. Lead Conversion (تبدیل سرنخ به فرصت)
# ==========================================

@router.post("/leads/{lead_id}/convert", response_model=OpportunityOut, status_code=status.HTTP_201_CREATED)
def convert_lead_to_opportunity(lead_id: int, req: LeadConvertRequest, db: Session = Depends(get_db)):
    """
    تبدیل سرنخ (Lead) به فرصت فروش (Opportunity)
    انتقال مشخصات نیاز، مخاطب و شرکت به معامله جدید و ارتقای وضعیت لید به Qualified
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="سرنخ تجاری مورد نظر یافت نشد")

    amount = req.amount or 0.0
    if not amount and lead.estimated_budget:
        import re
        norm_budget = lead.estimated_budget.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        num_match = re.search(r"(\d+(?:\.\d+)?)", norm_budget.replace(",", ""))
        if num_match:
            val = float(num_match.group(1))
            if "میلیون" in norm_budget:
                val *= 1_000_000
            elif "میلیارد" in norm_budget:
                val *= 1_000_000_000
            amount = val

    # بررسی اینکه آیا قبلاً فرصتی برای این لید ساخته شده است یا خیر
    existing_opp = db.query(Opportunity).filter(Opportunity.lead_id == lead.id).first()
    if existing_opp:
        if req.opportunity_title and req.opportunity_title.strip():
            existing_opp.title = req.opportunity_title.strip()
        if req.stage:
            existing_opp.stage = req.stage
            existing_opp.probability = req.probability if req.probability is not None else STAGE_PROBABILITIES.get(req.stage, existing_opp.probability)
        if req.expected_close_date:
            existing_opp.expected_close_date = req.expected_close_date
        if amount:
            existing_opp.amount = amount
        lead.status = "Converted"
        db.commit()
        db.refresh(existing_opp)
        return existing_opp

    opp_title = req.opportunity_title.strip() if req.opportunity_title and req.opportunity_title.strip() else f"فرصت: {lead.title}"
    stage = req.stage or "Requirement_Analysis"
    prob = req.probability if req.probability is not None else STAGE_PROBABILITIES.get(stage, 20)

    opp = Opportunity(
        title=opp_title,
        company_id=lead.company_id,
        contact_id=lead.contact_id,
        lead_id=lead.id,
        amount=amount,
        stage=stage,
        probability=prob,
        expected_close_date=req.expected_close_date or lead.timeline,
        deal_type="مشتری جدید",
        notes=req.notes or lead.notes
    )
    db.add(opp)

    # به‌روزرسانی وضعیت لید به Converted
    lead.status = "Converted"
    if not lead.notes:
        lead.notes = "تبدیل‌شده به فرصت فروش"
    else:
        lead.notes += " (تبدیل‌شده به فرصت فروش)"

    db.commit()
    db.refresh(opp)
    return opp


# ==========================================
# 7. Excel Export Endpoints (خروجی شیت‌های اکسل)
# ==========================================

@router.get("/export/leads")
def export_leads_excel(db: Session = Depends(get_db)):
    """خروجی فایل اکسل از جدول سرنخ‌ها و نیازها"""
    buffer = export_single_entity_to_excel("leads", db)
    filename = f"CRM_Leads_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"
    }
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )


@router.get("/export/opportunities")
def export_opportunities_excel(db: Session = Depends(get_db)):
    """خروجی فایل اکسل از جدول فرصت‌های تجاری و فروش"""
    buffer = export_single_entity_to_excel("opportunities", db)
    filename = f"CRM_Opportunities_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"
    }
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )


@router.get("/export/contacts")
def export_contacts_excel(db: Session = Depends(get_db)):
    """خروجی فایل اکسل از جدول اشخاص و مخاطبان"""
    buffer = export_single_entity_to_excel("contacts", db)
    filename = f"CRM_Contacts_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"
    }
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )


@router.get("/export/companies")
def export_companies_excel(db: Session = Depends(get_db)):
    """خروجی فایل اکسل از جدول شرکت‌ها و سازمان‌ها"""
    buffer = export_single_entity_to_excel("companies", db)
    filename = f"CRM_Companies_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"
    }
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )


@router.get("/export/all")
def export_all_crm_excel(db: Session = Depends(get_db)):
    """خروجی فایل جامع اکسل شامل ۴ شیت کامل از کلیه اطلاعات CRM"""
    buffer = export_all_crm_to_excel(db)
    filename = f"CRM_Complete_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"
    }
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )
