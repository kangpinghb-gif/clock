<p align="center">
  <h1 align="center">📞 电话提醒系统</h1>
  <p align="center">
    发文字或语音 ➔ 到时间自动打电话给你
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue" />
  <img src="https://img.shields.io/badge/飞书-已集成-blueviolet" />
  <img src="https://img.shields.io/badge/微信-已集成-success" />
  <img src="https://img.shields.io/badge/阿里云VMS-已集成-orange" />
</p>

---

## 🎯 一句话

> **发消息 → 到时间自动打电话。**

支持两个通道：

| 通道 | 用法 |
|------|------|
| 📱 **飞书** | 搜索「我的代办」 |
| 💚 **微信** | 直接发消息 |

---

## ✨ 功能

- 🎤 **语音输入** — 自动转文字
- 📞 **电话提醒** — 到时间自动拨打
- 👥 **多用户** — 每人绑自己的手机
- 📋 **清单管理** — 查看、撤销
- 🎯 **指定号码** — `给136xxx打电话提醒他开会`

---

## 💚 微信使用

### 开始

加微信好友后直接发消息。

### 绑定手机（首次必做）
```
/bind 138xxxx8000
```

### 常用操作
```
明天下午3点提醒我对账     ← 创建待办
5分钟后提醒我开会        ← 相对时间
给我打电话              ← 立即提醒
给136xxx打电话提醒他开会  ← 打给别人
/list                   ← 查看待办
/cancel 3               ← 撤销编号3
/cancel all             ← 撤销全部
/unbind                 ← 解绑手机
```

---

## 📱 飞书使用

### 开始

飞书搜索 **「我的代办」** → 开始对话。

### 绑定手机（首次必做）
```
/bind 138xxxx8000
```

### 常用操作
```
明天下午3点提醒我对账     ← 创建待办
🎤 发语音               ← 自动识别
给136xxx打电话提醒他开会  ← 打给别人
/list                   ← 查看待办
/cancel 3               ← 撤销编号3
/cancel all             ← 撤销全部
```

---

## ⏰ 时间格式

| 写法 | 时间 |
|------|------|
| `5分钟后` | 当前+5分钟 |
| `明天下午3点` | 次日15:00 |
| `今晚8点` | 当天20:00 |
| `后天早上9点` | 后天09:00 |
| `下周一10点` | 下周一10:00 |

---

## ❓ 常见问题

**电话没接到？** 自动重试3次，每次隔5分钟

**语音不准？** 改发文字

**费用？** 你接听免费

**微信和飞书冲突吗？** 不冲突，共用一个数据库，随便用哪个都行

---

## 🛠️ 部署（管理员）

```bash
git clone https://github.com/kangpinghb-gif/clock.git
cd clock
python3 setup.py
pip install -r requirements.txt --break-system-packages
pip install faster-whisper --break-system-packages
pip install alibabacloud_dyvmsapi20170525 --break-system-packages
sudo cp todo-recv.service /etc/systemd/system/
sudo cp todo-remind.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now todo-recv.service
sudo systemctl enable --now todo-remind.service
```

---

## 📁 项目文件

```
├── recv.py          # 飞书接收器
├── remind.py        # 电话提醒器
├── wechat-todo.py   # 微信旁路监听器
├── db.py            # 数据库
├── utils.py         # 时间解析
├── setup.py         # 一键配置向导
├── .env.example     # 配置模板
├── requirements.txt
├── todo-recv.service
├── todo-remind.service
├── todo-wechat.service
├── README.md
└── USAGE.md
```

---

📝 License: MIT
