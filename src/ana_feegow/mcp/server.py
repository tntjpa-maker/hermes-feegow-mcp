from fastmcp import FastMCP
import traceback
from pathlib import Path

from ana_feegow.ana.dialog import responder

LOG = Path("/tmp/mcp_error.log")
BASE = Path(__file__).resolve().parents[3] / "data" / "knowledge" / "BASE_UNICA_ANA.md"

mcp = FastMCP("magnolia-clinic")


@mcp.tool
def consultar_base_conhecimento() -> str:
    """
    FONTE OFICIAL da Clínica Magnólia.

    Use esta ferramenta SEMPRE que a pergunta envolver:
    - valores
    - consultas
    - procedimentos
    - convênios
    - pagamentos
    - endereço
    - horários
    - retorno
    - serviços
    - informações institucionais

    O texto retornado é a única fonte de verdade.

    Extraia literalmente a informação correspondente.

    Nunca responda por conhecimento próprio.

    Nunca estime valores.

    Nunca diga "pode variar".

    Se a informação existir no documento, utilize exatamente o conteúdo encontrado.
    """
    return BASE.read_text(encoding="utf-8")


@mcp.tool
def atender_paciente(
    telefone: str,
    mensagem: str,
    historico_recente: str = "",
):
    try:
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
