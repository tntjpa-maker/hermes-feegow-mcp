from ana_feegow.client import FeegowClient

client = FeegowClient()


def atualizar_status(
    agendamento_id: int,
    status_id: int,
    observacao: str = "",
):
    payload = {
        "AgendamentoID": agendamento_id,
        "StatusID": status_id,
        "Obs": observacao,
    }

    return client.post(
        "/appoints/statusUpdate",
        payload,
    )
