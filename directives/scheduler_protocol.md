# POP — Protocolo de Agendamento (Beta)

Este POP define o fluxo determinístico para processar a fila de agendamentos do Reels Bot.

---

## 1. Objetivo
Processar posts agendados, realizar upload para Meta (Instagram/Facebook) e atualizar o estado global (GDrive + Local).

## 2. Entradas (Inputs)
- `.env`: Credenciais de API e configurações.
- `schedule_queue.json`: Fila de posts.
- `accounts.json`: Configurações de contas vinculadas.
- `posted_history.json`: Histórico de posts realizados.

## 3. Fluxo Operacional (DOE)

### Fase 1: Sincronização (Sync)
1. Rodar `execution/sync_manager.py --action download`.
2. O script deve baixar a fila e as contas do GDrive para o diretório local.
3. Se falhar no Drive, usar os arquivos locais existentes como Fallback.

### Fase 2: Processamento (Process)
1. Rodar `execution/content_processor.py`.
2. Para cada item na fila:
   - Verificar se `current_time >= schedule_time`.
   - Baixar mídia do GDrive para `.tmp/`.
   - Chamar Meta API para upload.
   - Retornar objeto de resultado (Sucesso/Falha parcial/Falha total).

### Fase 3: Limpeza e Histórico (Cleanup)
1. Rodar `execution/cleanup_tool.py --results results.json`.
2. Remover mídias temporárias em `.tmp/`.
3. Se postado com sucesso em todas as contas:
   - Deletar arquivo do GDrive.
   - Adicionar ao `posted_history.json`.
   - Remover da fila.
4. Se postado parcialmente:
   - Manter na fila apenas as contas que falharam.
5. Sincronizar estados de volta ao GDrive: `execution/sync_manager.py --action upload`.

## 4. Edge Cases e Falhas
- **Drive Inacessível**: O sistema deve continuar operando localmente e tentar sincronizar no próximo ciclo.
- **Falha de Upload (Meta)**: Manter o item na fila para tentar novamente em 1 hora (limite de 3 posts/hora).
- **Mídia Não Encontrada**: Registrar erro no log e passar para o próximo.

---

## Aprendizados (Learnings)
- **2026-04-03**: Inicialização da estrutura DOE para substituir o `main.py` monolítico.
