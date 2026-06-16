"""
飞书消息接收器 — WebSocket 长连接 + Whisper 语音识别
"""
import os
import sys
import json
import time
import threading
import re
from datetime import datetime
from typing import Optional

from lark_oapi.ws import Client as WSClient
from lark_oapi import LogLevel
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import init_db, get_or_create_user, add_todo
from utils import parse_time

# 加载 .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Whisper 模型（按需加载）
_whisper_model = None


def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        print("[ASR] 加载 Whisper 模型...", flush=True)
        import os as _os
        # Use local cache to avoid network issues
        _os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        _cache = _os.path.expanduser("~/.cache/faster-whisper")
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8",
                                       download_root=_cache)
        print("[ASR] Whisper 加载完成", flush=True)
    return _whisper_model


def send_feishu_message(open_id: str, text: str):
    """给用户发送飞书消息"""
    from urllib.request import Request, urlopen
    import ssl as ssl_mod

    # 获取 token
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode()
    req = Request(token_url, data=payload,
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, context=ssl_mod._create_unverified_context()) as resp:
        token = json.loads(resp.read())["tenant_access_token"]

    # 发送消息
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    msg_body = {
        "receive_id": open_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }
    req = Request(url, data=json.dumps(msg_body).encode(),
                  headers={
                      "Authorization": f"Bearer {token}",
                      "Content-Type": "application/json",
                  }, method="POST")
    with urlopen(req, context=ssl_mod._create_unverified_context()) as resp:
        result = json.loads(resp.read())
    return result.get("code") == 0


def transcribe_audio(file_key: str) -> str:
    """下载飞书语音文件并用 Whisper 转文字"""
    import urllib.request
    import ssl as ssl_mod

    ctx = ssl_mod._create_unverified_context()

    # 1. 获取 token
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode()
    req = urllib.request.Request(token_url, data=payload,
                                  headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, context=ctx) as resp:
        token = json.loads(resp.read())["tenant_access_token"]

    # 2. 下载音频文件 (先获取临时文件ID，实际从消息中拿到的 file_key 可以直接下载)
    # 注意：这里 file_key 已知，我们需要从消息中拿到的 msg_id 和 file_key 下载
    # 但语音消息的 file_key 需要先通过 message resource API 获取
    # 简化处理：直接尝试用 file_key 下载
    print(f"[ASR] 下载语音文件: {file_key}")

    # 对于语音消息，content 里已经有 file_key 了
    # 我们直接用这个 file_key 调用 speech_to_text 或下载后用 Whisper
    # 但 speech_to_text API 需要付费，这里用本地 Whisper
    # 下载文件
    # 实际上语音消息的 file_key 在 content 中，可以直接用 resource API 下载
    # 但是需要 msg_id。这里简化：语音消息的 file_key 是通过 im/v1/messages/{msg_id}/resources/{file_key} 下载
    # 由于在事件回调中没有 msg_id... 其实有的！message_id 就是 msg_id

    # 暂时返回空，实际会在回调中处理
    return ""


def extract_target_phone(text: str) -> tuple[str, str]:
    """从文本中提取指定拨打的手机号。
    支持格式：
      "打电话给138xxxx提醒他..." -> 返回 ("138xxxx...", 清理后的文本)
      "打给138xxxx..." -> 同上
    """
    m = re.search(r"(?:打?电话?给|通知|呼叫|给)(1[3-9]\d{9})", text)
    if m:
        phone = m.group(1)
        clean_text = text.replace(m.group(0), "").strip()
        return phone, clean_text
    return "", text


def strip_time_phrases(text: str) -> str:
    """去除文本开头的时间描述和电话动作，只保留核心内容"""
    t = text.strip()
    # 中文数字映射
    _cn = r"[一二两三四五六七八九十\d]+"
    # 相对时间: "一分钟后" "5分钟后" "3个小时后"
    t = re.sub(r"^(?:" + _cn + r")分[钟]?(?:后|之[后後])[,，\s]*", "", t)
    t = re.sub(r"^(?:" + _cn + r")个小时?[后之][,，\s]*", "", t)
    # 具体时间: "12:20" "12:15"
    t = re.sub(r"^\d{1,2}[:：]\d{2}[,，\s]*", "", t)
    # 日期
    t = re.sub(r"^(?:大?后天|明天|今晚|明早|今天)[,，\s]*", "", t)
    t = re.sub(r"^[下这]个?[周星期][一二三四五六日天\d][,，\s]*", "", t)
    # 时间段 + 时间点
    t = re.sub(r"^(?:上午|下午|晚上|早上|凌晨|中午)(?:" + _cn + r")?点(?:" + _cn + r")?分?[,，\s]*", "", t)
    t = re.sub(r"^(?:" + _cn + r")点(?:" + _cn + r")?分?[,，\s]*", "", t)
    # "打电话" 前缀
    t = re.sub(r"^打?电话[,，\s]*", "", t)
    return t.strip() or text


