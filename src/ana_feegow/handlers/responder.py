from ana_feegow.ana.knowledge import RESPOSTAS


def responder(decisao, conv):
    return RESPOSTAS.get(
        decisao["intencao"],
        "Como posso ajudar você?"
    )
