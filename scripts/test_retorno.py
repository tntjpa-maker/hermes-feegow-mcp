#!/usr/bin/env python3

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ana_feegow.ana.dialog import responder

TELEFONE = "21985929056"      # paciente que já possui consulta

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

    print("\nANA:\n")
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


# ------------------------
# Fluxo Retorno
# ------------------------

conversar("Olá")

conversar("quero marcar retorno")

conversar("retorno")

conversar("para mim")

resposta, estado, dados = conversar("qualquer dia")

if estado == "aguardando_data":

    primeira = next(iter(dados["agenda"]))
    data = primeira[8:10] + "/" + primeira[5:7]

    print("\n>>> DATA:", data)

    resposta, estado, dados = conversar(data)

if estado == "aguardando_horario":

    horario = dados["horarios"]["slots"][0]

    print("\n>>> HORÁRIO:", horario)

    resposta, estado, dados = conversar(horario)

print("\n")
print("=" * 70)
print("PAYLOAD")
print("=" * 70)

payload = ROOT / "logs" / "agendamento_payload.json"

if payload.exists():
    print(payload.read_text())
else:
    print("Payload não encontrado.")
