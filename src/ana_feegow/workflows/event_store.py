import json
from datetime import datetime
from pathlib import Path

ARQUIVO = Path("data/eventos.json")


def registrar_evento(
    agendamento_id: int,
    tipo: str,
    dados: dict | None = None,
):
    eventos = []

    if ARQUIVO.exists():
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            eventos = json.load(f)

    eventos.append({
        "timestamp": datetime.now().isoformat(),
        "agendamento_id": agendamento_id,
        "tipo": tipo,
        "dados": dados or {},
    })

    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)

    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(eventos, f, indent=2, ensure_ascii=False)


def listar_eventos():
    if not ARQUIVO.exists():
        return []

    with open(ARQUIVO, "r", encoding="utf-8") as f:
        return json.load(f)
