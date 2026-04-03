---
name: corrigindo-e-revisando-reels-bot
description: Skill organizadora do projeto Reels Bot. Garante que qualquer correção de bug seja acompanhada de uma revisão holística do projeto para evitar regressões e garantir consistência. Ative quando o usuário reportar um erro, uma exceção, um comportamento inesperado, ou dizer 'corrija isso', 'esse erro ocorreu', 'encontrei um problema', 'o bot está falhando', 'analise o projeto' ou qualquer variação que envolva diagnóstico, correção ou evolução inteligente do codebase do Reels Bot.
---

# Corrigindo e Revisando o Reels Bot

## Quando usar esta skill
- Usuário reporta um erro, traceback ou comportamento inesperado
- Usuário pede para corrigir, ajustar ou melhorar alguma parte do sistema
- Usuário quer evoluir o projeto com uma nova feature
- Antes de qualquer alteração em arquivo `.py` do projeto

---

## Mapa do Projeto (Leia antes de tocar em qualquer arquivo)

```
reels-bot/
├── main.py                  ← Orquestrador DOE (só chama scripts de execution/)
├── config.py                ← Lê .env: META_ACCESS_TOKEN, IG_ACCOUNT_ID, FB_PAGE_ID, GDRIVE_FOLDER_ID
├── meta_api.py              ← Toda lógica de upload para Instagram e Facebook
├── gdrive_api.py            ← Toda lógica de acesso ao Google Drive
├── gui.py                   ← Interface gráfica (CustomTkinter) — muito grande (~3600 linhas)
├── accounts.json            ← Lista de contas configuradas (IG + FB por conta)
├── schedule_queue.json      ← Fila de jobs agendados (lida e escrita pelo bot E pela GUI)
├── posted_history.json      ← Histórico de todos os posts realizados
├── settings.json            ← Configurações gerais persistidas pela GUI
├── directives/
│   └── scheduler_protocol.md  ← POP do agendador (documentação viva)
└── execution/               ← Scripts determinísticos chamados pelo main.py
    ├── sync_manager.py      ← Download/Upload de JSONs (queue, history, accounts) no Drive
    ├── content_processor.py ← Loop principal: verifica horário, baixa mídia, chama MetaAPI
    ├── cleanup_tool.py      ← Pós-processamento: limpa .tmp/, atualiza fila e histórico
    └── test_runner.py       ← Bateria de testes end-to-end (ativado por 'teste-agora')
```

### Contratos entre módulos (NUNCA quebre estes):

| Quem produz | O que produz | Quem consome |
|------------|-------------|-------------|
| `gui.py` | `schedule_queue.json` (jobs) | `content_processor.py` |
| `content_processor.py` | `.tmp/last_execution_results.json` | `cleanup_tool.py` |
| `cleanup_tool.py` | `posted_history.json`, `schedule_queue.json` (atualizado) | `gui.py`, `sync_manager.py` |
| `sync_manager.py` | JSONs sincronizados localmente | `content_processor.py`, `cleanup_tool.py` |
| `meta_api.py` | `True/False` (sucesso/falha do upload) | `content_processor.py`, `test_runner.py` |
| `gdrive_api.py` | Arquivos locais em `.tmp/`, file_ids | `content_processor.py`, `sync_manager.py`, `test_runner.py` |

### Estrutura de um Job na Fila (schedule_queue.json)
```json
{
  "gdrive_id": "string | null",
  "filename": "string",
  "media_type": "REELS | IMAGE | CAROUSEL",
  "caption": "string",
  "schedule_time": 1234567890,
  "accounts": [
    {
      "name": "string",
      "ig_account_id": "string | null",
      "fb_page_id": "string | null",
      "access_token": "string"
    }
  ]
}
```

---

## Checklist de Execução (Siga SEMPRE esta ordem)

### 🔍 Fase 1: Diagnóstico
- [ ] 1.1 Ler a mensagem de erro completa (traceback, linha, arquivo)
- [ ] 1.2 Identificar o arquivo e a função exata que falhou
- [ ] 1.3 Verificar se o erro é de: tipo de dado, contrato de API, lógica, permissão, ou encoding
- [ ] 1.4 Checar o "Mapa de contratos" acima — entender quem chama quem

### 🔧 Fase 2: Correção Cirúrgica
- [ ] 2.1 Fazer a menor alteração possível para corrigir o erro
- [ ] 2.2 Não refatorar ou "melhorar" código que não está no escopo do erro
- [ ] 2.3 Se a correção exige mudança de contrato (ex: novo campo no JSON), atualizar TODOS os consumidores

