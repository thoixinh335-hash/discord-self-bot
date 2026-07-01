"""
AI Handler - Tích hợp OpenAI, Groq, Gemini và DeepSeek
"""
from typing import AsyncGenerator

from .config import Config


class AIHandler:
    """Xử lý AI chat, hỗ trợ OpenAI, Groq, DeepSeek và Gemini"""

    def __init__(self):
        self.provider = Config.AI_PROVIDER
        self._client = None

    async def _init_client(self):
        """Khởi tạo client theo provider"""
        if self._client is not None:
            return

        if self.provider in ("openai", "groq", "deepseek"):
            from openai import AsyncOpenAI

            if self.provider == "groq":
                self._client = AsyncOpenAI(
                    api_key=Config.GROQ_API_KEY,
                    base_url=Config.GROQ_BASE_URL,
                )
            elif self.provider == "deepseek":
                self._client = AsyncOpenAI(
                    api_key=Config.DEEPSEEK_API_KEY,
                    base_url="https://api.deepseek.com/v1",
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
        await self._init_client()

        if history is None:
            history = []

        if self.provider in ("openai", "groq", "deepseek"):
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
        if self.provider == "groq":
            model = Config.GROQ_MODEL
        elif self.provider == "deepseek":
            model = Config.DEEPSEEK_MODEL
        else:
            model = Config.OPENAI_MODEL

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
        full_prompt = f"{Config.get_system_prompt()}\n\nUser: {message}"
        resp = await self._client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=full_prompt,
            config={"max_output_tokens": 1024, "temperature": 0.7},
        )
        return resp.text or "..."

    @classmethod
    def check_available(cls) -> bool:
        if Config.AI_PROVIDER == "openai":
            return bool(Config.OPENAI_API_KEY)
        elif Config.AI_PROVIDER == "groq":
            return bool(Config.GROQ_API_KEY)
        elif Config.AI_PROVIDER == "deepseek":
            return bool(Config.DEEPSEEK_API_KEY)
        elif Config.AI_PROVIDER == "gemini":
            return bool(Config.GEMINI_API_KEY)
        return False
