"""
主窗口
"""
import customtkinter as ctk
from typing import Callable

from gui.pages.convert_page import ConvertPage
from gui.pages.batch_page import BatchPage
from gui.pages.groupsend_page import GroupSendPage
from gui.pages.history_page import HistoryPage
from gui.pages.settings_page import SettingsPage
from gui.pages.log_viewer_page import LogViewerPage
from gui.pages.monitor_page import MonitorPage
from gui.pages.cloud_collect_page import CloudCollectPage
from loguru import logger
import os
from pathlib import Path


class MainWindow:
    """主窗口"""

    def __init__(self, root: ctk.CTk, config):
        self.root = root
        self.config = config
        self.current_page = None

        # 创建侧边栏
        self.sidebar = self._create_sidebar()

        # 创建内容区
        self.content_frame = ctk.CTkFrame(root)
        self.content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # 创建所有页面
        self.pages = {
            "single": ConvertPage(self.content_frame, self.config),
            "batch": BatchPage(self.content_frame, self.config),
            "monitor": MonitorPage(self.content_frame, self.config),
            "cloud": CloudCollectPage(self.content_frame, self.config),
            "groupsend": GroupSendPage(self.content_frame, self.config),
            "history": HistoryPage(self.content_frame, self.config),
            "log": LogViewerPage(self.content_frame, self.config),
            "settings": SettingsPage(self.content_frame, self.config),
        }

        # 默认显示单条转链页
        self.show_page("single")

    def _create_sidebar(self) -> ctk.CTkFrame:
        """创建侧边栏"""
        sidebar = ctk.CTkFrame(self.root, width=250, corner_radius=0)
        sidebar.pack(side="left", fill="y", padx=0, pady=0)

        # Logo
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(pady=20, padx=20, fill="x")

        logo_label = ctk.CTkLabel(
            logo_frame,
            text="🚀 AI转链工具",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#1a1a1a", "#ffffff")
        )
        logo_label.pack()

        version_label = ctk.CTkLabel(
            logo_frame,
            text="v1.0.0",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        version_label.pack()

        # 导航按钮
        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.pack(pady=20, fill="x", padx=10)

        buttons = [
            ("⚡", "单条转链", "single"),
            ("📦", "批量转链", "batch"),
            ("👀", "消息监控", "monitor"),
            ("☁️", "云采集", "cloud"),
            ("📢", "QQ群发", "groupsend"),
            ("📊", "历史记录", "history"),
            ("📋", "异常日志", "log"),
            ("⚙️", "设置", "settings"),
        ]

        self.nav_buttons = {}
        for icon, text, page_id in buttons:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"{icon}  {text}",
                font=ctk.CTkFont(size=16),
                height=50,
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=lambda p=page_id: self.show_page(p)
            )
            btn.pack(pady=5, fill="x")
            self.nav_buttons[page_id] = btn

        # 状态栏
        self.status_frame = ctk.CTkFrame(sidebar)
        self.status_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="就绪",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(pady=5)

        return sidebar

    def show_page(self, page_id: str):
        """显示指定页面"""
        # 隐藏所有页面
        for page in self.pages.values():
            page.pack_forget()

        # 更新导航按钮状态
        for pid, btn in self.nav_buttons.items():
            if pid == page_id:
                btn.configure(
                    fg_color=("gray75", "gray25"),
                    text_color=("gray10", "gray90")
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("gray10", "gray90")
                )

        # 显示目标页面
        if page_id in self.pages:
            self.pages[page_id].pack(fill="both", expand=True)
            self.current_page = page_id

            # 刷新页面
            if hasattr(self.pages[page_id], 'refresh'):
                self.pages[page_id].refresh()

    def update_status(self, message: str):
        """更新状态栏"""
        self.status_label.configure(text=message)
        self.root.update()
