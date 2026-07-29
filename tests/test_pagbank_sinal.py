from ana_feegow.webhooks.pagbank_client import _valor_sinal_centavos


def test_sinal_consulta_presencial_e_20_por_cento_do_valor():
    # SERVICES["consulta_presencial"]["valor"] = 35000 (R$350,00).
    assert _valor_sinal_centavos("consulta_presencial") == 7000


def test_sinal_consulta_online_e_20_por_cento_do_valor():
    # SERVICES["consulta_online"]["valor"] = 25000 (R$250,00) -> sinal de
    # R$50,00 cobrado via PagBank no momento do agendamento.
    assert _valor_sinal_centavos("consulta_online") == 5000


def test_sinal_consulta_retorno_e_zero():
    assert _valor_sinal_centavos("consulta_retorno") == 0


def test_sinal_consulta_retorno_online_e_zero():
    # Assim como a consulta de retorno presencial, o retorno online não é
    # cobrado - nem passa pelo fluxo de checkout do PagBank de fato (ver
    # sync_handler.handle()), mas o cálculo precisa continuar zerado por
    # consistência caso a função seja chamada para esse tipo.
    assert _valor_sinal_centavos("consulta_retorno_online") == 0
