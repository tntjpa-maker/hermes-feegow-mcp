from typing import Optional

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


def buscar_agendamentos(
    paciente_id: int,
    data_start: str,
    data_end: str,
    client: Optional[FeegowClient] = None,
):
    """Busca o histórico de agendamentos de um paciente via GET /appoints/search.

    Diferente de `listar_agendamentos` (que usa /appoints/list e exige outros
    parâmetros não documentados), este endpoint foi validado manualmente contra
    a API real do Feegow e é a forma correta de consultar o histórico de
    consultas de um paciente.

    Datas no formato "DD-MM-AAAA". A API do Feegow exige que o intervalo entre
    data_start e data_end seja menor que 6 meses (erro 409 "Intervalo de data
    deve ser menor que 6 meses." caso contrário), e exige um dos parâmetros
    data_start/data_end, agendamento_id ou created_at_start/created_at_end
    (erro 422 caso nenhum esteja presente).
    """
    feegow_client = client or FeegowClient()

    return feegow_client.get(
        "/appoints/search",
        params={
            "paciente_id": paciente_id,
            "data_start": data_start,
            "data_end": data_end,
        },
    )
