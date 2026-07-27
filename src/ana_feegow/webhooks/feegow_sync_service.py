from ana_feegow.client import FeegowClient
from ana_feegow.services.agendamento_service import agendar_consulta
from ana_feegow.services.cancelamento_service import cancelar_consulta
from ana_feegow.services.remarcacao_service import remarcar_consulta
from ana_feegow.tools.create_patient import criar_paciente
from ana_feegow.tools.patients import buscar_paciente


def _find_id(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    if isinstance(value, dict):
        for key in (
            "agendamento_id",
            "appointment_id",
            "patient_id",
            "paciente_id",
            "id",
        ):
            candidate = _find_id(value.get(key))
            if candidate:
                return candidate
        for key in ("content", "paciente", "agendamento", "data"):
            candidate = _find_id(value.get(key))
            if candidate:
                return candidate
        for item in value.values():
            candidate = _find_id(item)
            if candidate:
                return candidate
    if isinstance(value, list):
        for item in value:
            candidate = _find_id(item)
            if candidate:
                return candidate
    return None


class FeegowSyncService:
    def __init__(self, client=None):
        self.client = client or FeegowClient()

    def ensure_patient(self, booking):
        result = buscar_paciente(cpf=booking.cpf, client=self.client)
        patient_id = _find_id(result)
        if not patient_id:
            result = buscar_paciente(telefone=booking.celular, client=self.client)
            patient_id = _find_id(result)
        if patient_id:
            return patient_id

        result = criar_paciente(
            nome=booking.nome,
            cpf=booking.cpf,
            nascimento=booking.nascimento,
            celular=booking.celular,
            email=booking.email,
            client=self.client,
        )
        patient_id = _find_id(result)
        if not patient_id:
            raise RuntimeError("Feegow não retornou o ID da paciente.")
        return patient_id

    def create_booking(self, booking):
        patient_id = self.ensure_patient(booking)
        result = agendar_consulta(
            paciente_id=patient_id,
            tipo_consulta=booking.tipo_consulta,
            data=booking.data,
            horario=booking.horario,
            celular=booking.celular,
            email=booking.email,
            notas=f"Cal.com UID: {booking.uid}. {booking.notas}".strip(),
            client=self.client,
        )
        if not result.get("success"):
            raise RuntimeError(f"Falha ao criar agendamento Feegow: {result}")
        appointment_id = _find_id(result.get("content"))
        if not appointment_id:
            raise RuntimeError("Feegow não retornou o ID do agendamento.")
        return appointment_id

    def reschedule_booking(self, appointment_id: int, booking):
        result = remarcar_consulta(
            agendamento_id=appointment_id,
            data=booking.data,
            horario=booking.horario,
            client=self.client,
        )
        # O Feegow pode recusar a remarcação (agenda ocupada, agendamento
        # já cancelado etc.) respondendo HTTP 200 com "success": false no
        # corpo - igual acontece na criação. Sem essa checagem, marcaríamos
        # a reserva como remarcada no nosso banco mesmo sem nada ter mudado
        # de fato na agenda da clínica.
        if not result.get("success"):
            raise RuntimeError(f"Falha ao remarcar agendamento Feegow: {result}")
        return result

    def cancel_booking(self, appointment_id: int):
        result = cancelar_consulta(
            agendamento_id=appointment_id,
            client=self.client,
        )
        # Mesmo raciocínio da remarcação: sem essa checagem, uma recusa do
        # Feegow (HTTP 200 com "success": false) seria tratada como
        # cancelamento bem-sucedido no nosso banco.
        if not result.get("success"):
            raise RuntimeError(f"Falha ao cancelar agendamento Feegow: {result}")
        return result
