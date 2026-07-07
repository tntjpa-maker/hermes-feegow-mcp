from ana_feegow.services.agendamento_service import agendar_consulta
from ana_feegow.appointments.update_status import atualizar_status


def criar_reserva(
    paciente_id: int,
    tipo_consulta: str,
    data: str,
    horario: str,
    celular: str,
    email: str = "",
):

    resultado = agendar_consulta(
        paciente_id=paciente_id,
        tipo_consulta=tipo_consulta,
        data=data,
        horario=horario,
        celular=celular,
        email=email,
        retorno=False,
        notas="Reserva criada pela ANA",
    )

    agendamento_id = resultado["content"]["agendamento_id"]

    atualizar_status(
        agendamento_id=agendamento_id,
        status_id=208,
        observacao="Aguardando pagamento",
    )

    return {
        "success": True,
        "agendamento_id": agendamento_id,
        "status": "aguardando_pagamento",
        "prazo_minutos": 30,
    }