def handle_text_message(open_id: str, text: str, msg_id: str):
    """处理文字消息"""
    text = text.strip()

    # 命令
    if text.startswith("/"):
        cmd_parts = text[1:].split(maxsplit=1)
        cmd = cmd_parts[0].lower()

        if cmd == "bind" and len(cmd_parts) > 1:
            phone = cmd_parts[1].strip()
            from db import bind_phone
            bind_phone(open_id, phone)
            send_feishu_message(open_id, f"✅ 已绑定手机号：{phone}")
            return

        if cmd in ("unbind", "解绑", "取消绑定"):
            from db import bind_phone
            bind_phone(open_id, "")
            send_feishu_message(open_id, "✅ 已解绑手机号，不会再接到电话提醒")
            return

        if cmd in ("help", "帮助"):
            send_feishu_message(open_id,
                "📋 使用说明\n\n"
                "📝 创建待办：\n"
                "   \"明天下午3点提醒我对账\"\n"
                "   \"5分钟后提醒我开会\"\n"
                "   \"今晚8点吃药\"\n\n"
                "🎤 语音消息：直接发语音，自动识别\n\n"
                "📱 绑定手机：\n"
                "   /bind 138xxxx8000\n\n"
                "📊 查看待办：\n"
                "   /list\n\n"
                "❌ 撤销待办：\n"
                "   /cancel <编号>  按编号撤销\n"
                "   /cancel <关键词>  按内容搜索撤销"
            )
            return

        if cmd in ("list", "待办"):
            from db import get_user_todos, get_pending_count
            todos = get_user_todos(open_id)
            pending = get_pending_count(open_id)
            if not todos:
                send_feishu_message(open_id, "📭 暂无待办记录")
                return
            lines = [f"📋 待办列表（待处理 {pending} 条）"]
            for t in todos[:10]:
                status = "⏳" if t["status"] == "pending" else ("✅" if t["status"] == "done" else "❌")
                lines.append(f"{status} #{t['id']} {t['remind_time']} {t['content'][:30]}")
            send_feishu_message(open_id, "\n".join(lines))
            return

        if cmd in ("cancel", "取消", "撤销"):
            from db import cancel_todo, cancel_todo_by_content
            if len(cmd_parts) > 1:
                arg = cmd_parts[1].strip()
                if arg in ("all", "全部", "所有"):
                    from db import get_user_todos
                    all_todos = get_user_todos(open_id)
                    pending_ids = [t["id"] for t in all_todos if t["status"] == "pending"]
                    if not pending_ids:
                        send_feishu_message(open_id, "📭 没有待撤销的待办")
                        return
                    count = 0
                    for tid in pending_ids:
                        if cancel_todo(tid, open_id):
                            count += 1
                    send_feishu_message(open_id, f"✅ 已全部撤销（共 {count} 条）")
                    return
                if arg.isdigit():
                    # 按 ID 撤销
                    ok = cancel_todo(int(arg), open_id)
                    if ok:
                        send_feishu_message(open_id, f"✅ 已撤销 #{arg}")
                    else:
                        send_feishu_message(open_id, f"❌ 未找到待办 #{arg}，请确认编号正确或待办尚未过期")
                else:
                    # 按关键词查找并撤销
                    ids = cancel_todo_by_content(open_id, arg)
                    if ids:
                        send_feishu_message(open_id, f"✅ 已撤销 {len(ids)} 条待办")
                    else:
                        send_feishu_message(open_id, f"❌ 未找到包含「{arg}」的待办")
            else:
                send_feishu_message(open_id, "用法：/cancel <待办编号> 或 /cancel <关键词>\n先用 /list 查看编号")

        send_feishu_message(open_id, "❌ 未知命令，发送「帮助」查看可用指令")
        return

    # 普通文字 → 解析时间
    time_obj = parse_time(text)
    if not time_obj:
        send_feishu_message(open_id,
            "❌ 未能识别时间，请参考格式：\n"
            "\"明天下午3点提醒我对账\"\n"
            "\"5分钟后提醒我开会\"")
        return

    remind_time = time_obj.strftime("%Y-%m-%d %H:%M")
    # 提取指定拨打的手机号
    target_phone, clean_text = extract_target_phone(text)
    # 如果没有指定号码，用用户绑定的号码
    if not target_phone:
        from db import get_user
        user = get_user(open_id)
        if user and user.get("phone"):
            target_phone = user["phone"]
    # 去除时间前缀，只保留核心内容
    core = strip_time_phrases(clean_text or text)
    content = core
    todo_id = add_todo(open_id, content, remind_time, msg_id, target_phone)

    print(f"  ✅ 已记录: [{remind_time}] {content[:50]}", flush=True)

    phone_line = f"\nTEL: {target_phone}" if target_phone else ""
    send_feishu_message(open_id,
        f"✅ 已记录！\n"
        f"📝 内容：{content[:50]}\n"
        f"⏰ 时间：{remind_time}"
        f"{phone_line}"
    )


