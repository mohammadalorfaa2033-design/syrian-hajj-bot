import os

from dotenv import load_dotenv

load_dotenv()

# التوكن اللي أخذته من @BotFather
BOT_TOKEN = os.environ["BOT_TOKEN"]

# قائمة بـ Telegram ID الخاصة بكل أدمن مسموح له يرسل بث جماعي (مفصولة بفواصل)
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]

# بيانات مشروع Supabase (من Project Settings -> API)
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

# كلمة مرور الدخول للوحة التحكم ومفتاح تشفير جلسات Flask
DASHBOARD_PASSWORD = os.environ["DASHBOARD_PASSWORD"]
FLASK_SECRET_KEY = os.environ["FLASK_SECRET_KEY"]
