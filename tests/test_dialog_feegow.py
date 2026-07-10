from pprint import pprint

from ana_feegow.ana.conversation import Conversation
from ana_feegow.ana.dialog import responder

conv = Conversation("21985929056")

print(responder("21985929056", ""))

print()

print(responder("21985929056", "Primeira consulta"))

print()

resultado = responder("21985929056", "15/07/2026")

print("HORÁRIOS")

pprint(resultado)

print()

print(responder("21985929056", "14:00"))
