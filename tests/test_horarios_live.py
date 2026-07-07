from ana_feegow.tools.availability import consultar_horarios


def test_horarios():
    resultado = consultar_horarios(
        procedimento_id=5,
        data_inicio="07-07-2026",
        data_fim="07-07-2026",
    )

    print(resultado)

    assert resultado["success"] is True
