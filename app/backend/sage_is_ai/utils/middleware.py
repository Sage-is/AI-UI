import time
import logging
import sys

import asyncio
from typing import Optional
import json
import html
import re
import ast

from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor


from fastapi import Request
from starlette.responses import StreamingResponse


from sage_is_ai.models.chats import Chats
from sage_is_ai.models.folders import Folders
from sage_is_ai.models.users import Users
from sage_is_ai.socket.main import (
    get_event_call,
    get_event_emitter,
    get_active_status_by_user_id,
)
from sage_is_ai.routers.tasks import (
    generate_queries,
    generate_title,
    generate_follow_ups,
    generate_image_prompt,
    generate_chat_tags,
)

from sage_is_ai.routers.images import (
    load_b64_image_data,
    image_generations,
    GenerateImageForm,
    upload_image,
)
from sage_is_ai.routers.pipelines import process_pipeline_inlet_filter
from sage_is_ai.routers.memories import query_memory, QueryMemoryForm

from sage_is_ai.utils.payload import merge_custom_params
from sage_is_ai.utils.webhook import post_webhook


from sage_is_ai.models.users import UserModel
from sage_is_ai.models.functions import Functions

from sage_is_ai.retrieval.utils import get_sources_from_items


from sage_is_ai.utils.chat import generate_chat_completion
from sage_is_ai.utils.task import (
    resolve_task_model_id,
    rag_template,
    tools_function_calling_generation_template,
)
from sage_is_ai.utils.misc import (
    get_available_models,
    get_message_list,
    add_or_update_system_message,
    add_or_update_user_message,
    get_last_user_message,
    get_last_assistant_message,
    prepend_to_first_user_message_content,
    convert_logit_bias_input_to_json,
)
from sage_is_ai.utils.tools import get_tools
from sage_is_ai.utils.filter import (
    get_sorted_filter_ids,
    process_filter_functions,
)
from sage_is_ai.utils.code_interpreter import execute_code_jupyter

from sage_is_ai.tasks import create_task

from sage_is_ai.config import (
    DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    DEFAULT_CODE_INTERPRETER_PROMPT,
)
from sage_is_ai.env import (
    SRC_LOG_LEVELS,
    GLOBAL_LOG_LEVEL,
    ENABLE_REALTIME_CHAT_SAVE,
)
from sage_is_ai.constants import TASKS


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


# Every end tag a model might emit to close its own reasoning, matched
# case-insensitively and tolerant of stray whitespace inside the tag. Kept here
# rather than inside the streaming closure because `finalize_content_blocks`
# below is module-level so a fixture can import and drive it directly.
REASONING_END_TAG_RE = re.compile(
    r"<\s*/\s*(?:think|thinking|reason|reasoning|thought)\s*>"
    r"|<\|end_of_thought\|>"
    r"|◁/think▷",
    re.IGNORECASE,
)


def finalize_content_blocks(content_blocks):
    """Close every block left open when a stream ends. Free trapped text.

    Closing stamps `ended_at`/`duration`. `serialize_content_blocks` reads
    `duration` to render "Thought for N seconds" instead of a perpetual
    "Thinking…". Nothing else in the streaming loop stamps it. The only close
    path for a field-opened reasoning block waits on a content delta, so a
    provider that streams the whole answer through the `reasoning` field never
    trips it: the block stays open and the answer is sealed inside.

    Stamping alone is not enough. When everything arrives through the reasoning
    field, the ANSWER is inside the block, and closing it collapses the answer
    behind a disclosure triangle. So when an unclosed reasoning block holds a
    stray end tag the model wrote itself, split there. Text before it is
    reasoning. Text after it is the answer, and it moves out to a text block.

    Idempotent. It touches only blocks with `started_at` and no `ended_at`, so
    a second call is a no-op. Both callers can run: the normal completion path
    and the cancellation handler.

    Walks the WHOLE list, not the tail. Every other close path in this module
    tests `content_blocks[-1]`, which is why a `tool_calls` block pushed on top
    of an open reasoning block orphans it permanently.
    """
    if not content_blocks:
        return content_blocks

    finalized = []
    for block in content_blocks:
        finalized.append(block)

        if block.get("ended_at") is not None or block.get("started_at") is None:
            continue

        if block.get("type") == "reasoning":
            text = block.get("content") or ""
            match = REASONING_END_TAG_RE.search(text)
            if match:
                # The model closed its own thought inside the reasoning stream.
                # Everything after that tag is the answer, not the thinking.
                block["content"] = text[: match.start()].strip()
                leftover = text[match.end() :].strip()
                if leftover:
                    finalized.append({"type": "text", "content": leftover})

        block["ended_at"] = time.time()
        block["duration"] = int(block["ended_at"] - block["started_at"])

    content_blocks[:] = finalized
    return content_blocks


# Pure block helpers, lifted out of `process_chat_response` on 2026-08-06.
# Each one closes over nothing but the others, so module level costs nothing
# and buys a name a unit test can import. They sit here beside
# `finalize_content_blocks`, which was lifted first for the same reason.
def split_content_and_whitespace(content):
    content_stripped = content.rstrip()
    original_whitespace = (
        content[len(content_stripped) :] if len(content) > len(content_stripped) else ""
    )
    return content_stripped, original_whitespace


def is_opening_code_block(content):
    backtick_segments = content.split("```")
    # Even number of segments means the last backticks are opening a new block
    return len(backtick_segments) > 1 and len(backtick_segments) % 2 == 0


def slice_json_object(text):
    """text[first '{' : last '}' + 1] — the historical JSON scrape, verbatim.

    Extracted from six duplicated call sites; quirks preserved on purpose,
    including the -1 slice when no '{' is present. It merges neighbouring
    objects and trusts the model not to restate the format — the ledger bug
    names the real fix (response_format on the task calls). This helper only
    removes the duplication.
    """
    return text[text.find("{") : text.rfind("}") + 1]


def _tool_call_details(tool_call, result):
    """One <details> element for a single tool call. `result` may be None."""
    tool_call_id = tool_call.get("id", "")
    tool_name = tool_call.get("function", {}).get("name", "")
    tool_arguments = tool_call.get("function", {}).get("arguments", "")

    # Truthiness, not `is not None`: a result with empty content renders as Executing...
    tool_result = result.get("content", None) if result else None
    tool_result_files = result.get("files", None) if result else None

    if tool_result:
        return f'\n<details type="tool_calls" done="true" id="{tool_call_id}" name="{tool_name}" arguments="{html.escape(json.dumps(tool_arguments))}" result="{html.escape(json.dumps(tool_result, ensure_ascii=False))}" files="{html.escape(json.dumps(tool_result_files)) if tool_result_files else ""}">\n<summary>Tool Executed</summary>\n</details>\n'
    return f'\n<details type="tool_calls" done="false" id="{tool_call_id}" name="{tool_name}" arguments="{html.escape(json.dumps(tool_arguments))}">\n<summary>Executing...</summary>\n</details>'


def _render_text(content, block, raw):
    return f"{content}{block['content'].strip()}\n"


def _json_or_verbatim(value):
    """Parse a JSON string, or hand back whatever came in.

    Accumulated tool-call deltas hold arguments as a JSON string; the raw
    renderer emits the object for legibility. An unparsable string — or a
    value that is already parsed — stays verbatim.
    """
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _render_tool_calls_raw(content, block):
    # Hermes-style tags — the format Qwen/Hermes tool templates train on, so
    # the model reads its own call back in a shape it already knows. NOT the
    # <details> UI form: feeding that back teaches the model to emit markup
    # the UI renders as a trusted "Tool Executed" card. The pairing is
    # positional (call, then its response), so no ids are emitted. See
    # docs/decisions/2026-08-08-raw-tool-call-form.md.
    results = block.get("results", [])
    parts = []
    for tool_call in block.get("content", []):
        tool_call_id = tool_call.get("id", "")
        tool_name = tool_call.get("function", {}).get("name", "")
        arguments = _json_or_verbatim(
            tool_call.get("function", {}).get("arguments", "")
        )
        call = json.dumps(
            {"name": tool_name, "arguments": arguments}, ensure_ascii=False
        )
        parts.append(f"<tool_call>\n{call}\n</tool_call>")
        result = next(
            (r for r in results if r.get("tool_call_id", "") == tool_call_id),
            None,
        )
        # Same discipline as the display arm: first match wins, and falsy
        # content means the call is still pending — no response tag.
        if result and result.get("content"):
            parts.append(f"<tool_response>\n{result['content']}\n</tool_response>")
    body = "\n".join(parts)
    return f"{content}\n{body}\n"


