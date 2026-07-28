from ana_feegow.tools.patients import buscar_paciente


class FakeFeegowClient:
    def __init__(self, pacientes=None, cpf_response=None):
        self.pacientes = pacientes or []
        self.cpf_response = cpf_response
        self.chamadas = []

    def get(self, endpoint, params=None):
        self.chamadas.append((endpoint, params))
        if params and "cpf" in params:
            return self.cpf_response
        # simula /patient/list ignorando filtros de telefone/celular,
        # sempre devolvendo a listagem paginada completa
        offset = params.get("offset", 0)
        limit = params.get("limit", 200)
        pagina = self.pacientes[offset : offset + limit]
        return {"total": len(self.pacientes), "content": pagina}


def paciente(patient_id, celular):
    return {"patient_id": patient_id, "nome": f"Paciente {patient_id}", "celular": celular}


def test_busca_por_telefone_filtra_corretamente_no_cliente():
    pacientes = [paciente(11, "21921223233"), paciente(12, "21985929056")]
    client = FakeFeegowClient(pacientes)

    resultado = buscar_paciente(telefone="21985929056", client=client)

    assert resultado["total"] == 1
    assert resultado["content"][0]["patient_id"] == 12


def test_busca_por_telefone_sem_correspondencia_devolve_vazio():
    pacientes = [paciente(11, "21921223233")]
    client = FakeFeegowClient(pacientes)

    resultado = buscar_paciente(telefone="21985929056", client=client)

    assert resultado == {"total": 0, "content": []}


def test_busca_por_cpf_continua_usando_o_filtro_do_servidor():
    client = FakeFeegowClient(
        cpf_response={"total": 1, "content": [{"patient_id": 5, "cpf": "11767993714"}]}
    )

    resultado = buscar_paciente(cpf="11767993714", client=client)

    assert resultado["content"][0]["patient_id"] == 5
    assert client.chamadas[0] == ("/patient/list", {"cpf": "11767993714"})


def test_sem_nenhum_parametro_levanta_erro():
    import pytest

    with pytest.raises(ValueError):
        buscar_paciente(client=FakeFeegowClient())
