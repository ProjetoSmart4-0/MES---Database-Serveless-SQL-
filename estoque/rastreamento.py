
"""Parte 6: consultas e histórico individual por QR Code."""

from .db_connection import get_db_connection


def listar_pecas(limit=100, order_id=None):
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, qr_code, production_order_id, status
            FROM pieces_traceability
            WHERE (%s::integer IS NULL OR production_order_id = %s)
            ORDER BY id DESC
            LIMIT %s
            """,
            (order_id, order_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]


def consultar_peca(qr_code):
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM pieces_traceability WHERE qr_code = %s",
            (qr_code,),
        )
        peca = cur.fetchone()

        if not peca:
            return None

        cur.execute(
            "SELECT to_regclass('public.piece_events') AS tabela"
        )
        existe = cur.fetchone()["tabela"] is not None

        eventos = []

        if existe:
            cur.execute(
                """
                SELECT
                    id,
                    previous_status,
                    new_status,
                    event_description AS details,
                    event_timestamp AS occurred_at,
                    station_id
                FROM piece_events
                WHERE piece_id = %s
                ORDER BY event_timestamp, id
                """,
                (peca["id"],),
            )
            eventos = [dict(e) for e in cur.fetchall()]

        return {
            "peca": dict(peca),
            "historico": eventos,
            "historico_habilitado": existe,
        }


def registrar_evento(qr_code, tipo, detalhes=None):
    """Registra um evento adicional sem alterar o estoque."""

    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, status
            FROM pieces_traceability
            WHERE qr_code = %s
            """,
            (qr_code,),
        )
        peca = cur.fetchone()

        if not peca:
            return None

        # Os valores permitidos pelo enum do banco ainda precisam
        # ser verificados antes de gravar um evento.
        raise ValueError(
            "Registro de eventos adicionais pendente de validação "
            "do enum e das restrições da tabela piece_events."
        )
