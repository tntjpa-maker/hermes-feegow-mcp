from pprint import pprint

from ana_feegow.tools.availability import consultar_horarios

try:
    resultado = consultar_horarios(
        "consulta_presencial",
        "15/07/2026",
        "15/07/2026",
    )

    pprint(resultado)

except Exception as e:
    print(type(e).__name__)
    print(e)

    if hasattr(e, "__dict__"):
        pprint(e.__dict__)
