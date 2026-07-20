import re
from datetime import date, datetime
from typing import Optional

from ana_feegow.events.event_bus import emitir_evento

from ana_feegow.ana.service import identificar_servico
from ana_feegow.services.agendamento_service import agendar_consulta
from ana_feegow.services.status_service import confirmar_pagamento
from ana_feegow.services.calendar_service import listar_datas_disponiveis
from ana_feegow.services.availability_service import listar_horarios_disponiveis
from ana_feegow.services.agenda_intent import interpretar_agenda
from ana_feegow.services.intent_resolver import resolver_intencao
from ana_feegow.tools.identify import identificar_paciente
from ana_feegow.tools.create_patient import criar_paciente


def _formatar_data(data: str) -> str:
    return datetime.fromisoformat(data).strftime("%d/%m/%Y")


def _formatar_slots(slots):
    return "\n".join(f"• {h}" for h in slots)


def executar_agendamento(
    conv,
    telefone: str,
    mensagem: str,
) -> Optional[str]:

    estado = conv.state

    if estado == "aguardando_motivo":

        conv.update("motivo", mensagem)

        conv.next("aguardando_preferencia")

        conv.next("aguardando_para_quem")

        return (
            "Perfeito!\n\n"
            "A consulta será para você ou para outra pessoa?"
        )

    if estado == "aguardando_preferencia":

        preferencia = interpretar_agenda(mensagem)

        if preferencia is None:
            return (
                "Pode me informar quando você gostaria da consulta?\n\n"
                "Exemplos:\n"
                "• qualquer dia\n"
                "• próxima semana\n"
                "• este mês\n"
                "• 29/07"
            )

        motivo = conv.data.get("motivo", "consulta presencial")
        tipo_consulta = identificar_servico(motivo)

        inicio = preferencia.get("inicio")

        if inicio is None:
            inicio = date.today().isoformat()

        agenda = listar_datas_disponiveis(
            tipo_consulta=tipo_consulta,
            data_inicio=inicio,
            dias_busca=30,
        )

        if not agenda:
            return "Não encontrei disponibilidade nos próximos 30 dias."

        conv.update("agenda", agenda)
        conv.next("aguardando_data")

        datas = "\n".join(
            f"• {_formatar_data(d)}"
            for d in agenda.keys()
        )

        return (
            "Tenho disponibilidade nas seguintes datas:\n\n"
            f"{datas}\n\n"
            "Qual delas você prefere?"
        )


    if estado == "aguardando_para_quem":

        resposta = mensagem.strip().lower()

        if any(x in resposta for x in (
            "outra",
            "outra pessoa",
            "meu filho",
            "minha filha",
            "meu marido",
            "minha esposa",
            "minha mãe",
            "meu pai",
            "minha irmã",
            "meu irmão",
        )):

            conv.update("para_terceiro", True)
            conv.next("identificando_paciente")

            return (
                "Perfeito!\n\n"
                "Qual é o nome completo da pessoa que fará a consulta?"
            )

        conv.update("para_terceiro", False)

        paciente = identificar_paciente(telefone)

        if paciente.get("existe"):
            conv.update("patient_id", paciente["paciente"]["patient_id"])
            conv.next("aguardando_preferencia")

            return (
                "Perfeito! 😊\n\n"
                "Quando você gostaria da consulta?\n\n"
                "Exemplos:\n"
                "• qualquer dia\n"
                "• próxima semana\n"
                "• este mês\n"
                "• 29/07"
            )

        conv.next("aguardando_nome")

        return (
            "Perfeito!\n\n"
            "Qual é o seu nome completo?"
        )


    if estado == "aguardando_data":

        if not conv.data.get("_evento_inicio_agendamento"):

            emitir_evento(
                "lead_agendamento_iniciado",
                telefone=telefone,
            )

            conv.update("_evento_inicio_agendamento", True)


        pref = interpretar_agenda(mensagem)

        if (
            pref is None
            or pref.get("tipo") != "DATA_ESPECIFICA"
        ):
            return "Escolha uma das datas apresentadas."

        data = pref["inicio"]

        motivo = conv.data.get("motivo", "consulta presencial")
        tipo_consulta = identificar_servico(motivo)

        disponibilidade = listar_horarios_disponiveis(
            tipo_consulta=tipo_consulta,
            data_inicio=data,
            data_fim=data,
        )

        slots = disponibilidade.get("slots", [])

        if not slots:
            return (
                "Essa data não possui mais horários disponíveis. "
                "Escolha outra data."
            )

        conv.update("data", data)
        conv.update("horarios", disponibilidade)
        conv.next("aguardando_horario")

        return (
            f"Tenho estes horários em {_formatar_data(data)}:\n\n"
            f"{_formatar_slots(slots)}\n\n"
            "Qual horário você prefere?"
        )

    if estado == "aguardando_horario":

        acao = resolver_intencao(mensagem)

        if acao.get("tipo") == "nova_busca":
            conv.next("aguardando_preferencia")
            return (
                "Sem problemas. Quando você gostaria da consulta?"
            )

        if acao.get("tipo") == "primeira_vaga":
            mensagem = conv.data["horarios"]["slots"][0]

        horario = mensagem.strip()

        disponibilidade = conv.data["horarios"]
        slots = disponibilidade.get("slots", [])

        if horario not in slots:

            return (
                "Esse horário não está disponível.\n\n"
                f"{_formatar_slots(slots)}\n\n"
                "Qual horário você prefere?"
            )

        conv.update("horario", horario)

        paciente = identificar_paciente(telefone)

        if not paciente.get("existe"):

            conv.next("aguardando_nome")

            return (
                "Esse horário está disponível.\n\n"
                "Qual é o seu nome completo?"
            )

        resultado = agendar_consulta(
            paciente_id=conv.data["patient_id"],
            tipo_consulta=identificar_servico(conv.data["motivo"]),
            data=conv.data["data"],
            horario=conv.data["horario"],
            retorno=conv.data["motivo"] == "retorno",
        )

        print("\n==============================")
        print("MOTIVO =", conv.data.get("motivo"))
        print("RETORNO =", conv.data.get("motivo") == "retorno")
        print("==============================")

        print("\nRESULTADO AGENDAMENTO =", resultado)

        if resultado.get("duplicate"):
            conv.reset()

            return (
                "Verifiquei que você já possui um agendamento para essa agenda. 😊\n\n"
                "Se desejar, posso ajudá-lo a remarcar ou cancelar essa consulta."
            )

        if not resultado.get("success"):
            return (
                "Ocorreu um problema ao realizar o agendamento.\n\n"
                "Vamos tentar novamente em alguns instantes."
            )

        conv.update("agendamento_id", resultado["content"]["agendamento_id"])

        emitir_evento(
            "reserva_criada",
            telefone=telefone,
            data=conv.data.get("data"),
            horario=conv.data.get("horario"),
            nome=conv.data.get("nome"),
            agendamento_id=conv.data["agendamento_id"],
        )

        conv.next("aguardando_pagamento")

        return (
            "Perfeito!\n\n"
            "Sua reserva foi realizada com sucesso.\n\n"
            "Agora preciso da confirmação do pagamento."
        )

    if estado == "aguardando_nome":

        conv.update("nome", mensagem.strip())

        conv.next("aguardando_nascimento")

        return "Qual sua data de nascimento?"


    if estado == "aguardando_nascimento":

        nascimento = mensagem.strip()

        conv.update("data_nascimento", nascimento)

        conv.next("aguardando_cpf")

        return "Qual é o seu CPF?"
        
    if estado == "aguardando_cpf":

        cpf = "".join(filter(str.isdigit, mensagem))

        conv.update("cpf", cpf)

        resultado = criar_paciente(
            nome=conv.data["nome"],
            cpf=conv.data["cpf"],
            nascimento="-".join(reversed(conv.data["data_nascimento"].split("/"))),
            celular=telefone,
        )



        import json
        from pathlib import Path

        Path("logs").mkdir(exist_ok=True)
        Path("logs/create_patient_response.json").write_text(
            json.dumps(resultado, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        content = resultado.get("content")

        patient_id = None

        if isinstance(content, int):
            patient_id = content

        elif isinstance(content, str) and content.isdigit():
            patient_id = int(content)

        elif isinstance(content, dict):
            patient_id = (
                content.get("patient_id")
                or content.get("paciente_id")
                or content.get("id")
            )

            if not patient_id and isinstance(content.get("paciente"), dict):
                patient_id = (
                    content["paciente"].get("patient_id")
                    or content["paciente"].get("paciente_id")
                    or content["paciente"].get("id")
                )

        if not patient_id:
            raise RuntimeError(
                f"Feegow não retornou patient_id ao criar paciente: {resultado}"
            )

        conv.update("patient_id", patient_id)

        emitir_evento(
            "paciente_criado",
            patient_id=patient_id,
            telefone=telefone,
        )

        conv.next("aguardando_data")

        return executar_agendamento(
            conv,
            telefone,
            "qualquer dia",
        )


    if estado == "aguardando_pagamento":

        if mensagem.strip().lower() != "paguei":
            return 'Quando concluir o pagamento responda apenas: "PAGUEI".'

        try:

            resultado = confirmar_pagamento(
                conv.data["agendamento_id"]
            )

        except Exception as erro:

            if "409" in str(erro):

                conv.next("aguardando_data")

                return (
                    "Esse horário acabou de ser ocupado. "
                    "Escolha outra data."
                )

            raise

        data_confirmada = conv.data["data"]
        horario_confirmado = conv.data["horario"]

        agendamento_id = resultado.get(
            "content",
            {},
        ).get("agendamento_id")

        emitir_evento(
            "lead_convertido",
            telefone=telefone,
            paciente_id=conv.data["patient_id"],
            agendamento_id=agendamento_id,
            data=data_confirmada,
            horario=horario_confirmado,
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
