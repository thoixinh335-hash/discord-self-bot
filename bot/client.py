"""
Discord Client - Kết nối và xử lý tin nhắn (discord.py-self)
"""
import asyncio
import base64
import json
import os
from typing import Callable

import discord

from .config import Config
from .ai import AIHandler


def _build_super_props() -> str:
    """Tạo x-super-properties cho Discord API"""
    return base64.b64encode(json.dumps({
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
    }).encode()).decode()


class DiscordBot:
    """Discord self-bot với AI chat + hệ thống lệnh"""

    def __init__(self):
        self.bot = discord.Client()
        self.ai = AIHandler()
        self._active_channel: int = 0  # Channel ID đang bật auto-reply, 0 = OFF
        self._spam_task: asyncio.Task | None = None  # Task auto-send
        self._spam_target: str = ""  # User bị tag
        self._spam_channel_id: int = 0  # Channel gửi
        self._spam_delay: float = 0.5  # Delay mặc định (giây)
        self._song_queue: list[dict] = []  # Queue nhạc [{url, title, web_url, duration}]
        self._now_playing: dict | None = None  # Bài đang phát
        self._patch_library_bugs()
        self._setup_events()
        self._setup_commands()

    def _patch_library_bugs(self):
        """Sửa lỗi có sẵn trong discord.py-self v2.1.0"""
        from discord.state import FakeClientPresence
        if not hasattr(FakeClientPresence, 'hidden_activities'):
            FakeClientPresence.hidden_activities = []

    def _setup_commands(self):
        """Đăng ký các lệnh prefix"""
        self._commands: dict[str, tuple[Callable, str, bool]] = {
            "help":   (self._cmd_help,   "Hiện danh sách lệnh", True),
            "status": (self._cmd_status, "Xem trạng thái bot",   True),
            "onbot":  (self._cmd_onbot,  "Bật auto-reply AI",    True),
            "offbot": (self._cmd_offbot, "Tắt auto-reply AI",    True),
            "attach": (self._cmd_attach, "Spam auto @user theo file txt", True),
            "attachai": (self._cmd_attachai, "Spam auto @user bằng AI", True),
            "detach": (self._cmd_detach, "Dừng spam auto",       True),
            "bottreo": (self._cmd_bottreo, "Vào voice channel theo ID", True),
            "yt":     (self._cmd_yt,     "Phát nhạc YouTube trong voice", True),
            "yts":    (self._cmd_yts,    "Skip bài hiện tại", True),
            "ytl":    (self._cmd_ytl,    "Xem danh sách chờ", True),
            "stop":   (self._cmd_stop,   "Dừng phát nhạc", True),
        }

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            state = "OFF" if not self._active_channel else "ON"
            print(f"[+] Đã đăng nhập: {self.bot.user} (ID: {self.bot.user.id})")
            print(f"[+] AI Provider: {Config.AI_PROVIDER}")
            print(f"[+] Bot đang {state} — dùng !onbot để bật")
            if Config.ADMIN_USER_IDS:
                print(f"[+] Admin IDs: {', '.join(Config.ADMIN_USER_IDS)}")
            else:
                print("[!] Chưa cấu hình ADMIN_USER_IDS — mọi người đều là admin!")
            try:
                await self._notify(f"🟢 **Bot đã online!**\nTrạng thái: {state}\nPrefix: `{Config.BOT_PREFIX}`\nAI: {Config.AI_PROVIDER}")
            except Exception as e:
                print(f"[!] Không gửi được thông báo online: {e}")

        @self.bot.event
        async def on_message(message):
            # === Parse lệnh prefix (kể cả từ chính mình) ===
            content = message.content or ""
            if content.startswith(Config.BOT_PREFIX):
                # Chỉ admin mới được dùng lệnh — non-admin im lặng hoàn toàn
                if not self._is_admin(message.author.id):
                    return
                try:
                    await self._handle_command(message)
                except Exception as e:
                    print(f"[!] Lỗi lệnh: {e}")
                return

            # Không auto-reply chính mình
            if message.author.id == self.bot.user.id:
                return

            # === Auto-reply (chỉ khi bot ON và đúng channel) ===
            if not self._active_channel or message.channel.id != self._active_channel:
                return

            should_reply = False

            # Bị tag
            if self.bot.user in message.mentions:
                should_reply = True

            # Reply tin nhắn của bot
            if (
                message.reference
                and message.reference.resolved
                and message.reference.resolved.author.id == self.bot.user.id
            ):
                should_reply = True

            # DM thì auto reply
            if isinstance(message.channel, discord.DMChannel):
                should_reply = True

            if should_reply:
                await self._handle_ai_reply(message)

        @self.bot.event
        async def on_error(event, *args, **kwargs):
            print(f"[!] Lỗi event {event}: {args} {kwargs}")

    # ─── Helpers ────────────────────────────────────────────────

    def _is_admin(self, user_id: int) -> bool:
        """Kiểm tra user có quyền admin không"""
        if not Config.ADMIN_USER_IDS:
            # Chưa cấu hình admin → mọi người đều là admin (cảnh báo khi start)
            return True
        return str(user_id) in Config.ADMIN_USER_IDS

    async def _notify(self, text: str):
        """Gửi thông báo đến NOTIFY_CHANNEL_ID nếu được cấu hình"""
        if not Config.NOTIFY_CHANNEL_ID:
            return
        try:
            channel = self.bot.get_channel(int(Config.NOTIFY_CHANNEL_ID))
            if channel:
                await channel.send(text)
        except Exception as e:
            print(f"[!] Không gửi được notify: {e}")

    async def _reply(self, message, text: str):
        """Gửi reply an toàn — thử reply trước, fallback sang send"""
        try:
            await message.reply(text, mention_author=False)
        except Exception:
            # Fallback: gửi không reference
            await message.channel.send(text)

    def _build_help_text(self) -> str:
        """Tạo text cho lệnh !help"""
        state = "✅ BẬT" if self._active_channel else "❌ TẮT"
        lines = [
            f"**🤖 Discord AI Bot**",
            f"**Trạng thái:** {state}",
            f"**Prefix:** `{Config.BOT_PREFIX}`",
            f"**AI:** {Config.AI_PROVIDER}",
            "",
            "**📋 Lệnh:**",
        ]
        for name, (_, desc, admin_only) in self._commands.items():
            tag = "🔒 " if admin_only else ""
            lines.append(f"  `{Config.BOT_PREFIX}{name}` — {tag}{desc}")
        lines.append("")
        lines.append("💡 Tag hoặc reply bot để chat AI (khi đã bật)")
        return "\n".join(lines)

    # ─── Command handlers ───────────────────────────────────────

    async def _handle_command(self, message):
        """Parse và thực thi lệnh"""
        parts = message.content[len(Config.BOT_PREFIX):].strip().split()
        if not parts:
            return
        cmd_name = parts[0].lower()

        cmd = self._commands.get(cmd_name)
        if not cmd:
            await self._reply(
                message,
                f"❓ Không rõ lệnh `{cmd_name}`. Gõ `{Config.BOT_PREFIX}help` để xem danh sách.",
            )
            return

        handler, _, _admin_only = cmd

        print(f"[CMD] {message.author.name}: {Config.BOT_PREFIX}{cmd_name}")
        await handler(message)

    async def _cmd_help(self, message):
        """Lệnh !help — hiện tất cả lệnh"""
        await self._reply(message, self._build_help_text())

    async def _cmd_status(self, message):
        """Lệnh !status — xem trạng thái bot"""
        state = "✅ BẬT" if self._active_channel else "❌ TẮT"
        info = (
            f"**Trạng thái bot**\n"
            f"• Auto-reply: {state}\n"
            f"• AI Provider: `{Config.AI_PROVIDER}`\n"
            f"• Prefix: `{Config.BOT_PREFIX}`\n"
            f"• Allowed channels: {len(Config.ALLOWED_CHANNEL_IDS) or 'tất cả'}\n"
            f"• Allowed users: {len(Config.ALLOWED_USER_IDS) or 'tất cả'}"
        )
        await self._reply(message, info)

    async def _cmd_onbot(self, message):
        """Lệnh !onbot — bật auto-reply AI tại channel hiện tại"""
        if self._active_channel:
            await self._reply(message, f"⚠️ Bot đã đang BẬT ở channel <#{self._active_channel}>.")
        else:
            self._active_channel = message.channel.id
            print(f"[+] Admin {message.author} đã BẬT bot tại channel {message.channel.id}")
            await self._reply(
                message,
                f"✅ **Bot đã BẬT** tại channel này — auto-reply AI đang hoạt động.",
            )

    async def _cmd_offbot(self, message):
        """Lệnh !offbot — tắt auto-reply AI"""
        if not self._active_channel:
            await self._reply(message, "⚠️ Bot đã đang TẮT sẵn rồi.")
        else:
            self._active_channel = 0
            print(f"[+] Admin {message.author} đã TẮT bot")
            await self._reply(
                message,
                "🛑 **Bot đã TẮT** — chỉ nhận lệnh, không auto-reply.",
            )

    async def _cmd_bottreo(self, message):
        """Lệnh !bottreo <voice_channel_id> — bot vào voice channel"""
        parts = message.content.split()
        if len(parts) < 2:
            await self._reply(
                message,
                f"❌ Thiếu Channel ID. Dùng: `{Config.BOT_PREFIX}bottreo <ID>`\n"
                "Lấy ID: Bật Developer Mode → Chuột phải voice channel → Copy ID",
            )
            return

        channel_id = parts[1]
        try:
            channel_id_int = int(channel_id)
        except ValueError:
            await self._reply(message, f"❌ `{channel_id}` không phải ID hợp lệ (phải là số).")
            return

        channel = self.bot.get_channel(channel_id_int)
        if channel is None:
            await self._reply(message, f"❌ Không tìm thấy channel với ID `{channel_id}`.")
            return

        if not isinstance(channel, discord.VoiceChannel):
            await self._reply(message, f"❌ `<#{channel_id_int}>` không phải voice channel.")
            return

        # Kiểm tra quyền + trạng thái
        voice_client = discord.utils.get(self.bot.voice_clients, guild=channel.guild)
        if voice_client:
            if voice_client.channel.id == channel_id_int:
                await self._reply(message, f"⚠️ Bot đã đang ở trong <#{channel_id_int}> rồi.")
                return
            # Đang ở channel khác → di chuyển
            await voice_client.move_to(channel)
            await self._unmute_voice(channel.guild, voice_client)
            await self._reply(message, f"🔊 Đã di chuyển sang <#{channel_id_int}>")
            print(f"[VOICE] Đã chuyển sang {channel.name} ({channel.guild.name})")
            return

        # Vào channel mới
        try:
            voice_client = await channel.connect(self_mute=False, self_deaf=False)
            # Fix: đôi lúc Discord tự mute/deaf sau connect, set lại sau khi voice ready
            await self._unmute_voice(channel.guild, voice_client)
            await self._reply(message, f"🔊 Đã vào voice channel <#{channel_id_int}>")
            print(f"[VOICE] Đã vào {channel.name} ({channel.guild.name})")
        except discord.Forbidden:
            await self._reply(message, "❌ Không có quyền vào voice channel này.")
        except asyncio.TimeoutError:
            await self._reply(message, "❌ Timeout khi kết nối voice channel.")
        except Exception as e:
            await self._reply(message, f"❌ Lỗi: {str(e)[:150]}")
            print(f"[VOICE] Lỗi: {e}")

    async def _cmd_yt(self, message):
        """Lệnh !yt <link> — thêm vào queue + phát nếu chưa có gì"""
        voice_client = discord.utils.find(
            lambda vc: vc.guild.id == message.guild.id, self.bot.voice_clients
        ) if message.guild else None

        if not voice_client or not voice_client.is_connected():
            await self._reply(
                message,
                f"❌ Bot chưa ở voice. Dùng `{Config.BOT_PREFIX}bottreo <ID>` trước.",
            )
            return

        parts = message.content.split(maxsplit=1)
        if len(parts) < 2:
            await self._reply(message, f"❌ Thiếu link. VD: `{Config.BOT_PREFIX}yt https://youtu.be/...`")
            return

        url = parts[1].strip().strip("<>")

        try:
            import yt_dlp
            loop = asyncio.get_event_loop()

            def extract():
                opts = {"format": "bestaudio/best", "quiet": True, "noplaylist": True}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return {
                        "url": info.get("url"),
                        "title": info.get("title", "YouTube"),
                        "web_url": info.get("webpage_url", url),
                        "duration": info.get("duration", 0),
                    }

            song = await loop.run_in_executor(None, extract)
            self._song_queue.append(song)

            # Format
            mins, secs = divmod(song["duration"] or 0, 60)
            dur = f"{mins}:{secs:02d}" if song["duration"] else "??:??"

            if voice_client.is_playing():
                # Đang phát → thêm vào queue
                pos = len(self._song_queue) - 1
                await self._reply(
                    message,
                    f"📝 **Đã thêm vào queue (#{pos}):** {song['title']}\n⏱ {dur} | 👉 {song['web_url']}",
                )
            else:
                # Chưa có gì → phát luôn
                await self._reply(
                    message,
                    f"▶️ **Đang phát:** {song['title']}\n⏱ {dur} | 👉 {song['web_url']}",
                )
                await self._play_next(voice_client)

        except Exception as e:
            await self._reply(message, f"❌ Lỗi: {str(e)[:150]}")
            print(f"[YT] Lỗi: {e}")

    async def _play_next(self, voice_client):
        """Phát bài tiếp theo trong queue (tự gọi khi bài trước kết thúc)"""
        if not self._song_queue:
            self._now_playing = None
            return

        song = self._song_queue.pop(0)
        self._now_playing = song

        try:
            import yt_dlp
            loop = asyncio.get_event_loop()

            def extract_now():
                opts = {"format": "bestaudio/best", "quiet": True, "noplaylist": True}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(song["web_url"], download=False)
                    return info.get("url")

            audio_url = await loop.run_in_executor(None, extract_now)

            source = discord.FFmpegPCMAudio(
                audio_url,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn",
            )
            voice_client.play(source, after=lambda _: asyncio.run_coroutine_threadsafe(
                self._on_song_end(voice_client), self.bot.loop
            ))
            print(f"[YT] ▶️ {song['title']}")

        except Exception as e:
            print(f"[YT] Lỗi play_next: {e}")
            # Skip lỗi, phát bài tiếp
            self._now_playing = None
            await self._play_next(voice_client)

    async def _on_song_end(self, voice_client):
        """Callback khi bài hát kết thúc → auto play next"""
        self._now_playing = None
        if self._song_queue:
            await self._play_next(voice_client)

    async def _cmd_yts(self, message):
        """Lệnh !yts — skip bài hiện tại, phát bài tiếp"""
        voice_client = discord.utils.find(
            lambda vc: vc.guild.id == message.guild.id, self.bot.voice_clients
        ) if message.guild else None

        if not voice_client or not voice_client.is_playing():
            await self._reply(message, "⚠️ Không có gì đang phát.")
            return

        skipped = self._now_playing.get("title", "???") if self._now_playing else "???"
        voice_client.stop()

        if self._song_queue:
            next_title = self._song_queue[0]["title"]
            await self._reply(message, f"⏭️ Đã skip **{skipped}**\n▶️ Tiếp theo: **{next_title}**")
        else:
            await self._reply(message, f"⏭️ Đã skip **{skipped}**\n📭 Queue trống.")
        print(f"[YT] Skip → {skipped}")

    async def _cmd_ytl(self, message):
        """Lệnh !ytl — xem danh sách chờ"""
        if not self._now_playing and not self._song_queue:
            await self._reply(message, "📭 Queue đang trống.")
            return

        lines = ["🎵 **Queue nhạc:**"]
        if self._now_playing:
            t = self._now_playing
            mins, secs = divmod(t.get("duration", 0) or 0, 60)
            lines.append(f"▶️ **{t['title']}** | ⏱ {mins}:{secs:02d}")

        for i, song in enumerate(self._song_queue, 1):
            mins, secs = divmod(song.get("duration", 0) or 0, 60)
            lines.append(f"  `#{i}` {song['title']} | ⏱ {mins}:{secs:02d}")

        lines.append(f"📊 Tổng: **{len(self._song_queue)}** bài đang chờ")
        await self._reply(message, "\n".join(lines))

    async def _cmd_stop(self, message):
        """Lệnh !stop — dừng phát + clear queue"""
        voice_client = discord.utils.find(
            lambda vc: vc.guild.id == message.guild.id, self.bot.voice_clients
        ) if message.guild else None

        stopped = False

        if voice_client and voice_client.is_playing():
            voice_client.stop()
            stopped = True

        queue_count = len(self._song_queue)
        self._song_queue.clear()
        self._now_playing = None
        if queue_count > 0:
            stopped = True

        if not stopped:
            await self._reply(message, "⚠️ Không có gì đang phát.")
            return

        await self._reply(message, f"⏹️ Đã dừng + xóa {queue_count} bài trong queue.")
        print("[STOP] Đã dừng + clear queue")

    @staticmethod
    async def _unmute_voice(guild, voice_client=None) -> None:
        """Bỏ tự động mute mic + deafen headphone khi vào voice"""
        try:
            # Đợi voice client sẵn sàng (handshake DAVE hoàn tất)
            waited = 0
            while voice_client and not voice_client.is_connected():
                await asyncio.sleep(0.3)
                waited += 1
                if waited > 20:  # timeout 6s
                    break
            # Gửi voice state qua gateway
            await guild.change_voice_state(
                channel=guild.me.voice.channel if guild.me.voice else None,
                self_mute=False,
                self_deaf=False,
            )
            print(f"[VOICE] Đã unmute + undeafen")
        except Exception as e:
            print(f"[VOICE] Không unmute được: {e}")

    # ─── Attach / Detach (spam auto) ──────────────────────────

    async def _cmd_attach(self, message):
        """Lệnh !attach @user [delay_giây] — gửi auto theo file attach.txt"""
        if self._spam_task:
            await self._reply(message, "⚠️ Đang spam rồi, dùng `!detach` để dừng trước.")
            return

        # Lấy user bị tag
        if not message.mentions:
            await self._reply(message, "❌ Phải tag 1 người. VD: `!attach @Tên 0.5`")
            return
        target = message.mentions[0]
        self._spam_target = target.mention
        self._spam_channel_id = message.channel.id

        # Parse delay (mặc định 0.5s)
        parts = message.content.split()
        delay = 0.5
        if len(parts) >= 3:
            try:
                delay = float(parts[2])
                delay = max(0.05, min(delay, 60.0))  # giới hạn 0.05s - 60s
            except ValueError:
                pass  # giữ mặc định

        self._spam_delay = delay

        # Đọc file attach.txt
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "attach.txt",
        )
        if not os.path.exists(file_path):
            await self._reply(message, "❌ Không tìm thấy `attach.txt`. Tạo file này trong thư mục bot.")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]

        if not lines:
            await self._reply(message, "❌ `attach.txt` trống.")
            return

        # Bắt đầu loop
        self._spam_task = asyncio.create_task(self._spam_loop(lines))
        print(f"[SPAM] Bắt đầu spam {len(lines)} dòng → {target.name} (delay={delay}s)")
        await self._reply(
            message,
            f"✅ Bắt đầu gửi {len(lines)} dòng → {target.mention}\n"
            f"⏱ Delay: **{delay}s** | Dùng `!detach` để dừng.",
        )

    async def _cmd_attachai(self, message):
        """Lệnh !attachai @user [delay_giây] — AI tự nghĩ câu để gửi"""
        if self._spam_task:
            await self._reply(message, "⚠️ Đang spam rồi, dùng `!detach` để dừng trước.")
            return

        if not message.mentions:
            await self._reply(message, "❌ Phải tag 1 người. VD: `!attachai @Tên 2.5`")
            return

        target = message.mentions[0]
        self._spam_target = target.mention
        self._spam_channel_id = message.channel.id

        # Parse delay (mặc định 3s)
        parts = message.content.split()
        delay = 3.0
        if len(parts) >= 3:
            try:
                delay = float(parts[2])
                delay = max(0.5, min(delay, 60.0))  # AI cần delay tối thiểu 0.5s
            except ValueError:
                pass

        self._spam_delay = delay

        self._spam_task = asyncio.create_task(self._spam_ai_loop(target.name))
        print(f"[SPAM AI] Bắt đầu spam AI → {target.name} (delay={delay}s)")
        await self._reply(
            message,
            f"🤖 AI bắt đầu tự viết câu → {target.mention}\n"
            f"⏱ Delay: **{delay}s** | Dùng `!detach` để dừng.",
        )

    async def _spam_ai_loop(self, target_name: str):
        """Loop AI tự sinh câu, gửi liên tục"""
        prompt = (
            f"Bạn đang nói chuyện với một cô gái tên {target_name}. "
            "Mỗi lần hãy nghĩ ra 1 câu nhắn ngắn gọn (1-2 câu) bằng tiếng Việt, "
            "tự nhiên, hài hước, flirty nhẹ. Không lặp lại câu cũ. "
            "Không hỏi về gặp mặt/địa điểm. Chỉ trả về câu nhắn, không giải thích."
        )
        used: list[str] = []
        try:
            while True:
                channel = self.bot.get_channel(self._spam_channel_id)
                if not channel:
                    break
                # Gọi AI sinh câu
                reply = await self.ai.chat(
                    f"Nghĩ 1 câu mới để nhắn với {target_name}. "
                    f"Đừng dùng lại: {', '.join(used[-5:]) if used else 'chưa có'}",
                    [{"role": "system", "content": prompt}],
                )
                reply = reply.strip().strip('"').strip("'")
                used.append(reply)
                text = f"{self._spam_target} {reply}"
                await channel.send(text)
                await asyncio.sleep(self._spam_delay)
        except asyncio.CancelledError:
            print("[SPAM AI] Task bị hủy")
        except Exception as e:
            print(f"[SPAM AI] Lỗi: {e}")

    async def _cmd_detach(self, message):
        """Lệnh !detach — dừng spam auto"""
        if not self._spam_task:
            await self._reply(message, "⚠️ Không có spam nào đang chạy.")
            return
        self._spam_task.cancel()
        self._spam_task = None
        self._spam_target = ""
        self._spam_channel_id = 0
        self._spam_delay = 0.5
        print("[SPAM] Đã dừng bởi admin")
        await self._reply(message, "🛑 Đã dừng auto-send.")

    async def _spam_loop(self, lines: list[str]):
        """Loop gửi từng dòng, hết file quay lại đầu"""
        idx = 0
        try:
            while True:
                channel = self.bot.get_channel(self._spam_channel_id)
                if not channel:
                    break
                line = lines[idx]
                text = f"{self._spam_target} {line}"
                await channel.send(text)
                idx = (idx + 1) % len(lines)
                await asyncio.sleep(self._spam_delay)
        except asyncio.CancelledError:
            print("[SPAM] Task bị hủy")
        except Exception as e:
            print(f"[SPAM] Lỗi: {e}")

    # ─── AI Reply ───────────────────────────────────────────────

    async def _handle_ai_reply(self, message):
        """Xử lý reply AI"""
        try:
            # Xóa mention của bot khỏi nội dung
            content = message.content
            for mention in message.mentions:
                content = content.replace(f"<@{mention.id}>", "").replace(
                    f"<@!{mention.id}>", ""
                )
            content = content.strip()

            if not content:
                content = "Xin chào!"  # mặc định nếu chỉ tag không

            # Thêm context: ai, ở đâu
            author_name = message.author.display_name or message.author.name
            if isinstance(message.channel, discord.DMChannel):
                ctx = f"[DM với {author_name}]"
            else:
                guild = message.guild.name if message.guild else "Unknown"
                channel = message.channel.name if hasattr(message.channel, 'name') else "Unknown"
                ctx = f"[{guild} / #{channel} / {author_name}]"

            # Typing indicator
            async with message.channel.typing():
                # Lấy lịch sử hội thoại gần đây (tối đa 10 tin)
                history = []
                async for msg in message.channel.history(limit=10, before=message):
                    name = msg.author.display_name or msg.author.name
                    if msg.author.id == self.bot.user.id:
                        history.insert(0, {
                            "role": "assistant",
                            "content": msg.content,
                        })
                    elif msg.author.id == message.author.id:
                        history.insert(0, {
                            "role": "user",
                            "content": f"[{name}]: {msg.content}",
                        })

                # Gọi AI với context
                reply = await self.ai.chat(f"{ctx}\n{content}", history)

            # Gửi phản hồi (chia nhỏ nếu quá 2000 ký tự)
            if len(reply) > 2000:
                parts = [reply[i : i + 1990] for i in range(0, len(reply), 1990)]
                for part in parts:
                    await self._reply(message, part)
                    await asyncio.sleep(0.5)
            else:
                await self._reply(message, reply)

            print(f"[>] Reply to {message.author}: {reply[:100]}...")

        except Exception as e:
            print(f"[!] Lỗi AI reply: {e}")
            try:
                await self._reply(message, f"❌ Lỗi: {str(e)[:100]}")
            except Exception:
                pass

    # ─── Run ────────────────────────────────────────────────────

    def run(self):
        """Chạy bot — login bằng email + password"""
        if not Config.DISCORD_EMAIL or not Config.DISCORD_PASSWORD:
            print("[!] Lỗi: Thiếu DISCORD_EMAIL + DISCORD_PASSWORD trong .env")
            return

        print(f"[*] Đang lấy token Discord bằng email: {Config.DISCORD_EMAIL}")
        token = Config.fetch_token(Config.DISCORD_EMAIL, Config.DISCORD_PASSWORD)
        if not token:
            print("[!] Không lấy được token. Kiểm tra email/password hoặc bật 2FA?")
            return
        print(f"[+] Đã lấy token: {token[:25]}...")
        self.bot.run(token)
