import hashlib
import json
import logging

from ana_feegow.webhooks.cal_parser import parse_booking
from ana_feegow.services import twenty_service

logger = logging.getLogger("webhooks")


class SyncHandler:
    def __init__(
        self,
        store,
        service,
        payment_service=None,
        calcom_client=None,
        email_client=None,
    ):
        self.store = store
        self.service = service
        self.payment_service = payment_service
        self.calcom_client = calcom_client
        self.email_client = email_client

    @staticmethod
    def event_key(envelope: dict) -> str:
        canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _create_checkout(self, booking):
        if self.payment_service is None:
            raise RuntimeError("Serviço de pagamento PagBank não configurado.")
        checkout = self.payment_service.create_checkout(booking)
        self.store.save_pending_booking(
            booking,
            checkout.checkout_id,
            checkout.payment_url,
        )
        twenty_service.registrar_reserva_aguardando_pagamento(booking.opportunity_id)
        return checkout

    def _cancelar_reserva_com_dados_invalidos(self, uid, exc):
        # O Cal.com já reserva o horário na agenda antes de nos avisar via
        # webhook. Se os dados da paciente forem inválidos (CPF, celular,
        # data de nascimento etc.) e recusarmos a reserva aqui, sem isso o
        # horário fica preso ocupando a agenda pra sempre, sem aparecer em
        # lugar nenhum pra paciente tentar de novo ou pra clínica perceber.
        if not uid:
            logger.error(
                "Reserva com dados inválidos (%s) não pôde ser cancelada no "
                "Cal.com: uid ausente no webhook.",
                exc,
            )
            return
        if self.calcom_client is None:
            logger.warning(
                "Reserva %s tem dados inválidos (%s) mas não foi cancelada no "
                "Cal.com: CALCOM_BASE_URL não configurada. Cancele manualmente.",
                uid,
                exc,
            )
            return
        try:
            self.calcom_client.cancelar_reserva(
                uid, motivo=f"Dados inválidos no agendamento: {exc}"
            )
            logger.info(
                "Reserva %s cancelada automaticamente no Cal.com (dados "
                "inválidos: %s).",
                uid,
                exc,
            )
        except Exception as cancel_exc:  # noqa: BLE001 - não pode mascarar o erro original
            logger.error(
                "Reserva %s tem dados inválidos (%s) e o cancelamento "
                "automático no Cal.com também falhou: %s - cancele manualmente.",
                uid,
                exc,
                cancel_exc,
            )

    def _notificar_remarcacao(self, booking):
        # Avisa a paciente do novo horário. Só roda depois que a remarcação
        # já foi confirmada no Cal.com e no Feegow (o que importa de
        # verdade já aconteceu), então falha aqui nunca pode derrubar o
        # processamento do webhook - só é logada.
        if self.email_client is None:
            return
        try:
            self.email_client.enviar_confirmacao_remarcacao(booking)
        except Exception as exc:  # noqa: BLE001 - notificação não pode derrubar o webhook
            logger.error(
                "Falha ao enviar e-mail de remarcação (uid=%s): %s", booking.uid, exc
            )

    def _notificar_cancelamento(self, envelope):
        # Mesma lógica do cancelamento: reconstrói os dados da paciente a
        # partir do payload do próprio webhook (o BOOKING_CANCELLED do
        # Cal.com traz a mesma estrutura de responses/attendees/startTime
        # que o BOOKING_CREATED) só para montar o e-mail. Se o payload
        # vier incompleto, avisa no log e segue sem quebrar o cancelamento
        # em si, que já foi concluído antes dessa chamada.
        if self.email_client is None:
            return
        try:
            booking = parse_booking(envelope)
        except ValueError as exc:
            logger.warning(
                "Não foi possível montar o e-mail de cancelamento (dados da "
                "paciente incompletos no webhook): %s",
                exc,
            )
            return
        try:
            self.email_client.enviar_confirmacao_cancelamento(booking)
        except Exception as exc:  # noqa: BLE001 - notificação não pode derrubar o webhook
            logger.error(
                "Falha ao enviar e-mail de cancelamento (uid=%s): %s", booking.uid, exc
            )

    def handle(self, envelope: dict):
        trigger = envelope.get("triggerEvent")
        if trigger not in {
            "BOOKING_CREATED",
            "BOOKING_PAID",
            "BOOKING_RESCHEDULED",
            "BOOKING_CANCELLED",
        }:
            return {"status": "ignored", "trigger": trigger}

        payload = envelope.get("payload") or {}
        uid = str(payload.get("uid") or "")
        key = self.event_key(envelope)
        if self.store.event_processed(key):
            return {"status": "duplicate", "trigger": trigger, "uid": uid}

        response = {"status": "processed", "trigger": trigger, "uid": uid}

        if trigger == "BOOKING_CREATED":
            try:
                booking = parse_booking(envelope)

                # Consulta de retorno, presencial ou online (eventos
                # dedicados no Cal.com, sem cobrança): não passa pelo fluxo
                # de checkout do PagBank, registra direto no Feegow assim
                # que a reserva é criada.
                if booking.tipo_consulta in (
                    "consulta_retorno",
                    "consulta_retorno_online",
                ):
                    existing_mapping = self.store.get_mapping(booking.uid)
                    if existing_mapping:
                        self.store.mark_event(key, trigger, booking.uid)
                        return {
                            "status": "duplicate",
                            "trigger": trigger,
                            "uid": booking.uid,
                        }
                    appointment_id = self.service.create_booking(booking)
                    self.store.save_mapping(
                        booking.uid,
                        booking.booking_id,
                        appointment_id,
                        "scheduled",
                    )
                else:
                    existing = self.store.get_pending_booking(booking.uid)
                    if existing:
                        self.store.mark_event(key, trigger, booking.uid)
                        return {
                            "status": "duplicate",
                            "trigger": trigger,
                            "uid": booking.uid,
                            "payment_url": existing["payment_url"],
                        }
                    checkout = self._create_checkout(booking)
                    response["payment_url"] = checkout.payment_url
            except ValueError as exc:
                self._cancelar_reserva_com_dados_invalidos(uid, exc)
                raise

        elif trigger == "BOOKING_PAID":
            booking = parse_booking(envelope)
            existing = self.store.get_mapping(booking.uid)
            if existing:
                self.store.mark_event(key, trigger, booking.uid)
                return {"status": "duplicate", "trigger": trigger, "uid": booking.uid}
            appointment_id = self.service.create_booking(booking)
            self.store.save_mapping(
                booking.uid,
                booking.booking_id,
                appointment_id,
                "scheduled",
            )

        elif trigger == "BOOKING_RESCHEDULED":
            previous_uid = str(
                payload.get("rescheduleUid")
                or payload.get("rescheduledFromUid")
                or payload.get("previousBookingUid")
                or ""
            )
            try:
                booking = parse_booking(envelope)
                mapping = self.store.get_mapping(booking.uid, previous_uid)
                if mapping:
                    self.service.reschedule_booking(
                        mapping["feegow_appointment_id"],
                        booking,
                    )
                    self.store.save_mapping(
                        booking.uid,
                        booking.booking_id,
                        mapping["feegow_appointment_id"],
                        "rescheduled",
                    )
                    # O Cal.com costuma gerar um uid novo a cada remarcação.
                    # Sem marcar o registro antigo, ele fica órfão no banco
                    # com o status velho (ex.: "scheduled") para sempre.
                    if mapping["cal_uid"] != booking.uid:
                        self.store.update_status(mapping["cal_uid"], "substituido")
                    self._notificar_remarcacao(booking)
                else:
                    pending = self.store.get_pending_booking(previous_uid or booking.uid)
                    if not pending:
                        raise LookupError("Reserva Cal.com sem vínculo com o Feegow.")
                    checkout = self._create_checkout(booking)
                    if previous_uid and previous_uid != booking.uid:
                        self.store.update_pending_status(previous_uid, "REPLACED")
                    response["payment_url"] = checkout.payment_url
            except ValueError as exc:
                self._cancelar_reserva_com_dados_invalidos(uid, exc)
                raise

        else:
            related_uid = str(payload.get("rescheduleUid") or "")
            mapping = self.store.get_mapping(uid, related_uid)
            if mapping:
                self.service.cancel_booking(mapping["feegow_appointment_id"])
                self.store.update_status(mapping["cal_uid"], "cancelled")
                self._notificar_cancelamento(envelope)
                pending_para_opp = self.store.get_pending_booking(mapping["cal_uid"])
                if pending_para_opp:
                    twenty_service.registrar_perdido(
                        pending_para_opp["booking"].get("opportunity_id", ""),
                        "CANCELAMENTO_PACIENTE",
                    )
            else:
                pending_uid = uid or related_uid
                pending = self.store.get_pending_booking(pending_uid)
                if not pending:
                    raise LookupError("Reserva Cal.com sem vínculo com o Feegow.")
                # Reivindica atomicamente antes de marcar como cancelada -
                # se o pagamento estiver sendo confirmado nesse exato
                # momento (self.store.claim_pending_status em
                # PagBankHandler), não sobrescrevemos o resultado dele.
                twenty_service.registrar_perdido(
                    pending["booking"].get("opportunity_id", ""),
                    "CANCELAMENTO_PACIENTE",
                )

                if not self.store.claim_pending_status(
                    pending_uid, pending["payment_status"], "CANCELED"
                ):
                    logger.warning(
                        "Cancelamento do Cal.com para %s chegou junto com uma "
                        "confirmação de pagamento em andamento - não marquei "
                        "como cancelada. Confira manualmente.",
                        pending_uid,
                    )

        self.store.mark_event(key, trigger, uid)
        return response
