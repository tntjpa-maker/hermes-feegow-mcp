from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class CalBooking:
    uid: str
    booking_id: int | None
    event_type_id: int | None
    tipo_consulta: str
    data: str
    horario: str
    nome: str
    email: str
    cpf: str
    nascimento: str
    celular: str
    notas: str
    opportunity_id: str = ""


def _value(container: dict, key: str, default=""):
    item = container.get(key, default)
    if isinstance(item, dict):
        return item.get("value", item.get("valor", default))
    return item


def _digits(value) -> str:
    return "".join(filter(str.isdigit, str(value or "")))


def _birth_date(value) -> str:
    text = str(value or "").strip()
    if not text:
        # Alguns tipos de evento (ex.: "Consulta Retorno") não coletam data
        # de nascimento no formulário do Cal.com, pois pressupõem paciente
        # já cadastrada na Feegow - ver parse_booking() e
        # feegow_sync_service.ensure_patient().
        return ""
    digits = _digits(text)
    if len(digits) == 8:
        try:
            return datetime.strptime(digits, "%d%m%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError("Data de nascimento inválida.")


def _consultation_type(payload: dict) -> str:
    event_id = payload.get("eventTypeId")
    slug = str(payload.get("type", "")).lower()
    # Precisa vir ANTES da checagem isolada de "retorno" logo abaixo: o slug
    # do evento "Consulta Retorno Online" (drathalita/consulta-retorno-online)
    # contém tanto "retorno" quanto "online", e sem essa checagem combinada
    # primeiro ele cairia no ramo de retorno presencial, perdendo a
    # sinalização de telemedicina (ver FeegowSyncService.create_booking).
    if "retorno" in slug and "online" in slug:
        return "consulta_retorno_online"
    # eventTypeId 9 = "Consulta Retorno" (cal.magnoliasdm.com.br/drathalita/consulta-retorno).
    # Consulta de retorno sem cobrança - ver sync_handler.handle() e
    # ana_feegow.services.retorno_service.
    if event_id == 9 or "consulta-retorno" in slug or "retorno" in slug:
        return "consulta_retorno"
    if event_id == 7 or "niteroi" in slug or "presencial" in slug:
        return "consulta_presencial"
    if "hibrid" in slug:
        return "consulta_hibrida"
    if "online" in slug:
        return "consulta_online"
    raise ValueError(f"Tipo de evento Cal.com não mapeado: {event_id}/{slug}")


def parse_booking(envelope: dict) -> CalBooking:
    payload = envelope.get("payload") or {}
    responses = payload.get("responses") or {}
    user_fields = payload.get("userFieldsResponses") or {}

    opportunity_id = str((payload.get("metadata") or {}).get("opportunityId", "") or "")

    def answer(key, default=""):
        return _value(user_fields, key, _value(responses, key, default))

    attendees = payload.get("attendees") or []
    attendee = attendees[0] if attendees else {}
    nome = str(answer("name", attendee.get("name", ""))).strip()
    email = str(answer("email", attendee.get("email", ""))).strip()
    cpf = _digits(answer("cpf"))
    celular = _digits(answer("celular") or answer("attendeePhoneNumber"))
    nascimento = _birth_date(answer("data_nascimento"))
    start = datetime.fromisoformat(
        str(payload["startTime"]).replace("Z", "+00:00")
    ).astimezone(ZoneInfo("America/Sao_Paulo"))

    tipo_consulta = _consultation_type(payload)

    if not payload.get("uid"):
        raise ValueError("UID da reserva ausente.")
    if tipo_consulta in ("consulta_retorno", "consulta_retorno_online"):
        # Retorno (presencial ou online) não cobra e pressupõe paciente já
        # cadastrada na Feegow (ver
        # retorno_service.verificar_elegibilidade_retorno) - o formulário do
        # Cal.com para esses eventos só coleta nome/email/celular, sem CPF
        # nem data de nascimento.
        if not nome or not email or not celular:
            raise ValueError("Dados obrigatórios da paciente ausentes.")
    elif not nome or not email or not cpf or not celular:
        raise ValueError("Dados obrigatórios da paciente ausentes.")

    return CalBooking(
        uid=str(payload["uid"]),
        booking_id=payload.get("bookingId"),
        event_type_id=payload.get("eventTypeId"),
        tipo_consulta=tipo_consulta,
        data=start.strftime("%Y-%m-%d"),
        horario=start.strftime("%H:%M:%S"),
        nome=nome,
        email=email,
        cpf=cpf,
        nascimento=nascimento,
        celular=celular,
        notas=str(answer("notes", payload.get("additionalNotes", "")) or ""),
        opportunity_id=opportunity_id,
    )
