from ana_feegow.tools.status import atualizar_status


STATUS_CONFIRMADO = 7


def confirmar_pagamento(agendamento_id: int):
    return atualizar_status(
        agendamento_id=agendamento_id,
        status_id=STATUS_CONFIRMADO,
        obs="Pagamento confirmado pela ANA via WhatsApp."
    )
