import json
import os
from typing import Any

DATA_DIR = "."


def _path(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


def load_json(filename: str, default: Any = None) -> Any:
    path = _path(filename)
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


def save_json(filename: str, data: Any) -> None:
    path = _path(filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
