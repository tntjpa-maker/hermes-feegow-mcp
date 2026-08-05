import logging

from ana_feegow.services import twenty_service

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
        twenty_service.registrar_perdido(
            pending["booking"].get("opportunity_id", ""),
            "PAGAMENTO_EXPIRADO",
        )
        logger.info("Reserva %s expirou sem pagamento e foi cancelada no Cal.com.", uid)
        processadas.append({"uid": uid, "status": "expirado"})

    return processadas


def concluir_atendimentos_realizados(buffer_horas: int = 2):
    """Varre oportunidades no estagio 'Agendado e pago' cujo horario da
    consulta ja passou (com uma margem de `buffer_horas`) e marca cada uma
    como 'Atendimento realizado' no Twenty. Retorna a lista do que foi
    processado, para log."""
    processadas = []
    for oportunidade in twenty_service.listar_oportunidades_para_concluir(buffer_horas):
        opportunity_id = oportunidade.get("id")
        if not opportunity_id:
            continue
        twenty_service.registrar_atendimento_realizado(opportunity_id)
        processadas.append({"opportunity_id": opportunity_id, "status": "concluido"})
    return processadas



def checkpoint_link_enviado(minutos: int = 60):
    """Checkpoint de recuperacao 'Link enviado': varre oportunidades no
    estagio 'Link de agendamento enviado' paradas ha mais de `minutos` e cria
    uma Task de follow-up manual no Twenty para cada uma que ainda nao tem
    follow-up registrado (evita duplicar a mesma task a cada varredura). Nao
    envia nenhuma mensagem para a paciente - apenas cria a task para a equipe
    humana agir manualmente. Retorna a lista do que foi processado, para log.
    """
    processadas = []
    for oportunidade in twenty_service.listar_oportunidades_link_enviado_para_followup(
        minutos
    ):
        opportunity_id = oportunidade.get("id")
        if not opportunity_id:
            continue
        servico = oportunidade.get("serviceOfInterest") or "consulta"
        titulo = (
            f"Follow-up manual: {servico} parado ha {minutos}min em "
            "Link de agendamento enviado"
        )
        twenty_service.criar_task_followup(
            opportunity_id,
            titulo,
            "Lead recebeu o link de agendamento e ainda nao reservou um "
            "horario. Considere um contato manual para recuperar o "
            "atendimento.",
        )
        processadas.append({"opportunity_id": opportunity_id, "status": "followup_criado"})
    return processadas


def checkpoint_reserva_pendente(minutos_antes_expirar: int = 10):
    """Checkpoint de recuperacao 'Reserva pendente': varre oportunidades no
    estagio 'Reserva aguardando pagamento' cujo prazo de pagamento esta a
    `minutos_antes_expirar` minutos (ou menos) de expirar e cria uma Task de
    follow-up manual no Twenty para cada uma que ainda nao tem follow-up
    registrado. Nao envia nenhuma mensagem para a paciente. Retorna a lista do
    que foi processado, para log.
    """
    processadas = []
    for oportunidade in twenty_service.listar_oportunidades_reserva_pendente_para_followup(
        minutos_antes_expirar
    ):
        opportunity_id = oportunidade.get("id")
        if not opportunity_id:
            continue
        servico = oportunidade.get("serviceOfInterest") or "consulta"
        titulo = (
            f"Follow-up manual: {servico} com reserva aguardando pagamento "
            "perto de expirar"
        )
        twenty_service.criar_task_followup(
            opportunity_id,
            titulo,
            "Lead reservou um horario mas ainda nao concluiu o pagamento do "
            "sinal. Considere um contato manual antes que a reserva expire "
            "automaticamente.",
            campo_controle="followUpReservaCriadoEm",
        )
        processadas.append({"opportunity_id": opportunity_id, "status": "followup_criado"})
    return processadas
