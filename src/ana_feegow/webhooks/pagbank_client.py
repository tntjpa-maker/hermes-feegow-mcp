import os
from dataclasses import dataclass
from urllib.parse import urlencode

import requests


@dataclass(frozen=True)
class PagBankCheckout:
    checkout_id: str
    payment_url: str


class PagBankClient:
    def __init__(
        self,
        token=None,
        base_url=None,
        amount=None,
        webhook_url=None,
        public_base_url=None,
        timeout=20,
        session=None,
    ):
        self.token = token or os.getenv("PAGBANK_TOKEN", "")
        self.base_url = (
            base_url
            or os.getenv("PAGBANK_BASE_URL", "https://sandbox.api.pagseguro.com")
        ).rstrip("/")
        self.amount = int(amount or os.getenv("PAGBANK_DEFAULT_AMOUNT", "100"))
        self.webhook_url = webhook_url or os.getenv("PAGBANK_WEBHOOK_URL", "")
        self.public_base_url = (
            public_base_url
            or os.getenv("PUBLIC_BASE_URL", "")
            or self.webhook_url.removesuffix("/webhooks/pagbank")
        ).rstrip("/")
        self.timeout = timeout
        self.session = session or requests

        if not self.token:
            raise RuntimeError("PAGBANK_TOKEN não configurado.")
        if not self.webhook_url:
            raise RuntimeError("PAGBANK_WEBHOOK_URL não configurada.")
        if not self.public_base_url:
            raise RuntimeError("PUBLIC_BASE_URL não configurada.")
        if self.amount <= 0:
            raise ValueError("PAGBANK_DEFAULT_AMOUNT deve ser maior que zero.")

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _phone(celular: str):
        digits = "".join(filter(str.isdigit, celular or ""))
        if len(digits) in (12, 13) and digits.startswith("55"):
            digits = digits[2:]
        if len(digits) not in (10, 11):
            raise ValueError("Celular inválido para o checkout PagBank.")
        return {
            "country": "+55",
            "area": digits[:2],
            "number": digits[2:],
        }

    def create_checkout(self, booking) -> PagBankCheckout:
        if len(booking.uid) > 64:
            raise ValueError("UID do Cal.com excede 64 caracteres.")

        return_query = urlencode({"uid": booking.uid})
        return_url = f"{self.public_base_url}/pagamento/retorno?{return_query}"
        payload = {
            "reference_id": booking.uid,
            "customer": {
                "name": booking.nome,
                "email": booking.email,
                "tax_id": booking.cpf,
                "phone": self._phone(booking.celular),
            },
            "customer_modifiable": False,
            "items": [
                {
                    "reference_id": booking.tipo_consulta,
                    "name": "Consulta Clínica Magnólia",
                    "quantity": 1,
                    "unit_amount": self.amount,
                }
            ],
            "redirect_url": return_url,
            "return_url": return_url,
            "redirect_waiting_time": 5,
            "notification_urls": [self.webhook_url],
            "payment_notification_urls": [self.webhook_url],
        }

        response = self.session.post(
            f"{self.base_url}/checkouts",
            headers=self.headers,
            json=payload,
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Falha ao criar checkout PagBank: HTTP {response.status_code}"
            )

        data = response.json()
        payment_url = next(
            (
                link.get("href")
                for link in data.get("links", [])
                if str(link.get("rel", "")).upper() == "PAY"
            ),
            None,
        )
        checkout_id = str(data.get("id") or "")
        if not checkout_id or not payment_url:
            raise RuntimeError("PagBank não retornou checkout_id e link PAY.")

        return PagBankCheckout(
            checkout_id=checkout_id,
            payment_url=str(payment_url),
        )
