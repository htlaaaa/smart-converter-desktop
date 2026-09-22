"""
单条转链页面
"""
import customtkinter as ctk
from typing import Callable
import asyncio
import threading
from tkinter import messagebox

from services.affiliate import detect_platform, extract_item_id, TaobaoAffiliateAPI
from services.ai import AIService
from services.qq_automation import send_to_qq_group
from core.config import Config


class ConvertPage(ctk.CTkFrame):
    """单条转链页面"""

    def __init__(self, parent, config: Config):
        super().__init__(parent, fg_color="transparent")
        self.config = config

        self._create_widgets()

    def _create_widgets(self):
        """创建组件"""
        # 主容器
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # 标题
        title = ctk.CTkLabel(
            container,
            text="⚡ 智能转链",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(0, 30), anchor="w")

        # 输入区域
        input_frame = ctk.CTkFrame(container)
        input_frame.pack(fill="x", pady=(0, 20))

        input_label = ctk.CTkLabel(
            input_frame,
            text="粘贴商品链接或淘口令",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        input_label.pack(anchor="w", padx=20, pady=(20, 10))

        self.url_textbox = ctk.CTkTextbox(
            input_frame,
            height=100,
            font=ctk.CTkFont(size=14),
            border_width=2,
            border_color=("gray70", "gray30")
        )
        self.url_textbox.pack(fill="x", padx=20, pady=(0, 20))

        # 选项区域
        options_frame = ctk.CTkFrame(container)
        options_frame.pack(fill="x", pady=(0, 20))

        options_label = ctk.CTkLabel(
            options_frame,
            text="转链选项",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        options_label.pack(anchor="w", padx=20, pady=(20, 15))

        # AI 增强开关
        self.ai_switch = ctk.CTkSwitch(
            options_frame,
            text="🤖 AI 增强分析",
            font=ctk.CTkFont(size=14),
            onvalue=True,
            offvalue=False
        )
        self.ai_switch.pack(anchor="w", padx=20, pady=10)

        if not self.config.is_ai_configured():
            self.ai_switch.configure(state="disabled")
            ai_warning = ctk.CTkLabel(
                options_frame,
                text="⚠️ 未配置 AI，请在设置中配置 Claude API",
                font=ctk.CTkFont(size=12),
                text_color="orange"
            )
            ai_warning.pack(anchor="w", padx=50, pady=(0, 10))

        # 文案风格选择
        style_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        style_frame.pack(fill="x", padx=20, pady=10)

        style_label = ctk.CTkLabel(
            style_frame,
            text="文案风格：",
            font=ctk.CTkFont(size=14)
        )
        style_label.pack(side="left", padx=(0, 10))

        self.style_menu = ctk.CTkOptionMenu(
            style_frame,
            values=["不生成文案", "小红书", "朋友圈", "微博", "抖音脚本", "通用"],
            font=ctk.CTkFont(size=14),
            width=200
        )
        self.style_menu.set("通用")
        self.style_menu.pack(side="left")

        # 转发群设置
        forward_group_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        forward_group_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            forward_group_frame,
            text="默认转发群：",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=(0, 10))

        self.forward_group_entry = ctk.CTkEntry(
            forward_group_frame,
            placeholder_text="自动发送到的群名",
            font=ctk.CTkFont(size=14),
            width=300
        )
        self.forward_group_entry.pack(side="left", padx=(0, 10))

        # 加载保存的群号
        saved_group = self.config.get('qq.forward_group', '')
        if saved_group:
            self.forward_group_entry.insert(0, saved_group)

        # 保存按钮
        ctk.CTkButton(
            forward_group_frame,
            text="保存",
            font=ctk.CTkFont(size=12),
            width=60,
            height=30,
            command=self._save_forward_group
        ).pack(side="left")

        # 转换按钮
        self.convert_btn = ctk.CTkButton(
            container,
            text="⚡ 一键转链",
            font=ctk.CTkFont(size=18, weight="bold"),
            height=60,
            fg_color="#7C3AED",
            hover_color="#6D28D9",
            command=self._on_convert
        )
        self.convert_btn.pack(pady=(0, 30), fill="x")

        # 结果区域
        self.result_frame = ctk.CTkFrame(container)
        self.result_frame.pack_forget()

    def refresh(self):
        """刷新页面"""
        self.url_textbox.delete("1.0", "end")
        self.result_frame.pack_forget()
        self.convert_btn.configure(state="normal", text="⚡ 一键转链")

    def _save_forward_group(self):
        """保存默认转发群"""
        group = self.forward_group_entry.get().strip()
        self.config.set('qq.forward_group', group)
        messagebox.showinfo("成功", "默认转发群已保存")

    def _on_convert(self):
        """转链按钮点击"""
        url = self.url_textbox.get("1.0", "end").strip()

        if not url:
            messagebox.showwarning("警告", "请输入商品链接")
            return

        if not self.config.is_taobao_configured():
            messagebox.showerror("错误", "请先在设置中配置淘宝联盟 API")
            self.master.master.show_page("settings")
            return

        # 在新线程中执行
        self.convert_btn.configure(state="disabled", text="处理中...")
        self.master.update()

        thread = threading.Thread(target=self._convert_async, args=(url,))
        thread.daemon = True
        thread.start()

    def _convert_async(self, url: str):
        """异步转链"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(self._do_convert(url))

            # 更新 UI
            self.after(0, lambda: self._show_result(result))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", str(e)))
            self.after(0, lambda: self.convert_btn.configure(state="normal", text="⚡ 一键转链"))

    async def _do_convert(self, url: str) -> dict:
        """执行转链"""
        platform = detect_platform(url)
        item_id = extract_item_id(url, platform)

        if platform != "taobao":
            raise Exception("目前仅支持淘宝/天猫商品链接")

        if not item_id:
            raise Exception("无法提取商品 ID")

        # 调用淘宝联盟 API
        api = TaobaoAffiliateAPI(
            app_key=self.config.get('taobao.app_key'),
            app_secret=self.config.get('taobao.app_secret'),
            pid=self.config.get('taobao.pid'),
            adzone_id=self.config.get('taobao.adzone_id'),
        )

        result = await api.create_promote_url(item_id)
        result['original_url'] = url
        result['platform'] = platform

        # AI 分析
        if self.ai_switch.get() and self.config.is_ai_configured():
            ai_service = AIService(
                api_key=self.config.get('ai.anthropic_api_key'),
                model=self.config.get('ai.model')
            )

            ai_analysis = await ai_service.analyze_product(result)
            result['ai_analysis'] = ai_analysis

            style = self.style_menu.get()
            if style != "不生成文案":
                copywriting = await ai_service.generate_copywriting(result, ai_analysis, style)
                result['copywriting'] = copywriting

        return result

    def _show_result(self, result: dict):
        """显示转链结果"""
        self.convert_btn.configure(state="normal", text="⚡ 一键转链")

        # 清除旧结果
        for widget in self.result_frame.winfo_children():
            widget.destroy()

        # 商品信息卡片
        info_card = ctk.CTkFrame(self.result_frame)
        info_card.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            info_card,
            text="📦 商品信息",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # 商品名称
        title_frame = ctk.CTkFrame(info_card, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(title_frame, text="商品：", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(title_frame, text=result.get('title', '')).pack(side="left", padx=(5, 0))

        # 价格
        price_frame = ctk.CTkFrame(info_card, fg_color="transparent")
        price_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(price_frame, text="价格：", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(price_frame, text=f"¥{result.get('price', 0)}", text_color="#EF4444").pack(side="left", padx=(5, 0))

        # 佣金
        if result.get('commission_rate'):
            comm_frame = ctk.CTkFrame(info_card, fg_color="transparent")
            comm_frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(comm_frame, text="佣金：", font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(
                comm_frame,
                text=f"{result.get('commission_rate', 0) * 100:.1f}% (¥{result.get('commission_amount', 0):.2f})",
                text_color="#10B981"
            ).pack(side="left", padx=(5, 0))

        # AI 分析卡片
        if result.get('ai_analysis'):
            ai_card = ctk.CTkFrame(self.result_frame)
            ai_card.pack(fill="x", pady=(0, 15))

            ctk.CTkLabel(
                ai_card,
                text="🤖 AI 分析",
                font=ctk.CTkFont(size=18, weight="bold")
            ).pack(anchor="w", padx=20, pady=(15, 10))

            analysis = result['ai_analysis']

            # 品类
            cat_frame = ctk.CTkFrame(ai_card, fg_color="transparent")
            cat_frame.pack(fill="x", padx=20, pady=3)
            ctk.CTkLabel(cat_frame, text="品类：", font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(cat_frame, text=analysis.get('category', '')).pack(side="left", padx=(5, 0))

            # 目标人群
            aud_frame = ctk.CTkFrame(ai_card, fg_color="transparent")
            aud_frame.pack(fill="x", padx=20, pady=3)
            ctk.CTkLabel(aud_frame, text="人群：", font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(aud_frame, text=", ".join(analysis.get('target_audience', []))).pack(side="left", padx=(5, 0))

            # 卖点
            selling_frame = ctk.CTkFrame(ai_card, fg_color="transparent")
            selling_frame.pack(fill="x", padx=20, pady=(3, 15))
            ctk.CTkLabel(selling_frame, text="卖点：", font=ctk.CTkFont(weight="bold")).pack(side="left", anchor="n")
            for point in analysis.get('key_selling_points', []):
                ctk.CTkLabel(
                    selling_frame,
                    text=f"• {point}",
                    text_color="gray"
                ).pack(anchor="w", padx=(50, 0), pady=2)

        # AI 文案
        if result.get('copywriting'):
            copy_card = ctk.CTkFrame(self.result_frame)
            copy_card.pack(fill="x", pady=(0, 15))

            ctk.CTkLabel(
                copy_card,
                text="✍️ AI 推广文案",
                font=ctk.CTkFont(size=18, weight="bold")
            ).pack(anchor="w", padx=20, pady=(15, 10))

            copy_textbox = ctk.CTkTextbox(
                copy_card,
                height=150,
                font=ctk.CTkFont(size=14),
                wrap="word"
            )
            copy_textbox.pack(fill="x", padx=20, pady=(0, 20))
            copy_textbox.insert("1.0", result['copywriting'])
            copy_textbox.configure(state="disabled")

            def copy_text():
                self.clipboard_clear()
                self.clipboard_append(result['copywriting'])
                messagebox.showinfo("成功", "文案已复制到剪贴板")

            ctk.CTkButton(
                copy_card,
                text="📋 复制文案",
                command=copy_text,
                width=200
            ).pack(pady=(0, 15))

        # 转链结果
        link_card = ctk.CTkFrame(self.result_frame)
        link_card.pack(fill="x")

        ctk.CTkLabel(
            link_card,
            text="🔗 推广链接 & 淘口令",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # 推广链接
        promote_frame = ctk.CTkFrame(link_card, fg_color="transparent")
        promote_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(promote_frame, text="推广链接：", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))

        promote_entry = ctk.CTkEntry(promote_frame, font=ctk.CTkFont(size=12))
        promote_entry.pack(fill="x", pady=(0, 5))
        promote_entry.insert(0, result.get('promote_url', ''))
        promote_entry.configure(state="readonly")

        ctk.CTkButton(
            promote_frame,
            text="📋 复制",
            command=lambda: self._copy_text(result.get('promote_url', '')),
            width=100
        ).pack(anchor="e")

        # 淘口令
        password_frame = ctk.CTkFrame(link_card, fg_color="transparent")
        password_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(password_frame, text="淘口令：", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))

        password_entry = ctk.CTkEntry(password_frame, font=ctk.CTkFont(size=14, weight="bold"))
        password_entry.pack(fill="x", pady=(0, 5))
        password_entry.insert(0, result.get('tao_password', ''))
        password_entry.configure(state="readonly")

        ctk.CTkButton(
            password_frame,
            text="📋 复制",
            command=lambda: self._copy_text(result.get('tao_password', '')),
            width=100
        ).pack(anchor="e")

        # QQ 发送按钮
        qq_frame = ctk.CTkFrame(link_card, fg_color="transparent")
        qq_frame.pack(fill="x", padx=20, pady=(15, 20))

        self.last_result = result  # 保存结果供QQ发送使用

        ctk.CTkButton(
            qq_frame,
            text="📢 发送到 QQ 群",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color="#12B7F5",
            hover_color="#0E9FE6",
            command=self._send_to_qq
        ).pack(fill="x")

        # 显示结果
        self.result_frame.pack(fill="both", expand=True)

    def _send_to_qq(self):
        """发送到 QQ 群"""
        if not hasattr(self, 'last_result') or not self.last_result:
            messagebox.showwarning("警告", "没有可发送的内容")
            return

        # 优先使用保存的默认转发群
        default_group = self.config.get('qq.forward_group', '')
        group_name = None

        if default_group:
            group_name = default_group
        else:
            # 弹出输入框
            dialog = ctk.CTkInputDialog(
                text="请输入 QQ 群名称：",
                title="发送到 QQ 群"
            )
            group_name = dialog.get_input()

        if not group_name:
            return

        # 确认对话框
        result = messagebox.askyesno(
            "确认发送",
            f"即将发送以下内容到 QQ 群【{group_name}】：\n\n"
            f"商品：{self.last_result.get('title', '')}\n"
            f"价格：¥{self.last_result.get('price', 0)}\n"
            f"淘口令：{self.last_result.get('tao_password', '')}\n\n"
            f"请确保：\n"
            f"1. QQ 已登录并打开\n"
            f"2. 已在 QQ 中打开该群聊窗口\n\n"
            f"是否继续？"
        )

        if not result:
            return

        # 准备消息
        message = self._format_qq_message(self.last_result)

        # 在新线程中发送
        thread = threading.Thread(
            target=self._send_qq_thread,
            args=(group_name, message)
        )
        thread.daemon = True
        thread.start()

    def _format_qq_message(self, result: dict) -> str:
        """格式化 QQ 消息"""
        lines = []

        # 商品名称
        title = result.get('title', '')
        lines.append(f"🔥 {title}")

        # 价格
        price = result.get('price', 0)
        original_price = result.get('original_price', 0)
        if original_price and original_price > price:
            lines.append(f"💰 券后价：¥{price}（原价¥{original_price}）")
        else:
            lines.append(f"💰 价格：¥{price}")

        # 佣金
        commission = result.get('commission_amount', 0)
        if commission:
            lines.append(f"💵 佣金：¥{commission:.2f}")

        # 淘口令
        password = result.get('tao_password', '')
        if password:
            lines.append(f"👉 淘口令：{password}")

        # AI 文案
        copywriting = result.get('copywriting', '')
        if copywriting:
            lines.append("")
            lines.append(copywriting)

        return "\n".join(lines)

    def _send_qq_thread(self, group_name: str, message: str):
        """QQ 发送线程"""
        try:
            from services.qq_automation import QQWindowAutomation

            self.after(0, lambda: messagebox.showinfo(
                "提示",
                "即将自动发送到 QQ 群\n\n"
                "请不要操作鼠标和键盘！"
            ))

            time.sleep(1)

            # 创建发送器并初始化
            sender = QQWindowAutomation()
            if not sender.initialize():
                self.after(0, lambda: messagebox.showerror(
                    "初始化失败",
                    f"未找到群窗口: {group_name}\n\n"
                    "请先在 QQ 中打开该群聊窗口"
                ))
                return

            success = sender.send_to_qq_group(group_name, message)

            if success:
                self.after(0, lambda: messagebox.showinfo("成功", f"已发送到群：{group_name}"))
            else:
                self.after(0, lambda: messagebox.showerror("失败", "发送失败，请检查 QQ 是否正常"))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", str(e)))

    def _copy_text(self, text: str):
        """复制文本"""
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("成功", "已复制到剪贴板")
