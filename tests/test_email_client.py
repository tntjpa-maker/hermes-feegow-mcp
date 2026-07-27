import email
import smtplib

import pytest

from ana_feegow.webhooks.cal_parser import CalBooking
from ana_feegow.webhooks.email_client import EmailClient


def _corpo(msg_str: str) -> str:
    """Decodifica o corpo (o smtplib recebe a mensagem como texto MIME
    pronto pra transmissão - com corpo em base64 por causa dos acentos)."""
    mensagem = email.message_from_string(msg_str)
    return mensagem.get_payload(decode=True).decode("utf-8")


def booking(tipo_consulta="consulta_presencial", email="paciente@example.com"):
    return CalBooking(
        uid="uid-1",
        booking_id=10,
        event_type_id=7,
        tipo_consulta=tipo_consulta,
        data="2026-08-12",
        horario="16:30:00",
        nome="Paciente Teste",
        email=email,
        cpf="11767993714",
        nascimento="1988-05-27",
        celular="21985929056",
        notas="",
    )


def pagbank_payload(payment_type="PIX", valor_centavos=7000):
    return {
        "reference_id": "uid-1",
        "charges": [
            {
                "status": "PAID",
                "amount": {"value": valor_centavos, "currency": "BRL"},
                "payment_method": {"type": payment_type},
            }
        ],
    }


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_args = None
        self.sent = None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, user, password):
        self.login_args = (user, password)

    def sendmail(self, from_addr, to_addrs, msg):
        self.sent = (from_addr, to_addrs, msg)


class FakeSMTPFalhaAoEnviar(FakeSMTP):
    def sendmail(self, from_addr, to_addrs, msg):
        raise smtplib.SMTPException("conexão recusada")


@pytest.fixture(autouse=True)
def _limpa_instancias():
    FakeSMTP.instances.clear()
    yield
    FakeSMTP.instances.clear()


def cliente(**kwargs):
    defaults = dict(
        host="smtp.gmail.com",
        port=587,
        user="magnoliasdm@gmail.com",
        password="senha-de-app",
        from_email="magnoliasdm@gmail.com",
        from_name="CLINICA MAGNÓLIA",
        endereco_presencial="Rua Exemplo, 123 - Niterói/RJ",
    )
    defaults.update(kwargs)
    return EmailClient(**defaults)


def test_sem_smtp_configurado_nao_envia_e_nao_quebra(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    client = cliente(host="", user="", password="")

    enviado = client.enviar_confirmacao_pagamento(booking(), pagbank_payload())

    assert enviado is False
    assert FakeSMTP.instances == []


def test_reserva_sem_email_nao_envia(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    client = cliente()

    enviado = client.enviar_confirmacao_pagamento(booking(email=""), pagbank_payload())

    assert enviado is False
    assert FakeSMTP.instances == []


def test_envio_presencial_inclui_data_horario_endereco_valor_e_forma_pagamento(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    client = cliente()

    enviado = client.enviar_confirmacao_pagamento(
        booking(tipo_consulta="consulta_presencial"),
        pagbank_payload(payment_type="PIX", valor_centavos=7000),
    )

    assert enviado is True
    smtp = FakeSMTP.instances[0]
    assert smtp.started_tls is True
    assert smtp.login_args == ("magnoliasdm@gmail.com", "senha-de-app")
    from_addr, to_addrs, msg = smtp.sent
    assert from_addr == "magnoliasdm@gmail.com"
    assert to_addrs == ["paciente@example.com"]
    assert "Agendamento confirmado - Clínica Magnólia" in str(
        email.header.make_header(email.header.decode_header(email.message_from_string(msg)["Subject"]))
    )
    corpo = _corpo(msg)
    assert "12/08/2026" in corpo
    assert "16:30" in corpo
    assert "Rua Exemplo, 123 - Niterói/RJ" in corpo
    assert "R$ 70,00" in corpo
    assert "Pix" in corpo


def test_envio_online_nao_inclui_endereco(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    client = cliente()

    client.enviar_confirmacao_pagamento(
        booking(tipo_consulta="consulta_online"),
        pagbank_payload(),
    )

    corpo = _corpo(FakeSMTP.instances[0].sent[2])
    assert "Endereço" not in corpo
    assert "Online" in corpo


def test_presencial_sem_endereco_configurado_envia_mesmo_assim(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    client = cliente(endereco_presencial="")

    enviado = client.enviar_confirmacao_pagamento(
        booking(tipo_consulta="consulta_presencial"),
        pagbank_payload(),
    )

    assert enviado is True
    corpo = _corpo(FakeSMTP.instances[0].sent[2])
    assert "Endereço" not in corpo


def test_forma_pagamento_desconhecida_usa_titulo_bruto(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    client = cliente()

    client.enviar_confirmacao_pagamento(
        booking(),
        pagbank_payload(payment_type="NOVO_METODO"),
    )

    corpo = _corpo(FakeSMTP.instances[0].sent[2])
    assert "Novo_Metodo" in corpo


def test_falha_no_envio_e_capturada_e_nao_lanca(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTPFalhaAoEnviar)
    client = cliente()

    enviado = client.enviar_confirmacao_pagamento(booking(), pagbank_payload())

    assert enviado is False


def test_sem_charges_no_payload_envia_sem_valor(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    client = cliente()

    enviado = client.enviar_confirmacao_pagamento(booking(), {"reference_id": "uid-1"})

    assert enviado is True
    corpo = _corpo(FakeSMTP.instances[0].sent[2])
    assert "Sinal de reserva" not in corpo
