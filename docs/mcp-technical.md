# MCP Feegow — Documentação Técnica

## Objetivo

O MCP é a camada de integração entre a ANA (Hermes Agent) e o Feegow.

Toda regra de negócio permanece na ANA.

O MCP apenas executa operações no Feegow.

---

# Arquitetura

Paciente

↓

WhatsApp Hermes

↓

ANA

↓

MCP Feegow

↓

API Feegow

↓

Feegow

---

# Ferramentas implementadas

## Pacientes

✓ buscar_paciente()

✓ identificar_paciente()

✓ criar_paciente()

## Agenda

✓ consultar_horarios()

⏳ criar_agendamento()

⏳ consultar_agendamento()

⏳ remarcar_agendamento()

## Status

✓ listar_status()

✓ alterar_status()

---

# Endpoints validados

GET /professional/list

GET /patient/list

POST /patient/create

GET /appoints/available-schedule

GET /appoints/status

POST /appoints/statusUpdate

POST /appoints/new-appoint

---

# Fluxo oficial

WhatsApp

↓

Telefone

↓

buscar_paciente()

↓

Paciente existe?

├── SIM

│

└── NÃO

↓

Paciente deseja agendar?

↓

criar_paciente()

↓

consultar_horarios()

↓

criar_agendamento()

↓

Status 208

↓

Pagamento

↓

Status 7

---

# Serviços

Consulta Presencial

Consulta Online

Consulta Híbrida

Os demais itens da clínica serão tratados como procedimentos adicionais.

---

# Regras

Retorno até 30 dias.

Após 30 dias:

Nova consulta.

Particular.

WhatsApp é o canal oficial.

Local único.

Profissional inicial:

Dra. Thalita Menezes.

---

# Estrutura

src/

ana_feegow/

client.py

config.py

tools/

professionals.py

patients.py

identify.py

create_patient.py

availability.py

appointments.py

status.py

tests/

docs/

---

# Descobertas importantes

- telefone é o parâmetro correto da busca.
- celular não realiza filtro.
- CPF é obrigatório para criar paciente.
- tipo=P para consulta de horários.
- data no formato d-m-Y.
- Feegow é a única fonte da verdade.

---

# Objetivo Sprint 1

✓ Buscar paciente

✓ Criar paciente

✓ Consultar horários

⏳ Criar agendamento

⏳ Alterar status

⏳ Remarcar

