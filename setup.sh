#!/bin/bash
# Setup script cho Discord Self-Bot trên Ubuntu/Debian VPS
# Chạy: bash setup.sh

set -e

echo "======================================="
echo " Discord Self-Bot VPS Setup"
echo "======================================="

# 1. Update + cài dependencies hệ thống
echo "[1/6] Cài đặt system packages..."
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv ffmpeg curl git

# 2. Cài Rust (cần cho davey - voice encryption)
echo "[2/6] Cài đặt Rust..."
if ! command -v rustc &>/dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# 3. Tạo virtual environment
echo "[3/6] Tạo Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Cài Python packages
echo "[4/6] Cài đặt Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Copy .env nếu chưa có
echo "[5/6] Kiểm tra .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "!!! ĐÃ TẠO .env TỪ .env.example — SỬA LẠI THÔNG TIN TRONG .env TRƯỚC KHI CHẠY !!!"
    echo "    nano .env"
fi

# 6. Tạo systemd service
echo "[6/6] Tạo systemd service..."
SERVICE_FILE="/etc/systemd/system/discord-bot.service"
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Discord Self-Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$CURRENT_DIR/venv/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=append:$CURRENT_DIR/bot.log
StandardError=append:$CURRENT_DIR/bot_error.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable discord-bot

echo ""
echo "======================================="
echo " SETUP HOÀN TẤT!"
echo "======================================="
echo ""
echo "Các lệnh quan trọng:"
echo "  sudo systemctl start discord-bot   # Chạy bot"
echo "  sudo systemctl stop discord-bot    # Dừng bot"
echo "  sudo systemctl status discord-bot  # Xem trạng thái"
echo "  sudo journalctl -u discord-bot -f  # Xem log real-time"
echo ""
echo "Trước khi start, nhớ sửa file .env:"
echo "  nano .env"
echo ""
