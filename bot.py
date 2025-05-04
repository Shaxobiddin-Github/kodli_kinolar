import logging
import json
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Faylga saqlanadigan ma'lumotlar
VIDEO_DATA_FILE = "video_map.json"

# Botni ishga tushirganingizda eski videolarni yuklash
if os.path.exists(VIDEO_DATA_FILE):
    with open(VIDEO_DATA_FILE, "r", encoding="utf-8") as f:
        hashtag_to_video = json.load(f)
        # Fayldan o‘qilganda tuple emas, faqat string bo‘ladi → to‘g‘rilash:
        hashtag_to_video = {k: tuple(v) for k, v in hashtag_to_video.items()}
else:
    hashtag_to_video = {}

# vaqtincha hashtaglarni saqlaymiz: {user_id: "#1234"}
user_last_hashtag = {}

TOKEN = '7560772282:AAHrigcEVe_zjKjwD_lkjFyFYtIqqLPaoHQ'  # bot token
application = Application.builder().token(TOKEN).build()

# Kanalga kelgan xabarlar
async def channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if not message:
        return

    user_id = message.chat_id  # kanalning chat_id
    text = message.text
    video = message.video

    if text and text.startswith("#"):
        user_last_hashtag[user_id] = text.strip()
        logger.info(f"Hashtag xabari qabul qilindi: {text.strip()}")

    elif video:
        hashtag = user_last_hashtag.get(user_id)
        if not hashtag:
            logger.info("Video keldi, lekin hashtag topilmadi.")
            return

        clean_hashtag = hashtag.lstrip("#")  # "#1234" → "1234"
        hashtag_to_video[clean_hashtag] = (message.chat_id, message.message_id)
        logger.info(f"Video va hashtag topildi: hashtag={clean_hashtag}, video_id={message.message_id}")

        # 🎯 Video yangi qo'shilganda faylga saqlaymiz
        with open(VIDEO_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(hashtag_to_video, f)

    else:
        logger.info("Xabar hashtag yoki video emas.")

# Botga shaxsiy yozilgan xabarlar
async def private_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip()
    user_chat_id = message.chat_id

    logger.info(f"Foydalanuvchi yubordi: {text}")

    if text in hashtag_to_video:
        video_chat_id, video_msg_id = hashtag_to_video[text]
        # Video yuborish
        await context.bot.copy_message(
            chat_id=user_chat_id,
            from_chat_id=video_chat_id,
            message_id=video_msg_id
        )
        # Kanal nomi bilan video pastiga qo'shish
        await context.bot.send_message(
            chat_id=user_chat_id,
            text=f"Kanal: [Kodli Kinolar](https://t.me/kodli_kinolar_1234)",
            parse_mode="Markdown"
        )
        logger.info(f"{text} uchun video yuborildi.")
    else:
        await message.reply_text("Kechirasiz, bu kod uchun video topilmadi.")
        logger.info("Video topilmadi.")

# Handlerlar
application.add_handler(MessageHandler(filters.ChatType.CHANNEL, channel_handler))
application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT, private_handler))

# Botni ishga tushiramiz
application.run_polling()
