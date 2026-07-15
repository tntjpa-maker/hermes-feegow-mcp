from fastmcp import FastMCP
import traceback
from pathlib import Path

from ana_feegow.ana.dialog import responder

LOG = Path("/tmp/mcp_error.log")
BASE = Path(__file__).resolve().parents[3] / "data" / "knowledge" / "BASE_UNICA_ANA.md"

mcp = FastMCP("magnolia-clinic")


from ana_feegow.conversation.knowledge_service import KnowledgeService

@mcp.tool
def consultar_base_conhecimento(pergunta: str) -> str:
    """
    Base Oficial da Clínica Magnólia.

    Utilize esta ferramenta SEMPRE que a paciente fizer perguntas sobre:

    • clínica
    • médica
    • consultas
    • valores
    • procedimentos
    • DIU
    • implantes
    • pagamento
    • convênio
    • endereço
    • retorno
    • horários
    • políticas
    • orientações
    • dúvidas gerais

    Envie SEMPRE a pergunta completa da paciente.

    Nunca resuma a pergunta.

    A ferramenta localizará automaticamente o capítulo correto da Base Oficial.
    """
    return KnowledgeService.search(pergunta)


@mcp.tool
def atender_paciente(
    telefone: str,
    mensagem: str,
    historico_recente: str = "",
):
    print("=" * 80)
    print("MCP -> atender_paciente")
    print("telefone:", telefone)
    print("mensagem:", mensagem)
    print("historico:", historico_recente)
    print("=" * 80)

    """
    ÚNICO ponto de entrada operacional da ANA.

    Utilize esta ferramenta SEMPRE que a paciente:

    • desejar agendar
    • perguntar sobre disponibilidade
    • escolher datas
    • escolher horários
    • confirmar horários
    • remarcar
    • cancelar
    • responder perguntas feitas anteriormente pela ANA
    • enviar informações para cadastro
    • responder "sim", "não", "pode", "esse", "qualquer horário", "próxima semana", etc.

    Nunca responda essas mensagens diretamente.

    Nunca diga que irá consultar agenda.

    Nunca diga que encontrou horários.

    Nunca invente disponibilidade.

    Sempre encaminhe para esta ferramenta.

    Envie sempre:

    telefone
    mensagem
    historico_recente
    """

    try:
        print(f"[MCP] telefone={telefone} mensagem={mensagem!r}")

        return responder(
            telefone=telefone,
            mensagem=mensagem,
            historico_recente=historico_recente,
        )

    except Exception:
        with open(LOG, "a") as f:
            traceback.print_exc(file=f)
            f.write("\n-----------------------------\n")
        raise


if __name__ == "__main__":
    mcp.run()
