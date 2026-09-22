"""
日志查看页面
"""
import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
from loguru import logger


class LogViewerPage(ctk.CTkFrame):
    """日志查看页面"""

    def __init__(self, parent, config):
        super().__init__(parent, fg_color="transparent")
        self.config = config
        self.log_file = Path.home() / ".smart_converter" / "app.log"

        self._create_widgets()

    def _create_widgets(self):
        """创建组件"""
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # 标题
        title = ctk.CTkLabel(
            container,
            text="📋 异常日志",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(0, 30), anchor="w")

        # 提示
        hint = ctk.CTkLabel(
            container,
            text="💡 这里显示程序运行时的异常和错误信息",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        hint.pack(pady=(0, 20), anchor="w")

        # 日志显示区
        self.log_textbox = ctk.CTkTextbox(
            container,
            font=ctk.CTkFont(size=12, family="Consolas"),
            wrap="none"
        )
        self.log_textbox.pack(fill="both", expand=True, pady=(0, 20))

        # 按钮区
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame,
            text="🔄 刷新",
            font=ctk.CTkFont(size=14),
            width=120,
            height=40,
            command=self._load_logs
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="🗑️ 清空日志",
            font=ctk.CTkFont(size=14),
            width=120,
            height=40,
            fg_color="#EF4444",
            hover_color="#DC2626",
            command=self._clear_logs
        ).pack(side="left")

        # 加载日志
        self.after(100, self._load_logs)

    def _load_logs(self):
        """加载日志"""
        self.log_textbox.delete("1.0", "end")

        if not self.log_file.exists():
            self.log_textbox.insert("end", "暂无日志文件\n")
            return

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 只显示最近的100行
            lines = lines[-100:]

            # 高亮错误行
            for line in lines:
                if "ERROR" in line or "Exception" in line or "Traceback" in line:
                    self.log_textbox.insert("end", line, "error")
                elif "WARNING" in line:
                    self.log_textbox.insert("end", line, "warning")
                else:
                    self.log_textbox.insert("end", line)

            # 配置标签颜色
            self.log_textbox.tag_config("error", foreground="#EF4444")
            self.log_textbox.tag_config("warning", foreground="#F59E0B")

            # 滚动到底部
            self.log_textbox.see("end")

        except Exception as e:
            self.log_textbox.insert("end", f"读取日志失败: {e}\n")

    def _clear_logs(self):
        """清空日志"""
        if not messagebox.askyesno("确认", "确定要清空日志文件吗？"):
            return

        try:
            if self.log_file.exists():
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write("")
            self.log_textbox.delete("1.0", "end")
            self.log_textbox.insert("end", "日志已清空\n")
            messagebox.showinfo("成功", "日志已清空")
        except Exception as e:
            messagebox.showerror("错误", f"清空日志失败: {e}")

    def refresh(self):
        """刷新"""
        self._load_logs()
