# Arquitetura da ANA

## Visão Geral

A ANA é uma plataforma de agentes especializada em atendimento clínico.

A Feegow é apenas uma camada de integração.

Toda a inteligência permanece na ANA.

------------------------------------------------------------

                    Hermes Agent
                          │
                          ▼
                    Conversation Manager
                          │
                          ▼
                     Session Manager
                          │
                          ▼
                     Workflow Engine
                          │
      ┌───────────────────┼────────────────────┐
      │                   │                    │
      ▼                   ▼                    ▼
Reserva           Pagamento            Remarcação
      │                   │                    │
      └───────────────────┼────────────────────┘
                          │
                          ▼
                   Payment Manager
                          │
                          ▼
                     Event Store
                          │
                          ▼
                   Feegow Integration
                          │
                          ▼
                     API Feegow

------------------------------------------------------------

Camadas

1. Hermes

Responsável pela orquestração.

2. ANA

Responsável pela inteligência.

3. Feegow

Responsável pelos dados clínicos.

------------------------------------------------------------

Princípios

- A inteligência nunca fica na Feegow.

- A Feegow nunca toma decisões.

- Toda regra de negócio pertence à ANA.

- Hermes coordena os agentes.

------------------------------------------------------------

Componentes

Conversation Manager

Gerencia conversas.

Session Manager

Gerencia estado do paciente.

Workflow Engine

Executa regras de negócio.

Payment Manager

Controla reservas e pagamentos.

Notification Service

Envia mensagens.

Event Store

Registra todos os eventos.

Feegow Integration

Integra com a API.

------------------------------------------------------------

Objetivo Final

Criar uma plataforma de atendimento autônoma capaz de operar múltiplas clínicas utilizando Hermes Agent como orquestrador e Feegow como sistema de gestão clínica.

