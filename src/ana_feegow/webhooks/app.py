import asyncio
import contextlib
import hashlib
import hmac
import json
import logging
import os
import time

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ana_feegow.webhooks.calcom_client import CalComClient
from ana_feegow.webhooks.expiracao import expirar_reservas_pendentes
from ana_feegow.config import settings
from ana_feegow.webhooks.email_client import EmailClient
from ana_feegow.webhooks.feegow_sync_service import FeegowSyncService
from ana_feegow.webhooks.pagbank_client import PagBankClient
from ana_feegow.webhooks.pagbank_handler import (
    RESERVA_INDISPONIVEL_PARA_PAGAMENTO,
    PagBankHandler,
)
from ana_feegow.webhooks.sync_handler import SyncHandler
from ana_feegow.webhooks.sync_store import SyncStore

logger = logging.getLogger("webhooks")

ESPERA_TENTATIVAS = 6
ESPERA_INTERVALO_SEGUNDOS = 0.5

RESERVA_EXPIRA_MINUTOS_PADRAO = 30
RESERVA_EXPIRA_INTERVALO_SEGUNDOS_PADRAO = 60


def _expira_minutos():
    return int(os.getenv("RESERVA_EXPIRA_MINUTOS", str(RESERVA_EXPIRA_MINUTOS_PADRAO)))


def _expira_intervalo_segundos():
    return int(
        os.getenv(
            "RESERVA_EXPIRA_INTERVALO_SEGUNDOS",
            str(RESERVA_EXPIRA_INTERVALO_SEGUNDOS_PADRAO),
        )
    )


async def _loop_expiracao_reservas(selected_store):
    # Libera automaticamente o horário no Cal.com quando o paciente não paga
    # o sinal dentro do prazo. Fica completamente desativado (só um aviso no
    # log) se CALCOM_BASE_URL não estiver configurada, para não quebrar
    # ambientes/testes que não precisam dessa funcionalidade.
    #
    # Lido via settings (pydantic-settings) e não via os.getenv() - mesmo
    # motivo do SMTP_*: em produção o processo real não enxerga variáveis
    # que só existem no arquivo .env como env vars do container.
    calcom_base_url = settings.CALCOM_BASE_URL
    if not calcom_base_url:
        logger.warning(
            "CALCOM_BASE_URL não configurada - expiração automática de reservas "
            "DESATIVADA. Configure para liberar automaticamente horários não pagos."
        )
        return

    try:
        calcom_client = CalComClient(base_url=calcom_base_url)
    except RuntimeError as exc:
        logger.error("Não foi possível iniciar o cliente Cal.com para expiração: %s", exc)
        return

    minutos = _expira_minutos()
    intervalo = _expira_intervalo_segundos()
    logger.info(
        "Expiração automática de reservas ativada: %s min de prazo, checagem a cada %ss.",
        minutos,
        intervalo,
    )
    while True:
        try:
            processadas = await asyncio.to_thread(
                expirar_reservas_pendentes, selected_store, calcom_client, minutos
            )
            if processadas:
                logger.info("Varredura de expiração processou: %s", processadas)
        except Exception as exc:  # noqa: BLE001 - o loop de fundo não pode morrer
            logger.error("Falha inesperada na varredura de expiração: %s", exc)
        await asyncio.sleep(intervalo)


def _db_path():
    return os.getenv(
        "CAL_FEEGOW_DB_PATH",
        "/opt/data/workspace/hermes-feegow-mcp/data/cal_feegow_sync.db",
    )


def _default_store():
    return SyncStore(_db_path())


def _html_remarcacao_confirmada():
    return """
    <!doctype html>
    <html lang="pt-BR">
      <head><meta charset="utf-8"><title>Consulta remarcada</title></head>
      <body style="font-family: sans-serif; max-width: 640px; margin: 64px auto; padding: 24px;">
        <h1>Consulta remarcada com sucesso</h1>
        <p>Seu novo horário já está confirmado na Clínica Magnólia.</p>
        <p>Não é necessário nenhum novo pagamento - o sinal de reserva já pago continua válido.</p>
        <p>Você receberá a confirmação atualizada pelos canais informados no agendamento.</p>
      </body>
    </html>
    """


