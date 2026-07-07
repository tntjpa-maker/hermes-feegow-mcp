from typing import Optional

from ana_feegow.client import FeegowClient


def consultar_horarios(
    procedimento_id: int,
    data_inicio: str,
    data_fim: str,
    convenio_id: int = 1,
    unidade_id: int = 0,
    client: Optional[FeegowClient] = None,
):
    client = client or FeegowClient()

    return client.get(
        "/appoints/available-schedule",
        params={
            "tipo": "P",
            "procedimento_id": procedimento_id,
            "unidade_id": unidade_id,
            "data_start": data_inicio,
            "data_end": data_fim,
            "convenio_id": convenio_id,
        },
    )
