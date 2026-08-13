CLINIC = {
    "local_id": 1,
    "profissional_id": 1,
    "sys_user": 173286780,
    "especialidade_id": 271,

    "canal_id": 10,
    "convenio_id": 1,
    "tabela_id": 0,

    "plano": 0,

    "retorno_dias": 30,

    # Slugs (relativos a CALCOM_BASE_URL) dos eventos do Cal.com usados para
    # direcionar o paciente durante a conversa com a ANA quando ele pede um
    # retorno. Ver ana_feegow.services.retorno_service.
    "calcom_slug_retorno": "drathalita/consulta-retorno",
    "calcom_slug_presencial": "drathalita/niteroi",
    "calcom_slug_online": "drathalita/consulta-online",
    "calcom_slug_retorno_online": "drathalita/consulta-retorno-online",
    # Consulta hibrida (pacote com uma consulta presencial + uma
    # consulta online, pelo mesmo valor da presencial). Ver
    # ana_feegow.ana.dialog para o fluxo completo.
    "calcom_slug_hibrida_presencial": "drathalita/hibridapresencial",
    "calcom_slug_hibrida_online": "drathalita/hibridaonline",
}
