import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
from utils.cache import get_cached, set_cached

# Базовые заголовки — позволяют имитировать обычный браузер
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120 Safari/537.36"
    )
}


# Загружаем HTML-страницу KNS
def fetch_kns_html(url: str) -> Optional[str]:
    print(f"[INFO] KNS → {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[ERROR] KNS загрузка: {e}")
        return None

# Извлекаем цену из meta-тега itemprop="price"
def extract_price(soup: BeautifulSoup) -> Optional[int]:
    tag = soup.find("meta", {"itemprop": "price"})
    if not tag:
        return None

    value = tag.get("content", "").replace(" ", "")
    return int(value) if value.isdigit() else None


# Извлекаем характеристики товара (объём памяти, тип памяти)
def extract_specs(soup: BeautifulSoup) -> Dict[str, str]:
    specs = {}

    # Все строки характеристик: название + значение
    rows = soup.select("div.row.no-gutters.my-2.align-items-end")

    for row in rows:
        key_el = row.find("div", class_="field-ex-name")
        val_el = row.find("div", attrs={"data-id": True})

        if not key_el or not val_el:
            continue

        key = key_el.get_text(strip=True)
        value = val_el.get_text(" ", strip=True)

        specs[key] = value

    return specs


# Нормализуем поле "Объём видеопамяти" (берём первые 2 слова)
def _normalize_memory(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v = v.split(" смотреть")[0]
    parts = v.split()
    return " ".join(parts[:2]) if len(parts) >= 2 else v

# Нормализуем поле "Тип видеопамяти"
def _normalize_memory_type(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v = v.split(" смотреть")[0]
    return v.split()[0]


# Парсим один товар KNS
def parse_kns_product(url: str) -> Dict:
    cache_key = f"KNS::{url}"

    # Проверяем кэш
    cached = get_cached(cache_key)
    if cached:
        return cached

    # Загружаем HTML
    html = fetch_kns_html(url)
    if not html:
        result = {
            "site": "KNS",
            "name": None,
            "price": None,
            "memory": None,
            "memory_type": None,
            "url": url,
            "error": "HTML not loaded",
        }
        set_cached(cache_key, result)
        return result

    soup = BeautifulSoup(html, "lxml")

    # Название товара
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else None

    # Цена
    price = extract_price(soup)

    # Характеристики
    specs = extract_specs(soup)
    raw_memory = specs.get("Объем видеопамяти")
    raw_memory_type = specs.get("Тип видеопамяти")

    memory = _normalize_memory(raw_memory)
    memory_type = _normalize_memory_type(raw_memory_type)

    result = {
        "site": "KNS",
        "name": title,
        "price": price,
        "memory": memory,
        "memory_type": memory_type,
        "url": url
    }

    # Сохраняем в кэш
    set_cached(cache_key, result)
    return result

# Парсим список товаров KNS
def parse_kns_list(urls: List[str]) -> List[Dict]:
    return [parse_kns_product(url) for url in urls]
