from datetime import datetime, timedelta

from ana_feegow.services.availability_service import listar_horarios_disponiveis


def listar_datas_disponiveis(
    tipo_consulta: str,
    data_inicio: str,
    dias_busca: int = 30,
):

    inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()

    datas = []

    for i in range(dias_busca):

        dia = inicio + timedelta(days=i)

        disponibilidade = listar_horarios_disponiveis(
            tipo_consulta=tipo_consulta,
            data_inicio=dia.isoformat(),
            data_fim=dia.isoformat(),
        )

        if disponibilidade.get("slots"):

            datas.append(
                {
                    "data": dia.isoformat(),
                    "slots": disponibilidade["slots"],
                }
            )

    return datas
