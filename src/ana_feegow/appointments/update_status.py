from typing import Optional

from ana_feegow.client import FeegowClient


def atualizar_status(
    agendamento_id: int,
    status_id: int,
    observacao: str = "",
    client: Optional[FeegowClient] = None,
):
    client = client or FeegowClient()
    payload = {
        "AgendamentoID": agendamento_id,
        "StatusID": status_id,
        "Obs": observacao,
    }
    return client.post("/appoints/statusUpdate", payload)
