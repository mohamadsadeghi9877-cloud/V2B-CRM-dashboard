from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ExtractedData(BaseModel):
    # Personal & Contact Information
    full_name: Optional[str] = Field(None, description="نام و نام خانوادگی بازدیدکننده")
    phone_number: Optional[str] = Field(None, description="شماره تماس معتبر")
    email: Optional[str] = Field(None, description="آدرس ایمیل")
    company_name: Optional[str] = Field(None, description="نام شرکت یا سازمان")
    job_title: Optional[str] = Field(None, description="سمت شغلی")

    # Project Inquiries & Additional Lead Insights
    project_description: Optional[str] = Field(None, description="شرح نیازمندی، ایده، سفارش یا پروژه درخواستی")
    field_of_interest: Optional[str] = Field(None, description="حوزه علاقه‌مندی یا محصول مورد نظر در غرفه")
    estimated_budget: Optional[str] = Field(None, description="بودجه تخمینی یا مقیاس مالی پروژه")
    timeline: Optional[str] = Field(None, description="زمان‌بندی یا فوریت اجرای پروژه")
    notes: Optional[str] = Field(None, description="سایر نکات مهم، توافقات اولیه یا جزئیات پیگیری برای تیم فروش")

    @field_validator("*", mode="before")
    @classmethod
    def coerce_to_string(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


class LLMResponse(BaseModel):
    spoken_response: str = Field(..., description="متن پاسخ برای پخش صوتی به کاربر")
    extracted_data: ExtractedData = Field(default_factory=ExtractedData, description="داده‌های استخراج‌شده از نوبت فعلی")
    is_off_topic: bool = Field(False, description="آیا ورودی کاربر خارج از موضوع یا شوخی بود")
    conversation_complete: bool = Field(False, description="آیا گفتگو به پایان رسیده و اطلاعات تکمیل شد")


class ChatMessage(BaseModel):
    role: str = Field(..., description="نقش: system, user, assistant")
    content: str = Field(..., description="محتوای پیام")


class AgentTurnResult(BaseModel):
    transcript: str
    spoken_response: str
    extracted_data: ExtractedData
    form_data: ExtractedData
    is_off_topic: bool
    conversation_complete: bool
    audio_base64: Optional[str] = None
