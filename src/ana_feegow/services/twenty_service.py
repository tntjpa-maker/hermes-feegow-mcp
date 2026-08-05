"""Integracao ANA (Hermes) <-> Twenty CRM.

Implementa o "Contrato de Integracao - ANA (Hermes) <-> Twenty" (doc no
Drive: Secretaria IA/hermes_twenti/hermestwentycontratointegracao.md).

Todas as funcoes publicas sao "best effort": qualquer falha de rede/API
e capturada e logada, sem nunca interromper o atendimento da paciente no
WhatsApp. O CRM e um efeito colateral, nao um requisito do fluxo de
conversa.
"""

import logging
import os
import re
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

TWENTY_BASE_URL = os.environ.get("TWENTY_BASE_URL", "https://crm.magnoliasdm.com.br")
TWENTY_API_KEY = os.environ.get("TWENTY_API_KEY")
TWENTY_TIMEOUT = 8

# Intencoes (decision.py) que sinalizam interesse comercial real - usadas
# para decidir quando disparar o Fluxo 1 (ver contrato, secao 2, criterio
# "Para NAO criar oportunidade"). Deliberadamente NAO inclui "informacao"
# (fallback generico de decision.py para qualquer mensagem nao reconhecida,
# incluindo "oi"/saudacoes) nem "atendimento_humano" (tratado a parte).
INTENCOES_COMERCIAIS = {
    "agendamento",
    "preco",
    "consulta_hibrida_info",
    "consulta_online_info",
    "consulta_presencial_info",
    "convenio",
    "avaliacoes",
    "obstetricia",
}

# Estados da maquina de conversa (dialog.py) em que a paciente ja esta
# dentro do fluxo de agendamento - tambem contam como comercial mesmo que
# a mensagem da vez nao bata em nenhuma palavra-chave especifica.
ESTADOS_COMERCIAIS = {"aguardando_motivo", "aguardando_modalidade_retorno"}


def _configurado() -> bool:
    if not TWENTY_API_KEY:
        logger.warning("TWENTY_API_KEY nao configurada - integracao com o Twenty desativada.")
        return False
    return True


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {TWENTY_API_KEY}",
        "Content-Type": "application/json",
    }


def _agora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def normalizar_telefone_e164(telefone: str) -> str:
    """Normaliza para E.164 assumindo Brasil (+55) quando o numero de
    digitos for compativel com DDD+numero (10 ou 11 digitos). Numeros que
    ja vem com codigo de pais, ou formatos atipicos (ex.: identificadores
    internos do WhatsApp), sao apenas prefixados com "+" sem alteracao."""
    digitos = re.sub(r"\D", "", telefone or "")
    if not digitos:
        return ""
    if not digitos.startswith("55") and len(digitos) <= 11:
        digitos = "55" + digitos
    return f"+{digitos}"


def e_intencao_comercial(intencao: str, conv_state: str) -> bool:
    return intencao in INTENCOES_COMERCIAIS or conv_state in ESTADOS_COMERCIAIS


