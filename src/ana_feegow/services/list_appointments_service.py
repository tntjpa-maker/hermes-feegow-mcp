from datetime import datetime, timedelta

from ana_feegow.client import FeegowClient
from ana_feegow.tools.identify import identificar_paciente

client = FeegowClient()


def listar_consultas_futuras(telefone: str):

    paciente = identificar_paciente(telefone)

    if not paciente.get("existe"):
        return []

    paciente_id = paciente["paciente"]["patient_id"]

    hoje = datetime.today()
    fim = hoje + timedelta(days=180)

    resultado = client.get(
        "/appoints/search",
        params={
            "paciente_id": paciente_id,
            "data_start": hoje.strftime("%d-%m-%Y"),
            "data_end": fim.strftime("%d-%m-%Y"),
        },
    )

    return resultado.get("content", [])
