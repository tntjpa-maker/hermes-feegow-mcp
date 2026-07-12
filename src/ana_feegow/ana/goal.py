class Goal:

    def __init__(self, objetivo):
        self.objetivo = objetivo
        self.slots = {}

    def preencher(self, campo, valor):
        self.slots[campo] = valor

    def possui(self, campo):
        return campo in self.slots

    def obter(self, campo):
        return self.slots.get(campo)

    def concluido(self):
        if self.objetivo == "agendar":
            obrigatorios = [
                "tipo_consulta",
                "data",
                "horario",
            ]
            return all(c in self.slots for c in obrigatorios)

        return False