def _render_tool_calls(content, block, raw):
    if raw:
        return _render_tool_calls_raw(content, block)

    # Both arms of the old if/else emitted the same string when no result matched, so
    # an empty `results` list needs no branch of its own.
    results = block.get("results", [])
    display = ""
    for tool_call in block.get("content", []):
        tool_call_id = tool_call.get("id", "")
        # Linear scan semantics: the FIRST match wins. A dict would keep the last.
        result = next(
            (r for r in results if r.get("tool_call_id", "") == tool_call_id), None
        )
        display = f"{display}{_tool_call_details(tool_call, result)}"

    return f"{content}\n{display}\n\n"


def _render_reasoning(content, block, raw):
    if raw:
        return f"{content}\n{block['start_tag']}{block['content']}{block['end_tag']}\n"

    body = "\n".join(
        (f"> {line}" if not line.startswith(">") else line)
        for line in block["content"].splitlines()
    )
    duration = block.get("duration", None)
    if duration is not None:
        return f'{content}\n<details type="reasoning" done="true" duration="{duration}">\n<summary>Thought for {duration} seconds</summary>\n{body}\n</details>\n'
    return f'{content}\n<details type="reasoning" done="false">\n<summary>Thinking\u2026</summary>\n{body}\n</details>\n'


def _render_code_interpreter(content, block, raw):
    lang = block.get("attributes", {}).get("lang", "")
    output = block.get("output", None)

    content_stripped, original_whitespace = split_content_and_whitespace(content)
    if is_opening_code_block(content_stripped):
        # Remove trailing backticks that would open a new block
        content = content_stripped.rstrip("`").rstrip() + original_whitespace
    else:
        # Keep content as is - either closing backticks or no backticks
        content = content_stripped + original_whitespace

    code = block["content"]
    if output:
        output = html.escape(json.dumps(output))
        if raw:
            return f'{content}\n<code_interpreter type="code" lang="{lang}">\n{code}\n</code_interpreter>\n```output\n{output}\n```\n'
        return f'{content}\n<details type="code_interpreter" done="true" output="{output}">\n<summary>Analyzed</summary>\n```{lang}\n{code}\n```\n</details>\n'
    if raw:
        return f'{content}\n<code_interpreter type="code" lang="{lang}">\n{code}\n</code_interpreter>\n'
    return f'{content}\n<details type="code_interpreter" done="false">\n<summary>Analyzing...</summary>\n```{lang}\n{code}\n```\n</details>\n'


def _render_fallback(content, block, raw):
    return f"{content}{block['type']}: {str(block['content']).strip()}\n"


BLOCK_RENDERERS = {
    "text": _render_text,
    "tool_calls": _render_tool_calls,
    "reasoning": _render_reasoning,
    "code_interpreter": _render_code_interpreter,
}


def serialize_content_blocks(content_blocks, raw=False):
    content = ""
    for block in content_blocks:
        # isinstance guard: the old if/elif chain routed ANY unrecognised type —
        # including unhashable ones — to the fallback. dict.get alone would raise
        # TypeError on an unhashable key, and plugins can hand this helper
        # arbitrary blocks.
        block_type = block["type"]
        render = (
            BLOCK_RENDERERS.get(block_type, _render_fallback)
            if isinstance(block_type, str)
            else _render_fallback
        )
        content = render(content, block, raw)
    return content.strip()


def convert_content_blocks_to_messages(content_blocks):
    messages = []

    temp_blocks = []
    for idx, block in enumerate(content_blocks):
        if block["type"] == "tool_calls":
            messages.append(
                {
                    "role": "assistant",
                    "content": serialize_content_blocks(temp_blocks),
                    "tool_calls": block.get("content"),
                }
            )

            results = block.get("results", [])

            for result in results:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": result["content"],
                    }
                )
            temp_blocks = []
        else:
            temp_blocks.append(block)

    if temp_blocks:
        content = serialize_content_blocks(temp_blocks)
        if content:
            messages.append(
                {
                    "role": "assistant",
                    "content": content,
                }
            )

    return messages


def tag_content_handler(content_type, tags, content, content_blocks):
    end_flag = False

    def extract_attributes(tag_content):
        """Extract a tag's attributes, if present."""
        attributes = {}
        if not tag_content:  # Ensure tag_content is not None
            return attributes
        # Match attributes in the format: key="value" (ignores single quotes for simplicity)
        matches = re.findall(r'(\w+)\s*=\s*"([^"]+)"', tag_content)
        for key, value in matches:
            attributes[key] = value
        return attributes

    if content_blocks[-1]["type"] == "text":
        for start_tag, end_tag in tags:
            start_tag_pattern = rf"{re.escape(start_tag)}"
            if start_tag.startswith("<") and start_tag.endswith(">"):
                # Match start tag e.g., <tag> or <tag attr="value">
                # remove both '<' and '>' from start_tag
                # Match start tag with attributes
                start_tag_pattern = rf"<{re.escape(start_tag[1:-1])}(\s.*?)?>"

            match = re.search(start_tag_pattern, content)
            if match:
                attr_content = (
                    match.group(1) if match.group(1) else ""
                )  # Ensure it's not None
                attributes = extract_attributes(
                    attr_content
                )  # Extract attributes safely

                # Capture everything before and after the matched tag
                before_tag = content[: match.start()]  # Content before opening tag
                after_tag = content[match.end() :]  # Content after opening tag

                # Remove the start tag and after from the currently handling text block
                content_blocks[-1]["content"] = content_blocks[-1]["content"].replace(
                    match.group(0) + after_tag, ""
                )

                if before_tag:
                    content_blocks[-1]["content"] = before_tag

                if not content_blocks[-1]["content"]:
                    content_blocks.pop()

                # Append the new block
                content_blocks.append(
                    {
                        "type": content_type,
                        "start_tag": start_tag,
                        "end_tag": end_tag,
                        "attributes": attributes,
                        "content": "",
                        "started_at": time.time(),
                    }
                )

                if after_tag:
                    content_blocks[-1]["content"] = after_tag
                    tag_content_handler(content_type, tags, after_tag, content_blocks)

                break
    elif content_blocks[-1]["type"] == content_type:
        start_tag = content_blocks[-1]["start_tag"]
        end_tag = content_blocks[-1]["end_tag"]

        if end_tag.startswith("<") and end_tag.endswith(">"):
            # Match end tag e.g., </tag>
            end_tag_pattern = rf"{re.escape(end_tag)}"
        else:
            # Handle cases where end_tag is just a tag name
            end_tag_pattern = rf"{re.escape(end_tag)}"

        # Check if the content has the end tag
        if re.search(end_tag_pattern, content):
            end_flag = True

            block_content = content_blocks[-1]["content"]
            # Strip start and end tags from the content. NOT dead code: with a
            # bracketed start_tag this builds e.g. `<<think>(.*?)>`, which never
            # matches the tag itself but DOES eat any literal `<<think>…>` span
            # inside the body — silently deleting text. Frozen bug, see the
            # ledger; proven live by the 2026-08-08 verify pass.
            start_tag_pattern = rf"<{re.escape(start_tag)}(.*?)>"
            block_content = re.sub(start_tag_pattern, "", block_content).strip()

            end_tag_regex = re.compile(end_tag_pattern, re.DOTALL)
            split_content = end_tag_regex.split(block_content, maxsplit=1)

            # Content inside the tag
            block_content = split_content[0].strip() if split_content else ""

            # Leftover content (everything after `</tag>`)
            leftover_content = (
                split_content[1].strip() if len(split_content) > 1 else ""
            )

            if block_content:
                content_blocks[-1]["content"] = block_content
                content_blocks[-1]["ended_at"] = time.time()
                content_blocks[-1]["duration"] = int(
                    content_blocks[-1]["ended_at"] - content_blocks[-1]["started_at"]
                )

                # Reset the content_blocks by appending a new text block.
                # `leftover_content` is already "" when nothing followed the tag.
                if content_type != "code_interpreter":
                    content_blocks.append(
                        {
                            "type": "text",
                            "content": leftover_content,
                        }
                    )

            else:
                # Remove the block if content is empty
                content_blocks.pop()

                content_blocks.append(
                    {
                        "type": "text",
                        "content": leftover_content,
                    }
                )

            # Clean processed content
            start_tag_pattern = rf"{re.escape(start_tag)}"
            if start_tag.startswith("<") and start_tag.endswith(">"):
                # Match start tag e.g., <tag> or <tag attr="value">
                # remove both '<' and '>' from start_tag
                # Match start tag with attributes
                start_tag_pattern = rf"<{re.escape(start_tag[1:-1])}(\s.*?)?>"

            content = re.sub(
                rf"{start_tag_pattern}(.|\n)*?{re.escape(end_tag)}",
                "",
                content,
                flags=re.DOTALL,
            )

    return content, content_blocks, end_flag


