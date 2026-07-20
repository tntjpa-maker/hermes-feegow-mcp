from datetime import datetime, timedelta

from ana_feegow.services.slot_service import gerar_slots
from ana_feegow.settings.schedule import SCHEDULE
from ana_feegow.tools.availability import consultar_horarios


def _calcular_disponibilidade(
    agenda,
    duracao_consulta,
    data,
):
    """
    Retorna todos os horários livres de um dia.
    Utilizado pelo calendar_service.
    """

    chave = data.strftime("%d-%m-%Y")

    resultado = []

    for periodo in SCHEDULE.get(data.weekday(), []):

        slots = gerar_slots(
            periodo["inicio"],
            periodo["fim"],
            periodo["slot"],
        )

        for slot in slots:

            inicio_slot = datetime.strptime(
                f"{chave} {slot.inicio}",
                "%d-%m-%Y %H:%M",
            )

            fim_consulta = inicio_slot + timedelta(
                minutes=duracao_consulta
            )

            fim_periodo = datetime.strptime(
                f"{chave} {periodo['fim']}",
                "%d-%m-%Y %H:%M",
            )

            if fim_consulta > fim_periodo:
                continue

            livre = True

            for ag in agenda:

                if ag["data"] != chave:
                    continue

                inicio_ag = datetime.strptime(
                    f"{chave} {ag['horario'][:5]}",
                    "%d-%m-%Y %H:%M",
                )

                fim_ag = inicio_ag + timedelta(
                    minutes=ag["duracao"]
                )

                if (
                    inicio_slot < fim_ag
                    and fim_consulta > inicio_ag
                ):
                    livre = False
                    break

            if livre:
                resultado.append(slot.inicio)

    return resultado


def listar_horarios_disponiveis(
    tipo_consulta,
    data_inicio,
    data_fim,
):

    dados = consultar_horarios(
        tipo_consulta,
        data_inicio,
        data_fim,
    )

    agenda = dados["agenda"]
    duracao_consulta = dados["duracao_consulta"]

    try:
        data = datetime.strptime(
            data_inicio,
            "%Y-%m-%d",
        )
    except ValueError:
        data = datetime.strptime(
            data_inicio,
            "%d-%m-%Y",
        )

    slots = _calcular_disponibilidade(
        agenda=agenda,
        duracao_consulta=duracao_consulta,
        data=data,
    )

    return {
        "requested_date": data_inicio,
        "available_date": data_inicio,
        "same_day": True,
        "slots": slots,
    }


def buscar_disponibilidade(
    tipo_consulta,
    data_inicio,
    dias_busca=30,
):
    """
    Novo motor único de disponibilidade.
    Será utilizado por Agendamento e Remarcação.
    """

    from ana_feegow.services.calendar_service import listar_datas_disponiveis

    datas = listar_datas_disponiveis(
        tipo_consulta=tipo_consulta,
        data_inicio=data_inicio,
        dias_busca=dias_busca,
    )

    if not datas:
        return {
            "requested_date": data_inicio,
            "available_date": None,
            "same_day": False,
            "slots": [],
        }

    primeira = next(iter(datas))

    return {
        "requested_date": data_inicio,
        "available_date": primeira,
        "same_day": primeira == data_inicio,
        "slots": datas[primeira],
    }
