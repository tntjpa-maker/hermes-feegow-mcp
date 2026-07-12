from datetime import datetime, timedelta

from ana_feegow.models.slot import Slot


def gerar_slots(inicio, fim, minutos):

    slots = []

    atual = datetime.strptime(inicio, "%H:%M")
    termino = datetime.strptime(fim, "%H:%M")

    while atual < termino:

        prox = atual + timedelta(minutes=minutos)

        slots.append(
            Slot(
                inicio=atual.strftime("%H:%M"),
                fim=prox.strftime("%H:%M"),
                livre=True,
            )
        )

        atual = prox

    return slots
