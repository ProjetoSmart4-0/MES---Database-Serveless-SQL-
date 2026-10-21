from fastapi import FastAPI, HTTPException
from estoque import listar_estoque, debitar_materia_prima, creditar_produto_acabado

app = FastAPI(title="MES - Módulo de Gestão de Estoque")

@app.get("/api/v1/mes/inventory")
def get_inventory():
    """Endpoint para consultar o saldo do estoque (consumido pelo Front-End e Gestor)."""
    items = listar_estoque()
    return {"status": "success", "data": items}

@app.post("/api/v1/mes/inventory/debit")
def debit_stock(item_name: str, quantity: int = 1):
    """Debita insumos ao iniciar uma ordem de produção."""
    res = debitar_materia_prima(item_name, quantity)
    if not res:
        raise HTTPException(status_code=400, detail="Insumo indisponível ou quantidade insuficiente no estoque.")
    return {"status": "success", "message": "Baixa realizada com sucesso", "data": res}