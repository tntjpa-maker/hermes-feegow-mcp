from ana_feegow.tools.update_appointment import remarcar_agendamento


def remarcar_consulta(
    agendamento_id: int,
    data: str,
    horario: str,
    motivo_id: int = 1,
):
    payload = {
        "agendamento_id": agendamento_id,
        "motivo_id": motivo_id,
        "data": data,
        "horario": horario if len(horario) == 8 else horario + ":00",
        "obs": "Remarcação realizada pela ANA",
    }

    return remarcar_agendamento(payload)
