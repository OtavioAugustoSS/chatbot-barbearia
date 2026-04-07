import os
import requests
from dotenv import load_dotenv

load_dotenv()

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
        response = requests.post(self.url, headers=self.headers, json=payload)
        # Debugging importante para sabermos a resposta da API Oficial
        print("====== RETORNO FACEBOOK (TEXTO) ======")
        print(response.text)
        return response.json()

    def enviar_mensagem_botoes(self, numero: str, texto: str, botoes: list):
        """
        Envia uma mensagem interativa com botões de resposta rápida.
        O layout esperado para os botoes é:
        [{"type": "reply", "reply": {"id": "ID_DO_BOTAO", "title": "Texto Visível"}}]
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": texto},
                "action": {
                    "buttons": botoes
                }
            }
        }
        response = requests.post(self.url, headers=self.headers, json=payload)
        return response.json()

def extrair_informacoes_mensagem(body: dict):
    """
    Função auxiliar padrão Meta Cloud API para extrair dados 
    brutos recebidos pelo webhook do Whatsapp.
    """
    try:
        entry = body.get('entry', [])[0]
        changes = entry.get('changes', [])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])
        
        if not messages:
            return None, None
            
        message = messages[0]
        numero_cliente = message.get('from')
        tipo = message.get('type')
        
        if tipo == 'text':
            texto = message.get('text', {}).get('body')
            return numero_cliente, texto
        elif tipo == 'interactive':
            interativo = message.get('interactive', {})
            tipo_interativo = interativo.get('type')
            if tipo_interativo == 'button_reply':
                payload = interativo.get('button_reply', {}).get('id')
                return numero_cliente, payload
        else:
            return numero_cliente, f"MÍDIA_{tipo}"

    except Exception:
        return None, None
