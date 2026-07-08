from pprint import pprint

from ana_feegow.tools.availability import consultar_horarios
from ana_feegow.errors import FeegowAPIError

try:
    resultado = consultar_horarios(
        tipo_consulta="consulta_presencial",
        data_inicio="15-07-2026",
        data_fim="15-07-2026",
    )

    pprint(resultado)

except FeegowAPIError as e:
    print("STATUS:", e.status_code)
    print("MENSAGEM:", e.message)
    pprint(e.payload)
except Exception as e:
    print(type(e).__name__)
    print(e)
