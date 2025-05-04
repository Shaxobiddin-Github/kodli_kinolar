import logging
import json
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from github import Github
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GitHub sozlamalari
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN muhit o'zgaruvchisi topilmadi!")

REPO_NAME = "Shaxobiddin-Github/kodli_kinolar"  # Sizning repozitoriy nomingiz
FILE_PATH = "video_map.json"

# GitHub'dan faylni o'qish
def load_video_data():
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        file_content = repo.get_contents(FILE_PATH)
        data = json.loads(base64.b64decode(file_content.content).decode("utf-8"))
        return {k: tuple(v) for k, v in data.items()}
    except Exception as e:
        logger.info(f"GitHub'dan fayl o'qishda xato: {e}")
        return {}

# GitHub'ga faylni saqlash
def save_video_data(data):
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        # Fayl mavjud bo'lsa, uni yangilaymiz
        try:
            file_content = repo.get_contents(FILE_PATH)
            repo.update_file(
                FILE_PATH,
                "Update video_map.json",
                json.dumps(data, ensure_ascii=False),
                file_content.sha
            )
        # Fayl mavjud bo'lmasa, yangisini yaratamiz
        except:
            repo.create_file(
                FILE_PATH,
                "Create video_map.json",
                json.dumps(data, ensure_ascii=False)
            )
    except Exception as e:
        logger.error(f"GitHub'ga fayl saqlashda xato: {e}")

hashtag_to_video = load_video_data()

# Vaqtincha hashtaglarni saqlaymiz
user_last_hashtag = {}

# TOKEN ni muhit o'zgaruvchisidan olish
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN muhit o'zgaruvchisi topilmadi!")

application = Application.builder().token(TOKEN).build()

# Kanalga kelgan xabarlar
async def channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if not message:
        return

    user_id = message.chat_id
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

        clean_hashtag = hashtag.lstrip("#")
        hashtag_to_video[clean_hashtag] = (message.chat_id, message.message_id)
        logger.info(f"Video va hashtag topildi: hashtag={clean_hashtag}, video_id={message.message_id}")

        # GitHub'ga saqlash
        save_video_data(hashtag_to_video)

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