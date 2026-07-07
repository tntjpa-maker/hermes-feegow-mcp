from ana_feegow.tools.appointments import criar_agendamento


def test_criar_agendamento():

    resultado = criar_agendamento(
        paciente_id=68,
        tipo_consulta="consulta_presencial",
        data="08-07-2026",
        horario="08:00:00",
        celular="21999999999",
        telefone="21999999999",
        email="teste@magnolia.com",
    )

    print(resultado)

    assert resultado["success"] is True
