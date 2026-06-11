import json
import os

COUNTER_PATH = os.path.join(os.path.dirname(__file__), "data", "counter.json")


def _load() -> dict:
    if os.path.exists(COUNTER_PATH):
        with open(COUNTER_PATH) as f:
            return json.load(f)
    return {}


def _save(data: dict):
    os.makedirs(os.path.dirname(COUNTER_PATH), exist_ok=True)
    with open(COUNTER_PATH, "w") as f:
        json.dump(data, f)


def get_next_number(tipo: str = "IF") -> int:
    """tipo: 'IF' para Informe de Ensayo, 'IS' para Informe de Servicio."""
    key = f"ultimo_{tipo}"
    return _load().get(key, 0) + 1


def save_number(n: int, tipo: str = "IF"):
    data = _load()
    data[f"ultimo_{tipo}"] = n
    _save(data)
