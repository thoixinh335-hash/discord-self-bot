# Discord AI Self-Bot 🤖

Chatbot AI tự động trả lời tin nhắn trên Discord bằng tài khoản cá nhân, dùng **Groq** (miễn phí, siêu nhanh).

> ⚠️ **CẢNH BÁO:** Self-bot vi phạm Điều khoản Dịch vụ Discord.
> Dùng tài khoản phụ, không dùng account chính.

## Tính năng

- 🤖 AI chat siêu nhanh nhờ **Groq** (Llama 3 70B miễn phí)
- 💬 Trả lời khi bị tag, reply, hoặc trong DM
- 🧠 Nhớ lịch sử hội thoại gần nhất
- 🔒 Lọc channel/user được phép
- ⚡ Gõ typing indicator khi đang xử lý

## Cài đặt

```bash
# 1. Clone & cd vào thư mục
cd d:\discord_bot

# 2. Tạo virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Cài dependencies
pip install -r requirements.txt

# 4. Tạo file .env
copy .env.example .env
```

## Cấu hình

Mở file `.env` và điền thông tin:

```env
# 🔑 Token Discord
DISCORD_TOKEN=your_token_here

# 🤖 AI Provider: "groq" (mặc định)
AI_PROVIDER=groq

# Groq API key (miễn phí) - https://console.groq.com/keys
GROQ_API_KEY=gsk_your_groq_key
GROQ_MODEL=llama3-70b-8192
```

### Lấy Discord Token

1. Mở Discord Web (https://discord.com/app)
2. `F12` → Console
3. Paste:

```js
(webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken()).exports.default.getToken()
```

4. Copy token được trả về, dán vào `DISCORD_TOKEN` trong `.env`

### Lấy API Key (chọn 1)

- **Groq** 🎯 — *khuyên dùng:* https://console.groq.com/keys (miễn phí, siêu nhanh)
- **OpenAI:** https://platform.openai.com/api-keys (cần có $)
- **Gemini:** https://aistudio.google.com/apikey (miễn phí)

## Chạy

```bash
python main.py
```

## Cách dùng

- Tag bot trong channel → bot trả lời
- Reply tin nhắn của bot → bot trả lời
- Nhắn tin riêng (DM) → bot tự động trả lời

Tùy chỉnh trong `.env`:
- `ALLOWED_CHANNEL_IDS` = chỉ cho phép những channel này (cách nhau bằng dấu phẩy)
- `ALLOWED_USER_IDS` = chỉ cho phép những user này
- `SYSTEM_PROMPT` = thay đổi tính cách bot
- `BOT_PREFIX` = prefix cho lệnh (mặc định `!`)