def _default_calcom_client():
    # Reaproveita o CalComClient da expiracao automatica pra cancelar no
    # Cal.com reservas que o nosso backend recusou por dados invalidos (CPF,
    # celular, data de nascimento etc.) - sem isso, o horario fica preso na
    # agenda sem aparecer em lugar nenhum pra clinica perceber.
    calcom_base_url = settings.CALCOM_BASE_URL
    if not calcom_base_url:
        return None
    try:
        return CalComClient(base_url=calcom_base_url)
    except RuntimeError as exc:
        logger.error(
            "Nao foi possivel iniciar o cliente Cal.com para cancelamento "
            "automatico de reservas com dados invalidos: %s",
            exc,
        )
        return None


def _default_handler():
    return SyncHandler(
        _default_store(),
        FeegowSyncService(),
        PagBankClient(),
        _default_calcom_client(),
        _default_email_client(),
    )


def _default_email_client():
    # E-mail de confirmação pós-pagamento, disparado pelo nosso backend (não
    # pelo Cal.com). Reaproveita o mesmo servidor/remetente SMTP que o
    # Cal.com já usa, mas com credenciais próprias no nosso .env - as duas
    # aplicações continuam independentes.
    #
    # Lido via settings (pydantic-settings, env_file=".env") e nao via
    # os.getenv(): em producao (EasyPanel) o processo real nao enxerga essas
    # variaveis como env vars do container (so existem no arquivo .env), e
    # os.getenv() sempre retorna vazio nesse caso. O FEEGOW_ACCESS_TOKEN ja
    # usava esse mesmo mecanismo com sucesso comprovado.
    host = settings.SMTP_HOST
    user = settings.SMTP_USER
    password = settings.SMTP_PASSWORD
    if not (host and user and password):
        logger.warning(
            "E-mail de confirmação de pagamento desativado: SMTP_HOST/"
            "SMTP_USER/SMTP_PASSWORD não configurados."
        )
        return None
    return EmailClient(
        host=host,
        port=settings.SMTP_PORT,
        user=user,
        password=password,
        from_email=settings.SMTP_FROM_EMAIL or user,
        from_name=settings.SMTP_FROM_NAME,
        endereco_presencial=settings.ENDERECO_CONSULTA_PRESENCIAL,
        calcom_base_url=settings.CALCOM_BASE_URL,
    )


def _default_pagbank_handler():
    return PagBankHandler(
        _default_store(),
        FeegowSyncService(),
        PagBankClient(),
        _default_email_client(),
    )


def create_app(
    handler=None,
    secret=None,
    pagbank_handler=None,
    pagbank_token=None,
    store=None,
):
    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI):
        selected_store = store or _default_store()
        tarefa = asyncio.create_task(_loop_expiracao_reservas(selected_store))
        try:
            yield
        finally:
            tarefa.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tarefa

    api = FastAPI(title="Cal.com → PagBank → Feegow", lifespan=lifespan)

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
    def iniciar_pagamento(
        uid: str = Query(min_length=1),
        rescheduleUid: str | None = Query(None),
    ):
        # Cal.com manda o usuário para esta URL após QUALQUER ação de
        # agendamento bem-sucedida (criação OU remarcação), pois a página de
        # sucesso configurada no tipo de evento é a mesma para os dois casos.
        # Numa remarcação não existe (e nunca vai existir) uma linha em
        # pending_bookings para o novo uid, porque o SyncHandler já trata o
        # BOOKING_RESCHEDULED direto: reaproveita o agendamento no Feegow e
        # atualiza o booking_map, sem exigir um novo sinal via PagBank. Sem
        # este atalho, o polling abaixo sempre esgotava as tentativas e
        # devolvia 404 para quem só estava remarcando uma consulta já paga.
        if rescheduleUid:
            return HTMLResponse(_html_remarcacao_confirmada())

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
        if pending["payment_status"] in RESERVA_INDISPONIVEL_PARA_PAGAMENTO:
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
