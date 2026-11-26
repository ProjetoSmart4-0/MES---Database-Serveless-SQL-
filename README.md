# SMART 4.0 | MES Grupo 3

O MES registra ordens de produção de blocos personalizados, acompanha peças por QR code e informa a capacidade fixa da máquina. A API FastAPI usa PostgreSQL/Neon para ordens, rastreabilidade e cálculo de OEE. A interface web está em `interface/`.

## Execução local

Com Python 3.14 e um ambiente virtual ativo, execute na raiz do projeto.

```sh
python -m pip install -r requirements.txt
python -m estoque
```

A API inicia em `http://127.0.0.1:8000`, com Swagger em `/docs`. Use `.env.example` como modelo de configuração local. Injete `DATABASE_URL` por configuração segura para usar as rotas que dependem do banco. O healthcheck e a consulta de capacidade funcionam sem essa configuração.

Abra `interface/index.html` com Live Server na porta 5500. Para outras origens, configure `CORS_ORIGINS` no backend. O [guia da interface](interface/README.md) explica como apontar para outra URL da API.

## API

| Operação | Rota |
| --- | --- |
| Saúde do serviço | `GET /api/v1/mes/health` |
| Capacidade fixa | `GET /api/v1/mes/inventory` |
| Ordens de produção | `GET` e `POST /api/v1/mes/orders`, `GET` e `PATCH /api/v1/mes/orders/{order_id}` |
| Processamento, inspeção e expedição | Rotas de ordens e peças em `/api/v1/mes` |
| Rastreabilidade | `GET /api/v1/mes/pieces` e `GET /api/v1/mes/pieces/{qr_code}` |
| Indicadores de produção | `GET /api/v1/mes/oee` |
| SSE de ordens | `GET /api/v1/mes/events` |

O SSE envia o estado das 50 ordens de maior ID por consulta periódica somente leitura, com intervalo de 10 segundos. O [guia de integração do Grupo 4](INTEGRACAO_GRUPO4.md) traz a lista completa de rotas, exemplos JSON, o contrato SSE e as mudanças de contrato em relação à API anterior.

## Verificação e deploy

```sh
python -m unittest discover -s tests -v
```

A configuração do serviço inclui `HOST`, `PORT` e `CORS_ORIGINS`. O Dockerfile usa `/api/v1/mes/health` para verificar a API. Consulte as [instruções de deploy e configuração](INTEGRACAO_GRUPO4.md#configuração-e-deploy).

A autenticação, a validação do esquema do histórico de peças e a confirmação da telemetria para OEE seguem como pendências. Os arquivos SQL estão em `services/mes-service/database/` e a inicialização do serviço não os executa.
