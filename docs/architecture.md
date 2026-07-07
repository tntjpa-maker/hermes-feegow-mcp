# Arquitetura

Paciente

↓

WhatsApp (Hermes)

↓

ANA

↓

MCP Feegow

↓

API Feegow

Princípios:

- ANA contém toda regra de negócio.
- MCP apenas integra com o Feegow.
- Feegow é a única fonte da verdade.
- Nenhum ID do Feegow é exposto para ANA.
