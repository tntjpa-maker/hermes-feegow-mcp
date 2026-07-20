from typing import Optional

from ana_feegow.client import FeegowClient


def identificar_paciente(
    telefone: str,
    client: Optional[FeegowClient] = None,
):
    client = client or FeegowClient()

    # Mantém apenas os dígitos
    telefone = "".join(filter(str.isdigit, telefone or ""))

    # WhatsApp/Hermes envia normalmente +55DDDNÚMERO
    # O Feegow armazena apenas DDD+NÚMERO.
    if telefone.startswith("55") and len(telefone) > 11:
        telefone = telefone[2:]

    resultado = client.get(
        "/patient/list",
        params={
            "telefone": telefone,
            "limit": 1,
            "offset": 0,
        },
    )

    if resultado.get("total", 0) > 0:
        return {
            "existe": True,
            "paciente": resultado["content"][0],
        }

    return {
        "existe": False,
        "paciente": None,
    }
