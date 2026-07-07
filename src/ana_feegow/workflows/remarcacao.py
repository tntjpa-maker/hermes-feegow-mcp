from datetime import datetime, timedelta

from ana_feegow.tools.availability import consultar_horarios
from ana_feegow.services.agendamento_service import agendar_consulta
from ana_feegow.appointments.update_status import atualizar_status
from ana_feegow.workflows.event_store import registrar_evento


def pode_remarcar(data: str, horario: str):
    consulta = datetime.strptime(
        f"{data} {horario}",
        "%d-%m-%Y %H:%M:%S"
    )

    return consulta - datetime.now() >= timedelta(hours=2)


def consultar_opcoes(
    tipo_consulta: str,
    data_inicio: str,
    data_fim: str,
):
    return consultar_horarios(
        tipo_consulta=tipo_consulta,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


def remarcar_consulta(
    agendamento_antigo: int,
    paciente_id: int,
    tipo_consulta: str,
    nova_data: str,
    novo_horario: str,
    celular: str,
    email: str = "",
):

    if not pode_remarcar(nova_data, novo_horario):
        return {
            "success": False,
            "motivo": "prazo_inferior_duas_horas",
            "acao": "encaminhar_secretaria",
        }

    novo = agendar_consulta(
        paciente_id=paciente_id,
        tipo_consulta=tipo_consulta,
        data=nova_data,
        horario=novo_horario,
        celular=celular,
        email=email,
        retorno=False,
        notas="Remarcação realizada pela ANA",
    )

    atualizar_status(
        agendamento_id=agendamento_antigo,
        status_id=15,
        observacao="Consulta remarcada automaticamente",
    )

    registrar_evento(
        agendamento_id=agendamento_antigo,
        tipo="consulta_remarcada",
        dados={
            "novo_agendamento": novo["content"]["agendamento_id"],
        },
    )

    return {
        "success": True,
        "agendamento_antigo": agendamento_antigo,
        "agendamento_novo": novo["content"]["agendamento_id"],
    }
