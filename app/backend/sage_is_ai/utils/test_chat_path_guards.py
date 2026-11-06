"""Chat-path shapes no replay covers, pinned from the source (2026-11-05).

Runs inside the image or the dev container:
    python3 -B -m unittest sage_is_ai.utils.test_chat_path_guards
"""

import ast
import unittest
from pathlib import Path

MIDDLEWARE = Path(__file__).resolve().parent / "middleware.py"


def function(tree, name):
    return next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


class ChatPathGuards(unittest.TestCase):
    def test_a_model_switch_reaches_the_retries(self):
        # `selected_model_id` mid-stream rebinds `model_id`; the tool-call and
        # code-interpreter retries in `response_handler` read it afterwards.
        # Without `nonlocal` the rebinding stayed local and the retries asked
        # the model the user had switched away from (found 2026-08-04).
        handler = function(ast.parse(MIDDLEWARE.read_text()), "stream_body_handler")
        declared = {
            name
            for node in ast.walk(handler)
            if isinstance(node, ast.Nonlocal)
            for name in node.names
        }
        self.assertIn("model_id", declared)


if __name__ == "__main__":
    unittest.main()
