import logging

from ana_feegow.ana.conversation import Conversation
from ana_feegow.ana.decision import (
    decidir,
    inferir_temperatura,
    MENSAGEM_AUTOAGRESSAO,
    MENSAGEM_URGENCIA,
)
from ana_feegow.ana.knowledge import RESPOSTAS
from ana_feegow.errors import FeegowError
from ana_feegow.ana.service import identificar_servico
from ana_feegow.services.retorno_service import (
    link_consulta_hibrida_online,
    link_consulta_hibrida_presencial,
    link_consulta_online,
    link_consulta_presencial,
    link_consulta_retorno,
    link_consulta_retorno_online,
    verificar_elegibilidade_retorno,
)
from ana_feegow.services import twenty_service

import os
import requests
import time

EQUIPE_CHAT_IDS = [
    "5521964577547@s.whatsapp.net",
    "5521985929056@s.whatsapp.net",
]
WHATSAPP_BRIDGE_URL = os.environ.get("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3000")

# TTL (em segundos) que a Ana fica em modo de espera apos um pedido de
# atendimento humano (#sech) antes de retomar o atendimento automatico.
HUMANO_TTL_SEGUNDOS = 45 * 60

# TTL (em segundos) para uma conversa parada no meio do fluxo de
# agendamento (por exemplo, a paciente nunca respondeu "como voce
# conheceu a Dra. Thalita?"). Sem isso, uma mensagem nova sem nenhuma
# relacao com aquele contexto - enviada horas ou dias depois - seria
# silenciosamente interpretada como resposta a pergunta que ficou
# pendente, fazendo a Ana "deduzir" (por exemplo) que a consulta e
# presencial sem nunca perguntar de novo. Ver reset em responder().
CONVERSATION_TTL_SEGUNDOS = 3 * 60 * 60

logger = logging.getLogger(__name__)


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


def notificar_paciente(chat_id: str, mensagem: str) -> bool:
    """Envia uma mensagem de WhatsApp de verdade diretamente para a paciente
    (nao para a equipe), reaproveitando o mesmo WHATSAPP_BRIDGE_URL e o mesmo
    endpoint /send de notificar_equipe. Usado pelos checkpoints de
    recuperacao de leads (link enviado / reserva pendente aguardando
    pagamento) para tentar reengajar a paciente automaticamente, alem da
    Task manual criada para a equipe. Best effort: nunca levanta excecao;
    retorna True se o bridge respondeu com sucesso (2xx), False caso
    contrario (e loga o erro)."""
    try:
        resp = requests.post(
            f"{WHATSAPP_BRIDGE_URL}/send",
            json={"chatId": chat_id, "message": mensagem},
            timeout=5,
        )
        resp.raise_for_status()
        return True
    except Exception:
        logger.exception(
            "Falha ao notificar paciente via WhatsApp (chat_id=%s)", chat_id
        )
        return False


def _sincronizar_twenty(telefone: str, conv, intencao: str) -> None:
    """Fluxo 1 do contrato ANA <-> Twenty: garante Person + Opportunity
    abertos no CRM sempre que a conversa tiver intencao comercial real.
    Best effort - qualquer falha e apenas logada, nunca interrompe o
    atendimento da paciente."""
    if not twenty_service.e_intencao_comercial(intencao, conv.state):
        return

    person_id, opportunity_id = twenty_service.garantir_pessoa_e_oportunidade(telefone)
    if person_id:
        conv.update("twenty_person_id", person_id)
    if opportunity_id:
        conv.update("twenty_opportunity_id", opportunity_id)


def _link_com_metadata_e_registro(conv, link_base: str) -> str:
    """Fluxo 3 do contrato ANA <-> Twenty: embute o opportunityId no link
    do Cal.com e registra no CRM que o link foi enviado. Best effort -
    se o Twenty nao estiver configurado ou a oportunidade nao existir,
    apenas retorna o link original sem modificacao."""
    opportunity_id = conv.data.get("twenty_opportunity_id")
    person_id = conv.data.get("twenty_person_id")
    twenty_service.registrar_link_enviado(opportunity_id, person_id)
    return twenty_service.montar_link_com_metadata(link_base, opportunity_id)


def _classificar_origem_lead(mensagem: str) -> str:
    """Classifica a origem do lead a partir de palavras-chave na resposta da
    paciente a pergunta 'como conheceu a Dra. Thalita'. Matching simples de
    palavras-chave e aceitavel nesta fase - o importante e o campo existir e
    ser preenchido na maioria dos casos, nao a sofisticacao da deteccao."""
    msg = mensagem.lower()
    if "insta" in msg:
        return "INSTAGRAM"
    if "indic" in msg or "amiga" in msg:
        return "INDICACAO"
    if "google" in msg or "pesquisa" in msg:
        return "GOOGLE"
    return "OUTRO"


