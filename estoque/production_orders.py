from datetime import datetime
from collections import Counter
from psycopg2.extras import RealDictCursor
from .db_connection import get_db_connection

BLOCK_SIZES = {"UNICO": 1, "DUPLO": 2, "TRIPLO": 3}
COLORS = {"PRETA", "VERMELHA", "BRANCA", "AMARELA", "VERDE", "AZUL"}
BASE_COLORS = {"PRETA", "VERMELHA"}
PLAQUE_LIMIT = 10


def _validate_order(block_type, base_color, boxes):
    if block_type not in BLOCK_SIZES:
        raise ValueError("Tipo de bloco inválido. Escolha único, duplo ou triplo.")
    if base_color not in BASE_COLORS:
        raise ValueError("A cor da base/tampa deve ser PRETA ou VERMELHA.")
    expected = BLOCK_SIZES[block_type]
    if len(boxes) != expected:
        raise ValueError(f"O bloco {block_type.lower()} exige exatamente {expected} caixinha(s).")
    usage = Counter()
    normalized = []
    for index, box in enumerate(boxes, start=1):
        colors = box.get("plaque_colors") or []
        if len(colors) != 3:
            raise ValueError(f"A caixinha {index} deve ter exatamente 3 cores de plaquinhas.")
        colors = [str(color).upper() for color in colors]
        if any(color not in COLORS for color in colors):
            raise ValueError(f"Cor de plaquinha inválida na caixinha {index}.")
        usage.update(colors)
        normalized.append({"box_number": index, "plaque_colors": colors})
    exhausted = [f"{color}: {count} (máximo {PLAQUE_LIMIT})" for color, count in usage.items() if count > PLAQUE_LIMIT]
    if exhausted:
        raise ValueError("O pedido excede a capacidade fixa de plaquinhas: " + "; ".join(exhausted))
    return normalized


def criar_ordem(block_type, base_color, boxes):
    boxes = _validate_order(block_type, base_color, boxes)
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT nextval('mes_order_number_seq') AS seq")
        seq = cur.fetchone()["seq"]
        order_number = f"OP-{datetime.now():%Y%m%d}-{seq:04d}"
        target_quantity = BLOCK_SIZES[block_type]
        cur.execute("""
            INSERT INTO production_orders
                (order_number, target_quantity, produced_quantity, defective_quantity,
                 status, block_type, base_color, lid_color, created_at, updated_at)
            VALUES (%s, %s, 0, 0, 'PENDING', %s, %s, %s, NOW(), NOW())
            RETURNING *;
        """, (order_number, target_quantity, block_type, base_color, base_color))
        order = dict(cur.fetchone())
        for box in boxes:
            cur.execute("""
                INSERT INTO order_boxes
                    (production_order_id, box_number, plaque_color_1, plaque_color_2, plaque_color_3)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, box_number, plaque_color_1, plaque_color_2, plaque_color_3;
            """, (order["id"], box["box_number"], *box["plaque_colors"]))
            box["id"] = cur.fetchone()["id"]
        conn.commit()
        order["boxes"] = [{"id": box["id"], "box_number": box["box_number"], "plaque_color_1": box["plaque_colors"][0], "plaque_color_2": box["plaque_colors"][1], "plaque_color_3": box["plaque_colors"][2]} for box in boxes]
        return order
    except Exception:
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        conn.close()


def listar_ordens():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT o.*,
                   COALESCE(json_agg(json_build_object(
                     'id', b.id, 'box_number', b.box_number,
                     'plaque_color_1', b.plaque_color_1,
                     'plaque_color_2', b.plaque_color_2,
                     'plaque_color_3', b.plaque_color_3
                   ) ORDER BY b.box_number) FILTER (WHERE b.id IS NOT NULL), '[]') AS boxes
            FROM production_orders o
            LEFT JOIN order_boxes b ON b.production_order_id = o.id
            GROUP BY o.id ORDER BY o.id DESC;
        """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close(); conn.close()


def buscar_ordem(order_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT o.*, COALESCE(json_agg(json_build_object(
              'id', b.id, 'box_number', b.box_number,
              'plaque_color_1', b.plaque_color_1,
              'plaque_color_2', b.plaque_color_2,
              'plaque_color_3', b.plaque_color_3
            ) ORDER BY b.box_number) FILTER (WHERE b.id IS NOT NULL), '[]') AS boxes
            FROM production_orders o LEFT JOIN order_boxes b ON b.production_order_id=o.id
            WHERE o.id=%s GROUP BY o.id;
        """, (order_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close(); conn.close()


def atualizar_ordem(order_id, dados):
    conn = get_db_connection(); cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        allowed = {"defective_quantity": "defective_quantity = %s", "status": "status = %s::order_status"}
        sets, values = [], []
        for key, value in dados.items():
            if value is None:
                raise ValueError(f"O campo {key} não pode ser nulo.")
            if key in allowed:
                sets.append(allowed[key]); values.append(value)
        if not sets:
            return None
        sets.append("updated_at=NOW()"); values.append(order_id)
        cur.execute(f"UPDATE production_orders SET {', '.join(sets)} WHERE id=%s RETURNING *", values)
        row = cur.fetchone(); conn.commit()
        return dict(row) if row else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()
