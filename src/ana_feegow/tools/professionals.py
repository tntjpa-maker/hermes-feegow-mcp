from typing import Optional

from ana_feegow.client import FeegowClient
from ana_feegow.config import settings


def listar_profissionais(
    client: Optional[FeegowClient] = None,
    unidade_id: Optional[int] = None,
    especialidade_id: Optional[int] = None,
    ativo: int = 1,
):
    client = client or FeegowClient()

    params = {
        "ativo": ativo,
        "unidade_id": unidade_id or settings.FEEGOW_DEFAULT_UNIDADE_ID,
        "especialidade_id": especialidade_id or settings.FEEGOW_DEFAULT_ESPECIALIDADE_ID,
    }

    return client.get("/professional/list", params=params)