# Every `chat:completion` event goes out through these two. Eleven call sites
# spelled the envelope by hand, four of them character for character; the
# oracle pins the payload, so the only thing standardising them can change is
# how much of this file is punctuation. The emitter is passed in rather than
# captured — these are module level so a test can drive them with a stub.
async def emit_event(event_emitter, event_type, data):
    """One {type, data} socket envelope. Ten sites spelled the dict by hand."""
    await event_emitter({"type": event_type, "data": data})


async def emit_completion(event_emitter, data):
    await event_emitter({"type": "chat:completion", "data": data})


async def execute_tool_call(
    tool, tool_name, tool_function_params, event_caller, metadata, ensure_ascii
):
    """Filter params to the spec, dispatch direct or local, normalize the result.

    Shared by the prompt-based path (chat_completion_tools_handler) and the
    native streaming path. Returns (tool_result, tool_result_files,
    filtered_params). The two callers historically disagreed on `ensure_ascii`
    for the JSON dump — the difference is preserved as an argument, not
    silently unified.
    """
    try:
        spec = tool.get("spec", {})
        allowed_params = spec.get("parameters", {}).get("properties", {}).keys()
        tool_function_params = {
            k: v for k, v in tool_function_params.items() if k in allowed_params
        }

        if tool.get("direct", False):
            tool_result = await event_caller(
                {
                    "type": "execute:tool",
                    "data": {
                        "id": str(uuid4()),
                        "name": tool_name,
                        "params": tool_function_params,
                        "server": tool.get("server", {}),
                        "session_id": metadata.get("session_id", None),
                    },
                }
            )
        else:
            tool_function = tool["callable"]
            tool_result = await tool_function(**tool_function_params)

    except Exception as e:
        tool_result = str(e)

    tool_result_files = []
    if isinstance(tool_result, list):
        for item in tool_result:
            # check if string
            if isinstance(item, str) and item.startswith("data:"):
                tool_result_files.append(item)
                tool_result.remove(item)

    if isinstance(tool_result, dict) or isinstance(tool_result, list):
        tool_result = json.dumps(tool_result, indent=2, ensure_ascii=ensure_ascii)

    return tool_result, tool_result_files, tool_function_params


def accumulate_tool_call_deltas(response_tool_calls, delta_tool_calls):
    """Merge streamed tool-call deltas into the accumulator, in place.

    A delta with a known `index` extends that call's name and arguments; an
    unseen `index` starts a new call. NOTE: `setdefault` mutates the delta dict
    itself, and that same object is appended to the accumulator — the parsed
    chunk the reader receives under ENABLE_REALTIME_CHAT_SAVE shares it. Do not
    "tidy" this with a copy.
    """
    for delta_tool_call in delta_tool_calls:
        tool_call_index = delta_tool_call.get("index")

        if tool_call_index is not None:
            # Check if the tool call already exists
            current_response_tool_call = None
            for response_tool_call in response_tool_calls:
                if response_tool_call.get("index") == tool_call_index:
                    current_response_tool_call = response_tool_call
                    break

            if current_response_tool_call is None:
                # Add the new tool call
                delta_tool_call.setdefault("function", {})
                delta_tool_call["function"].setdefault("name", "")
                delta_tool_call["function"].setdefault("arguments", "")
                response_tool_calls.append(delta_tool_call)
            else:
                # Update the existing tool call
                delta_name = delta_tool_call.get("function", {}).get("name")
                delta_arguments = delta_tool_call.get("function", {}).get("arguments")

                if delta_name:
                    current_response_tool_call["function"]["name"] += delta_name

                if delta_arguments:
                    current_response_tool_call["function"]["arguments"] += (
                        delta_arguments
                    )


def build_extra_params(request, model, metadata, user, event_emitter, event_call):
    """The six keys every filter and tool invocation receives."""
    return {
        "__event_emitter__": event_emitter,
        "__event_call__": event_call,
        "__user__": user.model_dump() if isinstance(user, UserModel) else {},
        "__metadata__": metadata,
        "__request__": request,
        "__model__": model,
    }


def get_filter_functions(request, model, metadata):
    """The model's filter functions, in execution order."""
    return [
        Functions.get_function_by_id(filter_id)
        for filter_id in get_sorted_filter_ids(
            request, model, metadata.get("filter_ids", [])
        )
    ]


def append_empty_text_block(content_blocks):
    """Start a fresh text block so later deltas land after a closed block.

    NOTE: two structurally identical pushes live INSIDE tag_content_handler and
    must stay inline — scripts/smoke/reasoning-tag-fixture.py executes that
    function standalone with only `re` and `time` in scope, so any new free
    variable breaks it silently.
    """
    content_blocks.append(
        {
            "type": "text",
            "content": "",
        }
    )


def upload_b64_images_in_text(request, text, metadata, user):
    """Replace each data:image/png;base64 line with an uploaded-image link."""
    lines = text.split("\n")
    for idx, line in enumerate(lines):
        if "data:image/png;base64" in line:
            image_url = ""
            # Extract base64 image data from the line
            image_data, content_type = load_b64_image_data(line)
            if image_data is not None:
                image_url = upload_image(
                    request,
                    image_data,
                    content_type,
                    metadata,
                    user,
                )
            lines[idx] = f"![Output Image]({image_url})"
    return "\n".join(lines)


def persist_message(metadata, payload):
    """Upsert `payload` onto this request's chat message. Ten sites spelled the
    chat-id/message-id pair by hand; the pair travels in `metadata`."""
    Chats.upsert_message_to_chat_by_id_and_message_id(
        metadata["chat_id"],
        metadata["message_id"],
        payload,
    )


def notify_webhook_if_offline(request, user, metadata, title, content):
    """Send a webhook notification if the user has no active session.

    `content` is whatever the caller shows the user — the streaming path
    deliberately passes the raw accumulator rather than the serialized blocks.
    """
    if not get_active_status_by_user_id(user.id):
        webhook_url = Users.get_user_webhook_url_by_id(user.id)
        if webhook_url:
            post_webhook(
                request.app.state.WEBUI_NAME,
                webhook_url,
                f"{title} - {request.app.state.config.WEBUI_URL}/c/{metadata['chat_id']}\n\n{content}",
                {
                    "action": "chat",
                    "message": content,
                    "title": title,
                    "url": f"{request.app.state.config.WEBUI_URL}/c/{metadata['chat_id']}",
                },
            )


