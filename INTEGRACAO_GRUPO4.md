# Integração do Grupo 4 com o MES

No ambiente local, use `http://127.0.0.1:8000` como URL base. A URL HTTPS pública do `mes-service` depende da escolha da hospedagem e da autorização para publicar. O Swagger fica em `/docs` e o contrato OpenAPI em `/openapi.json`.

## Rotas

Todos os caminhos da tabela têm o prefixo `/api/v1/mes`.

| Método | Caminho | Resposta e condições |
| --- | --- | --- |
| GET | `/health` | 200. Verifica se a API responde. A rota independe do Neon. |
| GET | `/inventory` | 200. Capacidade fixa de bases, tampas e plaquinhas. |
| GET | `/orders` | 200. Lista ordens por ID decrescente, incluindo `boxes`. |
| GET | `/orders/{order_id}` | 200 com a ordem e suas caixinhas. 404 se ausente. |
| POST | `/orders` | 201 com a ordem criada. 400 para violação das regras do pedido e 409 para conflito no número da ordem. |
| PATCH | `/orders/{order_id}` | 200 com a linha atualizada da ordem. Aceita `status` e/ou `defective_quantity`. 400 para corpo vazio ou campo nulo e 404 se a ordem estiver ausente. |
| POST | `/orders/{order_id}/pieces` | 201 com `peca`, `caixinha`, `produced_quantity`, `order_status` e `message` em `data`. Recebe `qr_code`. 400 para regra de processamento e 409 para QR duplicado. |
| GET | `/pieces` | 200 com peças resumidas. `limit` aceita 1–500 (padrão 100) e `order_id` é opcional. Limite fora do intervalo retorna 400. |
| GET | `/pieces/{qr_code}` | 200 com `peca`, `historico` e `historico_habilitado`, quando a estrutura de dados é compatível. 404 se a peça estiver ausente. |
| PATCH | `/pieces/{qr_code}/inspect` | 200 com a peça atualizada. Recebe `status` igual a `INSPECTED_OK` ou `INSPECTED_NOK`. 400 se a peça estiver ausente ou indisponível para inspeção. |
| PATCH | `/pieces/{qr_code}/expedite` | 200 com a peça expedida. Sem corpo. 400 se a peça estiver ausente ou sem aprovação. |
| POST | `/pieces/{qr_code}/events` | Rota declarada. A gravação permanece pendente de validação do esquema e dos valores aceitos no Neon. |
| GET | `/oee` | Cálculo implementado. 200 quando há dados e configuração suficientes. 422 para parâmetros ou dados insuficientes identificados pelo cálculo. |
| GET | `/events` | 200 com `text/event-stream`. Consulta periódica do estado das ordens. |

Erros de validação de tipos, campos obrigatórios e formatos identificados pelo FastAPI retornam 422. O código do MES ainda não aplica autenticação às rotas.

### Mudanças de contrato desde a API anterior

- A rota `POST /api/v1/mes/inventory/debit` foi retirada com a adoção da capacidade fixa. Em `GET /inventory`, as quantidades usam `current_quantity` e `min_quantity`, e a resposta indica `fixed: true`.
- A criação de ordens recebe `block_type`, `base_color` e `boxes`. O MES gera `order_number` e deriva `target_quantity` do tipo de bloco.
- O processamento das caixinhas atualiza `produced_quantity` e o andamento da ordem. A atualização direta aceita `status` e `defective_quantity`.

## Exemplos JSON

Os valores ilustram o contrato. Os exemplos de ordens e peças usam identificadores fictícios.

**Saúde da API** — `GET /api/v1/mes/health`

```json
{"status":"success","service":"SMART 4.0 MES"}
```

**Criação de ordem** — corpo de `POST /api/v1/mes/orders`

```json
{
  "block_type": "UNICO",
  "base_color": "PRETA",
  "boxes": [{"plaque_colors": ["VERMELHA", "BRANCA", "AZUL"]}]
}
```

`UNICO`, `DUPLO` e `TRIPLO` exigem respectivamente uma, duas e três caixinhas, cada uma com três plaquinhas. A tampa tem a cor da base. A criação retorna 201, com `status`, `message` e `data`. O objeto `data` inclui a ordem e as caixinhas. Em ordens do banco, podem aparecer campos adicionais da tabela.

