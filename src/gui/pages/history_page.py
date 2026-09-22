"""
历史记录页面
"""
import customtkinter as ctk
from typing import Callable
from datetime import datetime

from core.database import Database


class HistoryPage(ctk.CTkFrame):
    """历史记录页面"""

    def __init__(self, parent, config):
        super().__init__(parent, fg_color="transparent")
        self.config = config
        self.db = Database()
        self.records = []

        self._create_widgets()
        self._load_records()

    def _create_widgets(self):
        """创建组件"""
        # 标题栏
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header,
            text="📊 历史记录",
            font=ctk.CTkFont(size=32, weight="bold")
        ).pack(side="left")

        # 统计信息
        self.stats_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.stats_label.pack(side="right")

        # 搜索栏
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 搜索商品名称或链接...",
            font=ctk.CTkFont(size=14),
            height=40
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(15, 10), pady=10)
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search())

        ctk.CTkButton(
            search_frame,
            text="搜索",
            font=ctk.CTkFont(size=14),
            width=100,
            command=self._on_search
        ).pack(side="right", padx=(10, 15), pady=10)

        # 记录列表
        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=("gray95", "gray10")
        )
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # 空状态
        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="暂无历史记录\n开始使用后，您的转链记录将显示在这里",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        self.empty_label.pack(pady=100)

    def refresh(self):
        """刷新页面"""
        self._load_records()

    def _load_records(self, keyword: str = ""):
        """加载记录"""
        # 清除列表
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        # 查询记录
        if keyword:
            self.records = self.db.search_conversions(keyword)
        else:
            self.records = self.db.get_conversions(limit=200)

        # 更新统计
        stats = self.db.get_statistics()
        self.stats_label.configure(
            text=f"总计: {stats['total_conversions']} | 今日: {stats['today_conversions']} | 佣金: ¥{stats['total_commission']:.2f}"
        )

        if not self.records:
            self.empty_label = ctk.CTkLabel(
                self.list_frame,
                text="暂无历史记录\n开始使用后，您的转链记录将显示在这里",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            self.empty_label.pack(pady=100)
            return

        # 显示记录
        for record in self.records:
            self._create_record_card(record)

    def _create_record_card(self, record: dict):
        """创建记录卡片"""
        card = ctk.CTkFrame(self.list_frame)
        card.pack(fill="x", pady=8)

        # 标题行
        title_frame = ctk.CTkFrame(card, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            title_frame,
            text=record.get('title', '未知商品')[:50],
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(side="left")

        # 平台标签
        platform = record.get('platform', 'taobao')
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

        platform_label = ctk.CTkLabel(
            title_frame,
            text=platform_names.get(platform, platform),
            font=ctk.CTkFont(size=12),
            fg_color=platform_colors.get(platform, 'gray'),
            text_color="white",
            corner_radius=5,
            padx=10,
            pady=2
        )
        platform_label.pack(side="right")

        # 信息行
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=5)

        # 价格
        price = record.get('price', 0)
        if price:
            ctk.CTkLabel(
                info_frame,
                text=f"¥{price:.2f}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#EF4444"
            ).pack(side="left", padx=(0, 20))

        # 佣金
        commission = record.get('commission_amount', 0)
        if commission:
            ctk.CTkLabel(
                info_frame,
                text=f"佣金: ¥{commission:.2f}",
                font=ctk.CTkFont(size=13),
                text_color="#10B981"
            ).pack(side="left", padx=(0, 20))

        # 时间
        created_at = record.get('created_at', '')
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at)
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                time_str = created_at

            ctk.CTkLabel(
                info_frame,
                text=time_str,
                font=ctk.CTkFont(size=12),
                text_color="gray"
            ).pack(side="right")

        # 按钮行
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 10))

        ctk.CTkButton(
            btn_frame,
            text="📋 复制链接",
            font=ctk.CTkFont(size=12),
            width=100,
            height=30,
            command=lambda r=record: self._copy_promote_url(r)
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="🗑️ 删除",
            font=ctk.CTkFont(size=12),
            width=80,
            height=30,
            fg_color="#EF4444",
            hover_color="#DC2626",
            command=lambda rid=record.get('id'): self._delete_record(rid)
        ).pack(side="right")

    def _on_search(self):
        """搜索"""
        keyword = self.search_entry.get().strip()
        self._load_records(keyword)

    def _copy_promote_url(self, record: dict):
        """复制推广链接"""
        url = record.get('promote_url', '')
        if url:
            self.clipboard_clear()
            self.clipboard_append(url)
            messagebox.showinfo("成功", "推广链接已复制到剪贴板")

    def _delete_record(self, record_id: int):
        """删除记录"""
        if messagebox.askyesno("确认", "确定要删除这条记录吗？"):
            if self.db.delete_conversion(record_id):
                self._load_records()
                messagebox.showinfo("成功", "删除成功")
            else:
                messagebox.showerror("错误", "删除失败")
