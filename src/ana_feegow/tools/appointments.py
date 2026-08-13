from typing import Optional

from ana_feegow.client import FeegowClient


def criar_agendamento(dados, client: Optional[FeegowClient] = None):
    client = client or FeegowClient()
    return client.post("/appoints/new-appoint", dados)
