"""Tests for the mutable message:before_send gateway hook."""

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from gateway.config import Platform
from gateway.platforms.base import MessageEvent
from gateway.run import GatewayRunner
from gateway.session import SessionSource


def _source() -> SessionSource:
    return SessionSource(
        platform=Platform.TELEGRAM,
        user_id="user-1",
        chat_id="chat-1",
        user_name="Tester",
        chat_type="dm",
    )


def _event() -> MessageEvent:
    return MessageEvent(
        text="hello",
        message_id="msg-1",
        source=_source(),
    )


def _runner(results):
    runner = object.__new__(GatewayRunner)
    runner.hooks = SimpleNamespace(emit_collect=AsyncMock(return_value=results))
    return runner


class BeforeSendHookTests(unittest.IsolatedAsyncioTestCase):
    async def test_before_send_allow_keeps_original_response(self):
        runner = _runner([{"action": "allow"}])

        response = await runner._apply_before_send_hook(
            "original",
            event=_event(),
            source=_source(),
            session_id="session-1",
            session_key="telegram:chat-1",
            agent_result={"api_calls": 1},
        )

        self.assertEqual(response, "original")
        runner.hooks.emit_collect.assert_awaited_once()
        event_name, context = runner.hooks.emit_collect.await_args.args
        self.assertEqual(event_name, "message:before_send")
        self.assertEqual(context["platform"], "telegram")
        self.assertEqual(context["chat_id"], "chat-1")
        self.assertEqual(context["user_id"], "user-1")
        self.assertEqual(context["message_id"], "msg-1")
        self.assertEqual(context["session_id"], "session-1")
        self.assertEqual(context["final_response"], "original")

    async def test_before_send_rewrite_replaces_response(self):
        runner = _runner([{"action": "rewrite", "text": "replacement"}])

        response = await runner._apply_before_send_hook("original", source=_source())

        self.assertEqual(response, "replacement")

    async def test_before_send_block_uses_safe_response_when_provided(self):
        runner = _runner([{"action": "block", "safe_response": "safe refusal"}])

        response = await runner._apply_before_send_hook("original", source=_source())

        self.assertEqual(response, "safe refusal")

    async def test_before_send_block_without_safe_response_suppresses_send(self):
        runner = _runner([{"action": "block"}])

        response = await runner._apply_before_send_hook("original", source=_source())

        self.assertIsNone(response)

    async def test_before_send_hook_registry_error_sends_original_response(self):
        runner = object.__new__(GatewayRunner)
        runner.hooks = SimpleNamespace(emit_collect=AsyncMock(side_effect=RuntimeError("boom")))

        response = await runner._apply_before_send_hook("original", source=_source())

        self.assertEqual(response, "original")


if __name__ == "__main__":
    unittest.main()
