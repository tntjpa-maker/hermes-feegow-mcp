# Workflows da ANA

Todos os fluxos da plataforma são implementados como workflows independentes.

Cada workflow possui:

- Entrada
- Regras
- Ferramentas
- Eventos
- Saída

------------------------------------------------------------

WORKFLOW 1

Reserva

Paciente solicita horário

↓

Consultar disponibilidade

↓

Criar agendamento

↓

Status 208

↓

Registrar evento

↓

Iniciar prazo de pagamento

------------------------------------------------------------

WORKFLOW 2

Pagamento

Enviar PIX

↓

Enviar link cartão

↓

Aguardar comprovante

↓

Validar comprovante

↓

Status 7

↓

Registrar evento

↓

Enviar confirmação

------------------------------------------------------------

WORKFLOW 3

Remarcação

Paciente solicita nova data

↓

Verificar prazo

↓

Mais de 2 horas?

↓

SIM

↓

Consultar horários

↓

Paciente escolhe

↓

Criar novo agendamento

↓

Status antigo = 15

↓

Registrar evento

↓

Enviar confirmação

------------------------------------------------------------

Caso:

Menos de 2 horas

↓

Encaminhar para secretária

------------------------------------------------------------

WORKFLOW 4

Solicitação de Cancelamento

Paciente solicita cancelamento

↓

ANA identifica solicitação

↓

Encaminhar para secretária

↓

Fim

A ANA não executa cancelamentos.

------------------------------------------------------------

WORKFLOW 5

Lembrete de Pagamento

Reserva criada

↓

25 minutos

↓

Enviar lembrete

↓

30 minutos

↓

Pagamento recebido?

↓

SIM

↓

Confirmar

↓

NÃO

↓

Marcar reserva como expirada

↓

Notificar paciente

------------------------------------------------------------

WORKFLOW 6

Consulta Agendada

24 horas antes

↓

Enviar lembrete

↓

2 horas antes

↓

Último lembrete

↓

Consulta

------------------------------------------------------------

WORKFLOW 7

Pós Consulta

Consulta finalizada

↓

Enviar agradecimento

↓

Solicitar avaliação

↓

Registrar satisfação

↓

Oferecer retorno quando indicado

------------------------------------------------------------

Princípio

Cada workflow é independente.

A comunicação entre workflows ocorre através do Event Store.