async def emit_content(event_emitter, content_blocks):
    """Publish the blocks as they render right now."""
    await emit_completion(
        event_emitter, {"content": serialize_content_blocks(content_blocks)}
    )


async def chat_completion_tools_handler(
    request: Request, body: dict, extra_params: dict, user: UserModel, models, tools
) -> tuple[dict, dict]:
    async def get_content_from_response(response) -> Optional[str]:
        content = None
        if hasattr(response, "body_iterator"):
            async for chunk in response.body_iterator:
                data = json.loads(chunk.decode("utf-8"))
                content = data["choices"][0]["message"]["content"]

            # Cleanup any remaining background tasks if necessary
            if response.background is not None:
                await response.background()
        else:
            content = response["choices"][0]["message"]["content"]
        return content

    def get_tools_function_calling_payload(messages, task_model_id, content):
        user_message = get_last_user_message(messages)
        history = "\n".join(
            f'{message["role"].upper()}: """{message["content"]}"""'
            for message in messages[::-1][:4]
        )

        prompt = f"History:\n{history}\nQuery: {user_message}"

        return {
            "model": task_model_id,
            "messages": [
                {"role": "system", "content": content},
                {"role": "user", "content": f"Query: {prompt}"},
            ],
            "stream": False,
            "metadata": {"task": str(TASKS.FUNCTION_CALLING)},
        }

    event_caller = extra_params["__event_call__"]
    metadata = extra_params["__metadata__"]

    task_model_id = resolve_task_model_id(request, body["model"], models)

    skip_files = False
    sources = []

    specs = [tool["spec"] for tool in tools.values()]
    tools_specs = json.dumps(specs)

    if request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE != "":
        template = request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
    else:
        template = DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE

    tools_function_calling_prompt = tools_function_calling_generation_template(
        template, tools_specs
    )
    payload = get_tools_function_calling_payload(
        body["messages"], task_model_id, tools_function_calling_prompt
    )

    try:
        response = await generate_chat_completion(request, form_data=payload, user=user)
        log.debug(f"{response=}")
        content = await get_content_from_response(response)
        log.debug(f"{content=}")

        if not content:
            return body, {}

        try:
            content = slice_json_object(content)
            if not content:
                raise Exception("No JSON object found in the response")

            result = json.loads(content)

            async def tool_call_handler(tool_call):
                nonlocal skip_files

                log.debug(f"{tool_call=}")

                tool_function_name = tool_call.get("name", None)
                if tool_function_name not in tools:
                    return body, {}

                tool_function_params = tool_call.get("parameters", {})

                tool_result, _, tool_function_params = await execute_tool_call(
                    tools[tool_function_name],
                    tool_function_name,
                    tool_function_params,
                    event_caller,
                    metadata,
                    ensure_ascii=True,
                )

                if isinstance(tool_result, str):
                    tool = tools[tool_function_name]
                    tool_id = tool.get("tool_id", "")

                    tool_name = (
                        f"{tool_id}/{tool_function_name}"
                        if tool_id
                        else f"{tool_function_name}"
                    )

                    # Citation is enabled for this tool
                    sources.append(
                        {
                            "source": {
                                "name": (f"TOOL:{tool_name}"),
                            },
                            "document": [tool_result],
                            "metadata": [
                                {
                                    "source": (f"TOOL:{tool_name}"),
                                    "parameters": tool_function_params,
                                }
                            ],
                            "tool_result": True,
                        }
                    )
                    # Citation is not enabled for this tool
                    body["messages"] = add_or_update_user_message(
                        f"\nTool `{tool_name}` Output: {tool_result}",
                        body["messages"],
                    )

                    if (
                        tools[tool_function_name]
                        .get("metadata", {})
                        .get("file_handler", False)
                    ):
                        skip_files = True

            # check if "tool_calls" in result
            if result.get("tool_calls"):
                for tool_call in result.get("tool_calls"):
                    await tool_call_handler(tool_call)
            else:
                await tool_call_handler(result)

        except Exception as e:
            log.debug(f"Error: {e}")
            content = None
    except Exception as e:
        log.debug(f"Error: {e}")
        content = None

    log.debug(f"tool_contexts: {sources}")

    if skip_files and "files" in body.get("metadata", {}):
        del body["metadata"]["files"]

    return body, {"sources": sources}


async def chat_memory_handler(
    request: Request, form_data: dict, extra_params: dict, user
):
    try:
        results = await query_memory(
            request,
            QueryMemoryForm(
                **{
                    "content": get_last_user_message(form_data["messages"]) or "",
                    "k": 3,
                }
            ),
            user,
        )
    except Exception as e:
        log.debug(e)
        results = None

    user_context = ""
    if results and hasattr(results, "documents"):
        if results.documents and len(results.documents) > 0:
            for doc_idx, doc in enumerate(results.documents[0]):
                created_at_date = "Unknown Date"

                if results.metadatas[0][doc_idx].get("created_at"):
                    created_at_timestamp = results.metadatas[0][doc_idx]["created_at"]
                    created_at_date = time.strftime(
                        "%Y-%m-%d", time.localtime(created_at_timestamp)
                    )

                user_context += f"{doc_idx + 1}. [{created_at_date}] {doc}\n"

    form_data["messages"] = add_or_update_system_message(
        f"User Context:\n{user_context}\n", form_data["messages"], append=True
    )

    return form_data


async def chat_image_generation_handler(
    request: Request, form_data: dict, extra_params: dict, user
):
    __event_emitter__ = extra_params["__event_emitter__"]
    await emit_event(
        __event_emitter__,
        "status",
        {"description": "Generating an image", "done": False},
    )

    messages = form_data["messages"]
    user_message = get_last_user_message(messages)

    prompt = user_message

    if request.app.state.config.ENABLE_IMAGE_PROMPT_GENERATION:
        try:
            res = await generate_image_prompt(
                request,
                {
                    "model": form_data["model"],
                    "messages": messages,
                },
                user,
            )

            response = res["choices"][0]["message"]["content"]

            try:
                # `rfind + 1` can never be -1, so only the missing-'{' half of
                # the old guard was live.
                if "{" not in response:
                    raise Exception("No JSON object found in the response")

                response = slice_json_object(response)
                response = json.loads(response)
                prompt = response.get("prompt", [])
            except Exception:
                prompt = user_message

        except Exception as e:
            log.exception(e)
            prompt = user_message

    system_message_content = ""

    try:
        images = await image_generations(
            request=request,
            form_data=GenerateImageForm(**{"prompt": prompt}),
            user=user,
        )

        await emit_event(
            __event_emitter__,
            "status",
            {"description": "Generated an image", "done": True},
        )

        await emit_event(
            __event_emitter__,
            "files",
            {
                "files": [
                    {
                        "type": "image",
                        "url": image["url"],
                    }
                    for image in images
                ]
            },
        )

        system_message_content = "<context>User is shown the generated image, tell the user that the image has been generated</context>"
    except Exception as e:
        log.exception(e)
        await emit_event(
            __event_emitter__,
            "status",
            {
                "description": "An error occurred while generating an image",
                "done": True,
            },
        )

        system_message_content = "<context>Unable to generate an image, tell the user that an error occurred</context>"

    if system_message_content:
        form_data["messages"] = add_or_update_system_message(
            system_message_content, form_data["messages"]
        )

    return form_data


