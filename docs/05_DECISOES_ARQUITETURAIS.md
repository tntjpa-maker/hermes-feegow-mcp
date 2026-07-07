# Decisões Arquiteturais

## 1. Hermes

Hermes será o orquestrador principal.

## 2. ANA

ANA contém a inteligência, regras de negócio e workflows.

## 3. Feegow

Feegow é fonte da verdade para:

- pacientes
- profissionais
- agenda
- status

## 4. MCP

MCP é camada de integração.

Não decide regras.

Apenas executa operações.

## 5. Pagamento

Pagamento não é validado automaticamente no MVP.

Paciente envia comprovante.

ANA valida ou encaminha.

## 6. Reserva

Reserva dura 30 minutos.

Status inicial:

208 - Aguardando pagamento

## 7. Confirmação

Após pagamento:

7 - Marcado confirmado

## 8. Cancelamento

ANA não cancela consulta.

Cancelamento é humano.

## 9. Remarcação

Paciente pode remarcar automaticamente até 2 horas antes.

Após esse prazo:

encaminhar para secretária.

## 10. Event Store

Toda ação importante gera evento.

## 11. Scheduler

Será usado para:

- lembrete de pagamento
- expiração de reserva
- lembrete de consulta
- pós-consulta

## 12. Comunicação

WhatsApp será o canal principal.

## 13. Código

GitHub é a fonte oficial.

## 14. Documentação

Drive contém documentação funcional.

GitHub contém documentação técnica.

