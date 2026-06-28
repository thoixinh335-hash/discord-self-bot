"""
AI Handler - Tích hợp OpenAI và Google Gemini
"""
from typing import AsyncGenerator

from .config import Config


class AIHandler:
    """Xử lý AI chat, hỗ trợ OpenAI, Groq và Gemini"""

    def __init__(self):
        self.provider = Config.AI_PROVIDER
        self._client = None

    async def _init_client(self):
        """Khởi tạo client theo provider"""
        if self._client is not None:
            return

        if self.provider in ("openai", "groq"):
            from openai import AsyncOpenAI

            if self.provider == "groq":
                # Groq dùng OpenAI-compatible API
                self._client = AsyncOpenAI(
                    api_key=Config.GROQ_API_KEY,
                    base_url=Config.GROQ_BASE_URL,
                )
            else:
                self._client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)

        elif self.provider == "gemini":
            from google import genai

            self._client = genai.AsyncClient(api_key=Config.GEMINI_API_KEY)

    async def chat(
        self,
        message: str,
        history: list[dict] | None = None,
    ) -> str:
        """
        Gửi tin nhắn đến AI và nhận phản hồi

        Args:
            message: Nội dung tin nhắn
            history: Lịch sử hội thoại [{"role": "user"/"assistant", "content": "..."}]

        Returns:
            Phản hồi từ AI
        """
        await self._init_client()

        if history is None:
            history = []

        if self.provider in ("openai", "groq"):
            return await self._chat_openai(message, history)
        elif self.provider == "gemini":
            return await self._chat_gemini(message, history)
        else:
            return f"Unknown provider: {self.provider}"

    async def _chat_openai(
        self,
        message: str,
        history: list[dict],
    ) -> str:
        model = (
            Config.GROQ_MODEL if self.provider == "groq" else Config.OPENAI_MODEL
        )
        messages = [{"role": "system", "content": Config.get_system_prompt()}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        resp = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
        )
        return resp.choices[0].message.content or "..."

    async def _chat_gemini(
        self,
        message: str,
        history: list[dict],
    ) -> str:
        # Gemini dùng content history format riêng
        contents = []
        for h in history:
            role = "user" if h["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": h["content"]}]})
        # Thêm system prompt + message mới
        full_prompt = f"{Config.get_system_prompt()}\n\nUser: {message}"

        resp = await self._client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=full_prompt,
            config={"max_output_tokens": 1024, "temperature": 0.7},
        )
        return resp.text or "..."

    @classmethod
    def check_available(cls) -> bool:
        """Kiểm tra API key có hợp lệ không"""
        if Config.AI_PROVIDER == "openai":
            return bool(Config.OPENAI_API_KEY)
        elif Config.AI_PROVIDER == "groq":
            return bool(Config.GROQ_API_KEY)
        elif Config.AI_PROVIDER == "gemini":
            return bool(Config.GEMINI_API_KEY)
        return False
