
from psycopg2.extras import RealDictCursor
from .db_connection import get_db_connection


# Consultar todos os itens do estoque
def listar_estoque():
    conn = get_db_connection()

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                id,
                item_name,
                category,
                current_quantity,
                min_quantity,
                unit
            FROM inventory_stock
            ORDER BY id;
        """)

        return [dict(item) for item in cur.fetchall()]

    finally:
        cur.close()
        conn.close()


# Debitar uma quantidade de um item do estoque
def debitar_materia_prima(item_name: str, quantidade: int = 1):
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    conn = get_db_connection()

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE inventory_stock
            SET current_quantity = current_quantity - %s
            WHERE item_name = %s
              AND current_quantity >= %s
            RETURNING id, item_name, current_quantity, unit;
        """, (quantidade, item_name, quantidade))

        item = cur.fetchone()

        if not item:
            conn.rollback()
            return None

        conn.commit()
        return dict(item)

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


# Creditar uma quantidade de um item no estoque
def creditar_produto_acabado(
    item_name: str = "Caixa de Expedição",
    quantidade: int = 1
):
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    conn = get_db_connection()

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE inventory_stock
            SET current_quantity = current_quantity + %s
            WHERE item_name = %s
            RETURNING id, item_name, current_quantity, unit;
        """, (quantidade, item_name))

        item = cur.fetchone()

        if not item:
            conn.rollback()
            return None

        conn.commit()
        return dict(item)

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()
