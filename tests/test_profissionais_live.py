from ana_feegow.tools.professionals import listar_profissionais


def test_listar_profissionais_live():
    result = listar_profissionais()
    assert result is not None
    print(result)
