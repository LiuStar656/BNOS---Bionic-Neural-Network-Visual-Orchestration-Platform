@echo off
chcp 65001 >nul
echo ==============================================
echo          BNOS Project Auto Update to GitHub
echo ==============================================
echo.

:: ===================== Git Configuration =====================
git config --global user.name "LiuStar"
git config --global user.email "1240543656@qq.com"

echo [OK] Git configured: LiuStar / 1240543656@qq.com
echo.

:: ================ Step 1: Check Git Status ================
echo [1/5] Checking Git status...
git status --short
if %errorlevel% neq 0 (
    echo [ERROR] Not a Git repository!
    pause
    exit /b 1
)
echo.

:: ================ Step 2: Add All Changes ================
echo [2/5] Adding all modified files...
git add .
if %errorlevel% neq 0 (
    echo [ERROR] Failed to add files!
    pause
    exit /b 1
)
echo [OK] Files added successfully
echo.

:: ================ Step 3: Commit Changes ================
echo [3/5] Committing changes...
:: Check if there are staged changes
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo [WARN] No changes to commit
    echo.
    goto SKIP_COMMIT
)

:: Generate commit message with timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set commit_msg=BNOS auto update - %datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2% %datetime:~8,2%:%datetime:~10,2%

git commit -m "%commit_msg%"
if %errorlevel% neq 0 (
    echo [ERROR] Commit failed!
    pause
    exit /b 1
)
echo [OK] Committed: %commit_msg%
echo.

:SKIP_COMMIT
:: ================ Step 4: Pull Latest Code ================
echo [4/5] Pulling latest code from remote...
git pull origin main
if %errorlevel% neq 0 (
    echo [WARN] Pull failed or has conflicts
    echo Please resolve conflicts manually and run this script again
    pause
    exit /b 1
)
echo [OK] Pull completed
echo.

:: ================ Step 5: Push to GitHub ================
echo [5/5] Pushing to GitHub repository...
git push origin main
if %errorlevel% neq 0 (
    echo [ERROR] Push failed! Check network or permissions
    pause
    exit /b 1
)
echo [OK] Push successful
echo.

echo ==============================================
echo        SUCCESS: Code updated and pushed!
echo ==============================================
echo.
echo Tip: Edit this script to customize commit messages
echo.
pause
