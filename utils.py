"""
工具函数 — 自然语言时间解析
"""
import re
from datetime import datetime, timedelta
from typing import Optional

# 中文数字映射
CN_NUMS = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "半": 30,
}


def _cn_to_num(s: str) -> int:
    """中文数字转整数，如 '十二' -> 12, '二十' -> 20"""
    s = s.strip()
    if s.isdigit():
        return int(s)
    # 纯中文数字
    if "十" in s:
        parts = s.split("十")
        left = CN_NUMS.get(parts[0], 1) if parts[0] else 1
        right = CN_NUMS.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return left * 10 + right
    return CN_NUMS.get(s, 0)


def _extract_time_numbers(text: str) -> list:
    """提取文本中的时间数字，支持中文和阿拉伯数字"""
    results = []
    # 匹配 12:30 或 12点30分 格式
    patterns = [
        (r"(\d{1,2})[:：](\d{2})", lambda m: (int(m.group(1)), int(m.group(2)))),
        (r"([十二两三四五六七八九十\d]+)点([一二三四五六七八九十\d]+)分?", lambda m: (_cn_to_num(m.group(1)), _cn_to_num(m.group(2)))),
        (r"([十二两三四五六七八九十\d]+)点", lambda m: (_cn_to_num(m.group(1)), 0)),
    ]
    for pat, fn in patterns:
        for m in re.finditer(pat, text):
            try:
                results.append(fn(m))
            except:
                pass
    return results


def parse_time(text: str) -> Optional[datetime]:
    """
    从自然语言中解析提醒时间。
    支持:
    - "明天下午3点提醒我对账" -> 次日 15:00
    - "5分钟后提醒我" -> 当前+5min
    - "今天晚上8点" -> 当天 20:00
    - "后天早上9点" -> 后天 09:00
    - "下周一上午10点" -> 下周一 10:00
    - "3小时后" -> 当前+3h
    - "今晚8点半" -> 当天 20:30
    """
    now = datetime.now()
    target = now.replace(second=0, microsecond=0)
    text = text.strip()

    # 相对时间: N分钟后/小时后
    rel_minutes = re.search(r"(\d+|[一二两三四五六七八九十]+)\s*分[钟]?(后|之[后後])", text)
    rel_hours = re.search(r"(\d+|[一二两三四五六七八九十]+)\s*个小[时]?(后|之[后後])", text)
    if rel_minutes:
        mins = _cn_to_num(rel_minutes.group(1))
        return target + timedelta(minutes=mins)
    if rel_hours:
        hours = _cn_to_num(rel_hours.group(1))
        return target + timedelta(hours=hours)

    # 星期偏移
    weekday_map = {
        "一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6,
        "1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6,
        "下个": 7, "下": 7,
    }
    weekday_offset = 0
    for kw, offset in weekday_map.items():
        if f"下{kw}" in text or f"下个{kw}" in text:
            weekday_offset = offset
            days_ahead = (offset - now.weekday()) % 7
            if days_ahead <= 0:
                days_ahead += 7
            target = now + timedelta(days=days_ahead)
            target = target.replace(hour=0, minute=0, second=0, microsecond=0)
            break

    # 日期偏移: 今天/明天/后天
    if "后天" in text:
        target = now + timedelta(days=2)
        target = target.replace(hour=0, minute=0, second=0, microsecond=0)
    elif "明天" in text or "明早" in text:
        target = now + timedelta(days=1)
        target = target.replace(hour=0, minute=0, second=0, microsecond=0)
    elif "今天" in text or "今晚" in text or "今天" not in text and target.hour == now.hour and target.minute == now.minute:
        # 没指定日期默认为今天
        pass
    # "大后天" 等
    elif "大后天" in text:
        target = now + timedelta(days=3)
        target = target.replace(hour=0, minute=0, second=0, microsecond=0)

    # 时间偏移: 上午/下午/早上/晚上/中午
    has_ampm = False
    if any(w in text for w in ["下午", "晚上", "傍晚"]):
        ampm_offset = 12
        has_ampm = True
    elif any(w in text for w in ["凌晨"]):
        ampm_offset = 0
        has_ampm = True
    else:
        ampm_offset = None
        has_ampm = False

    # 提取具体时间
    times = _extract_time_numbers(text)
    if times:
        hour, minute = times[0]
        if has_ampm and ampm_offset == 12 and hour < 12:
            hour += 12
        if has_ampm and ampm_offset == 0 and hour >= 12:
            hour -= 12
        target = target.replace(hour=hour % 24, minute=minute % 60)
    elif any(w in text for w in ["上午", "早上"]):
        target = target.replace(hour=9, minute=0)
    elif "中午" in text:
        target = target.replace(hour=12, minute=0)
    elif "下午" in text:
        target = target.replace(hour=14, minute=0)
    elif "晚上" in text or "傍晚" in text:
        target = target.replace(hour=19, minute=0)
    elif "凌晨" in text:
        target = target.replace(hour=3, minute=0)
    elif "今晚" in text:
        target = target.replace(hour=20, minute=0)

    # 如果时间已经过了，+1天
    if target <= now:
        target = target + timedelta(days=1)

    return target
