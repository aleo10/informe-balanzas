from database import get_config, update_config


def get_next_number(tipo: str = "IF") -> int:
    """tipo: 'IF' o 'IS'."""
    key = f"ultimo_{tipo}"
    cfg = get_config()
    return int(cfg.get(key, 0)) + 1


def save_number(n: int, tipo: str = "IF"):
    update_config(f"ultimo_{tipo}", str(n))
