from ana_feegow.ana.conversation import Conversation
from ana_feegow.tools.availability import consultar_horarios


def responder(conv: Conversation, mensagem: str):

    if conv.state == "inicio":
        conv.next("aguardando_motivo")
        return (
            "Olá! 😊 Sou a ANA, secretária virtual da Dra. Thalita.\n\n"
            "É sua primeira consulta ou retorno?"
        )

    if conv.state == "aguardando_motivo":
        conv.update("motivo", mensagem)
        conv.next("aguardando_data")
        return "Qual dia você prefere para a consulta? (dd/mm/aaaa)"

    if conv.state == "aguardando_data":
        conv.update("data", mensagem)

        horarios = consultar_horarios(
            "consulta_presencial",
            mensagem,
            mensagem,
        )

        conv.update("horarios", horarios)

        conv.next("aguardando_horario")

        return horarios

    if conv.state == "aguardando_horario":
        conv.update("horario", mensagem)
        conv.next("confirmacao")

        return (
            f"Perfeito!\n"
            f"Vou reservar o horário {mensagem}."
        )

    return "Não consegui entender."
