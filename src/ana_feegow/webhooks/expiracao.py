import logging

logger = logging.getLogger("webhooks")

MOTIVO_PADRAO = "Sinal não pago dentro do prazo de 30 minutos."


def expirar_reservas_pendentes(store, calcom_client, minutos: int = 30, motivo: str = None):
    """Varre pending_bookings por reservas 'WAITING' há mais de `minutos`
    minutos, cancela cada uma no Cal.com (liberando o horário) e marca como
    EXPIRED no nosso banco. Retorna a lista do que foi processado, para log.
    """
    motivo = motivo or MOTIVO_PADRAO
    processadas = []
    for pending in store.list_pending_expirados(minutos):
        uid = pending["cal_uid"]

        # Reivindica a reserva atomicamente antes de mexer no Cal.com -
        # protege contra a corrida em que o pagamento é confirmado entre a
        # varredura acima e este ponto (ex.: paciente pagou no último
        # segundo do prazo). Se outra rotina (a confirmação do PagBank) já
        # tiver tirado a reserva do estado "WAITING", perdemos a corrida e
        # desistimos sem cancelar nada - inclusive se isso acontecer só
        # depois que a chamada ao Cal.com já tiver começado, porque
        # store.update_pending_status nunca é chamado sem essa reivindicação
        # ter sido bem-sucedida primeiro.
        if not store.claim_pending_status(uid, "WAITING", "EXPIRING"):
            continue

        try:
            calcom_client.cancelar_reserva(uid, motivo)
        except Exception as exc:  # noqa: BLE001 - queremos seguir para as próximas mesmo se uma falhar
            # Devolve a reserva pro estado WAITING pra que a próxima
            # varredura tente de novo (ou o pagamento ainda consiga passar).
            store.update_pending_status(uid, "WAITING")
            logger.error("Falha ao expirar/cancelar a reserva %s: %s", uid, exc)
            processadas.append({"uid": uid, "status": "falha", "erro": str(exc)})
            continue

        store.update_pending_status(uid, "EXPIRED")
        logger.info("Reserva %s expirou sem pagamento e foi cancelada no Cal.com.", uid)
        processadas.append({"uid": uid, "status": "expirado"})

    return processadas
