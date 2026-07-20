import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ana_feegow.ana.dialog import responder

TELEFONE = "21999999999"
historico = []


def conversar(msg):
    print("=" * 70)
    print("USUÁRIO:", msg)

    resp = responder(
        telefone=TELEFONE,
        mensagem=msg,
        historico_recente=historico,
    )

    print("\nANA:\n")
    print(resp)
    print()

    historico.append({"role": "user", "content": msg})
    historico.append({"role": "assistant", "content": resp})


conversar("Quero remarcar minha consulta")
conversar("1")
