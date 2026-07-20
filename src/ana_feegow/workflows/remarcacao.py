from ana_feegow.services.list_appointments_service import listar_consultas_futuras
from ana_feegow.services.availability_service import buscar_disponibilidade

def _tipo_por_procedimento(procedimento_id: int) -> str:
    mapa = {
        35: "consulta_presencial",
        36: "consulta_hibrida",
        37: "consulta_online",
    }
    return mapa.get(procedimento_id, "consulta_presencial")

from ana_feegow.services.remarcacao_service import remarcar_consulta


def executar_remarcacao(conv, telefone, mensagem):

    #
    # Escolha da consulta
    #
    if conv.state == "inicio":

        consultas = listar_consultas_futuras(telefone)

        if not consultas:
            conv.reset()
            return "Não encontrei consultas futuras para remarcação."

        conv.update("consultas", consultas)
        conv.next("aguardando_consulta")

        texto = "Encontrei estas consultas:\n\n"

        for i, c in enumerate(consultas, 1):
            texto += f"{i}. {c['data']} às {c['horario']}\n"

        texto += "\nQual delas você deseja remarcar?"

        return texto

    #
    # Consulta escolhida
    #
    if conv.state == "aguardando_consulta":

        try:
            indice = int(mensagem.strip()) - 1
        except ValueError:
            return "Informe apenas o número da consulta."

        consultas = conv.data["consultas"]

        if indice < 0 or indice >= len(consultas):
            return "Consulta inválida."

        consulta = consultas[indice]

        conv.update("agendamento_id", consulta["agendamento_id"])
        conv.update("procedimento_id", consulta["procedimento_id"])

        from datetime import date

        horarios = buscar_disponibilidade(
            tipo_consulta=_tipo_por_procedimento(consulta["procedimento_id"]),
            data_inicio=date.today().isoformat(),
        )

        conv.update("horarios", horarios)
        conv.next("aguardando_novo_horario")

        if not horarios["slots"]:
            return "Não encontrei horários disponíveis."

        texto = ""

        if horarios["same_day"]:
            texto += (
                f"Tenho disponibilidade em {horarios['available_date']}:\n\n"
            )
        else:
            texto += (
                f"A próxima disponibilidade é {horarios['available_date']}:\n\n"
            )

        texto += "\n".join(f"• {h}" for h in horarios["slots"])
        texto += "\n\nQual horário você prefere?"

        return texto

    #
    # Horário escolhido
    #
    if conv.state == "aguardando_novo_horario":

        horarios = conv.data["horarios"]

        resultado = remarcar_consulta(
            agendamento_id=conv.data["agendamento_id"],
            data=horarios["available_date"],
            horario=mensagem.strip() + ":00",
        )

        conv.reset()

        return (
            "Consulta remarcada com sucesso! 😊\n\n"
            f"Nova data: {horarios['available_date']}\n"
            f"Horário: {mensagem}"
        )

    return None
