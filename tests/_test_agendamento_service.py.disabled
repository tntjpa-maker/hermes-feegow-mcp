from pprint import pprint

from ana_feegow.services.agendamento_service import agendar_consulta
from ana_feegow.errors import FeegowAPIError

try:
    resultado = agendar_consulta(
        paciente_id=68,
        tipo_consulta="consulta_presencial",
        data="11-07-2026",
        horario="10:00:00",
        celular="21999999999",
        email="teste@magnolia.com",
        notas="Teste via agendamento_service",
    )

    print("\n==========================")
    print("AGENDAMENTO CRIADO")
    print("==========================")
    pprint(resultado)

except FeegowAPIError as e:
    print("\n==========================")
    print("STATUS:", e.status_code)
    print("==========================")
    print(e.body)

    if hasattr(e, "context"):
        print("\nPAYLOAD:")
        pprint(e.context.get("json"))
