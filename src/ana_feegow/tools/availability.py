from typing import Optional

from ana_feegow.client import FeegowClient
from ana_feegow.settings.clinic import CLINIC
from ana_feegow.settings.services import SERVICES


def consultar_horarios(
    tipo_consulta: str,
    data_inicio: str,
    data_fim: str,
    client: Optional[FeegowClient] = None,
):

    client = client or FeegowClient()

    servico = SERVICES[tipo_consulta]

    return client.get(
        "/appoints/available-schedule",
        params={
            "tipo": "P",
            "procedimento_id": servico["procedimento_id"],
            "unidade_id": CLINIC["local_id"],
            "convenio_id": CLINIC["convenio_id"],
            "data_start": data_inicio,
            "data_end": data_fim,
        },
    )
