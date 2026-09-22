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
import pyautogui
from typing import Optional, List, Tuple
from loguru import logger

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

            # 通过类名识别（更可靠）
            qq_classes = ["TXGuiFoundation", "StandardFrame", "TMainForm",
                          "QQMainFrame", "AfxFrameOrView70"]
            if any(qc in class_name for qc in qq_classes):
                windows.append((hwnd, title, class_name, 10))  # 类名匹配高分
                return True

            # 通过标题识别
            if title:
                if "QQ" in title or "NTQQ" in title or "腾讯QQ" in title:
                    windows.append((hwnd, title, class_name, 5))  # 标题匹配低分
            return True

        win32gui.EnumWindows(callback, candidates)

        if candidates:
            # 按分数排序，取最高的
            candidates.sort(key=lambda x: x[3], reverse=True)
            hwnd, title, class_name, score = candidates[0]
            self.qq_hwnd = hwnd
            logger.info(f"找到 QQ 窗口: hwnd={hwnd}, title={title}, class={class_name}")
            return hwnd

        logger.warning("未找到 QQ 窗口")
        return None

    def scan_all_group_windows(self) -> dict:
        """
        扫描所有可能的群窗口（增强版）

        Returns:
            群名字典 {群名/标题: 窗口句柄}
        """
        self.group_windows.clear()

        # QQ群窗口常见的类名
        qq_chat_classes = ["TXGuiFoundation", "StandardFrame", "TMainForm",
                           "ChatWnd", "QQChatWindow", "AfxFrameOrView70"]

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
            "Google Chrome", "Chrome",
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
        将窗口置前

        Args:
            hwnd: 窗口句柄

        Returns:
            是否成功
        """
        try:
            # 如果窗口最小化，先恢复
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

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
    def send_to_qq_group(group_name: str, message: str, qq_window_title: str = "QQ") -> bool:
        """
        快速发送消息到 QQ 群

        基于已打开的群窗口，通过 Windows API 直接发送（不抢焦点）

        Args:
            group_name: 群名称
            message: 消息内容
            qq_window_title: QQ 窗口标题

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

            # 2. 扫描所有群窗口
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

            # 4. 找到群窗口里的输入框控件（不抢焦点）
            input_hwnd = wm.find_input_control(chat_hwnd)
            if not input_hwnd:
                logger.warning("[回退] 未找到输入框控件，使用剪贴板方式")
                # 回退方案：使用剪贴板（会抢焦点）
                result = QQWindowAutomation._send_via_clipboard(chat_hwnd, message)
                if not result:
                    logger.error("[失败原因] 剪贴板方式也失败了")
                return result

            # 5. 使用 PostMessage + WM_SETTEXT 设置文本（不抢焦点！）
            logger.info(f"通过句柄发送消息（不抢焦点）: {group_name}")
            win32gui.PostMessage(input_hwnd, win32con.WM_SETTEXT, 0, message)

            time.sleep(0.3)

            # 6. 使用 PostMessage 发回车（不抢焦点！）
            win32gui.PostMessage(input_hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
            time.sleep(0.05)
            win32gui.PostMessage(input_hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)

            time.sleep(0.3)
            logger.info(f"✓ 发送成功: {group_name}")
            return True

        except Exception as e:
            logger.error(f"[失败原因] 发送异常: {e}")
            return False

    @staticmethod
    def _send_via_clipboard(chat_hwnd: int, message: str) -> bool:
        """回退方案：通过剪贴板发送（会抢焦点）"""
        try:
            # 激活窗口
            win32gui.SetForegroundWindow(chat_hwnd)
            time.sleep(0.3)

            # 点击输入框
            rect = win32gui.GetWindowRect(chat_hwnd)
            input_x = (rect[0] + rect[2]) // 2
            input_y = rect[3] - 100
            pyautogui.click(input_x, input_y)
            time.sleep(0.2)

            # 剪贴板 + 粘贴
            ClipboardManager.set_text(message)
            time.sleep(0.2)
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
