
from psycopg2.extras import RealDictCursor
from .db_connection import get_db_connection


# Criar uma nova Ordem de Produção, registra uma OP no banco, iniciando as quantidades em zero e o status como PENDING
def criar_ordem(order_number, target_quantity):
    conn = get_db_connection()

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO production_orders (
                order_number,
                target_quantity,
                produced_quantity,
                defective_quantity,
                status,
                created_at,
                updated_at
            )
            VALUES (%s, %s, 0, 0, 'PENDING', NOW(), NOW())
            RETURNING *;
        """, (order_number, target_quantity))

        ordem = cur.fetchone()
        conn.commit()

        return dict(ordem)

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


# Listar todas as Ordens de Produção, busca todas as OPs cadastradas 
def listar_ordens():
    conn = get_db_connection()

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM production_orders
            ORDER BY id DESC;
        """)

        ordens = cur.fetchall()

        return [dict(ordem) for ordem in ordens]

    finally:
        cur.close()
        conn.close()


# Consultar uma Ordem de Produção pelo ID
def buscar_ordem(order_id):
    conn = get_db_connection()

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM production_orders
            WHERE id = %s;
        """, (order_id,))

        ordem = cur.fetchone()

        return dict(ordem) if ordem else None

    finally:
        cur.close()
        conn.close()


# Atualizar uma Ordem de Produção
def atualizar_ordem(order_id, dados):
    conn = get_db_connection()

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        campos = {
            "produced_quantity": "produced_quantity = %s",
            "defective_quantity": "defective_quantity = %s",
            "status": "status = %s::order_status"
        }

        atualizacoes = []
        valores = []

        for campo, valor in dados.items():
            if campo in campos:
                atualizacoes.append(campos[campo])
                valores.append(valor)

        if not atualizacoes:
            return None

        atualizacoes.append("updated_at = NOW()")
        valores.append(order_id)

        consulta = f"""
            UPDATE production_orders
            SET {', '.join(atualizacoes)}
            WHERE id = %s
            RETURNING *;
        """

        cur.execute(consulta, valores)

        ordem = cur.fetchone()
        conn.commit()

        return dict(ordem) if ordem else None

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()
