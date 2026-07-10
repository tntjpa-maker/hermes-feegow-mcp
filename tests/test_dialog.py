from ana_feegow.ana.conversation import Conversation
from ana_feegow.ana.dialog import responder

conv = Conversation("21985929056")

mensagens = [
    "",
    "Primeira consulta",
    "Sexta-feira",
    "À tarde",
]

for m in mensagens:
    print("\nPACIENTE:", m)
    print("ANA:", responder("21985929056", m))
    print("ESTADO:", conv.state)