def _get(path: str, params: dict = None):
    resp = requests.get(
        f"{TWENTY_BASE_URL}{path}",
        headers=_headers(),
        params=params,
        timeout=TWENTY_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _post(path: str, payload: dict):
    resp = requests.post(
        f"{TWENTY_BASE_URL}{path}",
        headers=_headers(),
        json=payload,
        timeout=TWENTY_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _patch(path: str, payload: dict):
    resp = requests.patch(
        f"{TWENTY_BASE_URL}{path}",
        headers=_headers(),
        json=payload,
        timeout=TWENTY_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def buscar_pessoa_por_whatsapp(whatsapp_e164: str):
    data = _get(
        "/rest/people",
        params={"filter": f'whatsapp[eq]:"{whatsapp_e164}"', "limit": 1},
    )
    registros = data.get("data", {}).get("people", []) or []
    return registros[0] if registros else None


def criar_pessoa(whatsapp_e164: str, first_name: str, last_name: str, source: str = "WHATSAPP"):
    agora = _agora_iso()
    payload = {
        "name": {"firstName": first_name, "lastName": last_name},
        "whatsapp": whatsapp_e164,
        "source": source,
        "tipoDeContato": "LEAD",
        "firstcontactat": agora,
        "lastinteractionat": agora,
    }
    data = _post("/rest/people", payload)
    return data.get("data", {}).get("createPerson")


def atualizar_interacao_pessoa(person_id: str):
    _patch(f"/rest/people/{person_id}", {"lastinteractionat": _agora_iso()})


def buscar_pessoa_por_id(person_id: str) -> dict | None:
    """Busca uma Person no Twenty pelo id. Retorna None se a integracao nao
    estiver configurada, se person_id for vazio, ou se a chamada falhar
    (best effort - nunca levanta excecao)."""
    if not _configurado() or not person_id:
        return None
    try:
        data = _get(f"/rest/people/{person_id}")
        return (data.get("data", {}) or {}).get("person")
    except Exception:
        logger.exception(
            "Falha ao buscar pessoa por id (Twenty) para person_id=%s", person_id
        )
        return None


def numero_whatsapp_da_oportunidade(oportunidade: dict) -> str | None:
    """Resolve o numero de WhatsApp (apenas digitos, com DDI) da paciente
    dona de uma oportunidade, a partir do relacionamento pointOfContact
    (Person) da oportunidade. Usado pelos checkpoints de recuperacao de leads
    para montar o chatId do envio real de WhatsApp para a paciente. Retorna
    None se nao for possivel resolver (best effort - nunca levanta excecao)."""
    person_id = (oportunidade or {}).get("pointOfContactId")
    if not person_id:
        return None
    pessoa = buscar_pessoa_por_id(person_id)
    whatsapp = (pessoa or {}).get("whatsapp") or ""
    digitos = re.sub(r"\D", "", whatsapp)
    return digitos or None


def buscar_oportunidade_aberta(person_id: str):
    data = _get(
        "/rest/opportunities",
        params={
            "filter": f"pointOfContactId[eq]:{person_id}",
            "orderBy": "createdAt[DescNullsLast]",
            "limit": 10,
        },
    )
    registros = data.get("data", {}).get("opportunities", []) or []
    for oportunidade in registros:
        stage = oportunidade.get("stage")
        if stage not in ("PERDIDO", "ATENDIMENTO_REALIZADO"):
            return oportunidade
    return None


def criar_oportunidade(person_id: str, nome_contato: str):
    payload = {
        "name": f"Consulta ginecológica — {nome_contato}",
        "pointOfContactId": person_id,
        "stage": "EM_ATENDIMENTO",
        "serviceOfInterest": "Consulta ginecológica",
    }
    data = _post("/rest/opportunities", payload)
    return data.get("data", {}).get("createOpportunity")


def garantir_pessoa_e_oportunidade(telefone: str, nome: str = None, source: str = "WHATSAPP"):
    """Fluxo 1 do contrato: garante Person + Opportunity aberta para o
    telefone informado, criando o que faltar. Retorna (person_id,
    opportunity_id) ou (None, None) se a integracao nao estiver disponivel
    ou qualquer chamada falhar - nunca levanta excecao."""
    if not _configurado():
        return None, None

    try:
        whatsapp = normalizar_telefone_e164(telefone)
        if not whatsapp:
            return None, None

        nome_exibicao = nome or f"WhatsApp {telefone}"
        first_name, _, last_name = nome_exibicao.partition(" ")
        last_name = last_name or "(WhatsApp)"

        pessoa = buscar_pessoa_por_whatsapp(whatsapp)
        if pessoa is None:
            pessoa = criar_pessoa(whatsapp, first_name, last_name, source=source)
        else:
            atualizar_interacao_pessoa(pessoa["id"])

        if pessoa is None:
            return None, None

        person_id = pessoa["id"]

        oportunidade = buscar_oportunidade_aberta(person_id)
        if oportunidade is None:
            oportunidade = criar_oportunidade(person_id, nome_exibicao)

        opportunity_id = oportunidade["id"] if oportunidade else None
        return person_id, opportunity_id
    except Exception:
        logger.exception("Falha no Fluxo 1 (Twenty) para telefone=%s", telefone)
        return None, None


def montar_link_com_metadata(link_base: str, opportunity_id: str = None) -> str:
    """Embute ?metadata[opportunityId]=<id> no link do Cal.com (contrato,
    secao 4.4) - o elo entre a oportunidade no Twenty e a reserva que o
    servico FastAPI (cal-feegow-webhooks) vai processar depois."""
    if not opportunity_id:
        return link_base
    separador = "&" if "?" in link_base else "?"
    return f"{link_base}{separador}metadata[opportunityId]={opportunity_id}"


def registrar_link_enviado(opportunity_id: str, person_id: str = None):
    """Fluxo 3 do contrato: marca a oportunidade como link enviado,
    atualiza a pessoa e registra uma nota. Best effort - nunca levanta."""
    if not _configurado() or not opportunity_id:
        return

    try:
        agora = _agora_iso()
        _patch(
            f"/rest/opportunities/{opportunity_id}",
            {"stage": "LINK_DE_AGENDAMENTO_ENVIADO", "linkSentAt": agora},
        )

        if person_id:
            atualizar_interacao_pessoa(person_id)

        nota = _post(
            "/rest/notes",
            {
                "title": "Link de agendamento enviado",
                "bodyV2": {"markdown": "Link de agendamento enviado pela ANA."},
            },
        )
        note_id = nota.get("data", {}).get("createNote", {}).get("id")
        if note_id:
            target = {"noteId": note_id, "targetOpportunityId": opportunity_id}
            if person_id:
                target["targetPersonId"] = person_id
            _post("/rest/noteTargets", target)
    except Exception:
        logger.exception("Falha no Fluxo 3 (Twenty) para opportunity_id=%s", opportunity_id)


# Motivos de perda: as 5 chaves originais (usadas em producao por
# expiracao.py e sync_handler.py) foram mantidas intactas e as 8 novas
# categorias do documento estrategico da clinica foram adicionadas ao final.
LOSS_REASONS_VALIDOS = (
    "PAGAMENTO_EXPIRADO",
    "CANCELAMENTO_PACIENTE",
    "SEM_RESPOSTA",
    "HORARIO_INDISPONIVEL",
    "OUTRO",
    "PRECO",
    "FORMA_DE_PAGAMENTO",
    "NAO_ESTA_PRONTA_PARA_INICIAR",
    "DECIDIU_POR_OUTRO_PROFISSIONAL",
    "DISTANCIA_LOCALIZACAO",
    "DIFICULDADE_TECNICA",
    "CONTATO_DUPLICADO",
    "ATENDIMENTO_INADEQUADO",
)

TEMPERATURA_VALIDOS = ("QUENTE", "MORNO", "FRIO")

ORIGEM_LEAD_VALIDOS = ("INSTAGRAM", "INDICACAO", "GOOGLE", "OUTRO")



def listar_oportunidades_para_concluir(buffer_horas: int = 2):
    """Retorna oportunidades no estagio 'Agendado e pago' cujo horario da
    consulta (scheduledAt) ja passou ha mais de `buffer_horas`. Usado pelo
    job periodico que marca 'Atendimento realizado'. Best effort - retorna
    lista vazia se a integracao nao estiver disponivel ou a chamada falhar."""
    if not _configurado():
        return []
    try:
        data = _get(
            "/rest/opportunities",
            {
                "filter": "stage[eq]:AGENDADO_E_PAGO",
                "limit": 200,
            },
        )
        registros = data.get("data", {}).get("opportunities", []) or []
        limite = datetime.now(timezone.utc) - timedelta(hours=buffer_horas)
        elegiveis = []
        for oportunidade in registros:
            scheduled_raw = oportunidade.get("scheduledAt")
            if not scheduled_raw:
                continue
            try:
                scheduled_dt = datetime.fromisoformat(str(scheduled_raw).replace("Z", "+00:00"))
            except ValueError:
                continue
            if scheduled_dt <= limite:
                elegiveis.append(oportunidade)
        return elegiveis
    except Exception:
        logger.exception("Falha ao listar oportunidades para concluir (Twenty)")
        return []

def registrar_reserva_aguardando_pagamento(opportunity_id: str, payment_deadline_at: str = None) -> None:
    """Estagio 'Reserva aguardando pagamento': marcado quando o Cal.com cria a
    reserva (BOOKING_CREATED) para uma consulta paga e o checkout do PagBank
    e gerado. Best effort - qualquer falha e apenas logada, nunca levanta."""
    if not _configurado() or not opportunity_id:
        return
    try:
        payload = {
            "stage": "RESERVA_AGUARDANDO_PAGAMENTO",
            "paymentStatus": "PENDING",
        }
        if payment_deadline_at:
            payload["paymentDeadlineAt"] = payment_deadline_at
        _patch(f"/rest/opportunities/{opportunity_id}", payload)
    except Exception:
        logger.exception(
            "Falha ao registrar reserva aguardando pagamento (Twenty) para opportunity_id=%s",
            opportunity_id,
        )


def registrar_agendado_e_pago(
    opportunity_id: str,
    feegow_appointment_id: str = None,
    pagbank_transaction_id: str = None,
    scheduled_at: str = None,
    cal_booking_uid: str = None,
) -> None:
    """Estagio 'Agendado e pago': marcado quando o PagBank confirma o
    pagamento e o agendamento e criado no Feegow. Best effort - qualquer
    falha e apenas logada, nunca levanta."""
    if not _configurado() or not opportunity_id:
        return
    try:
        payload = {
            "stage": "AGENDADO_E_PAGO",
            "paymentStatus": "PAID",
            "paidAt": _agora_iso(),
        }
        if feegow_appointment_id:
            payload["feegowAppointmentId"] = str(feegow_appointment_id)
        if pagbank_transaction_id:
            payload["pagbankTransactionId"] = str(pagbank_transaction_id)
        if scheduled_at:
            payload["scheduledAt"] = scheduled_at
        if cal_booking_uid:
            payload["calBookingUid"] = cal_booking_uid
        _patch(f"/rest/opportunities/{opportunity_id}", payload)
    except Exception:
        logger.exception(
            "Falha ao registrar agendado e pago (Twenty) para opportunity_id=%s",
            opportunity_id,
        )


def registrar_atendimento_realizado(opportunity_id: str) -> None:
    """Estagio 'Atendimento realizado': marcado apos o horario da consulta ja
    ter passado. Best effort - qualquer falha e apenas logada, nunca levanta."""
    if not _configurado() or not opportunity_id:
        return
    try:
        _patch(
            f"/rest/opportunities/{opportunity_id}",
            {"stage": "ATENDIMENTO_REALIZADO", "completedAt": _agora_iso()},
        )
    except Exception:
        logger.exception(
            "Falha ao registrar atendimento realizado (Twenty) para opportunity_id=%s",
            opportunity_id,
        )


def registrar_perdido(opportunity_id: str, loss_reason: str = "OUTRO") -> None:
    """Estagio 'Perdido': marcado quando a reserva e cancelada pela paciente
    ou o pagamento expira sem confirmacao (ou qualquer outro caminho que
    leve a oportunidade a ser perdida - esta e a unica funcao que muda o
    stage para PERDIDO). Antes do PATCH, busca o stage atual da oportunidade
    e grava em 'ondeParou' (Onde parou) para permitir reconstruir de qual
    estagio o lead saiu do funil. Best effort - qualquer falha e apenas
    logada, nunca levanta."""
    if not _configurado() or not opportunity_id:
        return
    if loss_reason not in LOSS_REASONS_VALIDOS:
        loss_reason = "OUTRO"
    try:
        payload = {"stage": "PERDIDO", "lossReason": loss_reason}
        try:
            atual = _get(f"/rest/opportunities/{opportunity_id}")
            estagio_atual = (atual.get("data", {}).get("opportunity", {}) or {}).get(
                "stage"
            )
            if estagio_atual and estagio_atual != "PERDIDO":
                payload["ondeParou"] = estagio_atual
        except Exception:
            logger.exception(
                "Falha ao buscar stage atual antes de marcar perdido (Twenty) "
                "para opportunity_id=%s",
                opportunity_id,
            )
        _patch(f"/rest/opportunities/{opportunity_id}", payload)
    except Exception:
        logger.exception(
            "Falha ao registrar perdido (Twenty) para opportunity_id=%s",
            opportunity_id,
        )



def registrar_temperatura(opportunity_id: str, temperatura: str) -> None:
    """Grava a temperatura do lead (Quente/Morno/Frio), inferida pela Ana a
    partir do interesse demonstrado na conversa. Best effort - qualquer falha
    e apenas logada, nunca levanta e nunca interrompe o atendimento."""
    if not _configurado() or not opportunity_id:
        return
    if temperatura not in TEMPERATURA_VALIDOS:
        return
    try:
        _patch(f"/rest/opportunities/{opportunity_id}", {"temperatura": temperatura})
    except Exception:
        logger.exception(
            "Falha ao registrar temperatura (Twenty) para opportunity_id=%s",
            opportunity_id,
        )


def registrar_origem_lead(opportunity_id: str, origem: str) -> None:
    """Grava a origem do lead (Instagram/Indicacao/Google/Outro), classificada
    a partir da resposta da paciente a pergunta 'como conheceu a Dra.
    Thalita'. Best effort - qualquer falha e apenas logada, nunca levanta."""
    if not _configurado() or not opportunity_id:
        return
    if origem not in ORIGEM_LEAD_VALIDOS:
        origem = "OUTRO"
    try:
        _patch(f"/rest/opportunities/{opportunity_id}", {"origemDoLead": origem})
    except Exception:
        logger.exception(
            "Falha ao registrar origem do lead (Twenty) para opportunity_id=%s",
            opportunity_id,
        )



def listar_oportunidades_link_enviado_para_followup(minutos: int = 60):
    """Varre oportunidades no estagio 'Link de agendamento enviado' cujo
    linkSentAt ja passou de `minutos` e que ainda nao tem uma task de
    follow-up criada (campo followUpCriadoEm vazio). Retorna lista vazia se
    a integracao nao estiver disponivel ou a chamada falhar."""
    if not _configurado():
        return []
    try:
        data = _get(
            "/rest/opportunities",
            {
                "filter": "stage[eq]:LINK_DE_AGENDAMENTO_ENVIADO",
                "limit": 200,
            },
        )
        registros = data.get("data", {}).get("opportunities", []) or []
        limite = datetime.now(timezone.utc) - timedelta(minutes=minutos)
        elegiveis = []
        for oportunidade in registros:
            if oportunidade.get("followUpCriadoEm"):
                continue
            link_sent_raw = oportunidade.get("linkSentAt")
            if not link_sent_raw:
                continue
            try:
                link_sent_dt = datetime.fromisoformat(
                    str(link_sent_raw).replace("Z", "+00:00")
                )
            except ValueError:
                continue
            if link_sent_dt <= limite:
                elegiveis.append(oportunidade)
        return elegiveis
    except Exception:
        logger.exception(
            "Falha ao listar oportunidades (link enviado) para follow-up (Twenty)"
        )
        return []


def listar_oportunidades_reserva_pendente_para_followup(minutos_antes_expirar: int = 10):
    """Varre oportunidades no estagio 'Reserva aguardando pagamento' cujo
    paymentDeadlineAt esta a `minutos_antes_expirar` minutos (ou menos) de
    expirar - ou seja, ja passou tempo suficiente dentro da janela de
    pagamento de 30min (ver RESERVA_EXPIRA_MINUTOS_PADRAO em app.py) - e que
    ainda nao tem uma task de follow-up criada. Oportunidades sem
    paymentDeadlineAt preenchido (registros antigos, anteriores a esta fase)
    sao ignoradas. Retorna lista vazia se a integracao nao estiver disponivel
    ou a chamada falhar."""
    if not _configurado():
        return []
    try:
        data = _get(
            "/rest/opportunities",
            {
                "filter": "stage[eq]:RESERVA_AGUARDANDO_PAGAMENTO",
                "limit": 200,
            },
        )
        registros = data.get("data", {}).get("opportunities", []) or []
        agora = datetime.now(timezone.utc)
        elegiveis = []
        for oportunidade in registros:
            if oportunidade.get("followUpReservaCriadoEm"):
                continue
            deadline_raw = oportunidade.get("paymentDeadlineAt")
            if not deadline_raw:
                continue
            try:
                deadline_dt = datetime.fromisoformat(
                    str(deadline_raw).replace("Z", "+00:00")
                )
            except ValueError:
                continue
            checkpoint = deadline_dt - timedelta(minutes=minutos_antes_expirar)
            if agora >= checkpoint:
                elegiveis.append(oportunidade)
        return elegiveis
    except Exception:
        logger.exception(
            "Falha ao listar oportunidades (reserva pendente) para follow-up (Twenty)"
        )
        return []


def criar_task_followup(opportunity_id: str, titulo: str, corpo: str = None, campo_controle: str = "followUpCriadoEm") -> None:
    """Cria uma Task no Twenty vinculada a oportunidade (via taskTargets) e
    marca followUpCriadoEm com o horario atual, para que a mesma oportunidade
    nao gere uma nova task a cada nova varredura dos checkpoints de
    recuperacao. Nao envia nenhuma mensagem para a paciente - e apenas uma
    tarefa manual para a equipe humana. Best effort - qualquer falha e apenas
    logada, nunca levanta."""
    if not _configurado() or not opportunity_id:
        return
    try:
        payload = {"title": titulo, "status": "TODO"}
        if corpo:
            payload["bodyV2"] = {"markdown": corpo}
        tarefa = _post("/rest/tasks", payload)
        task_id = tarefa.get("data", {}).get("createTask", {}).get("id")
        if task_id:
            _post(
                "/rest/taskTargets",
                {"taskId": task_id, "targetOpportunityId": opportunity_id},
            )
        _patch(
            f"/rest/opportunities/{opportunity_id}",
            {campo_controle: _agora_iso()},
        )
    except Exception:
        logger.exception(
            "Falha ao criar task de follow-up (Twenty) para opportunity_id=%s",
            opportunity_id,
        )
