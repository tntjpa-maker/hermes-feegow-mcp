from pprint import pprint

from ana_feegow.ana.conversation import Conversation
from ana_feegow.ana.dialog import responder

conv = Conversation()

print(responder(conv, ""))

print()

print(responder(conv, "Primeira consulta"))

print()

resultado = responder(conv, "15/07/2026")

print("HORÁRIOS")

pprint(resultado)

print()

print(responder(conv, "14:00"))
