from ana_feegow.tools.identify import identificar_paciente


def test_identificar_paciente():

    resultado = identificar_paciente("21990368159")

    print(resultado)

    assert "existe" in resultado
