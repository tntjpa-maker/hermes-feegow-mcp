from pprint import pprint

from ana_feegow.workflows.finalizar_pagamento import confirmar_pagamento

print()
print("=" * 60)
print("CONFIRMAR PAGAMENTO")
print("=" * 60)

resultado = confirmar_pagamento(31)

pprint(resultado)
