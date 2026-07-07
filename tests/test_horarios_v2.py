from ana_feegow.tools.availability import consultar_horarios


def test_horarios():

    r = consultar_horarios(
        tipo_consulta="consulta_presencial",
        data_inicio="08-07-2026",
        data_fim="15-07-2026",
    )

    print(r)

    assert r["success"] is True
