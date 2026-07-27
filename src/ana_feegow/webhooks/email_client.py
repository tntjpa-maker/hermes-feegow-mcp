import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formataddr

logger = logging.getLogger("webhooks")

FORMAS_PAGAMENTO = {
    "PIX": "Pix",
    "CREDIT_CARD": "Cartão de crédito",
    "DEBIT_CARD": "Cartão de débito",
    "BOLETO": "Boleto",
}

TIPOS_CONSULTA_LABEL = {
    "consulta_presencial": "Presencial",
    "consulta_hibrida": "Híbrida",
    "consulta_online": "Online",
}


def _formatar_data(data: str) -> str:
    try:
        return datetime.strptime(data, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return data


def _formatar_horario(horario: str) -> str:
    try:
        return datetime.strptime(horario, "%H:%M:%S").strftime("%H:%M")
    except ValueError:
        return horario


def _formatar_valor(valor_centavos) -> str:
    try:
        reais = int(valor_centavos) / 100
    except (TypeError, ValueError):
        return ""
    texto = f"{reais:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


class EmailClient:
    """Envia por SMTP o e-mail de confirmação após o PagBank aprovar o
    pagamento. Reaproveita o mesmo servidor SMTP que o Cal.com já usa
    (mesma conta/remetente) mas com credenciais próprias, configuradas
    separadamente no .env do cal-feegow-webhooks - as duas aplicações não
    dependem uma da outra.
    """

    def __init__(
        self,
        host=None,
        port=587,
        user=None,
        password=None,
        from_email=None,
        from_name="Clínica Magnólia",
        endereco_presencial=None,
        timeout=15,
    ):
        self.host = host
        self.port = int(port) if port else 587
        self.user = user
        self.password = password
        self.from_email = from_email or user
        self.from_name = from_name
        self.endereco_presencial = (endereco_presencial or "").strip()
        self.timeout = timeout

    @property
    def configurado(self) -> bool:
        return bool(self.host and self.user and self.password and self.from_email)

    @staticmethod
    def _forma_pagamento(payload: dict) -> str:
        charges = payload.get("charges") or []
        if not charges:
            return ""
        tipo = str((charges[0].get("payment_method") or {}).get("type") or "").upper()
        if not tipo:
            return ""
        return FORMAS_PAGAMENTO.get(tipo, tipo.title())

    @staticmethod
    def _valor_pago_centavos(payload: dict):
        charges = payload.get("charges") or []
        if not charges:
            return None
        return (charges[0].get("amount") or {}).get("value")

    def _montar_corpo(self, booking, payload: dict) -> str:
        linhas = [
            f"Olá {booking.nome},",
            "",
            "Seu agendamento na Clínica Magnólia foi confirmado com sucesso!",
            "",
            f"Data: {_formatar_data(booking.data)}",
            f"Horário: {_formatar_horario(booking.horario)}",
            "Tipo de consulta: "
            + TIPOS_CONSULTA_LABEL.get(booking.tipo_consulta, booking.tipo_consulta),
        ]

        if booking.tipo_consulta == "consulta_presencial":
            if self.endereco_presencial:
                linhas.append(f"Endereço: {self.endereco_presencial}")
            else:
                logger.warning(
                    "E-mail de confirmação (uid=%s) enviado sem endereço: "
                    "ENDERECO_CONSULTA_PRESENCIAL não configurado.",
                    booking.uid,
                )

        valor_centavos = self._valor_pago_centavos(payload)
        if valor_centavos is not None:
            valor_fmt = _formatar_valor(valor_centavos)
            if valor_fmt:
                texto_valor = f"Sinal de reserva confirmado: {valor_fmt}"
                forma = self._forma_pagamento(payload)
                if forma:
                    texto_valor += f" via {forma}"
                linhas.append(texto_valor)

        linhas += [
            "",
            "Qualquer dúvida, estamos à disposição.",
            "",
            "Atenciosamente,",
            "Clínica Magnólia - Dra. Thalita Menezes",
        ]
        return "\n".join(linhas)

    def enviar_confirmacao_pagamento(self, booking, payload: dict) -> bool:
        # Nunca deve derrubar o processamento do pagamento: o agendamento
        # no Feegow já foi criado antes desse método ser chamado, o que
        # importa de verdade já aconteceu. Falha de e-mail só é logada.
        if not self.configurado:
            logger.warning(
                "E-mail de confirmação não enviado (uid=%s): SMTP não configurado "
                "(SMTP_HOST/SMTP_USER/SMTP_PASSWORD ausentes).",
                booking.uid,
            )
            return False
        if not booking.email:
            logger.warning(
                "E-mail de confirmação não enviado (uid=%s): reserva sem e-mail.",
                booking.uid,
            )
            return False

        corpo = self._montar_corpo(booking, payload)
        msg = MIMEText(corpo, "plain", "utf-8")
        msg["Subject"] = "Agendamento confirmado - Clínica Magnólia"
        msg["From"] = formataddr((self.from_name, self.from_email))
        msg["To"] = booking.email

        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
                smtp.starttls()
                smtp.login(self.user, self.password)
                smtp.sendmail(self.from_email, [booking.email], msg.as_string())
            logger.info(
                "E-mail de confirmação de pagamento enviado (uid=%s, destinatario=%s).",
                booking.uid,
                booking.email,
            )
            return True
        except Exception as exc:  # noqa: BLE001 - não pode mascarar/derrubar o pagamento
            logger.error(
                "Falha ao enviar e-mail de confirmação de pagamento (uid=%s): %s",
                booking.uid,
                exc,
            )
            return False
