#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
PS AI Recap — Telegram Bot
Password Reset Bot
"""

import sys
import os
from datetime import datetime
from loguru import logger

# ============================================================================
# PATH SETUP
# ============================================================================
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# ============================================================================
# TELEGRAM BOT TOKEN
# ============================================================================
BOT_TOKEN = "8567534759:AAEVQipMscrmVNVsl2_G0FqoQcFjHXB_084"

# ============================================================================
# IMPORTS
# ============================================================================
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ContextTypes,
        filters,
    )
    _TELEGRAM_AVAILABLE = True
except Exception as e:
    _TELEGRAM_AVAILABLE = False
    print(f"❌ python-telegram-bot not installed: {e}")

try:
    from app.services import coin_system as cs
    _COIN_SYSTEM_AVAILABLE = True
except Exception as e:
    _COIN_SYSTEM_AVAILABLE = False
    print(f"❌ coin_system not available: {e}")


# ============================================================================
# USER STATE (Email စောင့်နေတဲ့ User တွေ)
# ============================================================================
WAITING_EMAIL = {}  # {chat_id: True}


# ============================================================================
# COMMANDS
# ============================================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start — Welcome Message"""
    user = update.effective_user
    name = user.first_name or "User"

    welcome = (
        f"🎬 <b>PS AI Recap</b>\n"
        f"Movie Recap Studio\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"မင်္ဂလာပါ <b>{name}</b> 👋\n\n"
        f"ဒီ Bot က — <b>Password Reset</b> အတွက် ဖြစ်ပါတယ်။\n\n"
        f"<b>📋 Commands —</b>\n"
        f"🔐 /reset — Password Reset Code ရယူ\n"
        f"❓ /help — အကူအညီ\n"
        f"🆔 /mycode — သင့် Reset Code ကြည့်\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Password မေ့သွားရင် — /reset ကို နှိပ်ပါ"
    )

    await update.message.reply_text(
        welcome,
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help — Help Message"""
    help_text = (
        "❓ <b>အကူအညီ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>🔐 Password Reset လုပ်နည်း —</b>\n\n"
        "<b>၁။</b> /reset ကို နှိပ်ပါ\n"
        "<b>၂။</b> သင့် <b>Email</b> ကို ပို့ပါ\n"
        "<b>၃။</b> Bot က <b>6 လုံး Code</b> ပို့ပေးမယ်\n"
        "<b>၄။</b> Website မှာ — Email + Code + Password အသစ် ထည့်ပါ\n"
        "<b>၅။</b> Login ပြန်ဝင်ပါ ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <b>သတိထားပါ —</b>\n"
        "• Code က — <b>၁ နာရီ</b> ပဲ သက်တမ်းရှိတယ်\n"
        "• Code ကို — ဘယ်သူ့ကိုမှ မပြနဲ့\n"
        "• တစ်ခါပဲ သုံးလို့ ရတယ်\n\n"
        "📞 <b>ဆက်သွယ်ရန်:</b> @Ps2005b"
    )

    await update.message.reply_text(
        help_text,
        parse_mode="HTML",
    )


async def cmd_mycode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mycode — User ရဲ့ Code ကြည့် (ဆက်လုပ်ရန်)"""
    await update.message.reply_text(
        "💡 သင့် Reset Code ကို ပြန်ကြည့်ချင်ရင် — /reset ကို ပြန်နှိပ်ပါ။",
        parse_mode="HTML",
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reset — Password Reset စတင်"""
    chat_id = update.effective_chat.id

    if not _COIN_SYSTEM_AVAILABLE:
        await update.message.reply_text(
            "❌ Service မရနိုင်ပါ။ နောက်မှ ပြန်စမ်းပါ။",
        )
        return

    WAITING_EMAIL[chat_id] = True

    await update.message.reply_text(
        "🔐 <b>Password Reset</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "သင့် <b>Email</b> ကို ပို့ပေးပါ။\n\n"
        "<i>ဥပမာ — your@email.com</i>\n\n"
        "❌ Cancel လုပ်ချင်ရင် — /cancel",
        parse_mode="HTML",
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/cancel — Cancel Reset"""
    chat_id = update.effective_chat.id
    WAITING_EMAIL.pop(chat_id, None)

    await update.message.reply_text(
        "✅ Cancel လုပ်ပြီးပါပြီ။",
    )


# ============================================================================
# MESSAGE HANDLER — Email လက်ခံ
# ============================================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User ပို့တဲ့ Message ကို ကိုင်"""
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()

    # --- Email စောင့်နေတဲ့ User လား? ---
    if not WAITING_EMAIL.get(chat_id):
        await update.message.reply_text(
            "💡 Command များ — /start, /reset, /help",
        )
        return

    # --- Email မှန်/မှား စစ် ---
    if "@" not in text or "." not in text or len(text) > 100:
        await update.message.reply_text(
            "❌ Email မမှန်ကန်ပါ။ ပြန်ပို့ပါ။\n\n"
            "<i>ဥပမာ — your@email.com</i>",
            parse_mode="HTML",
        )
        return

    # --- Loading ---
    loading_msg = await update.message.reply_text(
        "⏳ စစ်ဆေးနေပါသည်...",
    )

    # --- Reset Code ဖန်တီး ---
    try:
        result = cs.create_password_reset(text, method="telegram", hours=1)
    except Exception as e:
        logger.error(f"create_password_reset failed: {e}")
        await loading_msg.edit_text(
            f"❌ Error — {e}",
        )
        WAITING_EMAIL.pop(chat_id, None)
        return

    WAITING_EMAIL.pop(chat_id, None)

    if not result.get("success"):
        await loading_msg.edit_text(
            f"❌ {result.get('error', 'Unknown error')}\n\n"
            f"💡 Email ကို ပြန်စစ်ပါ။",
        )
        return

    # --- Code ပို့ ---
    code = result["code"]
    expires_at = result.get("expires_at", "")
    user_code = result.get("user_code", "")

    # Expires time ကို Format
    expires_str = ""
    try:
        exp_dt = datetime.fromisoformat(str(expires_at).replace(" ", "T"))
        expires_str = exp_dt.strftime("%H:%M (%d/%m/%Y)")
    except Exception:
        expires_str = expires_at

    success_text = (
        f"✅ <b>Reset Code ရပါပြီ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>User ID:</b> {user_code}\n"
        f"📧 <b>Email:</b> {text}\n\n"
        f"🔐 <b>Reset Code:</b>\n"
        f"<code>{code}</code>\n\n"
        f"⏰ <b>သက်တမ်း:</b> ၁ နာရီ\n"
        f"📅 <b>ကုန်ဆုံး:</b> {expires_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📋 ဆက်လုပ်ရန် —</b>\n\n"
        f"<b>၁။</b> Website ကို ဖွင့်ပါ\n"
        f"<b>၂။</b> Forgot Password ကို နှိပ်ပါ\n"
        f"<b>၃။</b> <b>Email + Code</b> ထည့်ပါ\n"
        f"<b>၄။</b> Password အသစ် သတ်မှတ်ပါ\n\n"
        f"⚠️ Code ကို — ဘယ်သူ့ကိုမှ မပြနဲ့"
    )

    await loading_msg.edit_text(
        success_text,
        parse_mode="HTML",
    )


# ============================================================================
# ERROR HANDLER
# ============================================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Error တွေ ကို Log ထည့်"""
    logger.error(f"Telegram Bot Error: {context.error}")


# ============================================================================
# MAIN
# ============================================================================
def main():
    """Bot ကို Run"""
    if not _TELEGRAM_AVAILABLE:
        print("❌ python-telegram-bot not installed.")
        print("   Run: pip install python-telegram-bot")
        return

    if not _COIN_SYSTEM_AVAILABLE:
        print("❌ coin_system not available.")
        return

    print("=" * 60)
    print("  🤖 PS AI Recap — Telegram Bot")
    print("=" * 60)
    print(f"  Bot Token: {BOT_TOKEN[:20]}...")
    print(f"  Status: Starting...")
    print("=" * 60)
    print()

    # Application ဖန်တီး
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers ထည့်
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("reset", cmd_reset))
    application.add_handler(CommandHandler("mycode", cmd_mycode))
    application.add_handler(CommandHandler("cancel", cmd_cancel))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Error handler
    application.add_error_handler(error_handler)

    print("✅ Bot is running!")
    print("   Telegram မှာ @PSAI_Recap_Bot ကို သွားပြီး /start နှိပ်ပါ")
    print("   ရပ်ချင်ရင် — Ctrl + C")
    print()

    # Run
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()