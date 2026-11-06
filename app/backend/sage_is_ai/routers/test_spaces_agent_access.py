"""A Space agent replies under the mentioning member's own model access (routers/spaces.py
`_may_use`; Alexander, 2026-11-03).

Before, the reply passed bypass_filter, so any member reached a model, and the tool-server
key behind it, that they could not chat with. Runs inside the image or the dev container:
    python3 -B -m unittest sage_is_ai.routers.test_spaces_agent_access
"""

import asyncio
import types
import unittest
from unittest import mock

from sage_is_ai.routers import spaces

MODEL = {"id": "lia-crm", "name": "Lia", "info": {"meta": {}, "params": {}}}
DENIED = mock.patch(
    "sage_is_ai.utils.models.check_model_access",
    side_effect=Exception("Model not found"),
)
ALLOWED = mock.patch("sage_is_ai.utils.models.check_model_access", return_value=None)


def mention(user):
    """One @mention of the agent by `user`; the pipeline and the completion are recorded."""
    state = types.SimpleNamespace(MODELS={"lia-crm": MODEL}, TOOL_SERVERS=[])
    request = types.SimpleNamespace(
        app=types.SimpleNamespace(state=state), state=types.SimpleNamespace()
    )
    message = types.SimpleNamespace(content="@lia hello", parent_id=None)
    completion = mock.AsyncMock(
        return_value={"choices": [{"message": {"content": ""}}]}
    )
    payload = mock.AsyncMock(
        side_effect=lambda request, form, user, metadata, model: (form, metadata, [])
    )
    with (
        mock.patch.object(spaces.sio, "emit", mock.AsyncMock()) as emit,
        mock.patch("sage_is_ai.utils.chat.generate_chat_completion", completion),
        mock.patch("sage_is_ai.utils.middleware.process_chat_payload", payload),
    ):
        asyncio.run(
            spaces.generate_agent_response(
                request,
                types.SimpleNamespace(id="s1"),
                message,
                {"model_id": "lia-crm"},
                user,
            )
        )
    return completion, payload, emit


class AgentAccess(unittest.TestCase):
    member = types.SimpleNamespace(id="u1", role="user")

    def test_a_member_without_access_gets_no_reply_and_no_tool_call(self):
        with DENIED:
            completion, payload, emit = mention(self.member)
        completion.assert_not_called()
        payload.assert_not_called()  # the pipeline can call tool servers
        emit.assert_not_called()  # not even the "thinking" indicator

    def test_a_member_with_access_gets_a_reply_under_their_own_access(self):
        with ALLOWED:
            completion, _, _ = mention(self.member)
        completion.assert_called_once()
        self.assertFalse(completion.call_args.kwargs.get("bypass_filter", False))

    def test_an_admin_passes_without_the_model_check(self):
        with DENIED as check:
            completion, _, _ = mention(types.SimpleNamespace(id="a1", role="admin"))
        check.assert_not_called()
        completion.assert_called_once()


if __name__ == "__main__":
    unittest.main()
