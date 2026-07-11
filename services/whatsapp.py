import os
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("barbearia.whatsapp")


def criar_sender() -> "WhatsAppSender":
    """Factory do sender: real com credenciais Meta, fake (outbox do simulador) sem elas.

    A decisão vem de core.config.WHATSAPP_FAKE (presença de WHATSAPP_TOKEN e
    WHATSAPP_PHONE_ID) — nunca de tentativa de rede.
    """
    from core.config import WHATSAPP_FAKE

    if WHATSAPP_FAKE:
        from services.dev_sender import DevWhatsAppSender

        log.warning("WHATSAPP_TOKEN/PHONE_ID ausentes — usando DevWhatsAppSender (modo dev, sem envio real).")
        return DevWhatsAppSender()
    return WhatsAppSender()


class WhatsAppSender:
    def __init__(self):
        self.token = os.getenv("WHATSAPP_TOKEN")
        self.phone_id = os.getenv("WHATSAPP_PHONE_ID")
        self.url = f"https://graph.facebook.com/v19.0/{self.phone_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _post_com_retry(self, payload: dict, numero: str, tipo_log: str) -> tuple[bool, str | None]:
        """POST genérico à Meta API com 3 tentativas em 5xx e 429. Retorna (ok, wamid)."""
        try:
            for attempt in range(3):
                response = requests.post(self.url, headers=self.headers, json=payload, timeout=10)
                if response.status_code == 429:
                    # BE-01: respeita Retry-After da Meta; fallback para 5s se ausente.
                    retry_after = int(response.headers.get("Retry-After", 5))
                    log.warning("Meta API 429 (%s) para %s — aguardando %ds.", tipo_log, numero, retry_after)
                    if attempt < 2:
                        time.sleep(retry_after)
                    continue
                if response.status_code < 500:
                    break
                if attempt < 2:
                    time.sleep(1)
        except requests.RequestException as e:
            log.error("Falha de rede ao enviar %s para %s: %s", tipo_log, numero, e)
            return False, None

        if response.status_code == 401:
            # P0-2: token expirado/inválido — alerta DISTINTO e acionável (catchável por monitor/Sentry).
            # Em sandbox o WHATSAPP_TOKEN vence em 24h; em produção use System User token permanente.
            log.error(
                "WHATSAPP_TOKEN EXPIRADO OU INVÁLIDO (401) ao enviar %s. "
                "O bot NÃO está respondendo aos clientes — renove o WHATSAPP_TOKEN no .env e reinicie.",
                tipo_log,
            )
            return False, None
        if response.status_code >= 400:
            log.error("Meta API erro %s (%s) para %s: %s", response.status_code, tipo_log, numero, response.text[:500])
            return False, None

        log.info("Envio %s para %s (status %s)", tipo_log, numero, response.status_code)
        try:
            data = response.json()
            wamid = data.get("messages", [{}])[0].get("id")
        except ValueError:
            # BE-02: corpo de resposta não é JSON válido — não consideramos entregue.
            log.error("Meta API retornou resposta não-JSON (%s) para %s.", tipo_log, numero)
            return False, None
        return True, wamid

    def marcar_como_lida(self, message_id: str, numero: str) -> bool:
        """Envia read receipt à Meta — o CLIENTE vê os ticks azuis no WhatsApp dele.

        message_id: wamid da mensagem DO CLIENTE. O WhatsApp marca em cascata as
        anteriores da mesma conversa, então basta o wamid mais recente.
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        ok, _ = self._post_com_retry(payload, numero, "read_receipt")
        return ok

    def enviar_mensagem_texto(self, numero: str, texto: str) -> tuple[bool, str | None]:
        """
        Envia mensagem WhatsApp via Meta Cloud API.
        Retorna (ok, wamid): ok=True se Meta aceitou (200 OK), wamid=ID da mensagem para
        rastreamento de status (delivered/read). wamid é None em caso de falha.
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "text",
            "text": {"body": texto}
        }
        return self._post_com_retry(payload, numero, "texto")

    def enviar_lista_interativa(
        self,
        numero: str,
        body_text: str,
        button_text: str,
        sections: list[dict],
        header_text: str | None = None,
        footer_text: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Envia Interactive List Message via Meta Cloud API.
        Retorna True se aceito pela Meta, False em qualquer falha.

        Limites Meta (validados aqui — request é truncado/abortado se exceder):
          - button_text: 20 chars
          - header_text: 60 chars (text header apenas)
          - body_text: 1024 chars
          - footer_text: 60 chars
          - section.title: 24 chars
          - row.id: 200 chars
          - row.title: 24 chars
          - row.description: 72 chars
          - Total: máx 10 sections, máx 10 rows somando todas as sections

        sections: lista de dicts no formato:
          [{"title": "Seção", "rows": [{"id": "X", "title": "Y", "description": "Z"}, ...]}]

        Em caso de violação de limite local, loga ERROR e retorna False — caller
        deve cair para enviar_mensagem_texto() como fallback.
        """
        # Validação local de limites (evita request inválido que daria 4xx).
        if not button_text or len(button_text) > 20:
            log.error("enviar_lista_interativa: button_text inválido (%r)", button_text)
            return False, None
        if not body_text or len(body_text) > 1024:
            log.error("enviar_lista_interativa: body_text inválido (len=%d)", len(body_text or ""))
            return False, None
        if header_text is not None and len(header_text) > 60:
            log.error("enviar_lista_interativa: header_text excede 60 chars")
            return False, None
        if footer_text is not None and len(footer_text) > 60:
            log.error("enviar_lista_interativa: footer_text excede 60 chars")
            return False, None
        if not sections or len(sections) > 10:
            log.error("enviar_lista_interativa: número de sections inválido (%d)", len(sections or []))
            return False, None

        total_rows = 0
        for sec in sections:
            titulo = sec.get("title", "")
            rows = sec.get("rows", [])
            if len(titulo) > 24:
                log.error("enviar_lista_interativa: section.title >24 chars (%r)", titulo)
                return False, None
            if not rows:
                log.error("enviar_lista_interativa: section sem rows")
                return False, None
            for r in rows:
                rid = r.get("id", "")
                rtitle = r.get("title", "")
                rdesc = r.get("description", "")
                if not rid or len(rid) > 200:
                    log.error("enviar_lista_interativa: row.id inválido (%r)", rid)
                    return False, None
                if not rtitle or len(rtitle) > 24:
                    log.error("enviar_lista_interativa: row.title inválido (%r)", rtitle)
                    return False, None
                if rdesc and len(rdesc) > 72:
                    log.error("enviar_lista_interativa: row.description >72 chars")
                    return False, None
                total_rows += 1
        if total_rows == 0 or total_rows > 10:
            log.error("enviar_lista_interativa: total de rows inválido (%d)", total_rows)
            return False, None

        # Monta o objeto "action" no formato exato exigido pela Meta.
        action_sections = []
        for sec in sections:
            sec_rows = []
            for r in sec.get("rows", []):
                row_obj = {"id": r["id"], "title": r["title"]}
                if r.get("description"):
                    row_obj["description"] = r["description"]
                sec_rows.append(row_obj)
            action_sections.append({"title": sec["title"], "rows": sec_rows})

        interactive: dict = {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text,
                "sections": action_sections,
            },
        }
        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "interactive",
            "interactive": interactive,
        }
        return self._post_com_retry(payload, numero, "lista_interativa")

    def enviar_botoes_resposta(
        self,
        numero: str,
        body_text: str,
        buttons: list[dict],
        header_text: str | None = None,
        footer_text: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Envia Interactive Reply Buttons via Meta Cloud API.
        Retorna True se Meta aceitou, False em qualquer falha (caller deve fazer fallback).

        Limites Meta (validados aqui — request abortado se exceder):
          - máximo 3 botões
          - button.id: 1-256 chars
          - button.title: 1-20 chars
          - body_text: 1-1024 chars
          - header_text: ≤60 chars (text header)
          - footer_text: ≤60 chars

        buttons: lista no formato [{"id": "X", "title": "Y"}, ...]

        Diferença vs lista interativa: botões aparecem direto na tela (sem precisar
        tocar "Ver opções"). Ideal para 2-3 opções rápidas pós-seleção.
        """
        # Validação local de limites
        if not body_text or len(body_text) > 1024:
            log.error("enviar_botoes_resposta: body_text inválido (len=%d)", len(body_text or ""))
            return False, None
        if not buttons or len(buttons) > 3:
            log.error("enviar_botoes_resposta: número de botões inválido (%d)", len(buttons or []))
            return False, None
        if header_text is not None and len(header_text) > 60:
            log.error("enviar_botoes_resposta: header_text excede 60 chars")
            return False, None
        if footer_text is not None and len(footer_text) > 60:
            log.error("enviar_botoes_resposta: footer_text excede 60 chars")
            return False, None

        action_buttons = []
        ids_vistos = set()
        for b in buttons:
            bid = b.get("id", "")
            btitle = b.get("title", "")
            if not bid or len(bid) > 256:
                log.error("enviar_botoes_resposta: button.id inválido (%r)", bid)
                return False, None
            if not btitle or len(btitle) > 20:
                log.error("enviar_botoes_resposta: button.title inválido (%r, len=%d)", btitle, len(btitle))
                return False, None
            if bid in ids_vistos:
                log.error("enviar_botoes_resposta: button.id duplicado (%r)", bid)
                return False, None
            ids_vistos.add(bid)
            action_buttons.append({
                "type": "reply",
                "reply": {"id": bid, "title": btitle},
            })

        interactive: dict = {
            "type": "button",
            "body": {"text": body_text},
            "action": {"buttons": action_buttons},
        }
        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "interactive",
            "interactive": interactive,
        }
        return self._post_com_retry(payload, numero, "botoes_resposta")

    def upload_midia_whatsapp(self, file_bytes: bytes, mime_type: str, filename: str) -> tuple[bool, str | None]:
        """Faz upload de mídia para Meta. Retorna (ok, media_id) — mesmo contrato
        dos demais métodos (B7: antes levantava exceção, contrato inconsistente)."""
        url = f"https://graph.facebook.com/v19.0/{self.phone_id}/media"
        try:
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                data={"messaging_product": "whatsapp", "type": mime_type},
                files={"file": (filename, file_bytes, mime_type)},
                timeout=30,
            )
            resp.raise_for_status()
            return True, resp.json()["id"]
        except (requests.RequestException, ValueError, KeyError) as e:
            log.error("upload_midia_whatsapp falhou: %s", e)
            return False, None

    def enviar_mensagem_midia(self, telefone: str, media_id: str, media_type: str, caption: str = "") -> tuple[bool, str | None]:
        """Envia mensagem de mídia via WhatsApp Business API. Retorna (ok, wamid)."""
        media_payload: dict = {"id": media_id}
        # B6: Meta suporta caption em image, document e video (não em audio).
        if caption and media_type in ("image", "document", "video"):
            media_payload["caption"] = caption
        payload = {
            "messaging_product": "whatsapp",
            "to": telefone,
            "type": media_type,
            media_type: media_payload,
        }
        return self._post_com_retry(payload, telefone, f"midia_{media_type}")

    def gerar_url_avatar(self, nome: str | None, telefone: str) -> str:
        """Gera URL de avatar DiceBear via iniciais — sem rede, sem auth, sem expiração."""
        from urllib.parse import quote
        seed = quote((nome or telefone or "?").strip())
        return (
            f"https://api.dicebear.com/7.x/initials/svg"
            f"?seed={seed}&backgroundColor=2481cc&radius=50&fontSize=40&fontFamily=Arial,sans-serif"
        )



