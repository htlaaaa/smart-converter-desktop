"""
桌面版启动脚本 - 带环境检查
"""
import os
import sys
import subprocess
from pathlib import Path


def check_python():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Python 版本过低: {version.major}.{version.minor}")
        print("请安装 Python 3.9 或更高版本")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """检查并安装依赖"""
    print("\n📦 检查依赖...")

    requirements = Path(__file__).parent / "requirements.txt"

    if not requirements.exists():
        print("❌ 未找到 requirements.txt")
        return False

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
            check=True,
            capture_output=True
        )
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False


def init_config():
    """初始化配置"""
    print("\n⚙️  检查配置...")

    from core.config import Config
    config = Config()

    # 检查必要配置
    if not config.is_taobao_configured():
        print("⚠️  淘宝联盟 API 未配置")
        print("请在设置中配置以下信息：")
        print("  - App Key")
        print("  - App Secret")
        print("  - PID")
        print("  - Adzone ID")

    if not config.is_ai_configured():
        print("⚠️  Claude AI 未配置")
        print("AI 功能将不可用")
    else:
        print("✅ AI 配置完整")

    return config


def create_data_dir():
    """创建数据目录"""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    log_dir = Path.home() / ".smart_converter"
    log_dir.mkdir(exist_ok=True)


def main():
    """主函数"""
    print("=" * 60)
    print("  🚀 AI 智能转链工具 - 桌面版")
    print("=" * 60)
    print()

    # 检查 Python
    if not check_python():
        input("\n按 Enter 键退出...")
        return

    # 检查依赖
    if not check_dependencies():
        input("\n按 Enter 键退出...")
        return

    # 创建目录
    create_data_dir()

    # 初始化配置
    config = init_config()

    print("\n" + "=" * 60)
    print("🚀 启动应用...")
    print("=" * 60)
    print()

    # 启动 GUI
    try:
        import customtkinter as ctk
        from gui.main_window import MainWindow

        # 设置主题
        ctk.set_appearance_mode(config.get('general.theme', 'dark'))
        ctk.set_default_color_theme("blue")

        # 创建主窗口
        app = ctk.CTk()
        app.geometry("1200x700")
        app.minsize(900, 600)
        app.title("AI 智能转链工具 v1.0.0")

        # 创建主界面
        main_window = MainWindow(app, config)

        print("✅ 应用已启动！")
        print()
        print("使用提示：")
        print("  • 单条转链：粘贴商品链接，一键转链")
        print("  • 批量转链：批量处理多个链接")
        print("  • QQ群发：自动发送到 QQ 群")
        print("  • 历史记录：查看和管理转链记录")
        print()

        # 运行
        app.mainloop()

    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按 Enter 键退出...")


if __name__ == "__main__":
    main()
