"""
Config - Load cấu hình từ .env
"""
import os
import json
import base64
import urllib.request

from dotenv import load_dotenv

load_dotenv()


class Config:
    # Discord
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    DISCORD_EMAIL: str = os.getenv("DISCORD_EMAIL", "")
    DISCORD_PASSWORD: str = os.getenv("DISCORD_PASSWORD", "")

    # AI Provider: "openai" | "groq" | "gemini"
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openai")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Groq (OpenAI-compatible, siêu nhanh)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-70b-8192")
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Bot prefix
    BOT_PREFIX: str = os.getenv("BOT_PREFIX", "!")

    # Channel IDs cho phép auto-reply (cách nhau bằng dấu phẩy)
    ALLOWED_CHANNEL_IDS: list[str] = [
        c.strip()
        for c in os.getenv("ALLOWED_CHANNEL_IDS", "").split(",")
        if c.strip()
    ]

    # User IDs cho phép tương tác (cách nhau bằng dấu phẩy)
    ALLOWED_USER_IDS: list[str] = [
        u.strip()
        for u in os.getenv("ALLOWED_USER_IDS", "").split(",")
        if u.strip()
    ]

    # System prompt — ưu tiên đọc từ prompt.txt nếu có
    SYSTEM_PROMPT: str = os.getenv(
        "SYSTEM_PROMPT",
        "Bạn là một trợ lý AI thân thiện, hữu ích. Trả lời ngắn gọn, tự nhiên bằng tiếng Việt.",
    )

    @classmethod
    def get_system_prompt(cls) -> str:
        """Đọc system prompt từ prompt.txt nếu có, nếu không dùng env"""
        prompt_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "prompt.txt",
        )
        if os.path.exists(prompt_file):
            with open(prompt_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        return cls.SYSTEM_PROMPT

    # Admin user IDs được phép bật/tắt bot (cách nhau bằng dấu phẩy)
    ADMIN_USER_IDS: list[str] = [
        a.strip()
        for a in os.getenv("ADMIN_USER_IDS", "").split(",")
        if a.strip()
    ]

    # Channel ID để bot gửi thông báo trạng thái
    NOTIFY_CHANNEL_ID: str = os.getenv("NOTIFY_CHANNEL_ID", "")

    @classmethod
    def validate(cls) -> list[str]:
        """Kiểm tra cấu hình, trả về danh sách lỗi"""
        errors = []
        if not cls.DISCORD_TOKEN and not (cls.DISCORD_EMAIL and cls.DISCORD_PASSWORD):
            errors.append("Thiếu DISCORD_TOKEN hoặc DISCORD_EMAIL + DISCORD_PASSWORD trong .env")
        if cls.AI_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            errors.append("Thiếu OPENAI_API_KEY (AI_PROVIDER=openai)")
        if cls.AI_PROVIDER == "groq" and not cls.GROQ_API_KEY:
            errors.append("Thiếu GROQ_API_KEY (AI_PROVIDER=groq)")
        if cls.AI_PROVIDER == "gemini" and not cls.GEMINI_API_KEY:
            errors.append("Thiếu GEMINI_API_KEY (AI_PROVIDER=gemini)")
        if cls.AI_PROVIDER not in ("openai", "groq", "gemini"):
            errors.append(f"AI_PROVIDER không hợp lệ: {cls.AI_PROVIDER}")
        return errors

    @staticmethod
    def fetch_token(email: str, password: str) -> str | None:
        """Lấy token Discord từ email + password qua HTTP API.
        Trả về token nếu thành công, None nếu thất bại.
        """
        url = "https://discord.com/api/v9/auth/login"
        data = json.dumps({"login": email, "password": password}).encode()

        # Xây dựng x-super-properties (base64 của JSON)
        super_props = json.dumps({
            "os": "Windows",
            "browser": "Chrome",
            "device": "",
            "system_locale": "en-US",
            "browser_user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/132.0.0.0 Safari/537.36"
            ),
            "browser_version": "132.0.0.0",
            "os_version": "10",
            "referrer": "",
            "referring_domain": "",
            "referrer_current": "",
            "referring_domain_current": "",
            "release_channel": "stable",
            "client_build_number": 374320,
            "client_event_source": None,
        }).encode()
        x_super = base64.b64encode(super_props).decode()

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/132.0.0.0 Safari/537.36"
                ),
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://discord.com",
                "Referer": "https://discord.com/login",
                "X-Super-Properties": x_super,
                "X-Discord-Locale": "en-US",
                "X-Discord-Timezone": "Asia/Ho_Chi_Minh",
                "X-Debug-Options": "bugReporterEnabled",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read()
                result = json.loads(body)
                token = result.get("token")
                if token:
                    return token
                # Có thể cần 2FA
                if result.get("mfa"):
                    raise RuntimeError(
                        "Tài khoản bật 2FA — không thể login bằng email/password.\n"
                        "Dùng DISCORD_TOKEN thay thế (lấy từ F12 Console)."
                    )
                print(f"[!] Phản hồi lạ từ Discord: {result}")
                return None
        except urllib.error.HTTPError as e:
            err_body = e.read().decode(errors="replace")
            try:
                err_json = json.loads(err_body)
                if "captcha_key" in err_json:
                    print("[!] Discord yêu cầu captcha — không thể login bằng email/password.")
                    print("    Dùng DISCORD_TOKEN thay thế (lấy từ F12 Console).")
                    return None
            except json.JSONDecodeError:
                pass
            print(f"[!] Lỗi HTTP {e.code}: {err_body[:200]}")
            return None
