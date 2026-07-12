# Disponibilidade de Agenda

## Status

Sprint concluído e validado.

---

# Objetivo

Disponibilizar para a ANA apenas horários realmente livres.

Toda a inteligência permanece dentro do MCP.

A Feegow fornece apenas os dados da agenda.

---

# Arquitetura

Paciente
        │
        ▼
ANA
        │
        ▼
AvailabilityService
        │
        ├── consultar agenda ocupada
        │
        ├── carregar grade de atendimento
        │
        ├── gerar slots
        │
        ├── eliminar conflitos
        │
        ▼
Horários disponíveis

---

# Componentes

src/ana_feegow/tools/availability.py

Consulta os agendamentos existentes.

---

src/ana_feegow/services/availability_service.py

Motor de disponibilidade.

Responsável por:

- consultar agenda
- gerar slots
- calcular conflitos
- retornar horários livres

---

src/ana_feegow/services/slot_service.py

Responsável pela geração dos slots da agenda.

---

src/ana_feegow/models/slot.py

Modelo de Slot.

---

src/ana_feegow/settings/schedule.py

Configuração da agenda do profissional.

---

# Endpoints avaliados

## 1

GET

/api/professional/list

Status:

Utilizado.

Finalidade:

Listagem de profissionais.

Resultado:

Validado.

---

## 2

GET

/api/patient/list

Status:

Utilizado.

Finalidade:

Busca de pacientes.

Resultado:

Validado.

---

## 3

POST

/api/patient/create

Status:

Utilizado.

Finalidade:

Cadastro de pacientes.

Resultado:

Validado.

---

## 4

GET

/api/appoints/available-schedule

Status:

DESCARTADO.

Motivo:

Mesmo existindo horários livres na agenda da médica, retornava:

content: []

Não representa corretamente a agenda operacional da clínica.

Não será utilizado.

---

## 5

GET

/appoints/search

Status:

UTILIZADO.

Finalidade:

Consultar todos os agendamentos do profissional.

Resultado:

Retorna:

- horário
- duração
- procedimento
- profissional
- local
- status
- paciente
- encaixe

A partir desses dados o MCP calcula a disponibilidade.

---

## 6

POST

https://booking.feegow.com/api/working-hours/schedules/batch/preview

Status:

Investigado.

Resultado:

Necessita autenticação diferente da API pública.

Utiliza JWT da aplicação Web.

Não será utilizado na versão atual.

---

# Lógica implementada

1.

Consultar agenda do profissional.

↓

appoints/search

2.

Receber todos os agendamentos.

3.

Carregar grade do profissional.

4.

Gerar slots.

5.

Transformar cada agendamento em intervalo.

6.

Eliminar slots conflitantes.

7.

Retornar apenas horários disponíveis.

---

# Regras atuais

Grade configurável.

Slot configurável.

Consulta pode possuir duração variável.

Conflitos calculados por intervalo.

Não depende do endpoint available-schedule.

---

# Testes realizados

✔ Busca de profissionais

✔ Busca de pacientes

✔ Cadastro de pacientes

✔ Consulta de agenda

✔ Geração de slots

✔ Cálculo de conflitos

✔ Disponibilidade final

Resultado validado com agenda real da Dra. Thalita.

---

# Próximo Sprint

Integrar AvailabilityService ao fluxo da ANA.

Fluxo esperado:

Paciente

↓

Quero marcar consulta

↓

ANA

↓

AvailabilityService

↓

14:30

16:00

16:30

↓

Paciente escolhe horário.

