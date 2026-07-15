import re
from datetime import datetime
from typing import Optional

from ana_feegow.ana.service import identificar_servico
from ana_feegow.services.agendamento_service import agendar_consulta
from ana_feegow.services.calendar_service import listar_datas_disponiveis
from ana_feegow.services.availability_service import (
    listar_horarios_disponiveis,
)
from ana_feegow.tools.identify import identificar_paciente
from ana_feegow.services.agenda_intent import interpretar_agenda
from ana_feegow.services.intent_resolver import resolver_intencao


def _normalizar_data(mensagem: str) -> Optional[str]:
    texto = mensagem.strip()

    formatos = (
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    )

    for formato in formatos:
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            pass

    correspondencia = re.search(
        r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b",
        texto,
    )

    if not correspondencia:
        return None

    dia, mes, ano = correspondencia.groups()

    try:
        return datetime(
            int(ano),
            int(mes),
            int(dia),
        ).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _normalizar_horario(mensagem: str) -> Optional[str]:
    texto = mensagem.strip().lower()

    correspondencia = re.search(
        r"\b([01]?\d|2[0-3])(?:[:h](\d{2}))?\b",
        texto,
    )

    if not correspondencia:
        return None

    hora = int(correspondencia.group(1))
    minuto = int(correspondencia.group(2) or 0)

    if minuto not in (0, 30):
        return None

    return f"{hora:02d}:{minuto:02d}"


def _formatar_data(data: str) -> str:

    formatos = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    )

    for formato in formatos:
        try:
            return datetime.strptime(
                data,
                formato,
            ).strftime("%d/%m/%Y")
        except ValueError:
            pass

    return data


def _formatar_slots(slots: list[str]) -> str:
    return "\n".join(f"• {horario}" for horario in slots)


