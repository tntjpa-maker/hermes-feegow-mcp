from ana_feegow.client import FeegowClient

client = FeegowClient()


def listar_agendamentos(
    paciente_id: int,
    data_inicio: str = "",
    data_fim: str = "",
):
    params = {
        "paciente_id": paciente_id,
    }

    if data_inicio:
        params["data_start"] = data_inicio

    if data_fim:
        params["data_end"] = data_fim

    return client.get(
        "/appoints/list",
        params=params,
    )
