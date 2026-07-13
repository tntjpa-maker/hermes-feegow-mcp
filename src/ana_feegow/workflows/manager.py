from typing import Optional

from ana_feegow.workflows.agendamento import executar_agendamento


WORKFLOWS = {
    "appointment": executar_agendamento,
}


class WorkflowManager:

    @staticmethod
    def execute(
        conv,
        telefone: str,
        mensagem: str,
    ) -> Optional[str]:
        """
        Executa exclusivamente um workflow já ativo.
        O Decision Engine não participa enquanto houver workflow.
        """

        if not conv.workflow:
            return None

        workflow = WORKFLOWS.get(conv.workflow)

        if not workflow:
            conv.reset()
            return None

        return workflow(
            conv=conv,
            telefone=telefone,
            mensagem=mensagem,
        )

    @staticmethod
    def start(
        decisao: dict,
        conv,
        telefone: str,
    ) -> Optional[str]:
        """
        Inicia um workflow ou executa uma ação operacional
        identificada pelo Decision Engine.
        """

        acao = decisao.get("acao")
        intencao = decisao.get("intencao")

        if acao == "AGENDAR":
            conv.set_workflow("appointment")
            conv.next("aguardando_motivo")

            return (
                "Perfeito! 😊\n\n"
                "É sua primeira consulta ou retorno?"
            )

        if acao == "TIPO_CONSULTA":
            conv.set_workflow("appointment")
            conv.update("motivo", intencao)
            conv.next("aguardando_data")

            return "Qual dia você prefere para a consulta?"

        if acao == "HUMANO":
            conv.enable_human()

            return (
                "Vou encaminhar seu atendimento para "
                "nossa secretária humana."
            )

        if acao == "CANCELAR":
            conv.enable_human()

            return (
                "Vou encaminhar seu pedido de cancelamento "
                "para nossa secretária humana."
            )

        if acao == "REMARCAR":
            return (
                "Posso ajudar com o reagendamento. "
                "Esse fluxo será habilitado na próxima etapa."
            )

        return None
