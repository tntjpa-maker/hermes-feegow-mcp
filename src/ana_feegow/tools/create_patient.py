from typing import Optional

from ana_feegow.client import FeegowClient


def criar_paciente(
    nome: str,
    cpf: str,
    nascimento: str,
    celular: str,
    email: str = "",
    genero: str = "",
    client: Optional[FeegowClient] = None,
):
    client = client or FeegowClient()

    payload = {
        "nome_completo": nome,
        "cpf": cpf,
        "data_nascimento": nascimento,
        "celular1": "".join(filter(str.isdigit, celular)),
        "email1": email,
        "genero": genero,
    }

    return client.post("/patient/create", payload)
