# Guia de Desenvolvimento da ANA

## Objetivo

Este documento define as regras obrigatórias para desenvolvimento da plataforma ANA.

============================================================

ESTRUTURA

src/

ana_feegow/

appointments/

managers/

workflows/

tools/

settings/

============================================================

REGRA 1

Toda integração externa deve possuir um módulo próprio.

Exemplos:

appointments/

patients/

professionals/

============================================================

REGRA 2

Nenhuma regra de negócio pode ficar dentro da integração Feegow.

A integração apenas envia e recebe dados.

============================================================

REGRA 3

Toda regra clínica pertence aos workflows.

============================================================

REGRA 4

Toda decisão automática deve gerar um evento.

Exemplos

reserva_criada

pagamento_confirmado

consulta_remarcada

============================================================

REGRA 5

Todo módulo novo deve possuir teste.

Exemplo

src/ana_feegow/workflows/remarcacao.py

↓

tests/test_remarcacao.py

============================================================

REGRA 6

Nenhuma funcionalidade será considerada pronta sem documentação.

Sempre atualizar:

PROJECT_STATE

ROADMAP

WORKFLOWS

============================================================

REGRA 7

Toda alteração importante deverá possuir commit específico.

Nunca agrupar funcionalidades diferentes.

============================================================

REGRA 8

Sempre preservar compatibilidade dos módulos públicos.

Mudanças incompatíveis exigem nova versão.

============================================================

REGRA 9

A IA nunca executará decisões clínicas.

A IA apenas automatiza processos administrativos.

============================================================

REGRA 10

Toda automação deve ser auditável.

Toda decisão deve poder ser reconstruída através do Event Store.

============================================================

Objetivo

Manter a plataforma escalável, previsível e de fácil manutenção.

