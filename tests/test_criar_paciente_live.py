from ana_feegow.tools.create_patient import criar_paciente


def test_criar_paciente():

    resultado = criar_paciente(
        nome="PACIENTE TESTE MCP",
        cpf="12345678909",
        nascimento="1990-01-01",
        celular="21999999999",
        email="teste.mcp@magnolia.com"
    )

    print(resultado)

    assert resultado["success"] is True
