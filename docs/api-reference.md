# API Feegow - Referência Validada

## GET /professional/list
Status: Validado

## GET /patient/list
Busca por:
- telefone
- cpf
- nome
- limit
- offset

## POST /patient/create
Status: Validado

Campos mínimos:
- nome_completo
- cpf
- data_nascimento
- celular1

## GET /appoints/available-schedule
Status: Validado

Parâmetros:
- tipo=P
- procedimento_id
- unidade_id
- convenio_id
- data_start
- data_end

## GET /appoints/status
Status: Validado

## POST /appoints/statusUpdate
Status: Validado

## POST /appoints/new-appoint
Status: Em implementação