def responder(telefone: str, mensagem: str):

    conv = Conversation(telefone)

    # Conversa ja finalizada (agendamento anterior concluido) ou parada no
    # meio do fluxo ha mais de CONVERSATION_TTL_SEGUNDOS: tratamos como uma
    # conversa nova em vez de continuar de onde parou. "aguardando_humano"
    # fica de fora porque ja tem seu proprio TTL dedicado logo abaixo.
    if conv.state not in ("inicio", "aguardando_humano"):
        conversa_finalizada = conv.state == "finalizado"
        conversa_parada = (
            conv.atualizado_em is not None
            and time.time() - conv.atualizado_em > CONVERSATION_TTL_SEGUNDOS
        )
        if conversa_finalizada or conversa_parada:
            conv.state = "inicio"
            conv.data = {}

    acao = decidir(mensagem)
    intencao = acao.get("intencao")

    # Sinais de alarme clinicos e risco de autoagressao (ver decision.py):
    # tratados antes de qualquer outra logica, inclusive antes da
    # sincronizacao com o Twenty e do pedido explicito de humano, porque a
    # regra da clinica (AGENTS.md, Secao 6) e interromper IMEDIATAMENTE
    # qualquer atendimento comercial em andamento. Nao alteramos
    # conv.state: se a paciente continuar a conversa depois, o fluxo em
    # andamento (se houver) continua de onde estava.
    if acao.get("acao") == "EMERGENCIA":
        notificar_equipe(telefone, mensagem, "Sinal de alarme clinico (urgencia)")
        return MENSAGEM_URGENCIA

    if acao.get("acao") == "AUTOAGRESSAO":
        notificar_equipe(telefone, mensagem, "Risco de autoagressao/crise emocional")
        conv.update("humano_ts", time.time())
        conv.next("aguardando_humano")
        return MENSAGEM_AUTOAGRESSAO

    _sincronizar_twenty(telefone, conv, intencao)

    # Temperatura do lead (Quente/Morno/Frio): best effort, nunca deve
    # interromper o atendimento da paciente se a chamada ao Twenty falhar.
    opportunity_id = conv.data.get("twenty_opportunity_id")
    if opportunity_id:
        try:
            temperatura = inferir_temperatura(mensagem, acao)
            twenty_service.registrar_temperatura(opportunity_id, temperatura)
        except Exception:
            logger.exception(
                "Falha ao registrar temperatura (best effort) para telefone=%s",
                telefone,
            )

    if acao.get("acao") == "HUMANO":
        notificar_equipe(telefone, mensagem, "Pediu atendimento humano")
        conv.update("humano_ts", time.time())
        conv.next("aguardando_humano")
        return (
            "Claro. Vou encaminhar seu atendimento para nossa secretária "
            "humana. Ela vai te responder por aqui assim que possível."
        )

    if conv.state == "aguardando_humano":
        humano_ts = conv.data.get("humano_ts", 0)
        if time.time() - humano_ts < HUMANO_TTL_SEGUNDOS:
            return (
                "Nossa equipe já foi avisada e vai te responder por aqui em "
                "breve. Se preferir, pode continuar me contando o que precisa "
                "que eu ajudo no que for possível."
            )
        conv.next("inicio")

    if intencao == "informacao" and conv.state == "inicio":
        notificar_equipe(
            telefone,
            mensagem,
            "Pergunta fora da base de conhecimento oficial",
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
        # "aguardando_motivo" abaixo.
        return (
            "Oi! 😊Aqui é a Ana, da Clínica Magnólia — assistente da "
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
                link = _link_com_metadata_e_registro(conv, link_consulta_presencial())
                return (
                    "Não consegui confirmar sua elegibilidade para retorno "
                    "gratuito no momento, mas você pode agendar normalmente "
                    "pelo link abaixo:\n\n"
                    f"{link}"
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
            link = _link_com_metadata_e_registro(conv, link_consulta_presencial())
            return (
                "Verifiquei aqui e o prazo para retorno gratuito (30 dias após "
                "a última consulta) já passou, então este agendamento será "
                "tratado como uma nova consulta.\n\n"
                "Você pode agendar pelo link abaixo:\n\n"
                f"{link}"
            )

        # Consulta nova (não é retorno): a ANA nunca pergunta data nem
        # horário - ela identifica o tipo de serviço e envia direto o link
        # do Cal.com correspondente, para a paciente escolher livremente o
        # melhor dia e horário por conta própria. A reserva (sinal de 20%)
        # e a confirmação do agendamento no Feegow acontecem depois, pelo
        # webhook do Cal.com (ver
        # ana_feegow.webhooks.feegow_sync_service.FeegowSyncService).
        # A híbrida tem dois links dedicados no Cal.com (um para quando a
        # primeira etapa é presencial, outro para quando é online), ambos
        # mapeados no Feegow para o procedimento/valor da híbrida - ver
        # ana_feegow.webhooks.cal_parser._consultation_type. A segunda
        # etapa (retorno) não é cobrada nem enviada pela ANA; a paciente
        # agenda por conta própria depois, usando o link de retorno comum.
        conv.next("aguardando_modalidade_nova")
        return (
            "Para eu te ajudar melhor, essa consulta seria presencial, "
            "online ou híbrida (um pacote com atendimento presencial e "
            "online)?"
        )

    if conv.state == "aguardando_modalidade_nova":
        # A paciente pode ja ter indicado a modalidade na propria mensagem
        # que virou "motivo" (ex: "na verdade quero consulta hibrida"),
        # antes da ANA reperguntar "presencial, online ou hibrida?" aqui.
        # Se a resposta a essa pergunta nao repetir a palavra-chave (ex:
        # "quero agendar", "sim", "pode ser"), classificar so pela mensagem
        # atual faz identificar_servico() cair no padrao "consulta_presencial"
        # por omissao - perdendo a intencao ja explicitada e pulando a
        # pergunta de qual etapa da hibrida agendar primeiro (ver
        # Achado: paciente pede hibrida, ANA nunca pergunta presencial/
        # online da 1a etapa e manda o link presencial direto). Por isso
        # combinamos o motivo original com a resposta atual ao classificar.
        motivo_original = conv.data.get("motivo", "")
        tipo_consulta = identificar_servico(f"{motivo_original} {mensagem}")
        conv.update("tipo_consulta", tipo_consulta)

        if tipo_consulta == "consulta_hibrida":
            conv.next("aguardando_modalidade_hibrida")
            return (
                "A consulta híbrida é um pacote com um atendimento "
                "presencial e um atendimento online, pelo mesmo valor da "
                "consulta presencial. A primeira etapa (que vamos "
                "agendar agora) vai ser presencial ou online? A segunda "
                "etapa (retorno) você mesma agenda depois, sem custo "
                "adicional."
            )

        conv.next("aguardando_origem")
        return (
            "Antes de te mandar o link, como você conheceu a Dra. "
            "Thalita? (Instagram, indicação, Google...)"
        )

    if conv.state == "aguardando_modalidade_hibrida":
        primeira_etapa = (
            "online"
            if any(
                x in mensagem.lower()
                for x in ["online", "vídeo", "video", "teleconsulta"]
            )
            else "presencial"
        )
        conv.update("hibrida_primeira_etapa", primeira_etapa)
        conv.next("aguardando_origem")
        return (
            "Antes de te mandar o link, como você conheceu a Dra. "
            "Thalita? (Instagram, indicação, Google...)"
        )

    if conv.state == "aguardando_origem":
        conv.next("finalizado")

        # Origem do lead: best effort, nunca deve interromper o
        # atendimento da paciente se a chamada ao Twenty falhar.
        origem = _classificar_origem_lead(mensagem)
        opportunity_id = conv.data.get("twenty_opportunity_id")
        if opportunity_id:
            try:
                twenty_service.registrar_origem_lead(opportunity_id, origem)
            except Exception:
                logger.exception(
                    "Falha ao registrar origem do lead (best effort) para "
                    "telefone=%s",
                    telefone,
                )

        tipo_consulta = conv.data.get("tipo_consulta")
        if tipo_consulta == "consulta_hibrida":
            primeira_etapa = conv.data.get("hibrida_primeira_etapa")
            link_base = (
                link_consulta_hibrida_online()
                if primeira_etapa == "online"
                else link_consulta_hibrida_presencial()
            )
        elif tipo_consulta == "consulta_online":
            link_base = link_consulta_online()
        else:
            link_base = link_consulta_presencial()
        link = _link_com_metadata_e_registro(conv, link_base)

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
            link = _link_com_metadata_e_registro(conv, link_consulta_retorno_online())
            return (
                "Perfeito! Você pode agendar seu retorno online sem custo "
                "pelo link abaixo:\n\n"
                f"{link}"
            )
        link = _link_com_metadata_e_registro(conv, link_consulta_retorno())
        return (
            "Perfeito! Você pode agendar seu retorno presencial sem custo "
            "pelo link abaixo:\n\n"
            f"{link}"
        )

    return "Não consegui entender."
