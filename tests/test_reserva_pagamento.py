from pprint import pprint

from ana_feegow.workflows.reserva_pagamento import criar_reserva

resultado = criar_reserva(
    paciente_id=68,
    tipo_consulta="consulta_presencial",
    data="12-07-2026",
    horario="09:30:00",
    celular="21999999999",
    email="teste@magnolia.com",
)

print()
print("=" * 60)
print("RESERVA")
print("=" * 60)
pprint(resultado)
