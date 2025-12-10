import json
import time
from pathlib import Path

# Определяем корневую директорию проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Папка для кеша
CACHE_DIR = BASE_DIR / "cache"

# Файл кеша
CACHE_FILE = CACHE_DIR / "cache.json"

# Создаём папку cache, если её нет
CACHE_DIR.mkdir(exist_ok=True)


def load_cache() -> dict:
    """Загрузить cache.json (или вернуть пустой словарь, если файла нет)."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}  # если файл повреждён
    return {}


def save_cache(data: dict) -> None:
    """Сохранить словарь в cache.json."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_cached(url: str, lifetime: int = 600):
    """
    Вернуть кешированный объект,
    если он существует и ещё не устарел.
    lifetime — время жизни кеша в секундах (по умолчанию 10 минут).
    """
    cache = load_cache()
    item = cache.get(url)

    # Нет записи → нет кеша
    if not item:
        return None

    ts = item.get("timestamp")
    if not ts:
        return None

    # Проверяем, не устарел ли кеш
    if time.time() - ts > lifetime:
        return None

    return item.get("data")


def set_cached(url: str, data: dict):
    """Записать значение в кеш (с timestamp)."""
    cache = load_cache()

    cache[url] = {
        "timestamp": time.time(),  # время записи в кеш
        "data": data               # сами данные
    }

    save_cache(cache)
