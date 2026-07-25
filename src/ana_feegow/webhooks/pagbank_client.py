import logging
import os
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

from ana_feegow.settings.services import SERVICES

logger = logging.getLogger("webhooks")


@dataclass(frozen=True)
class PagBankCheckout:
    checkout_id: str
    payment_url: str


def _valor_sinal_centavos(tipo_consulta: str) -> int:
    if tipo_consulta not in SERVICES:
        raise ValueError(f"Tipo de consulta desconhecido: {tipo_consulta}")
    # Sinal = 20% do valor da consulta (regra confirmada no doc 14_Lacunas,
    # perguntas 30-31: sinal é só sobre consulta, não sobre procedimento/pacote).
    return round(SERVICES[tipo_consulta]["valor"] * 0.20)


class PagBankClient:
    def __init__(
        self,
        token=None,
        base_url=None,
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

    @staticmethod
    def _cpf_valido(cpf: str) -> bool:
        # Valida os dígitos verificadores reais do CPF (algoritmo padrão).
        # O PagBank rejeita CPFs "de brincadeira" (ex.: 11233223423) mesmo
        # que tenham 11 dígitos - por isso checamos isso antes de chamar a
        # API deles, em vez de deixar o erro estourar como HTTP 400 lá.
        digits = "".join(filter(str.isdigit, cpf or ""))
        if len(digits) != 11 or digits == digits[0] * 11:
            return False
        for pos in (9, 10):
            soma = sum(
                int(digits[num]) * ((pos + 1) - num) for num in range(0, pos)
            )
            digito = ((soma * 10) % 11) % 10
            if digito != int(digits[pos]):
                return False
        return True

    def create_checkout(self, booking) -> PagBankCheckout:
        if len(booking.uid) > 64:
            raise ValueError("UID do Cal.com excede 64 caracteres.")
        if not self._cpf_valido(booking.cpf):
            raise ValueError("CPF inválido para o checkout PagBank.")

        valor_sinal_centavos = _valor_sinal_centavos(booking.tipo_consulta)

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
                    "name": "Sinal de reserva - Clínica Magnólia",
                    "quantity": 1,
                    "unit_amount": valor_sinal_centavos,
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
            # Guarda o motivo real da recusa só no nosso log privado do
            # servidor (truncado, nunca devolvido ao Cal.com/paciente).
            corpo = (getattr(response, "text", "") or "")[:500]
            logger.error(
                "PagBank recusou o checkout: HTTP %s - %s",
                response.status_code,
                corpo,
            )
            raise RuntimeError(
                f"Falha ao criar checkout PagBank: HTTP {response.status_code} - {corpo}"
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

    def consultar_pedido(self, order_id: str) -> dict:
        # Reconfirma o status de um pedido direto na API do PagBank, com o
        # nosso próprio token - usado quando a notificação webhook chega sem
        # o header x-authenticity-token (bug conhecido do PagBank Sandbox,
        # sem correção oficial documentada) e por isso não pode ser
        # confiada apenas pelo corpo recebido.
        response = self.session.get(
            f"{self.base_url}/orders/{order_id}",
            headers=self.headers,
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            corpo = (getattr(response, "text", "") or "")[:500]
            logger.error(
                "PagBank recusou a consulta do pedido %s: HTTP %s - %s",
                order_id,
                response.status_code,
                corpo,
            )
            raise RuntimeError(
                f"Falha ao consultar pedido PagBank: HTTP {response.status_code} - {corpo}"
            )
        return response.json()
