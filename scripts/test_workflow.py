#!/usr/bin/env python3

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ana_feegow.ana.dialog import responder

TELEFONE = "21999999999"

conv_file = ROOT / "data" / "conversations" / f"{TELEFONE}.json"
if conv_file.exists():
    conv_file.unlink()

historico = ""


def conversar(msg):
    global historico

    print("\n" + "=" * 70)
    print("USUÁRIO:", msg)

    resposta = responder(
        telefone=TELEFONE,
        mensagem=msg,
        historico_recente=historico,
    )

    print("ANA:\n")
    print(resposta)

    historico += f"\nUsuário: {msg}\nANA: {resposta}"

    estado = None
    dados = {}

    if conv_file.exists():
        c = json.loads(conv_file.read_text())
        estado = c.get("state")
        dados = c.get("data", {})

    print("\nSTATE:", estado)

    return resposta, estado, dados


# Início
conversar("Olá, gostaria de agendar uma consulta.")
conversar("Primeira consulta")
conversar("Para mim")

# Preferência
resposta, estado, dados = conversar("qualquer dia")

# Primeira data
if estado == "aguardando_data":

    primeira_data = next(iter(dados["agenda"]))

    data = primeira_data[8:10] + "/" + primeira_data[5:7]

    print("\n>>> DATA:", data)

    resposta, estado, dados = conversar(data)

# Primeiro horário
if estado == "aguardando_horario":

    horario = dados["horarios"]["slots"][0]

    print("\n>>> HORÁRIO:", horario)

    resposta, estado, dados = conversar(horario)

print("\n")
print("=" * 70)
print("FIM DO TESTE")
print("=" * 70)
