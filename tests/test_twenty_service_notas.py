from ana_feegow.services import twenty_service


def test_registrar_origem_lead_texto_livre_cria_nota_e_vincula(monkeypatch):
    # Cobre o pedido do cliente: alem da categoria (origemDoLead), a
    # resposta literal da paciente a "como conheceu a Dra. Thalita" deve
    # ficar guardada como Nota no Twenty, vinculada a Oportunidade e a
    # Pessoa - dado usado depois para direcionamento de campanhas de
    # marketing. Mesmo padrao (nota -> noteTargets) de registrar_link_enviado.
    monkeypatch.setattr(twenty_service, "TWENTY_API_KEY", "fake-key")
    chamadas = []

    def fake_post(path, payload):
        chamadas.append((path, payload))
        if path == "/rest/notes":
            return {"data": {"createNote": {"id": "note-1"}}}
        return {"data": {}}

    monkeypatch.setattr(twenty_service, "_post", fake_post)

    twenty_service.registrar_origem_lead_texto_livre(
        "opp-1", "person-1", "vi minha prima comentando no Instagram"
    )

    assert len(chamadas) == 2
    assert chamadas[0][0] == "/rest/notes"
    assert "vi minha prima comentando no Instagram" in chamadas[0][1]["bodyV2"]["markdown"]
    assert chamadas[1] == (
        "/rest/noteTargets",
        {
            "noteId": "note-1",
            "targetOpportunityId": "opp-1",
            "targetPersonId": "person-1",
        },
    )


def test_registrar_origem_lead_texto_livre_sem_person_id_ainda_vincula_oportunidade(monkeypatch):
    monkeypatch.setattr(twenty_service, "TWENTY_API_KEY", "fake-key")
    chamadas = []

    def fake_post(path, payload):
        chamadas.append((path, payload))
        if path == "/rest/notes":
            return {"data": {"createNote": {"id": "note-1"}}}
        return {"data": {}}

    monkeypatch.setattr(twenty_service, "_post", fake_post)

    twenty_service.registrar_origem_lead_texto_livre("opp-1", None, "Google")

    assert chamadas[1] == ("/rest/noteTargets", {"noteId": "note-1", "targetOpportunityId": "opp-1"})


def test_registrar_origem_lead_texto_livre_ignora_texto_vazio(monkeypatch):
    monkeypatch.setattr(twenty_service, "TWENTY_API_KEY", "fake-key")
    chamadas = []
    monkeypatch.setattr(twenty_service, "_post", lambda *a, **k: chamadas.append(a) or {})

    twenty_service.registrar_origem_lead_texto_livre("opp-1", "person-1", "   ")

    assert chamadas == []


def test_registrar_origem_lead_texto_livre_sem_opportunity_id_nao_chama_api(monkeypatch):
    monkeypatch.setattr(twenty_service, "TWENTY_API_KEY", "fake-key")
    chamadas = []
    monkeypatch.setattr(twenty_service, "_post", lambda *a, **k: chamadas.append(a) or {})

    twenty_service.registrar_origem_lead_texto_livre("", "person-1", "Instagram")

    assert chamadas == []


def test_registrar_origem_lead_texto_livre_falha_da_api_nao_levanta(monkeypatch):
    monkeypatch.setattr(twenty_service, "TWENTY_API_KEY", "fake-key")

    def post_com_erro(path, payload):
        raise RuntimeError("Twenty fora do ar (simulado)")

    monkeypatch.setattr(twenty_service, "_post", post_com_erro)

    # Best effort: nao pode levantar excecao, mesmo com falha na API.
    twenty_service.registrar_origem_lead_texto_livre("opp-1", "person-1", "Instagram")
