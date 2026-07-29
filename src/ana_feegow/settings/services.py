SERVICES = {

    "consulta_presencial": {
        "procedimento_id": 35,
        "valor": 35000,
        "duracao": 60,
    },

    "consulta_hibrida": {
        "procedimento_id": 36,
        "valor": 35000,
        "duracao": 60,
    },

    "consulta_online": {
        "procedimento_id": 37,
        "valor": 25000,
        "duracao": 30,
    },

    # Consulta de retorno (sem cobrança) - evento dedicado no Cal.com
    # (drathalita/consulta-retorno, eventTypeId=9). Usa o mesmo procedimento
    # da consulta presencial, mas registrado no Feegow com retorno=True e
    # valor=0 (ver FeegowSyncService.create_booking e
    # ana_feegow.services.retorno_service).
    "consulta_retorno": {
        "procedimento_id": 35,
        "valor": 0,
        "duracao": 30,
    },

    # Consulta de retorno online (sem cobrança, por Google Meet) - evento
    # dedicado no Cal.com (drathalita/consulta-retorno-online). Mesmo
    # procedimento/valor da consulta de retorno presencial (retorno=True,
    # valor=0 - ver FeegowSyncService.create_booking), sinalizada como
    # telemedicina via prefixo na nota do agendamento, já que a API do
    # Feegow não persiste um campo "telemedicina" (ver
    # ana_feegow.services.agendamento_service.agendar_consulta).
    "consulta_retorno_online": {
        "procedimento_id": 35,
        "valor": 0,
        "duracao": 30,
    },

}
