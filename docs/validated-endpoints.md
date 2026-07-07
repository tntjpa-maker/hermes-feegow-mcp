# Endpoints Feegow validados

## Profissionais

GET /professional/list

Status: validado.

Retorno confirmado:
- profissional_id
- nome
- especialidades

## Pacientes

GET /patient/list

Status: validado.

Uso:
- busca por nome
- busca por celular

## Horários disponíveis

GET /appoints/available-schedule

Status: validado parcialmente.

Parâmetros obrigatórios confirmados:
- tipo
- data_start no formato d-m-Y
- data_end no formato d-m-Y

Parâmetro tipo confirmado pela documentação:
- P

Exemplo oficial:
GET /appoints/available-schedule?tipo=P&procedimento_id=5&unidade_id=0&data_start=08-08-2018&data_end=10-08-2018&convenio_id=1
