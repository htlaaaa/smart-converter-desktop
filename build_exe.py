#!/usr/bin/env python3
"""
打包成 EXE
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')


def clean_build():
    """清理旧的构建文件"""
    dirs_to_remove = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"🧹 清理 {dir_name}/")

    for spec_file in Path('.').glob('*.spec'):
        spec_file.unlink()
        print(f"🧹 清理 {spec_file}")


def build_exe():
    """构建 EXE"""
    print("=" * 50)
    print("🚀 开始打包智能转链工具...")
    print("=" * 50)

    # 清理旧构建
    clean_build()

    # PyInstaller 命令
    cmd = [
        "pyinstaller",
        "--onefile",  # 打包成单个 EXE
        "--windowed",  # 不显示控制台窗口
        "--name", "AI智能转链工具",  # EXE 名称
        "--add-data", "src;src",  # 包含数据文件
        "--hidden-import", "customtkinter",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "loguru",
        "--hidden-import", "httpx",
        "--hidden-import", "anthropic",
        "--hidden-import", "sqlite3",
        "--hidden-import", "pyautogui",
        "--hidden-import", "pyautogui._pyautogui_win",
        "--hidden-import", "pymsgbox",
        "--hidden-import", "pyscreeze",
        "--hidden-import", "mouseinfo",
        "--hidden-import", "pygetwindow",
        "--collect-all", "pyautogui",
        "src/main.py",
    ]

    print("📦 正在打包...")
    print(f"命令: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print()
        print("=" * 50)
        print("✅ 打包成功！")
        print("=" * 50)
        print(f"📁 EXE 文件位于: {os.path.abspath('dist/AI智能转链工具.exe')}")
        print()
        print("💡 使用提示:")
        print("  1. 将 EXE 复制到任意目录")
        print("  2. 首次运行会自动创建配置文件")
        print("  3. 在设置中配置 API 密钥即可使用")
        print()

    except subprocess.CalledProcessError as e:
        print()
        print("=" * 50)
        print("❌ 打包失败！")
        print("=" * 50)
        print(f"错误代码: {e.returncode}")
        sys.exit(1)


def build_with_console():
    """打包带控制台的版本（调试用）"""
    print("=" * 50)
    print("🚀 打包带控制台的版本...")
    print("=" * 50)

    cmd = [
        "pyinstaller",
        "--onefile",  # 打包成单个 EXE
        "--console",  # 显示控制台
        "--name", "AI智能转链工具-调试版",
        "--add-data", "src;src",
        "--hidden-import", "customtkinter",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "loguru",
        "--hidden-import", "httpx",
        "--hidden-import", "anthropic",
        "--hidden-import", "sqlite3",
        "--hidden-import", "pyautogui",
        "src/main.py",
    ]

    try:
        subprocess.run(cmd, check=True)
        print("✅ 打包成功！")
    except subprocess.CalledProcessError as e:
        print(f"❌ 打包失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="打包智能转链工具")
    parser.add_argument("--console", action="store_true", help="打包带控制台的版本")
    parser.add_argument("--clean", action="store_true", help="仅清理构建文件")

    args = parser.parse_args()

    if args.clean:
        clean_build()
        print("✅ 清理完成")
    elif args.console:
        build_with_console()
    else:
        build_exe()
