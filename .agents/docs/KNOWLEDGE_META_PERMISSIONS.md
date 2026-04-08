# Conhecimento: Permissões Meta Graph API (Comentários)

**Última atualização:** 2024-04-07
**Versão documentada:** v21.0 / v22.0
**Fonte:** [Meta Permissions Reference](https://developers.facebook.com/docs/permissions)

## Permissões Necessárias para Comentários

### 📘 Facebook (Páginas)
Para que o bot possa postar o "Primeiro Comentário" em uma página:
- **`pages_manage_engagement`**: CRÍTICO. Permite ao app criar, editar e excluir comentários e curtidas na página.
- **`pages_read_engagement`**: Necessário para visualizar o conteúdo da página onde o comentário será postado.
- **`pages_show_list`**: Permite que o app veja a lista de páginas que o usuário gerencia para obter o Token de Página.
- **`pages_manage_posts`**: Frequentemente necessário como base para interações em posts.

### 📸 Instagram (Business/Creator)
Para comentários no Instagram via API:
- **`instagram_manage_comments`**: CRÍTICO. Permite postar e gerenciar comentários em objetos de mídia do Instagram.
- **`instagram_basic`**: Permite ler metadados básicos das contas de Instagram vinculadas.
- **`instagram_content_publish`**: Já usado pelo bot para o post principal.

## Como Resolver o Erro "Invalid Scopes: pages_read_user_content"

Este erro ocorre porque o Graph API Explorer tenta injetar uma permissão legada que não existe mais na API v22.0.

### Procedimento de Limpeza:
1.  No **Graph API Explorer**, clique no ícone de **Reset/Limpar** (geralmente uma seta circular ou um "X" na lista de permissões à direita).
2.  Desmarque qualquer menção a `pages_read_user_content`.
3.  Adicione manualmente apenas:
    - `pages_manage_engagement`
    - `instagram_manage_comments`
    - `public_profile`
4.  Clique em **Generate Access Token**.

## Gotchas e Limitações
- **App Review**: Se o app estiver em modo "Live", essas permissões requerem App Review para usuários externos. Para o **Administrador do App**, elas funcionam em modo "Standard Access" imediatamente.
- **Token de Página vs Usuário**: O bot deve usar o **Page Access Token** para o Facebook. Um token de usuário não tem permissão para comentar como a página.

## MCPs Disponíveis
- Não há MCP oficial da Meta, mas a biblioteca `requests` no Python é o padrão ouro para esta integração.
