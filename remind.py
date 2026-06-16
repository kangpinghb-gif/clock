"""
电话提醒模块 — 定时检查待办 + 阿里云语音呼叫
"""
import os
import sys
import json
import time
import ssl as ssl_mod
from datetime import datetime
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import init_db, get_due_todos, mark_done, mark_failed, get_user
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
AK_ID = os.getenv("ALIYUN_ACCESS_KEY_ID", "")
AK_SECRET = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "")
TTS_CODE = os.getenv("ALIYUN_TTS_CODE", "")
DEFAULT_PHONE = os.getenv("ALIYUN_CALLED_NUMBER", "")

CHECK_INTERVAL = 30  # 检查间隔（秒）
MAX_RETRIES = 3      # 最多重试次数
RETRY_DELAY = 300    # 重试间隔（5分钟）


def get_feishu_token() -> str:
    """获取飞书 tenant_access_token"""
    ctx = ssl_mod._create_unverified_context()
    payload = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode()
    req = Request("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                  data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, context=ctx) as resp:
        return json.loads(resp.read())["tenant_access_token"]


def send_feishu_message(open_id: str, text: str):
    """发送飞书消息"""
    ctx = ssl_mod._create_unverified_context()
    token = get_feishu_token()
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    body = json.dumps({
        "receive_id": open_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }).encode()
    req = Request(url, data=body,
                  headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                  method="POST")
    with urlopen(req, context=ctx) as resp:
        return json.loads(resp.read())


# ─── 阿里云语音呼叫 ───


def _sign_request(params: dict) -> dict:
    """阿里云 HMAC-SHA1 签名（简化版，使用 SDK 会更好）"""
    # 使用 alibabacloud SDK 可大大简化签名
    # 这里用简化方案：如果 SDK 不可用，可以用 subprocess 调用 aliyun CLI
    return params


def make_phone_call(phone: str, content: str) -> dict:
    """
    调用阿里云 SingleCallByTts 拨打语音电话
    需要: pip install alibabacloud_dyvmsapi20170525
    """
    if not AK_ID or not AK_SECRET:
        return {"code": -1, "msg": "阿里云密钥未配置，请填写 ALIYUN_ACCESS_KEY_ID/ALIYUN_ACCESS_KEY_SECRET"}

    if not TTS_CODE:
        return {"code": -1, "msg": "语音模板 ID 未配置，请填写 ALIYUN_TTS_CODE"}

    try:
        from alibabacloud_dyvmsapi20170525.client import Client
        from alibabacloud_dyvmsapi20170525.models import SingleCallByTtsRequest
        from alibabacloud_tea_openapi.models import Config

        config = Config(
            access_key_id=AK_ID,
            access_key_secret=AK_SECRET,
            endpoint='dyvmsapi.aliyuncs.com'
        )
        client = Client(config)

        # 截断过长的内容
        tts_text = content[:200]

        req = SingleCallByTtsRequest(
            called_number=phone,
            tts_code=TTS_CODE,
            tts_param=json.dumps({"todo_content": tts_text}, ensure_ascii=False),
            play_times=2,
        )
        resp = client.single_call_by_tts(req)
        return {"code": 0, "call_id": resp.body.call_id, "msg": "ok"}

    except ImportError:
        return {"code": -1, "msg": "未安装阿里云 SDK，请执行: pip install alibabacloud_dyvmsapi20170525"}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


# ─── 主循环 ───


def check_and_call():
    """检查到期待办，拨打电话"""
    todos = get_due_todos()
    if not todos:
        return

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 发现 {len(todos)} 条到期待办")

    for todo in todos:
        todo_id = todo["id"]
        content = todo["content"]
        user_open_id = todo["open_id"]
        phone = todo.get("phone") or DEFAULT_PHONE

        if not phone:
            print(f"  [{todo_id}] 无手机号 (user={user_open_id})，跳过")
            mark_failed(todo_id)
            continue

        print(f"  [{todo_id}] 打电话: {phone} -> {content[:30]}...")

        result = make_phone_call(phone, content)

        if result.get("code") == 0:
            print(f"  [{todo_id}] ✅ 电话已发起, call_id={result.get('call_id')}")
            mark_done(todo_id)
            # 飞书通知
            send_feishu_message(user_open_id,
                                f"📞 已致电提醒：{content[:50]}")
        else:
            print(f"  [{todo_id}] ❌ 呼叫失败: {result.get('msg')}")
            # 检查重试次数
            retry_key = f"retry_{todo_id}"
            retry_count = int(os.environ.get(retry_key, 0))
            if retry_count < MAX_RETRIES:
                os.environ[retry_key] = str(retry_count + 1)
                print(f"  [{todo_id}] 将重试 ({retry_count+1}/{MAX_RETRIES})")
            else:
                mark_failed(todo_id)
                send_feishu_message(user_open_id,
                    f"❌ 电话提醒失败（已重试{MAX_RETRIES}次）：{content[:50]}")


def main():
    print("=" * 50)
    print("📞 电话提醒系统 - 提醒调度器")
    print(f"检查间隔: {CHECK_INTERVAL}s")
    print(f"最大重试: {MAX_RETRIES}次")
    print("=" * 50)

    init_db()

    # 检查阿里云配置
    if not AK_ID or not AK_SECRET:
        print("⚠️  阿里云密钥未配置，电话功能将在配置后生效")
    if not TTS_CODE:
        print("⚠️  语音模板 ID 未配置，电话功能将在配置后生效")
    if not DEFAULT_PHONE:
        print("ℹ️  默认手机号未配置，用户可通过 /bind 命令绑定")

    print("\n✅ 调度器启动，每 30 秒检查一次\n")

    while True:
        try:
            check_and_call()
        except Exception as e:
            print(f"[ERROR] 检查异常: {e}")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
