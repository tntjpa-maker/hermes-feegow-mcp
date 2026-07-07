from typing import Optional

from ana_feegow.client import FeegowClient


def identificar_paciente(
    telefone: str,
    client: Optional[FeegowClient] = None,
):
    client = client or FeegowClient()

    telefone = ''.join(c for c in telefone if c.isdigit())

    resultado = client.get(
        "/patient/list",
        params={"celular": telefone}
    )

    if resultado.get("total", 0) > 0:
        return {
            "existe": True,
            "paciente": resultado["content"][0]
        }

    return {
        "existe": False,
        "paciente": None
    }
