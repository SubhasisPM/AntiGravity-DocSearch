@echo off
echo ========================================
echo DocSearch - GitHub Deployment Helper
echo ========================================
echo.

echo Step 1: Checking if Git is installed...
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [!] Git is not installed
    echo.
    echo Please choose one of these options:
    echo.
    echo Option A - Install Git:
    echo   1. Download from: https://git-scm.com/download/win
    echo   2. Install with default settings
    echo   3. Restart this script
    echo.
    echo Option B - Use GitHub Desktop (RECOMMENDED):
    echo   1. Download from: https://desktop.github.com
    echo   2. Install and login with your GitHub account
    echo   3. Click "Add Local Repository"
    echo   4. Select: c:\Users\subchand7\Desktop\AntiGravity
    echo   5. Commit all files
    echo   6. Click "Publish repository"
    echo   7. Name it "DocSearch"
    echo   8. Done!
    echo.
    echo Option C - Manual Upload:
    echo   1. Go to: https://github.com/new
    echo   2. Create repository "DocSearch"
    echo   3. Upload files from: c:\Users\subchand7\Desktop\AntiGravity
    echo.
    pause
    exit /b 1
)

echo [OK] Git is installed!
echo.

echo Step 2: Initializing repository...
cd /d c:\Users\subchand7\Desktop\AntiGravity
git init
if %ERRORLEVEL% NEQ 0 (
    echo [!] Failed to initialize repository
    pause
    exit /b 1
)
echo [OK] Repository initialized
echo.

echo Step 3: Adding files...
git add .
if %ERRORLEVEL% NEQ 0 (
    echo [!] Failed to add files
    pause
    exit /b 1
)
echo [OK] Files added
echo.

echo Step 4: Creating commit...
git commit -m "Initial commit: AI-powered DocSearch with vector database"
if %ERRORLEVEL% NEQ 0 (
    echo [!] Failed to create commit
    pause
    exit /b 1
)
echo [OK] Commit created
echo.

echo Step 5: Setting up remote...
echo.
echo Please enter your GitHub repository URL
echo Example: https://github.com/SubhasisPM/DocSearch.git
echo.
set /p REPO_URL="Repository URL: "

git remote add origin %REPO_URL%
if %ERRORLEVEL% NEQ 0 (
    echo [!] Failed to add remote (it might already exist)
    git remote set-url origin %REPO_URL%
)
echo [OK] Remote configured
echo.

echo Step 6: Pushing to GitHub...
echo.
echo You will be prompted for GitHub credentials:
echo Username: SubhasisPM
echo Password: [Your Personal Access Token]
echo.
echo If you don't have a token, create one at:
echo https://github.com/settings/tokens
echo.
pause

git branch -M main
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS! Code deployed to GitHub!
    echo ========================================
    echo.
    echo Your repository: %REPO_URL%
    echo.
    echo Next steps:
    echo 1. Visit your repository on GitHub
    echo 2. Deploy to Render.com or Railway.app
    echo 3. Get your free URL!
    echo.
) else (
    echo.
    echo [!] Push failed. Please check:
    echo 1. Repository URL is correct
    echo 2. You have access to the repository
    echo 3. Your credentials are correct
    echo.
)

pause
