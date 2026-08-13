from typing import Optional

from ana_feegow.client import FeegowClient

PAGE_SIZE = 200


def identificar_paciente(
    telefone: str,
    client: Optional[FeegowClient] = None,
):
    # IMPORTANTE: o endpoint GET /patient/list do Feegow ignora os filtros
    # "telefone" e "celular" na prática (confirmado manualmente contra a API
    # real em 28/07/2026: buscar por um celular específico devolve
    # pacientes cujo celular não bate com o filtro, na ordem padrão da
    # listagem). Por isso, em vez de confiar no filtro do servidor, sempre
    # buscamos o(s) paciente(s) e comparamos o celular no cliente - só
    # assim garantimos que a paciente identificada é realmente a dona do
    # número de telefone informado.
    client = client or FeegowClient()

    telefone = ''.join(c for c in telefone if c.isdigit())

    offset = 0
    while True:
        resultado = client.get(
            "/patient/list",
            params={
                "limit": PAGE_SIZE,
                "offset": offset,
            },
        )

        pacientes = resultado.get("content") or []

        for paciente in pacientes:
            celular = ''.join(c for c in str(paciente.get("celular") or "") if c.isdigit())
            if celular and celular == telefone:
                return {
                    "existe": True,
                    "paciente": paciente,
                }

        total = resultado.get("total", len(pacientes))
        offset += len(pacientes)

        if not pacientes or offset >= total:
            break

    return {
        "existe": False,
        "paciente": None,
    }
