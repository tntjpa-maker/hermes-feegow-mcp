from typing import Optional

from ana_feegow.workflows.agendamento_v2 import executar_agendamento
from ana_feegow.workflows.remarcacao import executar_remarcacao
from ana_feegow.services.notificar_secretaria import notificar_secretaria


WORKFLOWS = {
    "appointment": executar_agendamento,
    "remarcacao": executar_remarcacao,
}


class WorkflowManager:

    @staticmethod
    def execute(
        conv,
        telefone: str,
        mensagem: str,
    ) -> Optional[str]:

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

        acao = decisao.get("acao")
        intencao = decisao.get("intencao")

        if acao == "AGENDAR":
            conv.set_workflow("appointment")

            if intencao in ("retorno", "primeira_consulta"):
                conv.update("motivo", intencao)
                conv.next("aguardando_para_quem")

                return (
                    "Perfeito!\n\n"
                    "A consulta será para você ou para outra pessoa?"
                )

            conv.next("aguardando_motivo")

            return (
                "Perfeito! 😊\n\n"
                "É sua primeira consulta ou retorno?"
            )

        if acao == "HUMANO":

            notificar_secretaria(
                telefone_paciente=telefone,
                motivo="Paciente solicitou atendimento humano.",
            )

            conv.enable_human()

            return (
                "Perfeito! 😊\n\n"
                "Já encaminhei sua conversa para nossa secretária. "
                "Ela continuará seu atendimento em instantes."
            )

        if acao == "CANCELAR":
            conv.enable_human()

            return (
                "Vou encaminhar seu pedido de cancelamento "
                "para nossa secretária humana."
            )

        if acao == "REMARCAR":
            conv.set_workflow("remarcacao")
            conv.next("inicio")

            return executar_remarcacao(
                conv=conv,
                telefone=telefone,
                mensagem="",
            )

        return None
