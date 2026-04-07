# 💈 Chatbot Inteligente - Barbearia Bolshoi

O Recepcionista Digital Oficial da Barbearia Bolshoi via WhatsApp, utilizando Inteligência Artificial (Gemini API) e FastAPI.

## 📌 Visão Geral do Projeto
O bot atua como um Concierge digital, construído em **Python (FastAPI)** com **MySQL** e conectado à **Meta Cloud API (WhatsApp)**.
As responsabilidades principais atendem rigorosamente à documentação original:
1. **FAQ Inteligente:** Responde perguntas sobre preços, horários e barbeiros com leitura rápida do banco de dados para evitar "alucinações".
2. **Redirecionamento Rígido:** Não agenda diretamente, envia sempre o link oficial do AppBarber.
3. **Triagem e Transbordo Humano:** Capacidade estrita de "calar a boca" (`bot_ativo = False`) quando o cliente manifestar problemas insolucionáveis ou desejar contato.

---

## 🛠 Pré-requisitos (O que você precisa para testar)

Para rodar este bot localmente 100% integrado ao WhatsApp e ao Google Gemini, certifique-se de que os itens abaixo estão cumpridos em sua máquina.

### 1. Conta Meta for Developers (WhatsApp)
Você deve possuir um App de teste na Meta For Developers.
- Anote o seu **Número de Identificação do Telefone** (`WHATSAPP_PHONE_ID`).
- Gere um **Token de Acesso Temporário** (`WHATSAPP_TOKEN`). (Dura 24 horas para testes).
- Anote no celular o número do WhatsApp de testes do Facebook e libere seu número pra testes.

### 2. Conta Google AI Studio (Gemini)
Você deve possuir uma chave de API para o Google Gemini.
- Gere em: [Google AI Studio](https://aistudio.google.com/app/apikey).
- Tenha certeza de copiar a `GEMINI_API_KEY`.

### 3. Banco de Dados MySQL
Mantenha o banco de dados rodando na porta padrão (Ex: XAMPP, Wampserver, etc). O modelo já contém as tabelas mapeadas no arquivo SQL providenciado.

---

## 🚀 Passo a Passo para Inicializar e Testar Hoje

Siga exatamente a ordem abaixo para subir o servidor e plugar no WhatsApp:

### Passo 1: Configurar Arquivo Secreto
Você precisará ter o seu arquivo `.env` alimentado na raiz do projeto:
```env
DB_USER=root
DB_PASS=SuaSenhaMySQL
DB_HOST=localhost
DB_NAME=barbearia_bot_db

WHATSAPP_PHONE_ID=seu_phone_id_aqui
WHATSAPP_TOKEN=seu_token_temporario_aqui
WEBHOOK_VERIFY_TOKEN=barbearia_bot_123

GEMINI_API_KEY=sua_api_key_do_gemini
```

### Passo 2: Instalar as Dependências
Utilize o Terminal do VSCode para instalar as bibliotecas do projeto (Opcional, se não tiver as feito na rodada de build):
```bash
pip install -r requirements.txt
```

### Passo 3: Criar um Túnel Público (Ngrok)
O Facebook exige uma URL pública com HTTPS para o Webhook para onde as mensagens serão enviadas.
```bash
ngrok http 8000
```
Isso gerará um link `https://xxxx.ngrok-free.app`. Copie a URL gerada (Sem a porta no final).

### Passo 4: Subir o Servidor FastAPI
Em um **2º Terminal** do VSCode, inicie a aplicação:
```bash
python main.py
```
O console exibirá "Application startup complete" e monitorará todos os contatos com as APIS em tempo real.

### Passo 5: Plugar a URL no Meta for Developers
Retorne ao painel da Meta For Developers > WhatsApp > API Setup > Configuration (Configurar Webhook):
- **URL de callback:** Cole a URL do Ngrok seguida de `/webhook`. (Ex: `https://xxxx.ngrok-free.app/webhook`).
- **Verificar token:** Escreva `barbearia_bot_123`.
- Clique em **Verificar e Salvar**.

*(📍 MUITO Importante: Na tabela "Campos de Webhook", mesma tela abaixo, encontre a palavra `messages` e clique em **Inscrever-se/Subscribe** ao final da linha).*

---

## 📱 Como Testar no Celular e Regras de Negócio

Abra o seu próprio WhatsApp, mande mensagem para o número provisório e teste na prática as regras aplicadas:

1. **Dúvida Operacional Livre:** "Quanto custa o corte e o que é o nanoblading?" A Inteligência Artificial buscará no MySQL e listará preços, seguidos das opções rápidas em botões.
2. **Pedir para Falar com Atendente (Traçagem/Transbordo):** Diga "Preciso falar com um humano". Ao bater nessa intenção forçada, a coluna do BD reterá `bot_ativo = False`, o atendente se dispõe e não haverá eco nas msgs.
3. **Botão de Agendamento:** Clicar num botão bypassa o IA, devolvendo na mesma hora o texto com Link do AppBarber. 

### 🤫 Destrancando o Bot Manualmente (P/ Desenvovedores)
Nos testes pesados, muito frequentemente você irá querer testar as ramificações mais de uma vez na mesma conversa, e a "Trava Humana" fará o bot calar.
Basta mandar no celular o comando secreto local:
**`!reiniciar`**
O seu banco de dados reverterá o desligamento instantaneamente!
