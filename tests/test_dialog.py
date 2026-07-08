from ana_feegow.ana.conversation import Conversation
from ana_feegow.ana.dialog import responder

conv = Conversation()

mensagens = [
    "",
    "Primeira consulta",
    "Sexta-feira",
    "À tarde",
]

for m in mensagens:
    print("\nPACIENTE:", m)
    print("ANA:", responder(conv, m))
    print("ESTADO:", conv.state)
