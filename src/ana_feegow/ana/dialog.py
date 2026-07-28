from ana_feegow.ana.conversation import Conversation
from ana_feegow.ana.decision import decidir
from ana_feegow.ana.knowledge import RESPOSTAS
from ana_feegow.errors import FeegowError
from ana_feegow.tools.availability import consultar_horarios
from ana_feegow.ana.service import identificar_servico
from ana_feegow.services.agendamento_service import agendar_consulta
from ana_feegow.services.retorno_service import (
    link_consulta_presencial,
    link_consulta_retorno,
    verificar_elegibilidade_retorno,
)
from ana_feegow.tools.identify import identificar_paciente


def responder(telefone: str, mensagem: str):

    conv = Conversation(telefone)

    acao = decidir(mensagem)

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

        try:

            resultado = agendar_consulta(
                paciente_id=paciente["paciente"]["patient_id"],
                tipo_consulta=conv.data["tipo_consulta"],
                data=conv.data["data"],
                horario=mensagem + ":00",
                notas="Agendado pela ANA",
            )

            conv.next("finalizado")

            return (
                f"Consulta agendada com sucesso!\n"
                f"ID: {resultado['content']['agendamento_id']}"
            )

        except Exception as e:

            erro = str(e)

            if "409" in erro:
                return (
                    "Esse horário não está mais disponível. "
                    "Escolha outro horário, por favor."
                )

            raise

    return "Não consegui entender."