### 🔎 Fase 3: Revisão Holística (OBRIGATÓRIO após qualquer correção)
- [ ] 3.1 **meta_api.py**: As assinaturas dos métodos (`upload_ig_reels_resumable`, `upload_ig_image`, `upload_ig_carousel`, `upload_fb_*`) estão intactas?
- [ ] 3.2 **content_processor.py**: As chamadas à MetaAPI ainda batem com as assinaturas?
- [ ] 3.3 **cleanup_tool.py**: O formato de `last_execution_results.json` não mudou?
- [ ] 3.4 **sync_manager.py**: Os nomes dos arquivos JSON (`schedule_queue.json`, `posted_history.json`, `accounts.json`) não mudaram?
- [ ] 3.5 **gui.py**: A estrutura do job que a GUI gera ainda bate com o que `content_processor.py` espera?
- [ ] 3.6 **main.py**: Os caminhos dos scripts em `execution/` ainda existem?
- [ ] 3.7 **config.py / .env**: Nenhuma nova variável de ambiente foi necessária sem ser documentada?

### ✅ Fase 4: Validação
- [ ] 4.1 Checar sintaxe: `python -m py_compile <arquivo_alterado>.py`
- [ ] 4.2 Se possível, oferecer executar `python execution/test_runner.py` (diz "teste-agora" para usar)

### 📝 Fase 5: Atualizar a Documentação Viva
- [ ] 5.1 Se o erro revelou um edge case novo → adicionar em `directives/scheduler_protocol.md` (seção "Edge Cases")
- [ ] 5.2 Se um novo script foi criado → adicionar no mapa desta skill
- [ ] 5.3 Se a estrutura do JSON de job mudou → atualizar o "Contrato" desta skill

---

## Instruções de Diagnóstico por Tipo de Erro

### 🔴 `AttributeError` / `KeyError`
- Verificar se o campo existe no JSON de entrada
- Verificar se está usando `.get('campo', default)` em vez de `['campo']`
- Checar se a MetaAPI está retornando o formato esperado

### 🔴 `FileNotFoundError`
- Verificar se `.tmp/` existe (`os.makedirs('.tmp', exist_ok=True)`)
- Verificar se `gdrive_api.download_file()` retornou `None` antes de usar o path

### 🔴 Erro de encoding (Windows)
- Sempre usar `encoding='utf-8'` ao abrir arquivos JSON
- Evitar caracteres especiais em prints sem encoding safe

### 🔴 Erro de API Meta (HTTP 400/403)
- Verificar se o `access_token` não expirou (campo `token_expiry` em `accounts.json`)
- Verificar se `ig_account_id` e `fb_page_id` são strings (não int)
- Checar o campo `DEBUG FB:` nos logs — a API sempre retorna o motivo

### 🔴 Erro de GDrive
- Verificar se `GDRIVE_JSON_B64` está corretamente setado no `.env`
- Se `self.service is None` → credenciais não carregaram
- `None` retornado por `download_file` → arquivo não encontrado ou sem permissão

### 🔴 Conflito de merge (`<<<<<<<`)
- Nunca manter marcadores de merge no código
- Sempre manter a versão DOE (HEAD) e descartar a alternativa

---

## Princípios de Evolução do Projeto

1. **Pequenos passos**: Cada sessão deve ter um objetivo claro. Prefira 3 pequenas melhorias bem testadas a 1 grande mudança arriscada.
2. **Não quebre o que funciona**: Antes de refatorar, garanta que os testes passam.
3. **O bot deve sempre ser executável**: `python main.py --once` deve rodar sem erros após qualquer sessão.
4. **A GUI é sagrada**: `gui.py` é o maior arquivo do projeto (~3600 linhas). Edite com precisão cirúrgica — sempre ler o contexto antes de alterar.
5. **Dados reais > Suposições**: Se não tiver certeza do formato de retorno de uma API, adicione um `print(json.dumps(res, indent=2))` temporário e veja o retorno real antes de corrigir.

---

## Recursos

- [directives/scheduler_protocol.md](../directives/scheduler_protocol.md) — POP do agendador (documentação viva)
- [execution/content_processor.py](../execution/content_processor.py) — Motor de postagem
- [execution/test_runner.py](../execution/test_runner.py) — Testes end-to-end
