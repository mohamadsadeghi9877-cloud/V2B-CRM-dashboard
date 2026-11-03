import re
import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from ghofreyar.models import LLMResponse, ExtractedData
from ghofreyar.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LLMResponseError(Exception):
    """Raised when the LLM response cannot be parsed into a valid LLMResponse."""
    pass


class LLMService:
    """Ollama-based LLM service for Persian booth assistant dialog and structured data extraction."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8888",
        model: str = "unsloth/Qwen3.5-4B-MTP-GGUF",
        api_key: Optional[str] = None,
        timeout_seconds: float = 60.0
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def parse_response(self, text: str) -> LLMResponse:
        """Parse raw text response from LLM into a validated LLMResponse object."""
        clean_text = (text or "").strip()
        if not clean_text:
            raise LLMResponseError("Empty response received from LLM.")

        # Strip markdown code blocks if present
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean_text, re.DOTALL)
        if json_match:
            raw_json_str = json_match.group(1).strip()
        else:
            # Fallback: find the first outer { ... } block
            brace_match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
            if brace_match:
                raw_json_str = brace_match.group(1).strip()
            else:
                raw_json_str = clean_text

        try:
            data = json.loads(raw_json_str)
        except json.JSONDecodeError:
            # Bracket & truncation healing
            healed = raw_json_str
            healed = re.sub(r',\s*"[^"]*"?\s*:?\s*[^,}]*$', '', healed).rstrip().rstrip(",")
            open_braces = healed.count("{") - healed.count("}")
            healed += "}" * max(0, open_braces)
            try:
                data = json.loads(healed)
            except Exception as e:
                logger.error(f"Failed to parse LLM response as JSON: {clean_text}")
                raise LLMResponseError(f"Invalid JSON from LLM: {e}") from e

        if not isinstance(data, dict):
            raise LLMResponseError("LLM output is not a JSON object.")

        try:
            return LLMResponse.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to validate LLM response schema: {e}")
            raise LLMResponseError(f"Schema validation failed: {e}") from e

    def generate_response(
        self,
        conversation_history: List[Dict[str, str]],
        temperature: float = 0.5
    ) -> LLMResponse:
        """Send conversation history to local LLM (Unsloth Desktop / LM Studio / Ollama)."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # 1. Try OpenAI-compatible endpoint (Unsloth AI Desktop, LM Studio, vLLM, llama.cpp)
        openai_endpoint = f"{self.base_url}/v1/chat/completions"
        openai_payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 320,
            "stream": False
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = httpx.post(openai_endpoint, json=openai_payload, headers=headers, timeout=self.timeout_seconds)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    raw_content = choices[0].get("message", {}).get("content", "")
                    return self.parse_response(raw_content)
            else:
                logger.warning(f"Unsloth endpoint returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Failed to connect to Unsloth /v1/chat/completions: {e}")

        # 2. Try Ollama native endpoint (/api/chat)
        ollama_endpoint = f"{self.base_url}/api/chat"
        ollama_payload = {
            "model": self.model,
            "messages": messages,
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature}
        }
        try:
            resp = httpx.post(ollama_endpoint, json=ollama_payload, timeout=self.timeout_seconds)
            if resp.status_code == 200:
                data = resp.json()
                raw_content = data.get("message", {}).get("content", "")
                return self.parse_response(raw_content)
        except Exception:
            pass

        # 3. Fallback heuristic when local model server is offline
        logger.warning(f"Local LLM not reachable at {self.base_url}. Using built-in exhibition dialog fallback.")
        return self._fallback_heuristic_response(conversation_history)

    def _fallback_heuristic_response(self, conversation_history: List[Dict[str, str]]) -> LLMResponse:
        """Heuristic Persian dialogue engine when local LLM is offline."""
        last_user_msg = ""
        for msg in reversed(conversation_history):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "").strip()
                break

        persian_digits = "۰۱۲۳۴۵۶۷۸۹"
        english_digits = "0123456789"
        digit_map = str.maketrans(persian_digits, english_digits)
        normalized_text = last_user_msg.translate(digit_map)

        # Off-topic checks
        if any(w in normalized_text for w in ["هوش مصنوعی هستی", "ربات هستی", "هوا چطوره", "فوتبال", "بتمن"]):
            return LLMResponse(
                spoken_response="بله! من دستیار هوشمند سامانه CRM هستم که برای ثبت اطلاعات و پروژه‌های شما اینجام. لطفاً نام و نام خانوادگیتون رو بفرمایید تا ثبت کنم.",
                extracted_data=ExtractedData(),
                is_off_topic=True,
                conversation_complete=False
            )

        if "123456" in normalized_text or "۱۲۳۴۵۶" in last_user_msg:
            return LLMResponse(
                spoken_response="چه شماره قشنگی! ولی من جدی می‌پرسم، شماره واقعیتون چیه؟ می‌خوام بعداً بتونیم باهاتون در تماس باشیم.",
                extracted_data=ExtractedData(),
                is_off_topic=True,
                conversation_complete=False
            )

        # Extract phone
        phone_match = re.search(r"(?:(?:\+?98)|0)?9\d{9}", normalized_text)
        found_phone = phone_match.group(0) if phone_match else None

        # Extract email
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", last_user_msg)
        found_email = email_match.group(0) if email_match else None

        # Extract name heuristics
        found_name = None
        name_m = re.search(r"(?:^|سلام|درود|من|اینجانب)\s*([آ-یa-zA-Z\s]{3,25}?)\s+از\s+شرکت", last_user_msg)
        if name_m:
            found_name = name_m.group(1).strip()
        if not found_name:
            name_m2 = re.search(r"(?:نام من|اسم من|من|اینجانب)\s+([آ-یa-zA-Z\s]{3,20}?)(?:\s+(?:هستم|از|با|سمت|کارشناس|مدیر))", last_user_msg)
            if name_m2:
                found_name = name_m2.group(1).strip()
        if not found_name and not found_phone and not found_email and not any(w in last_user_msg for w in ["پروژه", "شرکت", "میلیون", "تومان"]):
            name_clean = re.sub(r"(سلام|درود|من|هستم|اسمم|نامم|آقای|خانم)", "", last_user_msg).strip()
            name_tokens = name_clean.split()
            if 2 <= len(name_tokens) <= 4:
                found_name = " ".join(name_tokens)

        # Extract company heuristics
        found_company = None
        comp_m = re.search(r"از\s+شرکت\s+([آ-یa-zA-Z0-9\s]{2,30}?)(?:\s+(?:شماره|تلفن|همراه|با|سمت|برای|درخواست|$))", last_user_msg)
        if comp_m:
            found_company = comp_m.group(1).strip()
        elif "شرکت" in last_user_msg:
            comp_m2 = re.search(r"شرکت\s+([آ-یa-zA-Z0-9\s]{2,30}?)(?:\s+(?:شماره|تلفن|همراه|با|سمت|برای|درخواست|$))", last_user_msg)
            if comp_m2:
                found_company = comp_m2.group(1).strip()

        # Extract job title heuristics
        found_job_title = None
        title_m = re.search(r"سمت\s+([آ-یa-zA-Z\s]{2,25}?)(?:\s+(?:برای|شرکت|شماره|تلفن|با|و|درخواست|$))", last_user_msg)
        if title_m:
            found_job_title = title_m.group(1).strip()
        else:
            for t in ["کارشناس فروش", "مدیر فروش", "مدیر عامل", "مدیرعامل", "مدیر فنی", "مدیر بازرگانی", "کارشناس فنی", "مشاور"]:
                if t in last_user_msg:
                    found_job_title = t
                    break

        # Extract project inquiry heuristics
        found_project = None
        proj_m = re.search(r"برای\s+([آ-یa-zA-Z0-9\s]{3,40}?)\s+درخواست", last_user_msg)
        if proj_m:
            found_project = f"درخواست برای {proj_m.group(1).strip()}"
        elif any(w in last_user_msg for w in ["پروژه", "نیازمندی", "طراحی", "سفارش", "توسعه", "سیستم", "سامانه", "اپلیکیشن", "درخواست"]):
            found_project = last_user_msg

        # Extract field of interest
        found_interest = None
        int_m = re.search(r"(?:بحث|حوزه|موضوع|پروژه)\s+([آ-یa-zA-Z0-9\s\u200c]+?)\s+(?:علاقه داریم|علاقه‌مندیم|مایلیم)", last_user_msg)
        if int_m:
            found_interest = int_m.group(1).strip()

        # Extract budget heuristics
        found_budget = None
        if "بودجه" in last_user_msg:
            if any(w in last_user_msg for w in ["مشخص نیست", "معلوم نیست", "تقریبی", "نامشخص"]):
                found_budget = "نامشخص / در حال برآورد"
            else:
                b_m = re.search(r"(\d+[\s\w]*?(?:میلیون|میلیارد|تومان|ریال))", last_user_msg)
                found_budget = b_m.group(1) if b_m else "نامشخص"

        # Extract timeline heuristics
        found_timeline = None
        if any(w in last_user_msg for w in ["بازه زمانی", "زمان‌بندی", "زمانبندی", "مهلت"]):
            if any(w in last_user_msg for w in ["مشخص نیست", "معلوم نیست", "همین طور", "نامشخص"]):
                found_timeline = "نامشخص"
            else:
                t_m = re.search(r"(\d+[\s\w]*?(?:ماه|هفته|روز|سال))", last_user_msg)
                found_timeline = t_m.group(1) if t_m else "نامشخص"

        # Aggregate all extracted data simultaneously
        extracted = ExtractedData(
            full_name=found_name,
            phone_number=found_phone,
            email=found_email,
            company_name=found_company,
            job_title=found_job_title,
            project_description=found_project,
            field_of_interest=found_interest,
            estimated_budget=found_budget,
            timeline=found_timeline
        )

        has_data = any([found_name, found_phone, found_email, found_company, found_job_title, found_project, found_interest])

        # Spoken greeting / confirmation
        if found_name and (found_phone or found_company):
            spoken = f"با کمال میل، جناب {found_name}؛ تمامی مشخصات شما از شرکت {found_company or 'محترمتان'} با موفقیت ثبت شد."
        elif found_name:
            spoken = f"از آشنایی با شما خوشحالم جناب {found_name}! لطفاً شماره تماستون رو بفرمایید تا ثبت کنم."
        elif found_phone:
            spoken = "شماره تماس شما ثبت شد! لطفاً نام و شرکت خودتون رو هم بفرمایید."
        elif any(w in last_user_msg for w in ["سلام", "درود", "صبح بخیر", "عصر بخیر"]):
            spoken = "سلام! خوش آمدید. من دستیار هوشمند سامانه CRM هستم. ممکنه لطفاً خودتون و شرکتتون رو معرفی بفرمایید؟"
        else:
            spoken = "اطلاعات شما با دقت ثبت شد. آیا مورد دیگری هست که مایل باشید ثبت کنیم؟"

        return LLMResponse(
            spoken_response=spoken,
            extracted_data=extracted,
            is_off_topic=False,
            conversation_complete=False
        )

