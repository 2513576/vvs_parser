from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import re
import asyncio
from utils.cache import get_cached, set_cached

HEADLESS = False  # режим отображения браузера Playwright

def extract_memory_from_title(title: str) -> Optional[str]:
    """Извлекает объём памяти (например 128GB) из заголовка товара."""
    m = re.search(r"(\d+\s*(?:GB|ГБ|Gb|гб))", title, re.IGNORECASE)
    return m.group(1) if m else None


def extract_color_from_title(title: str) -> Optional[str]:
    """Определяет цвет устройства по известным ключевым словам."""
    colors = [
        "Black", "White", "Blue", "Pink", "Green", "Yellow",
        "Silver", "Space Gray", "Natural", "Titanium",
        "Черный", "Чёрный", "Белый", "Синий", "Ultramarine",
        "Deep Blue",
    ]
    low = title.lower()
    for c in colors:
        if c.lower() in low:
            return c
    return None


def extract_price_from_soup(soup: BeautifulSoup) -> Optional[int]:
    """Ищет цену на странице (через data-price или span.val)."""
    btn = soup.find("a", attrs={"data-price": True})
    if btn and btn.get("data-price"):
        raw = btn["data-price"].strip().replace(" ", "")
        return int(raw) if raw.isdigit() else None

    span = soup.find("span", class_="val")
    if span:
        raw = span.get_text(strip=True).replace(" ", "")
        return int(raw) if raw.isdigit() else None

    return None


# Получение HTML через PLAYWRIGHT
def fetch_quke_html(url: str) -> Optional[str]:
    """Открывает страницу через виртуальный браузер Playwright и возвращает HTML."""
    print(f"[INFO] Открываем браузер Playwright → {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
        )

        try:
            page.goto(url, wait_until="networkidle", timeout=60000)

            # Пытаемся дождаться основной информации товара
            try:
                page.wait_for_selector("h1, span.val", timeout=30000)
            except PlaywrightTimeoutError:
                print("[WARN] Не дождались h1/span.val, читаем HTML как есть")

            html = page.content()
            return html

        except Exception as e:
            print(f"[Playwright ERROR] {e}")
            return None

        finally:
            browser.close()


# Основной парсер товара
def parse_quke_product(url: str) -> Dict:
    """Парсит один товар Quke: заголовок, цену, память, цвет."""

    cache_key = f"QUKE::{url}"  # ключ кеша
    cached = get_cached(cache_key)
    if cached:
        return cached  # возвращаем данные из кеша

    html = fetch_quke_html(url)
    if not html:
        result = {
            "site": "Quke",
            "name": None,
            "price": None,
            "memory": None,
            "color": None,
            "url": url,
            "error": "HTML not loaded",
        }
        set_cached(cache_key, result)
        return result

    soup = BeautifulSoup(html, "html.parser")

    # Название товара
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else None

    # Цена + характеристики из заголовка
    price = extract_price_from_soup(soup)
    memory = extract_memory_from_title(title or "")
    color = extract_color_from_title(title or "")

    result = {
        "site": "Quke",
        "name": title,
        "price": price,
        "memory": memory,
        "color": color,
        "url": url,
    }

    set_cached(cache_key, result)  # сохраняем в кеш
    return result


# Синхронный список товаров
def parse_quke_list(urls: List[str]) -> List[Dict]:
    """Парсит список товаров синхронно (по одному)."""
    return [parse_quke_product(url) for url in urls]


# Асинхронная обертка для Telegram
async def parse_quke_product_async(url: str):
    """Асинхронная версия парсинга одного товара — вынос в отдельный поток."""
    return await asyncio.to_thread(parse_quke_product, url)


async def parse_quke_list_async(urls: List[str]):
    """Асинхронная версия парсинга списка товаров Quke."""
    results = []
    for url in urls:
        item = await parse_quke_product_async(url)
        results.append(item)
    return results

