@echo off
chcp 65001 >nul
echo ========================================
echo BNOS - Node Group Feature Test
echo ========================================
echo.

REM Activate virtual environment
call myenv_new\Scripts\activate.bat

echo [1/3] Testing NodeGroupManager...
python test_node_groups.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ Tests failed!
    pause
    exit /b 1
)

echo.
echo [2/3] All tests passed!
echo.
echo [3/3] Starting BNOS GUI...
echo.
echo 💡 Tips:
echo    - Use Ctrl+Click to select multiple nodes
echo    - Click "Create Group" button to create node groups
echo    - Right-click on groups to start/stop all nodes
echo    - Configuration auto-saves to node_groups.json
echo.

python bnos_gui.py

pause
