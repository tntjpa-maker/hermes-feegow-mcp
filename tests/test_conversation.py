from pprint import pprint

from ana_feegow.ana.conversation import Conversation

c = Conversation()

pprint(c.get())

c.next("aguardando_data")

c.update("motivo", "Primeira consulta")

pprint(c.get())
