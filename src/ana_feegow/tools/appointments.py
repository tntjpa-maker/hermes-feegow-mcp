from typing import Optional

from ana_feegow.client import FeegowClient
from ana_feegow.config.clinic import CLINIC


def criar_agendamento(
    paciente_id: int,
    data: str,
    horario: str,
    celular: str = "",
    telefone: str = "",
    email: str = "",
    notas: str = "",
    retorno: bool = False,
    client: Optional[FeegowClient] = None,
):
    client = client or FeegowClient()

    payload = {
        "local_id": CLINIC["local_id"],
        "paciente_id": paciente_id,
        "profissional_id": CLINIC["profissional_id"],
        "especialidade_id": CLINIC["especialidade_id"],
        "procedimento_id": CLINIC["procedimento_id"],
        "data": data,
        "horario": horario,
        "valor": CLINIC["valor_consulta"],
        "plano": 0,
        "canal_id": CLINIC["canal_id"],
        "tabela_id": CLINIC["tabela_id"],
        "notas": notas,
        "celular": celular,
        "telefone": telefone,
        "email": email,
        "retorno": retorno,
        "sys_user": CLINIC["sys_user"],
    }

    return client.post("/appoints/new-appoint", payload)
