from datetime import datetime, timedelta


def iniciar_pagamento(
    agendamento_id: int,
    paciente_id: int,
):
    agora = datetime.now()

    return {
        "success": True,
        "agendamento_id": agendamento_id,
        "paciente_id": paciente_id,
        "status": "aguardando_pagamento",
        "created_at": agora.isoformat(),
        "expires_at": (agora + timedelta(minutes=30)).isoformat(),
        "warning_at": (agora + timedelta(minutes=25)).isoformat(),
    }