**Consulta de ordem** — resposta de `GET /api/v1/mes/orders/42`

```json
{
  "status": "success",
  "data": {
    "id": 42,
    "order_number": "OP-20261125-0042",
    "status": "PENDING",
    "block_type": "UNICO",
    "base_color": "PRETA",
    "lid_color": "PRETA",
    "target_quantity": 1,
    "produced_quantity": 0,
    "defective_quantity": 0,
    "created_at": "2026-11-25T12:00:00+00:00",
    "updated_at": "2026-11-25T12:00:00+00:00",
    "boxes": [
      {"id": 100, "box_number": 1, "plaque_color_1": "VERMELHA", "plaque_color_2": "BRANCA", "plaque_color_3": "AZUL"}
    ]
  }
}
```

Na listagem, `data` é um array desses objetos. Na atualização, a resposta traz os campos da ordem sem a agregação de `boxes`.

**Atualização de ordem** — corpo de `PATCH /api/v1/mes/orders/42`

```json
{"status":"IN_PROGRESS","defective_quantity":0}
```

Os status aceitos na atualização são `PENDING`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` e `FAILED`.

**Processamento e inspeção de peça** — corpos de `POST /api/v1/mes/orders/42/pieces` e `PATCH /api/v1/mes/pieces/QR-EXEMPLO/inspect`, respectivamente

```json
{"qr_code":"QR-EXEMPLO"}
```

```json
{"status":"INSPECTED_OK"}
```

**OEE** — `GET /api/v1/mes/oee?inicio=2026-11-25T12:00:00Z&fim=2026-11-25T13:00:00Z&ppm=2`

`inicio` e `fim` precisam de fuso horário e a janela deve ser maior que zero e de até 31 dias. `ppm` é a produção teórica em peças por minuto e pode vir da configuração do serviço. O cálculo usa estados da máquina em `telemetry_logs` e inspeções em `pieces_traceability`.

Exemplo de resposta HTTP 422 quando falta telemetria para a janela

```json
{"detail":"Sem telemetria para calcular disponibilidade no período."}
```

Exemplo de resposta HTTP 200 com valores ilustrativos. Os indicadores usam a escala de 0 a 100.

```json
{
  "status": "success",
  "data": {
    "inicio": "2026-11-25T12:00:00+00:00",
    "fim": "2026-11-25T13:00:00+00:00",
    "ppm_teorico": 2.0,
    "tempo_planejado_segundos": 3600.0,
    "tempo_operacao_segundos": 2700.0,
    "pecas_processadas": 60,
    "pecas_aprovadas": 54,
    "disponibilidade_percentual": 75.0,
    "desempenho_percentual": 66.67,
    "qualidade_percentual": 90.0,
    "oee_percentual": 45.0,
    "observacao": "Qualidade baseada em peças inspecionadas; valide se EXPEDITED mantém a aprovação."
  }
}
```

## SSE para acompanhar ordens

URL local `http://127.0.0.1:8000/api/v1/mes/events`. No navegador, use `EventSource` e escute os eventos nomeados `mes.orders.snapshot` e `mes.orders.unavailable`. Leia o JSON com `JSON.parse(event.data)` e feche a assinatura com `source.close()` ao sair da tela.

```text
retry: 5000
: connected

event: mes.orders.snapshot
data: {"type":"mes.orders.snapshot","timestamp":"2026-11-25T12:00:00+00:00","data":{"orders":[{"id":42,"status":"PENDING","target_quantity":1,"produced_quantity":0,"defective_quantity":0}]}}

```

- `mes.orders.snapshot` traz o estado observado na primeira leitura bem-sucedida, quando os campos publicados mudam e quando a consulta volta a funcionar. Substitua a lista anterior pela nova. Sem ordens, `data.orders` é `[]`.
- `mes.orders.unavailable` sinaliza uma falha de leitura sem expor detalhes do banco. O fluxo permanece aberto e tenta consultar de novo.

