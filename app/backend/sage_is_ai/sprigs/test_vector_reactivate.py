"""A vector graft turns the vector client on, at boot and from the graft route (2026-11-02).

`vector` is a delivered overlay with no process, so neither the boot reconcile nor the
graft route re-pointed anything, and every restart left document search off until
someone ran `kb-reindex.py --vector-on`. Both now call `ensure_chromadb`. Runs inside the
image or the dev container with a throwaway key and database:
    python3 -B -m unittest sage_is_ai.sprigs.test_vector_reactivate
"""

import asyncio
import types
import unittest
from unittest import mock

from sage_is_ai.sprigs.supervisor import SprigSupervisor

APP = types.SimpleNamespace(state=types.SimpleNamespace())
VECTOR = types.SimpleNamespace(name="vector-chroma", capability="vector", process=None)


def supervisor(entries):
    """A supervisor with no I/O: state.json, the catalog and the graft are stand-ins."""
    sup = object.__new__(SprigSupervisor)
    sup.app, sup._deferred, sup._errors = APP, {}, {}
    sup.CATALOG = {
        "vector-chroma": {"capability": "vector"},
        "minilm": {"capability": "embedding"},
    }
    sup._read_state = lambda: entries
    sup.graft = mock.AsyncMock(return_value=VECTOR)
    return sup


class VectorReactivates(unittest.TestCase):
    def test_the_boot_reconcile_turns_the_vector_client_on(self):
        sup = supervisor([{"name": "vector-chroma", "capability": "vector"}])
        with mock.patch(
            "sage_is_ai.sprigs.vector_bootstrap.ensure_chromadb",
            new_callable=mock.AsyncMock,
        ) as ensure:
            asyncio.run(sup._reconcile())
        ensure.assert_awaited_once_with(APP)

    def test_other_capabilities_leave_the_vector_client_alone(self):
        sup = supervisor([{"name": "minilm", "capability": "embedding"}])
        sup.graft.return_value = types.SimpleNamespace(
            name="minilm", capability="embedding", process=None
        )
        with mock.patch(
            "sage_is_ai.sprigs.vector_bootstrap.ensure_chromadb",
            new_callable=mock.AsyncMock,
        ) as ensure:
            asyncio.run(sup._reconcile())
        ensure.assert_not_awaited()

    def test_the_graft_route_turns_the_vector_client_on(self):
        from sage_is_ai.routers import sprigs as route

        sup = supervisor([])
        sup.clear_error = lambda name: False
        sup.handles = lambda: {}
        request = types.SimpleNamespace(
            app=types.SimpleNamespace(state=types.SimpleNamespace(sprig_supervisor=sup))
        )
        form = types.SimpleNamespace(name="vector-chroma", capability="vector")
        with mock.patch(
            "sage_is_ai.sprigs.vector_bootstrap.ensure_chromadb",
            new_callable=mock.AsyncMock,
        ) as ensure:
            try:
                asyncio.run(
                    route.graft_sprig(
                        request, form, user=types.SimpleNamespace(role="admin")
                    )
                )
            except (
                Exception
            ):  # a response model the stand-ins cannot fill is not this test's concern
                pass
        ensure.assert_awaited_once_with(request.app)

    def test_an_overlay_that_fails_to_import_reports_false(self):
        # upgrade_gate, 2026-11-05: an amd64 overlay on an arm64 box left numpy half
        # loaded, the import raised AttributeError, and the graft route answered 500.
        import builtins

        from sage_is_ai.sprigs import vector_bootstrap

        real = builtins.__import__

        def broken(name, *args, **kwargs):
            if name == "chromadb":
                raise AttributeError("module 'numpy._globals' has no attribute")
            return real(name, *args, **kwargs)

        with mock.patch("builtins.__import__", broken):
            self.assertFalse(vector_bootstrap._try_activate("chroma"))

    def test_the_graft_route_says_when_search_did_not_start(self):
        from sage_is_ai.routers import sprigs as route

        sup = supervisor([])
        sup.clear_error = lambda name: False
        sup.handles = lambda: {}
        request = types.SimpleNamespace(
            app=types.SimpleNamespace(state=types.SimpleNamespace(sprig_supervisor=sup))
        )
        form = types.SimpleNamespace(name="vector-chroma", capability="vector")
        with mock.patch(
            "sage_is_ai.sprigs.vector_bootstrap.ensure_chromadb",
            new_callable=mock.AsyncMock,
            return_value=False,
        ):
            answer = asyncio.run(
                route.graft_sprig(
                    request, form, user=types.SimpleNamespace(role="admin")
                )
            )
        self.assertTrue(answer.delivered)
        self.assertIn("did not start", answer.warning)


if __name__ == "__main__":
    unittest.main()
