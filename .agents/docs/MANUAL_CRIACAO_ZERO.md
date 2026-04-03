# Manual de Criação do Zero: Reels Bot Cloud

> Este manual te guia desde uma máquina vazia até o bot funcionando completamente do zero.

---

## Pré-requisitos

| Software | Versão Mínima | Download |
|----------|--------------|---------|
| Python | 3.10+ (testado no 3.12) | [python.org](https://python.org/downloads) |
| Git | Qualquer | [git-scm.com](https://git-scm.com) |
| Conta Meta for Developers | — | [developers.facebook.com](https://developers.facebook.com) |
| Conta Google Cloud | — | [console.cloud.google.com](https://console.cloud.google.com) |
| Instagram Professional (Business ou Creator) | — | Configurar nas Configurações do Instagram |
| Facebook Page conectada ao Instagram | — | Meta Business Suite |

---

## Passo 1: Obter o Código

```bash
# Clone o repositório
git clone <URL_DO_REPO> reels-bot
cd reels-bot
```

Ou copie a pasta do projeto manualmente para o seu computador.

---

## Passo 2: Criar Ambiente Virtual e Instalar Dependências

```bash
# Criar ambiente virtual
python -m venv .venv

# Ativar (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Ativar (Windows CMD)
.venv\Scripts\activate.bat

# Ativar (Linux/Mac)
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

Dependências instaladas:
- `requests` — chamadas HTTP
- `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-api-python-client` — Google Drive
- `python-dotenv` — leitura do `.env`
- `customtkinter` — GUI moderna
- `Pillow` — imagens
- `pytz` — timezone Brasil

---

## Passo 3: Configurar o Google Drive (Service Account)

### 3.1 — Criar projeto no Google Cloud Console

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Clique em **Novo Projeto** → dê um nome (ex: `reels-bot`)
3. Selecione o projeto criado

### 3.2 — Ativar a Google Drive API

1. Menu → **APIs e Serviços** → **Biblioteca**
2. Pesquise `Google Drive API`
3. Clique em **Ativar**

### 3.3 — Criar Service Account

1. Menu → **IAM e Administração** → **Contas de serviço**
2. Clique em **Criar conta de serviço**
3. Nome: `reels-bot-drive` (qualquer nome)
4. Papel: **Editor** (ou **Proprietário** para permissão total)
5. Clique em **Concluído**

### 3.4 — Gerar a chave JSON

1. Clique na conta de serviço criada
2. Aba **Chaves** → **Adicionar chave** → **Criar nova chave**
3. Selecione **JSON** → **Criar**
4. Um arquivo `*.json` será baixado — este é o seu `credentials.json`
5. **Renomeie para `credentials.json`** e copie para a raiz do projeto

### 3.5 — Criar e compartilhar a pasta no Google Drive

1. Acesse [drive.google.com](https://drive.google.com)
2. Crie uma pasta (ex: `Reels Bot - Videos`)
3. Clique com botão direito → **Compartilhar**
4. Compartilhe com o **e-mail da service account** (ex: `reels-bot-drive@projeto.iam.gserviceaccount.com`) como **Editor**
5. Copie o **ID da pasta** da URL: `https://drive.google.com/drive/folders/`**`SEU_FOLDER_ID`**

> 💡 **Dica**: Crie uma pasta por conta do Instagram que você vai gerenciar. Cada conta pode ter sua própria pasta no Drive.

---

## Passo 4: Configurar o Aplicativo Meta

### 4.1 — Criar/Confirmar app no Meta for Developers

1. Acesse [developers.facebook.com/apps](https://developers.facebook.com/apps)
2. Crie um app do tipo **Negócios** ou use um existente
3. Adicione o produto **Instagram Graph API** ao app
4. Adicione o produto **Facebook Pages API** ao app

> ⚠️ O projeto já vem com `client_id` e `client_secret` hardcoded no `meta_api.py` (linhas 170). Esses são do app Meta já configurado. Se você não tiver seu próprio app, pode usar esses valores — mas para produção, recomenda-se criar o seu.

### 4.2 — Obter o Page Access Token (por conta)

Para **cada conta** que você quer gerenciar:

1. Acesse [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Selecione seu **App** no topo
3. Em **User or Page** → selecione a **Página do Facebook** da conta
4. Clique em **Gerar Token de Acesso**
5. Conceda as permissões: `pages_manage_posts`, `pages_read_engagement`, `instagram_basic`, `instagram_content_publish`, `publish_video`
6. Copie o token gerado

> 🔑 Este é o **Short-Lived Token**. Converta para Long-Lived Token (60 dias):
> ```
> GET https://graph.facebook.com/v25.0/oauth/access_token
>   ?grant_type=fb_exchange_token
>   &client_id=SEU_APP_ID
>   &client_secret=SEU_APP_SECRET
>   &fb_exchange_token=SEU_SHORT_LIVED_TOKEN
> ```

### 4.3 — Obter IDs das contas

**Instagram Business Account ID:**
```
GET https://graph.facebook.com/v25.0/me/accounts
  ?fields=name,instagram_business_account{id,username}
  &access_token=SEU_TOKEN
```
Procure `instagram_business_account.id` na resposta.

**Facebook Page ID:**
O mesmo endpoint acima retorna `id` para cada página — esse é o `fb_page_id`.

---

## Passo 5: Criar o Arquivo `.env`

Crie um arquivo chamado `.env` na raiz do projeto:

```env
# Token e IDs PADRÃO (conta principal ou fallback)
META_ACCESS_TOKEN=EAASPZAaNHHcYBR...  ← seu Page Access Token aqui
IG_ACCOUNT_ID=17841456604444988       ← ID da conta Instagram Business
FB_PAGE_ID=547184908483685            ← ID da Página Facebook

# Google Drive
GDRIVE_FOLDER_ID=1WmvdB-n-jXMyxQYAw47kFFQocs5Keyyi  ← ID da pasta Drive

# Opcional: se não quiser usar credentials.json como arquivo físico
# GDRIVE_JSON_B64=base64_do_seu_credentials_json_aqui
```

> ⚠️ O `.env` está listado no `.gitignore` — ele nunca deve ser commitado.

---

## Passo 6: Criar Arquivos de Estado Iniciais

Esses arquivos precisam existir antes do primeiro run:

```bash
# Fila de agendamentos (começa vazia)
echo "[]" > schedule_queue.json

# Histórico de posts (começa vazio)
echo "[]" > posted_history.json

# Pasta temporária
mkdir .tmp
```

O arquivo `accounts.json` é gerenciado pela GUI — pode iniciar como:
```bash
echo "[]" > accounts.json
```

---

## Passo 7: Configurar Contas via GUI

1. Execute a interface gráfica:
```bash
python gui.py
```

2. Na aba **Contas** (ou Configurações):
   - Clique em **Adicionar Conta**
   - Preencha:
     - **Nome**: nome identificador (ex: `Dentista Curioso`)
     - **Access Token**: token obtido no Passo 4
     - **IG Account ID**: ID do Instagram Business
     - **FB Page ID**: ID da Página do Facebook
     - **GDrive Folder ID**: ID da pasta do Drive desta conta
   - Clique em **Salvar**

3. Para buscar automaticamente, cole um token na caixa de detecção automática — a GUI consulta `/me/accounts` e preenche os campos.

---

## Passo 8: Primeiro Run

### Modo GUI (recomendado para uso diário):
```bash
python gui.py
```

### Modo Backend Automático (para servidor/cron):
```bash
python main.py
```

### Execução única (para testar):
```bash
python main.py --once
# ou
RUN_ONCE=true python main.py
```

---

## Verificação de Funcionamento

✅ **GUI inicia sem erros** → Python e dependências corretos

✅ **Drive lista vídeos** → `credentials.json` e `GDRIVE_FOLDER_ID` corretos

✅ **Conta aparece** → Token Meta válido e IDs corretos

✅ **Post de teste funciona** → Agende um post para agora mesmo e rode `python main.py --once`

✅ **Arquivo some do Drive após post** → O `cleanup_tool.py` está funcionando

---

## Estrutura de Diretórios que Precisa Existir

```
reels-bot/
├── .env                    ← CRIAR (ver Passo 5)
├── credentials.json        ← COPIAR do Google Cloud Console
├── accounts.json           ← CRIAR como [] ou via GUI
├── schedule_queue.json     ← CRIAR como []
├── posted_history.json     ← CRIAR como []
├── settings.json           ← Criado automaticamente pela GUI
├── library.json            ← Criado automaticamente pela GUI
├── .tmp/                   ← CRIAR pasta vazia
├── downloads/              ← Criado automaticamente
├── config.py               ← Já existe no repositório
├── main.py                 ← Já existe no repositório
├── gui.py                  ← Já existe no repositório
├── meta_api.py             ← Já existe no repositório
├── gdrive_api.py           ← Já existe no repositório
├── requirements.txt        ← Já existe no repositório
├── directives/
│   └── scheduler_protocol.md
├── execution/
│   ├── content_processor.py
│   ├── sync_manager.py
│   ├── cleanup_tool.py
│   └── test_runner.py
```

---

## Solução de Problemas Comuns

### ❌ `ModuleNotFoundError: No module named 'customtkinter'`
```bash
pip install customtkinter
# ou reinstale tudo:
pip install -r requirements.txt
```

### ❌ `META_ACCESS_TOKEN não configurado no .env`
- Verifique se o arquivo `.env` existe na raiz do projeto
- Verifique se a variável `META_ACCESS_TOKEN` está correta (sem espaços)
- Tente: `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('META_ACCESS_TOKEN'))"`

### ❌ `Erro ao carregar credenciais do Google Drive`
- Confirme que `credentials.json` está na raiz do projeto
- Confirme que a Service Account tem acesso à pasta do Drive
- Confirme que o `GDRIVE_FOLDER_ID` é o ID correto (não a URL completa)

### ❌ `Error Container IG Reels` / `OAuthException`
- Seu token Meta expirou → Abra a GUI → Aba Contas → Renovar Token
- Verifique se seu app Meta tem as permissões `instagram_content_publish` e `publish_video`

### ❌ `tmpfiles.org` falha e o vídeo não sobe para o IG
- O serviço tmpfiles.org está fora do ar temporariamente
- O sistema tentará usar o Google Drive como URL pública automaticamente
- Aguarde e tente novamente

### ❌ Erro de encoding no terminal Windows
```bash
# Execute antes de rodar o bot:
chcp 65001
python main.py
```

### ❌ `posted_history.json` não encontrado
```bash
echo "[]" > posted_history.json
```
