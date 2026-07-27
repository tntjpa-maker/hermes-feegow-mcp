import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from urllib.parse import quote

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
        calcom_base_url=None,
        timeout=15,
    ):
        self.host = host
        self.port = int(port) if port else 587
        self.user = user
        self.password = password
        self.from_email = from_email or user
        self.from_name = from_name
        self.endereco_presencial = (endereco_presencial or "").strip()
        # Usado para montar os links de cancelar/remarcar do e-mail, apontando
        # direto para a reserva certa no Cal.com (via uid). Se não configurado,
        # o e-mail é enviado normalmente, só sem esses links - igual acontecia
        # antes dessa funcionalidade existir.
        self.calcom_base_url = (calcom_base_url or "").rstrip("/")
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

    def _link_cancelar(self, booking) -> str:
        # Página pública do Cal.com com os detalhes da reserva - de lá o
        # paciente clica em "Cancelar" (fluxo já usado hoje pelo próprio
        # Cal.com, o mesmo endpoint que o CalComClient usa no cancelamento
        # automático por dados inválidos).
        return f"{self.calcom_base_url}/booking/{booking.uid}"

    def _link_remarcar(self, booking) -> str:
        # Leva direto pro calendário de remarcação daquela reserva específica.
        link = f"{self.calcom_base_url}/reschedule/{booking.uid}"
        if booking.email:
            link += f"?rescheduledBy={quote(booking.email)}"
        return link

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

        if self.calcom_base_url:
            linhas += [
                "",
                "Precisa cancelar ou remarcar?",
                f"Cancelar: {self._link_cancelar(booking)}",
                f"Remarcar: {self._link_remarcar(booking)}",
            ]

        linhas += [
            "",
            "Qualquer dúvida, estamos à disposição.",
            "",
            "Atenciosamente,",
            "Clínica Magnólia - Dra. Thalita Menezes",
        ]
        return "\n".join(linhas)

    def _montar_corpo_html(self, booking, payload: dict) -> str:
        linhas = [
            f"<p>Olá {booking.nome},</p>",
            "<p>Seu agendamento na Clínica Magnólia foi confirmado com sucesso!</p>",
            "<table cellpadding=\"4\" cellspacing=\"0\">",
            f"<tr><td><strong>Data:</strong></td><td>{_formatar_data(booking.data)}</td></tr>",
            f"<tr><td><strong>Horário:</strong></td><td>{_formatar_horario(booking.horario)}</td></tr>",
            "<tr><td><strong>Tipo de consulta:</strong></td><td>"
            + TIPOS_CONSULTA_LABEL.get(booking.tipo_consulta, booking.tipo_consulta)
            + "</td></tr>",
        ]

        if booking.tipo_consulta == "consulta_presencial" and self.endereco_presencial:
            linhas.append(
                f"<tr><td><strong>Endereço:</strong></td><td>{self.endereco_presencial}</td></tr>"
            )

        valor_centavos = self._valor_pago_centavos(payload)
        if valor_centavos is not None:
            valor_fmt = _formatar_valor(valor_centavos)
            if valor_fmt:
                texto_valor = f"Sinal de reserva confirmado: {valor_fmt}"
                forma = self._forma_pagamento(payload)
                if forma:
                    texto_valor += f" via {forma}"
                linhas.append(f"<tr><td colspan=\"2\">{texto_valor}</td></tr>")

        linhas.append("</table>")

        if self.calcom_base_url:
            estilo_botao = (
                "display:inline-block;padding:10px 20px;margin:8px 8px 0 0;"
                "border-radius:6px;text-decoration:none;font-weight:bold;"
            )
            linhas += [
                '<p style="margin-top:24px;">Precisa cancelar ou remarcar?</p>',
                "<p>",
                f'<a href="{self._link_remarcar(booking)}" '
                f'style="{estilo_botao}background-color:#7a4b8a;color:#ffffff;">Remarcar consulta</a>',
                f'<a href="{self._link_cancelar(booking)}" '
                f'style="{estilo_botao}background-color:#f2f2f2;color:#333333;border:1px solid #cccccc;">'
                "Cancelar consulta</a>",
                "</p>",
            ]

        linhas += [
            "<p>Qualquer dúvida, estamos à disposição.</p>",
            "<p>Atenciosamente,<br>Clínica Magnólia - Dra. Thalita Menezes</p>",
        ]
        return "<html><body>" + "\n".join(linhas) + "</body></html>"

    def _enviar_email(
        self, uid: str, destinatario: str, assunto: str, corpo_texto: str, corpo_html: str, contexto: str
    ) -> bool:
        # Mecânica de envio compartilhada pelos três tipos de e-mail
        # (confirmação de pagamento, cancelamento, remarcação). Nunca deve
        # derrubar o processamento do webhook que a chamou: a ação real
        # (pagamento confirmado, cancelamento ou remarcação no Feegow) já
        # aconteceu antes desse método ser chamado. Falha de e-mail só é
        # logada.
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = formataddr((self.from_name, self.from_email))
        msg["To"] = destinatario
        # Texto puro primeiro (fallback), HTML por último (é o que a maioria
        # dos clientes de e-mail prioriza mostrar) - ordem exigida pelo
        # próprio formato multipart/alternative.
        msg.attach(MIMEText(corpo_texto, "plain", "utf-8"))
        msg.attach(MIMEText(corpo_html, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
                smtp.starttls()
                smtp.login(self.user, self.password)
                smtp.sendmail(self.from_email, [destinatario], msg.as_string())
            logger.info(
                "E-mail de %s enviado (uid=%s, destinatario=%s).",
                contexto,
                uid,
                destinatario,
            )
            return True
        except Exception as exc:  # noqa: BLE001 - não pode mascarar/derrubar o webhook
            logger.error(
                "Falha ao enviar e-mail de %s (uid=%s): %s", contexto, uid, exc
            )
            return False

    def enviar_confirmacao_pagamento(self, booking, payload: dict) -> bool:
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

        if not self.calcom_base_url:
            logger.warning(
                "E-mail de confirmação (uid=%s) enviado sem links de cancelar/"
                "remarcar: CALCOM_BASE_URL não configurada.",
                booking.uid,
            )

        return self._enviar_email(
            booking.uid,
            booking.email,
            "Agendamento confirmado - Clínica Magnólia",
            self._montar_corpo(booking, payload),
            self._montar_corpo_html(booking, payload),
            contexto="confirmação de pagamento",
        )

    def enviar_confirmacao_cancelamento(self, booking) -> bool:
        # Disparado pelo SyncHandler depois que o cancelamento já foi
        # confirmado no Cal.com E no Feegow - só avisa a paciente, não faz
        # parte do fluxo crítico.
        if not self.configurado:
            logger.warning(
                "E-mail de cancelamento não enviado (uid=%s): SMTP não configurado "
                "(SMTP_HOST/SMTP_USER/SMTP_PASSWORD ausentes).",
                booking.uid,
            )
            return False
        if not booking.email:
            logger.warning(
                "E-mail de cancelamento não enviado (uid=%s): reserva sem e-mail.",
                booking.uid,
            )
            return False

        corpo_texto = "\n".join(
            [
                f"Olá {booking.nome},",
                "",
                "Sua consulta na Clínica Magnólia foi cancelada.",
                "",
                f"Data: {_formatar_data(booking.data)}",
                f"Horário: {_formatar_horario(booking.horario)}",
                "",
                "Se quiser marcar um novo horário, é só acessar novamente o "
                "link de agendamento ou entrar em contato com a clínica.",
                "",
                "Atenciosamente,",
                "Clínica Magnólia - Dra. Thalita Menezes",
            ]
        )
        corpo_html = (
            "<html><body>"
            f"<p>Olá {booking.nome},</p>"
            "<p>Sua consulta na Clínica Magnólia foi cancelada.</p>"
            '<table cellpadding="4" cellspacing="0">'
            f"<tr><td><strong>Data:</strong></td><td>{_formatar_data(booking.data)}</td></tr>"
            f"<tr><td><strong>Horário:</strong></td><td>{_formatar_horario(booking.horario)}</td></tr>"
            "</table>"
            "<p>Se quiser marcar um novo horário, é só acessar novamente o "
            "link de agendamento ou entrar em contato com a clínica.</p>"
            "<p>Atenciosamente,<br>Clínica Magnólia - Dra. Thalita Menezes</p>"
            "</body></html>"
        )
        return self._enviar_email(
            booking.uid,
            booking.email,
            "Consulta cancelada - Clínica Magnólia",
            corpo_texto,
            corpo_html,
            contexto="cancelamento",
        )

    def enviar_confirmacao_remarcacao(self, booking) -> bool:
        # `booking` já reflete os dados NOVOS (parseados do webhook
        # BOOKING_RESCHEDULED mais recente pelo SyncHandler), então a
        # data/horário mostrados aqui já são os atualizados. Disparado só
        # depois que a remarcação já foi confirmada no Cal.com E no Feegow.
        if not self.configurado:
            logger.warning(
                "E-mail de remarcação não enviado (uid=%s): SMTP não configurado "
                "(SMTP_HOST/SMTP_USER/SMTP_PASSWORD ausentes).",
                booking.uid,
            )
            return False
        if not booking.email:
            logger.warning(
                "E-mail de remarcação não enviado (uid=%s): reserva sem e-mail.",
                booking.uid,
            )
            return False

        linhas_texto = [
            f"Olá {booking.nome},",
            "",
            "Sua consulta na Clínica Magnólia foi remarcada com sucesso!",
            "",
            f"Novo horário - Data: {_formatar_data(booking.data)}",
            f"Novo horário - Horário: {_formatar_horario(booking.horario)}",
            "Tipo de consulta: "
            + TIPOS_CONSULTA_LABEL.get(booking.tipo_consulta, booking.tipo_consulta),
        ]
        if booking.tipo_consulta == "consulta_presencial" and self.endereco_presencial:
            linhas_texto.append(f"Endereço: {self.endereco_presencial}")
        linhas_texto += [
            "",
            "Não é necessário nenhum novo pagamento - o sinal de reserva já pago continua válido.",
        ]
        if self.calcom_base_url:
            linhas_texto += [
                "",
                "Precisa cancelar ou remarcar de novo?",
                f"Cancelar: {self._link_cancelar(booking)}",
                f"Remarcar: {self._link_remarcar(booking)}",
            ]
        linhas_texto += [
            "",
            "Qualquer dúvida, estamos à disposição.",
            "",
            "Atenciosamente,",
            "Clínica Magnólia - Dra. Thalita Menezes",
        ]
        corpo_texto = "\n".join(linhas_texto)

        linhas_html = [
            f"<p>Olá {booking.nome},</p>",
            "<p>Sua consulta na Clínica Magnólia foi remarcada com sucesso!</p>",
            '<table cellpadding="4" cellspacing="0">',
            f"<tr><td><strong>Nova data:</strong></td><td>{_formatar_data(booking.data)}</td></tr>",
            f"<tr><td><strong>Novo horário:</strong></td><td>{_formatar_horario(booking.horario)}</td></tr>",
            "<tr><td><strong>Tipo de consulta:</strong></td><td>"
            + TIPOS_CONSULTA_LABEL.get(booking.tipo_consulta, booking.tipo_consulta)
            + "</td></tr>",
        ]
        if booking.tipo_consulta == "consulta_presencial" and self.endereco_presencial:
            linhas_html.append(
                f"<tr><td><strong>Endereço:</strong></td><td>{self.endereco_presencial}</td></tr>"
            )
        linhas_html.append("</table>")
        linhas_html.append(
            "<p>Não é necessário nenhum novo pagamento - o sinal de reserva já "
            "pago continua válido.</p>"
        )
        if self.calcom_base_url:
            estilo_botao = (
                "display:inline-block;padding:10px 20px;margin:8px 8px 0 0;"
                "border-radius:6px;text-decoration:none;font-weight:bold;"
            )
            linhas_html += [
                '<p style="margin-top:24px;">Precisa cancelar ou remarcar de novo?</p>',
                "<p>",
                f'<a href="{self._link_remarcar(booking)}" '
                f'style="{estilo_botao}background-color:#7a4b8a;color:#ffffff;">Remarcar consulta</a>',
                f'<a href="{self._link_cancelar(booking)}" '
                f'style="{estilo_botao}background-color:#f2f2f2;color:#333333;border:1px solid #cccccc;">'
                "Cancelar consulta</a>",
                "</p>",
            ]
        linhas_html += [
            "<p>Qualquer dúvida, estamos à disposição.</p>",
            "<p>Atenciosamente,<br>Clínica Magnólia - Dra. Thalita Menezes</p>",
        ]
        corpo_html = "<html><body>" + "\n".join(linhas_html) + "</body></html>"

        return self._enviar_email(
            booking.uid,
            booking.email,
            "Consulta remarcada - Clínica Magnólia",
            corpo_texto,
            corpo_html,
            contexto="remarcação",
        )
