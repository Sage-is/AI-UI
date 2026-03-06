import logging
from typing import Optional

from sage_is_ai.bridges.types import OutgoingMessage
from sage_is_ai.models.bridges import BridgeConnections, BridgeThreads

log = logging.getLogger(__name__)


async def forward_channel_message_to_bridges(
    app,
    channel_id: str,
    content: str,
    user_id: str,
    message_id: str,
) -> None:
    """Forward a Sage channel message to all connected external bridges.

    Called as a background task when a message is posted in a channel.
    Skips messages that originated from bridges (loop prevention).
    """
    bridge_manager = getattr(app.state, "bridge_manager", None)
    if not bridge_manager:
        return

    # Find all enabled bridge connections linked to this channel
    connections = BridgeConnections.get_enabled_connections()
    channel_bridges = [
        c for c in connections
        if c.mode == "channel_bridge" and c.channel_id == channel_id
    ]

    if not channel_bridges:
        return

    from sage_is_ai.models.users import Users

    user = Users.get_user_by_id(user_id)
    sender_name = user.name if user else "Unknown"

    for connection in channel_bridges:
        adapter = bridge_manager.get_adapter(connection.id)
        if not adapter or not adapter.connected:
            continue

        # Get all threads for this connection to know which external chats to forward to
        threads = BridgeThreads.get_threads_by_connection_id(connection.id)

        if not threads:
            continue

        # Forward to each active external thread
        formatted_content = f"*{sender_name}*: {content}"

        for thread in threads:
            try:
                await adapter.send_message(
                    OutgoingMessage(
                        thread_id=thread.external_thread_id,
                        content=formatted_content,
                    )
                )
            except Exception as e:
                log.error(
                    f"Failed to forward message to bridge thread "
                    f"{thread.external_thread_id}: {e}"
                )
