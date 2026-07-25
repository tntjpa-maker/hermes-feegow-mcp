import hashlib
import json

from ana_feegow.webhooks.cal_parser import CalBooking

RESERVA_INDISPONIVEL_PARA_PAGAMENTO = {"CANCELED", "EXPIRED", "REPLACED"}


class PagBankHandler:
    def __init__(self, store, service, payment_client=None):
        self.store = store
        self.service = service
        self.payment_client = payment_client

    @staticmethod
    def event_key(payload: dict) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "pagbank:" + hashlib.sha256(canonical.encode()).hexdigest()

    @staticmethod
    def payment_status(payload: dict) -> str:
        charges = payload.get("charges") or []
        for charge in charges:
            if str(charge.get("status", "")).upper() == "PAID":
                return "PAID"
        return str(payload.get("status") or "").upper()

    @staticmethod
    def reference_id(payload: dict) -> str:
        return str(
            payload.get("reference_id")
            or (payload.get("checkout") or {}).get("reference_id")
            or (payload.get("order") or {}).get("reference_id")
            or ""
        )

    @staticmethod
    def charge_id(payload: dict) -> str:
        charges = payload.get("charges") or []
        if charges:
            return str(charges[0].get("id") or "")
        return str(payload.get("id") or "")

    def _reconfirmar_via_api(self, payload: dict) -> dict:
        # O header x-authenticity-token não veio nessa notificação (bug
        # conhecido do PagBank Sandbox, sem correção oficial documentada).
        # Em vez de confiar no corpo recebido, buscamos o pedido direto na
        # API do PagBank com o nosso próprio token - só aceitamos o status
        # que o PagBank realmente confirmar dessa forma.
        if not self.payment_client:
            raise ValueError(
                "Notificação PagBank sem assinatura e sem cliente para reconfirmar."
            )
        order_id = str(payload.get("id") or "")
        if not order_id:
            raise ValueError(
                "Notificação PagBank sem assinatura e sem id de pedido para reconfirmar."
            )
        pedido = self.payment_client.consultar_pedido(order_id)
        if str(pedido.get("id") or "") != order_id:
            raise ValueError(
                "Reconfirmação do PagBank não corresponde ao pedido notificado."
            )
        return pedido

    def handle(self, payload: dict, assinatura_confiavel: bool = True):
        if not assinatura_confiavel:
            payload = self._reconfirmar_via_api(payload)

        key = self.event_key(payload)
        uid = self.reference_id(payload)
        status = self.payment_status(payload)

        if self.store.event_processed(key):
            return {"status": "duplicate", "payment_status": status, "uid": uid}

        if not uid:
            raise ValueError("reference_id ausente na notificação PagBank.")

        pending = self.store.get_pending_booking(uid)
        if status != "PAID":
            if pending:
                self.store.update_pending_status(uid, status or "UNKNOWN")
            self.store.mark_event(key, f"PAGBANK_{status or 'UNKNOWN'}", uid)
            return {"status": "recorded", "payment_status": status, "uid": uid}

        mapping = self.store.get_mapping(uid)
        if mapping:
            self.store.update_pending_status(uid, "PAID")
            self.store.mark_event(key, "PAGBANK_PAID", uid)
            return {"status": "duplicate", "payment_status": status, "uid": uid}

        if not pending:
            raise LookupError("Pagamento sem reserva Cal.com pendente.")

        if pending["payment_status"] in RESERVA_INDISPONIVEL_PARA_PAGAMENTO:
            self.store.mark_event(key, "PAGBANK_PAID_APOS_CANCELAMENTO", uid)
            return {
                "status": "revisao_manual",
                "payment_status": status,
                "uid": uid,
                "motivo": (
                    f"reserva estava '{pending['payment_status']}' "
                    "quando o pagamento chegou"
                ),
            }

        booking = CalBooking(**pending["booking"])
        appointment_id = self.service.create_booking(booking)
        self.store.save_mapping(
            booking.uid,
            booking.booking_id,
            appointment_id,
            "scheduled",
            pagbank_transaction_id=self.charge_id(payload),
        )
        self.store.update_pending_status(uid, "PAID")
        self.store.mark_event(key, "PAGBANK_PAID", uid)
        return {
            "status": "processed",
            "payment_status": status,
            "uid": uid,
            "feegow_appointment_id": appointment_id,
        }
