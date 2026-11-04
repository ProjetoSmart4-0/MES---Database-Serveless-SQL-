
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal

from psycopg2.errors import UniqueViolation

from .estoque import (
    listar_estoque,
    debitar_materia_prima,
    creditar_produto_acabado
)

from .production_orders import (
    criar_ordem,
    listar_ordens,
    buscar_ordem,
    atualizar_ordem
)

from .piece_processing import (
    processar_peca,
    inspecionar_peca,
    expedir_peca
)


app = FastAPI(title="MES - Módulo de Gestão de Estoque")


# Configuração de acesso do Front-End
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# MODELOS DE DADOS

class ProductionOrderCreate(BaseModel):
    order_number: str
    target_quantity: int = Field(gt=0)


class ProductionOrderUpdate(BaseModel):
    produced_quantity: int | None = Field(default=None, ge=0)
    defective_quantity: int | None = Field(default=None, ge=0)
    status: Literal[
        "PENDING",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
        "FAILED"
    ] | None = None


class PieceProcessRequest(BaseModel):
    qr_code: str = Field(min_length=1)


class PieceInspectionRequest(BaseModel):
    status: Literal["INSPECTED_OK", "INSPECTED_NOK"]


# ESTOQUE

@app.get("/api/v1/mes/inventory")
def get_inventory():
    items = listar_estoque()

    return {
        "status": "success",
        "data": items
    }


@app.post("/api/v1/mes/inventory/debit")
def debit_stock(item_name: str, quantity: int = 1):

    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="A quantidade deve ser maior que zero."
        )

    res = debitar_materia_prima(item_name, quantity)

    if not res:
        raise HTTPException(
            status_code=400,
            detail="Insumo indisponível ou quantidade insuficiente."
        )

    return {
        "status": "success",
        "message": "Baixa realizada com sucesso.",
        "data": res
    }


# ORDENS DE PRODUÇÃO

@app.post("/api/v1/mes/orders", status_code=201)
def post_order(order: ProductionOrderCreate):

    try:
        resultado = criar_ordem(
            order.order_number,
            order.target_quantity
        )

        return {
            "status": "success",
            "message": "Ordem de produção criada!",
            "data": resultado
        }

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma ordem com esse número."
        )


@app.get("/api/v1/mes/orders")
def get_orders():

    ordens = listar_ordens()

    return {
        "status": "success",
        "data": ordens
    }


@app.get("/api/v1/mes/orders/{order_id}")
def get_order(order_id: int):

    ordem = buscar_ordem(order_id)

    if not ordem:
        raise HTTPException(
            status_code=404,
            detail="Ordem de produção não encontrada."
        )

    return {
        "status": "success",
        "data": ordem
    }


@app.patch("/api/v1/mes/orders/{order_id}")
def patch_order(order_id: int, dados: ProductionOrderUpdate):

    atualizacoes = dados.dict(exclude_unset=True)

    if not atualizacoes:
        raise HTTPException(
            status_code=400,
            detail="Nenhum dado foi enviado para atualização."
        )

    ordem = atualizar_ordem(order_id, atualizacoes)

    if not ordem:
        raise HTTPException(
            status_code=404,
            detail="Ordem de produção não encontrada."
        )

    return {
        "status": "success",
        "message": "Ordem atualizada!",
        "data": ordem
    }


# PROCESSAMENTO DE PEÇAS

@app.post("/api/v1/mes/orders/{order_id}/pieces", status_code=201)
def post_piece(order_id: int, dados: PieceProcessRequest):

    try:
        resultado = processar_peca(
            order_id,
            dados.qr_code
        )

        return {
            "status": "success",
            "message": "Peça processada e insumos debitados!",
            "data": resultado
        }

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Este QR Code já está cadastrado."
        )

    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )


# INSPEÇÃO DE PEÇAS

@app.patch("/api/v1/mes/pieces/{qr_code}/inspect")
def patch_inspection(qr_code: str, dados: PieceInspectionRequest):

    try:
        resultado = inspecionar_peca(
            qr_code,
            dados.status
        )

        return {
            "status": "success",
            "message": "Inspeção registrada!",
            "data": resultado
        }

    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )


# EXPEDIÇÃO DE PEÇAS

@app.patch("/api/v1/mes/pieces/{qr_code}/expedite")
def patch_expedition(qr_code: str):

    try:
        resultado = expedir_peca(qr_code)

        return {
            "status": "success",
            "message": "Peça embalada e expedida!",
            "data": resultado
        }

    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )
