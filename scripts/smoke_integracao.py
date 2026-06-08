"""
smoke_integracao.py — smoke de INTEGRAÇÃO contra o MySQL REAL.

Os testes da suíte rodam em SQLite + mocks. Este script exercita os fluxos core
contra o banco MySQL de verdade (do .env), pegando divergências que o SQLite
esconde (tipos ENUM/JSON/TIMESTAMP, transações, charset). É um check manual
pré-prod — NÃO chama o NIM (custo zero) e limpa todos os dados de teste no fim.

Uso:
    python scripts/smoke_integracao.py
Saída: lista PASS/FAIL e exit code 0 (tudo passou) ou 1 (alguma falha).
"""
import os
os.environ.setdefault("ALLOW_UNSIGNED_WEBHOOK", "1")  # garante boot + webhook não-assinado

import sys
import secrets
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PREFIXO = "smoke_intg_"
_resultados = []


def chk(nome, cond, detalhe=""):
    _resultados.append((nome, bool(cond), detalhe))


def main() -> int:
    from main import app
    from fastapi.testclient import TestClient
    import api.webhook as webhook
    import services.whatsapp as wa_mod
    from db.database import SessionLocal
    from db.models import (Atendente, Usuario, HistoricoConversa, MensagemProcessada,
                           CannedResponse, FiltroSalvo)
    from api.auth import hash_senha

    # Blindagens: sem NIM, sem rede WhatsApp.
    wa_mod.WhatsAppSender.upload_midia_whatsapp = lambda self, *a, **k: "media_smoke"
    wa_mod.WhatsAppSender.enviar_mensagem_midia = lambda self, *a, **k: (True, "wamid.s")
    webhook.whatsapp.enviar_mensagem_texto = lambda numero, texto: (True, "wamid.s")
    webhook.whatsapp.enviar_lista_interativa = lambda **k: (True, "wamid.s")
    webhook.whatsapp.enviar_botoes_resposta = lambda **k: (True, "wamid.s")
    webhook.ai_service._chamar_llm = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("NIM NAO CHAMAR"))

    client = TestClient(app)
    criados_atendentes, criados_telefones = [], []

    try:
        # --- leitura básica ---
        chk("/health", client.get("/health").status_code == 200)
        chk("/webhook verify", client.get("/webhook", params={
            "hub.mode": "subscribe", "hub.verify_token": os.getenv("WEBHOOK_VERIFY_TOKEN", ""),
            "hub.challenge": "ok"}).text == "ok")

        # --- operador throwaway + login ---
        login = PREFIXO + secrets.token_hex(3)
        db = SessionLocal()
        try:
            at = Atendente(nome="Smoke Intg", usuario_login=login,
                           senha_hash=hash_senha("smokesenha123"), ativo=True)
            db.add(at); db.commit(); db.refresh(at)
            at_id = at.id
            criados_atendentes.append(at_id)
        finally:
            db.close()
        tok = client.post("/admin/login", json={"usuario_login": login, "senha": "smokesenha123"}).json().get("token")
        chk("login → JWT", bool(tok))
        H = {"Authorization": f"Bearer {tok}"}
        chk("GET /admin/conversas", client.get("/admin/conversas", headers=H).status_code == 200)
        chk("GET /admin/horarios", client.get("/admin/horarios", headers=H).status_code == 200)

        # --- máquina de status (escreve ENUM status_conversa no MySQL real) ---
        tel = "55smk" + secrets.token_hex(6)   # <=20 (VARCHAR telefone)
        criados_telefones.append(tel)
        db = SessionLocal()
        try:
            db.add(Usuario(telefone=tel, nome_cliente="Smoke", bot_ativo=True, status_conversa="open"))
            db.commit()
        finally:
            db.close()
        r = client.patch(f"/admin/conversa/{tel}/status", json={"status": "resolved"}, headers=H)
        chk("PATCH status open→resolved (ENUM MySQL)", r.status_code == 200 and r.json()["status"] == "resolved")
        # confirma persistência real
        db = SessionLocal()
        try:
            u = db.query(Usuario).filter_by(telefone=tel).first()
            chk("status_conversa persistido no MySQL", u.status_conversa == "resolved")
        finally:
            db.close()

        # --- views CRUD (escreve JSON criterios no MySQL real) ---
        r = client.post("/admin/views", json={"nome": PREFIXO + "v", "criterios": {"filtro": "meus", "x": 1}, "ordem": 0}, headers=H)
        chk("POST /admin/views (JSON criterios)", r.status_code in (200, 201))
        vid = r.json().get("id") if r.status_code in (200, 201) else None
        if vid:
            chk("DELETE /admin/views", client.delete(f"/admin/views/{vid}", headers=H).status_code in (200, 204))

        # --- canned CRUD ---
        r = client.post("/admin/canned", json={"atalho": "/smk", "texto": "oi", "escopo": "pessoal"}, headers=H)
        chk("POST /admin/canned", r.status_code == 201)
        cid = r.json().get("id") if r.status_code == 201 else None
        if cid:
            chk("DELETE /admin/canned", client.delete(f"/admin/canned/{cid}", headers=H).status_code == 204)

        # --- enviar-midia (upload mockado) ---
        db = SessionLocal()
        try:
            u = db.query(Usuario).filter_by(telefone=tel).first()
            u.atendente_id = at_id; db.commit()
        finally:
            db.close()
        r = client.post(f"/admin/enviar-midia/{tel}",
                        files={"file": ("f.jpg", b"\xff\xd8\xff\xe0bytes", "image/jpeg")},
                        data={"caption": "x"}, headers=H)
        chk("POST /admin/enviar-midia", r.status_code == 200)
        chk("enviar-midia vazia → 400", client.post(f"/admin/enviar-midia/{tel}",
            files={"file": ("v.jpg", b"", "image/jpeg")}, headers=H).status_code == 400)

        # --- pipeline canônico via webhook (com histórico, sem NIM) ---
        tel2 = "55smk" + secrets.token_hex(6)  # <=20
        criados_telefones.append(tel2)
        db = SessionLocal()
        try:
            db.add(Usuario(telefone=tel2, nome_cliente="Smoke", bot_ativo=True))
            db.add(HistoricoConversa(telefone_usuario=tel2, mensagem_cliente="oi", resposta_bot="menu", origem="bot"))
            db.commit()
        finally:
            db.close()
        mid = PREFIXO + secrets.token_hex(6)
        pl = {"object": "whatsapp_business_account", "entry": [{"id": "e", "changes": [{"value": {
            "messaging_product": "whatsapp", "metadata": {"phone_number_id": "0"},
            "contacts": [{"profile": {"name": "Smoke"}, "wa_id": tel2}],
            "messages": [{"from": tel2, "id": mid, "timestamp": "1700000000", "type": "text",
                          "text": {"body": "qual o horario?"}}]}, "field": "messages"}]}]}
        chk("POST /webhook canônico (sem NIM)", client.post("/webhook", json=pl).status_code == 200)

        return 0 if all(ok for _, ok, _ in _resultados) else 1
    finally:
        # ---- limpeza de TODOS os dados de teste ----
        db = SessionLocal()
        try:
            for tel in criados_telefones:
                db.query(HistoricoConversa).filter(HistoricoConversa.telefone_usuario == tel).delete(synchronize_session=False)
                db.query(Usuario).filter(Usuario.telefone == tel).delete(synchronize_session=False)
            db.query(MensagemProcessada).filter(MensagemProcessada.message_id.like(PREFIXO + "%")).delete(synchronize_session=False)
            db.query(CannedResponse).filter(CannedResponse.atalho == "/smk").delete(synchronize_session=False)
            db.query(FiltroSalvo).filter(FiltroSalvo.nome.like(PREFIXO + "%")).delete(synchronize_session=False)
            for aid in criados_atendentes:
                db.query(Atendente).filter(Atendente.id == aid).delete(synchronize_session=False)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


if __name__ == "__main__":
    try:
        code = main()
    except Exception as e:
        chk("EXCEPTION", False, repr(e) + "\n" + traceback.format_exc()[-900:])
        code = 1
    def _safe(s):
        return str(s).encode("ascii", "replace").decode("ascii")
    print("\n===== SMOKE DE INTEGRACAO (MySQL real) =====")
    for nome, ok, det in _resultados:
        linha = f"[{'PASS' if ok else 'FAIL'}] {nome}" + (f"  -- {det}" if det and not ok else "")
        print(_safe(linha))
    print(">>> " + ("TODOS PASSARAM" if code == 0 else "HOUVE FALHA"))
    sys.exit(code)
