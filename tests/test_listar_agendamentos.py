from pprint import pprint

from ana_feegow.errors import FeegowAPIError
from ana_feegow.tools.list_appointments import listar_agendamentos

try:
    resultado = listar_agendamentos(
        paciente_id=68,
    )

    print("\n==========================")
    print("AGENDAMENTOS")
    print("==========================")
    pprint(resultado)

except FeegowAPIError as e:
    print("\n==========================")
    print("STATUS:", e.status_code)
    print("==========================")
    print(e.body)

    if hasattr(e, "context"):
        print("\nPARAMS:")
        pprint(e.context.get("params"))
