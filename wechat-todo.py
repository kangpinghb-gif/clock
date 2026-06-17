#!/usr/bin/env python3
"""
微信待办旁路监听器
监听 Hermes 网关日志，自动将微信消息中的待办存入数据库。
与飞书 recv.py 共用同一套数据库和电话系统。
"""
import os
import sys
import re
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import init_db, get_or_create_user, add_todo
from utils import parse_time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# 网关日志路径（支持多个 profile）
GATEWAY_LOGS = [
    os.path.expanduser("~/.hermes/profiles/code/logs/gateway.log"),
    os.path.expanduser("~/.hermes/profiles/writer/logs/gateway.log"),
]
# 微信用户映射到本地的 open_id
WECHAT_USER = "wechat_user"


def extract_wechat_msg(line: str) -> str | None:
    """从网关日志行中提取微信消息内容"""
    m = re.search(r"inbound message:.*?msg='([^']+)'", line)
    return m.group(1) if m else None


def follow_log():
    """持续监听网关日志"""
    import subprocess

    valid_logs = [p for p in GATEWAY_LOGS if os.path.exists(p)]
    if not valid_logs:
        print(f"[WECHAT] 日志文件不存在: {GATEWAY_LOGS}")
        return

    init_db()
    get_or_create_user(WECHAT_USER, "微信用户")

    print(f"[WECHAT] 监听 {len(valid_logs)} 个日志文件", flush=True)
    for lp in valid_logs:
        print(f"  - {lp}", flush=True)

    proc = subprocess.Popen(
        ["tail", "-F", "-n", "0"] + valid_logs,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, bufsize=1
    )

    try:
        for line in proc.stdout:
            line = line.strip()
            # tail -F 输出格式: "==> /path/file <=" (文件切换标记)
            if line.startswith("==") and line.endswith("=="):
                continue
            msg = extract_wechat_msg(line)
            if not msg:
                continue
            print(f"\n[WECHAT] 收到: {msg}", flush=True)
            process_message(msg)
    except KeyboardInterrupt:
        proc.terminate()


def process_message(text: str):
    """处理微信消息：解析时间 → 存库 → 飞书通知"""
    text = text.strip()

    # 提取目标号码
    target_phone = ""
    m = re.search(r"(?:打?电话?给|通知|呼叫|给)(1[3-9]\d{9})", text)
    if m:
        target_phone = m.group(1)
        text = text.replace(m.group(0), "").strip()

    # 检查撤销指令
    cancel_all = re.search(r"^(取消|撤销|删除)\s*(所有|全部|all)", text)
    cancel_id = re.search(r"^(取消|撤销|删除)\s*#?(\d+)", text)
    if cancel_all:
        from db import cancel_todo, get_user_todos
        todos = get_user_todos(WECHAT_USER)
        count = 0
        for t in todos:
            if t["status"] == "pending" and cancel_todo(t["id"], WECHAT_USER):
                count += 1
        print(f"  ✅ 已撤销 {count} 条待办", flush=True)
        return
    if cancel_id:
        tid = int(cancel_id.group(2))
        from db import cancel_todo
        if cancel_todo(tid, WECHAT_USER):
            print(f"  ✅ 已撤销 #{tid}", flush=True)
        else:
            print(f"  ❌ 未找到 #{tid} 或已过期", flush=True)
        return

    # 解析时间
    time_obj = parse_time(text)
    if not time_obj:
        return

    remind_time = time_obj.strftime("%Y-%m-%d %H:%M")
    todo_id = add_todo(WECHAT_USER, text, remind_time, "", target_phone, "weixin")

    print(f"  ✅ 已记录: [{remind_time}] {text[:50]} (source=weixin)", flush=True)




if __name__ == "__main__":
    print("=" * 50)
    print("📞 微信待办旁路监听器")
    print(f"日志: 监控 {len(GATEWAY_LOGS)} 个文件")
    print("=" * 50)
    follow_log()
