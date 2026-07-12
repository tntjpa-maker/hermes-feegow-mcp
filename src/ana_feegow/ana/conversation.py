import json
from pathlib import Path
from ana_feegow.ana.goal import Goal


BASE = Path(__file__).resolve().parents[3] / "data" / "conversations"
BASE.mkdir(parents=True, exist_ok=True)


class Conversation:

    def __init__(self, telefone=None):
        self.telefone = telefone
        self.state = "inicio"
        self.data = {}
        self.goal = Goal('agendar')

        if telefone:
            self.carregar()

    def update(self, key, value):
        self.data[key] = value
        self.salvar()

    def next(self, state):
        self.state = state
        self.salvar()

    def get(self):
        return {
            "state": self.state,
            "data": self.data
        }


    def salvar(self):
        if not self.telefone:
            return

        BASE.mkdir(parents=True, exist_ok=True)

        arquivo = BASE / f"{self.telefone}.json"

        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(
                self.get(),
                f,
                ensure_ascii=False,
                indent=2,
            )

    def carregar(self):
        arquivo = BASE / f"{self.telefone}.json"

        if not arquivo.exists():
            return

        with open(arquivo) as f:
            dados = json.load(f)

        self.state = dados["state"]
        self.data = dados["data"]
