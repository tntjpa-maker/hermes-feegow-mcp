from typing import Optional

from ana_feegow.appointments.update_status import atualizar_status
from ana_feegow.client import FeegowClient


def cancelar_consulta(
    agendamento_id: int,
    observacao: str = "Cancelamento recebido do Cal.com",
    client: Optional[FeegowClient] = None,
):
    return atualizar_status(
        agendamento_id=agendamento_id,
        status_id=11,
        observacao=observacao,
        client=client,
    )
