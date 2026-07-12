from datetime import datetime, timedelta

from ana_feegow.services.slot_service import gerar_slots
from ana_feegow.settings.schedule import SCHEDULE
from ana_feegow.tools.availability import consultar_horarios


def listar_horarios_disponiveis(
    tipo_consulta: str,
    data_inicio: str,
    data_fim: str,
):

    dados = consultar_horarios(
        tipo_consulta,
        data_inicio,
        data_fim,
    )

    agenda = dados["agenda"]
    duracao_consulta = dados["duracao_consulta"]

    resultado = {}

    data = datetime.strptime(data_inicio, "%Y-%m-%d")
    fim = datetime.strptime(data_fim, "%Y-%m-%d")

    while data <= fim:

        chave = data.strftime("%d-%m-%Y")
        weekday = data.weekday()

        resultado[chave] = []

        for periodo in SCHEDULE.get(weekday, []):

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
                    resultado[chave].append(slot.inicio)

        data += timedelta(days=1)

    return resultado
