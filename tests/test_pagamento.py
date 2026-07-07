from pprint import pprint

from ana_feegow.workflows.pagamento import iniciar_pagamento

resultado = iniciar_pagamento(
    agendamento_id=31,
    paciente_id=68,
)

print()
print("=" * 60)
print("CONTROLE DE PAGAMENTO")
print("=" * 60)
pprint(resultado)