def executar_agendamento(
    conv,
    telefone: str,
    mensagem: str,
) -> Optional[str]:


    
    if conv.state == "buscando_primeira_vaga":
        conv.next("aguardando_data")
        return executar_agendamento(
            conv,
            telefone,
            "qualquer dia",
        )

    if conv.state == "aguardando_motivo":
        motivo = mensagem.strip()

        conv.update("motivo", motivo)
        conv.goal.preencher("motivo", motivo)
        conv.next("buscando_primeira_vaga")

        return executar_agendamento(
            conv,
            telefone,
            mensagem,
        )

    
    if conv.state == "aguardando_data":

        preferencia = interpretar_agenda(mensagem)

        if preferencia is None:

            data_iso = _normalizar_data(mensagem)

            if not data_iso:
                return (
                    "Pode me informar quando você gostaria da consulta? "
                    "Exemplos: amanhã, próxima semana, qualquer dia, sexta-feira ou 15/08."
                )

        else:
            tipo = preferencia["tipo"]

            if tipo == "MES_ATUAL":
                from datetime import date
                data_iso = date.today().replace(day=1).isoformat()

            elif tipo == "PROXIMO_MES":
                from datetime import date
                hoje = date.today()

                if hoje.month == 12:
                    data_iso = date(hoje.year + 1, 1, 1).isoformat()
                else:
                    data_iso = date(hoje.year, hoje.month + 1, 1).isoformat()

            else:
                data_iso = preferencia.get("inicio")

            conv.update("preferencia", preferencia)
            conv.goal.preencher("preferencia", tipo)
        motivo = conv.data.get("motivo", "consulta presencial")
        tipo_consulta = identificar_servico(motivo)

        calendario = listar_datas_disponiveis(
            tipo_consulta=tipo_consulta,
            data_inicio=data_iso,
            dias_busca=30,
        )

        conv.update(
            "calendario",
            {
                "agenda": calendario
            },
        )

        disponibilidade = listar_horarios_disponiveis(
            tipo_consulta=tipo_consulta,
            data_inicio=data_iso,
            data_fim=data_iso,
        )

        slots = disponibilidade.get("slots", [])

        if not slots:

            disponibilidade = listar_horarios_disponiveis(
                tipo_consulta=tipo_consulta,
                data_inicio=data_iso,
                data_fim=data_iso,
                dias_busca=30,
            )

            slots = disponibilidade.get("slots", [])

            if not slots:
                return (
                    "Não encontrei horários disponíveis nos próximos 30 dias."
                )

            data_disponivel = disponibilidade["available_date"]

        conv.goal.preencher("data", data_disponivel)
        conv.update("data", data_disponivel)
        conv.update("tipo_consulta", tipo_consulta)
        conv.update("horarios", disponibilidade)
        conv.update(
            "calendario",
            {
                "agenda": calendario
            },
        )
        conv.next("aguardando_horario")

        calendario = conv.data.get("calendario", {})

        agenda = calendario.get("agenda", {})

        if len(agenda) > 1:

            lista_datas = "\n".join(
                f"• {_formatar_data(data)}"
                for data in sorted(agenda.keys())
            )

            conv.next("aguardando_data_calendario")

            return (
                "Tenho disponibilidade nas seguintes datas:\n\n"
                f"{lista_datas}\n\n"
                "Qual delas você prefere?"
            )

        lista = _formatar_slots(slots)

        return (
            f"Encontrei estes horários em {_formatar_data(data_disponivel)}:\n\n"
            f"{lista}\n\n"
            "Qual horário você prefere?"
        )

    if conv.state == "aguardando_data_calendario":

        preferencia = interpretar_agenda(mensagem)

        if (
            not preferencia
            or preferencia["tipo"] != "DATA_ESPECIFICA"
        ):
            return (
                "Pode me informar uma das datas disponíveis?"
            )

        data_iso = preferencia["inicio"]

        motivo = conv.data.get("motivo", "consulta presencial")
        tipo_consulta = identificar_servico(motivo)

        disponibilidade = listar_horarios_disponiveis(
            tipo_consulta=tipo_consulta,
            data_inicio=data_iso,
            data_fim=data_iso,
        )

        slots = disponibilidade.get("slots", [])

        if not slots:
            return (
                "Não encontrei horários para essa data. "
                "Pode escolher outra das datas disponíveis?"
            )

        conv.goal.preencher("data", data_iso)
        conv.update("data", data_iso)
        conv.update("horarios", disponibilidade)
        conv.next("aguardando_horario")

        lista = _formatar_slots(slots)

        return (
            f"Tenho estes horários em {_formatar_data(data_iso)}:\n\n"
            f"{lista}\n\n"
            "Qual horário você prefere?"
        )


    if conv.state == "aguardando_horario":

        acao = resolver_intencao(mensagem)

        if acao["tipo"] == "nova_busca":
            conv.next("aguardando_data")
            return executar_agendamento(
                conv=conv,
                telefone=telefone,
                mensagem=mensagem,
            )

        if acao["tipo"] == "primeira_vaga":
            mensagem = "qualquer horário"

        horario = _normalizar_horario(mensagem)

        if not horario:
            return (
                "Pode escolher um dos horários disponíveis ou dizer "
                "'qualquer horário' para que eu selecione a primeira vaga."
            )

        disponibilidade = conv.data.get("horarios", {})
        slots = disponibilidade.get("slots", [])

        if horario not in slots:
            lista = _formatar_slots(slots)

            return (
                "Esse horário não está disponível.\n\n"
                f"Os horários livres são:\n\n{lista}\n\n"
                "Qual deles você prefere?"
            )

        conv.goal.preencher("horario", horario)
        conv.update("horario", horario)

        paciente = identificar_paciente(telefone)

        if not paciente.get("existe"):
            conv.next("cadastro_pendente")

            return (
                "Esse horário está disponível. "
                "Agora preciso realizar seu cadastro para concluir a reserva. "
                "Qual é o seu nome completo?"
            )

        conv.next("aguardando_pagamento")

        return (
            "Perfeito! 😊\n\n"
            "O horário está disponível.\n\n"
            "Para confirmar sua reserva, é necessário o pagamento antecipado de 20% do valor da consulta.\n\n"
            "Esse valor será abatido integralmente no pagamento realizado no consultório.\n\n"
            'Após realizar o pagamento, responda apenas: "PAGUEI".'
        )

        conv.reset()

        agendamento_id = resultado.get("content", {}).get(
            "agendamento_id"
        )

        return (
            f"Consulta reservada para "
            f"{_formatar_data(conv.data['data'])} às {horario}."
            + (
                f"\nCódigo da reserva: {agendamento_id}."
                if agendamento_id
                else ""
            )
        )


    if conv.state == "aguardando_pagamento":

        if mensagem.strip().lower() != "paguei":
            return (
                'Assim que concluir o pagamento, responda apenas: "PAGUEI".'
            )

        paciente = identificar_paciente(telefone)

        try:
            resultado = agendar_consulta(
                paciente_id=paciente["paciente"]["patient_id"],
                tipo_consulta=conv.data["tipo_consulta"],
                data=conv.data["data"],
                horario=f"{conv.data['horario']}:00",
                notas="Agendado pela ANA",
            )

        except Exception as erro:

            if "409" in str(erro):
                conv.next("aguardando_data")

                return (
                    "Esse horário acabou de ser ocupado. "
                    "Qual outra data você prefere?"
                )

            raise

        data_confirmada = conv.data["data"]
        horario_confirmado = conv.data["horario"]

        agendamento_id = resultado.get("content", {}).get(
            "agendamento_id"
        )

        conv.reset()

        return (
            f"Consulta reservada para "
            f"{_formatar_data(data_confirmada)} às {horario_confirmado}."
            + (
                f"\nCódigo da reserva: {agendamento_id}."
                if agendamento_id
                else ""
            )
        )

    return None