def _extrair_uma_mensagem(message: dict, nome_cliente: str):
    """Converte um item de value.messages em (telefone, texto, nome, message_id)."""
    numero_cliente = message.get('from')
    tipo = message.get('type')
    message_id = message.get('id')

    if tipo == 'text':
        texto = message.get('text', {}).get('body')
        return numero_cliente, texto, nome_cliente, message_id
    elif tipo == 'interactive':
        interativo = message.get('interactive', {})
        tipo_interativo = interativo.get('type')
        if tipo_interativo == 'button_reply':
            payload = interativo.get('button_reply', {}).get('id')
            return numero_cliente, payload, nome_cliente, message_id
        elif tipo_interativo == 'list_reply':
            # Cliente selecionou item da Interactive List. Devolvemos o ID
            # da row como "texto" — o webhook decide o que fazer com MENU_*.
            payload = interativo.get('list_reply', {}).get('id')
            return numero_cliente, payload, nome_cliente, message_id
        # Tipo interactive desconhecido (futuro: nfm_reply etc) — ignora.
        return None, None, None, None
    else:
        return numero_cliente, f"MÍDIA_{tipo}", nome_cliente, message_id


def extrair_mensagens(body: dict) -> list[tuple]:
    """
    Extrai TODAS as mensagens de um payload Meta Cloud API.
    A Meta pode agrupar várias mensagens num único POST (batch) — processar só a
    primeira perdia as demais silenciosamente.
    Retorna lista de tuplas (telefone, texto, nome, message_id); vazia se nada útil.
    """
    try:
        entry = body.get('entry', [])[0]
        changes = entry.get('changes', [])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])
        if not messages:
            return []

        # Extração de Nome do Perfil (contato vale para o batch inteiro)
        nome_cliente = ""
        contacts = value.get('contacts', [])
        if contacts:
            nome_cliente = contacts[0].get('profile', {}).get('name', '')

        resultado = []
        for message in messages:
            try:
                extraida = _extrair_uma_mensagem(message, nome_cliente)
            except Exception:
                log.exception("Falha ao extrair uma mensagem do batch — pulando item.")
                continue
            if extraida[0] and extraida[1]:
                resultado.append(extraida)
        return resultado
    except Exception:
        log.exception("Falha ao extrair mensagens do payload Meta.")
        return []


def extrair_informacoes_mensagem(body: dict):
    """
    Wrapper de compatibilidade: devolve apenas a PRIMEIRA mensagem do payload.
    Retorna: (telefone, texto, nome, message_id) — Nones se não houver mensagem.
    Preferir extrair_mensagens() em código novo.
    """
    mensagens = extrair_mensagens(body)
    if not mensagens:
        return None, None, None, None
    return mensagens[0]
