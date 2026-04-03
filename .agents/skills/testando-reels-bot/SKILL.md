---
name: testando-reels-bot
description: Executa uma bateria de testes end-to-end no Reels Bot, testando todos os tipos de mídia (Reels/Vídeo, Imagem e Carrossel) nas contas configuradas. Ative quando o usuário disser 'teste-agora', 'testar o bot', 'rodar testes' ou qualquer variação que peça para validar o funcionamento do sistema de postagem. Ao final, retorna um relatório com links das postagens bem-sucedidas e descrição detalhada dos erros.
---

# Testando o Reels Bot (Bateria End-to-End)

## Quando usar esta skill
- Usuário diz `teste-agora`, `testar o bot`, `rodar testes`, `verificar se está funcionando`
- Após alterações no código para validar que nada quebrou
- Ao suspeitar de falhas silenciosas nas postagens

---

## Visão Geral do Fluxo

```
1. Gerar mídias de teste (pixel, imagem placeholder, carousel) em .tmp/test/
2. Injetar jobs na schedule_queue.json com schedule_time no passado
3. Executar python main.py --once
4. Extrair log de saída e comparar com posted_history.json
5. Consultar Meta API para obter links das postagens
6. Gerar relatório final em .tmp/test_report.md
```

---

## Checklist de Execução

- [ ] 1. Gerar arquivos de mídia de teste
- [ ] 2. Fazer upload dos arquivos para o Google Drive (para teste realista)
- [ ] 3. Injetar jobs na fila com `schedule_time = int(time.time()) - 60`
- [ ] 4. Executar `python main.py --once` e capturar o stdout/stderr
- [ ] 5. Aguardar conclusão e verificar `posted_history.json`
- [ ] 6. Consultar a Meta API para confirmar os links das postagens
- [ ] 7. Gerar `.tmp/test_report.md` com resultado completo
- [ ] 8. Limpar arquivos de teste do Drive e da fila

---

## Fluxo de Trabalho

### Passo 1: Executar o script de teste
O agente deve rodar:
```bash
python execution/test_runner.py
```

Este script realiza todos os passos automaticamente. Veja `execution/test_runner.py`.

### Passo 2: Aguardar e monitorar
- O script levará vários minutos (uploads para Meta API são lentos)
- Acompanhe o progresso via stdout
- Em caso de erro fatal, verifique `.tmp/test_runner.log`

### Passo 3: Ler o relatório
Após a conclusão, o relatório estará em `.tmp/test_report.md`.
O agente deve lê-lo e apresentar ao usuário de forma resumida.

---

## Instruções

### Tipos de Mídia Testados
| Teste | Plataforma | Tipo | Descrição |
|-------|-----------|------|-----------|
| T1 | Instagram | REELS | Vídeo .mp4 curto (pixel preto) |
| T2 | Instagram | IMAGE | Imagem .jpg (placeholder colorido) |
| T3 | Instagram | CAROUSEL | 2x imagens .jpg |
| T4 | Facebook | REELS | Mesmo vídeo do T1 |
| T5 | Facebook | IMAGE | Mesma imagem do T2 |
| T6 | Facebook | CAROUSEL | Mesmas imagens do T3 |

### Contas Testadas
- Todas as contas em `accounts.json` são testadas
- O scope de contas pode ser limitado setando `TEST_ACCOUNTS = ["Nome da Conta"]` antes de rodar

### Critérios de Sucesso
- ✅ Sucesso: `meta_api` retornou `True` E o ID aparece no `posted_history.json`
- ❌ Falha: retornou `False` ou levantou exceção — capturar a mensagem de erro completa

### Formato do Relatório Final (gerado em `.tmp/test_report.md`)
```markdown
# Relatório de Testes — Reels Bot
**Data:** YYYY-MM-DD HH:MM
**Duração:** X.X segundos
**Score:** X/X testes passaram

## ✅ Sucessos
| Conta | Plataforma | Tipo | ID do Post | Link |
| ...   | ...        | ...  | ...        | ...  |

## ❌ Falhas
| Conta | Plataforma | Tipo | Erro |
| ...   | ...        | ...  | ...  |
```

---

## Recursos

- [execution/test_runner.py](execution/test_runner.py) — Script principal de execução dos testes
