"""Elegibilidade de "consulta de retorno" (sem cobrança).

Regra de negócio definida pela clínica: o paciente pode agendar um retorno
gratuito se a última consulta efetivamente **atendida** (status Feegow
"Atendido", status_id=3 — confirmado empiricamente contra a API real em
28/07/2026 via GET /appoints/status) tiver ocorrido há no máximo
`CLINIC["retorno_dias"]` dias (padrão: 30).

Catálogo completo de status_id do Feegow, para referência (GET /appoints/status):
    1  - Marcado – não confirmado
    2  - Em atendimento
    3  - Atendido                     <- usado para elegibilidade de retorno
    4  - Aguardando
    5  - Chamando
    6  - Não compareceu
    7  - Marcado – confirmado
    11 - Desmarcado pelo paciente     <- status usado por cancelamento_service
    15 - Remarcado
    22 - Cancelado pelo profissional
    208 - Aguardando pagamento
"""

from datetime import datetime, timedelta
from typing import Optional

from ana_feegow.client import FeegowClient
from ana_feegow.settings.clinic import CLINIC
from ana_feegow.tools.identify import identificar_paciente
from ana_feegow.tools.list_appointments import buscar_agendamentos

STATUS_ATENDIDO = 3

# Janela de busca no histórico de agendamentos. Precisa ser maior que
# `retorno_dias` (para não perder a última consulta relevante) e menor que 6
# meses (limite da API Feegow para /appoints/search).
JANELA_BUSCA_DIAS = 150


def _parse_data_feegow(data_str: str) -> datetime:
    return datetime.strptime(data_str, "%d-%m-%Y")


def verificar_elegibilidade_retorno(
    telefone: str,
    dias_limite: Optional[int] = None,
    client: Optional[FeegowClient] = None,
    hoje: Optional[datetime] = None,
) -> dict:
    """Verifica se o paciente identificado por `telefone` pode agendar retorno.

    Retorna um dict com:
        elegivel (bool)
        motivo (str): "paciente_nao_encontrado" | "sem_consulta_atendida_recente"
                       | "dentro_do_prazo" | "fora_do_prazo"
        ultima_consulta_data (str | None): data no formato DD-MM-AAAA
        dias_desde_ultima (int | None)
    """
    dias_limite = dias_limite if dias_limite is not None else CLINIC["retorno_dias"]
    feegow_client = client or FeegowClient()
    hoje = hoje or datetime.now()

    paciente_info = identificar_paciente(telefone, client=feegow_client)

    if not paciente_info["existe"]:
        return {
            "elegivel": False,
            "motivo": "paciente_nao_encontrado",
            "ultima_consulta_data": None,
            "dias_desde_ultima": None,
        }

    paciente_id = paciente_info["paciente"]["patient_id"]

    data_inicio = hoje - timedelta(days=JANELA_BUSCA_DIAS)

    resultado = buscar_agendamentos(
        paciente_id=paciente_id,
        data_start=data_inicio.strftime("%d-%m-%Y"),
        data_end=hoje.strftime("%d-%m-%Y"),
        client=feegow_client,
    )

    agendamentos = resultado.get("content") or []

    atendidas = [a for a in agendamentos if a.get("status_id") == STATUS_ATENDIDO]

    if not atendidas:
        return {
            "elegivel": False,
            "motivo": "sem_consulta_atendida_recente",
            "ultima_consulta_data": None,
            "dias_desde_ultima": None,
        }

    atendidas.sort(key=lambda a: _parse_data_feegow(a["data"]), reverse=True)
    ultima = atendidas[0]
    ultima_data = _parse_data_feegow(ultima["data"])
    dias_desde = (hoje.date() - ultima_data.date()).days

    elegivel = 0 <= dias_desde <= dias_limite

    return {
        "elegivel": elegivel,
        "motivo": "dentro_do_prazo" if elegivel else "fora_do_prazo",
        "ultima_consulta_data": ultima["data"],
        "dias_desde_ultima": dias_desde,
    }


def link_consulta_retorno() -> str:
    from ana_feegow.config import settings

    base = settings.CALCOM_BASE_URL.rstrip("/")
    return f"{base}/{CLINIC['calcom_slug_retorno']}"


def link_consulta_presencial() -> str:
    from ana_feegow.config import settings

    base = settings.CALCOM_BASE_URL.rstrip("/")
    return f"{base}/{CLINIC['calcom_slug_presencial']}"


def link_consulta_online() -> str:
    from ana_feegow.config import settings

    base = settings.CALCOM_BASE_URL.rstrip("/")
    return f"{base}/{CLINIC['calcom_slug_online']}"
