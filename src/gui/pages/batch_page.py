"""
批量转链页面
"""
import customtkinter as ctk
from typing import Callable
import asyncio
import threading
from tkinter import messagebox
import uuid

from services.affiliate import detect_platform, extract_item_id, TaobaoAffiliateAPI
from services.ai import AIService
from core.config import Config


class BatchPage(ctk.CTkFrame):
    """批量转链页面"""

    def __init__(self, parent, config: Config):
        super().__init__(parent, fg_color="transparent")
        self.config = config
        self.batch_id = None
        self.results = []

        self._create_widgets()

    def _create_widgets(self):
        """创建组件"""
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # 标题
        title = ctk.CTkLabel(
            container,
            text="📦 批量转链",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(0, 30), anchor="w")

        # 输入区域
        input_frame = ctk.CTkFrame(container)
        input_frame.pack(fill="x", pady=(0, 20))

        input_label = ctk.CTkLabel(
            input_frame,
            text="粘贴商品链接（每行一个）",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        input_label.pack(anchor="w", padx=20, pady=(20, 10))

        self.url_textbox = ctk.CTkTextbox(
            input_frame,
            height=300,
            font=ctk.CTkFont(size=13),
            border_width=2,
            border_color=("gray70", "gray30")
        )
        self.url_textbox.pack(fill="x", padx=20, pady=(0, 15))

        # 提示
        hint_label = ctk.CTkLabel(
            input_frame,
            text="提示：支持最多 500 个链接",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        hint_label.pack(anchor="w", padx=20, pady=(0, 20))

        # 选项
        options_frame = ctk.CTkFrame(container)
        options_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            options_frame,
            text="批量选项",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # AI 开关
        self.ai_switch = ctk.CTkSwitch(
            options_frame,
            text="🤖 AI 增强分析",
            font=ctk.CTkFont(size=14),
            onvalue=True,
            offvalue=False
        )
        self.ai_switch.pack(anchor="w", padx=20, pady=10)

        # 文案风格
        style_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        style_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(style_frame, text="文案风格：", font=ctk.CTkFont(size=14)).pack(side="left", padx=(0, 10))

        self.style_menu = ctk.CTkOptionMenu(
            style_frame,
            values=["不生成文案", "小红书", "朋友圈", "微博", "通用"],
            font=ctk.CTkFont(size=14),
            width=200
        )
        self.style_menu.set("通用")
        self.style_menu.pack(side="left")

        # 开始按钮
        self.start_btn = ctk.CTkButton(
            container,
            text="🚀 开始批量处理",
            font=ctk.CTkFont(size=18, weight="bold"),
            height=60,
            fg_color="#7C3AED",
            hover_color="#6D28D9",
            command=self._on_start
        )
        self.start_btn.pack(pady=(0, 30), fill="x")

        # 进度区域
        self.progress_frame = ctk.CTkFrame(container)
        self.progress_frame.pack_forget()

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="处理进度：0%",
            font=ctk.CTkFont(size=16)
        )
        self.progress_label.pack(pady=(20, 10))

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            self.progress_frame,
            text="等待开始...",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.status_label.pack(pady=(0, 20))

    def refresh(self):
        """刷新页面"""
        self.url_textbox.delete("1.0", "end")
        self.results = []
        self.progress_frame.pack_forget()
        self.start_btn.configure(state="normal", text="🚀 开始批量处理")

    def _on_start(self):
        """开始批量处理"""
        urls = self.url_textbox.get("1.0", "end").strip().split('\n')
        urls = [url.strip() for url in urls if url.strip()]

        if not urls:
            messagebox.showwarning("警告", "请输入至少一个链接")
            return

        if len(urls) > 500:
            messagebox.showwarning("警告", "最多支持 500 个链接")
            return

        if not self.config.is_taobao_configured():
            messagebox.showerror("错误", "请先在设置中配置淘宝联盟 API")
            return

        # 显示进度条
        self.progress_frame.pack(fill="x", pady=(0, 20))
        self.start_btn.configure(state="disabled")

        # 在新线程中执行
        thread = threading.Thread(target=self._process_batch, args=(urls,))
        thread.daemon = True
        thread.start()

    def _process_batch(self, urls: list):
        """批量处理"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            self.results = loop.run_until_complete(self._batch_convert(urls))

            self.after(0, lambda: self._show_complete())

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", str(e)))
            self.after(0, lambda: self.start_btn.configure(state="normal", text="🚀 开始批量处理"))

    async def _batch_convert(self, urls: list) -> list:
        """批量转链"""
        results = []
        total = len(urls)

        api = TaobaoAffiliateAPI(
            app_key=self.config.get('taobao.app_key'),
            app_secret=self.config.get('taobao.app_secret'),
            pid=self.config.get('taobao.pid'),
            adzone_id=self.config.get('taobao.adzone_id'),
        )

        for i, url in enumerate(urls):
            try:
                platform = detect_platform(url)
                item_id = extract_item_id(url, platform)

                if not item_id:
                    results.append({"url": url, "success": False, "error": "无法提取商品 ID"})
                    continue

                result = await api.create_promote_url(item_id)
                result['original_url'] = url

                results.append({"success": True, "data": result})

            except Exception as e:
                results.append({"url": url, "success": False, "error": str(e)})

            # 更新进度
            progress = (i + 1) / total
            self.after(0, lambda p=progress: self.progress_bar.set(p))
            self.after(0, lambda p=progress: self.progress_label.configure(text=f"处理进度：{int(p * 100)}%"))
            self.after(0, lambda c=i+1, t=total: self.status_label.configure(text=f"已处理 {c}/{t} 个链接"))

        return results

    def _show_complete(self):
        """显示完成"""
        success_count = sum(1 for r in self.results if r.get('success'))
        failed_count = len(self.results) - success_count

        self.progress_bar.set(1.0)
        self.progress_label.configure(text=f"处理完成：100%")
        self.status_label.configure(text=f"✓ 成功: {success_count}  |  ✗ 失败: {failed_count}")
        self.start_btn.configure(state="normal", text="🚀 开始批量处理")

        messagebox.showinfo(
            "完成",
            f"批量处理完成！\n\n成功: {success_count}\n失败: {failed_count}"
        )
