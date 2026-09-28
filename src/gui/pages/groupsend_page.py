"""
群发页面
"""
import customtkinter as ctk
from typing import Callable
import threading
from tkinter import messagebox
import json

from services.qq_automation import QQWindowAutomation, send_to_qq_group, send_to_multiple_groups
from core.config import Config


class GroupSendPage(ctk.CTkFrame):
    """QQ 群发页面"""

    def __init__(self, parent, config: Config):
        super().__init__(parent, fg_color="transparent")
        self.config = config
        self.qq_automation = QQWindowAutomation()
        self.groups = []
        self.last_message = ""

        self._create_widgets()

    def _create_widgets(self):
        """创建组件"""
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # 标题
        title = ctk.CTkLabel(
            container,
            text="📢 QQ 群发",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(0, 30), anchor="w")

        # 提示
        hint_frame = ctk.CTkFrame(container, fg_color="#FEF3C7", border_color="#F59E0B", border_width=2)
        hint_frame.pack(fill="x", pady=(0, 20))

        hint_label = ctk.CTkLabel(
            hint_frame,
            text="⚠️ 注意事项：\n"
                 "1. 请先登录 QQ 并打开 NTQQ\n"
                 "2. 在 QQ 中打开所有需要发送的群聊窗口\n"
                 "3. 确保 QQ 窗口未被最小化\n"
                 "4. 发送过程中不要操作鼠标键盘\n"
                 "5. 建议添加延迟，避免被封",
            font=ctk.CTkFont(size=13),
            text_color="#92400E",
            justify="left"
        )
        hint_label.pack(anchor="w", padx=15, pady=10)

        # 群列表管理
        groups_frame = ctk.CTkFrame(container)
        groups_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            groups_frame,
            text="群列表",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # 群列表显示
        self.groups_listbox = ctk.CTkTextbox(
            groups_frame,
            height=150,
            font=ctk.CTkFont(size=13),
        )
        self.groups_listbox.pack(fill="x", padx=15, pady=(0, 10))

        # 群操作按钮
        btn_frame = ctk.CTkFrame(groups_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkButton(
            btn_frame,
            text="➕ 添加",
            font=ctk.CTkFont(size=13),
            width=100,
            command=self._add_group
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="📂 导入",
            font=ctk.CTkFont(size=13),
            width=100,
            command=self._import_groups
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="🗑️ 清空",
            font=ctk.CTkFont(size=13),
            width=100,
            command=self._clear_groups
        ).pack(side="left")

        # 消息内容
        message_frame = ctk.CTkFrame(container)
        message_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            message_frame,
            text="发送内容",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        self.message_textbox = ctk.CTkTextbox(
            message_frame,
            height=200,
            font=ctk.CTkFont(size=14),
            border_width=2,
            border_color=("gray70", "gray30")
        )
        self.message_textbox.pack(fill="x", padx=15, pady=(0, 15))

        # 发送选项
        options_frame = ctk.CTkFrame(container)
        options_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            options_frame,
            text="发送选项",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # 延迟设置
        delay_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        delay_frame.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(delay_frame, text="发送延迟（秒）：", font=ctk.CTkFont(size=14)).pack(side="left", padx=(0, 10))

        self.delay_slider = ctk.CTkSlider(
            delay_frame,
            from_=1,
            to=10,
            number_of_steps=9,
            width=300
        )
        self.delay_slider.set(3)
        self.delay_slider.pack(side="left", padx=(0, 10))

        self.delay_label = ctk.CTkLabel(delay_frame, text="3秒", font=ctk.CTkFont(size=14))
        self.delay_label.pack(side="left")

        self.delay_slider.configure(command=lambda v: self.delay_label.configure(text=f"{int(float(v))}秒"))

        # 静默模式
        silent_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        silent_frame.pack(fill="x", padx=15, pady=10)

        self.silent_var = ctk.BooleanVar(value=True)
        self.silent_checkbox = ctk.CTkCheckBox(
            silent_frame,
            text="静默发送（不抢占焦点，适合后台运行）",
            font=ctk.CTkFont(size=14),
            variable=self.silent_var,
            onvalue=True,
            offvalue=False
        )
        self.silent_checkbox.pack(side="left")

        # 静默模式说明
        self.silent_hint = ctk.CTkLabel(
            silent_frame,
            text="💡 静默模式不抢焦点，但需提前打开群窗口",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.silent_hint.pack(side="left", padx=(15, 0))

        # 发送按钮
        self.send_btn = ctk.CTkButton(
            container,
            text="🚀 开始群发",
            font=ctk.CTkFont(size=18, weight="bold"),
            height=60,
            fg_color="#7C3AED",
            hover_color="#6D28D9",
            command=self._on_send
        )
        self.send_btn.pack(pady=(0, 20), fill="x")

        # 进度显示
        self.progress_frame = ctk.CTkFrame(container)
        self.progress_frame.pack_forget()

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="准备发送...",
            font=ctk.CTkFont(size=16)
        )
        self.progress_label.pack(pady=(20, 10))

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 20))

    def refresh(self):
        """刷新"""
        pass

    def _add_group(self):
        """添加群"""
        dialog = ctk.CTkInputDialog(
            text="请输入群名称：",
            title="添加群"
        )
        group_name = dialog.get_input()

        if group_name and group_name not in self.groups:
            self.groups.append(group_name)
            self._update_groups_list()

    def _import_groups(self):
        """导入群列表"""
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="选择群列表文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    groups = [line.strip() for line in f if line.strip()]

                self.groups.extend(groups)
                self._update_groups_list()
                messagebox.showinfo("成功", f"已导入 {len(groups)} 个群")

            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")

    def _clear_groups(self):
        """清空群列表"""
        if messagebox.askyesno("确认", "确定要清空群列表吗？"):
            self.groups.clear()
            self._update_groups_list()

    def _update_groups_list(self):
        """更新群列表显示"""
        self.groups_listbox.delete("1.0", "end")

        if self.groups:
            for i, group in enumerate(self.groups, 1):
                self.groups_listbox.insert("end", f"{i}. {group}\n")
        else:
            self.groups_listbox.insert("end", "暂无群\n")

    def _on_send(self):
        """开始发送"""
        if not self.groups:
            messagebox.showwarning("警告", "请先添加群列表")
            return

        message = self.message_textbox.get("1.0", "end").strip()
        if not message:
            messagebox.showwarning("警告", "请输入发送内容")
            return

        # 确认对话框
        silent_mode = self.silent_var.get()
        mode_text = "静默模式（不抢焦点）" if silent_mode else "可见模式（会抢焦点）"

        result = messagebox.askyesno(
            "确认发送",
            f"即将发送消息到 {len(self.groups)} 个群\n\n"
            f"模式：{mode_text}\n"
            f"延迟：{int(self.delay_slider.get())} 秒\n\n"
            f"请确保：\n"
            f"1. QQ 已登录\n"
            f"2. QQ 窗口未被最小化\n\n"
            f"是否继续？"
        )

        if not result:
            return

        # 开始发送
        self.progress_frame.pack(fill="x", pady=(0, 20))
        self.send_btn.configure(state="disabled")

        thread = threading.Thread(
            target=self._send_thread,
            args=(message, int(self.delay_slider.get()), silent_mode)
        )
        thread.daemon = True
        thread.start()

    def _send_thread(self, message: str, delay: int, silent: bool = True):
        """发送线程"""
        try:
            # 初始化 sender
            from services.qq_automation import QQWindowAutomation
            sender = QQWindowAutomation()

            # 先初始化，扫描所有打开的群窗口
            if not sender.initialize():
                self.after(0, lambda: messagebox.showerror(
                    "初始化失败",
                    "未找到 QQ 窗口或群窗口\n\n"
                    "请确保：\n"
                    "1. QQ 已登录\n"
                    "2. 已在 QQ 中打开需要发送的群聊窗口"
                ))
                self.after(0, lambda: self.send_btn.configure(state="normal"))
                return

            total = len(self.groups)
            success_count = 0
            failed_groups = []  # 记录失败的群

            for i, group in enumerate(self.groups, 1):
                # 更新进度
                self.after(0, lambda p=i/total: self.progress_bar.set(p))
                self.after(0, lambda c=i, t=total: self.progress_label.configure(
                    text=f"正在发送到第 {c}/{t} 个群: {group}..."
                ))

                # 发送（静默/可见模式）
                if sender.send_to_qq_group(group, message, silent=silent):
                    success_count += 1
                else:
                    failed_groups.append(group)

                # 延迟
                if i < total:
                    time.sleep(delay)

            failed_count = len(failed_groups)

            # 完成
            self.after(0, lambda: self.progress_bar.set(1.0))
            mode_str = "静默" if silent else "可见"
            self.after(0, lambda: self.progress_label.configure(
                text=f"发送完成！({mode_str}模式) 成功: {success_count}, 失败: {failed_count}"
            ))
            self.after(0, lambda: self.send_btn.configure(state="normal"))

            # 提示（包含详细的失败信息）
            if failed_count > 0:
                failed_list = "\n".join([f"  • {g}" for g in failed_groups])
                hint = ""
                if success_count == 0:
                    hint = (
                        "\n\n💡 排查建议：\n"
                        "1. 确认目标群已在QQ中打开（不能最小化）\n"
                        "2. 确认群名完全匹配（可打开QQ窗口查看实际标题）\n"
                        "3. 查看『异常日志』菜单了解详细原因\n"
                        "4. 尝试切换到『可见模式』（关闭静默模式）"
                    )
                self.after(0, lambda: messagebox.showwarning(
                    "发送完成",
                    f"批量发送完成 ({mode_str}模式)\n\n"
                    f"✓ 成功: {success_count}\n"
                    f"✗ 失败: {failed_count}\n\n"
                    f"失败的群:\n{failed_list}"
                    f"{hint}"
                ))
            else:
                self.after(0, lambda: messagebox.showinfo(
                    "发送完成",
                    f"批量发送完成！({mode_str}模式)\n\n"
                    f"✓ 成功: {success_count}\n"
                    f"✗ 失败: 0"
                ))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", str(e)))
            self.after(0, lambda: self.send_btn.configure(state="normal"))
