from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import ContextTypes

from utils.products import load_products
from parsers.quke import parse_quke_list_async
from parsers.kns import parse_kns_list
from parsers.vernik import parse_vernik


# Главное меню бота — Inline-кнопки для выбора магазина
def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("🔵 QUKE", callback_data="quke"),
            InlineKeyboardButton("🟣 KNS", callback_data="kns"),
        ],
        [
            InlineKeyboardButton("🟡 VERNIK", callback_data="vernik"),
            InlineKeyboardButton("🌐 ВСЁ", callback_data="all"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# /start — первое сообщение пользователю
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Привет! 👋\n\n"
        "Этот бот умеет парсить цены с сайтов:\n"
        "• Quke.ru (Playwright)\n"
        "• KNS.ru (Requests + BS4)\n"
        "• Vernik.me\n\n"
        "Выбери магазин ниже:"
    )

    await update.message.reply_text(text, reply_markup=main_menu())


# Роутер для inline-кнопок
# В зависимости от callback_data вызывает нужный обработчик
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Telegram требует подтверждать callback
    action = query.data

    if action == "quke":
        await quke_handler(update, context, is_callback=True)
    elif action == "kns":
        await kns_handler(update, context, is_callback=True)
    elif action == "vernik":
        await vernik_handler(update, context, is_callback=True)
    elif action == "all":
        await all_handler(update, context, is_callback=True)


# Обработчик QUKE (асинхронный)
async def quke_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    # Загружаем ссылки из products.json
    products = load_products()
    urls = [p["url"] for p in products["quke"]]

    # Выбираем способ отправки (из callback или из чата)
    send = (
        update.callback_query.message.reply_text
        if is_callback else update.message.reply_text
    )

    await send("⌛ Парсим Quke…")

    # Асинхронный список парсеров
    items = await parse_quke_list_async(urls)

    # Фильтруем только те, у которых есть цена
    items = [x for x in items if x.get("price")]

    if not items:
        await send("❌ Не удалось получить данные с Quke.")
        return

    # Красивый вывод каждого товара
    for item in items:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Открыть товар", url=item["url"])]]
        )

        text = (
            f"📱 *{item['name']}*\n"
            f"💰 Цена: *{item['price']} ₽*"
        )

        await send(text, parse_mode="Markdown", reply_markup=keyboard)

    # Возвращаем меню выбора магазина
    await send("Готово! Выбери следующий магазин:", reply_markup=main_menu())


# Обработчик KNS
async def kns_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    products = load_products()
    urls = [p["url"] for p in products["kns"]]

    send = (
        update.callback_query.message.reply_text
        if is_callback else update.message.reply_text
    )

    await send("⌛ Парсим KNS…")

    items = parse_kns_list(urls)
    items = [x for x in items if x.get("price")]

    if not items:
        await send("❌ KNS не вернул данные.")
        return

    for item in items:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Открыть товар", url=item["url"])]]
        )

        text = (
            f"🟣 *{item['name']}*\n"
            f"💰 Цена: *{item['price']} ₽*"
        )

        await send(text, parse_mode="Markdown", reply_markup=keyboard)

    await send("Выбери следующий магазин:", reply_markup=main_menu())


# Обработчик VERNIK
async def vernik_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    products = load_products()

    send = (
        update.callback_query.message.reply_text
        if is_callback else update.message.reply_text
    )

    await send("⌛ Парсим Vernik…")

    # Каждый товар парсится отдельно
    items = [parse_vernik(p["url"], p["name"]) for p in products["vernik"]]
    items = [x for x in items if x.get("price")]

    if not items:
        await send("❌ Vernik не вернул данные.")
        return

    for item in items:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Открыть товар", url=item["url"])]]
        )

        text = (
            f"🟡 *{item['name']}*\n"
            f"💰 Цена: *{item['price']} ₽*"
        )

        await send(text, parse_mode="Markdown", reply_markup=keyboard)

    await send("Выбери следующий магазин:", reply_markup=main_menu())


# Обработчик: собрать данные со всех сайтов
async def all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    send = (
        update.callback_query.message.reply_text
        if is_callback else update.message.reply_text
    )

    await send("⌛ Собираю данные со всех сайтов…")

    products = load_products()

    # Получаем товары от всех парсеров
    quke_items = await parse_quke_list_async([p["url"] for p in products["quke"]])
    kns_items = parse_kns_list([p["url"] for p in products["kns"]])
    vernik_items = [parse_vernik(p["url"], p["name"]) for p in products["vernik"]]

    # Оставляем только товары с ценой
    all_items = [
        *[x for x in quke_items if x.get("price")],
        *[x for x in kns_items if x.get("price")],
        *[x for x in vernik_items if x.get("price")]
    ]

    if not all_items:
        await send("❌ Не удалось получить данные ни с одного сайта.")
        return

    # Отправляем товары по одному
    for item in all_items:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Открыть товар", url=item["url"])]]
        )

        text = (
            f"🛒 *{item['site']}*\n"
            f"{item['name']}\n"
            f"💰 *{item['price']} ₽*"
        )

        await send(text, parse_mode="Markdown", reply_markup=keyboard)

    await send("Готово! Выбери магазин:", reply_markup=main_menu())
