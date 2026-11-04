
from psycopg2.extras import RealDictCursor
from .db_connection import get_db_connection


# Debita um item, verificando se existe estoque suficiente.
# Esta função utiliza a conexão da operação principal.
def _debitar_item(cur, item_name, quantidade):

    cur.execute("""
        UPDATE inventory_stock
        SET current_quantity = current_quantity - %s
        WHERE item_name = %s
          AND current_quantity >= %s
        RETURNING id, item_name, current_quantity, unit;
    """, (quantidade, item_name, quantidade))

    item = cur.fetchone()

    if not item:
        raise ValueError(
            f"Estoque insuficiente ou item não encontrado: {item_name}"
        )

    return dict(item)


# 1. FABRICAR UMA PEÇA
def processar_peca(order_id, qr_code):

    conn = get_db_connection()

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Bloqueia a OP enquanto a peça está sendo processada.
        cur.execute("""
            SELECT id, target_quantity, produced_quantity, status
            FROM production_orders
            WHERE id = %s
            FOR UPDATE;
        """, (order_id,))

        ordem = cur.fetchone()

        if not ordem:
            raise ValueError("Ordem de produção não encontrada.")

        if ordem["status"] in ("COMPLETED", "CANCELLED", "FAILED"):
            raise ValueError("Esta ordem não pode receber novas peças.")

        produzidas = ordem["produced_quantity"] or 0

        if produzidas >= ordem["target_quantity"]:
            raise ValueError("A quantidade planejada já foi atingida.")

        # Debita 3 blocos de matéria-prima.
        bloco = _debitar_item(
            cur,
            "Bloco de Matéria-Prima",
            3
        )

        # Debita 1 tampa.
        tampa = _debitar_item(
            cur,
            "Tampa de Encaixe",
            1
        )

        # Registra a peça vinculada à OP.
        cur.execute("""
            INSERT INTO pieces_traceability (
                qr_code,
                production_order_id,
                status
            )
            VALUES (%s, %s, 'IN_PROCESSING')
            RETURNING id, qr_code, production_order_id, status;
        """, (qr_code, order_id))

        peca = dict(cur.fetchone())

        # Atualiza a quantidade produzida.
        nova_quantidade = produzidas + 1

        novo_status = (
            "COMPLETED"
            if nova_quantidade >= ordem["target_quantity"]
            else "IN_PROGRESS"
        )

        cur.execute("""
            UPDATE production_orders
            SET produced_quantity = %s,
                status = %s::order_status,
                updated_at = NOW()
            WHERE id = %s;
        """, (nova_quantidade, novo_status, order_id))

        # Confirma todas as operações juntas.
        conn.commit()

        return {
            "peca": peca,
            "bloco": bloco,
            "tampa": tampa,
            "produced_quantity": nova_quantidade,
            "order_status": novo_status
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


# 2. INSPECIONAR UMA PEÇA
def inspecionar_peca(qr_code, resultado):

    if resultado not in ("INSPECTED_OK", "INSPECTED_NOK"):
        raise ValueError("Resultado de inspeção inválido.")

    conn = get_db_connection()

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Bloqueia a peça durante a inspeção.
        cur.execute("""
            SELECT id, qr_code, production_order_id, status
            FROM pieces_traceability
            WHERE qr_code = %s
            FOR UPDATE;
        """, (qr_code,))

        peca = cur.fetchone()

        if not peca:
            raise ValueError("Peça não encontrada.")

        if peca["status"] != "IN_PROCESSING":
            raise ValueError(
                "A peça não está aguardando inspeção."
            )

        # Atualiza o status e a data da inspeção.
        cur.execute("""
            UPDATE pieces_traceability
            SET status = %s::piece_status,
                inspected_at = NOW()
            WHERE qr_code = %s
            RETURNING id, qr_code, production_order_id,
                      status, inspected_at;
        """, (resultado, qr_code))

        peca_atualizada = dict(cur.fetchone())

        # Se a peça foi reprovada, incrementa os defeitos da OP.
        if resultado == "INSPECTED_NOK":
            cur.execute("""
                UPDATE production_orders
                SET defective_quantity =
                    COALESCE(defective_quantity, 0) + 1,
                    updated_at = NOW()
                WHERE id = %s;
            """, (peca["production_order_id"],))

        conn.commit()

        return peca_atualizada

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


# 3. EMBALAR E EXPEDIR UMA PEÇA
def expedir_peca(qr_code):

    conn = get_db_connection()

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Bloqueia a peça para evitar expedição duplicada.
        cur.execute("""
            SELECT id, qr_code, production_order_id, status
            FROM pieces_traceability
            WHERE qr_code = %s
            FOR UPDATE;
        """, (qr_code,))

        peca = cur.fetchone()

        if not peca:
            raise ValueError("Peça não encontrada.")

        if peca["status"] != "INSPECTED_OK":
            raise ValueError(
                "Somente peças aprovadas podem ser expedidas."
            )

        # Debita uma caixa de expedição.
        caixa = _debitar_item(
            cur,
            "Caixa de Expedição",
            1
        )

        # Atualiza a situação da peça.
        cur.execute("""
            UPDATE pieces_traceability
            SET status = 'EXPEDITED'
            WHERE qr_code = %s
            RETURNING id, qr_code, production_order_id, status;
        """, (qr_code,))

        peca_atualizada = dict(cur.fetchone())

        conn.commit()

        return {
            "peca": peca_atualizada,
            "caixa": caixa
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()
