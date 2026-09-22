"""
主应用入口 - GUI
"""
import customtkinter as ctk
from tkinter import messagebox
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from gui.main_window import MainWindow
from core.config import Config
from loguru import logger

# 配置日志
logger.add(
    Path.home() / ".smart_converter" / "app.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    encoding='utf-8'
)


def main():
    """主函数"""
    # 加载配置
    config = Config()

    # 设置主题
    ctk.set_appearance_mode(config.get('general.theme', 'dark'))
    ctk.set_default_color_theme("blue")

    # 创建应用
    app = ctk.CTk()
    app.geometry("1200x700")
    app.minsize(900, 600)

    # 设置窗口标题和图标
    app.title("AI 智能转链工具 v1.0.0")

    # 创建主窗口
    main_window = MainWindow(app, config)

    # 运行
    app.mainloop()


if __name__ == "__main__":
    main()
