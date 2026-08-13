import logging

import requests

from ana_feegow.config import settings

logger = logging.getLogger("webhooks")


class CalComClient:
    """Cliente mínimo para cancelar reservas no Cal.com sem precisar de API
    key (recurso pago no self-hosted). Usa o mesmo endpoint público que a
    própria página de cancelamento do paciente usa (/api/cancel), que só
    exige um csrfToken de sessão anônima - confirmado inspecionando a
    chamada real feita pelo navegador ao clicar em "Cancelar este evento"
    na página pública de uma reserva.
    """

    def __init__(self, base_url=None, session=None, timeout=30):
        self.base_url = (base_url or settings.CALCOM_BASE_URL).rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout
        if not self.base_url:
            raise RuntimeError("CALCOM_BASE_URL não configurada.")

    def cancelar_reserva(self, uid: str, motivo: str) -> None:
        csrf_response = self.session.get(f"{self.base_url}/api/csrf", timeout=self.timeout)
        if csrf_response.status_code >= 400:
            raise RuntimeError(
                f"Falha ao obter csrfToken do Cal.com: HTTP {csrf_response.status_code}"
            )
        csrf_token = (csrf_response.json() or {}).get("csrfToken")
        if not csrf_token:
            raise RuntimeError("Cal.com não retornou csrfToken.")

        payload = {
            "csrfToken": csrf_token,
            "uid": uid,
            "cancellationReason": motivo,
            "allRemainingBookings": False,
        }
        response = self.session.post(
            f"{self.base_url}/api/cancel",
            json=payload,
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            corpo = (getattr(response, "text", "") or "")[:500]
            logger.error(
                "Cal.com recusou o cancelamento da reserva %s: HTTP %s - %s",
                uid,
                response.status_code,
                corpo,
            )
            raise RuntimeError(
                f"Falha ao cancelar reserva no Cal.com: HTTP {response.status_code} - {corpo}"
            )
