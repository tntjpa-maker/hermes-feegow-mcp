import re
from pathlib import Path

from ana_feegow.conversation.topic_map import TOPICS

BASE = Path(__file__).resolve().parents[3] / "data" / "knowledge" / "BASE_UNICA_ANA.md"


class KnowledgeMarkdown:

    @classmethod
    def load(cls):
        return BASE.read_text(encoding="utf-8")

    @classmethod
    def search(cls, pergunta: str):

        texto = cls.load()
        pergunta = pergunta.lower()

        capitulo = None

        for chave, secao in TOPICS.items():
            if chave in pergunta:
                capitulo = secao
                break

        if capitulo is None:
            return texto

        padrao = rf"^# {re.escape(capitulo)}.*?(?=^# |\Z)"

        m = re.search(
            padrao,
            texto,
            flags=re.S | re.M,
        )

        if m:
            return m.group(0)

        return texto