async def chat_completion_files_handler(
    request: Request, body: dict, user: UserModel
) -> tuple[dict, dict[str, list]]:
    sources = []

    if files := body.get("metadata", {}).get("files", None):
        queries = []
        try:
            queries_response = await generate_queries(
                request,
                {
                    "model": body["model"],
                    "messages": body["messages"],
                    "type": "retrieval",
                },
                user,
            )
            queries_response = queries_response["choices"][0]["message"]["content"]

            try:
                # Guard before the rebind: the fallback below wraps whatever
                # this name holds — the ORIGINAL reply when no '{' exists, the
                # sliced span when the parse itself fails.
                if "{" not in queries_response:
                    raise Exception("No JSON object found in the response")

                queries_response = slice_json_object(queries_response)
                queries_response = json.loads(queries_response)
            except Exception:
                queries_response = {"queries": [queries_response]}

            queries = queries_response.get("queries", [])
        except:  # noqa: E722
            pass

        if len(queries) == 0:
            queries = [get_last_user_message(body["messages"])]

        try:
            # Offload get_sources_from_items to a separate thread
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as executor:
                sources = await loop.run_in_executor(
                    executor,
                    lambda: get_sources_from_items(
                        request=request,
                        items=files,
                        queries=queries,
                        embedding_function=lambda query, prefix: (
                            request.app.state.EMBEDDING_FUNCTION(
                                query, prefix=prefix, user=user
                            )
                        ),
                        k=request.app.state.config.TOP_K,
                        reranking_function=(
                            (
                                lambda sentences: request.app.state.RERANKING_FUNCTION(
                                    sentences, user=user
                                )
                            )
                            if request.app.state.RERANKING_FUNCTION
                            else None
                        ),
                        k_reranker=request.app.state.config.TOP_K_RERANKER,
                        r=request.app.state.config.RELEVANCE_THRESHOLD,
                        hybrid_bm25_weight=request.app.state.config.HYBRID_BM25_WEIGHT,
                        hybrid_search=request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
                        full_context=request.app.state.config.RAG_FULL_CONTEXT,
                        user=user,
                    ),
                )
        except Exception as e:
            log.exception(e)

        log.debug(f"rag_contexts:sources: {sources}")

    return body, {"sources": sources}


def apply_params_to_form_data(form_data, model):
    params = form_data.pop("params", {})

    open_webui_params = {
        "stream_response": bool,
        "function_calling": str,
        "system": str,
    }

    for key in list(params.keys()):
        if key in open_webui_params:
            del params[key]

    params = merge_custom_params(params)

    if model.get("owned_by") == "ollama":
        # Ollama specific parameters
        form_data["options"] = params
    else:
        if isinstance(params, dict):
            for key, value in params.items():
                if value is not None:
                    form_data[key] = value

        if "logit_bias" in params and params["logit_bias"] is not None:
            try:
                form_data["logit_bias"] = json.loads(
                    convert_logit_bias_input_to_json(params["logit_bias"])
                )
            except Exception as e:
                log.exception(f"Error parsing logit_bias: {e}")

    return form_data


async def process_chat_payload(request, form_data, user, metadata, model):
    # Pipeline Inlet -> Filter Inlet -> Chat Memory -> Chat Web Search -> Chat Image Generation
    # -> Chat Code Interpreter (Form Data Update) -> (Default) Chat Tools Function Calling
    # -> Chat Files

    form_data = apply_params_to_form_data(form_data, model)
    log.debug(f"form_data: {form_data}")

    event_emitter = get_event_emitter(metadata)
    event_call = get_event_call(metadata)

    extra_params = build_extra_params(
        request, model, metadata, user, event_emitter, event_call
    )

    # Initialize events to store additional event to be sent to the client
    # Initialize contexts and citation
    models = get_available_models(request)

    task_model_id = resolve_task_model_id(request, form_data["model"], models)

    events = []
    sources = []

    # Folder "Project" handling
    # Check if the request has chat_id and is inside of a folder
    chat_id = metadata.get("chat_id", None)
    if chat_id and user:
        chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
        if chat and chat.folder_id:
            folder = Folders.get_folder_by_id_and_user_id(chat.folder_id, user.id)

            if folder and folder.data:
                if "system_prompt" in folder.data:
                    form_data["messages"] = add_or_update_system_message(
                        folder.data["system_prompt"], form_data["messages"]
                    )
                if "files" in folder.data:
                    form_data["files"] = [
                        *folder.data["files"],
                        *form_data.get("files", []),
                    ]

    # Model "Knowledge" handling
    user_message = get_last_user_message(form_data["messages"])
    model_knowledge = model.get("info", {}).get("meta", {}).get("knowledge", False)

    if model_knowledge:
        await emit_event(
            event_emitter,
            "status",
            {
                "action": "knowledge_search",
                "query": user_message,
                "done": False,
            },
        )

        knowledge_files = []
        for item in model_knowledge:
            if item.get("collection_name"):
                knowledge_files.append(
                    {
                        "id": item.get("collection_name"),
                        "name": item.get("name"),
                        "legacy": True,
                    }
                )
            elif item.get("collection_names"):
                knowledge_files.append(
                    {
                        "name": item.get("name"),
                        "type": "collection",
                        "collection_names": item.get("collection_names"),
                        "legacy": True,
                    }
                )
            else:
                knowledge_files.append(item)

        files = form_data.get("files", [])
        files.extend(knowledge_files)
        form_data["files"] = files

    form_data.pop("variables", None)

    # Process the form_data through the pipeline
    try:
        form_data = await process_pipeline_inlet_filter(
            request, form_data, user, models
        )
    except Exception as e:
        raise e

    try:
        filter_functions = get_filter_functions(request, model, metadata)

        form_data, flags = await process_filter_functions(
            request=request,
            filter_functions=filter_functions,
            filter_type="inlet",
            form_data=form_data,
            extra_params=extra_params,
        )
    except Exception as e:
        raise Exception(f"Error: {e}")

    features = form_data.pop("features", None)
    if features:
        if "memory" in features and features["memory"]:
            form_data = await chat_memory_handler(
                request, form_data, extra_params, user
            )

        if "web_search" in features and features["web_search"]:
            form_data = await chat_web_search_handler(  # noqa: F821 — grandfathered, not absolved: frozen NameError, TODO.md:601
                request, form_data, extra_params, user
            )

        if "image_generation" in features and features["image_generation"]:
            form_data = await chat_image_generation_handler(
                request, form_data, extra_params, user
            )

        if "code_interpreter" in features and features["code_interpreter"]:
            form_data["messages"] = add_or_update_user_message(
                (
                    request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE
                    if request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE != ""
                    else DEFAULT_CODE_INTERPRETER_PROMPT
                ),
                form_data["messages"],
            )

    tool_ids = form_data.pop("tool_ids", None)
    files = form_data.pop("files", None)

    # Remove files duplicates
    if files:
        files = list({json.dumps(f, sort_keys=True): f for f in files}.values())

    metadata = {
        **metadata,
        "tool_ids": tool_ids,
        "files": files,
    }
    form_data["metadata"] = metadata

    # Server side tools
    tool_ids = metadata.get("tool_ids", None)
    # Client side tools
    tool_servers = metadata.get("tool_servers", None)

    log.debug(f"{tool_ids=}")
    log.debug(f"{tool_servers=}")

    tools_dict = {}

    if tool_ids:
        tools_dict = get_tools(
            request,
            tool_ids,
            user,
            {
                **extra_params,
                "__model__": models[task_model_id],
                "__messages__": form_data["messages"],
                "__files__": metadata.get("files", []),
            },
        )

    if tool_servers:
        for tool_server in tool_servers:
            tool_specs = tool_server.pop("specs", [])

            for tool in tool_specs:
                tools_dict[tool["name"]] = {
                    "spec": tool,
                    "direct": True,
                    "server": tool_server,
                }

    if tools_dict:
        if metadata.get("function_calling") == "native":
            # If the function calling is native, then call the tools function calling handler
            metadata["tools"] = tools_dict
            form_data["tools"] = [
                {"type": "function", "function": tool.get("spec", {})}
                for tool in tools_dict.values()
            ]
        else:
            # If the function calling is not native, then call the tools function calling handler
            try:
                form_data, flags = await chat_completion_tools_handler(
                    request, form_data, extra_params, user, models, tools_dict
                )
                sources.extend(flags.get("sources", []))
            except Exception as e:
                log.exception(e)

    try:
        form_data, flags = await chat_completion_files_handler(request, form_data, user)
        sources.extend(flags.get("sources", []))
    except Exception as e:
        log.exception(e)

    # If context is not empty, insert it into the messages
    if len(sources) > 0:
        context_string = ""
        citation_idx_map = {}

        for source in sources:
            is_tool_result = source.get("tool_result", False)

            if "document" in source and not is_tool_result:
                for document_text, document_metadata in zip(
                    source["document"], source["metadata"]
                ):
                    source_name = source.get("source", {}).get("name", None)
                    source_id = (
                        document_metadata.get("source", None)
                        or source.get("source", {}).get("id", None)
                        or "N/A"
                    )

                    if source_id not in citation_idx_map:
                        citation_idx_map[source_id] = len(citation_idx_map) + 1

                    context_string += (
                        f'<source id="{citation_idx_map[source_id]}"'
                        + (f' name="{source_name}"' if source_name else "")
                        + f">{document_text}</source>\n"
                    )

        context_string = context_string.strip()

        prompt = get_last_user_message(form_data["messages"])
        if prompt is None:
            raise Exception("No user message found")

        if context_string == "":
            if request.app.state.config.RELEVANCE_THRESHOLD == 0:
                log.debug(
                    "With a 0 relevancy threshold for RAG, the context cannot be empty"
                )
        else:
            # Workaround for Ollama 2.0+ system prompt issue
            # TODO: replace with add_or_update_system_message
            if model.get("owned_by") == "ollama":
                form_data["messages"] = prepend_to_first_user_message_content(
                    rag_template(
                        request.app.state.config.RAG_TEMPLATE, context_string, prompt
                    ),
                    form_data["messages"],
                )
            else:
                form_data["messages"] = add_or_update_system_message(
                    rag_template(
                        request.app.state.config.RAG_TEMPLATE, context_string, prompt
                    ),
                    form_data["messages"],
                )

    # If there are citations, add them to the data_items
    sources = [
        source
        for source in sources
        if source.get("source", {}).get("name", "")
        or source.get("source", {}).get("id", "")
    ]

    if len(sources) > 0:
        events.append({"sources": sources})

    if model_knowledge:
        await emit_event(
            event_emitter,
            "status",
            {
                "action": "knowledge_search",
                "query": user_message,
                "done": True,
                "hidden": True,
            },
        )

    return form_data, metadata, events


