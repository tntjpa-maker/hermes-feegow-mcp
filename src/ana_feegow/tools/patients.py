from typing import Optional

from ana_feegow.client import FeegowClient
from ana_feegow.tools.identify import identificar_paciente

PAGE_SIZE = 200


def buscar_paciente(
    nome: Optional[str] = None,
    cpf: Optional[str] = None,
    telefone: Optional[str] = None,
    client: Optional[FeegowClient] = None,
):
    client = client or FeegowClient()

    if telefone:
        # IMPORTANTE: GET /patient/list ignora o filtro "celular" na
        # prática (confirmado manualmente contra a API real em 28/07/2026)
        # - sem essa checagem no cliente, esta função (usada como fallback
        # de identificação em FeegowSyncService.ensure_patient) devolveria
        # o primeiro paciente da listagem padrão do Feegow, vinculando o
        # agendamento a uma pessoa completamente diferente. Reaproveita a
        # mesma lógica, já corrigida, de identificar_paciente().
        resultado = identificar_paciente(telefone, client=client)
        if resultado["existe"]:
            return {"total": 1, "content": [resultado["paciente"]]}
        return {"total": 0, "content": []}

    params = {}

    if cpf:
        params["cpf"] = cpf
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
