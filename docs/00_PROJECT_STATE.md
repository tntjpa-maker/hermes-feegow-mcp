# ANA - Estado Atual do Projeto

Versão: 0.2.0

Data: 07/07/2026

Status Geral:
Em desenvolvimento.

--------------------------------------------------

MÓDULOS IMPLEMENTADOS

✓ Cliente Feegow

✓ Busca de pacientes

✓ Busca por telefone

✓ Cadastro de pacientes

✓ Atualização de pacientes

✓ Listagem de profissionais

✓ Consulta de horários

✓ Criação de agendamento

✓ Alteração de status

✓ Listagem de status

--------------------------------------------------

WORKFLOWS

✓ Reserva

✓ Pagamento

✓ Confirmação

✓ Remarcação

--------------------------------------------------

MANAGERS

✓ Payment Manager

--------------------------------------------------

PERSISTÊNCIA

✓ Reserva Store

✓ Event Store

--------------------------------------------------

REGRAS DE NEGÓCIO

Reserva

Status 208

Prazo:
30 minutos

Após confirmação:

Status 7

Remarcação

Permitida até:

2 horas antes da consulta

Cancelamento

Não realizado pela ANA.

Responsável:

Secretária.

--------------------------------------------------

EVENTOS

✓ reserva_criada

✓ pagamento_iniciado

✓ pagamento_confirmado

✓ consulta_remarcada

--------------------------------------------------

PRÓXIMO SPRINT

Conversation Manager

Session Manager

Scheduler

Evolution API

Prompt Engine

--------------------------------------------------

OBJETIVO

Transformar a ANA em uma secretária virtual autônoma integrada ao Hermes Agent.

