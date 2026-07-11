import os
import re
import requests
import asyncio
from telebot.async_telebot import AsyncTeleBot

# ─── CONFIGURATION ───
# Token နှင့် Admin ID ကို တိုက်ရိုက်သတ်မှတ်ထားပါတယ်
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8978508525:AAGBzwZ2CT5GNKQ2zYS1g8TJRh__DdYu6Us")
ADMIN_ID = "5510812164"
bot = AsyncTeleBot(BOT_TOKEN)

# Key သိုလှောင်ရန် ယာယီ Database (Memory-based)
# Bot ပိတ်သွားရင် key တွေပျက်မှာစိုးလို့ Admin ကို အမြဲတမ်း bypass ပေးထားပါမယ်
user_keys = {}

# ─── COMMAND HANDLERS ───

# /start Command
@bot.message_handler(commands=['start'])
async def send_welcome(message):
    welcome_text = (
        "✨ *Sky Light Ruijie Bypass Bot မှ ကြိုဆိုပါတယ်* ✨\n\n"
        "Wi-Fi Portal Link ကို Bypass လုပ်ရန်အတွက် အောက်ပါအတိုင်း ပို့ပေးပါ -\n"
        "`/setup <သင်၏ Ruijie Portal Link>`\n\n"
        "💡 _မှတ်ချက် - လူကြီးမင်းသည် Admin ဖြစ်ပါက ဘာ Key မှ ထည့်ရန်မလိုဘဲ တိုက်ရိုက်အသုံးပြုနိုင်ပါသည်။_"
    )
    await bot.reply_to(message, welcome_text, parse_mode='Markdown')

# Admin သီးသန့် Key ထုတ်ပေးသည့် Command (/genkey [plan] [user_id])
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
        
        # စနစ်ထဲတွင် အချိန်မရွေး သုံးနိုင်ရန် သိမ်းဆည်းခြင်း
        user_keys[target_id] = {
            "plan": plan,
            "expires": "9999-12-31T23:59:59Z"
        }
        
        success_msg = (
            "✅ *Key Generated Successfully*\n\n"
            f"👤 *USER ID :* `{target_id}`\n"
            f"📋 *PLAN :* {plan}\n"
            f"📅 *EXPIRES :* 9999-12-31T23:59:59Z"
        )
        await bot.reply_to(message, success_msg, parse_mode='Markdown')
    except Exception as e:
        await bot.reply_to(message, f"❌ Error: {str(e)}")

# /key Command (ရိုးရိုး User များအတွက် Key စစ်ဆေးရန်)
@bot.message_handler(commands=['key'])
async def check_key(message):
    user_id = str(message.from_user.id)
    
    if user_id == ADMIN_ID or user_id in user_keys:
        await bot.reply_to(message, "✅ သင်၏အကောင့်သည် Register လုပ်ပြီးသားဖြစ်၍ သုံးစွဲနိုင်ပါပြီ။")
    else:
        await bot.reply_to(message, "❌ သင်၏ Key ကို registered မလုပ်ရသေးပါ။")

# ─── CORE BYPASS SYSTEM (/setup သို့မဟုတ် /bypass) ───
@bot.message_handler(func=lambda message: message.text and (message.text.startswith('/setup') or message.text.startswith('/bypass')))
async def handle_bypass(message):
    user_id = str(message.from_user.id)
    
    # ခင်ဗျား (Admin) ဖြစ်ပါက သို့မဟုတ် Key ရှိပါက စစ်ဆေးမှု ကျော်ဖြတ်မည်
    if user_id == ADMIN_ID or user_id in user_keys:
        pass
    else:
        await bot.reply_to(message, "❌ /key ဖြင့် အတည်ပြုပြီးမှ အသုံးပြုပါ။")
        return

    # မက်ဆေ့ခ်ျထဲမှ Ruijie URL ကို ရှာဖွေခြင်း
    text = message.text
    url_match = re.search(r'(https?://[^\s]+)', text)
    
    if not url_match:
        await bot.reply_to(message, "⚠️ မက္ဆေ့ချ်ထဲတွင် Wi-Fi Portal Link (URL) မတွေ့ပါ။ သေချာပြန်စစ်ပေးပါ။")
        return
        
    portal_url = url_match.group(1)
    status_msg = await bot.reply_to(message, "⚡ *Sky Light Core:* Ruijie Portal ကို Bypass လုပ်နေပါပြီ... ခေတ္တစောင့်ပါ။", parse_mode='Markdown')

    # Ruijie Bypass API Processing Logic
    try:
        # URL ထဲမှ လိုအပ်သော Parameter များကို ဆွဲထုတ်ခြင်း
        gw_id = re.search(r'gw_id=([^&]+)', portal_url)
        gw_sn = re.search(r'gw_sn=([^&]+)', portal_url)
        gw_address = re.search(r'gw_address=([^&]+)', portal_url)
        gw_port = re.search(r'gw_port=([^&]+)', portal_url)
        ip = re.search(r'ip=([^&]+)', portal_url)
        mac = re.search(r'mac=([^&]+)', portal_url)
        
        if not (gw_id and gw_sn and ip and mac):
            await bot.edit_message_text("❌ URL Parameter များ မပြည့်စုံပါ။ Ruijie Portal Link အမှန်ဖြစ်ပါစေ။", chat_id=message.chat.id, message_id=status_msg.message_id)
            return

        # Ruijie Auth Server သို့ တိုက်ရိုက် Request ပို့ပြီး အင်တာနက်ဖွင့်ခြင်း
        auth_base = f"http://{gw_address.group(1)}:{gw_port.group(1)}/wifidog/auth" if gw_address else "https://portal-as.ruijienetworks.com/api/auth/wifidog"
        
        params = {
            "stage": "login",
            "gw_id": gw_id.group(1),
            "gw_sn": gw_sn.group(1),
            "ip": ip.group(1),
            "mac": mac.group(1),
            "token": "skylight_bypass_success_token"
        }
        
        # Timeout 15 စက္ကန့်ဖြင့် ခေါ်ယူခြင်း
        response = requests.get(auth_base, params=params, timeout=15)
        
        if response.status_code == 200:
            result_text = (
                "🎉 *Bypass Success! အင်တာနက် ပွင့်သွားပါပြီ* 🎉\n\n"
                f"📱 *Device MAC:* `{mac.group(1)}`\n"
                f"🌐 *IP Address:* `{ip.group(1)}`\n"
                "🚀 _ယခုအခါ Browser ပိတ်ပြီး အင်တာနက် စိတ်ကြိုက်သုံးနိုင်ပါပြီ။_"
            )
            await bot.edit_message_text(result_text, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='Markdown')
        else:
            await bot.edit_message_text(f"❌ Server မှ ငြင်းဆိုထားပါသည်။ (Status Code: {response.status_code})", chat_id=message.chat.id, message_id=status_msg.message_id)

    except requests.exceptions.RequestException as req_err:
        await bot.edit_message_text(f"📡 Network Timeout/Error: Wi-Fi Server ကို လှမ်းချိတ်မရပါ။\n({str(req_err)})", chat_id=message.chat.id, message_id=status_msg.message_id)
    except Exception as e:
        await bot.edit_message_text(f"❌ ဉာဏ်စမ်းအမှားတစ်ခု ဖြစ်သွားသည် - {str(e)}", chat_id=message.chat.id, message_id=status_msg.message_id)

# ─── BOT ASYNC POLLING ───
async def main():
    print("🚀 Sky Light Telegram Bot is starting up...")
    await bot.polling(non_stop=True)

if __name__ == "__main__":
    asyncio.run(main())
