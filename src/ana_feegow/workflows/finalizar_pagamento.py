from ana_feegow.appointments.update_status import atualizar_status


def confirmar_pagamento(agendamento_id: int):
    return atualizar_status(
        agendamento_id=agendamento_id,
        status_id=7,
        observacao="Pagamento confirmado automaticamente pela ANA",
    )


def cancelar_pagamento(agendamento_id: int):
    return atualizar_status(
        agendamento_id=agendamento_id,
        status_id=11,
        observacao="Reserva cancelada por timeout de pagamento",
    )
