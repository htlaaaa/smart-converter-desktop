"""
消息监控页面
监控其他群组的消息，自动识别商品链接并转链
"""
import customtkinter as ctk
from typing import Callable, Optional
import threading
import time
import re
import asyncio
from tkinter import messagebox
from datetime import datetime

from services.affiliate import detect_platform, extract_item_id, TaobaoAffiliateAPI
from services.jd_affiliate import JDAffiliateAPI, detect_jd_item_id
from loguru import logger


class MonitorPage(ctk.CTkFrame):
    """消息监控页面"""

    def __init__(self, parent, config):
        super().__init__(parent, fg_color="transparent")
        self.config = config
        self.pending_items = []  # 待发送的商品列表
        self.monitoring = False
        self.last_clipboard = ""
        self.monitor_thread = None

        self._create_widgets()

    def _create_widgets(self):
        """创建组件"""
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # 标题
        title = ctk.CTkLabel(
            container,
            text="👀 消息监控",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(0, 10), anchor="w")

        # 说明
        desc = ctk.CTkLabel(
            container,
            text="监控其他群的商品消息，自动转链后发到自己的群",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        desc.pack(pady=(0, 20), anchor="w")

        # 工作流程说明
        workflow_frame = ctk.CTkFrame(container, fg_color="#EFF6FF", border_color="#3B82F6", border_width=2)
        workflow_frame.pack(fill="x", pady=(0, 20))

        workflow_text = (
            "💡 工作流程：\n\n"
            "1️⃣ 在其他群中选中商品消息，按 Ctrl+C 复制\n"
            "2️⃣ 程序自动检测剪贴板中的商品链接\n"
            "3️⃣ 自动转链成你的推广链接\n"
            "4️⃣ 显示在下方待发送列表\n"
            "5️⃣ 点击「发送到目标群」一键发送"
        )

        ctk.CTkLabel(
            workflow_frame,
            text=workflow_text,
            font=ctk.CTkFont(size=13),
            text_color="#1E40AF",
            justify="left"
        ).pack(anchor="w", padx=15, pady=10)

        # 控制区域
        control_frame = ctk.CTkFrame(container)
        control_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            control_frame,
            text="监控控制",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # 监控开关
        self.monitor_switch = ctk.CTkSwitch(
            control_frame,
            text="🔛 启用剪贴板监控",
            font=ctk.CTkFont(size=14),
            command=self._toggle_monitor
        )
        self.monitor_switch.pack(anchor="w", padx=20, pady=10)

        # 状态显示
        self.status_label = ctk.CTkLabel(
            control_frame,
            text="● 未运行",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.status_label.pack(anchor="w", padx=20, pady=(0, 15))

        # 目标群设置
        target_frame = ctk.CTkFrame(container)
        target_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            target_frame,
            text="目标群（自己的群）",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        target_input_frame = ctk.CTkFrame(target_frame, fg_color="transparent")
        target_input_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.target_entry = ctk.CTkEntry(
            target_input_frame,
            placeholder_text="请输入目标群名（必须已在QQ中打开）",
            font=ctk.CTkFont(size=14),
            height=40
        )
        self.target_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            target_input_frame,
            text="保存",
            font=ctk.CTkFont(size=13),
            width=80,
            height=40,
            command=self._save_target
        ).pack(side="left")

        # 加载保存的目标群
        saved_target = self.config.get('monitor.target_group', '')
        if saved_target:
            self.target_entry.insert(0, saved_target)

        # 待发送列表
        list_frame = ctk.CTkFrame(container)
        list_frame.pack(fill="both", expand=True)

        list_header = ctk.CTkFrame(list_frame, fg_color="transparent")
        list_header.pack(fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            list_header,
            text="📦 待发送商品",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left")

        self.count_label = ctk.CTkLabel(
            list_header,
            text="共 0 个",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.count_label.pack(side="left", padx=(15, 0))

        # 按钮区
        btn_frame = ctk.CTkFrame(list_header, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(
            btn_frame,
            text="🚀 全部发送",
            font=ctk.CTkFont(size=13),
            width=100,
            height=35,
            fg_color="#7C3AED",
            hover_color="#6D28D9",
            command=self._send_all
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="🗑️ 清空",
            font=ctk.CTkFont(size=13),
            width=80,
            height=35,
            fg_color="#EF4444",
            hover_color="#DC2626",
            command=self._clear_list
        ).pack(side="left")

        # 商品列表
        self.items_frame = ctk.CTkScrollableFrame(
            list_frame,
            fg_color=("gray95", "gray10")
        )
        self.items_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # 空状态
        self.empty_label = ctk.CTkLabel(
            self.items_frame,
            text="暂无待发送商品\n复制其他群的消息后会自动出现",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.empty_label.pack(pady=50)

    def refresh(self):
        """刷新页面"""
        self._update_items_display()

    def _save_target(self):
        """保存目标群"""
        target = self.target_entry.get().strip()
        self.config.set('monitor.target_group', target)
        messagebox.showinfo("成功", f"目标群已保存: {target}")

    def _toggle_monitor(self):
        """切换监控状态"""
        if self.monitor_switch.get():
            self._start_monitor()
        else:
            self._stop_monitor()

    def _start_monitor(self):
        """启动监控"""
        if self.monitoring:
            return

        self.monitoring = True
        self.last_clipboard = self._get_clipboard()
        self.status_label.configure(text="● 运行中（监控剪贴板）", text_color="#10B981")

        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        logger.info("消息监控已启动")

    def _stop_monitor(self):
        """停止监控"""
        self.monitoring = False
        self.status_label.configure(text="● 未运行", text_color="gray")
        logger.info("消息监控已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                interval = self.config.get('monitor.check_interval', 2)
                time.sleep(interval)

                current_clipboard = self._get_clipboard()
                if current_clipboard != self.last_clipboard:
                    self.last_clipboard = current_clipboard
                    # 检查是否包含商品链接
                    url = self._extract_url(current_clipboard)
                    if url and not self._is_duplicate(url):
                        self.after(0, lambda u=url, c=current_clipboard: self._process_message(u, c))

            except Exception as e:
                logger.error(f"监控循环出错: {e}")

    def _get_clipboard(self) -> str:
        """获取剪贴板内容"""
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            return data
        except Exception:
            return ""

    def _extract_url(self, text: str) -> Optional[str]:
        """从文本中提取URL"""
        # 匹配商品链接的正则
        patterns = [
            r'https?://[^\s]*item\.taobao\.com[^\s]*',
            r'https?://[^\s]*detail\.tmall\.com[^\s]*',
            r'https?://[^\s]*item\.jd\.com[^\s]*',
            r'https?://[^\s]*pinduoduo\.com[^\s]*',
            r'https?://[^\s]*yangkeduo\.com[^\s]*',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return None

    def _is_duplicate(self, url: str) -> bool:
        """检查是否重复"""
        for item in self.pending_items:
            if item.get('original_url') == url:
                return True
        return False

    def _process_message(self, url: str, raw_text: str):
        """处理消息"""
        platform = detect_platform(url)

        # 京东特殊处理
        if platform == "jd":
            item_id = detect_jd_item_id(url)
        else:
            item_id = extract_item_id(url, platform)

        if not item_id:
            logger.warning(f"无法提取商品ID: {url}")
            return

        # 检查配置
        if platform == "taobao" and not self.config.is_taobao_configured():
            messagebox.showwarning("警告", "请先配置淘宝联盟API")
            return

        if platform == "jd" and not self.config.get('jd.app_key'):
            messagebox.showwarning("警告", "请先配置京东联盟API")
            return

        # 添加占位项
        placeholder = {
            "original_url": url,
            "platform": platform,
            "title": "转链中...",
            "status": "processing"
        }
        self.pending_items.append(placeholder)
        self._update_items_display()

        # 异步转链
        threading.Thread(
            target=self._convert_async,
            args=(placeholder, platform, item_id, raw_text),
            daemon=True
        ).start()

    def _convert_async(self, item: dict, platform: str, item_id: str, raw_text: str):
        """异步转链"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            if platform == "taobao":
                api = TaobaoAffiliateAPI(
                    app_key=self.config.get('taobao.app_key'),
                    app_secret=self.config.get('taobao.app_secret'),
                    pid=self.config.get('taobao.pid'),
                    adzone_id=self.config.get('taobao.adzone_id'),
                )
                result = loop.run_until_complete(api.create_promote_url(item_id))

            elif platform == "jd":
                api = JDAffiliateAPI(
                    app_key=self.config.get('jd.app_key'),
                    app_secret=self.config.get('jd.app_secret'),
                    pid=self.config.get('jd.pid'),
                )
                result = loop.run_until_complete(api.create_promote_url(item_id))

            else:
                raise Exception(f"暂不支持的平台: {platform}")

            # 更新数据
            item.update(result)
            item['status'] = 'ready'
            item['raw_text'] = raw_text

            self.after(0, self._update_items_display)
            logger.info(f"转链成功: {item.get('title', '')}")

        except Exception as e:
            item['status'] = 'failed'
            item['error'] = str(e)
            self.after(0, self._update_items_display)
            logger.error(f"转链失败: {e}")

    def _update_items_display(self):
        """更新商品列表显示"""
        # 清空
        for widget in self.items_frame.winfo_children():
            widget.destroy()

        if not self.pending_items:
            self.empty_label = ctk.CTkLabel(
                self.items_frame,
                text="暂无待发送商品\n复制其他群的消息后会自动出现",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            self.empty_label.pack(pady=50)
            self.count_label.configure(text="共 0 个")
            return

        self.count_label.configure(text=f"共 {len(self.pending_items)} 个")

        # 显示商品
        for i, item in enumerate(self.pending_items):
            self._create_item_card(i, item)

    def _create_item_card(self, index: int, item: dict):
        """创建商品卡片"""
        card = ctk.CTkFrame(self.items_frame)
        card.pack(fill="x", pady=5)

        # 平台标签
        platform = item.get('platform', 'taobao')
        platform_colors = {
            'taobao': '#FF6B00',
            'jd': '#E4393C',
            'pdd': '#E02E24',
        }
        platform_names = {
            'taobao': '淘宝',
            'jd': '京东',
            'pdd': '拼多多',
        }

        # 状态颜色
        status = item.get('status', 'processing')
        if status == 'processing':
            card_color = ("gray90", "gray20")
            status_text = "⏳ 转链中..."
            status_color = "gray"
        elif status == 'ready':
            card_color = ("#D1FAE5", "#065F46")
            status_text = "✓ 已就绪"
            status_color = "#10B981"
        else:  # failed
            card_color = ("#FEE2E2", "#7F1D1D")
            status_text = f"✗ 失败: {item.get('error', '')[:30]}"
            status_color = "#EF4444"

        # 顶部信息
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            top,
            text=f"#{index + 1} {item.get('title', '未知商品')[:40]}",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text=platform_names.get(platform, platform),
            font=ctk.CTkFont(size=11),
            fg_color=platform_colors.get(platform, 'gray'),
            text_color="white",
            corner_radius=3,
            padx=8,
            pady=2
        ).pack(side="right", padx=(10, 0))

        # 状态
        if status == 'ready':
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(fill="x", padx=15, pady=5)

            price = item.get('price', 0)
            commission = item.get('commission_amount', 0)

            ctk.CTkLabel(
                info,
                text=f"价格: ¥{price:.2f}",
                font=ctk.CTkFont(size=12)
            ).pack(side="left", padx=(0, 15))

            ctk.CTkLabel(
                info,
                text=f"佣金: ¥{commission:.2f}",
                font=ctk.CTkFont(size=12),
                text_color="#10B981"
            ).pack(side="left", padx=(0, 15))

            ctk.CTkLabel(
                info,
                text=status_text,
                font=ctk.CTkFont(size=12),
                text_color=status_color
            ).pack(side="right")

        else:
            ctk.CTkLabel(
                card,
                text=status_text,
                font=ctk.CTkFont(size=12),
                text_color=status_color
            ).pack(anchor="w", padx=15, pady=5)

    def _send_all(self):
        """发送所有商品"""
        target = self.target_entry.get().strip()
        if not target:
            messagebox.showwarning("警告", "请先输入目标群名")
            return

        ready_items = [item for item in self.pending_items if item.get('status') == 'ready']
        if not ready_items:
            messagebox.showwarning("警告", "没有可发送的商品")
            return

        if not messagebox.askyesno("确认", f"即将发送 {len(ready_items)} 个商品到【{target}】\n\n请确保目标群窗口已在QQ中打开"):
            return

        # 异步发送
        threading.Thread(
            target=self._send_async,
            args=(target, ready_items),
            daemon=True
        ).start()

    def _send_async(self, target: str, items: list):
        """异步发送"""
        from services.qq_automation import QQWindowAutomation

        try:
            sender = QQWindowAutomation()
            if not sender.initialize():
                self.after(0, lambda: messagebox.showerror("失败", "未找到QQ窗口或群窗口"))
                return

            success = 0
            failed = 0

            for i, item in enumerate(items, 1):
                message = self._format_message(item)
                if sender.send_to_qq_group(target, message):
                    success += 1
                else:
                    failed += 1
                time.sleep(2)  # 延迟

            self.after(0, lambda: messagebox.showinfo(
                "完成",
                f"发送完成！\n成功: {success}\n失败: {failed}"
            ))

            # 清空已发送的
            sent_urls = [item.get('original_url') for item in items]
            self.pending_items = [
                item for item in self.pending_items
                if item.get('original_url') not in sent_urls
            ]
            self.after(0, self._update_items_display)

        except Exception as e:
            logger.error(f"发送失败: {e}")
            self.after(0, lambda: messagebox.showerror("错误", str(e)))

    def _format_message(self, item: dict) -> str:
        """格式化消息"""
        lines = []
        lines.append(f"🔥 {item.get('title', '')}")

        price = item.get('price', 0)
        original_price = item.get('original_price', 0)
        if original_price and original_price > price:
            lines.append(f"💰 券后价：¥{price:.2f}（原价¥{original_price:.2f}）")
        else:
            lines.append(f"💰 价格：¥{price:.2f}")

        commission = item.get('commission_amount', 0)
        if commission:
            lines.append(f"💵 佣金：¥{commission:.2f}")

        password = item.get('tao_password', '')
        if password:
            lines.append(f"👉 淘口令：{password}")

        promote_url = item.get('promote_url', '')
        if promote_url:
            lines.append(f"🔗 {promote_url}")

        return "\n".join(lines)

    def _clear_list(self):
        """清空列表"""
        if not self.pending_items:
            return
        if messagebox.askyesno("确认", "确定要清空所有待发送商品吗？"):
            self.pending_items.clear()
            self._update_items_display()