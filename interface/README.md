# SMART 4.0 — Interface inicial do MES

Interface web inicial em HTML, CSS e JavaScript puro para o módulo MES do Grupo 3.

## O que já funciona
- Dashboard com resumo do estoque.
- Consulta `GET /api/v1/mes/inventory`.
- Tabela com itens, quantidades, ponto de reposição e status calculado na interface.
- Baixa de material com `POST /api/v1/mes/inventory/debit`.
- Navegação para áreas reservadas de Ordens de Produção e OEE.

## 1. Iniciar o backend FastAPI

Na pasta do backend, instalem as dependências necessárias (ajustem conforme o projeto):

```bash
pip install fastapi uvicorn psycopg2-binary
```

Iniciem o servidor usando o módulo Python correto. Exemplo, se `app.py` estiver dentro da pasta `estoque` e o pacote estiver organizado para isso:

```bash
uvicorn estoque.app:app --reload
```

Se a estrutura de pastas/imports de vocês for diferente, o comando muda. O backend precisa estar acessível em `http://127.0.0.1:8000`.

## 2. Habilitar CORS no FastAPI

Como a interface e a API podem rodar em endereços/portas diferentes, o navegador pode bloquear as requisições. No arquivo que cria `app = FastAPI(...)`, adicionem:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Para desenvolvimento, isso libera o Live Server nessas origens. Em produção, usem somente os domínios autorizados do projeto.

## 3. Abrir a interface

A forma mais simples é usar a extensão **Live Server** no VS Code:
1. Abram esta pasta no VS Code.
2. Instalem a extensão Live Server, se ainda não tiverem.
3. Cliquem com o botão direito em `index.html`.
4. Escolham **Open with Live Server**.

A página normalmente abrirá em `http://127.0.0.1:5500`.

## 4. Como a interface conversa com a API

Ao carregar, `app.js` faz:

```javascript
fetch("http://127.0.0.1:8000/api/v1/mes/inventory")
```

A interface espera uma resposta parecida com:

```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "item_name": "Bloco Bruto",
      "category": "RAW_MATERIAL",
      "quantity": 50,
      "reorder_point": 10,
      "updated_at": "2026-11-03T12:00:00Z"
    }
  ]
}
```

Para registrar a baixa, o JavaScript envia um `POST` para:

```text
/api/v1/mes/inventory/debit?item_name=Bloco%20Bruto&quantity=1
```

Isso corresponde à assinatura atual da rota no `estoque/app.py`, que recebe `item_name` e `quantity` como parâmetros de consulta.

## 5. Se o backend estiver hospedado

Editem `app.js` e troquem:

```javascript
const DEFAULT_API_BASE = "http://127.0.0.1:8000";
```

pelo endereço público do backend, sem colocar `/api/v1/...` no final.

## Observações importantes
- A baixa altera o banco real. Façam testes com quantidades pequenas e dados autorizados.
- O OEE e as Ordens de Produção são espaços reservados; ainda não estão conectados.
- Não coloquem senha ou URL secreta do Neon no JavaScript. A credencial do banco deve ficar somente no backend, em variável de ambiente.
- O código atual de vocês usa `psycopg2`; confirmem que a dependência está instalada no ambiente do servidor.
