from ana_feegow.tools.identify import identificar_paciente


class FakeFeegowClient:
    """Fake que reproduz o comportamento real observado do Feegow: o
    endpoint /patient/list IGNORA os filtros de telefone/celular e sempre
    devolve a listagem paginada completa, na ordem que o servidor quiser -
    exatamente o que quebrava a versão antiga de identificar_paciente()
    (que confiava no filtro do servidor com limit=1)."""

    def __init__(self, pacientes, page_size=200):
        self.pacientes = pacientes
        self.page_size = page_size
        self.chamadas = []

    def get(self, endpoint, params=None):
        assert endpoint == "/patient/list"
        self.chamadas.append(params)
        offset = params["offset"]
        limit = params["limit"]
        pagina = self.pacientes[offset : offset + limit]
        return {"total": len(self.pacientes), "content": pagina}


def paciente(patient_id, celular):
    return {"patient_id": patient_id, "nome": f"Paciente {patient_id}", "celular": celular}


def test_encontra_paciente_mesmo_quando_servidor_ignora_filtro_e_devolve_outro_primeiro():
    # simula exatamente o bug real: o paciente "errado" vem primeiro na
    # listagem, o telefone buscado só aparece mais à frente.
    pacientes = [
        paciente(11, "21921223233"),
        paciente(12, "21985929056"),
        paciente(13, None),
    ]
    client = FakeFeegowClient(pacientes)

    resultado = identificar_paciente("21985929056", client=client)

    assert resultado["existe"] is True
    assert resultado["paciente"]["patient_id"] == 12


def test_nao_encontra_quando_nenhum_celular_bate():
    pacientes = [paciente(11, "21921223233"), paciente(13, None)]
    client = FakeFeegowClient(pacientes)

    resultado = identificar_paciente("21985929056", client=client)

    assert resultado == {"existe": False, "paciente": None}


def test_normaliza_telefone_removendo_formatacao():
    pacientes = [paciente(12, "21985929056")]
    client = FakeFeegowClient(pacientes)

    resultado = identificar_paciente("(21) 98592-9056", client=client)

    assert resultado["existe"] is True
    assert resultado["paciente"]["patient_id"] == 12


def test_pacientes_com_celular_none_nao_quebram_a_busca():
    pacientes = [paciente(11, None), paciente(12, "21985929056")]
    client = FakeFeegowClient(pacientes)

    resultado = identificar_paciente("21985929056", client=client)

    assert resultado["existe"] is True


def test_percorre_todas_as_paginas_ate_encontrar(monkeypatch):
    import ana_feegow.tools.identify as identify_module

    monkeypatch.setattr(identify_module, "PAGE_SIZE", 2)

    pacientes = [
        paciente(1, "11111111111"),
        paciente(2, "22222222222"),
        paciente(3, "33333333333"),
        paciente(4, "21985929056"),  # só aparece na 2ª página (page_size=2)
    ]
    client = FakeFeegowClient(pacientes)

    resultado = identificar_paciente("21985929056", client=client)

    assert resultado["existe"] is True
    assert resultado["paciente"]["patient_id"] == 4
    assert len(client.chamadas) == 2


def test_para_de_paginar_assim_que_encontra_o_paciente(monkeypatch):
    import ana_feegow.tools.identify as identify_module

    monkeypatch.setattr(identify_module, "PAGE_SIZE", 2)

    pacientes = [
        paciente(1, "21985929056"),  # já está na 1ª página
        paciente(2, "22222222222"),
        paciente(3, "33333333333"),
    ]
    client = FakeFeegowClient(pacientes)

    resultado = identificar_paciente("21985929056", client=client)

    assert resultado["existe"] is True
    assert len(client.chamadas) == 1
