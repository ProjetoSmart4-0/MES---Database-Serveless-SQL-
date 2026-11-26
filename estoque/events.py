import asyncio
import json
from contextlib import closing
from datetime import datetime, timezone
from time import monotonic

import psycopg2
from fastapi import Request
from starlette.concurrency import run_in_threadpool

from .db_connection import get_db_connection

POLL_INTERVAL = 10
ORDER_LIMIT = 50


def read_orders():
    with closing(get_db_connection()) as conn:
        conn.set_session(readonly=True)
        with conn, conn.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '5s'")
            cursor.execute(
                """
                SELECT id, status, target_quantity, produced_quantity, defective_quantity
                FROM production_orders
                ORDER BY id DESC
                LIMIT %s
                """,
                (ORDER_LIMIT,),
            )
            return [dict(row) for row in cursor.fetchall()]


class OrderPoll:
    """Compartilha uma leitura por intervalo entre os clientes do processo."""

    def __init__(self):
        self.lock = asyncio.Lock()
        self.next_poll = 0.0
        self.orders = None

    async def read(self):
        async with self.lock:
            if monotonic() >= self.next_poll:
                try:
                    self.orders = await run_in_threadpool(read_orders)
                except (psycopg2.Error, RuntimeError):
                    self.orders = None
                self.next_poll = monotonic() + POLL_INTERVAL
            return self.orders


order_poll = OrderPoll()


def format_event(event_type, data):
    payload = {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    return f"event: {event_type}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


async def stream_order_events(request: Request):
    previous = None
    unavailable = False
    yield "retry: 5000\n: connected\n\n"
    while not await request.is_disconnected():
        orders = await order_poll.read()
        if await request.is_disconnected():
            break

        if orders is None and not unavailable:
            yield format_event("mes.orders.unavailable", {"code": "ORDERS_UNAVAILABLE"})
        elif orders is not None and (unavailable or orders != previous):
            yield format_event("mes.orders.snapshot", {"orders": orders})
        else:
            yield ": keepalive\n\n"

        previous = orders
        unavailable = orders is None
        await asyncio.sleep(POLL_INTERVAL)
