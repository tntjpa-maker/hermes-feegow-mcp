from ana_feegow.ana.conversation import Conversation
from ana_feegow.ana.decision import decidir
from ana_feegow.ana.knowledge import RESPOSTAS
from ana_feegow.errors import FeegowError
from ana_feegow.ana.service import identificar_servico
from ana_feegow.services.retorno_service import (
    link_consulta_online,
    link_consulta_presencial,
    link_consulta_retorno,
    link_consulta_retorno_online,
    verificar_elegibilidade_retorno,
)

import os
import requests

EQUIPE_CHAT_IDS = [
    "5521964577547@s.whatsapp.net",
    "5521985929056@s.whatsapp.net",
]
WHATSAPP_BRIDGE_URL = os.environ.get("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3000")


def notificar_equipe(telefone: str, mensagem: str, motivo: str) -> None:
    """Avisa a equipe humana via WhatsApp quando a ANA nao tem resposta
    pronta na base de conhecimento, ou quando a paciente pede atendimento
    humano diretamente. Falha silenciosamente para nao travar o
    atendimento da paciente caso o aviso nao seja entregue."""
    for chat_id in EQUIPE_CHAT_IDS:
        try:
            requests.post(
                f"{WHATSAPP_BRIDGE_URL}/send",
                json={
                    "chatId": chat_id,
                    "message": (
                        f"[ANA] {motivo}\n"
                        f"Paciente: {telefone}\n"
                        f"Mensagem: {mensagem}"
                    ),
                },
                timeout=5,
            )
        except Exception:
            pass


def responder(telefone: str, mensagem: str):

    conv = Conversation(telefone)

    acao = decidir(mensagem)
    intencao = acao.get("intencao")

    if acao.get("acao") == "HUMANO" or intencao == "informacao":
        notificar_equipe(
            telefone,
            mensagem,
            "Pediu atendimento humano"
            if acao.get("acao") == "HUMANO"
            else "Pergunta fora da base de conhecimento oficial",
        )

    # Perguntas informativas (preço, endereço, convênio, explicação sobre
    # os tipos de consulta) são respondidas diretamente, sem depender do
    # estado atual da conversa - antes desta checagem, "acao" era
    # calculado mas nunca usado, então qualquer pergunta feita fora da
    # sequência esperada (por exemplo "onde fica a clínica?" logo na
    # primeira mensagem, ou "quanto custa?" no meio de um agendamento em
    # andamento) caía sempre na resposta fixa do estado atual, ignorando o
    # que a paciente realmente perguntou.
    if acao.get("acao") == "RESPONDER" and intencao in RESPOSTAS:
        resposta_informativa = RESPOSTAS[intencao]

        if conv.state == "inicio":
            # Na primeira mensagem, além de responder, seguimos com o
            # fluxo normal de boas-vindas para não deixar a conversa presa.
            conv.next("aguardando_motivo")
            return (
                resposta_informativa
                + "\n\nSe quiser, posso te ajudar a agendar."
            )

        # Em qualquer outro estado, respondemos sem alterar o estado atual,
        # para que a próxima mensagem continue o fluxo de agendamento
        # exatamente de onde parou.
        return resposta_informativa

    if conv.state == "inicio":
        conv.next("aguardando_motivo")
        # Saudação humana e neutra - não emenda a pergunta "primeira
        # consulta ou retorno?" logo depois de um "bom dia", porque isso
        # soa como um menu de atendimento automático, não como uma
        # secretária de verdade (ver SOUL.md, seções 1 e 5). O que a
        # paciente disser em seguida já é suficiente para o próximo passo
        # decidir se é retorno ou consulta nova, no estado
        # "aguardando_motivo" logo abaixo.
        return (
            "Oi! 😊 Aqui é a Ana, da Clínica Magnólia — assistente da "
            "Dra. Thalita.\n\n"
            "Como posso te ajudar?"
        )

    if conv.state == "aguardando_motivo":
        conv.update("motivo", mensagem)

        if "retorno" in mensagem.lower():
            try:
                elegibilidade = verificar_elegibilidade_retorno(telefone)
            except FeegowError:
                conv.next("finalizado")
                return (
                    "Não consegui confirmar sua elegibilidade para retorno "
                    "gratuito no momento, mas você pode agendar normalmente "
                    "pelo link abaixo:\n\n"
                    f"{link_consulta_presencial()}"
                )

            conv.update("elegibilidade_retorno", elegibilidade)

            if elegibilidade["elegivel"]:
                conv.next("aguardando_modalidade_retorno")
                return (
                    "Que bom te ver novamente! Como sua última consulta foi há "
                    f"{elegibilidade['dias_desde_ultima']} dia(s), você pode "
                    "agendar seu retorno sem custo. Esse retorno vai ser "
                    "online ou presencial?"
                )

            conv.next("finalizado")
            return (
                "Verifiquei aqui e o prazo para retorno gratuito (30 dias após "
                "a última consulta) já passou, então este agendamento será "
                "tratado como uma nova consulta.\n\n"
                "Você pode agendar pelo link abaixo:\n\n"
                f"{link_consulta_presencial()}"
            )

        # Consulta nova (não é retorno): a ANA nunca pergunta data nem
        # horário - ela identifica o tipo de serviço e envia direto o link
        # do Cal.com correspondente, para a paciente escolher livremente o
        # melhor dia e horário por conta própria. A "híbrida" é uma
        # etiqueta de serviço/preço no Feegow (um pacote com um atendimento
        # presencial e um online), não um link de agenda à parte: por isso
        # ela usa o mesmo link presencial da primeira etapa. A reserva
        # (sinal de 20%) e a confirmação do agendamento no Feegow acontecem
        # depois, pelo webhook do Cal.com (ver
        # ana_feegow.webhooks.feegow_sync_service.FeegowSyncService).
        tipo_consulta = identificar_servico(mensagem)
        conv.update("tipo_consulta", tipo_consulta)
        conv.next("finalizado")

        link = (
            link_consulta_online()
            if tipo_consulta == "consulta_online"
            else link_consulta_presencial()
        )

        return (
            "Você pode escolher o melhor dia e horário direto por este "
            "link:\n\n"
            f"{link}\n\n"
            "Para reservar o horário é cobrado um sinal de 20% do valor da "
            "consulta - esse valor garante sua reserva, e a diferença é "
            "paga somente depois da consulta."
        )

    if conv.state == "aguardando_modalidade_retorno":
        conv.next("finalizado")
        msg = mensagem.lower()
        if any(x in msg for x in ["online", "video", "vídeo", "teleconsulta"]):
            return (
                "Perfeito! Você pode agendar seu retorno online sem custo "
                "pelo link abaixo:\n\n"
                f"{link_consulta_retorno_online()}"
            )
        return (
            "Perfeito! Você pode agendar seu retorno presencial sem custo "
            "pelo link abaixo:\n\n"
            f"{link_consulta_retorno()}"
        )

    return "Não consegui entender."
