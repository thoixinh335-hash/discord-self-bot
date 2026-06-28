"""
User Memory System — Bot nhớ người dùng và tiến hóa phản hồi theo thời gian
"""
import json
import os
import time


class UserMemory:
    """Lưu trữ memory cho từng user"""

    def __init__(self, storage_path: str = "user_memory.json"):
        self._path = storage_path
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {}

    def _save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    def get_profile(self, user_id: int, user_name: str) -> dict:
        sid = str(user_id)
        if sid not in self._data:
            self._data[sid] = {
                "name": user_name,
                "first_met": time.time(),
                "interactions": 0,
                "memories": [],
                "vibe": "thân thiện",
            }
            self._save()

        profile = self._data[sid]
        profile["name"] = user_name  # update name nếu đổi
        return profile

    def add_interaction(self, user_id: int, user_name: str, message: str):
        sid = str(user_id)
        profile = self.get_profile(user_id, user_name)
        profile["interactions"] += 1
        profile["last_seen"] = time.time()

        # Lưu key memories ngắn
        if len(message) > 10 and len(message) < 200:
            profile["memories"].append(message[:150])
            if len(profile["memories"]) > 10:
                profile["memories"] = profile["memories"][-10:]

        # Tiến hóa vibe dựa trên số lần tương tác
        n = profile["interactions"]
        if n < 5:
            profile["vibe"] = "lịch sự, làm quen"
        elif n < 20:
            profile["vibe"] = "thân thiện, gần gũi"
        elif n < 50:
            profile["vibe"] = "bạn thân, thoải mái, hài hước"
        else:
            profile["vibe"] = "cực kỳ thân, tự nhiên, flirty nhẹ, nhiều cảm xúc"

        self._save()

    def build_context_prompt(self, user_id: int, user_name: str, gender: str, is_dm: bool) -> str:
        profile = self.get_profile(user_id, user_name)
        n = profile["interactions"]
        vibe = profile["vibe"]
        memories = profile["memories"]
        gender_text = {"female": "cô ấy", "male": "anh ấy", "unknown": "người này"}.get(gender, "người này")

        # Build context cho AI
        parts = []
        parts.append(f"Bạn đang nói chuyện với {user_name} ({gender_text}).")
        parts.append(f"Hai bạn đã nói chuyện {n} lần. Mối quan hệ: {vibe}.")

        if memories:
            recent = memories[-3:]
            parts.append(f"Những điều {gender_text} từng nói: " + " | ".join(recent))

        # Style instruction
        style_map = {
            "lịch sự, làm quen": "Trả lời lịch sự, nhẹ nhàng, tạo thiện cảm.",
            "thân thiện, gần gũi": "Trả lời tự nhiên, thêm chút hài hước, thể hiện sự quan tâm.",
            "bạn thân, thoải mái, hài hước": "Trả lời như bạn thân, hài hước, chêm meme/emoji, cực kỳ thoải mái.",
            "cực kỳ thân, tự nhiên, flirty nhẹ, nhiều cảm xúc": "Trả lời cực kỳ tự nhiên, nhiều cảm xúc, flirty tinh tế, như người yêu hoặc best friend.",
        }
        parts.append(style_map.get(vibe, "Trả lời tự nhiên."))

        return "\n".join(parts)
