from ana_feegow.ana.conversation import Conversation
from ana_feegow.ana.decision import decidir
from ana_feegow.ana.knowledge import RESPOSTAS
from ana_feegow.errors import FeegowError
from ana_feegow.tools.availability import consultar_horarios
from ana_feegow.tools.create_patient import criar_paciente
from ana_feegow.ana.service import identificar_servico
from ana_feegow.services.agendamento_service import agendar_consulta
from ana_feegow.services.retorno_service import (
    link_consulta_presencial,
    link_consulta_retorno,
    verificar_elegibilidade_retorno,
)
from ana_feegow.tools.identify import identificar_paciente
from ana_feegow.utils.response import find_id


def responder(telefone: str, mensagem: str):

    conv = Conversation(telefone)

    acao = decidir(mensagem)
    intencao = acao.get("intencao")

    # Perguntas informativas (preço, endereço, convênio) são respondidas
    # diretamente, sem depender do estado atual da conversa - antes desta
    # checagem, "acao" era calculado mas nunca usado, então qualquer
    # pergunta feita fora da sequência esperada (por exemplo "onde fica a
    # clínica?" logo na primeira mensagem, ou "quanto custa?" no meio de um
    # agendamento em andamento) caía sempre na resposta fixa do estado
    # atual, ignorando o que a paciente realmente perguntou.
    if acao.get("acao") == "RESPONDER" and intencao in RESPOSTAS:
        resposta_informativa = RESPOSTAS[intencao]

        if conv.state == "inicio":
            # Na primeira mensagem, além de responder, seguimos com o
            # fluxo normal de boas-vindas para não deixar a conversa presa.
            conv.next("aguardando_motivo")
            return (
                resposta_informativa
                + "\n\nSe quiser, posso te ajudar a agendar agora. "
                "É sua primeira consulta ou retorno?"
            )

        # Em qualquer outro estado, respondemos sem alterar o estado atual,
        # para que a próxima mensagem continue o fluxo de agendamento
        # exatamente de onde parou.
        return resposta_informativa

    if conv.state == "inicio":
        conv.next("aguardando_motivo")
        return (
            "Olá! 😊 Sou a ANA, secretária virtual da Dra. Thalita.\n\n"
            "É sua primeira consulta ou retorno?"
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
            conv.next("finalizado")

            if elegibilidade["elegivel"]:
                return (
                    "Que bom te ver novamente! Como sua última consulta foi há "
                    f"{elegibilidade['dias_desde_ultima']} dia(s), você pode "
                    "agendar seu retorno sem custo pelo link abaixo:\n\n"
                    f"{link_consulta_retorno()}"
                )

            return (
                "Verifiquei aqui e o prazo para retorno gratuito (30 dias após "
                "a última consulta) já passou, então este agendamento será "
                "tratado como uma nova consulta.\n\n"
                "Você pode agendar pelo link abaixo:\n\n"
                f"{link_consulta_presencial()}"
            )

        conv.next("aguardando_data")
        return "Qual dia você prefere para a consulta? (dd/mm/aaaa)"

    if conv.state == "aguardando_data":
        mensagem = mensagem.replace("/", "-")
        conv.update("data", mensagem)

        tipo_consulta = identificar_servico(conv.data["motivo"])
        conv.update("tipo_consulta", tipo_consulta)

        horarios = consultar_horarios(
            tipo_consulta,
            mensagem,
            mensagem,
        )

        conv.update("horarios", horarios)

        conv.next("aguardando_horario")

        if horarios.get("content"):
            return horarios

        return "Informe o horário desejado (HH:MM)."

    if conv.state == "aguardando_horario":
        conv.update("horario", mensagem)

        paciente = identificar_paciente(telefone)

        if not paciente["existe"]:
            conv.next("cadastro_nome")
            return (
                "Não encontrei seu cadastro.\n\n"
                "Para continuar, informe seu nome completo."
            )

        return _confirmar_agendamento(
            conv=conv,
            paciente_id=paciente["paciente"]["patient_id"],
            horario=mensagem,
        )

    # Cadastro de paciente nova - só é alcançado quando a busca em
    # "aguardando_horario" não encontrou a paciente pelo telefone. Antes
    # desta correção, não havia handler para "cadastro_nome" (nem para os
    # estados seguintes): a resposta pedia o nome, mas a próxima mensagem
    # da paciente caía direto no "Não consegui entender." final, e o
    # cadastro nunca era concluído.
    if conv.state == "cadastro_nome":
        conv.update("nome", mensagem)
        conv.next("cadastro_cpf")
        return "Obrigada! Agora, por favor, informe seu CPF."

    if conv.state == "cadastro_cpf":
        conv.update("cpf", mensagem)
        conv.next("cadastro_nascimento")
        return "Perfeito. Qual sua data de nascimento? (dd/mm/aaaa)"

    if conv.state == "cadastro_nascimento":
        conv.update("nascimento", mensagem.replace("/", "-"))

        try:
            resultado_cadastro = criar_paciente(
                nome=conv.data["nome"],
                cpf=conv.data["cpf"],
                nascimento=conv.data["nascimento"],
                celular=telefone,
            )
        except Exception:
            conv.next("finalizado")
            return (
                "Não consegui concluir seu cadastro agora. Vou encaminhar "
                "seu atendimento para nossa secretária humana."
            )

        paciente_id = find_id(resultado_cadastro)

        if not paciente_id:
            conv.next("finalizado")
            return (
                "Seu cadastro foi enviado, mas não consegui confirmar o "
                "número gerado. Vou encaminhar seu atendimento para nossa "
                "secretária humana para concluir o agendamento."
            )

        return _confirmar_agendamento(
            conv=conv,
            paciente_id=paciente_id,
            horario=conv.data["horario"],
        )

    return "Não consegui entender."


def _confirmar_agendamento(conv: Conversation, paciente_id, horario: str) -> str:
    try:
        resultado = agendar_consulta(
            paciente_id=paciente_id,
            tipo_consulta=conv.data["tipo_consulta"],
            data=conv.data["data"],
            horario=horario + ":00",
            notas="Agendado pela ANA",
        )

        conv.next("finalizado")

        agendamento_id = find_id(resultado)

        return (
            f"Consulta agendada com sucesso!\n"
            f"ID: {agendamento_id}"
        )

    except Exception as e:

        erro = str(e)

        if "409" in erro:
            conv.next("aguardando_horario")
            return (
                "Esse horário não está mais disponível. "
                "Escolha outro horário, por favor."
            )

        raise
