from pprint import pprint

from ana_feegow.appointments.update_status import atualizar_status
from ana_feegow.errors import FeegowAPIError

AGENDAMENTO_ID = 30

try:

    resultado = atualizar_status(
        agendamento_id=AGENDAMENTO_ID,
        status_id=208,
        observacao="Reserva criada automaticamente pela ANA",
    )

    print("\n==============================")
    print("STATUS ALTERADO")
    print("==============================")
    pprint(resultado)

except FeegowAPIError as e:

    print("\n==============================")
    print("STATUS:", e.status_code)
    print("==============================")
    print(e.message)
    print(e.payload)
