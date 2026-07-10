from typing import Optional

from ana_feegow.client import FeegowClient


def buscar_paciente(
    nome: Optional[str] = None,
    cpf: Optional[str] = None,
    telefone: Optional[str] = None,
    client: Optional[FeegowClient] = None,
):
    client = client or FeegowClient()

    params = {}

    if cpf:
        params["cpf"] = cpf
    elif telefone:
        params["celular"] = telefone
    elif nome:
        params["nome"] = nome
    else:
        raise ValueError("Informe nome, CPF ou telefone.")

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
