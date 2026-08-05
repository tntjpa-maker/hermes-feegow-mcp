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
from datetime import datetime, timezone

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
