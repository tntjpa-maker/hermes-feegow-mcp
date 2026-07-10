from fastmcp import FastMCP
import traceback
from pathlib import Path

from ana_feegow.ana.dialog import responder

LOG = Path("/tmp/mcp_error.log")

mcp = FastMCP("magnolia-clinic")


@mcp.tool
def atender_paciente(
    telefone: str,
    mensagem: str,
):
    """
    PONTO DE ENTRADA ÚNICO DA ANA.

    Toda mensagem enviada por um paciente da Clínica Magnólia
    deve obrigatoriamente passar por esta ferramenta antes de
    qualquer resposta do assistente.

    Esta ferramenta é responsável por:

    - identificar a intenção do paciente;
    - responder dúvidas;
    - consultar a base de conhecimento;
    - consultar o Feegow quando necessário;
    - criar cadastros somente quando necessário;
    - realizar agendamentos;
    - encaminhar para atendimento humano quando apropriado.

    O assistente NÃO deve responder diretamente ao paciente sem
    utilizar esta ferramenta.
    """

    try:
        return responder(
            telefone=telefone,
            mensagem=mensagem,
        )

    except Exception:
        with open(LOG, "a") as f:
            traceback.print_exc(file=f)
            f.write("\n-----------------------------\n")

        raise


if __name__ == "__main__":
    mcp.run()
