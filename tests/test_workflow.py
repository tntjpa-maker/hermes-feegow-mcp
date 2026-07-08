from ana_feegow.ana.conversation import Conversation
from ana_feegow.workflows.agendamento import proxima_acao

c = Conversation()

print(c.state, "->", proxima_acao(c))

c.state = "aguardando_motivo"
print(c.state, "->", proxima_acao(c))

c.state = "aguardando_data"
print(c.state, "->", proxima_acao(c))

c.state = "aguardando_horario"
print(c.state, "->", proxima_acao(c))

c.state = "aguardando_pagamento"
print(c.state, "->", proxima_acao(c))

c.state = "confirmado"
print(c.state, "->", proxima_acao(c))
