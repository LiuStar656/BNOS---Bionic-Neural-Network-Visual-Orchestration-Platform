# 🆕 Recent Updates

## 🆕 Recent Updates (2026-05-08)

### ✨ New Features and Optimizations

#### 1. **VSCode Workspace Integration** 🔧
- **Feature**: Added "Open as VSCode Workspace" button in node configuration dialog
- **Implementation Details**:
  - Auto-generate standard `.code-workspace` configuration file for node folders
  - Smart Python virtual environment interpreter path configuration (cross-platform: Windows/macOS/Linux)
  - Auto-exclude `__pycache__` and `.pyc` files, keep workspace clean
  - One-click VSCode open in workspace mode with node directory
- **Technical Implementation**: Non-intrusive design, only added `open_vscode_workspace()` function, no modification to existing code
- **Affected Files**: `ui/property_panel.py` - `NodeConfigDialog` class
- **User Value**: Simplified development workflow, provides instant source code access with auto-configured development environment

#### 2. **VSCode Workspace Feature Optimization** ⚡
- **Smart Detection Mechanism**: Pre-check if VSCode is installed before attempting to open
  - Windows systems: Use `where code` command
  - macOS/Linux systems: Use `which code` command
  - Timeout protection: 3-second timeout, avoid long waits
- **Relative Path Configuration**:
  - Workspace folder uses `"path": "."` (relative path)
  - Python interpreter path uses `${workspaceFolder}` variable
  - Ensures project portability, supports safe migration
- **Friendly User Interaction**:
  - VSCode not detected: Show confirmation dialog with clear instructions
  - User can still choose to create workspace file (for future use)
  - Provides installation hint: "Add 'code' command to PATH"
  - Respects user choice: Can cancel without creating any files
- **Cross-Platform Support**: Runs seamlessly on Windows, macOS, Linux
- **Enhanced Feedback Info**: Shows different success prompts based on VSCode availability
  - VSCode installed: "✅ Created and automatically opened"
  - VSCode not installed: "✅ Created, double-click to open after installing VSCode"
- **Technical Improvement**: Separated detection logic to independent `_check_vscode_installed()` method, improved maintainability
