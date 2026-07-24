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
