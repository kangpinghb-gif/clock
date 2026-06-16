<p align="center">
  <h1 align="center">📞 飞书电话提醒系统</h1>
  <p align="center">
    给飞书机器人发文字或语音 → 到时间自动打电话给你
    <br />
    <a href="USAGE.md"><strong>📖 用户手册</strong></a>
    ·
    <a href="https://github.com/kangpinghb-gif/clock/issues"><strong>🐛 提交问题</strong></a>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue" />
  <img src="https://img.shields.io/badge/飞书-已集成-blueviolet" />
  <img src="https://img.shields.io/badge/阿里云VMS-已集成-orange" />
  <img src="https://img.shields.io/badge/Whisper-本地部署-success" />
  <img src="https://img.shields.io/badge/systemd-开机自启-yellow" />
</p>

---

## 🎯 项目简介

通过飞书机器人「我的代办」接收文字或语音消息，自动记录待办事项。到预定时间后，系统自动拨打你的手机电话，用语音播报待办内容——再也不用担心错过待办。

**一句话：给飞书发消息，到时间自动打电话给你。**

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🎤 **语音输入** | 发语音消息，Whisper 自动转文字 |
| 📝 **文字输入** | 支持自然语言时间，如"明天下午3点提醒我对账" |
| 📞 **电话提醒** | 到时间自动拨打电话，语音播报待办内容 |
| 👥 **多用户** | 每人绑定自己的手机号，独立使用 |
| 📋 **查看待办** | 发送 `/list` 查看你的待办列表 |

---

## 🚀 快速开始（用户）

### 1. 找到机器人

打开飞书 → 搜索 **「我的代办」**

### 2. 绑定手机号（首次必做）

```
/bind 138xxxx8000
```

### 3. 创建待办

```
明天下午3点提醒我对账
5分钟后提醒我开会
今晚8点吃药
🎤 或者直接发语音
```

### 4. 到时间接电话 📞

手机响起 → 接听后播放：

> *"您好，您有一条待办提醒：明天下午3点提醒您对账，请及时处理"*

---

## ⏰ 支持的时间格式

| 输入 | 理解的时间 |
|------|-----------|
| `5分钟后` | 当前 + 5分钟 |
| `明天下午3点` | 次日 15:00 |
| `今晚8点` | 当天 20:00 |
| `后天早上9点` | 后天 09:00 |
| `下周一上午10点` | 下周一 10:00 |

---

## 🛠️ 部署指南（管理员）

### 前置要求

- Linux 服务器（Debian/Ubuntu）
- Python 3.12
- 飞书企业自建应用（已开通 Bot + WebSocket 事件）
- 阿里云语音服务（已开通并创建 TTS 模板）

### 1. 克隆

```bash
git clone https://github.com/kangpinghb-gif/clock.git
cd clock
```

### 2. 安装依赖

```bash
pip install -r requirements.txt --break-system-packages
# 语音识别模型
pip install faster-whisper --break-system-packages
# 阿里云 SDK
pip install alibabacloud_dyvmsapi20170525 --break-system-packages
```

### 3. 配置

```bash
cp .env.example .env
vim .env
```

填入以下内容：

| 变量 | 说明 |
|------|------|
| `FEISHU_APP_ID` | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret |
| `ALIYUN_ACCESS_KEY_ID` | 阿里云 AccessKey ID |
| `ALIYUN_ACCESS_KEY_SECRET` | 阿里云 AccessKey Secret |
| `ALIYUN_TTS_CODE` | 语音模板 ID（如 TTS_332510274） |
| `ALIYUN_CALLED_NUMBER` | 默认被叫手机号（+86xxxxxxxxx） |

### 4. 安装系统服务

```bash
sudo cp todo-recv.service /etc/systemd/system/
sudo cp todo-remind.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now todo-recv.service
sudo systemctl enable --now todo-remind.service
```

### 5. 查看运行状态

```bash
# 接收器状态
systemctl status todo-recv.service

# 电话提醒器状态
systemctl status todo-remind.service

# 实时日志
journalctl -u todo-recv.service -f
journalctl -u todo-remind.service -f
```

---

## 🏗️ 系统架构

```
用户 (飞书) ──→ WebSocket ──→ recv.py ──→ SQLite
                   │                          │
                   │                    ┌─────┘
                   ▼                    ▼
               Whisper              remind.py
              (语音转文字)              │
                                        ▼
                                  阿里云 VMS
                                  (打电话)
```

---

## 📁 项目文件

```
├── recv.py           # 飞书消息接收器（WebSocket + Whisper）
├── remind.py         # 电话提醒调度器（阿里云 VMS）
├── weekly.py         # 每周汇总推送
├── db.py             # SQLite 数据库操作
├── utils.py          # 中文时间解析
├── .env.example      # 配置模板
├── requirements.txt  # Python 依赖
├── todo-recv.service    # systemd 接收服务
├── todo-remind.service  # systemd 提醒服务
├── README.md         # 本文件
└── USAGE.md          # 用户使用手册
```

---

## 📊 技术栈

| 层 | 技术 |
|----|------|
| 消息接收 | 飞书 WebSocket (lark-oapi) |
| 语音识别 | faster-whisper (base 模型, 本地运行) |
| 电话外呼 | 阿里云语音服务 (SingleCallByTts) |
| 数据库 | SQLite |
| 后台守护 | systemd |
| 语言 | Python 3.12 |

---

## 📝 License

MIT
