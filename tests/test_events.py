import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from psycopg2 import OperationalError

from estoque import events
from estoque.app import app


class EventTests(unittest.IsolatedAsyncioTestCase):
    def test_reads_only_the_published_fields_in_a_read_only_session(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [{"id": 42, "status": "PENDING"}]
        with patch.object(events, "get_db_connection", return_value=connection):
            self.assertEqual(events.read_orders(), [{"id": 42, "status": "PENDING"}])

        connection.set_session.assert_called_once_with(readonly=True)
        connection.close.assert_called_once_with()
        timeout, select = cursor.execute.call_args_list
        self.assertTrue(timeout.args[0].startswith("SET LOCAL statement_timeout"))
        self.assertIn(
            "SELECT id, status, target_quantity, produced_quantity, defective_quantity",
            select.args[0],
        )
        self.assertEqual(select.args[1], (50,))

    async def test_poll_shares_read_across_clients(self):
        poll = events.OrderPoll()
        with patch.object(events, "read_orders", return_value=[]) as read:
            self.assertEqual(await asyncio.gather(poll.read(), poll.read()), [[], []])
            read.assert_called_once_with()

    async def test_database_failure_is_cached_without_exposing_details(self):
        poll = events.OrderPoll()
        with patch.object(events, "read_orders", side_effect=OperationalError("private")) as read:
            self.assertIsNone(await poll.read())
            self.assertIsNone(await poll.read())
            read.assert_called_once_with()

    async def test_stream_handles_failure_recovery_and_disconnect(self):
        request = Mock(is_disconnected=AsyncMock(return_value=False))
        poll = Mock(read=AsyncMock(side_effect=[None, None, [], [], [{"id": 42}]]))
        with patch.object(events, "order_poll", poll), patch.object(events, "POLL_INTERVAL", 0):
            stream = events.stream_order_events(request)
            self.assertEqual(await anext(stream), "retry: 5000\n: connected\n\n")
            error = await anext(stream)
            self.assertIn("event: mes.orders.unavailable\n", error)
            self.assertEqual(json.loads(error.splitlines()[1][6:])["data"], {"code": "ORDERS_UNAVAILABLE"})
            self.assertEqual(await anext(stream), ": keepalive\n\n")
            snapshot = await anext(stream)
            self.assertIn("event: mes.orders.snapshot\n", snapshot)
            self.assertEqual(json.loads(snapshot.splitlines()[1][6:])["data"], {"orders": []})
            self.assertEqual(await anext(stream), ": keepalive\n\n")
            self.assertIn('"orders":[{"id":42}]', await anext(stream))
            request.is_disconnected.return_value = True
            with self.assertRaises(StopAsyncIteration):
                await anext(stream)
            self.assertEqual(poll.read.await_count, 5)

    async def test_endpoint_sends_stream_headers_and_stops_on_disconnect(self):
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/mes/events",
            "root_path": "",
            "query_string": b"",
            "headers": [],
        }
        messages = []
        disconnected = asyncio.Event()

        async def receive():
            await disconnected.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)
            if b"event: mes.orders.snapshot" in message.get("body", b""):
                disconnected.set()

        with patch.object(events, "order_poll", Mock(read=AsyncMock(return_value=[]))):
            await asyncio.wait_for(app(scope, receive, send), timeout=2)

        self.assertEqual(messages[0]["status"], 200)
        headers = dict(messages[0]["headers"])
        self.assertEqual(headers[b"content-type"], b"text/event-stream; charset=utf-8")
        self.assertEqual(headers[b"x-accel-buffering"], b"no")
        self.assertEqual(headers[b"cache-control"], b"no-cache, no-transform")
        self.assertTrue(disconnected.is_set())
