"""
QQ 窗口自动化服务
基于 Windows API 实现 QQ/NTQQ 的窗口识别和自动发送
"""
import time
import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32clipboard
import win32process
import pyautogui
from typing import Optional, List, Tuple
from loguru import logger

# 禁用 PyAutoGUI 的安全机制（0,0 坐标保护），多显示器环境下会误触发
pyautogui.FAILSAFE = False
# 操作间隔，避免操作太快
pyautogui.PAUSE = 0.1


# QQ / NTQQ 进程名（用于按进程过滤窗口，避免误抓其他 Chromium 程序）
QQ_PROCESS_NAMES = {
    "qq.exe", "ntqq.exe", "qqprotect.exe",
    "qqexternal.exe", "txplatform.exe",
}


def _is_qq_process(hwnd: int) -> bool:
    """判断窗口是否属于 QQ / NTQQ 进程"""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return False
        # 进程快照里查进程名
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        PROCESS_VM_READ = 0x0010
        h = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid
        )
        if not h:
            return False
        try:
            buf = ctypes.create_unicode_buffer(512)
            size = wintypes.DWORD(512)
            ctypes.windll.kernel32.QueryFullProcessImageNameW(
                h, 0, buf, ctypes.byref(size)
            )
            exe = buf.value.split("\\")[-1].lower()
            return exe in QQ_PROCESS_NAMES
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    except Exception:
        return False

# Windows API 常量
WM_SETTEXT = 0x000C
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
WM_COPYDATA = 0x004A
WM_PASTE = 0x0302
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D


