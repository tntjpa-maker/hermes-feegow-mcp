from ana_feegow.ana.intent import identificar_intencao

mensagens = [
    "Quero marcar uma consulta",
    "Preciso remarcar",
    "Quero cancelar",
    "Segue comprovante do pix",
    "Bom dia"
]

for m in mensagens:
    print(m)
    print("->", identificar_intencao(m))
    print()
