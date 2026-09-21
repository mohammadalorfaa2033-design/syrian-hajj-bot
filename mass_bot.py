import asyncio
import logging

from telegram import Update
from telegram.error import Forbidden, BadRequest
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import ADMIN_IDS, BOT_TOKEN
import storage

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# فاصل زمني بسيط بين كل رسالة وأخرى (بالثانية) لتفادي حدود تيليجرام
BROADCAST_DELAY = 0.05

NATIONAL_ID, FULL_NAME, PHONE = range(3)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    storage.add_subscriber(user.id, user.username, user.first_name)

    if storage.is_profile_complete(user.id):
        await update.message.reply_text("أنت مسجل مسبقًا وبياناتك مكتملة.")
        return ConversationHandler.END

    await update.message.reply_text(
        "أهلاً بك! لإتمام تسجيلك بدنا منك بعض المعلومات.\n"
        "أرسل رجاءً رقمك الوطني:"
    )
    return NATIONAL_ID


async def receive_national_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or not (5 <= len(text) <= 15):
        await update.message.reply_text(
            "الرقم الوطني غير صالح، لازم يتكون من أرقام فقط. أعد إرساله:"
        )
        return NATIONAL_ID

    context.user_data["national_id"] = text
    await update.message.reply_text("تمام، الآن أرسل اسمك الكامل (ثلاثي على الأقل):")
    return FULL_NAME


async def receive_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if len(text.split()) < 2:
        await update.message.reply_text(
            "الرجاء إرسال الاسم الكامل (اسم ثنائي على الأقل):"
        )
        return FULL_NAME

    context.user_data["full_name"] = text
    await update.message.reply_text("وأخيرًا، أرسل رقم هاتفك (مع رمز الدولة إن أمكن):")
    return PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(" ", "")
    digits = text.lstrip("+")
    if not digits.isdigit() or not (7 <= len(digits) <= 15):
        await update.message.reply_text("رقم الهاتف غير صالح. أعد إرساله:")
        return PHONE

    user = update.effective_user
    storage.update_profile(
        chat_id=user.id,
        national_id=context.user_data["national_id"],
        full_name=context.user_data["full_name"],
        phone_number=text,
    )
    await update.message.reply_text("تم تسجيل بياناتك بنجاح، شكرًا لك.")
    logger.info("Profile completed for subscriber: %s (%s)", user.id, user.username)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("تم إلغاء عملية التسجيل. أرسل /start للبدء من جديد.")
    return ConversationHandler.END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    storage.remove_subscriber(user.id)
    await update.message.reply_text("تم إلغاء اشتراكك، لن تصلك رسائل بعد الآن.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("هذا الأمر مخصص للأدمن فقط.")
        return

    count = storage.count_subscribers()
    await update.message.reply_text(f"عدد المشتركين الحاليين: {count}")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("هذا الأمر مخصص للأدمن فقط.")
        return

    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("استخدم الأمر هيك: /broadcast نص الرسالة هون")
        return

    subscriber_ids = storage.get_all_subscriber_ids()
    if not subscriber_ids:
        await update.message.reply_text("لا يوجد مشتركين بعد.")
        return

    status_msg = await update.message.reply_text(
        f"جاري الإرسال إلى {len(subscriber_ids)} مشترك..."
    )

    sent = 0
    failed = 0
    for chat_id in subscriber_ids:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            sent += 1
        except Forbidden:
            # المستخدم حظر البوت أو حذف حسابه -> نشيله من القائمة
            storage.remove_subscriber(chat_id)
            failed += 1
        except BadRequest as e:
            logger.warning("Failed to send to %s: %s", chat_id, e)
            failed += 1
        await asyncio.sleep(BROADCAST_DELAY)

    await status_msg.edit_text(
        f"تم الإرسال بنجاح إلى {sent} مشترك.\nفشل الإرسال إلى {failed} مشترك (تمت إزالتهم إذا حظروا البوت)."
    )


def main():
    storage.init_db()

    app: Application = ApplicationBuilder().token(BOT_TOKEN).build()

    registration_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NATIONAL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_national_id)],
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_full_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(registration_conv)
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
