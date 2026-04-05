# ✅ Deu Certo — Reels Bot V2 Estável

**Data:** 05/04/2026 20:07 
**Projeto:** Reels Bot (BOT AGENDAMETOS FACE INSTA)

## O que funcionou

O bot agora está operando com uma GUI moderna e unificada via CustomTkinter, com suporte total para postagem de Imagens e Reels no Instagram e Facebook via Meta Graph API. Foram corrigidos problemas críticos de decodificação Unicode no scan de arquivos e implementada redundância de upload (fallback local) quando a cota do Google Drive é atingida. O sistema de agendamento visual permite selecionar mídias e datas com feedback em tempo real.

## Arquivos envolvidos

| Arquivo | Papel na solução |
|---------|-----------------|
| `gui.py` | Interface principal completa com abas de Biblioteca, Agendamento e Estatísticas. |
| `meta_api.py` | Integração estável com Meta Graph API para postagem de Reels e Imagens. |
| `gdrive_api.py` | Integração com Google Drive e tratamento de erros de cota (403). |
| `config.py` | Carregamento centralizado de credenciais e mapeamento de contas sociais. |
| `accounts.json` | Arquivo de tokens e IDs das páginas/contas IG configuradas. |
| `settings.json` | Preferências do usuário e configurações de sistema. |

## Como replicar

1. Verifique se os tokens de acesso de longa duração (User Access Token) estão válidos no `accounts.json`.
2. Garanta que o `credentials.json` (Google Drive) esteja presente se for usar nuvem.
3. Execute `python gui.py` para abrir a interface gráfica.
4. Utilize a aba "Biblioteca" para escanear e selecionar mídias, e a aba "Calendário" para definir datas e horários.

## Observações

- **Bypass de Drive**: Se a cota do Drive for excedida, o bot busca arquivos locais se disponíveis.
- **UTF-8**: O processamento de arquivos JSON agora utiliza codificação UTF-8 explícita para evitar erros em sistemas Windows com nomes de arquivos acentuados.
- **Postagem**: A postagem de Reels no Meta requer que o arquivo esteja acessível via URL pública ou que o bot o envie via container POST (suportado).
