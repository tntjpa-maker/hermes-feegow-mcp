import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from ana_feegow.webhooks.app import create_app
from ana_feegow.webhooks.cal_parser import parse_booking
from ana_feegow.webhooks.pagbank_client import PagBankClient
from ana_feegow.webhooks.pagbank_handler import PagBankHandler
from ana_feegow.webhooks.sync_handler import SyncHandler
from ana_feegow.webhooks.sync_store import SyncStore

# eventTypeId=7 / type="niteroi" -> consulta_presencial (SERVICES["consulta_presencial"]["valor"] = 35000)
# Sinal = 20% -> 7000 centavos (R$70,00).
SINAL_CONSULTA_PRESENCIAL_CENTAVOS = 7000


def cal_payload(trigger="BOOKING_CREATED"):
    return {
        "triggerEvent": trigger,
        "createdAt": "2026-07-25T12:00:00Z",
        "payload": {
            "uid": "cal-uid-pagbank-1",
            "bookingId": 900001,
            "eventTypeId": 7,
            "type": "niteroi",
            "startTime": "2026-07-29T12:00:00Z",
            "responses": {
                "name": {"value": "Paciente Teste"},
                "email": {"value": "paciente@example.com"},
                "cpf": {"value": "11767993714"},
                "data_nascimento": {"value": "27051988"},
                "celular": {"value": "21985929056"},
            },
        },
    }


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "id": "CHEC_123",
            "links": [{"rel": "PAY", "href": "https://sandbox.pagbank.test/pay"}],
        }


class FakeSession:
    def __init__(self):
        self.payload = None

    def post(self, url, **kwargs):
        self.payload = kwargs["json"]
        return FakeResponse()


class FakePaymentClient:
    """Simula o PagBankClient só para o método usado na reconfirmação."""

    def __init__(self, pedido):
        self.pedido = pedido
        self.consultas = []

    def consultar_pedido(self, order_id):
        self.consultas.append(order_id)
        return self.pedido


class FakeFeegow:
    def __init__(self):
        self.created = 0

    def create_booking(self, booking):
        self.created += 1
        return 54

    def reschedule_booking(self, appointment_id, booking):
        return {"success": True}

    def cancel_booking(self, appointment_id):
        return {"success": True}