class QQWindowManager:
    """QQ 窗口管理器"""

    def __init__(self):
        self.qq_hwnd = None
        self.chat_hwnd = None
        self.last_active_window = None
        self.group_windows = {}  # 群名 -> 窗口句柄映射

    def find_qq_window(self, title_keyword: str = "QQ") -> Optional[int]:
        """
        查找 QQ 主窗口（增强版：兼容新版NTQQ）

        Args:
            title_keyword: 窗口标题关键词

        Returns:
            窗口句柄，如果未找到返回 None
        """
        candidates = []

        def callback(hwnd, windows):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)

            # 通过进程名过滤：必须是 QQ/NTQQ 进程（最可靠）
            if not _is_qq_process(hwnd):
                return True

            # 排除子窗口（只看顶层窗口）
            if win32gui.GetParent(hwnd) != 0:
                return True

            # 排除极小的窗口（可能是无效控件）
            rect = win32gui.GetWindowRect(hwnd)
            w, h = rect[2] - rect[0], rect[3] - rect[1]
            if w < 80:  # 只限制最小宽度，不限制高度（NTQQ 最小化后高度可能 < 50）
                return True

            # 通过类名识别
            qq_classes = [
                "TXGuiFoundation", "StandardFrame", "TMainForm",
                "QQMainFrame", "AfxFrameOrView70",
                "Chrome_WidgetWin_1", "Chrome_RenderWidgetHostHWND",
            ]
            if any(qc in class_name for qc in qq_classes):
                score = 10

                # 标题包含"QQ"或"NTQQ" → 主窗口
                if "QQ" in title or "NTQQ" in title:
                    score += 15
                # 标题是联系人/群名（不包含QQ） → 聊天窗口
                else:
                    score -= 5
                # 窗口尺寸较大 → 主窗口
                if w > 500 and h > 300:
                    score += 3

                windows.append((hwnd, title, class_name, score))
            return True

        win32gui.EnumWindows(callback, candidates)

        if candidates:
            # 按分数排序
            candidates.sort(key=lambda x: x[3], reverse=True)
            hwnd, title, class_name, score = candidates[0]

            # 如果最高分 < 10，说明没有明确的主窗口，返回 None
            if score < 10:
                logger.warning(f"找到的窗口分数过低 (score={score})，可能不是 QQ 主窗口")
                return None

            self.qq_hwnd = hwnd
            logger.info(f"找到 QQ 窗口: hwnd={hwnd}, title='{title}', class={class_name}, score={score}")
            return hwnd

        logger.warning("未找到 QQ 窗口")
        return None

    def scan_all_group_windows(self) -> dict:
        """
        扫描所有可能的群窗口（增强版：兼容 NTQQ 的独立窗口/弹窗模式）

        Returns:
            群名字典 {群名/标题: 窗口句柄}
        """
        self.group_windows.clear()

        # QQ群窗口常见的类名（含旧版原生类 + NTQQ 的 Chromium 类）
        qq_chat_classes = [
            # 旧版原生
            "TXGuiFoundation", "StandardFrame", "TMainForm",
            "ChatWnd", "QQChatWindow", "AfxFrameOrView70",
            # 新版 NTQQ（独立窗口 / 弹出窗口 都是这个类）
            "Chrome_WidgetWin_1", "Chrome_RenderWidgetHostHWND",
        ]

        # 明确排除的非群窗口（系统/工具类应用）
        excluded_keywords = [
            "Program Manager", "任务栏", "Taskbar",
            "Settings", "设置", "Control Panel",
            "Windows 输入体验", "Windows Input Experience",
            "文件资源管理器", "File Explorer",
            "Navicat", "Studio -", "JetBrains",
            "Dist -", "money", "ragOne",
            "agent-from-zero-to-hero",
            "OnChain", "OnChain-X",
            "CC Switch", "ccswitch",
            "网易UU远程", "UURemote",
            "version management", "版本管理",
            "Microsoft Edge", "Edge",
            "微信", "WeChat", "wxwork",
            "飞书", "Lark", "Feishu",
            "tenant-admin", "com.ccswitch",
        ]

        def callback(hwnd, groups):
            if not win32gui.IsWindowVisible(hwnd):
                return True

            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)

            # 主窗口跳过
            if hwnd == self.qq_hwnd:
                return True

            # 必须有标题
            if not title or len(title.strip()) < 1:
                return True

            # 进程过滤：只接受 QQ/NTQQ 进程（排除 Chrome 浏览器等）
            if not _is_qq_process(hwnd):
                return True

            # 通过类名识别（QQ群窗口特征）
            is_qq_chat = any(qc in class_name for qc in qq_chat_classes)

            if is_qq_chat:
                groups[title] = hwnd
                logger.debug(f"通过类名识别QQ群: {title} ({class_name})")
                return True

            # 排除明显的非QQ窗口
            for ex in excluded_keywords:
                if ex in title:
                    return True

            # 启发式：顶级窗口，尺寸合理，可能是群
            try:
                rect = win32gui.GetWindowRect(hwnd)
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                parent = win32gui.GetParent(hwnd)

                # QQ群窗口特征：宽度>400, 高度>300，顶级窗口
                if width >= 400 and height >= 300 and parent == 0:
                    # 通过类名启发：QQ群窗口通常用特定类名
                    # 一些可能的类名前缀
                    likely_qk = class_name in [
                        "StandardFrame", "TXGuiFoundation",
                        "TMainForm", "AfxFrameOrView70",
                        "WindowsForms10.Window.0.app",
                        "TContentsForm",
                        "TUnifiedFriendGroupList",
                        "TUnifiedGroupList",
                        "Chrome_WidgetWin_1",
                        "Chrome_RenderWidgetHostHWND",
                    ]

                    # 如果类名可疑，加入候选
                    if likely_qk:
                        groups[title] = hwnd
                        logger.debug(f"通过类名启发识别QQ群: {title} ({class_name})")
                        return True

            except:
                pass

            return True

        win32gui.EnumWindows(callback, self.group_windows)

        logger.info(f"扫描到 {len(self.group_windows)} 个可能的群窗口")
        for name, hwnd in list(self.group_windows.items())[:50]:
            logger.debug(f"  窗口: {name} (hwnd={hwnd})")

        return self.group_windows

    def find_chat_window(self, group_name: str) -> Optional[int]:
        """
        查找群聊窗口

        Args:
            group_name: 群名称

        Returns:
            窗口句柄
        """
        # 先查找缓存
        if group_name in self.group_windows:
            hwnd = self.group_windows[group_name]
            if win32gui.IsWindow(hwnd):
                logger.info(f"找到群聊窗口(缓存): hwnd={hwnd}, title={group_name}")
                self.chat_hwnd = hwnd
                return hwnd

        # 重新扫描
        self.scan_all_group_windows()

        if group_name in self.group_windows:
            hwnd = self.group_windows[group_name]
            if win32gui.IsWindow(hwnd):
                logger.info(f"找到群聊窗口: hwnd={hwnd}, title={group_name}")
                self.chat_hwnd = hwnd
                return hwnd

        logger.warning(f"未找到群聊窗口: {group_name}")
        return None

    def bring_window_to_front(self, hwnd: int) -> bool:
        """
        将窗口置前（多显示器兼容版）

        Args:
            hwnd: 窗口句柄

        Returns:
            是否成功
        """
        try:
            # 如果窗口最小化，先恢复
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            # 获取窗口所在显示器
            hmonitor = ctypes.windll.user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONULL

            # 置前
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.3)  # 等待窗口激活

            # 验证是否成功
            foreground = win32gui.GetForegroundWindow()
            return foreground == hwnd

        except Exception as e:
            logger.error(f"置前窗口失败: {e}")
            return False

    def get_window_rect(self, hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        """
        获取窗口位置和大小

        Returns:
            (left, top, right, bottom)
        """
        try:
            rect = win32gui.GetWindowRect(hwnd)
            return rect
        except Exception as e:
            logger.error(f"获取窗口位置失败: {e}")
            return None

    def find_input_control(self, chat_hwnd: int) -> Optional[int]:
        """
        查找QQ群窗口内的输入框控件（增强版：兼容新版QQ/NTQQ）

        Args:
            chat_hwnd: 群窗口句柄

        Returns:
            输入框控件句柄
        """
        try:
            # 所有可能的输入框类名（兼容各种QQ版本）
            edit_class_names = [
                "RichEdit20W", "RICHEDIT20W",
                "Edit",
                "TMEdit",
                "IMRichEdit", "QQLightRichEdit",
                "StandardInputEdit",
                "TXWeikeEdit",
                "TChatInput",
                "Chrome_RenderWidgetHostHWND",
            ]

            all_candidates = []

            def callback(hwnd, candidates):
                """枚举子窗口回调"""
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                class_name = win32gui.GetClassName(hwnd)

                # 是否是候选
                is_candidate = False
                for name in edit_class_names:
                    if name in class_name or class_name in name:
                        is_candidate = True
                        break

                if is_candidate:
                    try:
                        rect = win32gui.GetWindowRect(hwnd)
                    except:
                        rect = None
                    candidates.append({
                        "hwnd": hwnd,
                        "class": class_name,
                        "rect": rect
                    })
                    logger.debug(f"找到候选控件: hwnd={hwnd}, class={class_name}")

                return True

            # 1. 先枚举群窗口的直接子控件
            win32gui.EnumChildWindows(chat_hwnd, callback, all_candidates)

            if not all_candidates:
                # 2. 没找到就再扫一遍（包括所有后代）
                logger.debug("未找到直接子控件，尝试深度扫描...")
                win32gui.EnumChildWindows(chat_hwnd, callback, all_candidates)

            if not all_candidates:
                logger.warning("未找到任何输入框候选控件")
                # 输出群窗口所有可见控件，辅助调试
                def debug_callback(hwnd, debug_list):
                    if win32gui.IsWindowVisible(hwnd):
                        try:
                            debug_list.append({
                                "hwnd": hwnd,
                                "class": win32gui.GetClassName(hwnd),
                                "text": win32gui.GetWindowText(hwnd)[:30]
                            })
                        except:
                            pass
                    return True
                debug_list = []
                win32gui.EnumChildWindows(chat_hwnd, debug_callback, debug_list)
                for item in debug_list[:30]:
                    logger.debug(f"  [调试] hwnd={item['hwnd']}, class={item['class']}, text={item['text']}")
                return None

            # 3. 选最合适的控件（按优先级）
            # 优先级1：RichEdit
            for cand in all_candidates:
                if "RichEdit" in cand["class"]:
                    logger.info(f"找到输入框(优先级1): hwnd={cand['hwnd']}, class={cand['class']}")
                    return cand["hwnd"]

            # 优先级2：Edit
            for cand in all_candidates:
                if "Edit" in cand["class"]:
                    logger.info(f"找到输入框(优先级2): hwnd={cand['hwnd']}, class={cand['class']}")
                    return cand["hwnd"]

            # 优先级3：位置启发式（窗口底部，宽度较大）
            try:
                chat_rect = win32gui.GetWindowRect(chat_hwnd)
                chat_height = chat_rect[3] - chat_rect[1]
                chat_width = chat_rect[2] - chat_rect[0]

                for cand in all_candidates:
                    if not cand["rect"]:
                        continue
                    cand_rect = cand["rect"]
                    cand_height = cand_rect[3] - cand_rect[1]
                    cand_width = cand_rect[2] - cand_rect[0]
                    # 输入框特征：底部50%+，宽度>40%
                    rel_y = (cand_rect[1] - chat_rect[1]) / chat_height
                    rel_width = cand_width / chat_width
                    # 高度要合理（>20px）
                    if rel_y > 0.5 and rel_width > 0.4 and cand_height > 20:
                        logger.info(f"找到输入框(优先级3-位置): hwnd={cand['hwnd']}, class={cand['class']}")
                        return cand["hwnd"]
            except Exception as e:
                logger.debug(f"位置启发式失败: {e}")

            # 优先级4：首个候选
            logger.info(f"找到输入框(优先级4): hwnd={all_candidates[0]['hwnd']}, class={all_candidates[0]['class']}")
            return all_candidates[0]["hwnd"]

        except Exception as e:
            logger.error(f"查找输入框失败: {e}")
            return None


class ClipboardManager:
    """剪贴板管理器"""

    @staticmethod
    def set_text(text: str) -> bool:
        """
        设置剪贴板文本

        Args:
            text: 要设置的文本

        Returns:
            是否成功
        """
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            logger.debug(f"剪贴板已设置: {text[:50]}...")
            return True

        except Exception as e:
            logger.error(f"设置剪贴板失败: {e}")
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            return False

    @staticmethod
    def get_text() -> Optional[str]:
        """获取剪贴板文本"""
        try:
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return data

        except Exception as e:
            logger.error(f"获取剪贴板失败: {e}")
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            return None


class QQAutoSender:
    """QQ 自动发送器"""

    def __init__(self):
        self.window_manager = QQWindowManager()
        self.clipboard = ClipboardManager()
        self.is_initialized = False

    def initialize(self) -> bool:
        """
        初始化，查找 QQ 窗口并扫描所有群窗口

        Returns:
            是否成功
        """
        logger.info("正在初始化 QQ 自动化...")

        # 查找 QQ 主窗口
        hwnd = self.window_manager.find_qq_window()
        if not hwnd:
            logger.error("未找到 QQ 窗口，请确保 QQ 已登录")
            return False

        # 扫描所有群窗口
        groups = self.window_manager.scan_all_group_windows()
        if not groups:
            logger.warning("未找到任何群窗口，请先打开需要发送的群")
            return False

        self.is_initialized = True
        logger.info(f"QQ 自动化初始化成功，找到 {len(groups)} 个群窗口")
        return True

    def send_message_to_group(self, group_name: str, message: str) -> bool:
        """
        发送消息到指定群

        Args:
            group_name: 群名称
            message: 消息内容

        Returns:
            是否成功
        """
        if not self.is_initialized:
            logger.error("未初始化")
            return False

        logger.info(f"正在发送消息到群: {group_name}")

        try:
            # 1. 查找群窗口
            chat_hwnd = self.window_manager.find_chat_window(group_name)
            if not chat_hwnd:
                logger.error(f"未找到群窗口: {group_name}")
                return False

            # 2. 激活群窗口
            if not self.window_manager.bring_window_to_front(chat_hwnd):
                logger.error(f"无法激活窗口: {group_name}")
                return False

            time.sleep(0.3)

            # 3. 点击输入框（窗口底部中间）
            rect = self.window_manager.get_window_rect(chat_hwnd)
            if rect:
                input_x = (rect[0] + rect[2]) // 2
                input_y = rect[3] - 100
                pyautogui.click(input_x, input_y)
                time.sleep(0.2)

            # 4. 设置剪贴板
            if not self.clipboard.set_text(message):
                return False

            # 5. 粘贴
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.2)

            # 6. 发送
            pyautogui.press('enter')
            time.sleep(0.3)

            logger.info(f"消息发送成功: {group_name}")
            return True

        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    def send_message_to_multiple_groups(
        self,
        groups: List[str],
        message: str,
        delay_between: float = 2.0
    ) -> Tuple[int, int]:
        """
        批量发送到多个群

        Args:
            groups: 群名称列表
            message: 消息内容
            delay_between: 群之间的延迟（秒）

        Returns:
            (成功数, 失败数)
        """
        success_count = 0
        failed_count = 0

        logger.info(f"开始批量发送: {len(groups)} 个群")

        for i, group in enumerate(groups, 1):
            logger.info(f"发送到第 {i}/{len(groups)} 个群: {group}")

            if self.send_message_to_group(group, message):
                success_count += 1
            else:
                failed_count += 1

            # 延迟，避免被封
            if i < len(groups):
                time.sleep(delay_between)

        logger.info(f"批量发送完成: 成功 {success_count}, 失败 {failed_count}")
        return success_count, failed_count


