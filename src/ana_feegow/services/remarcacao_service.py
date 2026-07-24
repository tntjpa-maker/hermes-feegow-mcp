from datetime import datetime
from typing import Optional

from ana_feegow.client import FeegowClient
from ana_feegow.tools.update_appointment import remarcar_agendamento


def remarcar_consulta(
    agendamento_id: int,
    data: str,
    horario: str,
    motivo_id: int = 1,
    observacao: str = "Remarcação realizada pela integração Cal.com",
    client: Optional[FeegowClient] = None,
):
    payload = {
        "agendamento_id": agendamento_id,
        "motivo_id": motivo_id,
        "data": datetime.strptime(data, "%Y-%m-%d").strftime("%d-%m-%Y"),
        "horario": (
            horario if len(horario) == 8 else f"{horario}:00"
        ),
        "obs": observacao,
    }
    return remarcar_agendamento(payload, client=client)