async def process_chat_response(
    request, response, form_data, user, metadata, model, events, tasks
):
    async def background_tasks_handler():
        message_map = Chats.get_messages_by_chat_id(metadata["chat_id"])
        message = message_map.get(metadata["message_id"]) if message_map else None

        if message:
            message_list = get_message_list(message_map, metadata["message_id"])

            # Remove details tags and files from the messages.
            # as get_message_list creates a new list, it does not affect
            # the original messages outside of this handler

            messages = []
            for message in message_list:
                content = message.get("content", "")
                if isinstance(content, list):
                    for item in content:
                        if item.get("type") == "text":
                            content = item["text"]
                            break

                if isinstance(content, str):
                    content = re.sub(
                        r"<details\b[^>]*>.*?<\/details>|!\[.*?\]\(.*?\)",
                        "",
                        content,
                        flags=re.S | re.I,
                    ).strip()

                messages.append(
                    {
                        **message,
                        "role": message.get(
                            "role", "assistant"
                        ),  # Safe fallback for missing role
                        "content": content,
                    }
                )

            async def run_json_task(task_fn, payload, key, persist, make_event):
                """Follow-ups and tags share this envelope character for
                character; only the key, persist call and event shape differ.
                The title task does NOT fit — its fallback chain persists and
                emits even on parse failure, and it has a no-LLM arm.

                persist and emit stay INSIDE the try: a DB or emitter error is
                swallowed exactly as the inline copies swallowed it.
                """
                res = await task_fn(request, payload, user)

                if res and isinstance(res, dict):
                    if len(res.get("choices", [])) == 1:
                        value_string = (
                            res.get("choices", [])[0]
                            .get("message", {})
                            .get("content", "")
                        )
                    else:
                        value_string = ""

                    value_string = slice_json_object(value_string)

                    try:
                        value = json.loads(value_string).get(key, [])

                        persist(value)

                        await event_emitter(make_event(value))
                    except Exception:
                        pass

            if tasks and messages:
                if (
                    TASKS.FOLLOW_UP_GENERATION in tasks
                    and tasks[TASKS.FOLLOW_UP_GENERATION]
                ):
                    await run_json_task(
                        generate_follow_ups,
                        {
                            "model": message["model"],
                            "messages": messages,
                            "message_id": metadata["message_id"],
                            "chat_id": metadata["chat_id"],
                        },
                        "follow_ups",
                        lambda v: persist_message(metadata, {"followUps": v}),
                        lambda v: {
                            "type": "chat:message:follow_ups",
                            "data": {"follow_ups": v},
                        },
                    )

                if TASKS.TITLE_GENERATION in tasks:
                    user_message = get_last_user_message(messages)
                    if user_message and len(user_message) > 100:
                        user_message = user_message[:100] + "..."

                    if tasks[TASKS.TITLE_GENERATION]:
                        res = await generate_title(
                            request,
                            {
                                "model": message["model"],
                                "messages": messages,
                                "chat_id": metadata["chat_id"],
                            },
                            user,
                        )

                        if res and isinstance(res, dict):
                            if len(res.get("choices", [])) == 1:
                                title_string = (
                                    res.get("choices", [])[0]
                                    .get("message", {})
                                    .get(
                                        "content", message.get("content", user_message)
                                    )
                                )
                            else:
                                title_string = ""

                            title_string = slice_json_object(title_string)

                            try:
                                title = json.loads(title_string).get(
                                    "title", user_message
                                )
                            except Exception:
                                title = ""

                            if not title:
                                title = messages[0].get("content", user_message)

                            Chats.update_chat_title_by_id(metadata["chat_id"], title)

                            await emit_event(event_emitter, "chat:title", title)
                    elif len(messages) == 2:
                        title = messages[0].get("content", user_message)

                        Chats.update_chat_title_by_id(metadata["chat_id"], title)

                        # NOT `title` — the two-message arm emits the last
                        # message while persisting the first. Frozen bug.
                        await emit_event(
                            event_emitter,
                            "chat:title",
                            message.get("content", user_message),
                        )

                if TASKS.TAGS_GENERATION in tasks and tasks[TASKS.TAGS_GENERATION]:
                    await run_json_task(
                        generate_chat_tags,
                        {
                            "model": message["model"],
                            "messages": messages,
                            "chat_id": metadata["chat_id"],
                        },
                        "tags",
                        lambda v: Chats.update_chat_tags_by_id(
                            metadata["chat_id"], v, user
                        ),
                        lambda v: {"type": "chat:tags", "data": v},
                    )

    event_emitter = None
    event_caller = None
    if (
        "session_id" in metadata
        and metadata["session_id"]
        and "chat_id" in metadata
        and metadata["chat_id"]
        and "message_id" in metadata
        and metadata["message_id"]
    ):
        event_emitter = get_event_emitter(metadata)
        event_caller = get_event_call(metadata)

    # Non-streaming response
    if not isinstance(response, StreamingResponse):
        if event_emitter:
            if "error" in response:
                error = response["error"].get("detail", response["error"])
                persist_message(
                    metadata,
                    {
                        "error": {"content": error},
                    },
                )

            if "selected_model_id" in response:
                persist_message(
                    metadata,
                    {
                        "selectedModelId": response["selected_model_id"],
                    },
                )

            choices = response.get("choices", [])
            if choices and choices[0].get("message", {}).get("content"):
                content = response["choices"][0]["message"]["content"]

                if content:
                    await emit_completion(event_emitter, response)

                    title = Chats.get_chat_title_by_id(metadata["chat_id"])

                    await emit_completion(
                        event_emitter,
                        {"done": True, "content": content, "title": title},
                    )

                    # Save message in the database
                    persist_message(
                        metadata,
                        {
                            "role": "assistant",
                            "content": content,
                        },
                    )

                    notify_webhook_if_offline(request, user, metadata, title, content)

                    await background_tasks_handler()

        # Identical for the emitter and no-emitter paths: fold the precomputed
        # events into the response body.
        if events and isinstance(events, list) and isinstance(response, dict):
            extra_response = {}
            for event in events:
                if isinstance(event, dict):
                    extra_response.update(event)
                else:
                    extra_response[event] = True

            response = {
                **extra_response,
                **response,
            }

        return response

    # Non standard response
    if not any(
        content_type in response.headers["Content-Type"]
        for content_type in ["text/event-stream", "application/x-ndjson"]
    ):
        return response

    extra_params = build_extra_params(
        request, model, metadata, user, event_emitter, event_caller
    )
    filter_functions = get_filter_functions(request, model, metadata)

    # Streaming response
    if event_emitter and event_caller:
        model_id = form_data.get("model", "")

        persist_message(
            metadata,
            {
                "model": model_id,
            },
        )

        # Handle as a background task
        async def response_handler(response, events):
            message = Chats.get_message_by_id_and_message_id(
                metadata["chat_id"], metadata["message_id"]
            )

            tool_calls = []

            last_assistant_message = None
            try:
                if form_data["messages"][-1]["role"] == "assistant":
                    last_assistant_message = get_last_assistant_message(
                        form_data["messages"]
                    )
            except Exception:
                pass

            content = (
                message.get("content", "")
                if message
                else last_assistant_message
                if last_assistant_message
                else ""
            )

            content_blocks = [
                {
                    "type": "text",
                    "content": content,
                }
            ]

            DETECT_CODE_INTERPRETER = metadata.get("features", {}).get(
                "code_interpreter", False
            )

            reasoning_tags = [
                ("<think>", "</think>"),
                ("<thinking>", "</thinking>"),
                ("<reason>", "</reason>"),
                ("<reasoning>", "</reasoning>"),
                ("<thought>", "</thought>"),
                ("<Thought>", "</Thought>"),
                ("<|begin_of_thought|>", "<|end_of_thought|>"),
                ("◁think▷", "◁/think▷"),
            ]

            code_interpreter_tags = [("<code_interpreter>", "</code_interpreter>")]

            solution_tags = [("<|begin_of_solution|>", "<|end_of_solution|>")]

            try:
                for event in events:
                    await emit_completion(event_emitter, event)

                    # Save message in the database
                    persist_message(
                        metadata,
                        {
                            **event,
                        },
                    )

                async def stream_body_handler(response, form_data):
                    nonlocal content
                    nonlocal content_blocks

                    response_tool_calls = []

                    async for line in response.body_iterator:
                        line = line.decode("utf-8") if isinstance(line, bytes) else line
                        data = line

                        # Skip empty lines
                        if not data.strip():
                            continue

                        # "data:" is the prefix for each event
                        if not data.startswith("data:"):
                            continue

                        # Remove the prefix
                        data = data[len("data:") :].strip()

                        try:
                            data = json.loads(data)

                            data, _ = await process_filter_functions(
                                request=request,
                                filter_functions=filter_functions,
                                filter_type="stream",
                                form_data=data,
                                extra_params={"__body__": form_data, **extra_params},
                            )

                            if data:
                                if "event" in data:
                                    await event_emitter(data.get("event", {}))

                                if "selected_model_id" in data:
                                    model_id = data["selected_model_id"]
                                    persist_message(
                                        metadata,
                                        {
                                            "selectedModelId": model_id,
                                        },
                                    )
                                else:
                                    choices = data.get("choices", [])
                                    if not choices:
                                        error = data.get("error", {})
                                        if error:
                                            await emit_completion(
                                                event_emitter, {"error": error}
                                            )
                                        usage = data.get("usage", {})
                                        if usage:
                                            await emit_completion(
                                                event_emitter, {"usage": usage}
                                            )
                                        continue

                                    delta = choices[0].get("delta", {})
                                    delta_tool_calls = delta.get("tool_calls", None)

                                    if delta_tool_calls:
                                        accumulate_tool_call_deltas(
                                            response_tool_calls, delta_tool_calls
                                        )

                                    value = delta.get("content")

                                    reasoning_content = (
                                        delta.get("reasoning_content")
                                        or delta.get("reasoning")
                                        or delta.get("thinking")
                                    )
                                    if reasoning_content:
                                        if (
                                            not content_blocks
                                            or content_blocks[-1]["type"] != "reasoning"
                                        ):
                                            reasoning_block = {
                                                "type": "reasoning",
                                                "start_tag": "think",
                                                "end_tag": "/think",
                                                "attributes": {
                                                    "type": "reasoning_content"
                                                },
                                                "content": "",
                                                "started_at": time.time(),
                                            }
                                            content_blocks.append(reasoning_block)
                                        else:
                                            reasoning_block = content_blocks[-1]

                                        reasoning_block["content"] += reasoning_content

                                        data = {
                                            "content": serialize_content_blocks(
                                                content_blocks
                                            )
                                        }

                                    if value:
                                        if (
                                            content_blocks
                                            and content_blocks[-1]["type"]
                                            == "reasoning"
                                            and content_blocks[-1]
                                            .get("attributes", {})
                                            .get("type")
                                            == "reasoning_content"
                                        ):
                                            reasoning_block = content_blocks[-1]
                                            reasoning_block["ended_at"] = time.time()
                                            reasoning_block["duration"] = int(
                                                reasoning_block["ended_at"]
                                                - reasoning_block["started_at"]
                                            )

                                            append_empty_text_block(content_blocks)

                                        content = f"{content}{value}"
                                        if not content_blocks:
                                            append_empty_text_block(content_blocks)

                                        content_blocks[-1]["content"] = (
                                            content_blocks[-1]["content"] + value
                                        )

                                        content, content_blocks, _ = (
                                            tag_content_handler(
                                                "reasoning",
                                                reasoning_tags,
                                                content,
                                                content_blocks,
                                            )
                                        )

                                        if DETECT_CODE_INTERPRETER:
                                            content, content_blocks, end = (
                                                tag_content_handler(
                                                    "code_interpreter",
                                                    code_interpreter_tags,
                                                    content,
                                                    content_blocks,
                                                )
                                            )

                                            if end:
                                                break

                                        content, content_blocks, _ = (
                                            tag_content_handler(
                                                "solution",
                                                solution_tags,
                                                content,
                                                content_blocks,
                                            )
                                        )

                                        if ENABLE_REALTIME_CHAT_SAVE:
                                            # Save message in the database
                                            persist_message(
                                                metadata,
                                                {
                                                    "content": serialize_content_blocks(
                                                        content_blocks
                                                    ),
                                                },
                                            )
                                        else:
                                            data = {
                                                "content": serialize_content_blocks(
                                                    content_blocks
                                                ),
                                            }

                                await emit_completion(event_emitter, data)
                        except Exception as e:
                            # `data: [DONE]` fails json.loads by design; anything
                            # else is a real parse error worth logging. Neither
                            # ends the loop — content after the sentinel is still
                            # processed (frozen bug, see the ledger).
                            if "data: [DONE]" not in line:
                                log.debug(f"Error: {e}")

                    if content_blocks:
                        # Clean up the last text block
                        if content_blocks[-1]["type"] == "text":
                            content_blocks[-1]["content"] = content_blocks[-1][
                                "content"
                            ].strip()

                            if not content_blocks[-1]["content"]:
                                content_blocks.pop()

                                if not content_blocks:
                                    append_empty_text_block(content_blocks)

                    if response_tool_calls:
                        tool_calls.append(response_tool_calls)

                    if response.background:
                        await response.background()

                async def continue_stream_round(build_new_form_data):
                    """One continuation round: emit the blocks, request the next
                    stream, drain it. Returns False when the caller must break.

                    Nested on purpose: it closes over stream_body_handler and
                    the fenced state. `build_new_form_data` is a thunk so
                    payload construction stays INSIDE the try — a KeyError
                    there is a logged break, not a task crash.
                    """
                    append_empty_text_block(content_blocks)

                    await emit_content(event_emitter, content_blocks)

                    try:
                        new_form_data = build_new_form_data()

                        res = await generate_chat_completion(
                            request,
                            new_form_data,
                            user,
                        )

                        if isinstance(res, StreamingResponse):
                            await stream_body_handler(res, new_form_data)
                        else:
                            return False
                    except Exception as e:
                        log.debug(e)
                        return False
                    return True

                await stream_body_handler(response, form_data)

                MAX_TOOL_CALL_RETRIES = 10
                tool_call_retries = 0

                while len(tool_calls) > 0 and tool_call_retries < MAX_TOOL_CALL_RETRIES:
                    tool_call_retries += 1

                    response_tool_calls = tool_calls.pop(0)

                    content_blocks.append(
                        {
                            "type": "tool_calls",
                            "content": response_tool_calls,
                        }
                    )

                    await emit_content(event_emitter, content_blocks)

                    tools = metadata.get("tools", {})

                    results = []

                    for tool_call in response_tool_calls:
                        tool_call_id = tool_call.get("id", "")
                        tool_name = tool_call.get("function", {}).get("name", "")
                        tool_args = tool_call.get("function", {}).get("arguments", "{}")

                        tool_function_params = {}
                        try:
                            # json.loads cannot be used because some models do not produce valid JSON
                            tool_function_params = ast.literal_eval(tool_args)
                        except Exception as e:
                            log.debug(e)
                            # Fallback to JSON parsing
                            try:
                                tool_function_params = json.loads(tool_args)
                            except Exception as e:
                                log.error(
                                    f"Error parsing tool call arguments: {tool_args}"
                                )

                        # Mutate the original tool call response params as they are passed back to the passed
                        # back to the LLM via the content blocks. If they are in a json block and are invalid json,
                        # this can cause downstream LLM integrations to fail (e.g. bedrock gateway) where response
                        # params are not valid json.
                        # Main case so far is no args = "" = invalid json.
                        log.debug(
                            f"Parsed args from {tool_args} to {tool_function_params}"
                        )
                        tool_call.setdefault("function", {})["arguments"] = json.dumps(
                            tool_function_params
                        )

                        tool_result = None
                        tool_result_files = []

                        if tool_name in tools:
                            (
                                tool_result,
                                tool_result_files,
                                tool_function_params,
                            ) = await execute_tool_call(
                                tools[tool_name],
                                tool_name,
                                tool_function_params,
                                event_caller,
                                metadata,
                                ensure_ascii=False,
                            )

                        results.append(
                            {
                                "tool_call_id": tool_call_id,
                                "content": tool_result,
                                **(
                                    {"files": tool_result_files}
                                    if tool_result_files
                                    else {}
                                ),
                            }
                        )

                    content_blocks[-1]["results"] = results

                    if not await continue_stream_round(
                        lambda: {
                            "model": model_id,
                            "stream": True,
                            "tools": form_data["tools"],
                            "messages": [
                                *form_data["messages"],
                                *convert_content_blocks_to_messages(content_blocks),
                            ],
                        }
                    ):
                        break

                if DETECT_CODE_INTERPRETER:
                    MAX_RETRIES = 5
                    retries = 0

                    while (
                        content_blocks[-1]["type"] == "code_interpreter"
                        and retries < MAX_RETRIES
                    ):
                        await emit_content(event_emitter, content_blocks)

                        retries += 1
                        log.debug(f"Attempt count: {retries}")

                        output = ""
                        try:
                            if content_blocks[-1]["attributes"].get("type") == "code":
                                code = content_blocks[-1]["content"]

                                if (
                                    request.app.state.config.CODE_INTERPRETER_ENGINE
                                    == "pyodide"
                                ):
                                    output = await event_caller(
                                        {
                                            "type": "execute:python",
                                            "data": {
                                                "id": str(uuid4()),
                                                "code": code,
                                                "session_id": metadata.get(
                                                    "session_id", None
                                                ),
                                            },
                                        }
                                    )
                                elif (
                                    request.app.state.config.CODE_INTERPRETER_ENGINE
                                    == "jupyter"
                                ):
                                    output = await execute_code_jupyter(
                                        request.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
                                        code,
                                        (
                                            request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN
                                            if request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH
                                            == "token"
                                            else None
                                        ),
                                        (
                                            request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD
                                            if request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH
                                            == "password"
                                            else None
                                        ),
                                        request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
                                    )
                                else:
                                    output = {
                                        "stdout": "Code interpreter engine not configured."
                                    }

                                log.debug(f"Code interpreter output: {output}")

                                if isinstance(output, dict):
                                    stdout = output.get("stdout", "")

                                    if isinstance(stdout, str):
                                        output["stdout"] = upload_b64_images_in_text(
                                            request, stdout, metadata, user
                                        )

                                    result = output.get("result", "")

                                    if isinstance(result, str):
                                        output["result"] = upload_b64_images_in_text(
                                            request, result, metadata, user
                                        )
                        except Exception as e:
                            output = str(e)

                        content_blocks[-1]["output"] = output

                        if not await continue_stream_round(
                            lambda: {
                                "model": model_id,
                                "stream": True,
                                "messages": [
                                    *form_data["messages"],
                                    {
                                        "role": "assistant",
                                        "content": serialize_content_blocks(
                                            content_blocks, raw=True
                                        ),
                                    },
                                ],
                            }
                        ):
                            break

                # The stream is over. Close anything still open BEFORE the last
                # serialize, or a block the provider never closed is persisted
                # mid-flight and renders as "Thinking…" forever, with the answer
                # sealed inside it.
                finalize_content_blocks(content_blocks)

                title = Chats.get_chat_title_by_id(metadata["chat_id"])
                data = {
                    "done": True,
                    "content": serialize_content_blocks(content_blocks),
                    "title": title,
                }

                if not ENABLE_REALTIME_CHAT_SAVE:
                    # Save message in the database
                    persist_message(
                        metadata,
                        {
                            "content": serialize_content_blocks(content_blocks),
                        },
                    )

                # The raw accumulator, not the serialized blocks — deliberate.
                notify_webhook_if_offline(request, user, metadata, title, content)

                await emit_completion(event_emitter, data)

                await background_tasks_handler()
            except asyncio.CancelledError:
                log.warning("Task was cancelled!")
                await event_emitter({"type": "task-cancelled"})

                # Same reason as the normal path, and it has to happen HERE
                # rather than in a `finally`: this handler saves, and a `finally`
                # would run after that save. A cancelled stream is the case most
                # likely to leave a block open, so it is the last one to leave
                # unfinalized. Safe to run twice — the finalizer is idempotent.
                finalize_content_blocks(content_blocks)

                if not ENABLE_REALTIME_CHAT_SAVE:
                    # Save message in the database
                    persist_message(
                        metadata,
                        {
                            "content": serialize_content_blocks(content_blocks),
                        },
                    )

            if response.background is not None:
                await response.background()

        # background_tasks.add_task(response_handler, response, events)
        task_id, _ = await create_task(
            request.app.state.redis,
            response_handler(response, events),
            id=metadata["chat_id"],
        )
        return {"status": True, "task_id": task_id}

    else:
        # Fallback to the original response
        async def stream_wrapper(original_generator, events):
            def wrap_item(item):
                return f"data: {item}\n\n"

            for event in events:
                event, _ = await process_filter_functions(
                    request=request,
                    filter_functions=filter_functions,
                    filter_type="stream",
                    form_data=event,
                    extra_params=extra_params,
                )

                if event:
                    yield wrap_item(json.dumps(event))

            async for data in original_generator:
                data, _ = await process_filter_functions(
                    request=request,
                    filter_functions=filter_functions,
                    filter_type="stream",
                    form_data=data,
                    extra_params=extra_params,
                )

                if data:
                    yield data

        return StreamingResponse(
            stream_wrapper(response.body_iterator, events),
            headers=dict(response.headers),
            background=response.background,
        )
