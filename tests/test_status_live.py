from ana_feegow.tools.status import listar_status


def test_status():
    r = listar_status()

    print(r)

    assert r["success"] is True
