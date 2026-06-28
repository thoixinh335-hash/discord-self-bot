"""
Discord AI Self-Bot - Main Entry Point

Chạy: python main.py
"""
import sys
import os

# Thêm thư mục hiện tại vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.config import Config
from bot.client import DiscordBot


def main():
    # Validate config
    errors = Config.validate()
    if errors:
        print("[!] Lỗi cấu hình:")
        for e in errors:
            print(f"    - {e}")
        print("\nTạo file .env từ .env.example và điền thông tin:")
        print("    copy .env.example .env")
        input("\nNhấn Enter để thoát...")
        return

    # Kiểm tra AI có sẵn không
    if not AIHandler.check_available():
        print("[!] Cảnh báo: Chưa cấu hình API key cho AI")

    # Chạy bot
    bot = DiscordBot()
    bot.run()


if __name__ == "__main__":
    from bot.ai import AIHandler

    main()
