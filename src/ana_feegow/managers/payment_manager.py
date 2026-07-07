from datetime import datetime


def verificar_pagamento(reserva: dict):
    agora = datetime.now()

    warning = datetime.fromisoformat(reserva["warning_at"])
    expires = datetime.fromisoformat(reserva["expires_at"])

    if agora >= expires:
        return {
            "acao": "cancelar_reserva",
            "status": 11,
            "motivo": "timeout_pagamento",
        }

    if agora >= warning:
        return {
            "acao": "enviar_lembrete",
            "minutos_restantes": int((expires - agora).total_seconds() / 60),
        }

    return {
        "acao": "aguardar",
        "minutos_restantes": int((expires - agora).total_seconds() / 60),
    }
