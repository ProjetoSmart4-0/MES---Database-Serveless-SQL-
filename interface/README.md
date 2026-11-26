# Interface Web — SMART 4.0 MES

Abra `index.html` com Live Server (porta 5500). A interface consome a API FastAPI, por padrão em `http://127.0.0.1:8000`.

O formulário permite selecionar bloco único/duplo/triplo, cor única para base e tampa e três cores de plaquinhas por caixinha. O número da OP é gerado pelo backend. O painel de estoque apresenta a capacidade fixa da máquina e não oferece baixa manual.

Em Codespaces, se necessário, defina no console do navegador:
`localStorage.setItem('smart40_mes_api_base', 'https://SUA-PORTA-8000.app.github.dev')`

No backend, inclua em `CORS_ORIGINS` a origem HTTPS exata da interface na porta 5500, sem barra final. A configuração está descrita no [guia de integração](../INTEGRACAO_GRUPO4.md).

Não publique credenciais nem arquivos `.env`.
