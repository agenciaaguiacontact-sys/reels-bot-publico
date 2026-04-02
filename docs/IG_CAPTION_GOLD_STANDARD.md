# Guia da Configuração de Ouro (Instagram Captions)

Este documento registra a configuração que finalmente resolveu o problema das legendas que sumiam no Instagram Reels. **NÃO ALTERE ESTAS REGRAS** sem testar exaustivamente.

## Regra 1: O Limite Mortal de 30 Hashtags
- **O Problema**: O Instagram Reels permite no máximo **30 hashtags**. 
- **O Sintoma**: Se você enviar 31 ou mais hashtags, a API publica o vídeo com sucesso, mas **apaga a legenda inteira** sem dar aviso de erro.
- **A Solução**: Implementamos uma "trava" no `meta_api.py` que conta as hashtags e corta automaticamente o excedente para proteger o texto da legenda.

## Regra 2: Codificação de URL (API v25.0)
- **O Problema**: A API da Meta no modo `video_url` (v25.0) é temperamental com o corpo da requisição (POST body).
- **A Solução**: Enviar as informações do container (`media_type`, `video_url`, `caption`, `access_token`) através do argumento `params=payload` no Python. Isso as coloca na Query String da URL de forma segura.
- **Dica de Encoding**: O `requests` cuida da codificação. Tentamos forçar `%20` manualmente antes, mas descobrimos que o segredo era apenas respeitar o limite das 30 hashtags.

## Regra 3: Limites de Tamanho e FFmpeg
- **O Problema**: Vídeos acima de 95MB via URL costumam falhar no processamento de legenda no Instagram.
- **A Solução**: Todo vídeo acima de 90MB é comprimido via FFmpeg para ~85MB usando o filtro de escala fixed no `meta_api.py`.

---
*Configuração validada e estabilizada em 28/03/2026.*
