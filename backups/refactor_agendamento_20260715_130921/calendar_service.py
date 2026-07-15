from collections import OrderedDict
from datetime import date, timedelta

from ana_feegow.services.availability_service import _calcular_disponibilidade
from ana_feegow.tools.availability import consultar_horarios


def listar_datas_disponiveis(
    tipo_consulta: str,
    data_inicio: str,
    dias_busca: int = 30,
):
    inicio = date.fromisoformat(data_inicio)
    fim = inicio + timedelta(days=dias_busca - 1)

    dados = consultar_horarios(
        tipo_consulta=tipo_consulta,
        data_inicio=inicio.isoformat(),
        data_fim=fim.isoformat(),
    )

    agenda = dados["agenda"]
    duracao_consulta = dados["duracao_consulta"]

    datas = OrderedDict()

    for i in range(dias_busca):
        dia = inicio + timedelta(days=i)

        slots = _calcular_disponibilidade(
            agenda=agenda,
            duracao_consulta=duracao_consulta,
            data=dia,
        )

        if slots:
            datas[dia.isoformat()] = slots

    return datas
