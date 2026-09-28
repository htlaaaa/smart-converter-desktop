# 智能转链工具 · 桌面版

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![GUI](https://img.shields.io/badge/GUI-CustomTkinter-orange)](https://github.com/TomSchimansky/CustomTkinter)

一款基于 **Windows 窗口自动化** 的桌面端 AI 智能转链 / 群发工具，支持淘宝、天猫、京东商品转链与 QQ / NTQQ 群消息推送。

> ⚠️ 本工具仅供**学习与研究**使用，请遵守《QQ 用户协议》及平台运营规范，合规使用。

---

## 📑 目录

- [功能特性](#-功能特性)
- [快速开始](#-快速开始)
- [QQ 群发使用指南](#-qq-群发使用指南)
- [项目结构](#-项目结构)
- [打包成 EXE](#-打包成-exe)
- [配置说明](#-配置说明)
- [技术栈](#-技术栈)
- [常见问题](#-常见问题)
- [更新日志](#-更新日志)
- [贡献](#-贡献)
- [许可证](#-许可证)
- [免责声明](#-免责声明)

---

## ✨ 功能特性

### 🔗 智能转链

| 平台 | 能力 |
| ---- | ---- |
| 淘宝 / 天猫 | 商品链接转推广链接、自动生成淘口令、佣金查询 |
| 京东         | 京品库转链、优惠券解析、佣金明细 |
| 二维码       | 一键导出推广二维码 |

### 🤖 AI 增强（可选）

- 商品智能分析：品类 / 目标人群 / 核心卖点
- 5 种风格的推广文案自动生成（种草、测评、对比、促销、福利）
- 推广文案合规风险检测

### 📦 批量处理

- 批量转链，最多 **500 个 / 次**
- 多线程并发加速
- 实时进度条 + 失败重试

### 📢 QQ 群发（窗口自动化，无 Hook）

- 基于 PyAutoGUI + Win32 API 的纯窗口自动化
- 批量群发，发送延迟可调
- 消息模板变量：`{title}` `{price}` `{tao_password}` 等
- 群名批量导入（手动 / 文件）
- 实时日志与发送统计

### 📊 数据与监控

- 转链历史记录，支持搜索 / 筛选 / 导出
- 每日 / 每月转链统计、佣金汇总
- 云端采集任务监控
- 日志查看器

---

## 🚀 快速开始

### 环境要求

- **操作系统**：Windows 10 / 11（窗口自动化依赖 Win32 API）
- **Python**：3.9 及以上
- **QQ**：登录桌面版 **QQ** 或 **NTQQ**，并保持窗口可见

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/htlaaaa/smart-converter-desktop.git
cd smart-converter-desktop

# 2. （推荐）创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt
```

### 启动

```bash
# 方式一：模块化启动
cd src
python run.py

# 方式二：直接入口
python src/main.py
```

### 首次配置

启动后点击右上角 **⚙️ 设置**，按需填写：

1. **淘宝联盟 API**（[申请地址](https://pub.alimama.com/)）：App Key / App Secret / PID / Adzone ID
2. **京东联盟 API**（可选）：App Key / App Secret / 网站 ID
3. **Claude API Key**（[申请地址](https://console.anthropic.com/)）：用于 AI 文案 / 分析，可不填

> 💡 配置默认保存在 `config.json`，已在 `.gitignore` 中忽略，不会随仓库泄露。

---

## 📢 QQ 群发使用指南

### 工作原理

基于 Windows 窗口自动化（不注入、不 Hook QQ 进程）：

1. 枚举并定位 QQ/NTQQ 窗口
2. `Ctrl+F` 唤起搜索框 → 输入群名 → `Enter` 进入群聊
3. 剪贴板写入待发送文本 → `Ctrl+V` 粘贴 → `Enter` 发送
4. 按设定延迟循环下一个群

### 使用步骤

1. **准备环境**
   - 登录 QQ 或 NTQQ，保持窗口处于前台（不要最小化）
   - 提前把目标群加入搜索列表

2. **导入群名**
   - 进入 **📢 QQ群发** 页
   - 手动粘贴或从 `.txt` 文件导入，每行一个群名

3. **编辑消息模板**
   - 支持多行文本
   - 支持变量插值：
     | 变量 | 含义 |
     | ---- | ---- |
     | `{title}` | 商品标题 |
     | `{price}` | 商品价格 |
     | `{tao_password}` | 淘口令 |
     | `{coupon}` | 优惠券金额 |

4. **设置延迟**：建议 **3 ~ 5 秒**，过低有封号风险

5. **开始发送**：点击 **🚀 开始群发**，**全程不要触碰鼠标键盘**

### ⚠️ 注意事项

- ❌ 不要最小化 QQ 窗口
- ❌ 发送过程中不要操作鼠标键盘
- ❌ 不要同时在 QQ 窗口做其他事
- ⚠️ 建议先用小号、测试群验证效果
- ⚠️ 短时间内大量群发可能限制账号功能

---

## 📁 项目结构

```
smart-converter-desktop/
├── src/
│   ├── main.py                      # 程序入口
│   ├── run.py                       # 启动脚本（含环境自检）
│   ├── core/                        # 核心模块
│   │   ├── config.py                # 配置管理（读写 config.json）
│   │   └── database.py              # SQLite 封装
│   ├── services/                    # 服务层
│   │   ├── affiliate.py             # 淘宝联盟 API
│   │   ├── jd_affiliate.py          # 京东联盟 API
│   │   ├── ai.py                    # AI 服务（Claude）
│   │   ├── cloud_collector.py       # 云端商品采集
│   │   └── qq_automation.py         # QQ 窗口自动化 ⭐
│   ├── gui/                         # 界面
│   │   ├── main_window.py           # 主窗口 + 导航
│   │   └── pages/
│   │       ├── convert_page.py          # 单品转链
│   │       ├── batch_page.py            # 批量转链
│   │       ├── groupsend_page.py        # QQ 群发 ⭐
│   │       ├── cloud_collect_page.py    # 云端采集
│   │       ├── monitor_page.py          # 任务监控
│   │       ├── log_viewer_page.py       # 日志查看
│   │       ├── history_page.py          # 历史记录
│   │       └── settings_page.py         # 设置
│   └── utils/                       # 通用工具
├── build_exe.py                     # PyInstaller 打包脚本
├── requirements.txt                 # 依赖清单
├── .gitignore                       # 已忽略 dist/、build/、*.exe、配置密钥等
└── README.md
```

---

## ⚙️ 配置说明

### 淘宝开放平台（必填）

1. 访问 <https://pub.alimama.com/>
2. 「推广管理」→ 「我的应用」创建应用获取 `App Key` / `App Secret`
3. 「推广位管理」获取 `PID` 与 `Adzone ID`

### 京东联盟（可选）

1. 访问 <https://union.jd.com/>
2. 创建应用并申请「商品转链」「优惠券解析」权限

### Claude API（可选）

1. 访问 <https://console.anthropic.com/>
2. 创建 API Key，余额充足即可启用 AI 文案与分析

---

## 🛠️ 技术栈

| 类别     | 技术                       |
| ---------- | -------------------------- |
| GUI       | CustomTkinter 5.2+        |
| 后端      | Python 3.9+               |
| AI        | Claude（Anthropic SDK）   |
| 自动化    | PyAutoGUI + Win32 API     |
| 网络      | httpx                      |
| 日志      | loguru                     |
| 数据库    | SQLite3（标准库内置）     |
| 打包      | PyInstaller 6+            |

---

## 📦 打包成 EXE

> 打包产物 `dist/*.exe` 已在 `.gitignore` 中忽略，不会被推送到 GitHub。

```bash
# 安装 PyInstaller
pip install pyinstaller

# 运行打包脚本（自动配置图标、隐藏控制台等）
python build_exe.py

# 产物
dir dist\
# -> AI智能转链工具.exe
```

打包完成后双击 `dist/AI智能转链工具.exe` 即可在未安装 Python 的环境下使用。

---

## ❓ 常见问题

<details>
<summary><b>Q1：运行后报 <code>ModuleNotFoundError: No module named 'pyautogui'</code></b></summary>

A：在 Windows 上 `pip install -r requirements.txt` 后仍报错，通常是因为在**非 Windows** 环境下安装，导致 Windows 专属依赖被跳过。请在 Windows + Python 3.9+ 中重新执行：

```bash
pip install pyautogui pywin32
```

</details>

<details>
<summary><b>Q2：QQ 群发找不到窗口 / 一直停在搜索</b></summary>

A：
- 确认 QQ 是**桌面版**而非 Web 版；
- QQ 窗口必须**前台可见**，不能被遮挡或最小化；
- 检查是否被杀毒软件拦截了 `pyautogui` 的键盘模拟。

</details>

<details>
<summary><b>Q3：淘宝 API 返回 "权限不足" / "invalid signature"</b></summary>

A：
- 确认 `App Key / App Secret / Adzone ID` 全部正确；
- 系统时间偏差过大会触发签名校验失败，请同步 NTP。

</details>

<details>
<summary><b>Q4：能跑通但 AI 文案始终空白</b></summary>

A：
- 检查 API Key 是否有效、余额是否充足；
- 在 **⚙️ 设置** 页面查看「AI 服务」开关是否打开；
- 查看 **📜 日志** 页面，错误码会以红色高亮。

</details>

---

## 📝 更新日志

### v1.2.0 · 2026-09

- 🆕 京东联盟转链支持
- 🆕 云端商品采集任务
- 🆕 实时任务监控页 & 日志查看器
- ⚡ 批量转链并发参数可调

### v1.1.0 · 2026-06

- 🆕 QQ 群发功能（窗口自动化）
- 🆕 群发消息模板变量
- ⚡ 历史记录筛选性能优化

### v1.0.0 · 2026-03

- 🆕 淘宝 / 天猫基础转链
- 🆕 AI 商品分析与文案生成
- 🆕 批量转链（最多 500 / 次）
- 🆕 桌面 GUI（CustomTkinter）

---

## 🤝 贡献

欢迎 Issue 与 PR：

1. Fork 本仓库
3. 在新分支提交功能 / 修复：`git checkout -b feat/awesome`
4. 提交并描述清楚改动动机
5. 发起 Pull Request

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

## ⚠️ 免责声明

使用本工具即表示你同意：

1. 遵守 QQ 用户协议与中华人民共和国相关法律法规
2. 自行承担使用本工具的风险与后果
3. 不将本工具用于任何违法违规、骚扰他人、虚假宣传等场景
4. 因使用本工具产生的任何法律责任由使用者本人承担

**本工具仅供学习研究使用，请勿用于商业推广、骚扰、广告轰炸等场景。**