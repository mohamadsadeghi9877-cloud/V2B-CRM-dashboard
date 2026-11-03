@echo off
chcp 65001 >nul
title سامانه هوشمند مدیریت ارتباط با مشتریان (CRM)
color 0B

echo ========================================================
echo   🚀 در حال راه‌اندازی سامانه هوشمند مدیریت ارتباط با مشتریان (CRM)...
echo ========================================================
echo.
echo  📍 پورت سرور: http://localhost:8090
echo  ⏳ لطفاً چند لحظه صبر کنید تا سرور آماده شود...
echo.

:: رفتن به مسیر همین فایل
cd /d "%~dp0"

:: تنظیم محیط اجرای پایتون و متغیرهای لازم
set PYTHONIOENCODING=utf-8

:: بررسی و اجرای خودکار سرور محلی هوش مصنوعی (Qwen روی کارت گرافیک)
powershell -Command "if (-not (Get-NetTCPConnection -LocalPort 8888 -State Listen -ErrorAction SilentlyContinue)) { Start-Process -FilePath 'C:\Users\m.sadeghi\.unsloth\llama.cpp\build\bin\Release\llama-server.exe' -ArgumentList '-m \"C:\Users\m.sadeghi\.cache\huggingface\hub\models--unsloth--Qwen3.5-4B-MTP-GGUF\snapshots\86835bf9949e4d14d6860f7910b1340ad4f271a9\Qwen3.5-4B-UD-IQ2_M.gguf\" --host 127.0.0.1 --port 8888 -ngl 99 -c 2048 --parallel 1 --flash-attn on --reasoning off --reasoning-budget 0' -WindowStyle Hidden }"

:: باز کردن مرورگر پس از ۳ ثانیه در پس‌زمینه
start /b cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8090"

:: اجرای سرور با ابزار uv
python -m uv run uvicorn ghofreyar.app:app --host 0.0.0.0 --port 8090 --reload

pause
