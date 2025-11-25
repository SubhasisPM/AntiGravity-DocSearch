@echo off
echo ========================================
echo DocSearch - API Key Setup
echo ========================================
echo.
echo This script will help you set up your API keys for the best experience.
echo You can use Google Gemini (Recommended/Free Tier) or OpenAI.
echo.

set /p GEMINI_KEY="Enter Google Gemini API Key (Press Enter to skip): "
set /p OPENAI_KEY="Enter OpenAI API Key (Press Enter to skip): "

echo.
echo Saving to .env file...

echo # DocSearch Configuration > .env
if not "%GEMINI_KEY%"=="" echo GEMINI_API_KEY=%GEMINI_KEY% >> .env
if not "%OPENAI_KEY%"=="" echo OPENAI_API_KEY=%OPENAI_KEY% >> .env

echo.
echo [OK] Configuration saved!
echo.
echo Please restart the application for changes to take effect.
echo.
pause
