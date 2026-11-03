"""
CRM Data Schemas (Pydantic Models)
Defines request validation and response formatting for Companies, Contacts, and Leads.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==========================================
# 1. Company Schemas (شرکت‌ها)
# ==========================================

class CompanyBase(BaseModel):
    name: str = Field(..., description="نام شرکت یا برند تجاری")
    industry: Optional[str] = Field(None, description="صنعت / حوزه فعالیت")
    website: Optional[str] = Field(None, description="وب‌سایت")
    phone: Optional[str] = Field(None, description="تلفن تماس شرکت")
    address: Optional[str] = Field(None, description="آدرس یا شهر")


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, description="نام شرکت یا برند تجاری")
    industry: Optional[str] = Field(None, description="صنعت / حوزه فعالیت")
    website: Optional[str] = Field(None, description="وب‌سایت")
    phone: Optional[str] = Field(None, description="تلفن تماس شرکت")
    address: Optional[str] = Field(None, description="آدرس یا شهر")


class CompanyOut(CompanyBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# 2. Contact Schemas (مخاطبان)
# ==========================================

class ContactBase(BaseModel):
    full_name: str = Field(..., description="نام و نام خانوادگی مخاطب")
    phone_number: str = Field(..., description="شماره همراه / تماس")
    email: Optional[str] = Field(None, description="آدرس ایمیل")
    job_title: Optional[str] = Field(None, description="سمت شغلی")
    company_id: Optional[int] = Field(None, description="شناسه شرکت مربوطه")


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    full_name: Optional[str] = Field(None, description="نام و نام خانوادگی مخاطب")
    phone_number: Optional[str] = Field(None, description="شماره همراه / تماس")
    email: Optional[str] = Field(None, description="آدرس ایمیل")
    job_title: Optional[str] = Field(None, description="سمت شغلی")
    company_id: Optional[int] = Field(None, description="شناسه شرکت مربوطه")


class ContactOut(ContactBase):
    id: int
    created_at: datetime
    company: Optional[CompanyOut] = None

    class Config:
        from_attributes = True


# ==========================================
# 3. Lead Schemas (سرنخ‌های تجاری)
# ==========================================

class LeadBase(BaseModel):
    title: Optional[str] = Field(None, description="عنوان خلاصه نیاز یا پروژه")
    field_of_interest: Optional[str] = Field(None, description="حوزه علاقه‌مندی یا خدمت مورد نظر")
    status: Optional[str] = Field("New", description="وضعیت: New, In_Progress, Converted, Disqualified")
    temperature: Optional[str] = Field("Warm", description="درجه حرارت: Hot, Warm, Cold")
    estimated_budget: Optional[str] = Field(None, description="بودجه تخمینی کارفرما")
    timeline: Optional[str] = Field(None, description="بازه زمانی اجرای پروژه")
    source: Optional[str] = Field("نمایشگاه", description="مبدأ ورودی لید")
    notes: Optional[str] = Field(None, description="یادداشت‌های فنی یا بازرگانی")
    contact_id: int = Field(..., description="شناسه شخص صاحب لید")
    company_id: Optional[int] = Field(None, description="شناسه شرکت مربوطه")


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    title: Optional[str] = Field(None, description="عنوان خلاصه نیاز یا پروژه")
    field_of_interest: Optional[str] = Field(None, description="حوزه علاقه‌مندی")
    status: Optional[str] = Field(None, description="تغییر وضعیت")
    temperature: Optional[str] = Field(None, description="تغییر درجه اهمیت")
    estimated_budget: Optional[str] = Field(None, description="بودجه تخمینی")
    timeline: Optional[str] = Field(None, description="بازه زمانی")
    notes: Optional[str] = Field(None, description="یادداشت‌ها")
    contact_id: Optional[int] = Field(None, description="تغییر مخاطب صاحب لید")
    company_id: Optional[int] = Field(None, description="تغییر شرکت")


class LeadUpdateStatus(BaseModel):
    status: Optional[str] = Field(None, description="تغییر وضعیت لید")
    temperature: Optional[str] = Field(None, description="تغییر درجه اهمیت")
    notes: Optional[str] = Field(None, description="یادداشت تکمیلی پیگیری")



class LeadOut(LeadBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    contact: Optional[ContactOut] = None
    company: Optional[CompanyOut] = None

    class Config:
        from_attributes = True


# ==========================================
# 4. Opportunity Schemas (فرصت‌های تجاری و فروش)
# ==========================================

class OpportunityBase(BaseModel):
    title: str = Field(..., description="عنوان فرصت فروش یا نام معامله")
    company_id: Optional[int] = Field(None, description="شناسه شرکت طرف معامله")
    contact_id: Optional[int] = Field(None, description="شناسه مخاطب تصمیم‌گیرنده")
    lead_id: Optional[int] = Field(None, description="شناسه سرنخ مبدا")
    amount: Optional[float] = Field(0.0, description="ارزش مالی معامله به تومان")
    stage: Optional[str] = Field("Requirement_Analysis", description="مرحله پایپ‌لاین: Requirement_Analysis, Proposal, Negotiation, Closed_Won, Closed_Lost")
    probability: Optional[int] = Field(None, description="درصد احتمال موفقیت (۰ تا ۱۰۰)")
    expected_close_date: Optional[str] = Field(None, description="تاریخ تخمینی بستن معامله")
    priority: Optional[str] = Field("Medium", description="درجه اهمیت: High, Medium, Low")
    deal_type: Optional[str] = Field("مشتری جدید", description="نوع معامله")
    notes: Optional[str] = Field(None, description="شرح مذاکرات یا یادداشت‌ها")


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    company_id: Optional[int] = None
    contact_id: Optional[int] = None
    lead_id: Optional[int] = None
    amount: Optional[float] = None
    stage: Optional[str] = None
    probability: Optional[int] = None
    expected_close_date: Optional[str] = None
    priority: Optional[str] = None
    deal_type: Optional[str] = None
    notes: Optional[str] = None


class OpportunityUpdateStage(BaseModel):
    stage: str = Field(..., description="مرحله جدید فرصت فروش")
    probability: Optional[int] = Field(None, description="درصد احتمال موفقیت جدید")
    notes: Optional[str] = Field(None, description="یادداشت تکمیلی تغییر مرحله")


class OpportunityOut(OpportunityBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    company: Optional[CompanyOut] = None
    contact: Optional[ContactOut] = None

    class Config:
        from_attributes = True


class LeadConvertRequest(BaseModel):
    """
    تبدیل سرنخ (Lead) به فرصت فروش (Opportunity)
    """
    opportunity_title: Optional[str] = Field(None, description="عنوان معامله (پیش‌فرض عنوان لید)")
    amount: Optional[float] = Field(0.0, description="ارزش مالی تخمینی به تومان")
    stage: Optional[str] = Field("Qualification", description="مرحله شروع پایپ‌لاین")
    probability: Optional[int] = Field(None, description="درصد احتمال موفقیت اولیه")
    expected_close_date: Optional[str] = Field(None, description="تاریخ تخمینی بستن قرارداد")
    notes: Optional[str] = Field(None, description="یادداشت‌های بیشتر")


# ==========================================
# 5. Quick Capture Schema (ثبت جامع در یک مرحله)
# ==========================================

class QuickLeadCaptureRequest(BaseModel):
    """
    برای ثبت همزمان شخص، شرکت و لید در یک مرحله (مثلاً از طرف ایجنت هوش مصنوعی یا فرم سریع غرفه)
    """
    full_name: str
    phone_number: str
    email: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    project_title: Optional[str] = None
    field_of_interest: Optional[str] = None
    estimated_budget: Optional[str] = None
    timeline: Optional[str] = None
    notes: Optional[str] = None
    temperature: Optional[str] = "Warm"

