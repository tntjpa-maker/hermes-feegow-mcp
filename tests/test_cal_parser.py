import pytest

from ana_feegow.webhooks.cal_parser import parse_booking


def sample(trigger="BOOKING_PAID"):
    return {
        "triggerEvent": trigger,
        "createdAt": "2026-07-24T09:55:21.579Z",
        "payload": {
            "uid": "cal-uid-1",
            "bookingId": 10,
            "eventTypeId": 7,
            "type": "niteroi",
            "startTime": "2026-07-29T19:30:00+00:00",
            "responses": {
                "name": {"value": "Paciente Teste"},
                "email": {"value": "paciente@example.com"},
                "cpf": {"value": "117.679.937-14"},
                "data_nascimento": {"value": "27051988"},
                "celular": {"value": "(21) 98592-9056"},
                "notes": {"value": "Observação"},
            },
        },
    }


def test_parser_converte_campos_e_fuso():
    booking = parse_booking(sample())
    assert booking.data == "2026-07-29"
    assert booking.horario == "16:30:00"
    assert booking.cpf == "11767993714"
    assert booking.nascimento == "1988-05-27"
    assert booking.celular == "21985929056"
    assert booking.tipo_consulta == "consulta_presencial"


def test_parser_reconhece_evento_de_consulta_retorno_por_event_type_id():
    envelope = sample()
    envelope["payload"]["eventTypeId"] = 9
    envelope["payload"]["type"] = "consulta-retorno"

    booking = parse_booking(envelope)

    assert booking.tipo_consulta == "consulta_retorno"


def test_parser_reconhece_evento_de_consulta_retorno_por_slug():
    envelope = sample()
    # eventTypeId ausente/diferente, mas slug identifica o evento de retorno
    envelope["payload"]["eventTypeId"] = None
    envelope["payload"]["type"] = "drathalita/consulta-retorno"

    booking = parse_booking(envelope)

    assert booking.tipo_consulta == "consulta_retorno"


def test_parser_aceita_consulta_retorno_sem_cpf_e_sem_nascimento():
    # Reproduz o payload real do evento "Consulta Retorno" no Cal.com, que
    # só coleta nome/email/celular - CPF e data de nascimento não existem
    # no formulário (bug real observado em produção em 28/07/2026, ver
    # ensure_patient() em feegow_sync_service.py).
    envelope = sample()
    envelope["payload"]["eventTypeId"] = 9
    envelope["payload"]["type"] = "consulta-retorno"
    envelope["payload"]["responses"] = {
        "name": {"value": "Paciente Retorno"},
        "email": {"value": "retorno@example.com"},
        "celular": {"value": "(21) 98592-9056"},
    }

    booking = parse_booking(envelope)

    assert booking.tipo_consulta == "consulta_retorno"
    assert booking.cpf == ""
    assert booking.nascimento == ""
    assert booking.celular == "21985929056"


def test_parser_recusa_consulta_retorno_sem_celular():
    envelope = sample()
    envelope["payload"]["eventTypeId"] = 9
    envelope["payload"]["type"] = "consulta-retorno"
    envelope["payload"]["responses"] = {
        "name": {"value": "Paciente Retorno"},
        "email": {"value": "retorno@example.com"},
    }

    with pytest.raises(ValueError):
        parse_booking(envelope)


def test_parser_ainda_exige_cpf_para_consulta_presencial_normal():
    envelope = sample()
    envelope["payload"]["responses"]["cpf"] = {"value": ""}

    with pytest.raises(ValueError):
        parse_booking(envelope)


def test_parser_reconhece_evento_de_consulta_online_por_slug():
    envelope = sample()
    envelope["payload"]["eventTypeId"] = None
    envelope["payload"]["type"] = "drathalita/consulta-online"

    booking = parse_booking(envelope)

    assert booking.tipo_consulta == "consulta_online"


def test_parser_exige_cpf_para_consulta_online():
    # Consulta online não é isenta como a de retorno - o formulário do
    # Cal.com para este evento coleta CPF normalmente (paciente pode ser
    # nova), então o parser deve continuar exigindo os mesmos dados da
    # consulta presencial.
    envelope = sample()
    envelope["payload"]["eventTypeId"] = None
    envelope["payload"]["type"] = "drathalita/consulta-online"
    envelope["payload"]["responses"]["cpf"] = {"value": ""}

    with pytest.raises(ValueError):
        parse_booking(envelope)
