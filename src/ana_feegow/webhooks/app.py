import hashlib
import hmac
import json
import os

from fastapi import FastAPI, Header, HTTPException, Request

from ana_feegow.webhooks.feegow_sync_service import FeegowSyncService
from ana_feegow.webhooks.sync_handler import SyncHandler
from ana_feegow.webhooks.sync_store import SyncStore


def _default_handler():
    db_path = os.getenv(
        "CAL_FEEGOW_DB_PATH",
        "/opt/data/workspace/hermes-feegow-mcp/data/cal_feegow_sync.db",
    )
    return SyncHandler(SyncStore(db_path), FeegowSyncService())


def create_app(handler=None, secret=None):
    api = FastAPI(title="Cal.com → Feegow")

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
            result = (handler or _default_handler()).handle(envelope)
            return result
        except (ValueError, LookupError) as exc:
            raise HTTPException(422, str(exc)) from exc
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "JSON inválido") from exc

    return api


app = create_app()
