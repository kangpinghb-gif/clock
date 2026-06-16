# 📞 我的代办 — 飞书电话提醒系统

通过飞书机器人 **「我的代办」** 发送文字或语音消息，自动记录待办事项，到时间后拨打手机电话提醒。

---

## ✅ 当前状态

| 功能 | 状态 | 备注 |
|------|------|------|
| 接收文字消息 | 🟢 已上线 | 自动存入 SQLite + 飞书回复确认 |
| 接收语音消息 | 🟢 已上线 | Whisper 本地模型转文字 |
| `/bind` 绑定手机 | 🟢 已上线 | 发送 `/bind 138xxxx` 即可 |
| `/list` 查看待办 | 🟢 已上线 | 显示最近 10 条 |
| `帮助` 查看指令 | 🟢 已上线 | 发送「帮助」获取 |
| 定时电话提醒 | ⏳ 待配置 | 需阿里云语音服务密钥 |
| 每周汇总推送 | ⏳ 待配置 | 需阿里云密钥 |
| 多用户支持 | ✅ 架构已支持 | 每个用户独立手机号 |

---

## 🏗️ 系统架构

```
                  ┌──────────────────────────┐
                  │     飞书「我的代办」Bot      │
                  │     (im.message.receive)   │
                  └────────┬─────────────────┘
                           │ WebSocket 长连接
                           ▼
┌─────────────────────────────────────────────────┐
│  todo-recv.service (systemd 后台守护)            │
│                                                  │
│  文字 → handle_text_message() → SQLite + 回复    │
│  语音 → download_ogg → Whisper → 文字 → SQLite   │
│  命令 → /bind /list /帮助                         │
└──────────┬──────────────────────────────────────┘
           │ 定时检查 (每 30 秒)
           ▼
┌─────────────────────────────────────────────────┐
│  todo-remind.service (systemd, 需阿里云密钥)     │
│                                                  │
│  get_due_todos() → SingleCallByTts → 打电话      │
│                 → mark_done() → 飞书通知          │
└─────────────────────────────────────────────────┘
```

---

## 📁 项目文件

```
/home/ubuntu/todo-voice-caller/
├── .env                  # 密钥配置
├── .env.example          # 配置模板
├── requirements.txt      # Python 依赖
├── install.sh            # 一键安装 systemd 服务
│
├── recv.py               # 飞书接收器（正在运行）
├── remind.py             # 电话提醒器（待配置）
├── weekly.py             # 周报推送（待配置）
├── db.py                 # 数据库操作
├── utils.py              # 时间解析工具
│
├── todo-recv.service     # systemd 接收服务
├── todo-remind.service   # systemd 提醒服务
│
├── todos.db              # SQLite 数据库（自动生成）
└── venv/                 # Python 虚拟环境
```

---

## 🚀 快速使用

### 1. 找到机器人

打开飞书 → 搜 **「我的代办」** → 进入对话

### 2. 发消息创建待办

| 示例 | 说明 |
|------|------|
| `明天下午3点提醒我对账` | 创建待办 |
| `5分钟后提醒我开会` | 相对时间 |
| `今晚8点吃药` | 当天时间 |
| 🎤 直接发语音 | 自动转文字 |

### 3. 查看日志

```bash
journalctl -u todo-recv.service -f
```

输出示例：
```
📩 [21:57:00] 收到文字: 明天下午3点提醒我对账
  ✅ 已记录: [2026-06-16 15:00] 明天下午3点提醒我对账
🎤 [21:57:05] 收到语音 (3000ms)
  🎤 识别结果: 明天下午3点提醒我对账
  ✅ 已记录: [2026-06-16 15:00] 明天下午3点提醒我对账
```

### 4. 命令

| 命令 | 说明 |
|------|------|
| `/bind 138xxxx8000` | 绑定手机号 |
| `/list` | 查看待办列表 |
| `帮助` | 查看使用说明 |

---

## ⚙️ 服务管理

```bash
# 状态
systemctl status todo-recv.service

# 实时日志
journalctl -u todo-recv.service -f

# 重启
sudo systemctl restart todo-recv.service

# 停止
sudo systemctl stop todo-recv.service

# 开机自启（已启用）
systemctl is-enabled todo-recv.service
```

---

## 🔑 配置阿里云电话提醒

### 1. 开通服务

打开 https://dyvms.console.aliyun.com → 开通语音服务（需实名认证）

### 2. 创建语音模板

```
控制台 → 语音消息 → 语音通知 → 模板管理 → 创建模板
```

| 字段 | 填写 |
|------|------|
| 模板类型 | 文本转语音（TTS） |
| 模板内容 | `您好，您有一条待办提醒：${content}，请及时处理` |
| 声音 | 推荐「小云标准女声」 |

> 模板提交后需审核（1-2 个工作日）

### 3. 编辑 .env

```bash
vim /home/ubuntu/todo-voice-caller/.env
```

填写：
```
ALIYUN_ACCESS_KEY_ID=你的AccessKeyId
ALIYUN_ACCESS_KEY_SECRET=你的AccessKeySecret
ALIYUN_TTS_CODE=TTS_xxxxxx
ALIYUN_CALLED_NUMBER=+8613800138000
```

### 4. 启动提醒服务

```bash
sudo systemctl enable --now todo-remind.service
```

---

## 📊 数据库查询

```bash
# 查看所有待办
sqlite3 /home/ubuntu/todo-voice-caller/todos.db "SELECT * FROM todos ORDER BY id DESC LIMIT 20;"

# 查看用户
sqlite3 ~/todo-voice-caller/todos.db "SELECT * FROM users;"
```

---

## ❓ 常见问题

### Q: 服务会自动重启吗？
系统已配置 `Restart=always`，进程崩溃或服务器重启都会自动拉起。

### Q: 语音识别准确率如何？
使用本地 Whisper base 模型，中英文混合识别。如果环境安静、发音清晰，准确率很高。

### Q: 电话没接到会怎样？
系统会重试 3 次，每次间隔 5 分钟。

### Q: 费用多少？
阿里云语音通知约 0.05~0.1 元/分钟（接通才计费），个人使用月费几乎可以忽略。

### Q: 如何添加更多用户？
用户首次给机器人发消息会自动注册，使用 `/bind` 绑定自己手机号即可。管理员可在飞书控制台设置应用可用范围。

---

## 📝 项目信息

- **部署路径**: `/home/ubuntu/todo-voice-caller/`
- **飞书应用**: 「我的代办」(`cli_aaad6679fcfc9bd8`)
- **后台服务**: `todo-recv.service`（运行中）
- **开发语言**: Python 3.12
- **语音模型**: faster-whisper (base)
