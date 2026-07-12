from typing import Optional

from ana_feegow.client import FeegowClient
from ana_feegow.config import settings


def listar_profissionais(
    client: Optional[FeegowClient] = None,
    unidade_id: Optional[int] = None,
    especialidade_id: Optional[int] = None,
    ativo: Optional[int] = 1,
):
    client = client or FeegowClient()

    params = {}

    if ativo is not None:
        params["ativo"] = ativo

    if unidade_id is not None:
        params["unidade_id"] = unidade_id

    if especialidade_id is not None:
        params["especialidade_id"] = especialidade_id
    elif settings.FEEGOW_DEFAULT_ESPECIALIDADE_ID:
        params["especialidade_id"] = settings.FEEGOW_DEFAULT_ESPECIALIDADE_ID

    return client.get("/professional/list", params=params)