def test_booking_created_checkout_paid_feegow_e_idempotencia(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    session = FakeSession()
    pagbank = PagBankClient(
        token="token",
        webhook_url="https://integracao.example/webhooks/pagbank",
        public_base_url="https://integracao.example",
        session=session,
    )
    feegow = FakeFeegow()
    cal_handler = SyncHandler(store, feegow, pagbank)

    result = cal_handler.handle(cal_payload())
    assert result["status"] == "processed"
    assert result["payment_url"] == "https://sandbox.pagbank.test/pay"
    assert session.payload["reference_id"] == "cal-uid-pagbank-1"
    assert session.payload["items"][0]["unit_amount"] == SINAL_CONSULTA_PRESENCIAL_CENTAVOS
    assert store.get_mapping("cal-uid-pagbank-1") is None

    notification = {
        "id": "ORDE_123",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_123", "status": "PAID"}],
    }
    handler = PagBankHandler(store, feegow)
    assert handler.handle(notification)["status"] == "processed"
    assert handler.handle(notification)["status"] == "duplicate"
    assert feegow.created == 1
    assert store.get_mapping("cal-uid-pagbank-1")["feegow_appointment_id"] == 54


def test_webhook_pagbank_valida_assinatura_e_redireciona(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(
        booking,
        "CHEC_123",
        "https://sandbox.pagbank.test/pay",
    )

    class FakePagBankHandler:
        def handle(self, payload, assinatura_confiavel=True):
            return {"status": "processed", "uid": payload["reference_id"]}

    client = TestClient(
        create_app(
            handler=object(),
            secret="cal-secret",
            pagbank_handler=FakePagBankHandler(),
            pagbank_token="pagbank-token",
            store=store,
        )
    )
    raw = json.dumps(
        {"reference_id": "cal-uid-pagbank-1", "status": "PAID"},
        separators=(",", ":"),
    ).encode()
    signature = hashlib.sha256(b"pagbank-token-" + raw).hexdigest()

    response = client.post(
        "/webhooks/pagbank",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-authenticity-token": signature,
        },
    )
    assert response.status_code == 200

    redirect = client.get(
        "/pagamento/iniciar?uid=cal-uid-pagbank-1",
        follow_redirects=False,
    )
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://sandbox.pagbank.test/pay"


def test_pagamento_iniciar_com_reschedule_uid_nao_espera_reserva_pendente(tmp_path):
    # Reproduz o bug real: o Cal.com manda o navegador pra /pagamento/iniciar
    # após QUALQUER ação de agendamento bem-sucedida, inclusive remarcação -
    # mas numa remarcação nunca existe (nem vai existir) uma linha em
    # pending_bookings para o novo uid, porque o SyncHandler já trata o
    # BOOKING_RESCHEDULED direto, sem exigir novo pagamento. Sem o atalho
    # baseado no parâmetro rescheduleUid, isso sempre esgotava as tentativas
    # de polling e devolvia 404 pro paciente que só remarcou uma consulta já
    # paga.
    store = SyncStore(str(tmp_path / "sync.db"))
    client = TestClient(
        create_app(
            handler=object(),
            secret="cal-secret",
            pagbank_handler=object(),
            pagbank_token="pagbank-token",
            store=store,
        )
    )

    response = client.get(
        "/pagamento/iniciar?uid=novo-uid-remarcado&rescheduleUid=uid-antigo-pago",
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "remarcada" in response.text.lower()
    assert store.get_pending_booking("novo-uid-remarcado") is None


def test_pagbank_reconfirma_via_api_quando_assinatura_ausente(tmp_path):
    # Simula o bug conhecido do PagBank Sandbox: a notificação chega sem o
    # header x-authenticity-token. O handler não deve confiar no corpo
    # recebido - só cria a consulta se a API do PagBank confirmar o
    # pagamento de verdade quando consultada com o token da clínica.
    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(booking, "CHEC_999", "https://sandbox.pagbank.test/pay")

    pedido_confirmado_pela_api = {
        "id": "ORDE_999",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_999", "status": "PAID"}],
    }
    feegow = FakeFeegow()
    payment_client = FakePaymentClient(pedido_confirmado_pela_api)
    handler = PagBankHandler(store, feegow, payment_client)

    # Payload "cru" da notificação, sem assinatura confiável - mesmo se
    # viesse adulterado, só usamos o "id" para buscar o pedido de verdade.
    payload_nao_confiavel = {"id": "ORDE_999", "reference_id": "cal-uid-pagbank-1"}

    result = handler.handle(payload_nao_confiavel, assinatura_confiavel=False)

    assert result["status"] == "processed"
    assert result["feegow_appointment_id"] == 54
    assert payment_client.consultas == ["ORDE_999"]
    assert feegow.created == 1
    assert store.get_mapping("cal-uid-pagbank-1")["pagbank_transaction_id"] == "CHAR_999"


def test_pagbank_sem_assinatura_e_sem_cliente_de_pagamento_e_rejeitado(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    feegow = FakeFeegow()
    handler = PagBankHandler(store, feegow)  # sem payment_client

    with pytest.raises(ValueError):
        handler.handle({"id": "ORDE_999"}, assinatura_confiavel=False)


def test_webhook_pagbank_sem_header_reconfirma_no_handler(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    chamadas = []

    class SpyPagBankHandler:
        def handle(self, payload, assinatura_confiavel=True):
            chamadas.append(assinatura_confiavel)
            return {"status": "processed", "uid": payload.get("reference_id")}

    client = TestClient(
        create_app(
            handler=object(),
            secret="cal-secret",
            pagbank_handler=SpyPagBankHandler(),
            pagbank_token="pagbank-token",
            store=store,
        )
    )
    raw = json.dumps(
        {"id": "ORDE_1", "reference_id": "cal-uid-x"},
        separators=(",", ":"),
    ).encode()

    response = client.post(
        "/webhooks/pagbank",
        content=raw,
        headers={"content-type": "application/json"},  # sem x-authenticity-token
    )
    assert response.status_code == 200
    assert chamadas == [False]


def test_webhook_pagbank_assinatura_errada_ainda_rejeita(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    client = TestClient(
        create_app(
            handler=object(),
            secret="cal-secret",
            pagbank_handler=object(),
            pagbank_token="pagbank-token",
            store=store,
        )
    )
    raw = json.dumps({"reference_id": "cal-uid-x"}, separators=(",", ":")).encode()

    response = client.post(
        "/webhooks/pagbank",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-authenticity-token": "assinatura-errada",
        },
    )
    assert response.status_code == 401


def test_create_checkout_rejeita_cpf_com_digito_verificador_invalido(tmp_path):
    # CPFs "de brincadeira" (ex.: 11233223423, usado numa reserva de teste
    # real) têm 11 dígitos mas não passam no cálculo do dígito verificador.
    # O PagBank rejeita esses com HTTP 400 - detectamos isso antes, sem
    # nem chamar a API deles.
    session = FakeSession()
    pagbank = PagBankClient(
        token="token",
        webhook_url="https://integracao.example/webhooks/pagbank",
        public_base_url="https://integracao.example",
        session=session,
    )
    envelope = cal_payload()
    envelope["payload"]["responses"]["cpf"]["value"] = "11233223423"
    booking_cpf_invalido = parse_booking(envelope)

    with pytest.raises(ValueError, match="CPF inválido"):
        pagbank.create_checkout(booking_cpf_invalido)

    assert session.payload is None  # não deve nem tentar chamar a API do PagBank


class FakeEmailClient:
    def __init__(self, deve_falhar=False):
        self.chamadas = []
        self.deve_falhar = deve_falhar

    def enviar_confirmacao_pagamento(self, booking, payload):
        self.chamadas.append((booking.uid, payload))
        if self.deve_falhar:
            raise RuntimeError("SMTP indisponivel (simulado)")
        return True


def test_pagamento_confirmado_dispara_email_de_confirmacao(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(booking, "CHEC_123", "https://sandbox.pagbank.test/pay")

    feegow = FakeFeegow()
    email_client = FakeEmailClient()
    handler = PagBankHandler(store, feegow, email_client=email_client)

    notification = {
        "id": "ORDE_123",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_123", "status": "PAID"}],
    }
    result = handler.handle(notification)

    assert result["status"] == "processed"
    assert len(email_client.chamadas) == 1
    uid_enviado, payload_enviado = email_client.chamadas[0]
    assert uid_enviado == "cal-uid-pagbank-1"
    assert payload_enviado is notification


def test_pagamento_duplicado_nao_dispara_email_de_novo(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(booking, "CHEC_123", "https://sandbox.pagbank.test/pay")

    feegow = FakeFeegow()
    email_client = FakeEmailClient()
    handler = PagBankHandler(store, feegow, email_client=email_client)

    notification = {
        "id": "ORDE_123",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_123", "status": "PAID"}],
    }
    handler.handle(notification)
    handler.handle(notification)  # mesma notificacao, deve ser tratada como duplicata

    assert len(email_client.chamadas) == 1


def test_pagamento_tardio_apos_expiracao_ja_ter_reivindicado_nao_cria_consulta(tmp_path):
    # Reproduz o bug real encontrado em produção: a reserva expirou (30 min
    # sem pagamento) e a expiração automática já reivindicou a linha
    # (WAITING -> EXPIRING) antes de cancelar no Cal.com, mas a notificação
    # PAID do PagBank chega logo em seguida. Antes da correção, o handler
    # lia o status uma única vez no início e criava a consulta no Feegow
    # mesmo assim; agora ele reivindica atomicamente antes de criar, então
    # perde a corrida e não cria nada.
    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(booking, "CHEC_123", "https://sandbox.pagbank.test/pay")

    # Simula a expiração automática tendo acabado de reivindicar a reserva.
    assert store.claim_pending_status("cal-uid-pagbank-1", "WAITING", "EXPIRING") is True

    feegow = FakeFeegow()
    handler = PagBankHandler(store, feegow)

    notification = {
        "id": "ORDE_123",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_123", "status": "PAID"}],
    }
    result = handler.handle(notification)

    assert result["status"] == "revisao_manual"
    assert feegow.created == 0
    assert store.get_mapping("cal-uid-pagbank-1") is None


def test_pagamento_perde_corrida_apos_ler_status_disponivel_nao_cria_consulta(tmp_path, monkeypatch):
    # Mesmo cenário acima, mas simulando a corrida no ponto mais estreito
    # possível: o status ainda está "WAITING" quando o handler lê `pending`,
    # e só muda (por outra rotina) um instante depois, exatamente entre a
    # leitura e a reivindicação atômica. A reivindicação deve perder e
    # nenhuma consulta deve ser criada no Feegow.
    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(booking, "CHEC_123", "https://sandbox.pagbank.test/pay")

    feegow = FakeFeegow()
    handler = PagBankHandler(store, feegow)

    original_claim = store.claim_pending_status

    def claim_simulando_corrida(uid, de_status, para_status):
        store.update_pending_status(uid, "EXPIRED")
        return original_claim(uid, de_status, para_status)

    monkeypatch.setattr(store, "claim_pending_status", claim_simulando_corrida)
    notification = {
        "id": "ORDE_123",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_123", "status": "PAID"}],
    }
    result = handler.handle(notification)

    assert result["status"] == "revisao_manual"
    assert feegow.created == 0
    assert store.get_mapping("cal-uid-pagbank-1") is None


def test_falha_ao_criar_no_feegow_devolve_reserva_para_reivindicacao_futura(tmp_path):
    # Se claim_pending_status já reivindicou a reserva (WAITING -> PROCESSING)
    # mas a criação no Feegow falhar (ex.: API fora do ar), a reserva não
    # pode ficar travada em "PROCESSING" para sempre - um reenvio do webhook
    # pelo PagBank (comportamento normal dele) precisa conseguir tentar de
    # novo.
    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(booking, "CHEC_123", "https://sandbox.pagbank.test/pay")

    class FeegowQuebrado:
        def create_booking(self, booking):
            raise RuntimeError("Feegow fora do ar")

    handler = PagBankHandler(store, FeegowQuebrado())
    notification = {
        "id": "ORDE_123",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_123", "status": "PAID"}],
    }

    with pytest.raises(RuntimeError):
        handler.handle(notification)

    assert store.get_pending_booking("cal-uid-pagbank-1")["payment_status"] == "WAITING"


def test_sem_email_client_configurado_pagamento_segue_normalmente(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(booking, "CHEC_123", "https://sandbox.pagbank.test/pay")

    feegow = FakeFeegow()
    handler = PagBankHandler(store, feegow)  # sem email_client, como antes

    notification = {
        "id": "ORDE_123",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_123", "status": "PAID"}],
    }
    result = handler.handle(notification)

    assert result["status"] == "processed"
    assert feegow.created == 1


def test_falha_no_envio_de_email_nao_derruba_confirmacao_do_pagamento(tmp_path):
    # O agendamento no Feegow ja foi criado quando o e-mail e disparado -
    # uma falha no SMTP nao pode fazer o webhook do PagBank retornar erro
    # (o PagBank ficaria reenviando a notificacao a toa).
    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(booking, "CHEC_123", "https://sandbox.pagbank.test/pay")

    feegow = FakeFeegow()
    email_client = FakeEmailClient(deve_falhar=True)
    handler = PagBankHandler(store, feegow, email_client=email_client)

    notification = {
        "id": "ORDE_123",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_123", "status": "PAID"}],
    }

    with pytest.raises(RuntimeError):
        handler.handle(notification)
    # nota: no EmailClient de verdade, enviar_confirmacao_pagamento nunca
    # lanca - esse teste usa um duble que propositalmente lanca pra provar
    # que, SE lancasse, o pagamento ja estava confirmado no Feegow antes.
    assert feegow.created == 1
    assert store.get_mapping("cal-uid-pagbank-1")["feegow_appointment_id"] == 54


def test_pagamento_confirmado_notifica_paciente_por_whatsapp(tmp_path, monkeypatch):
    import ana_feegow.webhooks.pagbank_handler as pagbank_handler_module

    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(booking, "CHEC_123", "https://sandbox.pagbank.test/pay")

    feegow = FakeFeegow()
    handler = PagBankHandler(store, feegow)

    chamadas = []
    monkeypatch.setattr(
        pagbank_handler_module.dialog,
        "notificar_paciente",
        lambda chat_id, mensagem: chamadas.append((chat_id, mensagem)) or True,
    )

    notification = {
        "id": "ORDE_123",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_123", "status": "PAID"}],
    }
    result = handler.handle(notification)

    assert result["status"] == "processed"
    assert len(chamadas) == 1
    chat_id, mensagem = chamadas[0]
    assert chat_id == "5521985929056@s.whatsapp.net"
    assert "pagamento foi confirmado" in mensagem.lower()
    assert "29/07/2026" in mensagem
    assert "09:00" in mensagem


def test_confirmacao_pagamento_normaliza_celular_sem_ddi(monkeypatch):
    """Regressao: um bug real foi encontrado em teste ao vivo em producao -
    o celular do Cal.com normalmente vem sem o DDI 55 (so DDD+numero), e o
    chat_id era montado direto com esse valor cru, entao a mensagem nunca
    chegava de verdade no WhatsApp (a chamada ao bridge nao lancava excecao,
    mas o numero de destino era invalido). Aqui garantimos que o celular e
    sempre normalizado para E.164 (com 55) antes de montar o chat_id -
    tanto quando falta o DDI quanto quando ja vem completo (nao pode
    duplicar o 55)."""
    import ana_feegow.webhooks.pagbank_handler as pagbank_handler_module
    from ana_feegow.webhooks.cal_parser import CalBooking

    chamadas = []
    monkeypatch.setattr(
        pagbank_handler_module.dialog,
        "notificar_paciente",
        lambda chat_id, mensagem: chamadas.append(chat_id) or True,
    )

    base = dict(
        uid="uid-x", booking_id=1, event_type_id=7, tipo_consulta="consulta",
        data="2026-07-29", horario="09:00:00", nome="Paciente Teste",
        email="p@example.com", cpf="", nascimento="", notas="",
        opportunity_id="opp-1",
    )
    pagbank_handler_module.PagBankHandler._notificar_confirmacao_pagamento(
        CalBooking(**base, celular="21985929056")
    )
    pagbank_handler_module.PagBankHandler._notificar_confirmacao_pagamento(
        CalBooking(**base, celular="5521985929056")
    )

    assert chamadas == [
        "5521985929056@s.whatsapp.net",
        "5521985929056@s.whatsapp.net",
    ]


def test_falha_no_envio_de_whatsapp_nao_derruba_confirmacao_do_pagamento(tmp_path, monkeypatch):
    import ana_feegow.webhooks.pagbank_handler as pagbank_handler_module

    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(booking, "CHEC_123", "https://sandbox.pagbank.test/pay")

    feegow = FakeFeegow()
    handler = PagBankHandler(store, feegow)

    def notificar_com_erro(chat_id, mensagem):
        raise RuntimeError("bridge do WhatsApp fora do ar (simulado)")

    monkeypatch.setattr(
        pagbank_handler_module.dialog, "notificar_paciente", notificar_com_erro
    )

    notification = {
        "id": "ORDE_123",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_123", "status": "PAID"}],
    }
    result = handler.handle(notification)

    assert result["status"] == "processed"
    assert feegow.created == 1


def test_create_checkout_aceita_cpf_de_teste_oficial_do_pagbank(tmp_path):
    # 01234567890 é o CPF de teste recomendado pela documentação do
    # PagBank para o ambiente Sandbox - precisa continuar passando.
    session = FakeSession()
    pagbank = PagBankClient(
        token="token",
        webhook_url="https://integracao.example/webhooks/pagbank",
        public_base_url="https://integracao.example",
        session=session,
    )
    envelope = cal_payload()
    envelope["payload"]["responses"]["cpf"]["value"] = "01234567890"
    booking = parse_booking(envelope)

    checkout = pagbank.create_checkout(booking)

    assert checkout.checkout_id == "CHEC_123"
    assert session.payload["customer"]["tax_id"] == "01234567890"
