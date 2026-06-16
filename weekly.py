"""
每周汇总 — 每周日晚 8 点推送待办统计
"""
import os
import sys
import json
import ssl as ssl_mod
from datetime import datetime
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import init_db, get_weekly_summary
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")


def get_feishu_token() -> str:
    ctx = ssl_mod._create_unverified_context()
    payload = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode()
    req = Request("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                  data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, context=ctx) as resp:
        return json.loads(resp.read())["tenant_access_token"]


def get_all_users() -> list:
    """获取所有有手机号的用户"""
    import sqlite3
    db_path = os.getenv("DB_PATH", os.path.expanduser("~/todo-voice-caller/todos.db"))
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT open_id, phone, name FROM users WHERE phone != ''").fetchall()
    conn.close()
    return [{"open_id": r[0], "phone": r[1], "name": r[2]} for r in rows]


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 生成周报...")

    init_db()
    summary = get_weekly_summary()
    users = get_all_users()

    if not users:
        print("  暂无用户绑定，跳过")
        return

    msg = (
        f"📊 本周待办汇总\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📋 总待办: {summary['total']} 条\n"
        f"✅ 已完成: {summary['done_count']} 条\n"
        f"⏳ 待处理: {summary['pending_count']} 条\n"
        f"━━━━━━━━━━━━━━━\n"
        f"继续加油！💪"
    )

    token = get_feishu_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for user in users:
        url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
        body = json.dumps({
            "receive_id": user["open_id"],
            "msg_type": "text",
            "content": json.dumps({"text": msg}, ensure_ascii=False),
        }).encode()
        req = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(req, context=ssl_mod._create_unverified_context()) as resp:
                result = json.loads(resp.read())
            if result.get("code") == 0:
                print(f"  推送给 {user['name'] or user['open_id'][:8]}: ✅")
            else:
                print(f"  推送给 {user['open_id'][:8]}: ❌ {result.get('msg','')}")
        except Exception as e:
            print(f"  推送给 {user['open_id'][:8]}: ❌ {e}")

    print("周报推送完成")


if __name__ == "__main__":
    main()
