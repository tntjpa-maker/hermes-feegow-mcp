from pprint import pprint

from ana_feegow.workflows.pagamento import iniciar_pagamento
from ana_feegow.workflows.reserva_store import (
    salvar_reserva,
    listar_reservas,
)

reserva = iniciar_pagamento(
    agendamento_id=31,
    paciente_id=68,
)

salvar_reserva(reserva)

print()
print("=" * 60)
print("RESERVAS")
print("=" * 60)

pprint(listar_reservas())
