import json
from pathlib import Path

#Загружает products.json, который хранит список ссылок для парсинга
def load_products():
    ROOT = Path(__file__).resolve().parent.parent  # корень проекта

    config_path = ROOT / "config" / "products.json"

    # Проверка существования файла
    if not config_path.exists():
        raise FileNotFoundError(
            f"Файл не найден: {config_path}\n"
            "Убедись, что products.json находится в папке config/"
        )

    # Загружаем JSON
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)

