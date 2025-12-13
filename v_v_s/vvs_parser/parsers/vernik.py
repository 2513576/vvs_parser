import requests
from bs4 import BeautifulSoup
import re
import json
from utils.cache import get_cached, set_cached


class VernikSimpleParser:
    def __init__(self):
        # Заголовки для запроса — имитация браузера
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

    def parse_vernik(self, url: str, product_name: str) -> dict:
        """Основной метод: загружает страницу, пытается извлечь цену и метаданные."""

        cache_key = f"VERNIK::{url}::{product_name}"   # уникальный ключ кеша
        cached = get_cached(cache_key)
        if cached:
            return cached  # если в кеше — сразу возвращаем

        print(f"\n VERNIK → {product_name}")

        html = self._load_page(url)
        if not html:
            result = self._error_dict(product_name, url, "HTML not loaded")
            set_cached(cache_key, result)
            return result

        # Пробуем разные способы найти цену — по цепочке OR
        price = (
            self._method_selectors(html, product_name)
            or self._method_json_ld(html, product_name)
            or self._method_meta(html, product_name)
            or self._method_text(html, product_name)
            or self._method_numbers(html, product_name)
        )

        if not price:
            result = self._error_dict(product_name, url, "Price not found")
            set_cached(cache_key, result)
            return result

        # Определяем цвет и объём памяти из названия
        color = self._guess_color(product_name)
        memory = self._guess_memory(product_name)

        result = {
            "site": "Vernik",
            "name": product_name,
            "price": price,
            "memory": memory,
            "color": color,
            "url": url
        }

        set_cached(cache_key, result)  # сохраняем результат в кеш
        return result

    # Загрузка HTML
    def _load_page(self, url):
        """Загружает HTML страницы (requests)."""
        try:
            print(f"→ Загружаем страницу: {url}")
            rsp = requests.get(url, headers=self.headers, timeout=15)
            if rsp.status_code != 200:
                print(f" Ошибка HTTP {rsp.status_code}")
                return None
            return rsp.text
        except Exception as e:
            print(f" Ошибка загрузки: {e}")
            return None

    # Формирование объекта ошибки
    def _error_dict(self, name, url, err):
        """Возвращает структурированный объект ошибки парсинга."""
        return {
            "site": "Vernik",
            "name": name,
            "price": None,
            "memory": None,
            "color": None,
            "url": url,
            "error": err,
        }

    # Метод 1 — поиск цены по CSS селекторам
    def _method_selectors(self, html, product_name):
        """Ищет цену по распространённым CSS-классам."""
        print(" Метод 1: CSS селекторы")
        soup = BeautifulSoup(html, "html.parser")

        selectors = [
            ".product-price", ".price", ".current-price",
            ".product-card-price", ".product__price", ".product-item-price",
            '[itemprop="price"]', ".price__value",
            ".woocommerce-Price-amount", ".amount",
            ".value", ".cost", ".cena",
        ]

        for css in selectors:
            try:
                elements = soup.select(css)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    price = self._extract_price(text)
                    if price:
                        print(f" По селектору '{css}' → {price}")
                        return price
            except:
                continue
        return None

    # Метод 2 — JSON-LD
    def _method_json_ld(self, html, product_name):
        """Ищет цену внутри JSON-LD блока (структурированные данные)."""
        print(" Метод 2: JSON-LD")
        matches = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            html, re.DOTALL
        )

        for block in matches:
            try:
                data = json.loads(block)

                if isinstance(data, dict) and data.get("@type") == "Product":

                    offers = data.get("offers")

                    # Вариант 1: один объект offers
                    if isinstance(offers, dict) and "price" in offers:
                        return self._extract_price(offers["price"])

                    # Вариант 2: массив offers
                    if isinstance(offers, list):
                        prices = [
                            self._extract_price(offer.get("price"))
                            for offer in offers if "price" in offer
                        ]
                        prices = [p for p in prices if p]
                        if prices:
                            return max(prices)

                    # Вариант 3: price на верхнем уровне JSON-LD
                    if "price" in data:
                        return self._extract_price(data["price"])

            except Exception:
                continue

        return None

    # Метод 3 — META-теги
    def _method_meta(self, html, product_name):
        """Ищет цену внутри meta-тегов страницы."""
        print(" Метод 3: мета-теги")
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all("meta"):
            attrs = (tag.get("property", "") + tag.get("name", "")).lower()

            if "price" in attrs:
                price = self._extract_price(tag.get("content", ""))
                if price:
                    return price

            if tag.get("itemprop") == "price":
                price = self._extract_price(tag.get("content", ""))
                if price:
                    return price

        return None

    # Метод 4 — поиск цены в тексте
    def _method_text(self, html, product_name):
        """Перебирает текст страницы в поиске строки со словом 'руб', '₽' или 'цена'."""
        print(" Метод 4: текст страницы")
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")

        lines = [
            ln.strip() for ln in text.split("\n")
            if "руб" in ln.lower() or "₽" in ln or "цена" in ln.lower()
        ]

        for ln in lines:
            price = self._extract_price(ln)
            if price:
                return price

        return None

    # Метод 5 — поиск чисел большого диапазона
    def _method_numbers(self, html, product_name):
        """Ищет числа в диапазоне 50 000–500 000, если ничего другого не найдено."""
        print(" Метод 5: поиск чисел")
        cleaned = re.sub(r"<[^>]+>", " ", html)
        nums = re.findall(r"\b\d{4,7}\b", cleaned)

        nums = [int(n) for n in nums if 50_000 <= int(n) <= 500_000]

        if nums:
            return max(nums)

        return None

    # Вспомогательные методы
    def _extract_price(self, text):
        """Выделяет число из строки (убирает пробелы/символы и валидирует диапазон)."""
        if not text:
            return None

        cleaned = (
            str(text)
            .replace(" ", "")
            .replace(",", "")
            .replace("\xa0", "")
            .replace("\u2009", "")
        )

        cleaned = re.sub(r"[^\d]", "", cleaned)

        if cleaned.isdigit():
            price = int(cleaned)
            return price if 50_000 <= price <= 500_000 else None

        return None

    def _guess_color(self, name):
        """Определяет цвет по ключевым словам в названии."""
        name_l = name.lower()
        colors = ["black", "white", "blue", "silver", "gold", "green", "red", "gray"]
        for c in colors:
            if c in name_l:
                return c.capitalize()
        return None

    def _guess_memory(self, name):
        """Извлекает объём памяти вида '128gb'."""
        m = re.search(r"(\d+gb)", name.lower())
        return m.group(1).upper() if m else None


def parse_vernik(url: str, name: str) -> dict:
    """Глобальная функция-проходник, которую вызывает бот."""
    parser = VernikSimpleParser()
    return parser.parse_vernik(url, name)

