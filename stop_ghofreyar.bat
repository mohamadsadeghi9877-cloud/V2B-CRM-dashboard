@echo off
chcp 65001 >nul
title خاموش کردن سامانه غرفه‌یار
color 0C

echo ========================================================
echo         🛑 در حال بستن و متوقف کردن سرور غرفه‌یار...
echo ========================================================
echo.

:: بستن پروسه‌های در حال گوش دادن به پورت ۸۰۹۰ و ۸۸۸۸
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8090') do (
    taskkill /f /pid %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8888') do (
    taskkill /f /pid %%a 2>nul
)

echo ✅ سرور غرفه‌یار با موفقیت متوقف شد.
echo.
timeout /t 3 >nul
