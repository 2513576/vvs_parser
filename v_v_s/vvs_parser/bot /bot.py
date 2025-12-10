import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

# Импортируем обработчики из handlers.py
from handlers import (
    start_handler,
    button_router,
    quke_handler,
    kns_handler,
    vernik_handler,
    all_handler
)

# Загружаем переменные окружения (.env)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверяем что токен найден
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в .env! Добавьте BOT_TOKEN=<ваш токен>")

# Настройка логирования (INFO — только важные события)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger("TelegramBot")


def main():
    print("🚀 Запуск Telegram-бота...")
    print("Загружаем обработчики, читаем конфигурацию…")

    # Создаём экземпляр Telegram-приложения
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Регистрируем команды
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("quke", quke_handler))
    app.add_handler(CommandHandler("kns", kns_handler))
    app.add_handler(CommandHandler("vernik", vernik_handler))
    app.add_handler(CommandHandler("all", all_handler))

    # Регистрируем обработчик inline-кнопок
    app.add_handler(CallbackQueryHandler(button_router))

    print("🤖 Бот запущен! Ожидаю команды…\n")

    # Запускаем бота в режиме polling
    app.run_polling()


# Запуск при выполнении файла
if __name__ == "__main__":
    main()
