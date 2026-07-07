from typing import Optional

from ana_feegow.client import FeegowClient


def buscar_paciente(
    nome: Optional[str] = None,
    telefone: Optional[str] = None,
    client: Optional[FeegowClient] = None,
):
    client = client or FeegowClient()

    params = {}

    if nome:
        params["nome"] = nome

    if telefone:
        params["celular"] = telefone

    return client.get("/patient/list", params=params)


def buscar_paciente_por_id(
    paciente_id: int,
    client: Optional[FeegowClient] = None,
):
    client = client or FeegowClient()

    return client.get(
        "/patient/search",
        params={"paciente_id": paciente_id},
    )
