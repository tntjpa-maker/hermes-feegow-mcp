import json
from pathlib import Path

ARQUIVO = Path("data/reservas.json")


def _carregar():
    if not ARQUIVO.exists():
        return []

    with open(ARQUIVO, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_reserva(reserva: dict):
    reservas = _carregar()
    reservas.append(reserva)

    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)

    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(reservas, f, indent=2, ensure_ascii=False)


def listar_reservas():
    return _carregar()
