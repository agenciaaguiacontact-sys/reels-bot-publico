# Manual de Uso Diário: Reels Bot Cloud

> Para quem já configurou o bot e quer saber como usá-lo no dia a dia.

---

## Como Iniciar o Bot

### Opção 1: Interface Gráfica (Recomendado)

Abra o terminal na pasta do projeto e execute:

```bash
# Ativar ambiente virtual primeiro (se necessário)
.venv\Scripts\Activate.ps1   # Windows PowerShell
# ou
.venv\Scripts\activate.bat   # Windows CMD

# Iniciar a GUI
python gui.py
```

A janela do **Reels Bot** abre com dashboard, biblioteca, agenda e contas.

### Opção 2: Backend Automático (Servidor)

```bash
# Roda em loop infinito, verificando a fila a cada 60 segundos
python main.py

# Para testar uma única execução do ciclo completo:
python main.py --once
```

---

## Operações Principais

### 🎬 Postagem Imediata (Manual)

1. Faça upload do vídeo/imagem/zip para a pasta do Google Drive da conta
2. Abra a GUI: `python gui.py`
3. Vá para a aba **Biblioteca**
4. Clique em **🔄 Atualizar** para listar os arquivos do Drive
5. Selecione o(s) arquivo(s) desejados (checkbox)
6. Clique em **📅 Agendar Selecionados**
7. No wizard:
   - Selecione as contas onde publicar
   - Defina o horário (coloque data/hora atual ou no passado para postar imediatamente)
   - Adicione ou edite a legenda
8. Clique em **✅ Confirmar Agendamento**
9. Execute o ciclo de processamento: `python main.py --once`

---

### 📅 Agendamento Futuro (Recomendado)

1. Faça upload do(s) vídeo(s) para o Drive da conta
2. Abra a GUI: `python gui.py`
3. Vá para a aba **Agenda** ou **Biblioteca**
4. Selecione os arquivos
5. No calendário, clique nas **datas desejadas** para marcá-las
6. Clique em **✨ Agendar Selecionados**
7. No wizard:
   - ✅ Marque as contas
   - 🕘 Defina horário de início
   - 🔁 Configure intervalo entre posts se houver múltiplos vídeos
   - 📝 Edite a legenda (ou use o padrão de `settings.json`)
8. **Confirmar** — os posts são adicionados à `schedule_queue.json`
9. O backend (`python main.py`) vai publicar automaticamente na hora certa

---

### 📁 Tipos de Mídia Suportados

| Tipo | Extensão no Drive | Como preparar |
|------|-------------------|---------------|
| **Reels/Vídeo** | `.mp4` | Vídeo direto na pasta do Drive |
| **Imagem** | `.jpg`, `.jpeg`, `.png` | Imagem direto na pasta do Drive |
| **Carrossel** | `.zip` | Compacte as imagens em um ZIP, faça upload do ZIP |

> ⚠️ O nome do arquivo ZIP aparecerá com ícone 🎠 na biblioteca.

---

### 👤 Gerenciar Contas

**Adicionar nova conta:**
1. GUI → Aba **Contas**
2. Clique em **+ Adicionar Conta**
3. Cole o Access Token Meta na caixa de detecção automática
4. Clique em **Buscar Dados** — a GUI preenche os IDs automaticamente
5. Adicione o `gdrive_folder_id` da pasta desta conta
6. **Salvar**

**Editar conta existente:**
1. GUI → Aba **Contas**
2. Clique no ícone ✏️ ao lado da conta
3. Modifique os campos necessários
4. **Salvar**

**Remover conta:**
1. GUI → Aba **Contas**
2. Clique no ícone 🗑️ ao lado da conta
3. Confirme a remoção

---

### 🔑 Renovar Token (Importante!)

Os tokens Meta expiram em aproximadamente **60 dias**. Para renovar:

1. GUI → Aba **Contas**
2. Selecione a conta com token expirando
3. Clique em **🔄 Renovar Token**
4. A GUI faz a requisição automaticamente e atualiza `accounts.json`
5. **Salvar**

