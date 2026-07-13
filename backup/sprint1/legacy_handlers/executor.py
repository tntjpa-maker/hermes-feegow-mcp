from ana_feegow.handlers.responder import responder
from ana_feegow.handlers.agendar import agendar
from ana_feegow.handlers.cadastro import cadastro

HANDLERS = {
    "RESPONDER": responder,
    "AGENDAR": agendar,
    "CADASTRO": cadastro,
    "TIPO_CONSULTA": agendar,
}


def executar(decisao, conv):
    handler = HANDLERS.get(decisao["acao"])

    if handler:
        return handler(conv) if decisao["acao"] == "CADASTRO" else handler(decisao, conv)

    return "Ainda não sei executar essa ação."
