import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser

# === الإعدادات من المتغيرات البيئية ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("❌ خطأ: يجب تعيين TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID في المتغيرات البيئية.")
    sys.exit(1)

# === دالة إرسال رسالة تيليجرام ===
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ الرسالة أُرسلت بنجاح إلى Telegram.")
        else:
            print(f"❌ فشل إرسال الرسالة: {response.text}")
    except Exception as e:
        print(f"🚨 خطأ في إرسال الرسالة: {e}")

# === جلب بيانات OI من CBOE ===
def fetch_spx_oi():
    today = datetime.now().strftime('%Y%m%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    
    # قائمة بتواريخ المحاولة (اليوم، ثم الأمس)
    dates_to_try = [today, yesterday]
    
    for date_str in dates_to_try:
        url = f"https://datashop.cboe.com/option-chain-data/spx/{date_str}_spx_options.csv"
        print(f"⏳ محاولة تحميل: {url}")
        try:
            df = pd.read_csv(url)
            # التحقق من وجود الأعمدة المطلوبة
            if 'cp_flag' in df.columns and 'open_interest' in df.columns:
                calls_oi = df[df['cp_flag'] == 'C']['open_interest'].sum()
                puts_oi = df[df['cp_flag'] == 'P']['open_interest'].sum()
                return calls_oi, puts_oi, date_str
        except Exception as e:
            print(f"❌ فشل تحميل {date_str}: {e}")
            continue
    raise Exception("فشل جلب بيانات OI لليوم والأمس من CBOE.")

# === التحليل وإرسال الإشارة ===
def analyze_and_alert():
    try:
        calls_oi, puts_oi, data_date = fetch_spx_oi()
        ratio = puts_oi / calls_oi if calls_oi > 0 else 0

        date_formatted = parser.parse(data_date).strftime('%Y-%m-%d')
        message = (
            f"📊 *SPX Open Interest Alert* ({date_formatted})\n\n"
            f"• Calls OI: {int(calls_oi):,}\n"
            f"• Puts OI: {int(puts_oi):,}\n"
            f"• Put/Call Ratio: {ratio:.3f}\n\n"
        )

        if ratio > 1.3:
            message += "🔴 *إشارة بيع قوية*\nتوقع هبوط في SPX (المضاربون يشترون	puts بكثافة)"
        elif ratio > 1.1:
            message += "🟠 *تحذير هبوطي*\nنشاط مرتفع في puts"
        elif ratio < 0.7:
            message += "🟢 *إشارة شراء قوية*\nتوقع صعود في SPX (المضاربون يشترون calls بكثافة)"
        elif ratio < 0.85:
            message += "🔵 *تحذير صعودي*\nنشاط مرتفع في calls"
        else:
            message += "⚪ *سوق متوازن*\nلا يوجد إشارة قوية حاليًا"

        send_telegram_message(message)

    except Exception as e:
        error_msg = f"🚨 *خطأ في SPX OI Bot*\n\n{str(e)}"
        send_telegram_message(error_msg)

# === النقطة الرئيسية ===
if __name__ == "__main__":
    print("🚀 بدء تشغيل SPX Open Interest Bot...")
    analyze_and_alert()
    print("🔚 انتهى التشغيل.")
