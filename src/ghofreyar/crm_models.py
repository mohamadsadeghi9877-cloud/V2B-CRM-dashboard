"""
CRM Database Models (SQLAlchemy ORM)
Architecture for Exhibition Booth CRM:
1. Company (Organizations / Enterprises)
2. Contact (Individual Decision Makers / Visitors)
3. Lead (Commercial Opportunities / Inquiries)
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Float
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Company(Base):
    """
    جدول شرکت‌ها و سازمان‌ها
    نگه‌داری مشخصات حقوقی سازمان‌هایی که مخاطب از طرف آن‌ها به غرفه آمده است.
    """
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False, index=True, doc="نام شرکت یا برند")
    industry = Column(String(100), nullable=True, doc="حوزه فعالیت / صنعت")
    website = Column(String(150), nullable=True, doc="وب‌سایت رسمی")
    phone = Column(String(50), nullable=True, doc="تلفن مرکزی شرکت")
    address = Column(String(250), nullable=True, doc="شهر / آدرس دفتر")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), doc="زمان ثبت شرکت")

    # روابط (یک شرکت می‌تواند چندین مخاطب، چندین لید و چندین فرصت داشته باشد)
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="company", cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.name}')>"


class Contact(Base):
    """
    جدول اشخاص و مخاطبان
    نگه‌داری اطلاعات هویتی و راه‌های تماس با فرد تصمیم‌گیرنده
    """
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, doc="شناسه شرکت مربوطه")
    
    full_name = Column(String(150), nullable=False, index=True, doc="نام و نام خانوادگی")
    phone_number = Column(String(30), nullable=False, index=True, doc="شماره همراه / تماس")
    email = Column(String(120), nullable=True, index=True, doc="ایمیل")
    job_title = Column(String(100), nullable=True, doc="سمت شغلی (مدیرعامل، مدیر فنی و...)")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), doc="زمان ثبت مخاطب")

    # روابط
    company = relationship("Company", back_populates="contacts")
    leads = relationship("Lead", back_populates="contact", cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="contact")

    def __repr__(self):
        return f"<Contact(id={self.id}, name='{self.full_name}', phone='{self.phone_number}')>"


class Lead(Base):
    """
    جدول سرنخ‌های تجاری (Leads)
    نگه‌داری فرصت‌های همکاری، نیاز پروژه، بودجه و وضعیت فروش
    """
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, doc="شناسه شخص صاحب لید")
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, doc="شناسه شرکت مرتبط")

    title = Column(String(200), nullable=True, doc="عنوان درخواست یا خلاصه پروژه")
    field_of_interest = Column(String(100), nullable=True, doc="دسته محصول یا خدمت مورد نظر")
    
    # وضعیت در پایپ‌لاین: New (جدید), In_Progress (در حال پیگیری), Qualified (واجد شرایط), Won (موفق), Lost (رد شده)
    status = Column(String(50), default="New", index=True, doc="وضعیت پیگیری فروش")
    
    # درجه حرارت: Hot (داغ), Warm (گرم), Cold (سرد)
    temperature = Column(String(20), default="Warm", index=True, doc="درجه اولویت و داغ بودن لید")
    
    estimated_budget = Column(String(100), nullable=True, doc="بودجه تخمینی اعلام‌شده")
    timeline = Column(String(100), nullable=True, doc="بازه زمانی و فوریت اجرای کار")
    source = Column(String(100), default="نمایشگاه", doc="مبدأ ورودی لید")
    notes = Column(Text, nullable=True, doc="یادداشت‌ها و جزئیات بیشتر")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), doc="زمان ثبت")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # روابط
    contact = relationship("Contact", back_populates="leads")
    company = relationship("Company", back_populates="leads")
    opportunities = relationship("Opportunity", back_populates="lead")

    def __repr__(self):
        return f"<Lead(id={self.id}, title='{self.title}', status='{self.status}')>"


class Opportunity(Base):
    """
    جدول فرصت‌های تجاری و فروش (Opportunities / Deals)
    نگه‌داری معاملات تجاری، ارزش قرارداد، مراحل پایپ‌لاین و درصد احتمال موفقیت
    """
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False, index=True, doc="عنوان فرصت فروش یا نام معامله")

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, doc="شناسه شرکت طرف معامله")
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, doc="شناسه مخاطب تصمیم‌گیرنده")
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, doc="شناسه سرنخ مبدا")

    amount = Column(Float, default=0.0, doc="ارزش مالی تخمینی معامله به تومان")
    
    # مراحل پایپ‌لاین فروش:
    # Prospecting (شناسایی اولیه) - ۱۰٪
    # Qualification (ارزیابی و نیازسنجی) - ۳۰٪
    # Proposal (ارائه پیش‌فاکتور / طرح پیشنهادی) - ۶۰٪
    # Negotiation (مذاکره نهایی و قیمت) - ۸۰٪
    # Closed_Won (بسته شده - موفق / عقد قرارداد) - ۱۰۰٪
    # Closed_Lost (بسته شده - ناموفق / رد شده) - ۰٪
    stage = Column(String(50), default="Prospecting", index=True, doc="مرحله فعلی در پایپ‌لاین فروش")
    probability = Column(Integer, default=10, doc="احتمال موفقیت معامله (درصد)")

    expected_close_date = Column(String(50), nullable=True, doc="تاریخ پیش‌بینی انعقاد قرارداد (مثلاً ۱۴۰۵/۰۹/۰۱)")
    priority = Column(String(20), default="Medium", doc="درجه اهمیت (High, Medium, Low)")
    deal_type = Column(String(50), default="مشتری جدید", doc="نوع معامله (مشتری جدید، ارتقای قرارداد، تمدید سالانه)")
    notes = Column(Text, nullable=True, doc="شرح مذاکرات، نیازمندی‌ها و شروط طرفین")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), doc="زمان ثبت فرصت")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # روابط
    company = relationship("Company", back_populates="opportunities")
    contact = relationship("Contact", back_populates="opportunities")
    lead = relationship("Lead", back_populates="opportunities")

    def __repr__(self):
        return f"<Opportunity(id={self.id}, title='{self.title}', amount={self.amount}, stage='{self.stage}')>"
