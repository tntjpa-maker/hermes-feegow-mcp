from ana_feegow.ana.conversation import Conversation
from ana_feegow.ana.decision import decidir
from ana_feegow.ana.knowledge import RESPOSTAS
from ana_feegow.workflows.manager import WorkflowManager


def responder(
    telefone: str,
    mensagem: str,
):
    print("\n### MCP BUILD 2026-07-13 13:35 ###\n")
    conv = Conversation(telefone)

    print("=" * 60)
    print("MENSAGEM :", mensagem)
    print("TELEFONE :", telefone)
    print("WORKFLOW :", conv.workflow)
    print("STATE    :", conv.state)
    print("DATA     :", conv.data)
    print("=" * 60)


    if conv.human_mode:
        return None

    resposta = WorkflowManager.execute(
        conv=conv,
        telefone=telefone,
        mensagem=mensagem,
    )

    if resposta is not None:
        return resposta

    decisao = decidir(mensagem)
    intencao = decisao.get("intencao")

    if intencao in RESPOSTAS:
        return RESPOSTAS[intencao]

    resposta = WorkflowManager.start(
        decisao=decisao,
        conv=conv,
        telefone=telefone,
    )

    if resposta is not None:
        return resposta

    return "Não consegui entender sua solicitação."
