# Regras de Negócio da ANA

## Objetivo

Centralizar todas as regras operacionais da plataforma.

A Feegow executa operações.

A ANA toma decisões.

------------------------------------------------------------

# AGENDAMENTO

O paciente poderá:

- Agendar consulta
- Remarcar consulta
- Confirmar pagamento

A ANA deverá verificar disponibilidade antes de qualquer reserva.

------------------------------------------------------------

# RESERVA

Ao selecionar um horário:

- Criar agendamento na Feegow
- Alterar status para 208 (Aguardando pagamento)
- Registrar evento "reserva_criada"
- Iniciar contador de 30 minutos

------------------------------------------------------------

# PAGAMENTO

A ANA deverá enviar:

- PIX
- Link de pagamento por cartão

O paciente possui:

30 minutos

para enviar o comprovante.

------------------------------------------------------------

# LEMBRETE

Após 25 minutos:

Enviar mensagem informando que restam 5 minutos para conclusão do pagamento.

------------------------------------------------------------

# CONFIRMAÇÃO

Após validação do pagamento:

Alterar status para:

7

Marcado - confirmado

Registrar evento:

pagamento_confirmado

Enviar confirmação ao paciente.

------------------------------------------------------------

# REMARCAÇÃO

Permitida automaticamente.

Regra:

Até 2 horas antes da consulta.

Fluxo:

Consultar horários

↓

Paciente escolhe

↓

Criar novo agendamento

↓

Alterar antigo para Status 15

↓

Registrar evento

↓

Enviar confirmação

------------------------------------------------------------

# BLOQUEIO DE REMARCAÇÃO

Se faltar menos de:

2 horas

A ANA não remarca.

Encaminha para a secretária.

------------------------------------------------------------

# CANCELAMENTO

A ANA NÃO cancela consultas.

O cancelamento é responsabilidade da secretária.

A ANA apenas encaminha a solicitação.

------------------------------------------------------------

# STATUS UTILIZADOS

1

Marcado - não confirmado

7

Marcado - confirmado

15

Remarcado

208

Aguardando pagamento

------------------------------------------------------------

# EVENTOS

reserva_criada

pagamento_iniciado

pagamento_confirmado

consulta_remarcada

------------------------------------------------------------

# PRINCÍPIOS

Toda regra pertence à ANA.

A Feegow apenas registra o resultado das decisões.

