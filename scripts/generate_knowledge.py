import json
from pathlib import Path

BASE = Path("data/knowledge")

clinic = json.loads((BASE/"clinic_info.json").read_text(encoding="utf-8"))
doctor = json.loads((BASE/"doctor.json").read_text(encoding="utf-8"))
prices = json.loads((BASE/"prices.json").read_text(encoding="utf-8"))
payment = json.loads((BASE/"payment.json").read_text(encoding="utf-8"))
services = json.loads((BASE/"services.json").read_text(encoding="utf-8"))
hours = json.loads((BASE/"business_hours.json").read_text(encoding="utf-8"))

md = f"""# BASE ÚNICA DE CONHECIMENTO — ANA

## Clínica

Nome: {clinic["clinic_name"]}

Endereço:
{clinic["address"]}, {clinic["room"]} - {clinic["city"]}/{clinic["state"]}

---

## Médica

Nome:
{doctor["name"]}

Especialidade:
{doctor["specialty"]}

Convênio:
{"Não. Atendimento particular com emissão de nota fiscal para reembolso." if not doctor["accepts_insurance"] else "Sim"}

---

## Valores

Consulta presencial:
R$ {prices["consulta_presencial"]:.2f}

Consulta online:
R$ {prices["consulta_online"]:.2f}

Consulta híbrida:
R$ {prices["consulta_hibrida"]:.2f}

---

## Serviços

"""

for s in services["services"]:
    md += f"- {s}\n"

md += f"""

---

## Pagamento

Formas aceitas:
{", ".join(payment["methods"])}

Nota fiscal:
{"Sim" if payment["invoice"] else "Não"}

---

## Retorno

Retorno em {hours["return_days"]} dias.
"""

(BASE/"BASE_UNICA_ANA.md").write_text(md, encoding="utf-8")

print("BASE_UNICA_ANA.md atualizada.")
