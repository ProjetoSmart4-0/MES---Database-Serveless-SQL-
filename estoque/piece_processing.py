from psycopg2.extras import RealDictCursor
from .db_connection import get_db_connection


def processar_peca(order_id, qr_code):
    """Registra uma caixinha da OP sem alterar a capacidade fixa da máquina."""
    conn = get_db_connection(); cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT id, order_number, target_quantity, produced_quantity, status, block_type
            FROM production_orders WHERE id=%s FOR UPDATE;
        """, (order_id,))
        order = cur.fetchone()
        if not order:
            raise ValueError("Ordem de produção não encontrada.")
        if order["status"] in ("COMPLETED", "CANCELLED", "FAILED"):
            raise ValueError("Esta ordem não pode receber novas caixinhas.")
        produced = order["produced_quantity"] or 0
        if produced >= order["target_quantity"]:
            raise ValueError("Todas as caixinhas deste bloco já foram processadas.")
        cur.execute("""
            SELECT b.* FROM order_boxes b
            WHERE b.production_order_id=%s
              AND NOT EXISTS (SELECT 1 FROM pieces_traceability p WHERE p.order_box_id=b.id)
            ORDER BY b.box_number LIMIT 1 FOR UPDATE;
        """, (order_id,))
        box = cur.fetchone()
        if not box:
            raise ValueError("Não há caixinha pendente configurada para esta OP. Confira a migration e o cadastro do pedido.")
        cur.execute("""
            INSERT INTO pieces_traceability (qr_code, production_order_id, order_box_id, status)
            VALUES (%s, %s, %s, 'IN_PROCESSING')
            RETURNING id, qr_code, production_order_id, order_box_id, status;
        """, (qr_code, order_id, box["id"]))
        piece = dict(cur.fetchone())
        new_count = produced + 1
        new_status = "COMPLETED" if new_count >= order["target_quantity"] else "IN_PROGRESS"
        cur.execute("""UPDATE production_orders SET produced_quantity=%s,
                     status=%s::order_status, updated_at=NOW() WHERE id=%s""", (new_count, new_status, order_id))
        conn.commit()
        return {"peca": piece, "caixinha": dict(box), "produced_quantity": new_count, "order_status": new_status,
                "message": "Caixinha registrada. A capacidade fixa da máquina não foi alterada."}
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()


def inspecionar_peca(qr_code, resultado):
    if resultado not in ("INSPECTED_OK", "INSPECTED_NOK"):
        raise ValueError("Resultado de inspeção inválido.")
    conn = get_db_connection(); cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT id, qr_code, production_order_id, status FROM pieces_traceability WHERE qr_code=%s FOR UPDATE", (qr_code,))
        piece = cur.fetchone()
        if not piece: raise ValueError("Caixinha não encontrada.")
        if piece["status"] != "IN_PROCESSING": raise ValueError("A caixinha não está aguardando inspeção.")
        cur.execute("""UPDATE pieces_traceability SET status=%s::piece_status, inspected_at=NOW()
                     WHERE qr_code=%s RETURNING id, qr_code, production_order_id, order_box_id, status, inspected_at""", (resultado, qr_code))
        updated = dict(cur.fetchone())
        if resultado == "INSPECTED_NOK":
            cur.execute("UPDATE production_orders SET defective_quantity=COALESCE(defective_quantity,0)+1, updated_at=NOW() WHERE id=%s", (piece["production_order_id"],))
        conn.commit(); return updated
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()


def expedir_peca(qr_code):
    """Marca expedição sem baixar componente: o MES não altera o estoque fixo."""
    conn = get_db_connection(); cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT id, qr_code, production_order_id, status FROM pieces_traceability WHERE qr_code=%s FOR UPDATE", (qr_code,))
        piece = cur.fetchone()
        if not piece: raise ValueError("Caixinha não encontrada.")
        if piece["status"] != "INSPECTED_OK": raise ValueError("Somente caixinhas aprovadas podem ser expedidas.")
        cur.execute("UPDATE pieces_traceability SET status='EXPEDITED' WHERE qr_code=%s RETURNING id, qr_code, production_order_id, order_box_id, status", (qr_code,))
        updated = dict(cur.fetchone()); conn.commit(); return updated
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()
