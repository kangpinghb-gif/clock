#!/usr/bin/env bash
# 电话提醒系统 — 配置向导
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ENV="$DIR/.env"

echo "============================================"
echo "  📞 电话提醒系统 — 配置向导"
echo "============================================"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1. 飞书应用配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "  App ID    : " AID
read -p "  App Secret: " ASEC
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  2. 阿里云语音服务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "  AccessKey ID    : " KID
read -p "  AccessKey Secret: " KSEC
read -p "  语音模板 ID     : " TTS
read -p "  手机号 (+86xxx) : " PHONE
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  3. 写入配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"

cat > "$ENV" << EOF
# --- Feishu ---
FEISHU_APP_ID=${AID}
FEISHU_APP_SECRET=${ASEC}

# --- Aliyun Voice ---
ALIYUN_ACCESS_KEY_ID=${KID}
ALIYUN_ACCESS_KEY_SECRET=${KSEC}
ALIYUN_TTS_CODE=${TTS}
ALIYUN_CALLED_NUMBER=${PHONE}

# --- System ---
DB_PATH=${DIR}/todos.db
WHISPER_MODEL=base
EOF

echo "✅ 配置文件已生成: $ENV"
echo ""
echo "下一步："
echo "  cd $DIR"
echo "  pip install -r requirements.txt --break-system-packages"
echo "  pip install faster-whisper --break-system-packages"
echo "  pip install alibabacloud_dyvmsapi20170525 --break-system-packages"
echo "  sudo cp todo-recv.service /etc/systemd/system/"
echo "  sudo cp todo-remind.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable --now todo-recv.service"
echo "  sudo systemctl enable --now todo-remind.service"
echo ""
