import asyncio
import logging
import sys
from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from config import BOT_TOKEN, ADMIN_CHAT_ID, PROXY_URL
from database import Database

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
Q1, Q2 = range(2)

# Тексты сообщений
WELCOME_TEXT = (
    "!ВАЖНО! Для новичков мы бесплатно предоставляем обучение по УБТ трафику \n"
    "и монтажу роликов которое проходит вместе с наставником, с которым спустя \n"
    "неделю у вас уже будут первые результаты.\n\n"
    "Для начала необходимо заполнить небольшую анкету"
)

Q1_TEXT = (
    "Этап 1/2\n\n"
    "Выкладывали видео / баннерную рекламу в TikTok, YouTube, Instagram?\n\n"
    "Если есть такие каналы - предоставьте ссылки в сообщении\n\n"
    "Отправьте ответ текстом:"
)

Q2_TEXT = (
    "Этап 2/2\n\n"
    "Сколько вы готовы уделять времени работе?\n\n"
    "Какой ваш ожидаемый доход в месяц?\n\n"
    "Откуда узнали о партнерке RodnoyVPN?\n\n"
    "Отправьте ответ текстом:"
)

SUCCESS_TEXT = (
    "Отлично, мы приняли вашу анкету. Скоро с вами свяжется наш менеджер @RodnoyVpnManager"
)

ALREADY_APPLIED_TEXT = (
    "Вы уже отправляли анкету. Ожидайте, скоро с вами свяжется наш менеджер @RodnoyVpnManager"
)

CANCEL_TEXT = "Анкета отменена. Чтобы начать заново, нажмите /start"

NOT_TEXT_REPLY = "Пожалуйста, отправьте ответ текстом."

DURING_FORM_TEXT = "Ответьте текстом."

HELP_TEXT = "Если у вас возникла проблема, пишите @RodnoyVPNManager"

# Инициализация БД
db = Database()


async def start(update: Update, context: Any) -> None:
    user_id = update.effective_user.id

    # Проверка на дубликат
    if db.is_already_applied(user_id):
        await update.message.reply_text(ALREADY_APPLIED_TEXT)
        return

    keyboard = [
        [InlineKeyboardButton("Заполнить анкету", callback_data="fill_form")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(WELCOME_TEXT, reply_markup=reply_markup)


async def help_command(update: Update, context: Any) -> None:
    await update.message.reply_text(HELP_TEXT)


async def fill_form_callback(update: Update, context: Any) -> int:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # Проверка на дубликат
    if db.is_already_applied(user_id):
        await query.edit_message_text(ALREADY_APPLIED_TEXT)
        return ConversationHandler.END

    # Удаляем приветственное сообщение
    try:
        await query.delete_message()
    except Exception as e:
        logger.warning(f"Не удалось удалить приветствие: {e}")

    # Отправляем вопрос 1
    msg = await context.bot.send_message(
        chat_id=query.from_user.id,
        text=Q1_TEXT,
    )
    context.user_data["q1_message_id"] = msg.message_id
    return Q1


async def handle_q1(update: Update, context: Any) -> int:
    user_data = context.user_data
    user_data["answer_1"] = update.message.text

    # Удаляем ответ пользователя
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить ответ на Q1: {e}")

    # Удаляем вопрос 1 по сохранённому message_id
    q1_msg_id = user_data.get("q1_message_id")
    if q1_msg_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=q1_msg_id,
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить Q1 сообщение: {e}")

    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_q1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = await update.message.reply_text(Q2_TEXT, reply_markup=reply_markup)
    user_data["q2_message_id"] = msg.message_id
    return Q2


async def handle_q2(update: Update, context: Any) -> int:
    user_data = context.user_data
    user_data["answer_2"] = update.message.text

    # Удаляем ответ пользователя
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить ответ на Q2: {e}")

    # Удаляем вопрос 2 по сохранённому message_id
    q2_msg_id = user_data.get("q2_message_id")
    if q2_msg_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=q2_msg_id,
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить Q2 сообщение: {e}")

    user = update.effective_user
    user_id = user.id
    username = user.username
    full_name = user.full_name
    answer_1 = user_data.get("answer_1", "")
    answer_2 = user_data.get("answer_2", "")

    # Проверка на дубликат перед сохранением
    if db.is_already_applied(user_id):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=ALREADY_APPLIED_TEXT,
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Сохраняем в БД
    try:
        db.save_application(
            user_id=user_id,
            username=username,
            full_name=full_name,
            answer_1=answer_1,
            answer_2=answer_2,
        )
    except Exception as e:
        logger.error(f"Ошибка сохранения заявки: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка. Попробуйте позже.",
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Отправляем уведомление администратору
    admin_message = (
        f"Новая анкета\n\n"
        f"Пользователь: {full_name} | @{username} | id: {user_id}\n\n"
        f"Этап 1/2:\n"
        f"{answer_1}\n\n"
        f"Этап 2/2:\n"
        f"{answer_2}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления администратору: {e}")

    # Отправляем подтверждение пользователю
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=SUCCESS_TEXT,
    )

    # Очищаем user_data
    context.user_data.clear()
    return ConversationHandler.END


async def back_to_q1_callback(update: Update, context: Any) -> int:
    query = update.callback_query
    await query.answer()

    user_data = context.user_data

    # Удаляем сообщение с Q2
    q2_msg_id = user_data.get("q2_message_id")
    try:
        await query.delete_message()
    except Exception as e:
        logger.warning(f"Не удалось удалить Q2 при возврате: {e}")

    # Отправляем новый вопрос 1
    msg = await context.bot.send_message(
        chat_id=query.from_user.id,
        text=Q1_TEXT,
    )
    user_data["q1_message_id"] = msg.message_id
    # Удаляем q2_message_id из user_data (он больше не актуален)
    user_data.pop("q2_message_id", None)
    return Q1


async def cancel(update: Update, context: Any) -> int:
    await update.message.reply_text(CANCEL_TEXT)
    context.user_data.clear()
    return ConversationHandler.END


async def ignore_start(update: Update, context: Any) -> int:
    """Игнорируем /start во время опроса — ничего не отвечаем."""
    return context.user_data.get("current_state", Q1)


async def handle_non_text(update: Update, context: Any) -> None:
    """Обработка сообщений, которые не являются текстом во время опроса."""
    await update.message.reply_text(NOT_TEXT_REPLY)


def main() -> None:
    builder = Application.builder().token(BOT_TOKEN)
    
    if PROXY_URL:
        logger.info(f"Используем прокси: {PROXY_URL}")
        builder.proxy_url(PROXY_URL)
    
    application = builder.build()

    # ConversationHandler для опроса
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(fill_form_callback, pattern="^fill_form$"),
        ],
        states={
            Q1: [
                CommandHandler("start", ignore_start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q1),
                MessageHandler(~filters.TEXT & ~filters.COMMAND, handle_non_text),
            ],
            Q2: [
                CommandHandler("start", ignore_start),
                CallbackQueryHandler(back_to_q1_callback, pattern="^back_to_q1$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q2),
                MessageHandler(~filters.TEXT & ~filters.COMMAND, handle_non_text),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", ignore_start),
        ],
    )

    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)

    # Обработчик не-текстовых сообщений вне ConversationHandler
    application.add_handler(
        MessageHandler(~filters.TEXT & ~filters.COMMAND, handle_non_text)
    )

    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # На Python 3.14+ необходимо явно создать event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main()
