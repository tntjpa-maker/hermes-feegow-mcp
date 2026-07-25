import hashlib
import hmac
import json
import logging
import os
import time

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ana_feegow.webhooks.feegow_sync_service import FeegowSyncService
from ana_feegow.webhooks.pagbank_client import PagBankClient
from ana_feegow.webhooks.pagbank_handler import PagBankHandler
from ana_feegow.webhooks.sync_handler import SyncHandler
from ana_feegow.webhooks.sync_store import SyncStore

logger = logging.getLogger("webhooks")

ESPERA_TENTATIVAS = 6
ESPERA_INTERVALO_SEGUNDOS = 0.5


def _db_path():
    return os.getenv(
        "CAL_FEEGOW_DB_PATH",
        "/opt/data/workspace/hermes-feegow-mcp/data/cal_feegow_sync.db",
    )


def _default_store():
    return SyncStore(_db_path())


def _default_handler():
    return SyncHandler(
        _default_store(),
        FeegowSyncService(),
        PagBankClient(),
    )


def _default_pagbank_handler():
    return PagBankHandler(
        _default_store(),
        FeegowSyncService(),
        PagBankClient(),
    )


def create_app(
    handler=None,
    secret=None,
    pagbank_handler=None,
    pagbank_token=None,
    store=None,
):
    api = FastAPI(title="Cal.com → PagBank → Feegow")

    @api.get("/health")
    def health():
        return {"status": "ok", "service": "cal-feegow-webhooks"}

    @api.post("/webhooks/calcom")
    async def calcom_webhook(
        request: Request,
        x_cal_signature_256: str | None = Header(default=None),
    ):
        raw = await request.body()
        configured_secret = secret or os.getenv("CALCOM_WEBHOOK_SECRET", "")
        if not configured_secret:
            raise HTTPException(503, "Segredo do webhook não configurado")
        if not x_cal_signature_256:
            raise HTTPException(401, "Assinatura ausente")

        expected = hmac.new(
            configured_secret.encode(),
            raw,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, x_cal_signature_256):
            raise HTTPException(401, "Assinatura inválida")

        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "JSON inválido") from exc

        try:
            result = (handler or _default_handler()).handle(envelope)
            logger.info("Webhook Cal.com processado: %s", result)
            return result
        except (ValueError, LookupError) as exc:
            logger.warning("Webhook Cal.com rejeitado (422): %s", exc)
            raise HTTPException(422, str(exc)) from exc
        except RuntimeError as exc:
            logger.error("Webhook Cal.com falhou (502): %s", exc)
            raise HTTPException(502, "Falha ao processar pagamento, tente novamente") from exc

    @api.post("/webhooks/pagbank")
    async def pagbank_webhook(
        request: Request,
        x_authenticity_token: str | None = Header(default=None),
    ):
        raw = await request.body()
        configured_token = pagbank_token or os.getenv("PAGBANK_TOKEN", "")
        if not configured_token:
            raise HTTPException(503, "Token PagBank não configurado")

        # O PagBank tem um problema conhecido (relatado por outros
        # integradores, sem correção oficial documentada) de às vezes não
        # enviar o header x-authenticity-token em notificações de Sandbox.
        # Se o header vier e não bater, é sinal de adulteração - rejeitamos
        # na hora. Se o header simplesmente não vier, não confiamos direto
        # no corpo: o handler vai reconfirmar o status direto na API do
        # PagBank (com o nosso token) antes de aceitar qualquer pagamento.
        assinatura_confiavel = False
        if x_authenticity_token:
            expected = hashlib.sha256(
                configured_token.encode() + b"-" + raw
            ).hexdigest()
            if hmac.compare_digest(expected, x_authenticity_token):
                assinatura_confiavel = True
            else:
                logger.warning(
                    "Webhook PagBank rejeitado (401): assinatura não bateu. "
                    "corpo=%s bytes, esperado[:8]=%s, recebido[:8]=%s",
                    len(raw),
                    expected[:8],
                    x_authenticity_token[:8],
                )
                raise HTTPException(401, "Assinatura PagBank inválida")
        else:
            logger.warning(
                "Webhook PagBank sem header x-authenticity-token (bug conhecido "
                "do PagBank Sandbox) - reconfirmando direto na API do PagBank "
                "antes de aceitar. corpo=%s bytes, headers recebidos=%s",
                len(raw),
                sorted(request.headers.keys()),
            )

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "JSON inválido") from exc

        try:
            result = (pagbank_handler or _default_pagbank_handler()).handle(
                payload, assinatura_confiavel=assinatura_confiavel
            )
            logger.info("Webhook PagBank processado: %s", result)
            return result
        except (ValueError, LookupError) as exc:
            logger.warning("Webhook PagBank rejeitado (422): %s", exc)
            raise HTTPException(422, str(exc)) from exc
        except RuntimeError as exc:
            logger.error("Webhook PagBank falhou (502): %s", exc)
            raise HTTPException(502, "Falha ao confirmar pagamento, tente novamente") from exc

    @api.get("/pagamento/iniciar")
    def iniciar_pagamento(uid: str = Query(min_length=1)):
        selected_store = store or _default_store()

        pending = None
        for tentativa in range(ESPERA_TENTATIVAS):
            pending = selected_store.get_pending_booking(uid)
            if pending:
                break
            time.sleep(ESPERA_INTERVALO_SEGUNDOS)

        if not pending:
            logger.warning(
                "pagamento/iniciar: reserva %s não encontrada após %s tentativas",
                uid,
                ESPERA_TENTATIVAS,
            )
            raise HTTPException(404, "Reserva pendente não encontrada")
        if pending["payment_status"] in {"CANCELED", "EXPIRED", "REPLACED"}:
            raise HTTPException(409, "Esta reserva não aceita mais pagamento")
        return RedirectResponse(pending["payment_url"], status_code=307)

    @api.get("/pagamento/retorno", response_class=HTMLResponse)
    def retorno_pagamento():
        return """
        <!doctype html>
        <html lang="pt-BR">
          <head><meta charset="utf-8"><title>Pagamento recebido</title></head>
          <body style="font-family: sans-serif; max-width: 640px; margin: 64px auto; padding: 24px;">
            <h1>Pagamento enviado para confirmação</h1>
            <p>Assim que o PagBank confirmar o pagamento, sua consulta será registrada no sistema da clínica.</p>
            <p>Você receberá a confirmação pelos canais informados no agendamento.</p>
          </body>
        </html>
        """

    return api


app = create_app()
