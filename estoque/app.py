import os
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from psycopg2.errors import UniqueViolation

from .estoque import listar_estoque
from .production_orders import criar_ordem, listar_ordens, buscar_ordem, atualizar_ordem
from .piece_processing import processar_peca, inspecionar_peca, expedir_peca
from .events import stream_order_events


def cors_origins():
    configured = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500")
    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    for origin in origins:
        try:
            parts = urlsplit(origin)
            if (
                parts.scheme in ("http", "https")
                and parts.hostname
                and parts.username is None
                and (parts.port or not parts.netloc.endswith(":"))
                and origin == f"{parts.scheme}://{parts.netloc}"
                and "*" not in origin
                and not any(char.isspace() for char in origin)
            ):
                continue
        except ValueError:
            pass
        raise ValueError("CORS_ORIGINS deve conter origens HTTP(S) explícitas, separadas por vírgula.")
    return origins


app = FastAPI(title="SMART 4.0 - MES | Grupo 3")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

class BoxCustomization(BaseModel):
    plaque_colors: list[Literal["PRETA", "VERMELHA", "BRANCA", "AMARELA", "VERDE", "AZUL"]]

class ProductionOrderCreate(BaseModel):
    block_type: Literal["UNICO", "DUPLO", "TRIPLO"]
    base_color: Literal["PRETA", "VERMELHA"]
    boxes: list[BoxCustomization]

class ProductionOrderUpdate(BaseModel):
    defective_quantity: int | None = Field(default=None, ge=0)
    status: Literal["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED", "FAILED"] | None = None

class PieceProcessRequest(BaseModel):
    qr_code: str = Field(min_length=1, max_length=200)

class PieceInspectionRequest(BaseModel):
    status: Literal["INSPECTED_OK", "INSPECTED_NOK"]

@app.get("/api/v1/mes/health")
def health():
    return {"status": "success", "service": "SMART 4.0 MES"}

@app.get(
    "/api/v1/mes/events",
    response_class=StreamingResponse,
    responses={200: {"description": "Fluxo SSE de ordens", "content": {"text/event-stream": {}}}},
)
async def get_events(request: Request):
    return StreamingResponse(
        stream_order_events(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )

@app.get("/api/v1/mes/inventory")
def get_inventory():
    return {"status": "success", "data": listar_estoque(), "fixed": True,
            "message": "Capacidade fixa da máquina; os valores não são debitados nem alterados pelo MES."}

@app.post("/api/v1/mes/orders", status_code=201)
def post_order(order: ProductionOrderCreate):
    try:
        result = criar_ordem(order.block_type, order.base_color, [box.model_dump() if hasattr(box, "model_dump") else box.dict() for box in order.boxes])
        return {"status": "success", "message": "Pedido convertido em ordem de produção.", "data": result}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="Conflito ao gerar o número da ordem. Tente novamente.")

@app.get("/api/v1/mes/orders")
def get_orders():
    return {"status": "success", "data": listar_ordens()}

@app.get("/api/v1/mes/orders/{order_id}")
def get_order(order_id: int):
    order = buscar_ordem(order_id)
    if not order: raise HTTPException(status_code=404, detail="Ordem de produção não encontrada.")
    return {"status": "success", "data": order}

@app.patch("/api/v1/mes/orders/{order_id}")
def patch_order(order_id: int, data: ProductionOrderUpdate):
    updates = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data.dict(exclude_unset=True)
    if not updates: raise HTTPException(status_code=400, detail="Nenhum dado enviado para atualização.")
    try:
        order = atualizar_ordem(order_id, updates)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    if not order: raise HTTPException(status_code=404, detail="Ordem de produção não encontrada.")
    return {"status": "success", "data": order}

@app.post("/api/v1/mes/orders/{order_id}/pieces", status_code=201)
def post_piece(order_id: int, data: PieceProcessRequest):
    try:
        return {"status": "success", "message": "Caixinha registrada no processamento.", "data": processar_peca(order_id, data.qr_code)}
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="Este QR Code já está cadastrado.")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

@app.patch("/api/v1/mes/pieces/{qr_code}/inspect")
def patch_inspection(qr_code: str, data: PieceInspectionRequest):
    try: return {"status": "success", "data": inspecionar_peca(qr_code, data.status)}
    except ValueError as error: raise HTTPException(status_code=400, detail=str(error))

@app.patch("/api/v1/mes/pieces/{qr_code}/expedite")
def patch_expedition(qr_code: str):
    try: return {"status": "success", "data": expedir_peca(qr_code)}
    except ValueError as error: raise HTTPException(status_code=400, detail=str(error))


# PARTE 6 - RASTREABILIDADE
from datetime import datetime
from .rastreamento import listar_pecas, consultar_peca, registrar_evento
from .oee import calcular_oee

class PieceEventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=50)
    details: str | None = Field(default=None, max_length=1000)

@app.get('/api/v1/mes/pieces')
def get_pieces(limit: int = 100, order_id: int | None = None):
    if not 1 <= limit <= 500:
        raise HTTPException(400, 'limit deve ser entre 1 e 500')
    return {'status': 'success', 'data': listar_pecas(limit, order_id)}

@app.get('/api/v1/mes/pieces/{qr_code}')
def get_piece(qr_code: str):
    resultado = consultar_peca(qr_code)
    if not resultado:
        raise HTTPException(404, 'Peça não encontrada')
    return {'status': 'success', 'data': resultado}

@app.post('/api/v1/mes/pieces/{qr_code}/events', status_code=201)
def post_piece_event(qr_code: str, body: PieceEventCreate):
    try:
        resultado = registrar_evento(qr_code, body.event_type, body.details)
    except Exception as erro:
        # Sem a migração, a tabela de eventos não existe.
        if getattr(erro, 'pgcode', None) == '42P01':
            raise HTTPException(503, 'Execute primeiro a migração 01_piece_events.sql')
        raise
    if not resultado:
        raise HTTPException(404, 'Peça não encontrada')
    return {'status': 'success', 'data': resultado}

# PARTE 7 - OEE
@app.get('/api/v1/mes/oee')
def get_oee(inicio: datetime, fim: datetime, ppm: float | None = None):
    try:
        return {'status': 'success', 'data': calcular_oee(inicio, fim, ppm)}
    except ValueError as erro:
        raise HTTPException(422, str(erro))
