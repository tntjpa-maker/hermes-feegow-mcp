from ana_feegow.client import FeegowClient

client = FeegowClient()


def atualizar_status(
    agendamento_id: int,
    status_id: int,
    obs: str = "",
):
    return client.post(
        "/appoints/statusUpdate",
        {
            "AgendamentoID": agendamento_id,
            "StatusID": status_id,
            "Obs": obs,
        },
    )