```json
{"type":"mes.orders.unavailable","timestamp":"2026-11-25T12:00:10+00:00","data":{"code":"ORDERS_UNAVAILABLE"}}
```

O timestamp UTC é o momento de emissão. O processo consulta as 50 ordens de maior ID a cada 10 segundos enquanto há clientes conectados e compartilha a leitura entre eles. Réplicas têm consultas independentes. Sem mudança, o servidor envia o comentário SSE `: keepalive`. Ao reconectar, o cliente recebe o estado disponível e deve substituir a lista anterior. Mudanças intermediárias entre consultas podem passar despercebidas. Para ordens fora das 50 mais recentes por ID, consulte as rotas de ordens. O fluxo publica somente os campos de ordem do exemplo, sem histórico, QR codes ou indicadores OEE.

## Configuração e deploy

| Variável | Uso |
| --- | --- |
| `HOST` | Bind do servidor. Padrão local `127.0.0.1`. A imagem Docker usa `0.0.0.0`. |
| `PORT` | Porta HTTP. Padrão `8000`. O healthcheck da imagem usa esta variável. |
| `CORS_ORIGINS` | Origens explícitas separadas por vírgula, com esquema e porta quando aplicável, sem barra final. Por padrão, permite `http://127.0.0.1:5500` e `http://localhost:5500`. Para Codespaces ou para o Grupo 4, informe a origem exata. |
| `DATABASE_URL` | Conexão PostgreSQL para as rotas que consultam ou gravam dados. Injete pelo gerenciador de segredos do ambiente. |
| `OEE_THEORETICAL_PPM` | Produção teórica, maior que zero. Necessária quando a requisição omite `ppm`. |
| `OEE_TELEMETRY_TIME`, `OEE_TELEMETRY_STATE`, `OEE_RUNNING_VALUE` | Colunas de tempo e estado e valor de máquina em operação. Padrões `recorded_at`, `machine_state` e `RUNNING`. |
| `OEE_MACHINE_COLUMN`, `OEE_MACHINE_VALUE` | Filtro opcional de máquina na telemetria. |

Configuração do processo tem precedência sobre o `.env` local. Use `.env.example` como modelo. O `JWT_SECRET` é de responsabilidade do Grupo 5 e ainda não é consumido no MES.

Na raiz do projeto, instale as dependências e execute o serviço localmente.

```sh
python -m pip install -r requirements.txt
python -m estoque
```

Em um ambiente autorizado com Docker, gere a imagem e injete as variáveis de execução. O arquivo `.env` abaixo é local e usado somente em execução.

```sh
docker build -t mes-service .
docker run --rm --env-file .env -e HOST=0.0.0.0 -p 8000:8000 mes-service
```

Se usar uma porta diferente, ajuste o mapeamento do contêiner. A imagem inclui um healthcheck HTTP que verifica o processo. Para hospedar sem contêiner, instale o mesmo arquivo de dependências, defina `HOST=0.0.0.0` e use `python -m estoque` com a porta fornecida pela plataforma. Configure a verificação da plataforma em `/api/v1/mes/health`. O proxy HTTPS deve manter a resposta SSE aberta, desabilitar o buffering nessa rota e usar um timeout de leitura que acomode o polling e o tempo de conexão ao banco, por exemplo 60 segundos. A inicialização do serviço não roda migrações.

## Pendências de integração

- Definir hospedagem, estabelecer controle de acesso com o Grupo 5 e publicar mediante autorização. CORS controla origens no navegador, enquanto o acesso às rotas precisa de proteção no ambiente de publicação ou na aplicação.
- Validar o esquema existente do Neon antes de qualquer migração ou mudança no histórico. A consulta de histórico espera colunas diferentes das definidas em `01_piece_events.sql`. Confirmar com o Grupo 1 o acesso via configuração segura.
- Confirmar o esquema, estados e cobertura da telemetria para calcular OEE, além do significado de `EXPEDITED` para qualidade. A interface atual ainda tem uma tela de espera para o indicador.
- Confirmar o consumo de ordens, OEE e SSE com o Grupo 4. Os contratos dos demais grupos dependem da disponibilidade de seus repositórios ou especificações.
