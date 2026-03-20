import logging
import time

from sage_is_ai.models.tools import (
    ToolUserResponse,
)
from fastapi import APIRouter, Depends, Request
from sage_is_ai.utils.auth import get_verified_user
from sage_is_ai.utils.access_control import has_access
from sage_is_ai.env import SRC_LOG_LEVELS

from sage_is_ai.utils.tools import get_tool_servers_data


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


router = APIRouter()

############################
# GetTools
############################


@router.get("/", response_model=list[ToolUserResponse])
async def get_tools(request: Request, user=Depends(get_verified_user)):

    if not request.app.state.TOOL_SERVERS:
        # If the tool servers are not set, we need to set them
        # This is done only once when the server starts
        # This is done to avoid loading the tool servers every time

        request.app.state.TOOL_SERVERS = await get_tool_servers_data(
            request.app.state.config.TOOL_SERVER_CONNECTIONS
        )

    tools = []
    for server in request.app.state.TOOL_SERVERS:
        tools.append(
            ToolUserResponse(
                **{
                    "id": f"server:{server['idx']}",
                    "user_id": f"server:{server['idx']}",
                    "name": server.get("openapi", {})
                    .get("info", {})
                    .get("title", "Tool Server"),
                    "meta": {
                        "description": server.get("openapi", {})
                        .get("info", {})
                        .get("description", ""),
                    },
                    "access_control": request.app.state.config.TOOL_SERVER_CONNECTIONS[
                        server["idx"]
                    ]
                    .get("config", {})
                    .get("access_control", None),
                    "updated_at": int(time.time()),
                    "created_at": int(time.time()),
                }
            )
        )

    if user.role != "admin":
        tools = [
            tool
            for tool in tools
            if tool.user_id == user.id
            or has_access(user.id, "read", tool.access_control)
        ]

    return tools