> ⏰ Observe o campo `token_expiry` em `accounts.json` — é um timestamp Unix. Converta em [epochconverter.com](https://epochconverter.com) para saber a data exata.

---

## Manutenção Rotineira

### Verificações Semanais

- [ ] **Tokens Meta**: verifique `token_expiry` em `accounts.json` — renove se faltar menos de 7 dias
- [ ] **Espaço no Drive**: verifique se há acúmulo de arquivos antigos não deletados
- [ ] **`posted_history.json`**: confirme que os posts recentes aparecem no histórico
- [ ] **Logs de erro**: verifique os arquivos `final_debug_log_*.txt` por erros recorrentes

### Limpeza Manual (se necessário)

```bash
# Limpar pasta temporária
Remove-Item -Recurse -Force .tmp\*

# Verificar fila atual
python -c "import json; q=json.load(open('schedule_queue.json')); print(f'{len(q)} jobs na fila')"

# Verificar histórico
python -c "import json; h=json.load(open('posted_history.json')); print(f'{len(h)} posts realizados')"
```

---

## Referência Rápida de Comandos

| Ação | Comando |
|------|---------|
| Abrir GUI | `python gui.py` |
| Rodar bot automático | `python main.py` |
| Rodar 1 ciclo só | `python main.py --once` |
| Baixar estados do Drive | `python execution/sync_manager.py --action download` |
| Enviar estados ao Drive | `python execution/sync_manager.py --action upload` |
| Instalar dependências | `pip install -r requirements.txt` |
| Ativar venv (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Ver fila de agendamentos | `python -c "import json; print(json.dumps(json.load(open('schedule_queue.json')), indent=2, ensure_ascii=False))"` |
| Ver histórico de posts | `python -c "import json; print(json.dumps(json.load(open('posted_history.json')), indent=2, ensure_ascii=False))"` |
| Rodar testes E2E | `python execution/test_runner.py` |

---

## Quando Algo Dá Errado

### 🔴 Bot não posta nada

1. Verifique se o `schedule_time` no `schedule_queue.json` já passou:
   ```bash
   python -c "import json,time; q=json.load(open('schedule_queue.json')); [print(j['filename'], 'DUE' if time.time()>=j['schedule_time'] else 'FUTURO') for j in q]"
   ```
2. Verifique se o token Meta não expirou — abra a GUI → Contas → Renovar Token
3. Verifique se o `gdrive_id` no job existe no Drive
4. Rode manualmente: `python main.py --once` e leia os logs no terminal

### 🔴 Erro "OAuthException" ou "Invalid OAuth access token"

- Token expirado → GUI → Contas → Renovar Token
- Token sem permissões → [Graph API Explorer](https://developers.facebook.com/tools/explorer/) → gerar novo token com todas as permissões necessárias

### 🔴 Erro "File not found" no Google Drive

- O arquivo foi deletado do Drive (por `cleanup_tool` após post bem-sucedido) mas ainda está na fila
- Solução: edite `schedule_queue.json` e remova o job com o `gdrive_id` do arquivo deletado

### 🔴 GUI não abre / trava

- Verifique se `customtkinter` está instalado: `pip install customtkinter`
- Verifique encoding do terminal (Windows): `chcp 65001`
- Tente iniciar sem ambiente virtual e veja o erro completo

### 🔴 Posts duplicados

- O `posted_history.json` pode ter sido apagado acidentalmente
- Restaure o histórico do Drive: `python execution/sync_manager.py --action download`

### 🔴 Drive não sincroniza

- Verifique se `credentials.json` existe na raiz
- Verifique se a Service Account tem acesso à pasta: Drive → Compartilhar → verifique o e-mail da SA
- Verifique se `GDRIVE_FOLDER_ID` está correto (apenas o ID, não a URL completa)

---

## Tokens — Quando Renovar

| Credencial | Validade | Como Renovar | Onde Verificar |
|-----------|---------|--------------|---------------|
| `access_token` (Meta) | ~60 dias | GUI → Contas → Renovar Token | `accounts.json` → campo `token_expiry` (timestamp Unix) |
| `credentials.json` (Google SA) | **Permanente** | Não precisa renovar | Arquivo físico |
| `GDRIVE_FOLDER_ID` | **Permanente** | Não precisa renovar | `.env` |
| App Meta (`client_id/secret`) | **Permanente** | Raramente — somente se o app for suspenso | `meta_api.py` linha 170 |

### Como converter `token_expiry` em data legível:
```bash
python -c "import json,datetime; a=json.load(open('accounts.json')); [print(x['name'], datetime.datetime.fromtimestamp(x.get('token_expiry',0))) for x in a]"
```

---

## Fluxo Resumido do Dia a Dia

```
1. Upload de vídeos → Google Drive (pasta da conta certa)
2. Abrir GUI → python gui.py
3. Biblioteca → Atualizar → Selecionar vídeos
4. Agendar → Escolher contas + datas + horário + legenda
5. Confirmar → schedule_queue.json atualizado
6. Deixar rodando → python main.py (em background)
   └── A cada 60s verifica a fila e publica no horário certo
7. Verificar resultados → posted_history.json ou Dashboard da GUI
```

---

## Dicas de Produtividade

- **Caption padrão**: Defina `default_caption` em `settings.json` com sua legenda padrão e hashtags
- **Múltiplos vídeos de uma vez**: Selecione vários arquivos na biblioteca e agende todos de uma vez — o wizard distribui nos dias selecionados
- **Monitoramento overnight**: Inicie `python main.py` antes de dormir e verifique `posted_history.json` de manhã
- **Backup da fila**: Antes de editar `schedule_queue.json` manualmente, copie o arquivo atual como backup
