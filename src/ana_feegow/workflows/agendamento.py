from ana_feegow.ana.conversation import Conversation


def proxima_acao(conv: Conversation):

    estado = conv.state

    if estado == "inicio":
        return "perguntar_tipo_consulta"

    if estado == "aguardando_motivo":
        return "perguntar_data"

    if estado == "aguardando_data":
        return "consultar_agenda"

    if estado == "aguardando_horario":
        return "reservar_horario"

    if estado == "aguardando_pagamento":
        return "aguardar_pagamento"

    if estado == "confirmado":
        return "encerrar"

    return "desconhecido"
