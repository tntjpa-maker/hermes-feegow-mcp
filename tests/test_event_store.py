from pprint import pprint

from ana_feegow.workflows.event_store import (
    registrar_evento,
    listar_eventos,
)

registrar_evento(
    agendamento_id=31,
    tipo="reserva_criada",
    dados={
        "paciente_id": 68,
        "status": 208,
    },
)

print()
print("=" * 60)
print("EVENTOS")
print("=" * 60)

pprint(listar_eventos())
