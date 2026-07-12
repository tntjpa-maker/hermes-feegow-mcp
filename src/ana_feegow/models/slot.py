from dataclasses import dataclass


@dataclass
class Slot:
    inicio: str
    fim: str
    livre: bool = True