class QQWindowAutomation:
    """
    QQ 窗口自动化（简化版）

    基于已打开的群窗口发送消息，不需要搜索
    """

    def __init__(self):
        self.window_manager = QQWindowManager()
        self.is_initialized = False

    def initialize(self) -> bool:
        """
        初始化，扫描所有打开的群窗口

        Returns:
            是否成功
        """
        logger.info("正在初始化 QQ 自动化...")

        # 查找 QQ 主窗口
        hwnd = self.window_manager.find_qq_window()
        if not hwnd:
            logger.error("未找到 QQ 窗口，请确保 QQ 已登录")
            return False

        # 扫描所有群窗口
        groups = self.window_manager.scan_all_group_windows()
        if not groups:
            logger.warning("未找到任何群窗口，请先打开需要发送的群")
            return False

        self.is_initialized = True
        logger.info(f"QQ 自动化初始化成功，找到 {len(groups)} 个群窗口")
        return True

    @staticmethod
    def send_to_qq_group(group_name: str, message: str, qq_window_title: str = "QQ", silent: bool = True) -> bool:
        """
        发送消息到 QQ 群

        Args:
            group_name: 群名称
            message: 消息内容
            qq_window_title: QQ 窗口标题关键词
            silent: 是否静默发送（True=不抢焦点，False=传统模式）

        Returns:
            是否成功
        """
        try:
            # 创建临时管理器
            wm = QQWindowManager()

            # 1. 查找 QQ 主窗口
            hwnd = wm.find_qq_window(qq_window_title)
            if not hwnd:
                logger.error("[失败原因] 未找到 QQ 主窗口，请确保 QQ 已登录并打开")
                return False

            # 2. 扫描所有群窗口（包括独立弹出窗口）
            groups = wm.scan_all_group_windows()
            if not groups:
                logger.error("[失败原因] 未找到任何群窗口，请先打开需要发送的群聊窗口")
                return False

            # 3. 查找目标群窗口
            if group_name not in groups:
                # 模糊匹配：群名包含输入的群名
                matched = None
                for gname in groups.keys():
                    if group_name in gname or gname in group_name:
                        matched = gname
                        break

                if not matched:
                    logger.error(f"[失败原因] 未找到群窗口: {group_name}")
                    logger.error(f"  当前已打开的群: {', '.join(groups.keys())}")
                    return False

                logger.info(f"模糊匹配成功: '{group_name}' -> '{matched}'")
                group_name = matched
                chat_hwnd = groups[matched]
            else:
                chat_hwnd = groups[group_name]

            # 4. 发送消息
            if silent:
                return QQWindowAutomation._send_silent(chat_hwnd, message, group_name)
            else:
                return QQWindowAutomation._send_visible(chat_hwnd, message, group_name, wm)

        except Exception as e:
            logger.error(f"[失败原因] 发送异常: {e}")
            return False

    @staticmethod
    def _send_silent(chat_hwnd: int, message: str, group_name: str = "") -> bool:
        """
        静默发送：通过 PostMessage 后台发送，不抢焦点

        原理：
        1. 用 PostMessage 向输入框发送 WM_PASTE 和回车
        2. 全程不调用 SetForegroundWindow，不干扰用户当前操作
        3. 通过剪贴板传递文本，但恢复原有剪贴板内容

        Args:
            chat_hwnd: 群窗口句柄
            message: 消息内容
            group_name: 群名称（日志用）

        Returns:
            是否成功
        """
        try:
            logger.info(f"[静默模式] 准备发送到: {group_name} (hwnd={chat_hwnd})")

            # 1. 查找输入框
            wm = QQWindowManager()
            input_hwnd = wm.find_input_control(chat_hwnd)

            if not input_hwnd:
                logger.warning("[静默模式] 未找到输入框控件，尝试备用方案...")
                # 备用方案：直接用 PostMessage 给群窗口本身
                input_hwnd = chat_hwnd

            # 2. 保存用户原来的剪贴板内容
            import win32clipboard
            original_clipboard = None
            try:
                win32clipboard.OpenClipboard()
                try:
                    original_clipboard = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                except:
                    pass
                win32clipboard.CloseClipboard()
            except:
                pass

            # 3. 设置剪贴板（仅后台设置，不激活任何窗口）
            ClipboardManager.set_text(message)
            time.sleep(0.1)

            # 4. 通过 PostMessage 后台发送粘贴
            logger.info("[静默模式] 发送粘贴命令...")
            win32gui.PostMessage(input_hwnd, win32con.WM_PASTE, 0, 0)
            time.sleep(0.2)

            # 5. 发送回车
            logger.info("[静默模式] 发送回车...")
            win32gui.PostMessage(input_hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
            time.sleep(0.05)
            win32gui.PostMessage(input_hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
            time.sleep(0.2)

            # 6. 恢复用户原来的剪贴板
            if original_clipboard is not None:
                try:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, original_clipboard)
                    win32clipboard.CloseClipboard()
                    logger.debug("[静默模式] 剪贴板已恢复")
                except:
                    pass

            logger.info(f"[静默模式] ✓ 发送完成: {group_name}")
            return True

        except Exception as e:
            logger.error(f"[静默模式] 发送失败: {e}")
            return False

    @staticmethod
    def _send_visible(chat_hwnd: int, message: str, group_name: str = "", wm: QQWindowManager = None) -> bool:
        """
        可见模式：物理模拟点击（适合 NTQQ 等 Electron 应用）

        Args:
            chat_hwnd: 群窗口句柄
            message: 消息内容
            group_name: 群名称
            wm: 窗口管理器实例

        Returns:
            是否成功
        """
        if wm is None:
            wm = QQWindowManager()

        try:
            # 激活窗口
            if not wm.bring_window_to_front(chat_hwnd):
                logger.warning(f"无法激活窗口，尝试继续...")

            time.sleep(0.3)

            # 获取窗口位置
            rect = wm.get_window_rect(chat_hwnd)
            if not rect:
                logger.error("[失败原因] 无法获取窗口位置")
                return False

            left, top, right, bottom = rect
            width = right - left
            height = bottom - top

            logger.info(f"窗口位置: ({left}, {top}) - ({right}, {bottom}), 尺寸: {width}x{height}")

            # 计算输入框位置
            input_x = left + width // 2
            input_y = bottom - int(height * 0.22)

            logger.info(f"输入框估算位置: ({input_x}, {input_y})")

            # 点击输入框
            logger.info(f"点击输入框...")
            try:
                pyautogui.click(input_x, input_y)
            except pyautogui.FailSafeException:
                logger.warning(f"PyAutoGUI 安全机制触发，尝试继续...")
                pyautogui.FAILSAFE = False
                pyautogui.click(input_x, input_y)

            time.sleep(0.3)

            # 检查焦点是否还在目标窗口
            fg_hwnd = win32gui.GetForegroundWindow()
            if fg_hwnd != chat_hwnd:
                logger.warning(f"点击后焦点丢失: 期望 hwnd={chat_hwnd}, 实际 hwnd={fg_hwnd}")
                logger.warning(f"  尝试重新激活...")
                wm.bring_window_to_front(chat_hwnd)
                time.sleep(0.3)

            # 剪贴板粘贴文本
            if not ClipboardManager.set_text(message):
                logger.error("[失败原因] 剪贴板设置失败")
                return False

            logger.info("粘贴消息内容...")
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)

            # 按 Enter 发送
            logger.info("按 Enter 发送...")
            pyautogui.press('enter')
            time.sleep(0.5)

            # 验证发送结果
            fg_hwnd = win32gui.GetForegroundWindow()
            fg_title = win32gui.GetWindowText(fg_hwnd)
            logger.info(f"发送后焦点窗口: hwnd={fg_hwnd}, title='{fg_title}'")

            logger.info(f"✓ 发送完成: {group_name}")
            return True

        except Exception as e:
            logger.error(f"[失败原因] 发送异常: {e}")
            return False

    @staticmethod
    def _send_via_clipboard(chat_hwnd: int, message: str) -> bool:
        """
        物理模拟发送：剪贴板 + 点击 + 键盘（兼容 NTQQ）

        Args:
            chat_hwnd: 群窗口句柄
            message: 消息内容

        Returns:
            是否成功
        """
        try:
            wm = QQWindowManager()

            # 激活窗口
            if not wm.bring_window_to_front(chat_hwnd):
                logger.warning("无法激活窗口，尝试继续...")

            time.sleep(0.3)

            # 获取窗口位置
            rect = wm.get_window_rect(chat_hwnd)
            if not rect:
                return False

            left, top, right, bottom = rect
            width = right - left
            height = bottom - top

            # 点击输入框
            input_x = left + width // 2
            input_y = bottom - int(height * 0.25)
            logger.info(f"点击输入框: ({input_x}, {input_y})")
            pyautogui.click(input_x, input_y)
            time.sleep(0.2)

            # 剪贴板粘贴
            if not ClipboardManager.set_text(message):
                return False

            logger.info("粘贴并发送...")
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(0.5)

            return True

        except Exception as e:
            logger.error(f"剪贴板方式发送失败: {e}")
            return False


# 便捷函数
def send_to_qq_group(group_name: str, message: str) -> bool:
    """
    便捷函数：发送消息到 QQ 群

    Args:
        group_name: 群名称
        message: 消息内容

    Returns:
        是否成功
    """
    sender = QQWindowAutomation()
    return sender.send_to_qq_group(group_name, message)


def send_to_multiple_groups(groups: List[str], message: str, delay: float = 2.0) -> Tuple[int, int]:
    """
    便捷函数：批量发送到多个群

    Args:
        groups: 群列表
        message: 消息内容
        delay: 延迟

    Returns:
        (成功数, 失败数)
    """
    sender = QQWindowAutomation()
    return sender.send_message_to_multiple_groups(groups, message, delay)
