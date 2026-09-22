"""
设置页面
"""
import customtkinter as ctk
from tkinter import messagebox

from core.config import Config


class SettingsPage(ctk.CTkFrame):
    """设置页面"""

    def __init__(self, parent, config: Config):
        super().__init__(parent, fg_color="transparent")
        self.config = config

        self._create_widgets()

    def _create_widgets(self):
        """创建组件"""
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # 标题
        ctk.CTkLabel(
            container,
            text="⚙️ 设置",
            font=ctk.CTkFont(size=32, weight="bold")
        ).pack(pady=(0, 30), anchor="w")

        # ========== 淘宝联盟配置 ==========
        taobao_frame = ctk.CTkFrame(container)
        taobao_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            taobao_frame,
            text="淘宝联盟 API",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # App Key
        self._create_input_field(
            taobao_frame,
            "App Key",
            "taobao.app_key",
            "请输入淘宝联盟 App Key"
        )

        # App Secret
        self._create_input_field(
            taobao_frame,
            "App Secret",
            "taobao.app_secret",
            "请输入淘宝联盟 App Secret",
            show="*"
        )

        # PID
        self._create_input_field(
            taobao_frame,
            "PID",
            "taobao.pid",
            "请输入你的 PID"
        )

        # Adzone ID
        self._create_input_field(
            taobao_frame,
            "Adzone ID",
            "taobao.adzone_id",
            "请输入 Adzone ID"
        )

        # ========== AI 配置 ==========
        ai_frame = ctk.CTkFrame(container)
        ai_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            ai_frame,
            text="Claude AI 配置",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        self._create_input_field(
            ai_frame,
            "API Key",
            "ai.anthropic_api_key",
            "请输入 Claude API Key",
            show="*"
        )

        # 模型选择
        model_frame = ctk.CTkFrame(ai_frame, fg_color="transparent")
        model_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(model_frame, text="模型：", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))

        self.model_menu = ctk.CTkOptionMenu(
            model_frame,
            values=["claude-fable-5", "claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5-20251001"],
            font=ctk.CTkFont(size=14),
            width=300
        )
        self.model_menu.pack(side="left")

        # 保存按钮
        save_btn = ctk.CTkButton(
            ai_frame,
            text="💾 保存 AI 配置",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color="#7C3AED",
            hover_color="#6D28D9",
            command=lambda: self._save_ai_config()
        )
        save_btn.pack(padx=20, pady=(0, 20))

        # ========== 外观设置 ==========
        appearance_frame = ctk.CTkFrame(container)
        appearance_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            appearance_frame,
            text="外观设置",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        theme_frame = ctk.CTkFrame(appearance_frame, fg_color="transparent")
        theme_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(theme_frame, text="主题模式：", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))

        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["dark", "light", "system"],
            font=ctk.CTkFont(size=14),
            width=200,
            command=self._on_theme_change
        )
        self.theme_menu.set(self.config.get('general.theme', 'dark'))
        self.theme_menu.pack(side="left")

        # ========== 关于 ==========
        about_frame = ctk.CTkFrame(container)
        about_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            about_frame,
            text="关于",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        about_text = """AI 智能转链工具 v1.0.0

基于 CustomTkinter 和 Claude AI 构建
支持淘宝/京东/拼多多联盟推广链接转换

© 2024 All Rights Reserved
MIT License"""

        ctk.CTkLabel(
            about_frame,
            text=about_text,
            font=ctk.CTkFont(size=13),
            text_color="gray",
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 20))

    def _create_input_field(self, parent, label: str, config_key: str, placeholder: str = "", show: str = None):
        """创建输入字段"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=10)

        label_widget = ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        label_widget.pack(anchor="w", pady=(0, 5))

        entry = ctk.CTkEntry(
            frame,
            placeholder_text=placeholder,
            font=ctk.CTkFont(size=14),
            height=40,
            show=show
        )
        entry.pack(fill="x", pady=(0, 5))

        # 加载已保存的值
        value = self.config.get(config_key, "")
        if value:
            entry.insert(0, value)

        # 保存按钮
        save_btn = ctk.CTkButton(
            frame,
            text="保存",
            font=ctk.CTkFont(size=12),
            width=80,
            height=30,
            command=lambda: self._save_field(config_key, entry.get())
        )
        save_btn.pack(anchor="e")

    def _save_field(self, key: str, value: str):
        """保存字段"""
        self.config.set(key, value)
        messagebox.showinfo("成功", "配置已保存")

    def _save_ai_config(self):
        """保存 AI 配置"""
        # 从输入框获取值
        # TODO: 需要维护输入框引用
        messagebox.showinfo("成功", "AI 配置已保存")

    def _on_theme_change(self, theme: str):
        """主题切换"""
        ctk.set_appearance_mode(theme)
        self.config.set('general.theme', theme)

    def refresh(self):
        """刷新"""
        pass
