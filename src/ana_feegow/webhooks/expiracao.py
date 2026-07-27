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

        # Reconfere o status bem antes de cancelar - protege contra a
        # corrida rara em que o pagamento chega entre a consulta acima e
        # este ponto (ex.: paciente pagou no último segundo do prazo).
        atual = store.get_pending_booking(uid)
        if not atual or atual["payment_status"] != "WAITING":
            continue

        try:
            calcom_client.cancelar_reserva(uid, motivo)
            store.update_pending_status(uid, "EXPIRED")
            logger.info("Reserva %s expirou sem pagamento e foi cancelada no Cal.com.", uid)
            processadas.append({"uid": uid, "status": "expirado"})
        except Exception as exc:  # noqa: BLE001 - queremos seguir para as próximas mesmo se uma falhar
            logger.error("Falha ao expirar/cancelar a reserva %s: %s", uid, exc)
            processadas.append({"uid": uid, "status": "falha", "erro": str(exc)})

    return processadas
