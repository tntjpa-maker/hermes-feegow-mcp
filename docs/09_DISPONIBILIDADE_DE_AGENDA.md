# Disponibilidade de Agenda

## Objetivo

Fornecer à ANA apenas os horários realmente disponíveis para agendamento.

A inteligência de disponibilidade permanece no MCP.

A Feegow fornece apenas os dados brutos da agenda.

---

# Arquitetura

Paciente
    ↓
ANA
    ↓
AvailabilityService
    ├── consultar_horarios()
    │       ↓
    │   /appoints/search
    │
    └── Schedule
            ↓
      Grade da médica

↓

Horários disponíveis

---

# Fluxo

1. ANA identifica intenção de agendamento.

2. AvailabilityService consulta:

GET /appoints/search

3. Recebe todos os agendamentos do período.

4. Carrega a grade oficial da médica.

5. Gera slots.

6. Elimina slots conflitantes.

7. Retorna apenas horários livres.

---

# Componentes

src/ana_feegow/tools/availability.py

Responsável por consultar a agenda ocupada.

---

src/ana_feegow/services/availability_service.py

Responsável pela inteligência de disponibilidade.

---

src/ana_feegow/services/slot_service.py

Responsável por gerar slots da agenda.

---

src/ana_feegow/models/slot.py

Modelo de Slot.

---

src/ana_feegow/settings/schedule.py

Configuração da grade de atendimento.

---

# Decisões Arquiteturais

Não utilizar:

GET /appoints/available-schedule

Motivo:

Retornava agenda vazia mesmo existindo horários livres.

Optou-se por utilizar:

GET /appoints/search

que retorna todos os agendamentos e permite ao MCP calcular a disponibilidade.

Toda a inteligência permanece no MCP.

---

# Estado

Status:

VALIDADO

Testado com agenda real da Dra. Thalita.

Disponibilidade calculada corretamente.