def on_message(data):
    """处理飞书消息事件"""
    try:
        event = data.event
        if not event or not event.message:
            return None

        msg = event.message
        msg_id = msg.message_id
        msg_type = msg.message_type
        content = msg.content
        chat_id = msg.chat_id
        sender = event.sender

        # 只处理单聊消息
        if chat_id and not chat_id.startswith("oc_"):
            return None

        open_id = sender.sender_id.open_id if sender and sender.sender_id else ""
        if not open_id:
            return None

        # 获取/创建用户
        get_or_create_user(open_id)

        if msg_type == "text":
            # 文字消息
            try:
                text_data = json.loads(content)
                text = text_data.get("text", "").strip()
            except:
                text = content.strip()
            if text:
                print(f"\n📩 [{datetime.now().strftime('%H:%M:%S')}] 收到文字: {text}", flush=True)
                handle_text_message(open_id, text, msg_id)

        elif msg_type == "audio":
            # 语音消息
            try:
                audio_data = json.loads(content)
                file_key = audio_data.get("file_key", "")
                duration = audio_data.get("duration", 0)
            except:
                file_key = ""
                duration = 0

            if file_key:
                print(f"\n🎤 [{datetime.now().strftime('%H:%M:%S')}] 收到语音 ({duration}ms)", flush=True)
                # 异步处理语音识别
                threading.Thread(target=handle_audio_message,
                                 args=(open_id, file_key, duration, msg_id),
                                 daemon=True).start()
            else:
                send_feishu_message(open_id, "❌ 未能获取语音文件，请重试或使用文字输入")

    except Exception as e:
        print(f"[ERROR] 处理消息异常: {e}")

    return None


def handle_audio_message(open_id: str, file_key: str, duration: int, msg_id: str):
    """处理语音消息：下载 → 识别 → 解析 → 存储"""
    import urllib.request
    import ssl as ssl_mod
    import subprocess
    import tempfile

    ctx = ssl_mod._create_unverified_context()

    try:
        send_feishu_message(open_id, "🎤 正在识别语音...")

        # 1. 获取 token
        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode()
        req = urllib.request.Request(token_url, data=payload,
                                      headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, context=ctx) as resp:
            token = json.loads(resp.read())["tenant_access_token"]

        # 2. 获取语音文件的 msg_id 对应的 chat 和 message
        # 对于语音消息，file_key 在收到的 content 中
        # 通过 im/v1/messages/{msg_id}/resources/{file_key}?type=file 下载
        dl_url = (f"https://open.feishu.cn/open-apis/im/v1/messages/"
                  f"{msg_id}/resources/{file_key}?type=file")
        req = urllib.request.Request(dl_url,
                                      headers={"Authorization": f"Bearer {token}"},
                                      method="GET")
        with urllib.request.urlopen(req, context=ctx) as resp:
            audio_data = resp.read()

        # 3. 保存临时文件
        ogg_path = os.path.join(tempfile.gettempdir(), f"feishu_audio_{file_key[-8:]}.ogg")
        with open(ogg_path, "wb") as f:
            f.write(audio_data)

        # 4. 转码为 WAV (Whisper 需要)
        wav_path = ogg_path.replace(".ogg", ".wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1",
             "-sample_fmt", "s16", wav_path],
            capture_output=True, timeout=30
        )

        # 5. Whisper 识别
        model = get_whisper()
        segments, info = model.transcribe(wav_path, language="zh")
        text = " ".join(seg.text for seg in segments).strip()

        # 清理临时文件
        try:
            os.remove(ogg_path)
            os.remove(wav_path)
        except:
            pass

        if not text:
            send_feishu_message(open_id, "❌ 未能识别语音内容，请重试或使用文字输入")
            return

        print(f"  🎤 识别结果: {text}", flush=True)

        # 6. 当作文字消息处理
        handle_text_message(open_id, text, msg_id)

    except Exception as e:
        print(f"[ERROR] 语音处理异常: {e}")
        send_feishu_message(open_id, f"❌ 语音识别失败: {str(e)[:50]}")


def main():
    print("=" * 50)
    print("📞 电话提醒系统 - 飞书接收器")
    print(f"App ID: {APP_ID}")
    print("=" * 50)

    # 初始化数据库
    init_db()
    print("[DB] 数据库初始化完成")
    print("[ASR] 正在加载语音模型...")
    get_whisper()

    handler = EventDispatcherHandler.builder(
        encrypt_key="", verification_token=""
    ).register_p2_im_message_receive_v1(on_message).build()

    client = WSClient(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        log_level=LogLevel.INFO,
        event_handler=handler,
        domain="https://open.feishu.cn",
        auto_reconnect=True,
    )

    print("\n✅ 监听启动，等待消息...\n")
    client.start()


if __name__ == "__main__":
    main()
