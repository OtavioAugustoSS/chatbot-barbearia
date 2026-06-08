"""Sprint C (restante) — P2-7b: /presence autentica pelo body (sendBeacon),
não mais pela query param (que vazava em access log)."""


def test_presence_autentica_via_token_no_body(client, atendente_teste, token):
    # Caminho sendBeacon: sem header Authorization, token vai no body.
    r = client.post("/admin/presence", json={"status": "offline", "token": token})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_presence_sem_token_em_lugar_nenhum_401(client):
    r = client.post("/admin/presence", json={"status": "offline"})
    assert r.status_code == 401


def test_presence_header_authorization_continua_funcionando(client, atendente_teste, auth_headers):
    # Heartbeat normal (AJAX) usa header — não deve quebrar.
    r = client.post("/admin/presence", json={"status": "online"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_presence_token_invalido_no_body_401(client):
    r = client.post("/admin/presence", json={"status": "online", "token": "lixo.nao.jwt"})
    assert r.status_code == 401
