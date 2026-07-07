# Integração MCP (ANA) com Feegow

Versão: 1.0

Data: 07/07/2026

=================================================================

OBJETIVO

Este documento descreve toda a integração entre a plataforma ANA
(MCP) e a API oficial da Feegow.

A integração foi construída seguindo arquitetura em camadas,
mantendo separação entre:

• Inteligência (ANA)

• Integração (Feegow)

• Orquestração (Hermes)

=================================================================

ARQUITETURA

Hermes
    │
    ▼
Conversation Manager
    │
    ▼
Workflow Engine
    │
    ▼
Managers
    │
    ▼
Feegow Client
    │
    ▼
API REST Feegow

=================================================================

CLIENTE FEEGOW

Arquivo

src/ana_feegow/client.py

Responsabilidade

Implementar toda comunicação HTTP.

Funções

GET

POST

PUT

DELETE

Também implementa

• autenticação

• timeout

• retries

• tratamento de erros

Nenhum workflow comunica diretamente com requests.

Toda comunicação passa pelo FeegowClient.

=================================================================

CONFIGURAÇÃO

Arquivo

src/ana_feegow/config.py

Responsável por

FEEGOW_BASE_URL

FEEGOW_ACCESS_TOKEN

Timeout

Retries

Todos os parâmetros são carregados do .env.

=================================================================

PACIENTES

Responsabilidade

Pesquisar pacientes.

Atualizar pacientes.

Cadastrar pacientes.

Ferramentas

buscar_paciente()

buscar_por_telefone()

criar_paciente()

atualizar_paciente()

Endpoints utilizados

GET /patient/search

POST /patient/insert

PUT /patient/update

=================================================================

PROFISSIONAIS

Responsabilidade

Listar profissionais ativos.

Ferramenta

list_professionals()

Endpoint

GET /professional/list

=================================================================

HORÁRIOS

Responsabilidade

Consultar disponibilidade.

Ferramenta

consultar_horarios()

Endpoint

GET /appoints/available-schedule

=================================================================

AGENDAMENTOS

Responsabilidade

Criar consultas.

Ferramenta

criar_agendamento()

Endpoint

POST /appoints/new-appoint

Payload utilizado

local_id

paciente_id

profissional_id

especialidade_id

procedimento_id

data

horario

valor

plano

canal_id

tabela_id

notas

celular

telefone

email

retorno

sys_user

=================================================================

STATUS

Responsabilidade

Atualizar status.

Ferramenta

atualizar_status()

Endpoint

POST /appoints/statusUpdate

Payload

AgendamentoID

StatusID

Obs

=================================================================

STATUS DISPONÍVEIS

1

Marcado não confirmado

7

Marcado confirmado

15

Remarcado

208

Aguardando pagamento

=================================================================

WORKFLOW RESERVA

Fluxo

Consultar horários

↓

Criar agendamento

↓

Status 208

↓

Registrar evento

↓

Iniciar Payment Manager

=================================================================

WORKFLOW PAGAMENTO

Fluxo

Enviar cobrança

↓

Receber comprovante

↓

Validar

↓

Status 7

↓

Registrar evento

=================================================================

WORKFLOW REMARCAÇÃO

Fluxo

Consultar horários

↓

Criar novo agendamento

↓

Status antigo = 15

↓

Registrar evento

=================================================================

EVENT STORE

Responsabilidade

Registrar todas as ações executadas.

Exemplos

reserva_criada

pagamento_confirmado

consulta_remarcada

=================================================================

PAYMENT MANAGER

Responsabilidade

Controlar

Prazo

Lembretes

Expiração da reserva

=================================================================

SEPARAÇÃO DE RESPONSABILIDADES

Feegow

Armazena dados.

Executa operações.

Nunca toma decisões.

ANA

Executa regras de negócio.

Decide workflows.

Controla estados.

Hermes

Orquestra agentes.

Controla execução.

=================================================================

FILOSOFIA

Toda regra pertence à ANA.

Toda persistência clínica pertence à Feegow.

Toda orquestração pertence ao Hermes.

Esta separação permite evolução independente dos componentes,
facilitando manutenção, testes e escalabilidade.

