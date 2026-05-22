#!/bin/bash

echo "======================================"
echo "  BNOS Console - Visual Node Orchestration"
echo "======================================"
echo ""

# ==================== Step 1: Check Python Installation ====================
echo "[INFO] Checking Python installation..."

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed or not in PATH"
    echo ""
    echo "Please install Python 3.8+:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv"
    echo "  macOS: brew install python3"
    echo "  Fedora: sudo dnf install python3"
    exit 1
fi

python3 --version
echo "[SUCCESS] Python detected"
echo ""

# ==================== Step 2: Check and Create Virtual Environment ====================
echo "[INFO] Checking virtual environment..."

if [ ! -f "myenv_new/bin/activate" ]; then
    echo "[WARN] Virtual environment not found"
    echo ""
    echo "[INFO] Creating virtual environment (myenv_new)..."
    python3 -m venv myenv_new
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "[ERROR] Failed to create virtual environment"
        echo ""
        echo "Possible reasons:"
        echo "1. Python3 is not properly installed"
        echo "2. Insufficient disk space"
        echo "3. No write permission in current directory"
        echo ""
        read -p "Press Enter to exit..."
        exit 1
    fi
    
    echo "[SUCCESS] Virtual environment created successfully"
else
    echo "[SUCCESS] Virtual environment found"
fi
echo ""

# ==================== Step 3: Activate Virtual Environment ====================
echo "[INFO] Activating virtual environment..."
source myenv_new/bin/activate

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Failed to activate virtual environment"
    echo ""
    echo "Please try:"
    echo "1. Delete the myenv_new folder"
    echo "2. Run this script again"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo "[SUCCESS] Virtual environment activated"
echo ""

# ==================== Step 4: Upgrade pip ====================
echo "[INFO] Upgrading pip..."
python -m pip install --upgrade pip > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "[WARN] Failed to upgrade pip, but will continue"
else
    echo "[SUCCESS] pip upgraded"
fi
echo ""

# ==================== Step 5: Check and Install Dependencies ====================
echo "[INFO] Checking dependencies..."

# Check if requirements file exists
if [ ! -f "requirements.txt" ]; then
    echo "[WARN] requirements.txt not found"
    echo ""
    echo "[INFO] Will attempt to install basic dependencies..."
    INSTALL_CMD="pip install pyqt6"
else
    echo "[INFO] Found requirements.txt"
    echo ""
    INSTALL_CMD="pip install -r requirements.txt"
fi

# Quick check if key dependency is installed
python -c "import PyQt6" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[WARN] Key dependencies not found"
    echo ""
    echo "[INFO] Installing dependencies (this may take a few minutes)..."
    echo ""
    
    $INSTALL_CMD
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "[ERROR] Failed to install dependencies"
        echo ""
        echo "Please try:"
        echo "1. Check your internet connection"
        echo "2. Try running: pip install pyqt6 manually"
        echo "3. See README.md for manual installation instructions"
        echo ""
        read -p "Press Enter to exit..."
        exit 1
    fi
    
    echo ""
    echo "[SUCCESS] Dependencies installed successfully"
else
    echo "[SUCCESS] All dependencies are ready"
fi
echo ""

# ==================== Step 6: Start Application ====================
echo "======================================"
echo "Starting BNOS Node Platform..."
echo "======================================"
echo ""

python bnos_console.py

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "======================================"
    echo "[ERROR] Program exited with error code: $EXIT_CODE"
    echo "======================================"
    echo ""
    echo "Common issues:"
    echo "1. Missing display server (Wayland/X11)"
    echo "2. PyQt6 installation incomplete"
    echo "3. Permission denied"
    echo ""
    echo "Check the error messages above for details"
    read -p "Press Enter to exit..."
fi

exit $EXIT_CODE