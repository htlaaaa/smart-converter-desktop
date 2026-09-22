"""
云采集页面
从好单库等平台采集商品，配置到对应群组
"""
import customtkinter as ctk
from typing import Callable
import asyncio
import threading
import time
from tkinter import messagebox

from services.cloud_collector import CloudCollector, CloudResource
from loguru import logger


class CloudCollectPage(ctk.CTkFrame):
    """云采集页面"""

    def __init__(self, parent, config):
        super().__init__(parent, fg_color="transparent")
        self.config = config
        self.collected_items = []
        self.is_collecting = False
        self.auto_collect_thread = None

        self._create_widgets()

    def _create_widgets(self):
        """创建组件"""
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # 标题
        title = ctk.CTkLabel(
            container,
            text="☁️ 云采集",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(0, 10), anchor="w")

        desc = ctk.CTkLabel(
            container,
            text="从好单库等平台采集商品，配置到不同群组自动发送",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        desc.pack(pady=(0, 20), anchor="w")

        # API Key 配置
        apikey_frame = ctk.CTkFrame(container)
        apikey_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            apikey_frame,
            text="好单库 API Key",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        apikey_input_frame = ctk.CTkFrame(apikey_frame, fg_color="transparent")
        apikey_input_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.apikey_entry = ctk.CTkEntry(
            apikey_input_frame,
            placeholder_text="请到 haodanku.com 注册获取 API Key",
            font=ctk.CTkFont(size=13),
            width=500
        )
        self.apikey_entry.pack(side="left", padx=(0, 10))

        # 加载保存的API Key
        saved_key = self.config.get('cloud_collect.haodanku_apikey', '')
        if saved_key:
            self.apikey_entry.insert(0, saved_key)

        ctk.CTkButton(
            apikey_input_frame,
            text="保存",
            font=ctk.CTkFont(size=13),
            width=80,
            command=self._save_apikey
        ).pack(side="left")

        # 资源管理
        resource_section = ctk.CTkFrame(container)
        resource_section.pack(fill="both", expand=True, pady=(0, 20))

        resource_header = ctk.CTkFrame(resource_section, fg_color="transparent")
        resource_header.pack(fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            resource_header,
            text="📋 采集资源管理",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            resource_header,
            text="➕ 添加资源",
            font=ctk.CTkFont(size=13),
            width=100,
            fg_color="#10B981",
            hover_color="#059669",
            command=self._show_add_resource_dialog
        ).pack(side="right")

        # 资源列表
        self.resource_list_frame = ctk.CTkScrollableFrame(
            resource_section,
            height=200,
            fg_color=("gray95", "gray10")
        )
        self.resource_list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self._refresh_resource_list()

        # 群组映射
        mapping_section = ctk.CTkFrame(container)
        mapping_section.pack(fill="both", expand=True, pady=(0, 20))

        mapping_header = ctk.CTkFrame(mapping_section, fg_color="transparent")
        mapping_header.pack(fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            mapping_header,
            text="🔗 群组资源映射",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left")

        ctk.CTkLabel(
            mapping_header,
            text="配置每个群使用哪些采集资源",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(side="left", padx=(15, 0))

        self.mapping_frame = ctk.CTkScrollableFrame(
            mapping_section,
            height=150,
            fg_color=("gray95", "gray10")
        )
        self.mapping_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # 自动采集控制
        auto_frame = ctk.CTkFrame(container)
        auto_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            auto_frame,
            text="⚙️ 自动模式",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        auto_control = ctk.CTkFrame(auto_frame, fg_color="transparent")
        auto_control.pack(fill="x", padx=15, pady=(0, 15))

        self.auto_switch = ctk.CTkSwitch(
            auto_control,
            text="启用自动采集",
            font=ctk.CTkFont(size=14),
            command=self._toggle_auto
        )
        self.auto_switch.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(
            auto_control,
            text="采集间隔：",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=(0, 10))

        self.interval_entry = ctk.CTkEntry(
            auto_control,
            placeholder_text="30",
            font=ctk.CTkFont(size=14),
            width=80
        )
        self.interval_entry.pack(side="left", padx=(0, 10))
        self.interval_entry.insert(0, str(self.config.get('cloud_collect.collect_interval', 30)))

        ctk.CTkLabel(
            auto_control,
            text="分钟",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=(0, 20))

        ctk.CTkButton(
            auto_control,
            text="🚀 立即采集所有资源",
            font=ctk.CTkFont(size=13),
            width=150,
            fg_color="#7C3AED",
            hover_color="#6D28D9",
            command=self._collect_all_now
        ).pack(side="left")

        self.auto_status_label = ctk.CTkLabel(
            auto_frame,
            text="● 自动采集未启动",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.auto_status_label.pack(anchor="w", padx=15, pady=(0, 15))

    def refresh(self):
        """刷新页面"""
        self._refresh_resource_list()
        self._refresh_mapping_list()

    def _save_apikey(self):
        """保存API Key"""
        key = self.apikey_entry.get().strip()
        self.config.set('cloud_collect.haodanku_apikey', key)
        messagebox.showinfo("成功", "API Key 已保存")

    def _show_add_resource_dialog(self):
        """显示添加资源对话框"""
        dialog = AddResourceDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            self._add_resource(dialog.result)

    def _add_resource(self, resource_data: dict):
        """添加资源"""
        resource = CloudResource(
            name=resource_data['name'],
            resource_type=resource_data['type'],
            params=resource_data['params'],
            enabled=True
        )

        resources = self.config.get('cloud_collect.resources', [])
        resources.append(resource.to_dict())
        self.config.set('cloud_collect.resources', resources)

        self._refresh_resource_list()
        messagebox.showinfo("成功", f"已添加采集资源: {resource.name}")

    def _delete_resource(self, resource_id: str):
        """删除资源"""
        if not messagebox.askyesno("确认", "确定要删除这个采集资源吗？"):
            return

        resources = self.config.get('cloud_collect.resources', [])
        resources = [r for r in resources if r.get("resource_id") != resource_id]
        self.config.set('cloud_collect.resources', resources)

        # 删除相关映射
        mappings = self.config.get('cloud_collect.group_mappings', {})
        for group_name in list(mappings.keys()):
            mappings[group_name] = [
                rid for rid in mappings[group_name] if rid != resource_id
            ]
        self.config.set('cloud_collect.group_mappings', mappings)

        self._refresh_resource_list()
        self._refresh_mapping_list()

    def _toggle_resource(self, resource_id: str, enabled: bool):
        """启用/禁用资源"""
        resources = self.config.get('cloud_collect.resources', [])
        for r in resources:
            if r.get("resource_id") == resource_id:
                r["enabled"] = enabled
                break
        self.config.set('cloud_collect.resources', resources)

    def _refresh_resource_list(self):
        """刷新资源列表"""
        for widget in self.resource_list_frame.winfo_children():
            widget.destroy()

        resources = self.config.get('cloud_collect.resources', [])

        if not resources:
            empty_label = ctk.CTkLabel(
                self.resource_list_frame,
                text="暂无采集资源\n点击「➕ 添加资源」创建",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_label.pack(pady=30)
            return

        # 资源类型中文名
        type_names = {
            "top_items": "今日精选",
            "itemlist_channel": "好券清单",
            "supersearch": "超级搜索",
        }

        for resource_data in resources:
            res_type = resource_data.get("resource_type", "")
            type_name = type_names.get(res_type, res_type)

            card = ctk.CTkFrame(self.resource_list_frame)
            card.pack(fill="x", pady=5, padx=5)

            left_frame = ctk.CTkFrame(card, fg_color="transparent")
            left_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            ctk.CTkLabel(
                left_frame,
                text=f"📌 {resource_data.get('name', '')}",
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(anchor="w")

            params_text = f"类型: {type_name}"
            if "keyword" in resource_data.get("params", {}):
                params_text += f" | 关键词: {resource_data['params']['keyword']}"
            elif "channel_type" in resource_data.get("params", {}):
                params_text += f" | 频道: {resource_data['params']['channel_type']}"

            ctk.CTkLabel(
                left_frame,
                text=params_text,
                font=ctk.CTkFont(size=12),
                text_color="gray"
            ).pack(anchor="w")

            right_frame = ctk.CTkFrame(card, fg_color="transparent")
            right_frame.pack(side="right", padx=10)

            enabled = resource_data.get("enabled", True)
            switch_var = ctk.BooleanVar(value=enabled)

            def make_toggle(rid=resource_data["resource_id"]):
                return lambda: self._toggle_resource(rid, switch_var.get())

            switch = ctk.CTkSwitch(
                right_frame,
                text="启用" if enabled else "禁用",
                font=ctk.CTkFont(size=12),
                variable=switch_var,
                command=make_toggle()
            )
            switch.pack(side="left", padx=(0, 10))

            ctk.CTkButton(
                right_frame,
                text="删除",
                font=ctk.CTkFont(size=12),
                width=60,
                height=28,
                fg_color="#EF4444",
                hover_color="#DC2626",
                command=lambda rid=resource_data["resource_id"]: self._delete_resource(rid)
            ).pack(side="left")

    def _refresh_mapping_list(self):
        """刷新映射列表"""
        for widget in self.mapping_frame.winfo_children():
            widget.destroy()

        resources = self.config.get('cloud_collect.resources', [])
        mappings = self.config.get('cloud_collect.group_mappings', {})

        if not resources:
            empty_label = ctk.CTkLabel(
                self.mapping_frame,
                text="请先添加采集资源",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_label.pack(pady=20)
            return

        # 添加新映射按钮
        add_frame = ctk.CTkFrame(self.mapping_frame, fg_color="transparent")
        add_frame.pack(fill="x", padx=10, pady=10)

        self.new_group_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="群名（必须在QQ中已打开）",
            font=ctk.CTkFont(size=13),
            width=200
        )
        self.new_group_entry.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            add_frame,
            text="➕ 添加群映射",
            font=ctk.CTkFont(size=12),
            width=100,
            command=self._show_add_mapping_dialog
        ).pack(side="left")

        # 显示现有映射
        if not mappings:
            return

        for group_name, resource_ids in mappings.items():
            self._create_mapping_card(group_name, resource_ids, resources)

    def _show_add_mapping_dialog(self):
        """显示添加映射对话框"""
        group_name = self.new_group_entry.get().strip()
        if not group_name:
            messagebox.showwarning("警告", "请输入群名")
            return

        # 显示资源选择对话框
        dialog = ResourceSelectDialog(self, group_name)
        self.wait_window(dialog)

        if dialog.selected_resources:
            mappings = self.config.get('cloud_collect.group_mappings', {})
            mappings[group_name] = dialog.selected_resources
            self.config.set('cloud_collect.group_mappings', mappings)
            self._refresh_mapping_list()
            messagebox.showinfo("成功", f"已为群【{group_name}】配置 {len(dialog.selected_resources)} 个资源")

    def _create_mapping_card(self, group_name, resource_ids, resources):
        """创建映射卡片"""
        card = ctk.CTkFrame(self.mapping_frame)
        card.pack(fill="x", pady=5, padx=10)

        ctk.CTkLabel(
            card,
            text=f"👥 {group_name}",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # 资源名称
        resource_map = {r["resource_id"]: r["name"] for r in resources}
        selected_names = [resource_map.get(rid, "未知") for rid in resource_ids]
        names_text = ", ".join(selected_names) if selected_names else "未配置资源"

        ctk.CTkLabel(
            card,
            text=f"资源: {names_text}",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(anchor="w", padx=10, pady=(0, 10))

        # 删除按钮
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="🗑️ 删除映射",
            font=ctk.CTkFont(size=12),
            width=100,
            height=28,
            fg_color="#EF4444",
            hover_color="#DC2626",
            command=lambda g=group_name: self._delete_mapping(g)
        ).pack(side="right")

    def _delete_mapping(self, group_name):
        """删除映射"""
        mappings = self.config.get('cloud_collect.group_mappings', {})
        if group_name in mappings:
            del mappings[group_name]
            self.config.set('cloud_collect.group_mappings', mappings)
            self._refresh_mapping_list()

    def _toggle_auto(self):
        """切换自动模式"""
        if self.auto_switch.get():
            self._start_auto_collect()
        else:
            self._stop_auto_collect()

    def _start_auto_collect(self):
        """启动自动采集"""
        self.auto_status_label.configure(text="● 自动采集中...", text_color="#10B981")

        interval = int(self.interval_entry.get() or 30)
        self.config.set('cloud_collect.collect_interval', interval)

        self.auto_collect_thread = threading.Thread(
            target=self._auto_collect_loop,
            daemon=True
        )
        self.auto_collect_thread.start()

    def _stop_auto_collect(self):
        """停止自动采集"""
        self.auto_status_label.configure(text="● 自动采集未启动", text_color="gray")
        self.config.set('cloud_collect.auto_collect_enabled', False)

    def _auto_collect_loop(self):
        """自动采集循环"""
        while self.auto_switch.get():
            try:
                self._collect_all_async()
                interval = int(self.interval_entry.get() or 30) * 60
                time.sleep(interval)
            except Exception as e:
                logger.error(f"自动采集出错: {e}")
                time.sleep(60)

    def _collect_all_now(self):
        """立即采集所有资源"""
        if self.is_collecting:
            messagebox.showwarning("警告", "正在采集中，请稍候")
            return

        threading.Thread(target=self._collect_all_async, daemon=True).start()

    def _collect_all_async(self):
        """异步采集所有资源"""
        try:
            self.is_collecting = True
            apikey = self.config.get('cloud_collect.haodanku_apikey', '')
            if not apikey:
                self.after(0, lambda: messagebox.showerror("错误", "请先配置好单库 API Key"))
                return

            self.after(0, lambda: self.auto_status_label.configure(text="● 采集中..."))

            collector = CloudCollector(apikey)
            resources_data = self.config.get('cloud_collect.resources', [])

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            all_items = []
            for res_data in resources_data:
                if not res_data.get("enabled", True):
                    continue

                resource = CloudResource.from_dict(res_data)
                items = loop.run_until_complete(collector.collect_resource(resource))
                all_items.extend(items)

            self.collected_items = all_items
            logger.info(f"采集完成，共 {len(all_items)} 个商品")

            self.after(0, lambda: self.auto_status_label.configure(
                text=f"● 上次采集: {len(all_items)} 个商品",
                text_color="#10B981"
            ))

            # 自动发送到配置的群
            if self.config.get('cloud_collect.auto_send_enabled', False):
                self._auto_send_to_groups(all_items, loop)

        except Exception as e:
            logger.error(f"采集失败: {e}")
            self.after(0, lambda: messagebox.showerror("错误", str(e)))
        finally:
            self.is_collecting = False

    def _auto_send_to_groups(self, items, loop):
        """自动发送到群"""
        from services.qq_automation import QQWindowAutomation
        from services.affiliate import TaobaoAffiliateAPI

        try:
            mappings = self.config.get('cloud_collect.group_mappings', {})
            if not mappings:
                logger.info("没有配置群组映射")
                return

            api = TaobaoAffiliateAPI(
                app_key=self.config.get('taobao.app_key'),
                app_secret=self.config.get('taobao.app_secret'),
                pid=self.config.get('taobao.pid'),
                adzone_id=self.config.get('taobao.adzone_id'),
            )

            sender = QQWindowAutomation()
            if not sender.initialize():
                logger.error("QQ自动化初始化失败")
                return

            # 为每个群发送对应的资源采集的商品
            for group_name, resource_ids in mappings.items():
                # 找出该群关联的资源采集的商品
                # 这里简化处理：发送前N个
                group_items = items[:10]  # 每个群最多10个

                for item in group_items:
                    try:
                        # 转链
                        item_id = item.get("item_id")
                        result = loop.run_until_complete(api.create_promote_url(item_id))

                        # 构造消息
                        message = self._format_collect_message(result)

                        # 发送
                        sender.send_to_qq_group(group_name, message)
                        time.sleep(3)  # 延迟

                    except Exception as e:
                        logger.error(f"发送商品失败: {e}")

                time.sleep(5)  # 群间延迟

        except Exception as e:
            logger.error(f"自动发送失败: {e}")

    def _format_collect_message(self, item: dict) -> str:
        """格式化采集的商品消息"""
        lines = []
        lines.append(f"🔥 {item.get('title', '')}")

        price = item.get("discount_price", item.get("price", 0))
        original_price = item.get("original_price", 0)
        coupon = item.get("coupon_amount", 0)

        if coupon:
            lines.append(f"💰 券后价: ¥{price:.2f}（原价¥{original_price:.2f}, 券¥{coupon:.2f}）")
        else:
            lines.append(f"💰 价格: ¥{price:.2f}")

        commission = item.get("commission_amount", 0)
        if commission:
            lines.append(f"💵 预计佣金: ¥{commission:.2f}")

        sales = item.get("sales_count", 0)
        if sales:
            lines.append(f"📦 已售: {sales} 件")

        # 淘口令
        password = item.get("tao_password", "")
        if password:
            lines.append(f"👉 {password}")

        return "\n".join(lines)


class AddResourceDialog(ctk.CTkToplevel):
    """添加资源对话框"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("添加采集资源")
        self.geometry("500x500")
        self.transient(parent)
        self.grab_set()

        self.result = None

        # 名称
        ctk.CTkLabel(self, text="资源名称:", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=20, pady=(20, 5))
        self.name_entry = ctk.CTkEntry(self, placeholder_text="例如: 今日精选爆款", font=ctk.CTkFont(size=13))
        self.name_entry.pack(fill="x", padx=20, pady=(0, 15))

        # 类型
        ctk.CTkLabel(self, text="资源类型:", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=20, pady=(0, 5))
        self.type_menu = ctk.CTkOptionMenu(
            self,
            values=["今日精选 (top_items)", "好券清单 (itemlist_channel)", "超级搜索 (supersearch)"],
            font=ctk.CTkFont(size=13),
            command=self._on_type_change
        )
        self.type_menu.pack(fill="x", padx=20, pady=(0, 15))

        # 参数配置
        self.params_frame = ctk.CTkFrame(self)
        self.params_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # 关键词输入（超级搜索）
        self.keyword_label = ctk.CTkLabel(self.params_frame, text="搜索关键词:", font=ctk.CTkFont(size=14))
        self.keyword_entry = ctk.CTkEntry(self.params_frame, placeholder_text="例如: 女装 母婴", font=ctk.CTkFont(size=13))

        # 频道选择（好券清单）
        self.channel_label = ctk.CTkLabel(self.params_frame, text="频道类型:", font=ctk.CTkFont(size=14))
        self.channel_menu = ctk.CTkOptionMenu(
            self.params_frame,
            values=["肉丝", "优质", "品牌", "小等"],
            font=ctk.CTkFont(size=13)
        )

        # 排序
        self.sort_label = ctk.CTkLabel(self.params_frame, text="排序方式:", font=ctk.CTkFont(size=14))
        self.sort_menu = ctk.CTkOptionMenu(
            self.params_frame,
            values=["综合", "销量", "价格升序", "价格降序", "佣金比例"],
            font=ctk.CTkFont(size=13)
        )

        self._on_type_change("今日精选 (top_items)")

        # 按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(size=13),
            width=100,
            command=self.destroy
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame,
            text="确定",
            font=ctk.CTkFont(size=13),
            width=100,
            fg_color="#10B981",
            hover_color="#059669",
            command=self._on_confirm
        ).pack(side="right")

    def _on_type_change(self, value):
        """类型变化"""
        for widget in self.params_frame.winfo_children():
            widget.pack_forget()

        type_str = value
        if "top_items" in type_str:
            self.sort_label.pack(anchor="w", pady=(5, 5))
            self.sort_menu.pack(fill="x", pady=(0, 10))
        elif "itemlist_channel" in type_str:
            self.channel_label.pack(anchor="w", pady=(5, 5))
            self.channel_menu.pack(fill="x", pady=(0, 10))
            self.sort_label.pack(anchor="w", pady=(5, 5))
            self.sort_menu.pack(fill="x", pady=(0, 10))
        elif "supersearch" in type_str:
            self.keyword_label.pack(anchor="w", pady=(5, 5))
            self.keyword_entry.pack(fill="x", pady=(0, 10))
            self.sort_label.pack(anchor="w", pady=(5, 5))
            self.sort_menu.pack(fill="x", pady=(0, 10))

    def _on_confirm(self):
        """确认"""
        name = self.name_entry.get().strip()
        if not name:
            return

        type_str = self.type_menu.get()
        sort_value = ["综合", "销量", "价格升序", "价格降序", "佣金比例"].index(self.sort_menu.get())

        if "top_items" in type_str:
            self.result = {
                "name": name,
                "type": "top_items",
                "params": {"back": 100, "sort": sort_value}
            }
        elif "itemlist_channel" in type_str:
            self.result = {
                "name": name,
                "type": "itemlist_channel",
                "params": {
                    "channel_type": self.channel_menu.get(),
                    "back": 100,
                    "sort": sort_value
                }
            }
        elif "supersearch" in type_str:
            keyword = self.keyword_entry.get().strip()
            if not keyword:
                return
            self.result = {
                "name": name,
                "type": "supersearch",
                "params": {"keyword": keyword, "back": 100, "sort": sort_value}
            }

        self.destroy()


class ResourceSelectDialog(ctk.CTkToplevel):
    """资源选择对话框"""

    def __init__(self, parent, group_name):
        super().__init__(parent)
        self.title(f"为群【{group_name}】选择资源")
        self.geometry("400x500")
        self.transient(parent)
        self.grab_set()

        self.selected_resources = []
        self.group_name = group_name

        ctk.CTkLabel(self, text=f"为群【{group_name}】选择采集资源:",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))

        # 资源列表（多选）
        self.checkbox_vars = {}
        config = parent.config
        resources = config.get('cloud_collect.resources', [])
        mappings = config.get('cloud_collect.group_mappings', {})
        existing = mappings.get(group_name, [])

        for res in resources:
            var = ctk.BooleanVar(value=res["resource_id"] in existing)
            self.checkbox_vars[res["resource_id"]] = var

            cb = ctk.CTkCheckBox(
                self,
                text=res.get("name", ""),
                variable=var,
                font=ctk.CTkFont(size=13)
            )
            cb.pack(anchor="w", padx=20, pady=5)

        # 按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(20, 20))

        ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(size=13),
            width=100,
            command=self.destroy
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame,
            text="确定",
            font=ctk.CTkFont(size=13),
            width=100,
            fg_color="#10B981",
            hover_color="#059669",
            command=self._on_confirm
        ).pack(side="right")

    def _on_confirm(self):
        """确认"""
        self.selected_resources = [
            rid for rid, var in self.checkbox_vars.items() if var.get()
        ]
        self.destroy()