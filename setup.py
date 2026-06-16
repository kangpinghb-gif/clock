#!/usr/bin/env python3
"""电话提醒系统 — 配置向导"""
import os, sys

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

print("=" * 44)
print("  📞 电话提醒系统 — 配置向导")
print("=" * 44)
print()

# Feishu
print("━" * 36)
print("  第 1 步：飞书应用配置")
print("━" * 36)
aid = input("  App ID    : ").strip()
asec = input("  App Secret: ").strip()
print()

# Aliyun
print("━" * 36)
print("  第 2 步：阿里云语音服务")
print("━" * 36)
kid = input("  AccessKey ID    : ").strip()
ksec = input("  AccessKey Secret: ").strip()
tts = input("  语音模板 ID     : ").strip()
phone = input("  手机号 (+86xxx) : ").strip()
print()

# Write env
lines = []
lines.append("# --- Feishu ---")
lines.append(f"FEISHU_APP_ID={aid}")
lines.append(f"FEISHU_APP_SECRET={asec}")
lines.append("")
lines.append("# --- Aliyun Voice ---")
lines.append(f"ALIYUN_ACCESS_KEY_ID={kid}")
lines.append(f"ALIYUN_ACCESS_KEY_SECRET={ksec}")
lines.append(f"ALIYUN_TTS_CODE={tts}")
lines.append(f"ALIYUN_CALLED_NUMBER={phone}")
lines.append("")
lines.append("# --- System ---")
lines.append(f"DB_PATH={os.path.join(os.path.dirname(env_path), 'todos.db')}")
lines.append("WHISPER_MODEL=base")
lines.append("")

with open(env_path, "w") as f:
    f.write("\n".join(lines))

print("✅ 配置文件已生成:", env_path)
print()
print("下一步：")
print(f"  cd {os.path.dirname(env_path)}")
print("  pip install -r requirements.txt --break-system-packages")
print("  pip install faster-whisper --break-system-packages")
print("  pip install alibabacloud_dyvmsapi20170525 --break-system-packages")
print("  sudo cp todo-recv.service /etc/systemd/system/")
print("  sudo cp todo-remind.service /etc/systemd/system/")
print("  sudo systemctl daemon-reload")
print("  sudo systemctl enable --now todo-recv.service")
print("  sudo systemctl enable --now todo-remind.service")
