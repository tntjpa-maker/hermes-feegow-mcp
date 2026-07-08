# Decisão - Consulta de Agenda Feegow

A ANA deve usar a API REST oficial da Feegow sempre que possível.

Não usar cookies ou sessão do navegador como integração principal.

Motivo:

- Sessões expiram.
- Cookies não são estáveis.
- Não é adequado para produção.
- A integração deve ser reproduzível em novo servidor.

Endpoint testado:

GET /appoints/available-schedule

Parâmetros:

- tipo_consulta
- data_inicio
- data_fim

Formato de data usado:

dd-mm-YYYY

Caso o endpoint falhe, a ANA poderá inicialmente trabalhar com tentativa controlada de reserva e tratamento de conflito até definirmos uma forma oficial de disponibilidade.

