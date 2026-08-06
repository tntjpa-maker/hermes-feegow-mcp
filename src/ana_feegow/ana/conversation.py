import json
import time
from pathlib import Path


BASE = Path(__file__).resolve().parents[3] / "data" / "conversations"
BASE.mkdir(parents=True, exist_ok=True)


class Conversation:

    def __init__(self, telefone=None):
        self.telefone = telefone
        self.state = "inicio"
        self.data = {}
        # Timestamp (epoch) da ultima vez que esta conversa foi salva.
        # Usado pelo dialog.responder() para detectar conversas paradas no
        # meio do fluxo (ver CONVERSATION_TTL_SEGUNDOS em dialog.py) - sem
        # isso, uma mensagem nova e sem relacao alguma com o contexto (ex:
        # "quero agendar uma consulta" dias depois de uma conversa que
        # ficou pela metade) pode ser silenciosamente interpretada como
        # resposta a pergunta que ficou pendente.
        self.atualizado_em = None

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
            "data": self.data,
            "atualizado_em": self.atualizado_em,
        }


    def salvar(self):
        if not self.telefone:
            return

        BASE.mkdir(parents=True, exist_ok=True)

        self.atualizado_em = time.time()

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
        self.atualizado_em = dados.get("atualizado_em")
