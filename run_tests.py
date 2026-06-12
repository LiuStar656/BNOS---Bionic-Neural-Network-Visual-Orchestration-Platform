#!/usr/bin/env python
"""
测试运行脚本
运行所有单元测试
"""

import subprocess
import sys
import os

def main():
    # 确保在项目根目录运行
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 运行 pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    print("测试输出:")
    print("=" * 60)
    print(result.stdout)
    print(result.stderr)
    print("=" * 60)
    print(f"测试完成，返回码: {result.returncode}")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())