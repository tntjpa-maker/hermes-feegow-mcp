from datetime import datetime
from pathlib import Path
import json


LOG = Path("logs/events.jsonl")


def emitir_evento(tipo: str, **dados):

    LOG.parent.mkdir(exist_ok=True)

    evento = {
        "timestamp": datetime.utcnow().isoformat(),
        "tipo": tipo,
        "dados": dados,
    }

    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")
