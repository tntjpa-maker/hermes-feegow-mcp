from pathlib import Path

from ana_feegow.ana.decision import decidir


BASE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "knowledge"
    / "BASE_UNICA_ANA.md"
)


class KnowledgeResponder:

    @classmethod
    def answer(cls, pergunta: str):

        if not BASE.exists():
            return None

        contexto = BASE.read_text(encoding="utf-8")

        prompt = f"""
Você é a ANA, secretária da Clínica Magnólia.

Utilize EXCLUSIVAMENTE a Base de Conhecimento abaixo.

Se a resposta não estiver nela, responda apenas:

NÃO_ENCONTRADO

--------------------

{contexto}

--------------------

Pergunta da paciente:

{pergunta}
"""

        resposta = decidir(prompt)

        if isinstance(resposta, dict):
            resposta = resposta.get("resposta") or resposta.get("response")

        if not resposta:
            return None

        resposta = str(resposta).strip()

        if "NÃO_ENCONTRADO" in resposta.upper():
            return None

        return resposta
