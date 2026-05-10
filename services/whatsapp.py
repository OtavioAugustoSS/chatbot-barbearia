import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("barbearia.whatsapp")


class WhatsAppSender:
    def __init__(self):
        self.token = os.getenv("WHATSAPP_TOKEN")
        self.phone_id = os.getenv("WHATSAPP_PHONE_ID")
        self.url = f"https://graph.facebook.com/v19.0/{self.phone_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def enviar_mensagem_texto(self, numero: str, texto: str):
        payload = {
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "text",
            "text": {"body": texto}
        }
        try:
            response = requests.post(self.url, headers=self.headers, json=payload, timeout=10)
        except requests.RequestException as e:
            log.error("Falha de rede ao enviar mensagem para %s: %s", numero, e)
            return None

        if response.status_code >= 400:
            # Apenas erros vão pro log, e em DEBUG; sucesso silencioso pra não vazar metadados.
            log.error("Meta API erro %s para %s: %s", response.status_code, numero, response.text[:500])
        else:
            log.debug("Mensagem enviada para %s (status %s)", numero, response.status_code)

        try:
            return response.json()
        except ValueError:
            return None


def extrair_informacoes_mensagem(body: dict):
    """
    Função auxiliar padrão Meta Cloud API para extrair dados
    brutos recebidos pelo webhook do Whatsapp.
    Retorna: (telefone, texto, nome, message_id)
    """
    try:
        entry = body.get('entry', [])[0]
        changes = entry.get('changes', [])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])

        if not messages:
            return None, None, None, None

        message = messages[0]
        numero_cliente = message.get('from')
        tipo = message.get('type')
        message_id = message.get('id')

        # Extração de Nome do Perfil
        nome_cliente = ""
        contacts = value.get('contacts', [])
        if contacts:
            nome_cliente = contacts[0].get('profile', {}).get('name', '')

        if tipo == 'text':
            texto = message.get('text', {}).get('body')
            return numero_cliente, texto, nome_cliente, message_id
        elif tipo == 'interactive':
            interativo = message.get('interactive', {})
            tipo_interativo = interativo.get('type')
            if tipo_interativo == 'button_reply':
                payload = interativo.get('button_reply', {}).get('id')
                return numero_cliente, payload, nome_cliente, message_id
        else:
            return numero_cliente, f"MÍDIA_{tipo}", nome_cliente, message_id

    except Exception:
        return None, None, None, None
