from pprint import pprint

from ana_feegow.managers.payment_manager import verificar_pagamento
from ana_feegow.workflows.pagamento import iniciar_pagamento

reserva = iniciar_pagamento(
    agendamento_id=31,
    paciente_id=68,
)

print()
print("=" * 60)
print("PAYMENT MANAGER")
print("=" * 60)

pprint(verificar_pagamento(reserva))
