from db_connection import get_db_connection

def listar_estoque():
    '''Retorna o saldo físico e alertas de reabastecimento'''
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, item_name, category, quantity, reorder_point, updated_at FROM inventory_stock ORDER BY id;")
    estoque = cur.fetchall()
    cur.close()
    conn.close()
    return estoque

def debitar_materia_prima(item_name: str, quantidade: int = 1):
    '''Realiza a baixa automatica de máteria-prima no início da OP'''
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE inventory_stock 
        SET quantity = quantity - %s, updated_at = NOW() 
        WHERE item_name = %s AND quantity >= %s
        RETURNING id, item_name, quantity;
    """, (quantidade, item_name, quantidade))
    item_atualizado = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return item_atualizado

def creditar_produto_acabado(item_name: str = 'Caixa Expedição', quantidade: int = 1):
    """Entrada de produto acabado no setor de expedição após inspeção OK"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE inventory_stock 
        SET quantity = quantity + %s, updated_at = NOW() 
        WHERE item_name = %s
        RETURNING id, item_name, quantity;
    """, (quantidade, item_name))
    item_atualizado = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return item_atualizado