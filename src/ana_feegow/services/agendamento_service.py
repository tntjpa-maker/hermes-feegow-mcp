from datetime import datetime
from typing import Optional

from ana_feegow.client import FeegowClient
from ana_feegow.errors import FeegowAPIError
from ana_feegow.settings.clinic import CLINIC
from ana_feegow.settings.services import SERVICES
from ana_feegow.tools.appointments import criar_agendamento


def _normalizar_data(data: str) -> str:
    for formato in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(data, formato).strftime("%d-%m-%Y")
        except ValueError:
            continue
    raise ValueError("Data inválida. Use YYYY-MM-DD, DD-MM-YYYY ou DD/MM/YYYY.")


def _normalizar_horario(horario: str) -> str:
    for formato in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(horario, formato).strftime("%H:%M:%S")
        except ValueError:
            continue
    raise ValueError("Horário inválido. Use HH:MM ou HH:MM:SS.")


def agendar_consulta(
    paciente_id: int,
    tipo_consulta: str,
    data: str,
    horario: str,
    celular: str = "",
    telefone: str = "",
    email: str = "",
    retorno: bool = False,
    notas: str = "",
    client: Optional[FeegowClient] = None,
):
    if tipo_consulta not in SERVICES:
        raise ValueError(f"Tipo de consulta desconhecido: {tipo_consulta}")

    servico = SERVICES[tipo_consulta]
    dados = {
        "local_id": CLINIC["local_id"],
        "paciente_id": paciente_id,
        "profissional_id": CLINIC["profissional_id"],
        "especialidade_id": CLINIC["especialidade_id"],
        "procedimento_id": servico["procedimento_id"],
        "data": _normalizar_data(data),
        "horario": _normalizar_horario(horario),
        "valor": servico["valor"],
        "plano": CLINIC["plano"],
        "canal_id": CLINIC["canal_id"],
        "tabela_id": CLINIC["tabela_id"],
        "notas": notas.strip() or "Agendamento realizado pela integração",
        "celular": celular,
        "telefone": telefone,
        "email": email,
        "retorno": retorno,
        "sys_user": CLINIC["sys_user"],
    }

    try:
        return criar_agendamento(dados, client=client)
    except FeegowAPIError as exc:
        return {
            "success": False,
            "duplicate": exc.status_code == 409,
            "status_code": exc.status_code,
            "message": exc.message,
        }
